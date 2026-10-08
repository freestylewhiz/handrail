"""One durable execution path for Herdr-managed workers.

Identity checks bracket mutations, but Herdr currently has no compare-and-send
primitive. A possible occupant race remains visible in every message receipt.
"""
import copy
import json
from pathlib import Path
from functools import wraps
from handrail.authorization.service import Authorization
from handrail.shared.errors import HandrailError
from handrail.shared.identity import new_id, now, digest
from .identity import record, agent_identity, assert_agent, find_value, pane_ids
from .process import process_identity, reconcile_identity


def resource_scope(config, owner=None, **extra):
    """Use configuration only for a new scope; existing resources must be pinned."""
    source = config if owner is None else owner.get("resource_scope")
    if not isinstance(source, dict) or any(key not in source for key in ("repo", "endpoint", "worktree_root")):
        raise HandrailError("RESOURCE_SCOPE_MISSING", "Existing execution needs its original repo, endpoint and worktree root")
    result = {key: copy.deepcopy(source[key]) for key in ("repo", "endpoint", "worktree_root")}
    if not all(isinstance(result[key], str) and Path(result[key]).is_absolute() for key in ("repo", "worktree_root")):
        raise HandrailError("RESOURCE_SCOPE_INVALID", "Pinned repository and worktree root must be absolute")
    endpoint = result["endpoint"]
    if not isinstance(endpoint, dict) or set(endpoint) not in ({"session"}, {"socket"}):
        raise HandrailError("RESOURCE_SCOPE_INVALID", "Use one explicit pinned Herdr endpoint")
    if any(key in result for key in extra):
        raise HandrailError("RESOURCE_SCOPE_INVALID", "Action scope cannot replace pinned resources")
    return dict(result, **extra)


def serialized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self.store.exclusive("agentroom-mutation"):
            return method(self, *args, **kwargs)
    return call


