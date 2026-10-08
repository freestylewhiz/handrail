"""Read-only discovery of real paths; access() is a hint, not a sandbox grant."""
import os
import shutil
from pathlib import Path
from handrail.shared.errors import HandrailError
from .settings import context, data_root, connection


def path_check(path, action):
    original = Path(path)
    nearest = original
    while not nearest.exists() and nearest != nearest.parent:
        nearest = nearest.parent
    return {"path": str(original), "action": action, "exists": original.exists(),
            "nearest_existing": str(nearest), "os_access_hint": os.access(nearest, os.W_OK),
            "host_permission": "not_proven"}


def doctor(repo="."):
    checks = [{"name": name, "path": shutil.which(name), "available": bool(shutil.which(name)),
               "required": name in ("git", "herdr")}
              for name in ("git", "herdr", "codex", "cursor-agent")]
    result = {"executables": checks, "data_root": str(data_root()), "mode": "inside" if
              os.environ.get("HERDR_ENV") == "1" else "external", "writes_performed": False}
    try:
        result["preflight"] = preflight(repo)
    except HandrailError as exc:
        result["setup"] = exc.as_dict()
    result["exit_code"] = 2 if "setup" in result else 1 if any(c["required"] and not c["available"] for c in checks) else 0
    return result


def preflight(repo="."):
    ctx = context(repo)
    config = ctx["config"]
    profile = connection(config["profile"])
    attempts = [a for a in ctx["store"].list("attempt") if not a.get("worktree_removed")]
    paths = sorted({a["path"] for a in attempts})
    return {"workspace_id": config["workspace_id"], "endpoint": config["endpoint"],
            "resources": [path_check(config["repo"], "integrate and verify"),
                          path_check(config["common_dir"], "git metadata and objects"),
                          path_check(config["worktree_root"], "worker sources and dependencies"),
                          path_check(ctx["store"].path, "private journal and execution state")] +
                         [path_check(path, "existing worker source and dependency writes") for path in paths],
            "network": {"connection": config["profile"], "url": profile["url"], "project_id": config["project_id"]},
            "pinned_cycles": ctx["store"].list("cycle_scope"),
            "ipc": config["endpoint"], "host_ready": "unknown",
            "note": "Host sandbox, IPC and network permissions are independent of Handrail grants."}
