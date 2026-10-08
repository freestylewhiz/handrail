"""Local process continuity evidence; display status and PID alone are insufficient."""
import hashlib
from pathlib import Path
from handrail.shared.errors import HandrailError
from .identity import record


def process_identity(client, pane):
    info = record(client.pane_process_info(pane), "process_info")
    if info.get("pane_id") != pane:
        raise HandrailError("PROCESS_IDENTITY", "Process observation belongs to another pane")
    try:
        boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        processes = []
        for entry in info.get("foreground_processes", []):
            pid = entry.get("pid")
            if not isinstance(pid, int) or pid <= 0:
                continue
            root = Path("/proc") / str(pid)
            stat = (root / "stat").read_text().rsplit(")", 1)[1].split()
            # Fields 3 onward: pgrp=5, starttime=22. Bind PID to boot and birth.
            if int(stat[2]) != info.get("foreground_process_group_id"):
                return None
            executable = str((root / "exe").resolve(strict=True))
            argv = (root / "cmdline").read_bytes()
            first = argv.split(b"\0", 1)[0].decode(errors="replace")
            # Prefer the actual provider process. A persistent shell wrapper
            # would otherwise hide replacement of its child agent. Transient
            # Git/tool subprocesses are not part of the execution identity.
            names = {Path(executable).name, Path(first).name}
            parts = [p.decode(errors="replace") for p in argv.split(b"\0")[:4] if p]
            script_provider = (Path(executable).name in ("node", "bun", "nodejs") and any(
                "cursor-agent" in Path(p).parts or ("@openai" in Path(p).parts and "codex" in Path(p).parts)
                for p in parts[1:] if not p.startswith("-")))
            if not script_provider and not any(n in ("codex", "cursor-agent", "agent") for n in names):
                continue
            actual_cwd = str((root / "cwd").resolve(strict=True))
            if entry.get("cwd") and actual_cwd != str(Path(entry["cwd"]).resolve()):
                return None
            processes.append({"pid": pid, "start_ticks": stat[19], "cwd": actual_cwd,
                              "executable": executable,
                              "argv_sha256": hashlib.sha256(argv).hexdigest()})
        if not processes or info.get("foreground_process_group_id") == info.get("shell_pid"):
            return None
        return {"boot_id": boot, "pane_id": pane, "shell_pid": info.get("shell_pid"),
                "processes": sorted(processes, key=lambda p: p["pid"])}
    except (OSError, ValueError, IndexError):
        return None


def session_key(value):
    if isinstance(value, dict):
        return (value.get("agent"), value.get("kind"), value.get("value"))
    return value


def reconcile_identity(pinned, current, process, *, explicit=False):
    for key in ("workspace_id", "pane_id", "terminal_id", "provider"):
        if pinned.get(key) != current.get(key):
            raise HandrailError("ROOM_OCCUPANT_CHANGED", "Recorded worker location or provider changed",
                                details={"field": key, "expected": pinned.get(key), "observed": current.get(key)})
    if pinned.get("name") and current.get("name") != pinned["name"]:
        raise HandrailError("ROOM_OCCUPANT_CHANGED", "Worker registration changed")
    before, after = session_key(pinned.get("provider_session")), session_key(current.get("provider_session"))
    old_process = pinned.get("process_identity")
    continuous = bool(old_process and process and old_process == process)
    if before and before != after:
        raise HandrailError("IDENTITY_STALE", "Provider conversation changed; inspect an explicit replacement",
                            details={"pane_id": current["pane_id"]})
    if old_process and process and old_process != process:
        raise HandrailError("IDENTITY_STALE", "Worker process changed; recover its execution explicitly")
    if not before and (after or current.get("provider")) and not continuous:
        if not explicit or not process:
            raise HandrailError("IDENTITY_UNPROVEN", "Inspect and reconcile the worker identity before continuing",
                                details={"pane_id": current["pane_id"], "session_observed": bool(after),
                                         "process_observed": bool(process), "next": "plan cleanup PLAN --inspect"})
    return dict(current, process_identity=process or old_process)
