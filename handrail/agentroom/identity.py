from pathlib import Path
from handrail.shared.errors import HandrailError


def record(payload, key):
    if isinstance(payload, dict) and isinstance(payload.get(key), dict):
        return payload[key]
    if isinstance(payload, dict):
        return payload
    raise HandrailError("ROOM_RESPONSE", "Agentroom returned an invalid identity record")


def agent_identity(payload):
    row = record(payload, "agent")
    if not row.get("pane_id") or not row.get("terminal_id") or not row.get("workspace_id"):
        raise HandrailError("AGENT_IDENTITY", "Herdr response lacks pane, workspace or terminal identity")
    session = row.get("agent_session")
    return {"workspace_id": row["workspace_id"], "pane_id": row["pane_id"],
            "terminal_id": row["terminal_id"], "provider_session": session,
            "provider": row.get("agent"), "name": row.get("name")}


def assert_agent(pinned, observed, worktree=None):
    current = agent_identity(observed)
    for key in ("workspace_id", "pane_id", "terminal_id", "provider"):
        if pinned.get(key) != current.get(key):
            raise HandrailError("IDENTITY_STALE", "Worker occupant changed; recover explicitly", details={"field": key})
    from .process import session_key
    if pinned.get("provider_session") and session_key(current.get("provider_session")) != session_key(pinned["provider_session"]):
        raise HandrailError("IDENTITY_STALE", "Provider conversation changed; recover explicitly")
    row = record(observed, "agent")
    cwd = row.get("foreground_cwd") or row.get("cwd")
    if worktree and cwd:
        root, actual = Path(worktree).resolve(), Path(cwd).resolve()
        if actual != root and root not in actual.parents:
            raise HandrailError("WORKER_LOCATION", "Worker is outside its recorded checkout")
    return row


def find_value(value, key):
    if isinstance(value, dict):
        if key in value and value[key] is not None:
            return value[key]
        for item in value.values():
            found = find_value(item, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = find_value(item, key)
            if found is not None:
                return found
    return None


def pane_ids(value):
    output = set()
    if isinstance(value, dict):
        if value.get("pane_id"):
            output.add(value["pane_id"])
        for item in value.values():
            output.update(pane_ids(item))
    elif isinstance(value, list):
        for item in value:
            output.update(pane_ids(item))
    return output
