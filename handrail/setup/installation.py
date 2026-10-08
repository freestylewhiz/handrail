"""Report exact paths from the loaded runtime, without reconstructing cache layout."""
import json
from pathlib import Path
from handrail import __version__
from handrail.shared.errors import HandrailError


def locate():
    package = Path(__file__).resolve().parents[1]
    candidates = [package.parent.parent, package.parent / "plugins/handrail"]
    for root in candidates:
        skill = root / "skills/handrail/SKILL.md"
        launcher = root / "scripts/handrail.py"
        if skill.is_file() and launcher.is_file():
            manifest = json.loads((root / ".codex-plugin/plugin.json").read_text())
            if manifest.get("name") != "handrail":
                continue
            return {"version": __version__, "plugin_version": manifest["version"],
                    "plugin_root": str(root), "skill_path": str(skill), "launcher": str(launcher),
                    "stable_launcher": str(Path.home() / ".local/bin/handrail"),
                    "cursor_skill": str(Path.home() / ".cursor/skills/handrail/SKILL.md"),
                    "runtime": str(package), "bundled": package.parent.name == "runtime",
                    "next": "Use the stable_launcher with --repo ABSOLUTE_REPO before the command; compare this version with the loaded skill"}
    raise HandrailError("PLUGIN_LAYOUT_INVALID", "The loaded runtime has no matching plugin skill and launcher")