class AgentRoomService:
    def __init__(self, store, config, git, client, workflow):
        self.store, self.config, self.git = store, config, git
        self.client, self.workflow = client, workflow
        self._client_endpoint = copy.deepcopy(config["endpoint"])
        self.authorization = Authorization(store)

    def _require(self, kind, identity):
        value = self.store.read(kind, identity)
        if value is None:
            raise HandrailError("NOT_FOUND", f"Unknown {kind}: {identity}")
        return value

    def _plan(self, plan_id):
        return self._require("plan", plan_id)

    def _scope(self, owner=None, **extra):
        return resource_scope(self.config, owner, **extra)

    @serialized
    def cycle_scope(self, plan_id, cycle=None):
        plan = self._plan(plan_id)
        cycle = plan["cycle"] if cycle is None else cycle
        identity = f"{plan_id}:{cycle}"
        existing = self.store.read("cycle_scope", identity)
        if existing:
            self._scope(existing)
            return existing
        # Never infer an older execution's resources from today's settings.
        room = self.store.read("room", identity)
        if room:
            scope = self._scope(room)
        elif cycle != plan["cycle"] or self.store.read("operation", "room-create:" + identity):
            raise HandrailError("RESOURCE_SCOPE_MISSING", "Recover the original cycle resource scope explicitly")
        else:
            scope = self._scope()
        value = {"id": identity, "plan_id": plan_id, "cycle": cycle, "resource_scope": scope}
        with self.store.transaction() as tx:
            tx.put("cycle_scope", identity, value)
            tx.event(plan_id, "cycle.resources_pinned", value)
        return value

    def _authorize(self, owner, action, **extra):
        return self.authorization.require(owner["plan_id"], action, self._scope(owner, **extra), cycle=owner["cycle"])

    def _client(self, owner):
        endpoint = self._scope(owner)["endpoint"]
        if endpoint == self._client_endpoint:
            return self.client
        from handrail.interfaces.agentroom.herdr import HerdrClient
        # Select the recorded endpoint directly. Never retry on another connection.
        return HerdrClient(endpoint, executable=getattr(self.client, "executable", "herdr"),
                           timeout=getattr(self.client, "timeout", 30))

    def _git(self, owner):
        repo = self._scope(owner)["repo"]
        if Path(repo).resolve() == self.git.root:
            return self.git
        from handrail.interfaces.git.repository import GitRepository
        return GitRepository(repo)

    def _active_work(self, attempt, *, integrated=False):
        current = self._require("attempt", attempt["id"])
        work = self._require("work", attempt["work_id"])
        plan = self._plan(attempt["plan_id"])
        if (current["state"] != "active" or current.get("identity") != attempt.get("identity") or
                work.get("attempt_id") != attempt["id"] or work["cycle"] != attempt["cycle"]):
            raise HandrailError("ATTEMPT_STALE", "Only the current active attempt can change this work")
        if (plan["state"] != "doing" or plan["cycle"] != attempt["cycle"] or
                not plan.get("approval") or plan["approval"]["cycle"] != attempt["cycle"]):
            raise HandrailError("PLAN_NOT_ACTIVE", "This execution is retained for review or cleanup")
        if work["state"] == "done" or (work.get("integration") and not integrated):
            raise HandrailError("WORK_IMMUTABLE", "Create follow-up work after integration")
        if not integrated:
            pending = [op["id"] for op in self.store.list("operation")
                       if op["action"] == "work.integrate" and op["request"].get("entity") == work["id"] and
                       op["status"] in ("sending", "unknown", "complete", "rejected")]
            if pending:
                raise HandrailError("INTEGRATION_PENDING", "Reconcile the integration before changing its candidate or review",
                                    details={"operation_ids": pending})
        return work

    @staticmethod
    def _workspace_panes(payload, workspace_id, client=None, candidates=()):
        workspace = record(payload, "workspace")
        if workspace.get("workspace_id") != workspace_id:
            raise HandrailError("ROOM_IDENTITY", "Workspace response does not match the pinned target")
        identities = pane_ids(payload)
        count = workspace.get("pane_count")
        # workspace.get returns WorkspaceInfo (count, not a pane list) in the
        # installed schema. Prove coverage using explicit known pane IDs and
        # their workspace membership; an extra unknown pane makes counts differ.
        if not identities and isinstance(count, int) and count > 0 and client is not None:
            for pane in sorted(set(candidates)):
                try:
                    row = record(client.pane_get(pane), "pane")
                except HandrailError as exc:
                    absent = (exc.code == "HERDR_FAILED" and not exc.uncertain and
                              exc.details.get("herdr_code") == "pane_not_found" and
                              exc.details.get("command") == "get" and exc.details.get("parsed") is True)
                    if absent:
                        continue
                    raise
                if row.get("workspace_id") == workspace_id and row.get("pane_id") == pane:
                    identities.add(pane)
        if not isinstance(count, int) or isinstance(count, bool) or count != len(identities):
            raise HandrailError("ROOM_SNAPSHOT_INCOMPLETE", "Require a complete workspace pane snapshot before ownership decisions")
        return identities

    @staticmethod
    def _pane_owner(client, pane_id, workspace_id):
        row = record(client.pane_get(pane_id), "pane")
        identity = agent_identity(row)
        if identity.get("provider"):
            live = record(client.agent_get(pane_id), "agent")
            observed = agent_identity(live)
            if any(observed.get(k) != identity.get(k) for k in ("pane_id", "workspace_id", "terminal_id", "provider")):
                raise HandrailError("ROOM_OCCUPANT_CHANGED", "Pane and agent snapshots refer to different occupants")
            identity, row = observed, live
        if identity["pane_id"] != pane_id or identity["workspace_id"] != workspace_id:
            raise HandrailError("ROOM_IDENTITY", "Pane response belongs to a different target")
        return identity, row

    @staticmethod
    def _created_owners(payload):
        owners = {}
        if isinstance(payload, dict):
            if all(payload.get(key) for key in ("pane_id", "workspace_id", "terminal_id")):
                owners[payload["pane_id"]] = agent_identity(payload)
            for value in payload.values():
                owners.update(AgentRoomService._created_owners(value))
        elif isinstance(payload, list):
            for value in payload:
                owners.update(AgentRoomService._created_owners(value))
        return owners

    def _pin_pane(self, room, identity, origin):
        with self.store.transaction() as tx:
            current = tx.require("room", room["id"])
            if current["state"] != "open":
                raise HandrailError("ROOM_CLOSED", "Cannot attach a worker to a closed room")
            current.setdefault("owned_panes", {})[identity["pane_id"]] = {
                "identity": copy.deepcopy(identity), "origin": origin, "pinned_at": now()}
            tx.put("room", room["id"], current)

    def _accepted_cycle(self, room, allow_superseded=False):
        plan = self._plan(room["plan_id"])
        cycle = plan if plan["cycle"] == room["cycle"] else next(
            (value for value in plan.get("cycles", []) if value["cycle"] == room["cycle"]), None)
        acceptance = (cycle or {}).get("acceptance") or {}
        submission = (cycle or {}).get("submission") or {}
        if (allow_superseded and cycle and room["cycle"] < plan["cycle"] and
                plan["state"] == "done" and plan.get("acceptance") and
                plan["acceptance"].get("submission_id") == (plan.get("submission") or {}).get("id")):
            return cycle
        if (not cycle or cycle["state"] != "done" or not acceptance or
                acceptance.get("cycle") != room["cycle"] or acceptance.get("revision") != cycle["revision"] or
                not submission.get("id") or acceptance.get("submission_id") != submission["id"]):
            raise HandrailError("REVIEW_RETENTION", "Retain the room until its own cycle has a recorded user acceptance")
        return cycle

    def _external(self, operation_id, action, request, callback):
        with self.store.transaction() as tx:
            operation = tx.intent(operation_id, action, request)
            if operation["status"] == "complete":
                return operation["result"]
            if operation["status"] != "prepared":
                raise HandrailError("OPERATION_UNCERTAIN", "Inspect and reconcile this operation before another mutation",
                                    details={"operation_id": operation_id, "status": operation["status"]}, uncertain=True)
            operation["status"] = "sending"
            tx.put("operation", operation_id, operation)
        try:
            result = callback()
        except Exception as exc:
            uncertain = not isinstance(exc, HandrailError) or exc.uncertain
            if isinstance(exc, HandrailError):
                exc.details = dict(exc.details, operation_id=operation_id)
            with self.store.transaction() as tx:
                operation = tx.require("operation", operation_id)
                operation.update(status="unknown" if uncertain else "rejected",
                                 error=exc.as_dict() if isinstance(exc, HandrailError) else {"type": type(exc).__name__})
                tx.put("operation", operation_id, operation)
                tx.event(request.get("entity", operation_id), action + ".failed", {"operation_id": operation_id,
                         "uncertain": uncertain, "error": operation["error"]})
            raise
        with self.store.transaction() as tx:
            operation = tx.require("operation", operation_id)
            operation.update(status="complete", result=result, completed_at=now())
            tx.put("operation", operation_id, operation)
        return result

    @serialized
    def create(self, plan_id):
        plan = self._plan(plan_id)
        room_id = f"{plan_id}:{plan['cycle']}"
        existing = self.store.read("room", room_id)
        if existing:
            self._scope(existing)
            return existing
        if plan["state"] not in ("todo", "doing") or not plan.get("approval") or plan["approval"]["cycle"] != plan["cycle"]:
            raise HandrailError("PLAN_NOT_ACTIVE", "Approve the plan before opening a room")
        scope = self.cycle_scope(plan_id)
        resources = self._scope(scope)
        grant = self._authorize(scope, "room.create")
        client = self._client(scope)
        origin = "room-create:" + room_id
        label = "Handrail " + room_id + " " + digest(origin)[:12]
        request = {"entity": plan_id, "cycle": plan["cycle"], "resource_scope": resources, "label": label}
        payload = self._external(origin, "room.create", request,
                                 lambda: client.workspace_create(resources["repo"], label))
        workspace_id = find_value(payload, "workspace_id")
        if not workspace_id:
            raise HandrailError("ROOM_RESPONSE", "Workspace creation did not return an identity", uncertain=True)
        initial = pane_ids(payload)
        if not initial:
            raise HandrailError("ROOM_RESPONSE", "Creation returned no pane identities; adopt with explicit ownership scope",
                                details={"origin_operation_id": origin, "workspace_id": workspace_id}, uncertain=True)
        owned = {}
        created = self._created_owners(payload)
        for pane in sorted(initial):
            identity, row = self._pane_owner(client, pane, workspace_id)
            expected = created.get(pane)
            if (not expected or identity["provider"] or identity["provider_session"] or
                    any(expected.get(key) != identity.get(key) for key in ("workspace_id", "pane_id", "terminal_id"))):
                raise HandrailError("ROOM_OCCUPANT_CHANGED", "Creation no longer proves the initial terminal occupant; recover explicitly")
            owned[pane] = {"identity": identity, "origin": origin, "pinned_at": now()}
        value = {"id": room_id, "plan_id": plan_id, "cycle": plan["cycle"], "workspace_id": workspace_id,
                 "endpoint": resources["endpoint"], "resource_scope": resources,
                 "origin_operation_id": origin, "owned_panes": owned, "initial_panes": sorted(initial),
                 "state": "open", "created_at": now(), "grant_id": grant}
        with self.store.transaction() as tx:
            tx.put("room", room_id, value)
            tx.event(plan_id, "room.opened", value)
        return value

    @serialized
    def adopt_room(self, plan_id, workspace_id, evidence, origin_operation_id=None, owned_panes=None):
        """Adopt a lost creation result with explicit origin and selected pane IDs.

        CLI callers may pass evidence as JSON containing text,
        origin_operation_id and owned_panes. Discovery alone never grants ownership.
        """
        plan = self._plan(plan_id)
        if isinstance(evidence, str) and evidence.lstrip().startswith("{"):
            try:
                evidence = json.loads(evidence)
            except ValueError:
                raise HandrailError("RECOVERY_INVALID", "Adoption evidence must be valid JSON") from None
        if isinstance(evidence, dict):
            origin_operation_id = origin_operation_id or evidence.get("origin_operation_id")
            owned_panes = evidence.get("owned_panes") if owned_panes is None else owned_panes
            evidence = evidence.get("text")
        if not isinstance(evidence, str) or not evidence.strip():
            raise HandrailError("EVIDENCE_REQUIRED", "Record how the room was identified")
        if (not isinstance(owned_panes, list) or any(not isinstance(pane, str) or not pane.strip() for pane in owned_panes)
                or len(set(owned_panes)) != len(owned_panes)):
            raise HandrailError("RECOVERY_SCOPE_REQUIRED", "Explicitly select owned_panes, including [] when claiming none")
        room_id = f"{plan_id}:{plan['cycle']}"
        if origin_operation_id != "room-create:" + room_id:
            raise HandrailError("RECOVERY_ORIGIN", "Select the original room creation operation for this cycle")
        origin = self._require("operation", origin_operation_id)
        scope = self.cycle_scope(plan_id)
        resources = self._scope(scope)
        if (origin["action"] != "room.create" or origin["status"] not in ("sending", "unknown", "complete") or
                origin["request"].get("entity") != plan_id or origin["request"].get("cycle") != plan["cycle"] or
                origin["request"].get("resource_scope") != resources or not origin["request"].get("label")):
            raise HandrailError("RECOVERY_ORIGIN", "Creation intent does not establish this cycle's original resource scope")
        if plan["state"] not in ("todo", "doing") or not plan.get("approval"):
            raise HandrailError("PLAN_NOT_ACTIVE", "Adopt only the approved active cycle's creation")
        grant = self._authorize(scope, "worker.recover", workspace_id=workspace_id,
                                origin_operation_id=origin_operation_id, owned_panes=sorted(owned_panes))
        if self.store.read("room", room_id):
            raise HandrailError("ROOM_EXISTS", "A room is already bound to this cycle")
        client = self._client(scope)
        payload = client.workspace_get(workspace_id)
        workspace = record(payload, "workspace")
        if workspace.get("workspace_id") != workspace_id:
            raise HandrailError("ROOM_IDENTITY", "Workspace identity does not match the explicit adoption target")
        discovered = pane_ids(payload)
        if workspace.get("label") != origin["request"]["label"]:
            raise HandrailError("RECOVERY_ORIGIN", "Workspace label does not match the original creation intent")
        recorded_workspace = find_value(origin.get("result"), "workspace_id")
        if recorded_workspace and recorded_workspace != workspace_id:
            raise HandrailError("RECOVERY_ORIGIN", "Creation already identifies a different workspace")
        if discovered and not set(owned_panes) <= discovered:
            raise HandrailError("RECOVERY_SCOPE_INVALID", "Selected panes must belong to the recovered workspace")
        owned = {}
        for pane in sorted(owned_panes):
            identity, row = self._pane_owner(client, pane, workspace_id)
            owned[pane] = {"identity": identity, "origin": origin_operation_id, "pinned_at": now()}
        value = {"id": room_id, "plan_id": plan_id, "cycle": plan["cycle"], "workspace_id": workspace_id,
                 "endpoint": resources["endpoint"], "resource_scope": resources,
                 "origin_operation_id": origin_operation_id, "owned_panes": owned,
                 "initial_panes": sorted(owned_panes), "discovered_panes": sorted(discovered),
                 "observed_pane_count": workspace.get("pane_count"),
                 "state": "open", "created_at": now(), "grant_id": grant, "recovery_evidence": evidence}
        with self.store.transaction() as tx:
            tx.put("room", room_id, value)
            origin.update(status="complete", result=payload, completed_at=now(),
                          reconciliation={"workspace_id": workspace_id, "evidence": evidence,
                                          "owned_panes": sorted(owned_panes), "grant_id": grant})
            tx.put("operation", origin_operation_id, origin)
            tx.event(plan_id, "room.adopted", value)
        return value

    @serialized
    def start(self, work_id, provider, model, instructions, effort=None, operation_id=None, request_hash=None):
        if provider not in ("codex", "cursor") or not model.strip() or not instructions.strip():
            raise HandrailError("WORKER_SELECTION", "Choose the provider, model and instructions explicitly")
        operation_id = operation_id or new_id("attempt-")
        work = self._require("work", work_id)
        plan = self._plan(work["plan_id"])
        if (plan["state"] not in ("todo", "doing") or not plan.get("approval") or
                work["cycle"] != plan["cycle"] or work["state"] == "done" or work.get("integration")):
            raise HandrailError("WORK_NOT_ACTIVE", "Worker must belong to the active plan cycle")
        scope = self.cycle_scope(plan["id"])
        grant = self._authorize(scope, "worker.start", provider=provider, model=model)
        room = self.create(plan["id"])
        if room["state"] != "open":
            raise HandrailError("ROOM_CLOSED", "Reopen the plan for a new room")
        resources = self._scope(room)
        if resources != self._scope(scope):
            raise HandrailError("RESOURCE_SCOPE_INVALID", "Room differs from its original cycle resources")
        client, git = self._client(room), self._git(room)
        old = self.store.read("attempt", operation_id)
        if old:
            if (old["work_id"], old["provider"], old["model"], old.get("effort"), old["initial_instructions_hash"]) != (
                    work_id, provider, model, effort, digest(instructions)):
                raise HandrailError("OPERATION_CONFLICT", "Attempt ID belongs to different work or instructions")
            if self._scope(old) != resources or old["state"] in ("closed", "replaced"):
                raise HandrailError("ATTEMPT_STALE", "Cannot restart an earlier execution or change its resources")
            if old.get("identity"):
                self._live(old)
                self._pin_pane(room, old["identity"], operation_id + ":start")
                self.workflow.start_work(work_id, operation_id)
                initial = old.get("bootstrap", instructions)
                return {"attempt": old, "message": self._prompt(old, initial, operation_id + ":initial", grant),
                        "next": "worker continue ATTEMPT after worker readiness; coordinator tick monitors completion"}
            attempt = old
        else:
            if any(a["work_id"] == work_id and a["state"] not in ("replaced", "closed") for a in self.store.list("attempt")):
                raise HandrailError("ATTEMPT_EXISTS", "Observe or recover the existing attempt")
            # Path segments are generated hashes, never user-provided task titles/IDs.
            path = Path(resources["worktree_root"]) / digest(plan["id"])[:12] / digest(operation_id)[:16]
            attempt = {"id": operation_id, "work_id": work_id, "plan_id": plan["id"], "cycle": plan["cycle"],
                       "room_id": room["id"], "path": str(path), "branch": "handrail/" + digest(operation_id)[:24],
                       "base_revision": git.revision(), "provider": provider, "model": model, "effort": effort,
                       "initial_instructions_hash": digest(instructions), "endpoint": room["endpoint"],
                       "request_instructions_hash": request_hash,
                       "resource_scope": resources, "state": "preparing", "activity": "unknown",
                       "created_at": now(), "grant_id": grant}
            with self.store.transaction() as tx:
                # Atomic reservation prevents two starts for the same work item.
                if any(a["work_id"] == work_id and a["state"] not in ("replaced", "closed") for a in tx.list("attempt")):
                    raise HandrailError("ATTEMPT_EXISTS", "Another attempt already owns this work")
                tx.put("attempt", operation_id, attempt)
                tx.event(work_id, "worker.prepared", {"attempt_id": operation_id, "path": str(path)})
        git.create_worktree(attempt["path"], attempt["branch"], attempt["base_revision"])
        if not attempt.get("worker_contract"):
            from .handoff import prepare
            attempt.update(prepare(attempt, git, instructions))
            with self.store.transaction() as tx:
                tx.put("attempt", operation_id, attempt)
        tab = self._external(operation_id + ":tab", "worker.tab",
                             {"entity": work_id, "room": room["id"], "path": attempt["path"], "resource_scope": resources},
                             lambda: client.tab_create(room["workspace_id"], attempt["path"], work_id))
        pane = find_value(tab, "pane_id")
        if not pane:
            raise HandrailError("ROOM_RESPONSE", "Worker tab lacks pane identity", uncertain=True)
        attempt["pane_id"] = pane
        attempt["name"] = "hr-" + digest(operation_id)[:20]
        with self.store.transaction() as tx:
            tx.put("attempt", operation_id, attempt)
        if pane not in self._require("room", room["id"]).get("owned_panes", {}):
            identity, row = self._pane_owner(client, pane, room["workspace_id"])
            expected = self._created_owners(tab).get(pane)
            if (not expected or identity["provider"] or identity["provider_session"] or
                    expected["terminal_id"] != identity["terminal_id"]):
                raise HandrailError("ROOM_OCCUPANT_CHANGED", "Worker tab acquired an unexpected occupant")
            self._pin_pane(room, identity, operation_id + ":tab")
        self._external(operation_id + ":start", "worker.start",
                       {"entity": work_id, "pane_id": pane, "provider": provider, "model": model,
                        "effort": effort, "resource_scope": resources, "launch": attempt["launch"]},
                       lambda: client.agent_start(attempt["name"], provider, pane, model, effort=effort,
                                                  writable_paths=attempt["launch"]["requested_paths"]))
        live = client.agent_get(pane)
        attempt["identity"] = agent_identity(live)
        attempt["identity"]["process_identity"] = process_identity(client, pane)
        pinned = self._require("room", room["id"])["owned_panes"][pane]["identity"]
        if (attempt["identity"]["pane_id"] != pane or attempt["identity"]["workspace_id"] != room["workspace_id"] or
                attempt["identity"]["provider"] != provider or attempt["identity"]["terminal_id"] != pinned["terminal_id"] or
                attempt["identity"].get("name") != attempt["name"]):
            raise HandrailError("AGENT_IDENTITY", "Started worker does not match the requested pane, room and provider")
        assert_agent(attempt["identity"], live, attempt["path"])
        attempt["state"] = "active"
        attempt["activity"] = record(live, "agent").get("agent_status", "unknown")
        with self.store.transaction() as tx:
            tx.put("attempt", operation_id, attempt)
            tx.event(work_id, "worker.started", {"attempt_id": operation_id, "identity": attempt["identity"]})
            monitor = tx.get("monitor", plan["id"]) or {"id": plan["id"], "owner": "current coordinator",
                "last_check": None, "next_check": now(), "interval_seconds": 20, "targets": [],
                "running": False, "host_wakeup": "unavailable", "mode": "foreground-tick"}
            monitor["targets"] = list(dict.fromkeys(monitor.get("targets", []) + [operation_id]))
            tx.put("monitor", plan["id"], monitor)
        self._pin_pane(room, attempt["identity"], operation_id + ":start")
        self.workflow.start_work(work_id, operation_id)
        # Starting a worker includes its initial, explicitly supplied task instruction.
        return {"attempt": attempt, "message": self._prompt(attempt, attempt["bootstrap"], operation_id + ":initial", grant),
                "next": "worker continue ATTEMPT after worker readiness; coordinator tick monitors completion"}

    def _live(self, attempt):
        current = self._require("attempt", attempt["id"])
        if current["state"] != "active" or not attempt.get("identity") or current.get("identity") != attempt["identity"]:
            raise HandrailError("ATTEMPT_INACTIVE", "This attempt cannot receive commands")
        self._git(attempt).verify_worktree(attempt["path"], attempt["branch"])
        client = self._client(attempt)
        live = client.agent_get(attempt["identity"]["pane_id"])
        result = assert_agent(attempt["identity"], live, attempt["path"])
        enriched = reconcile_identity(attempt["identity"], agent_identity(live),
                                      process_identity(client, attempt["identity"]["pane_id"]))
        if enriched != attempt["identity"]:
            with self.store.transaction() as tx:
                current = tx.require("attempt", attempt["id"])
                if current.get("identity") != attempt["identity"]:
                    raise HandrailError("ATTEMPT_STALE", "Identity changed during observation")
                current["identity"] = enriched
                tx.put("attempt", current["id"], current)
                owned_room = tx.require("room", attempt["room_id"])
                pane = enriched["pane_id"]
                ownership = owned_room.get("owned_panes", {}).get(pane)
                if owned_room["state"] != "open" or not ownership:
                    raise HandrailError("ROOM_OWNERSHIP_UNKNOWN", "Inspect the recorded room ownership before enriching this worker")
                owned_room["owned_panes"][pane] = dict(ownership, identity=copy.deepcopy(enriched), pinned_at=now())
                tx.put("room", owned_room["id"], owned_room)
                tx.event(current["work_id"], "worker.identity_enriched", {"attempt_id": current["id"], "identity": enriched})
            attempt["identity"] = enriched
        return result

    def _prompt(self, attempt, text, message_id, grant):
        self._active_work(attempt)
        if not text.strip():
            raise HandrailError("MESSAGE_EMPTY", "Instructions cannot be empty")
        old = self.store.read("message", message_id)
        if old:
            if old["attempt_id"] != attempt["id"] or old["text_hash"] != digest(text):
                raise HandrailError("OPERATION_CONFLICT", "Message ID belongs to a different request")
            return old
        pending = [op for op in self.store.list("operation") if op["action"] == "worker.prompt" and
                   op["request"].get("attempt_id") == attempt["id"] and op["status"] in ("sending", "unknown") and op["id"] != message_id]
        if pending:
            raise HandrailError("DELIVERY_UNKNOWN", "Reconcile the earlier instruction before another prompt",
                                details={"operation_id": pending[0]["id"]}, uncertain=True)
        before = self._live(attempt)
        submitted = self.store.read("operation", message_id)
        if (not submitted or submitted["status"] != "complete") and before.get("agent_status") not in ("idle", "done"):
            raise HandrailError("WORKER_NOT_READY", "Observe the worker's question or activity before sending",
                                details={"agent_status": before.get("agent_status")})
        request = {"entity": attempt["work_id"], "attempt_id": attempt["id"],
                   "text_hash": digest(text), "identity": attempt["identity"], "resource_scope": self._scope(attempt)}
        if submitted:
            original = submitted["request"]
            if any(original.get(k) != request[k] for k in ("entity", "attempt_id", "text_hash", "resource_scope")):
                raise HandrailError("OPERATION_CONFLICT", "Pending message belongs to different instructions or resources")
            # _live already proved execution continuity. Late identity
            # enrichment must not rewrite a durable request's fingerprint.
            request = original
        payload = self._external(message_id, "worker.prompt", request,
                                 lambda: self._client(attempt).agent_prompt(attempt["identity"]["pane_id"], text))
        after = self._live(attempt)
        value = {"id": message_id, "attempt_id": attempt["id"], "text_hash": digest(text),
                 "delivery": "submitted", "activity": after.get("agent_status", "unknown"),
                 "response_observed": False, "occupant_race_possible": True, "receipt": payload,
                 "grant_id": grant, "submitted_at": now()}
        with self.store.transaction() as tx:
            tx.put("message", message_id, value)
            current = tx.require("attempt", attempt["id"])
            if current["state"] != "active" or current.get("identity") != attempt["identity"]:
                raise HandrailError("ATTEMPT_STALE", "Attempt changed while the instruction was submitted", uncertain=True)
            current.update(activity=value["activity"], observed_at=now())
            tx.put("attempt", attempt["id"], current)
            tx.event(attempt["work_id"], "message.submitted", {"message_id": message_id, "attempt_id": attempt["id"]})
        return value

    @serialized
    def prompt(self, attempt_id, text, message_id=None):
        attempt = self._require("attempt", attempt_id)
        self._active_work(attempt)
        grant = self._authorize(attempt, "worker.prompt", provider=attempt["provider"], model=attempt["model"])
        return self._prompt(attempt, text, message_id or new_id("message-"), grant)

    def observe(self, attempt_id, recent=False):
        attempt = self._require("attempt", attempt_id)
        live = self._live(attempt)
        source = "recent-unwrapped" if recent or live.get("agent_status") in ("idle", "done") else "visible"
        text = self._client(attempt).agent_read(attempt["identity"]["pane_id"], source=source, lines=200)
        self._live(attempt)
        return {"attempt_id": attempt_id, "agent_status": live.get("agent_status", "unknown"),
                "identity": attempt["identity"], "observed_at": now(), "source": source, "text": text,
                "screen_hash": digest(text), "business_completion": "not_inferred", "occupant_race_possible": True}

    @serialized
    def collect(self, attempt_id, recent=False):
        result = self.observe(attempt_id, recent)
        result["id"] = new_id("observation-")
        with self.store.transaction() as tx:
            attempt = tx.require("attempt", attempt_id)
            work = tx.require("work", attempt["work_id"])
            applicable = (attempt["state"] == "active" and attempt.get("identity") == result["identity"] and
                          work.get("attempt_id") == attempt_id)
            if applicable:
                attempt.update(activity=result["agent_status"], observed_at=result["observed_at"], observation_id=result["id"])
                tx.put("attempt", attempt_id, attempt)
            result["applied_to_activity"] = applicable
            tx.put("observation", result["id"], result)
            tx.event(attempt["work_id"], "worker.observed", {"attempt_id": attempt_id, "observation_id": result["id"],
                                                           "applied_to_activity": applicable})
        return result

    @serialized
    def resolve_message(self, operation_id, outcome, evidence):
        operation = self._require("operation", operation_id)
        if operation["action"] != "worker.prompt" or outcome not in ("delivered", "not_delivered") or not evidence.strip():
            raise HandrailError("RECOVERY_INVALID", "Resolve a prompt with delivered/not_delivered and observed evidence")
        attempt = self._require("attempt", operation["request"]["attempt_id"])
        self._authorize(attempt, "worker.recover")
        self._live(attempt)
        with self.store.transaction() as tx:
            operation = tx.require("operation", operation_id)
            if operation["status"] not in ("sending", "unknown", "rejected"):
                raise HandrailError("RECOVERY_INVALID", "Only unresolved operations can be reconciled")
            operation.update(status="complete" if outcome == "delivered" else "prepared",
                             result={"reconciled": outcome, "evidence": evidence})
            tx.put("operation", operation_id, operation)
            tx.event(attempt["work_id"], "message.reconciled", {"operation_id": operation_id, "outcome": outcome, "evidence": evidence})
        return operation

    @serialized
    def keys(self, attempt_id, keys, observation_id, reason, operation_id=None):
        attempt = self._require("attempt", attempt_id)
        self._active_work(attempt)
        observation = self._require("observation", observation_id)
        if observation["attempt_id"] != attempt_id or not reason.strip():
            raise HandrailError("INSPECTION_REQUIRED", "Use an observation of this worker and explain the intended action")
        grant = self._authorize(attempt, "worker.keys", provider=attempt["provider"], model=attempt["model"],
                                keys=keys, screen_hash=observation["screen_hash"])
        current = self.observe(attempt_id, observation["source"] == "recent-unwrapped")
        if current["screen_hash"] != observation["screen_hash"]:
            raise HandrailError("SCREEN_CHANGED", "Inspect the changed screen before sending keys")
        result = self._external(operation_id or new_id("keys-"), "worker.keys",
                                {"entity": attempt["work_id"], "identity": attempt["identity"], "keys": keys,
                                 "attempt_id": attempt_id, "resource_scope": self._scope(attempt),
                                 "screen_hash": current["screen_hash"], "grant_id": grant, "reason": reason},
                                lambda: self._client(attempt).agent_keys(attempt["identity"]["pane_id"], keys))
        self._live(attempt)
        return result

    @serialized
    def recover(self, attempt_id, target, evidence):
        old = self._require("attempt", attempt_id)
        self._authorize(old, "worker.recover")
        if old["state"] == "replaced":
            replacement = self._require("attempt", old["replaced_by"])
            if target not in (replacement["identity"].get("pane_id"), replacement["identity"].get("name")):
                raise HandrailError("RECOVERY_CONFLICT", "Attempt was already replaced by a different worker")
            self._live(replacement)
            self._pin_pane(self._require("room", old["room_id"]), replacement["identity"], replacement["id"])
            self.workflow.start_work(old["work_id"], replacement["id"])
            return replacement
        work = self._require("work", old["work_id"])
        if old["state"] == "closed" or (work.get("attempt_id") and work["attempt_id"] != attempt_id):
            raise HandrailError("ATTEMPT_STALE", "Recover only the current or unfinished initial attempt")
        if work["state"] == "done" or work.get("integration"):
            raise HandrailError("WORK_IMMUTABLE", "Create follow-up work after integration")
        if any(op["action"] == "work.integrate" and op["request"].get("entity") == work["id"] and
               op["status"] in ("sending", "unknown", "complete", "rejected") for op in self.store.list("operation")):
            raise HandrailError("INTEGRATION_PENDING", "Reconcile the current integration before replacing its attempt")
        plan = self._plan(old["plan_id"])
        if (plan["state"] not in ("todo", "doing") or plan["cycle"] != old["cycle"] or
                not plan.get("approval") or plan["approval"]["cycle"] != old["cycle"] or
                not isinstance(evidence, str) or not evidence.strip()):
            raise HandrailError("RECOVERY_INVALID", "Recover only active work with explicit identity evidence")
        live = self._client(old).agent_get(target)
        identity = agent_identity(live)
        identity["process_identity"] = process_identity(self._client(old), identity["pane_id"])
        room = self._require("room", old["room_id"])
        if (room["state"] != "open" or self._scope(room) != self._scope(old) or
                identity["workspace_id"] != room["workspace_id"] or identity["provider"] != old["provider"]):
            raise HandrailError("RECOVERY_IDENTITY", "Replacement must match the room and approved provider")
        if any(item["id"] != old["id"] and item["state"] not in ("closed", "replaced") and
               item.get("pane_id") == identity["pane_id"] and self._scope(item) == self._scope(old)
               for item in self.store.list("attempt")):
            raise HandrailError("RECOVERY_IDENTITY", "Replacement pane is already assigned to another active attempt")
        assert_agent(identity, live, old["path"])
        self._git(old).verify_worktree(old["path"], old["branch"])
        replacement = dict(old, id=new_id("attempt-"), identity=identity, pane_id=identity["pane_id"],
                           state="active", activity=record(live, "agent").get("agent_status", "unknown"),
                           replaces=attempt_id, created_at=now(), recovery_evidence=evidence)
        replacement.pop("observation_id", None)
        replacement.pop("observed_at", None)
        replacement.pop("implementation_message_text", None)
        if old.get("protocol") == 2:
            from .handoff import prepare
            # Every real replacement gets a new nonce/channel and readiness gate.
            replacement.update(prepare(replacement, self._git(old), old.get("task_instructions", "")))
        with self.store.transaction() as tx:
            current = tx.require("attempt", attempt_id)
            if current["state"] == "replaced":
                raise HandrailError("ATTEMPT_REPLACED", "Recover the latest attempt instead")
            current.update(state="replaced", replaced_by=replacement["id"])
            tx.put("attempt", attempt_id, current)
            tx.put("attempt", replacement["id"], replacement)
            tx.event(old["work_id"], "worker.recovered", {"previous": attempt_id, "replacement": replacement["id"], "evidence": evidence})
        self._pin_pane(room, identity, replacement["id"])
        self.workflow.start_work(old["work_id"], replacement["id"])
        return dict(replacement, next="Send the recorded bootstrap with worker prompt, then worker continue")

    @serialized
    def integrate(self, attempt_id):
        attempt = self._require("attempt", attempt_id)
        work = self._require("work", attempt["work_id"])
        if work.get("attempt_id") != attempt_id:
            raise HandrailError("ATTEMPT_STALE", "Only the active reviewed attempt may be integrated")
        self._authorize(attempt, "work.integrate")
        if work.get("integration"):
            # Replaying a successful integration never moves canonical HEAD.
            if work["integration"]["attempt_id"] != attempt_id:
                raise HandrailError("ATTEMPT_STALE", "Integration belongs to a different attempt")
            return self.workflow.mark_integrated(work["id"], work["integration"]["revision"])
        self._active_work(attempt, integrated=True)
        git = self._git(attempt)
        # This gate spans calls, not just one merge. An incomplete integration
        # owns canonical HEAD until its criterion evidence and completion commit.
        blockers = [item["id"] for item in self.store.list("work")
                    if item["id"] != work["id"] and item.get("integration") and item["state"] != "done"]
        operations = [item["id"] for item in self.store.list("operation")
                      if item["action"] == "work.integrate" and item["request"].get("entity") != work["id"] and
                      (item["status"] in ("sending", "unknown", "rejected") or
                       (item["status"] == "complete" and not
                        (self.store.read("work", item["request"]["entity"]) or {}).get("integration")))]
        if blockers or operations:
            raise HandrailError("INTEGRATION_PENDING", "Finish the earlier integration's evidence and completion before another merge",
                                details={"work_ids": blockers, "operation_ids": operations})
        worker = git.verify_worktree(attempt["path"], attempt["branch"])
        revision = worker.revision()
        # Workflow review is checked before any mutation; no inferred acceptance from idle.
        review = work.get("review") or {}
        if review.get("verdict") != "accept":
            raise HandrailError("REVIEW_REQUIRED", "Accept the worker changes before integration")
        if review.get("revision") != revision or review.get("attempt_id") != attempt_id:
            raise HandrailError("REVIEW_STALE", "Worker commit changed after review; review this candidate again")
        operation_id = "integrate:" + attempt_id + ":" + revision
        operation = self.store.read("operation", operation_id)
        request = operation["request"] if operation else {"entity": work["id"], "before": git.revision(), "worker": revision,
                                                         "attempt_id": attempt_id, "review_id": review["id"],
                                                         "resource_scope": self._scope(attempt)}
        if (request.get("review_id") != review["id"] or request.get("resource_scope") != self._scope(attempt) or
                request.get("attempt_id") != attempt_id or request.get("worker") != revision):
            raise HandrailError("REVIEW_STALE", "Integration intent belongs to an earlier review or different resources")
        if operation and operation["status"] in ("unknown", "sending", "rejected"):
            git.require_clean()
            contained = git.contains(revision)
            if contained and not git.contains(operation["request"]["before"]):
                raise HandrailError("INTEGRATION_DIVERGED", "Canonical history no longer contains the pre-integration commit")
            if not contained and operation["status"] != "rejected":
                raise HandrailError("INTEGRATION_UNKNOWN", "Resolve the Git integration before retrying", uncertain=True)
            if not contained and git.revision() != operation["request"]["before"]:
                raise HandrailError("INTEGRATION_DIVERGED", "Resolve the changed canonical checkout before retrying")
            observed_revision = git.revision()
            with self.store.transaction() as tx:
                if contained:
                    operation.update(status="complete", result=observed_revision)
                else:
                    # A returned rejection plus unchanged clean HEAD allows this
                    # explicit retry. Unknown outcomes are never reset this way.
                    operation.update(status="prepared")
                tx.event(work["id"], "integration.reconciled", {"operation_id": operation_id,
                         "result": operation["status"], "observed_revision": observed_revision})
                tx.put("operation", operation_id, operation)
        integrated = self._external(operation_id, "work.integrate", request,
                                    lambda: git.integrate(attempt["path"], attempt["branch"], request["before"], revision))
        return self.workflow.mark_integrated(work["id"], integrated)

    @serialized
    def close(self, room_id):
        room = self._require("room", room_id)
        if room["state"] == "closed":
            return room
        self._accepted_cycle(room, allow_superseded=True)
        operation_id = "close:" + room_id
        request = {"entity": room["plan_id"], "room_id": room_id, "cycle": room["cycle"],
                   "workspace_id": room["workspace_id"], "resource_scope": self._scope(room)}
        operation = self.store.read("operation", operation_id)
        if operation and (operation["action"] != "room.close" or
                          any(operation["request"].get(key) != value for key, value in request.items())):
            raise HandrailError("OPERATION_CONFLICT", "Room close intent belongs to different resources")
        if operation and operation["status"] == "complete":
            # No live read or repeated authorization is needed to finalize an
            # already-authorized remote effect. Its room may no longer exist.
            return self._finalize_close(room, operation_id)
        grant = self._authorize(room, "room.close")
        client = self._client(room)
        try:
            snapshot = client.workspace_get(room["workspace_id"])
        except HandrailError as exc:
            # HerdrClient maps a parsed workspace.get rejection to HERDR_FAILED
            # and preserves the exact server error in details.herdr_code. A
            # missing socket, timeout, permission error or generic 404 is NOT
            # evidence that the workspace was closed.
            absent = (exc.code == "HERDR_FAILED" and not exc.uncertain and
                      exc.details.get("herdr_code") == "workspace_not_found" and
                      exc.details.get("command") == "get" and exc.details.get("parsed") is True)
            if not absent:
                raise
            if operation and operation["status"] not in ("prepared", "sending", "unknown", "rejected"):
                raise
            proof = {"workspace_id": room["workspace_id"], "endpoint": self._scope(room)["endpoint"],
                     "observed_at": now(), "error": exc.as_dict(), "grant_id": grant}
            with self.store.transaction() as tx:
                current = tx.intent(operation_id, "room.close", operation["request"] if operation else request)
                if current["status"] not in ("prepared", "sending", "unknown", "rejected"):
                    raise HandrailError("OPERATION_CONFLICT", "Close intent changed during reconciliation")
                current.update(status="complete", result={"reconciled": "workspace_absent", "evidence": proof}, completed_at=now())
                tx.put("operation", operation_id, current)
                tx.event(room["plan_id"], "room.close_reconciled", {"operation_id": operation_id, "evidence": proof})
            return self._finalize_close(room, operation_id)
        if operation and operation["status"] in ("sending", "unknown"):
            raise HandrailError("OPERATION_UNCERTAIN", "Workspace still exists; inspect the unresolved close instead of resending",
                                details={"operation_id": operation_id}, uncertain=True)
        owned = room.get("owned_panes", {})
        current_panes = self._workspace_panes(snapshot, room["workspace_id"], client, owned)
        if current_panes - set(owned):
            raise HandrailError("ROOM_HAS_OTHER_WORK", "Room contains panes without explicit recorded ownership",
                                details={"pane_ids": sorted(current_panes - set(owned))})
        # Include initial/adopted/replaced panes: an old pane ID is never enough
        # to authorize closing whichever terminal or provider now occupies it.
        verified = {}
        for pane in sorted(current_panes):
            pinned = owned[pane]["identity"]
            current, row = self._pane_owner(client, pane, room["workspace_id"])
            current = reconcile_identity(pinned, current, process_identity(client, pane) if current["provider"] else None)
            activity = row.get("agent_status", "unknown")
            if (current["provider"] and activity not in ("idle", "done")) or activity in ("working", "blocked"):
                raise HandrailError("WORKER_BUSY", "Retain active or blocked occupants before closing the room")
            if not current["provider"]:
                process = record(client.pane_process_info(pane), "process_info")
                shell = process.get("shell_pid")
                foreground = process.get("foreground_process_group_id")
                processes = process.get("foreground_processes", [])
                if (process.get("pane_id") != pane or not shell or foreground != shell or
                        any(item.get("pid") != shell for item in processes)):
                    raise HandrailError("ROOM_PROCESS_BUSY", "Retain a shell pane with an active or unproven foreground process",
                                        details={"pane_id": pane})
            verified[pane] = current
        # Re-read the set immediately before the mutation. Herdr has no atomic
        # compare-and-close, so a final external occupant race remains possible.
        if self._workspace_panes(client.workspace_get(room["workspace_id"]), room["workspace_id"], client, owned) != current_panes:
            raise HandrailError("ROOM_OCCUPANT_CHANGED", "Workspace panes changed during closure inspection")
        request.update(grant_id=grant, occupants=verified, occupant_race_possible=True)
        def close_and_observe():
            result = client.workspace_close(room["workspace_id"])
            try:
                client.workspace_get(room["workspace_id"])
            except HandrailError as exc:
                absent = (exc.code == "HERDR_FAILED" and not exc.uncertain and
                          exc.details.get("herdr_code") == "workspace_not_found" and
                          exc.details.get("command") == "get" and exc.details.get("parsed") is True)
                if absent:
                    return {"closed": result, "absence_observed_at": now()}
                raise
            raise HandrailError("ROOM_CLOSE_UNCERTAIN", "Workspace still appears after close; inspect before retrying", uncertain=True)
        self._external(operation_id, "room.close", operation["request"] if operation else request, close_and_observe)
        return self._finalize_close(room, operation_id)

    def _finalize_close(self, room, operation_id):
        with self.store.transaction() as tx:
            operation = tx.require("operation", operation_id)
            if operation["status"] != "complete":
                raise HandrailError("OPERATION_UNCERTAIN", "Resolve remote closure before local finalization", uncertain=True)
            room = tx.require("room", room["id"])
            if room["state"] == "closed":
                return room
            room.update(state="closed", closed_at=now(), close_operation_id=operation_id)
            tx.put("room", room["id"], room)
            for attempt in tx.list("attempt"):
                if attempt["room_id"] == room["id"]:
                    attempt["state_before_close"] = attempt["state"]
                    attempt.update(state="closed", closed_at=room["closed_at"])
                    tx.put("attempt", attempt["id"], attempt)
            tx.event(room["plan_id"], "room.closed", {"room_id": room["id"], "operation_id": operation_id,
                                                     "worktrees_retained": True})
        return room

    @serialized
    def remove_worktree(self, attempt_id):
        attempt = self._require("attempt", attempt_id)
        room = self._require("room", attempt["room_id"])
        if room["state"] != "closed":
            raise HandrailError("RETENTION_REQUIRED", "Close the accepted plan room before removing worktrees")
        self._accepted_cycle(room)
        self._authorize(attempt, "worktree.remove")
        if not attempt.get("worktree_removed"):
            git = self._git(attempt)
            operation_id = "worktree-remove:" + digest(attempt["path"])
            operation = self.store.read("operation", operation_id)
            request = {"entity": attempt["work_id"], "path": attempt["path"], "branch": attempt["branch"],
                       "resource_scope": self._scope(attempt)}
            if operation and operation["status"] in ("sending", "unknown", "rejected"):
                if not Path(attempt["path"]).exists() and not git.has_worktree(attempt["path"]):
                    with self.store.transaction() as tx:
                        operation.update(status="complete", result={"reconciled": "worktree_absent"}, completed_at=now())
                        tx.put("operation", operation_id, operation)
                elif operation["status"] == "rejected":
                    # A definite Git rejection can be retried explicitly after
                    # preserving/committing changes; the adapter rechecks ownership.
                    with self.store.transaction() as tx:
                        operation.update(status="prepared")
                        tx.put("operation", operation_id, operation)
            self._external(operation_id, "worktree.remove", request,
                           lambda: git.remove_worktree(attempt["path"], attempt["branch"]))
            with self.store.transaction() as tx:
                for item in tx.list("attempt"):
                    if item["path"] == attempt["path"]:
                        item["worktree_removed"] = now()
                        tx.put("attempt", item["id"], item)
                tx.event(attempt["work_id"], "worktree.removed", {"path": attempt["path"]})
        return self._require("attempt", attempt_id)
