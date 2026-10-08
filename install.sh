#!/bin/sh
# Install a versioned wheel/local package into a dedicated environment.
set -eu
case "${1:-}" in
  "") ;;
  -h|--help) echo "Usage: bash install.sh"; exit 0 ;;
  *) echo "Usage: bash install.sh" >&2; exit 2 ;;
esac
if [ "$#" -ne 0 ]; then echo "Unexpected arguments" >&2; exit 2; fi
task_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
task_env="${HANDRAIL_VENV:-$HOME/.local/share/handrail/venv}"
task_bin="${HANDRAIL_BIN:-$HOME/.local/bin}"
if [ -e "$task_bin/handrail" ] && [ ! -L "$task_bin/handrail" ]; then
  echo "Refusing to overwrite $task_bin/handrail" >&2
  exit 1
fi
python3 -m venv "$task_env"
"$task_env/bin/python" -m pip install "$task_root"
mkdir -p "$task_bin"
ln -sfn "$task_env/bin/handrail" "$task_bin/handrail"
echo "Installed $task_bin/handrail. Ensure $task_bin is on PATH."
