"""Discover existing endpoints without creating sessions or spoofing HERDR_ENV."""
import os
from pathlib import Path
from handrail.interfaces.agentroom.herdr import HerdrClient
from handrail.shared.errors import HandrailError
from .interaction import choose


def probe(endpoint):
    HerdrClient(endpoint, timeout=5)._json("workspace", "list")
    return {"endpoint": endpoint, "reachable": True}


def discover(explicit=None, saved=None):
    if explicit or saved:
        selected = explicit or saved
        probe(selected)
        return selected
    candidates = []
    for key, field in (("HERDR_SOCKET_PATH", "socket"), ("HERDR_SESSION", "session")):
        if os.environ.get(key):
            candidates.append({field: os.environ[key]})
    roots = {Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "herdr"}
    if os.environ.get("HERDR_CONFIG_PATH"):
        roots.add(Path(os.environ["HERDR_CONFIG_PATH"]).expanduser().parent)
    for root in roots:
        if root.is_dir():
            for path in root.rglob("*.sock"):
                if path.is_socket():
                    candidates.append({"socket": str(path.absolute())})
    unique = {tuple(row.items()): row for row in candidates}
    reachable, failures = [], []
    for row in unique.values():
        try:
            probe(row)
            reachable.append(row)
        except HandrailError as exc:
            failures.append({"endpoint": row, "error": exc.as_dict()})
    if not reachable:
        raise HandrailError("HERDR_CONNECTION_REQUIRED", "Start Herdr or allow access to the discovered endpoint",
                            details={"boundary": "host/ipc", "candidates": failures,
                                     "next": "Run handrail init again after resolving IPC access; no session will be created"})
    selected = choose("herdr", [{"name": next(iter(e.values())), "label": next(iter(e.values())),
                                  "value": i} for i, e in enumerate(reachable)])
    return reachable[selected]
