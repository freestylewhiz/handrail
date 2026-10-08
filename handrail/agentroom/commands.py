"""Explicit dependency preparation and checks, with recorded exact argv scope."""
import subprocess
import os
import signal
from pathlib import Path
from handrail.authorization.service import Authorization
from handrail.shared.identity import now, new_id, digest
from handrail.shared.errors import HandrailError


def run_command(ctx, plan_id, argv, cwd, purpose, operation_id=None, timeout=300):
    with ctx["store"].exclusive("agentroom-mutation"):
        return _run_command(ctx, plan_id, argv, cwd, purpose, operation_id, timeout)


def _run_command(ctx, plan_id, argv, cwd, purpose, operation_id, timeout):
    if (not isinstance(argv, list) or not argv or any(not isinstance(v, str) or not v for v in argv)
            or purpose not in ("prepare", "verify")):
        raise HandrailError("COMMAND_INVALID", "Use a nonempty argv list and prepare/verify purpose")
    if not isinstance(timeout, int) or timeout <= 0:
        raise HandrailError("COMMAND_INVALID", "Timeout must be positive")
    path = Path(cwd).expanduser().resolve()
    config, store = ctx["config"], ctx["store"]
    plan = store.read("plan", plan_id)
    if not plan or plan["state"] not in ("todo", "doing") or not plan.get("approval"):
        raise HandrailError("PLAN_NOT_ACTIVE", "Run commands only for an approved active plan")
    from .service import AgentRoomService, resource_scope
    from handrail.interfaces.agentroom.herdr import HerdrClient
    from handrail.workflow.service import WorkflowService
    room = AgentRoomService(store, config, ctx["git"], HerdrClient(config["endpoint"]), WorkflowService(store))
    scope = resource_scope(config, room.cycle_scope(plan_id))
    allowed = {Path(scope["repo"])} | {Path(a["path"]) for a in store.list("attempt")
               if a["plan_id"] == plan_id and a["cycle"] == plan["cycle"] and not a.get("worktree_removed")}
    if not any(path == root or root in path.parents for root in allowed):
        raise HandrailError("COMMAND_LOCATION", "Command directory must belong to this plan's pinned checkouts")
    resources = dict(scope, argv=argv, cwd=str(path), purpose=purpose)
    grant = Authorization(store).require(plan_id, "command.run", resources)
    identity = operation_id or new_id("command-")
    request = dict(resources, plan_id=plan_id, cycle=plan["cycle"])
    from handrail.interfaces.git.repository import GitRepository
    git = GitRepository(path)
    if purpose == "verify":
        git.require_clean()
    before = git.revision()
    with store.transaction() as tx:
        pending = [item for item in tx.list("operation") if item["action"] == "command.run" and
                   item["status"] in ("sending", "unknown") and item["request"] == request
                   and item["id"] != identity]
        if pending:
            raise HandrailError("COMMAND_UNKNOWN", "Reconcile the previous command before repeating the same argv",
                                details={"operation_id": pending[0]["id"]}, uncertain=True)
        operation = tx.intent(identity, "command.run", request)
        if operation["status"] == "complete":
            return operation["result"]
        if operation["status"] != "prepared":
            raise HandrailError("COMMAND_UNKNOWN", "Inspect the interrupted command before rerunning", uncertain=True)
        operation["status"] = "sending"
        tx.put("operation", identity, operation)
    # Spool output directly to private files; avoid unbounded memory use and terminal flooding.
    logs = store.path.parent / "commands"
    logs.mkdir(mode=0o700, exist_ok=True)
    output_path = logs / (digest(identity) + ".log")
    try:
        with output_path.open("w", encoding="utf-8") as output:
            output_path.chmod(0o600)
            process = subprocess.Popen(argv, cwd=str(path), stdout=output, stderr=subprocess.STDOUT,
                                       text=True, shell=False, start_new_session=True)
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                raise
        result = {"id": identity, "argv": argv, "cwd": str(path), "purpose": purpose,
                  "exit_code": process.returncode, "log": str(output_path), "revision_before": before,
                  "revision_after": git.revision(), "clean_after": git.clean(), "grant_id": grant, "finished_at": now()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        with store.transaction() as tx:
            operation.update(status="unknown", error={"type": type(exc).__name__})
            tx.put("operation", identity, operation)
            tx.event(plan_id, "command.unknown", {"operation_id": identity, "log": str(output_path)})
        raise HandrailError("COMMAND_UNKNOWN", "Command did not finish normally; inspect its private log",
                            details={"operation_id": identity, "log": str(output_path)}, uncertain=True) from None
    with store.transaction() as tx:
        operation.update(status="complete", result=result)
        tx.put("operation", identity, operation)
        tx.event(plan_id, "command.finished", result)
    return result


def resolve_command(ctx, operation_id, evidence):
    """Explicitly attest an interrupted process was inspected and may be retried.

    This never manufactures a successful check or turns an unknown run into
    evidence. A subsequent command gets a new operation ID and fresh output.
    """
    store = ctx["store"]
    if not isinstance(evidence, str) or not evidence.strip():
        raise HandrailError("EVIDENCE_REQUIRED", "Explain how process termination and side effects were inspected")
    with store.exclusive("agentroom-mutation"):
        operation = store.read("operation", operation_id)
        if not operation or operation["action"] != "command.run" or operation["status"] not in ("sending", "unknown"):
            raise HandrailError("COMMAND_RECOVERY_INVALID", "Only an interrupted command may be resolved")
        request = operation["request"]
        scope = {key: value for key, value in request.items() if key not in ("plan_id", "cycle")}
        Authorization(store).require(request["plan_id"], "command.run", scope, cycle=request["cycle"])
        with store.transaction() as tx:
            operation.update(status="reconciled", resolution={"evidence": evidence, "resolved_at": now(), "verified": False})
            tx.put("operation", operation_id, operation)
            tx.event(request["plan_id"], "command.reconciled", {"operation_id": operation_id, "evidence": evidence})
    return operation
