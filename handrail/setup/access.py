"""Reviewable, narrow provider rules for one stable launcher and repository."""
import json
import os
import shlex
from pathlib import Path
from handrail.shared.errors import HandrailError
from handrail.shared.identity import digest, now
from .settings import read_json, write_json
# Compatibility for existing callers; host rule management and filesystem
# diagnostics have separate implementations and must not replace each other.
from .write_access import check_writes

OPERATIONS = {
    "read": [("status",), ("history",), ("board", "list"), ("card", "list"), ("card", "read"),
             ("summary", "list"), ("summary", "read"), ("instruction", "list"), ("instruction", "read")],
    "board-sync": [("sync", "--topic", "board")],
    "labels-sync": [("card", "types")],
    "summary-sync": [("sync", "--topic", "summary")],
    "monitor": [("coordinator", "tick"), ("worker", "collect"), ("worker", "receive"), ("worker", "continue")],
    "cleanup": [("plan", "cleanup"), ("sync", "--topic", "room.cleanup")],
    "onboarding": [("init",)],
}

METRICS = ("host-approval", "user-choice", "wait")
CATEGORIES = ("intent", "board", "model", "host-execution", "acceptance", "cleanup")


def _replace(path, content):
    """Keep an existing policy file's mode and its directory's permissions."""
    import tempfile
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".handrail-policy-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def plan(config, provider, groups):
    if provider not in ("codex", "cursor") or not groups or any(g not in OPERATIONS for g in groups):
        raise HandrailError("ACCESS_SCOPE_INVALID", "Select provider and named operation groups", details={"groups": list(OPERATIONS)})
    launcher = str(Path.home() / ".local/bin/handrail")
    repo = str(Path(config["repo"]).resolve())
    if any(ord(ch) < 32 for ch in launcher + repo):
        raise HandrailError("ACCESS_PATH_INVALID", "Permission policy paths must not contain control characters")
    prefixes = []
    for group in dict.fromkeys(groups):
        for operation in OPERATIONS[group]:
            command = [launcher, "--repo", repo, *operation]
            prefixes.extend([command, ["rtk", *command]])
    if provider == "cursor" and any(any(c in token for c in "*?[]():\n\r\t ") for row in prefixes for token in row):
        raise HandrailError("ACCESS_PATTERN_UNSUPPORTED", "This path contains Cursor permission-pattern syntax; use host approval for the exact command")
    identity = digest(repo)[:16]
    target = (Path.home() / ".codex/rules" / ("handrail-" + identity + ".rules") if provider == "codex" else
              Path.home() / ".cursor/cli-config.json")
    rules = (["prefix_rule(pattern=" + json.dumps(p, ensure_ascii=False) + ", decision=\"allow\")" for p in prefixes]
             if provider == "codex" else ["Shell(" + p[0] + ":" + " ".join(p[1:]) + " *)" for p in prefixes] +
             ["Shell(" + p[0] + ":" + " ".join(p[1:]) + ")" for p in prefixes])
    return {"provider": provider, "surface": "CLI", "repo": repo, "launcher": launcher,
            "groups": list(dict.fromkeys(groups)), "target": str(target), "rules": rules,
            "prefixes": prefixes, "approval_boundary": "host command approval; workflow user intent stays separate",
            "network_scope": "The command uses this repository's saved Vikunja/Herdr binding",
            "effective_permission": "unverified until a new provider session observes these rules",
            "limitations": ["IDE and managed permission policies may not use CLI rules",
                            "No arbitrary Python, shell, raw Herdr, all-Handrail, or unrestricted network allowance",
                            "A rule covers subsequent arguments to its listed operation; inspect all selected groups"]}


