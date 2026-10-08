#!/usr/bin/env python3
"""Build the current nested runtime and skill as an isolated plugin artifact."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from audit_runtime import require_valid

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0a6"
PLUGIN_VERSION = "1.0.0-alpha.6"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_tree(source, destination, predicate):
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if "__pycache__" in relative.parts:
            continue
        if path.is_symlink():
            raise SystemExit("Refusing symlink in build inputs: " + str(path))
        if path.is_file() and predicate(path):
            output = destination / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    destination = args.output.expanduser().resolve()
    if destination.exists():
        raise SystemExit("Output already exists; choose a new build directory")
    metadata = json.loads((ROOT / "plugins/handrail/plugin.json").read_text())
    compatible = json.loads((ROOT / "plugins/handrail/.codex-plugin/plugin.json").read_text())
    plugin_version = compatible["version"]
    if (metadata["version"] != plugin_version or not re.fullmatch(
            re.escape(PLUGIN_VERSION) + r"(?:\+codex\.[a-z0-9-]+)?", plugin_version)):
        raise SystemExit("Plugin versions do not match the build")
    if f'version = "{VERSION}"' not in (ROOT / "pyproject.toml").read_text():
        raise SystemExit("Package version does not match the build")
    if f'__version__ = "{VERSION}"' not in (ROOT / "handrail/__init__.py").read_text():
        raise SystemExit("Runtime version does not match the build")
    audit = require_valid(ROOT / "handrail")
    output = destination / "handrail"
    output.mkdir(parents=True)
    copy_tree(ROOT / "plugins/handrail", output, lambda path: path.suffix in (".md", ".json", ".py"))
    copy_tree(ROOT / "handrail", output / "runtime/handrail", lambda path: path.suffix == ".py")
    shutil.copyfile(ROOT / "LICENSE", output / "LICENSE")
    revision = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True)
    status = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True)
    files = {path.relative_to(output).as_posix(): sha(path) for path in sorted(output.rglob("*")) if path.is_file()}
    require_valid(output / "runtime/handrail")
    info = {"version": VERSION, "plugin_version": plugin_version,
            "static_import_audit": {"modules": audit["modules"], "errors": audit["errors"], "scope": audit["scope"]},
            "source_revision": revision.stdout.strip() if revision.returncode == 0 else None,
            "source_tree_dirty": bool(status.stdout.strip()), "files_sha256": files}
    (output / "build-info.json").write_text(json.dumps(info, indent=2) + "\n")
    archive = destination / f"handrail-{plugin_version}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(output.rglob("*")):
            if path.is_file():
                member = zipfile.ZipInfo(path.relative_to(destination).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
                member.compress_type = zipfile.ZIP_DEFLATED
                member.external_attr = 0o100644 << 16
                bundle.writestr(member, path.read_bytes())
    (destination / "SHA256SUMS").write_text(sha(archive) + "  " + archive.name + "\n")
    print(json.dumps({"plugin": str(output), "archive": str(archive), "sha256": sha(archive)}))


if __name__ == "__main__":
    main()
