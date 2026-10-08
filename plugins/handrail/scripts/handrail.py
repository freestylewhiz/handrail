#!/usr/bin/env python3
"""Read-only-cache launcher for the bundled Handrail runtime."""
import os
from pathlib import Path
import sys

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
plugin_root = Path(__file__).resolve().parent.parent
runtime_root = plugin_root / "runtime"
if not (runtime_root / "handrail" / "__init__.py").is_file():
    sys.stderr.write("Handrail bundled runtime is missing. Rebuild or reinstall the plugin.\n")
    raise SystemExit(2)
try:
    import json
    build_info = json.loads((plugin_root / "build-info.json").read_text(encoding="utf-8"))
    os.environ["HANDRAIL_BUILD_REVISION"] = str(build_info.get("source_revision") or "")
except (OSError, ValueError):
    sys.stderr.write("Handrail build metadata is missing or invalid. Rebuild or reinstall the plugin.\n")
    raise SystemExit(2)
sys.path.insert(0, str(runtime_root))
from handrail.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
