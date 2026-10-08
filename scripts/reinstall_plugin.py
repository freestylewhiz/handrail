#!/usr/bin/env python3
"""Replace a managed Handrail installation; optionally clear host settings."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess


def run(*args):
    result = subprocess.run(["rtk", *args], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout


def verify(plugin):
    info = json.loads((plugin / "build-info.json").read_text())
    for relative, expected in info["files_sha256"].items():
        part = Path(relative)
        if part.is_absolute() or ".." in part.parts:
            raise RuntimeError("Invalid build member")
        path = plugin / part
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError("Build integrity mismatch: " + relative)
    manifest = json.loads((plugin / ".codex-plugin/plugin.json").read_text())
    if manifest["name"] != "handrail" or manifest["version"] != info["plugin_version"]:
        raise RuntimeError("Plugin identity mismatch")
    skill = plugin / "skills/handrail/SKILL.md"
    if not skill.read_text().startswith("---\nname: handrail\n"):
        raise RuntimeError("Skill discovery metadata missing")
    return info


def remove(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        for base, _, _ in os.walk(path, followlinks=False):
            directory = Path(base)
            if directory.stat().st_uid != os.getuid():
                raise RuntimeError("Not owned by current user: " + str(directory))
            directory.chmod(directory.stat().st_mode | 0o700)
        shutil.rmtree(path)


def reset_paths(home):
    """Inventory host manager state, leaving source worktrees and service data."""
    targets, preserved = [], []
    data = home / ".local/share/handrail"
    for root in (home / ".config/handrail", data, home / ".cache/handrail", home / ".local/state/handrail"):
        if root.is_symlink():
            raise RuntimeError("Inspect symlinked settings root before reset: " + str(root))
    for path in (home / ".config/handrail", home / ".cache/handrail", home / ".local/state/handrail"):
        if path.exists():
            targets.append(path)
    if data.exists():
        for path in sorted(data.iterdir()):
            if path.name in ("worktrees", "herdr-worktrees"):
                preserved.append(path)
            elif path.name == "projects" and path.is_dir() and not path.is_symlink():
                for project in sorted(path.iterdir()):
                    if not project.is_dir() or project.is_symlink():
                        targets.append(project)
                        continue
                    for child in sorted(project.iterdir()):
                        if child.name in ("worktrees", "herdr-worktrees"):
                            preserved.append(child)
                        else:
                            targets.append(child)
            elif path.name in ("venv", "plugins", "artifacts"):
                continue  # Installer cleans old runtime files after successful replacement.
            else:
                targets.append(path)
    # Inspect all targets before removing any: never mistake a checkout for state.
    for path in targets:
        if path.is_symlink() or not path.is_dir():
            continue
        for base, dirs, files in os.walk(path, followlinks=False):
            if ".git" in dirs or ".git" in files or any(n in dirs for n in ("worktrees", "herdr-worktrees")):
                raise RuntimeError("Source storage found inside reset target; inspect before deleting: " + str(path))
            if Path(base).stat().st_uid != os.getuid():
                raise RuntimeError("Settings are not owned by current user: " + str(base))
    return targets, preserved


def reset_settings(home, build):
    targets, preserved = reset_paths(home)
    report = {"removed": [], "preserved_worktree_roots": [str(p) for p in preserved],
              "preserved_service_data": str(home / ".local/share/handrail-development")}
    report_path = build / "host-settings-reset.json"
    for path in targets:
        remove(path)
        report["removed"].append(str(path))
        report_path.write_text(json.dumps(report, indent=2) + "\n")
    projects = home / ".local/share/handrail/projects"
    if projects.exists():
        for project in projects.iterdir():
            if project.is_dir() and not project.is_symlink() and not any(project.iterdir()):
                project.rmdir()
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--reset-settings", action="store_true",
                        help="Explicitly remove host Handrail credentials, bindings and journals before reinstall; preserve worktrees and external services")
    parser.add_argument("--dry-run", action="store_true", help="Inspect the install and reset paths without writing")
    args = parser.parse_args()
    build = args.build.resolve()
    source = build / "handrail"
    info = verify(source)
    version = info["plugin_version"]
    if not re.fullmatch(r"[0-9][A-Za-z0-9.+-]*", version):
        raise RuntimeError("Invalid version")
    home = Path.home()
    releases = home / ".local/share/handrail-plugin-releases"
    target = releases / version
    markets = json.loads(run("codex", "plugin", "marketplace", "list", "--json"))["marketplaces"]
    matches = [row for row in markets if row["name"] == "handrail"]
    if len(matches) != 1 or matches[0].get("marketplaceSource", {}).get("sourceType") != "local":
        raise RuntimeError("Expected one configured local Handrail marketplace")
    old = Path(matches[0]["root"])
    if old.parent != releases or old == target or target.exists():
        raise RuntimeError("Choose a new build version; source must be an existing managed local release")
    market_bytes = (old / ".agents/plugins/marketplace.json").read_bytes()
    market = json.loads(market_bytes)
    if market["name"] != "handrail" or len(market["plugins"]) != 1 or market["plugins"][0]["name"] != "handrail":
        raise RuntimeError("Marketplace contains unexpected plugins")
    if market["plugins"][0]["source"] != {"source": "local", "path": "./plugins/handrail"}:
        raise RuntimeError("Marketplace source does not match the managed bundle")
    command = home / ".local/bin/handrail"
    old_link = os.readlink(command) if command.is_symlink() else None
    old_command = command.read_bytes() if command.is_file() and not command.is_symlink() else None
    old_cache = home / ".codex/plugins/cache/handrail/handrail" / old.name
    cursor_skill = home / ".cursor/skills/handrail"
    old_cursor_link = os.readlink(cursor_skill) if cursor_skill.is_symlink() else None
    if cursor_skill.exists() and not cursor_skill.is_symlink():
        raise RuntimeError("Preserve the existing unmanaged Cursor skill; choose its ownership explicitly: " + str(cursor_skill))
    if old_cursor_link and not Path(old_cursor_link).is_relative_to(releases):
        raise RuntimeError("Existing Cursor skill points outside managed Handrail releases")
    if old_command and (not old_command.startswith(b"#!/bin/sh\n") or
                        not any(str(path).encode() in old_command for path in (old, old_cache))):
        raise RuntimeError("Global command is not the existing managed launcher")
    if old_link and not old_link.startswith(str(home / ".local/share/handrail/venv")):
        raise RuntimeError("Unexpected global command symlink")
    if args.dry_run:
        targets, preserved = reset_paths(home) if args.reset_settings else ([], [])
        print(json.dumps({"version": version, "reset_paths": [str(p) for p in targets],
                          "preserved_worktree_roots": [str(p) for p in preserved],
                          "stable_launcher": str(command), "cursor_skill": str(cursor_skill),
                          "old_release": str(old), "new_release": str(target)}, indent=2))
        return
    reset = reset_settings(home, build) if args.reset_settings else None
    shutil.copytree(source, target / "plugins/handrail")
    market_path = target / ".agents/plugins/marketplace.json"
    market_path.parent.mkdir(parents=True)
    market_path.write_bytes(market_bytes)
    for filename in ("handrail-" + version + ".zip", "SHA256SUMS"):
        shutil.copyfile(build / filename, target / filename)
    verify(target / "plugins/handrail")
    removed, switched = False, False
    try:
        print(run("codex", "plugin", "remove", "handrail@handrail", "--json"), flush=True)
        removed = True
        run("codex", "plugin", "marketplace", "remove", "handrail", "--json")
        switched = True
        run("codex", "plugin", "marketplace", "add", str(target))
        installed = json.loads(run("codex", "plugin", "add", "handrail@handrail", "--json"))
        cache = Path(installed["installedPath"])
        verify(cache)
        # Both providers use an owned release; Codex cache is discovery only.
        launcher = target / "plugins/handrail/scripts/handrail.py"
        command.parent.mkdir(parents=True, exist_ok=True)
        if command.is_symlink():
            command.unlink()
        command.write_text("#!/bin/sh\nexec /usr/bin/python3 -I " + shlex.quote(str(launcher)) + ' "$@"\n')
        command.chmod(0o755)
        cursor_skill.parent.mkdir(parents=True, exist_ok=True)
        if cursor_skill.is_symlink():
            cursor_skill.unlink()
        cursor_skill.symlink_to(target / "plugins/handrail/skills/handrail", target_is_directory=True)
        detected = json.loads(run(str(command), "locate"))
        if Path(detected["skill_path"]) != target / "plugins/handrail/skills/handrail/SKILL.md" or detected["plugin_version"] != version:
            raise RuntimeError("Installed skill discovery mismatch")
        actual_version = run(str(command), "--version").strip()
    except Exception:
        if cursor_skill.is_symlink() and Path(os.readlink(cursor_skill)).is_relative_to(target):
            cursor_skill.unlink()
            if old_cursor_link:
                cursor_skill.symlink_to(old_cursor_link, target_is_directory=True)
        # Keep old files until the new installation is confirmed, and restore native registration on failure.
        if removed:
            if switched:
                try:
                    run("codex", "plugin", "remove", "handrail@handrail", "--json")
                except RuntimeError:
                    pass
                try:
                    run("codex", "plugin", "marketplace", "remove", "handrail", "--json")
                except RuntimeError:
                    pass
                run("codex", "plugin", "marketplace", "add", str(old))
            run("codex", "plugin", "add", "handrail@handrail", "--json")
            if command.is_symlink() or command.exists():
                command.unlink()
            if old_link:
                command.symlink_to(old_link)
            elif old_command:
                command.write_bytes(old_command)
                command.chmod(0o755)
        raise
    deleted = []
    for path in releases.iterdir():
        if path != target and (re.fullmatch(r"[0-9][A-Za-z0-9.+-]*", path.name) or path.name == "backups"):
            remove(path)
            deleted.append(str(path))
    for path in (home / ".local/share/handrail/venv", home / ".local/share/handrail/plugins",
                 home / ".local/share/handrail/artifacts"):
        if path.exists() or path.is_symlink():
            remove(path)
            deleted.append(str(path))
    for path in cache.parent.iterdir():
        if path != cache:
            remove(path)
            deleted.append(str(path))
    report = {"version": actual_version, "installed": installed, "locate": detected,
              "cursor_skill": str(cursor_skill), "stable_launcher": str(command),
              "verified_files": len(info["files_sha256"]), "removed_installations": deleted,
              "settings_reset": reset,
              "preserved": (["worktrees", "external service data"] if reset is not None else
                            ["connections", "project bindings and histories", "worktrees", "external service data"]),
              "next": "Start a new Codex session in your project and request Handrail setup, or run handrail init"}
    (build / "host-install-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