def apply(config, provider, groups, approval):
    if not isinstance(approval, str) or not approval.strip():
        raise HandrailError("HOST_POLICY_APPROVAL_REQUIRED", "Record approval for the exact proposed host rule scope")
    result = plan(config, provider, groups)
    target = Path(result["target"])
    if target.is_symlink():
        raise HandrailError("ACCESS_PATH_INVALID", "Permission file must not be a symlink")
    if provider == "cursor":
        before = read_json(target, {})
        permissions = before.setdefault("permissions", {})
        if not isinstance(permissions, dict) or not isinstance(permissions.get("allow", []), list):
            raise HandrailError("ACCESS_CONFIG_INVALID", "Existing Cursor permissions have an unsupported format")
        result["added_rules"] = [r for r in result["rules"] if r not in permissions.get("allow", [])]
        permissions["allow"] = list(dict.fromkeys(permissions.get("allow", []) + result["rules"]))
        # Retain deny rules and every unrelated setting. A deny may still win.
        _replace(target, json.dumps(before, ensure_ascii=False, indent=2) + "\n")
    else:
        marker = "# Handrail managed rules for " + result["repo"] + "\n"
        prior = target.read_text() if target.exists() else ""
        if prior and not prior.startswith(marker):
            raise HandrailError("ACCESS_CONFIG_OWNERSHIP", "Refuse to overwrite an unrecognized permission file")
        additions = [line for line in result["rules"] if line not in prior.splitlines()]
        result["added_rules"] = additions
        content = (prior.rstrip() + "\n" if prior else marker) + "\n".join(additions) + "\n"
        _replace(target, content)
    result.update(written=True, approval=approval, at=now(), next="Start a new provider CLI session; observe actual approval behavior")
    return result


def update_policy(store, config, provider, groups, approval, revoke=False):
    if not isinstance(approval, str) or not approval.strip():
        raise HandrailError("HOST_POLICY_APPROVAL_REQUIRED", "Record the user's host policy change request")
    from .onboarding import setup_store
    key = provider + ":" + digest(config["repo"])
    with setup_store().exclusive("host-access-policy"):
        if not revoke:
            result = apply(config, provider, groups, approval)
            with store.transaction() as tx:
                previous = tx.get("access_policy", key) or {}
                tx.put("access_policy", key, {"id": key, "provider": provider, "target": result["target"],
                       "owned_rules": list(dict.fromkeys(previous.get("owned_rules", []) + result["added_rules"])),
                       "scope_version": 1, "updated_at": now()})
                tx.event("access", "access.policy_applied", result)
            return result
        result = plan(config, provider, groups)
        saved = store.read("access_policy", key)
        if not saved or saved["target"] != result["target"]:
            raise HandrailError("ACCESS_OWNERSHIP_UNKNOWN", "No owned host rules are recorded for this repository")
        removed = [r for r in result["rules"] if r in saved["owned_rules"]]
        target = Path(result["target"])
        if target.is_symlink():
            raise HandrailError("ACCESS_PATH_INVALID", "Permission file must not be a symlink")
        if target.exists():
            if provider == "cursor":
                data = read_json(target, {})
                allow = data.get("permissions", {}).get("allow", [])
                if not isinstance(allow, list):
                    raise HandrailError("ACCESS_CONFIG_INVALID", "Unexpected Cursor allow rules")
                data.setdefault("permissions", {})["allow"] = [r for r in allow if r not in removed]
                _replace(target, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
            else:
                _replace(target, "\n".join(r for r in target.read_text().splitlines() if r not in removed) + "\n")
        with store.transaction() as tx:
            saved["owned_rules"] = [r for r in saved["owned_rules"] if r not in removed]
            tx.put("access_policy", key, saved)
            tx.event("access", "access.policy_revoked", {"provider": provider, "groups": groups, "removed_rules": removed,
                                                       "reason": approval})
        return {"revoked_rules": removed, "provider": provider, "next": "New provider sessions observe the revised policy"}


def record_metric(store, kind, evidence, category=None, duration_ms=None):
    if kind not in METRICS or not evidence.strip() or category is not None and category not in CATEGORIES:
        raise HandrailError("METRIC_INVALID", "Record an observed host approval, user choice or wait")
    if duration_ms is not None and duration_ms < 0:
        raise HandrailError("METRIC_INVALID", "Duration must be nonnegative")
    value = {"evidence": evidence, "source": "explicit observation", "category": category, "duration_ms": duration_ms}
    with store.transaction() as tx:
        identity = tx.event("usability", "usability." + kind, value)
    return {"event_id": identity, "kind": kind, **value}


def metrics(store):
    events = [r for r in store.history("usability") if r["kind"].startswith("usability.")]
    return {"counts": {k: sum(r["kind"] == "usability." + k for r in events) for k in METRICS},
            "categories": {k: sum(r["data"].get("category") == k for r in events) for k in CATEGORIES},
            "observed_wait_ms": sum(r["data"].get("duration_ms") or 0 for r in events if r["kind"] == "usability.wait"),
            "coverage": "Only recorded observations; not a claim that unrecorded approvals never occurred", "observations": events}
