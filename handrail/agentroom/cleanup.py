"""Completion cleanup is an explicit, resumable choice scoped to recorded rooms."""
from handrail.shared.errors import HandrailError
from handrail.shared.identity import digest, now
from .service import resource_scope
from .process import process_identity, reconcile_identity


def stable_target(target):
    """Consent identifies resources and ownership, not late observation fields."""
    result = {k: target[k] for k in ("room_id", "workspace_id", "resource_scope")}
    result["owned_panes"] = {pane: {"origin": owner["origin"], "identity": {
        k: owner["identity"].get(k) for k in ("workspace_id", "pane_id", "terminal_id", "provider", "name")}}
        for pane, owner in sorted(target.get("owned_panes", {}).items())}
    return result


class CleanupService:
    def __init__(self, app):
        self.app, self.store = app, app.store

    def preview(self, plan_id):
        rooms = [r for r in self.store.list("room") if r["plan_id"] == plan_id and r["state"] != "closed"]
        scope = [{"room_id": r["id"], "workspace_id": r["workspace_id"],
                  "resource_scope": resource_scope(self.app.config, r), "owned_panes": r.get("owned_panes", {})} for r in rooms]
        scope = [stable_target(t) for t in sorted(scope, key=lambda t: t["room_id"])]
        token = digest(scope)
        choices = [c for c in self.store.list("cleanup_choice") if c["plan_id"] == plan_id and
                   sorted([stable_target(t) for t in c["rooms"]], key=lambda t: t["room_id"]) == scope]
        choice = max(choices, key=lambda c: c["at"]) if choices else None
        return {"plan_id": plan_id, "scope_token": token, "rooms": scope,
                "workers": [{k: a.get(k) for k in ("id", "room_id", "name", "provider", "model", "state", "activity", "observed_at")}
                            for a in self.store.list("attempt") if a["room_id"] in {r["id"] for r in rooms}],
                "requires_user_response": bool(rooms) and not choice,
                "choice": choice["choice"] if choice else None,
                "choices": ["close", "keep"], "worktrees_deleted": False,
                "effects": "Close only listed AgentRooms and their owned idle workers/terminals; retain worktrees and files. Shared, changed or busy occupants block closure.",
                "next": ("plan cleanup PLAN --resume" if choice and choice["choice"] == "close" else
                         "Ask whether to close or keep these rooms; record the answer with plan cleanup") if rooms else "No rooms to clean"}

    def inspect(self, plan_id):
        service = self.app.room()
        observations = []
        for room in self.store.list("room"):
            if room["plan_id"] != plan_id or room["state"] == "closed":
                continue
            client = service._client(room)
            for pane, owner in room.get("owned_panes", {}).items():
                current, row = service._pane_owner(client, pane, room["workspace_id"])
                process = process_identity(client, pane) if current["provider"] else None
                item = {"room_id": room["id"], "pane_id": pane, "pinned": owner["identity"],
                        "observed": current, "process_identity": process, "activity": row.get("agent_status")}
                try:
                    reconcile_identity(owner["identity"], current, process)
                    item["identity_status"] = "confirmed"
                except HandrailError as exc:
                    item.update(identity_status="unproven" if exc.code == "IDENTITY_UNPROVEN" else "changed", error=exc.as_dict())
                observations.append(item)
        return {"plan_id": plan_id, "observations": observations, "observation_token": digest(observations),
                "next": "Use --reconcile TOKEN --evidence TEXT only after inspecting ownership; then --resume"}

    def reconcile(self, plan_id, token, evidence):
        if not isinstance(evidence, str) or not evidence.strip():
            raise HandrailError("EVIDENCE_REQUIRED", "Record evidence connecting the observed worker to its original launch")
        with self.store.exclusive("agentroom-mutation"):
            snapshot = self.inspect(plan_id)
            if snapshot["observation_token"] != token:
                raise HandrailError("IDENTITY_OBSERVATION_CHANGED", "Inspect again before reconciling", details=snapshot)
            updates = []
            for item in snapshot["observations"]:
                if item["identity_status"] == "unproven":
                    room = self.store.read("room", item["room_id"])
                    owner = room["owned_panes"][item["pane_id"]]
                    launch = self.store.read("operation", owner["origin"])
                    attempts = [a for a in self.store.list("attempt") if a["room_id"] == item["room_id"] and
                                a.get("identity") == item["pinned"]]
                    processes = (item["process_identity"] or {}).get("processes", [])
                    from pathlib import Path
                    if (not launch or launch["action"] != "worker.start" or launch["status"] != "complete" or
                        len(attempts) != 1 or not processes or any(
                            Path(p["cwd"]) != Path(attempts[0]["path"]) and
                            Path(attempts[0]["path"]) not in Path(p["cwd"]).parents for p in processes)):
                        raise HandrailError("IDENTITY_UNPROVEN", "Legacy reconciliation needs its completed launch receipt and owned-worktree process evidence")
                identity = reconcile_identity(item["pinned"], item["observed"], item["process_identity"], explicit=True)
                updates.append((item, identity))
            with self.store.transaction() as tx:
                for item, identity in updates:
                    room = tx.require("room", item["room_id"])
                    room["owned_panes"][item["pane_id"]]["identity"] = identity
                    tx.put("room", room["id"], room)
                    for attempt in tx.list("attempt"):
                        if attempt["room_id"] == room["id"] and attempt.get("identity") == item["pinned"]:
                            attempt["identity"] = identity
                            tx.put("attempt", attempt["id"], attempt)
                tx.event(plan_id, "cleanup.identity_reconciled", {"observation_token": token, "evidence": evidence,
                         "observations": snapshot["observations"], "workflow_state_changed": False})
        return {"plan_id": plan_id, "reconciled": True, "next": "plan cleanup PLAN --resume"}

    def resume(self, plan_id):
        preview = self.preview(plan_id)
        if not preview["rooms"]:
            return preview
        if preview["choice"] != "close":
            raise HandrailError("CLEANUP_CHOICE_REQUIRED", "Record a close choice for these resources", details=preview)
        results = []
        for target in preview["rooms"]:
            try:
                results.append({"status": "complete", "result": self.deliver(target["room_id"])})
            except HandrailError as exc:
                results.append({"status": "unknown" if exc.uncertain else "failed", "error": exc.as_dict()})
        return {"cleanup": results, "next": "sync --topic room.cleanup to finalize pending receipts"}

    def choose(self, plan_id, choice, approval, scope_token):
        if not isinstance(approval, str) or not approval.strip():
            raise HandrailError("APPROVAL_REQUIRED", "Record the user's cleanup choice")
        if choice not in ("close", "keep"):
            raise HandrailError("CLEANUP_CHOICE_INVALID", "Choose close or keep")
        with self.store.exclusive("agentroom-mutation"):
            preview = self.preview(plan_id)
            if preview["scope_token"] != scope_token:
                raise HandrailError("CLEANUP_SCOPE_CHANGED", "Preview the current rooms before applying the choice", details=preview)
            identity = "cleanup-choice:" + digest({"plan": plan_id, "token": scope_token})
            previous = self.store.read("cleanup_choice", identity)
            decision_version = (previous or {}).get("decision_version", 0)
            if not previous or previous["choice"] != choice:
                decision_version += 1
            value = {"id": identity, "plan_id": plan_id, "choice": choice, "approval": approval,
                     "scope_token": scope_token, "rooms": preview["rooms"], "at": now(), "decision_version": decision_version}
            if choice == "close":
                self._accepted(plan_id)
                self._summary_ready(plan_id)
                service = self.app.room()
                for target in preview["rooms"]:
                    room = self.store.read("room", target["room_id"])
                    resources = resource_scope(self.app.config, room)
                    authorized = service.authorization.preview(plan_id, "room.close", resources, cycle=room["cycle"])
                    if not authorized["authorized"]:
                        service.authorization.grant(plan_id, dict(resources, actions=["room.close"]), approval, cycle=room["cycle"])
            with self.store.transaction() as tx:
                tx.put("cleanup_choice", identity, value)
                tx.event(plan_id, "cleanup.choice_recorded", {"choice_id": identity, "choice": choice, "scope_token": scope_token})
                if choice == "close":
                    for target in preview["rooms"]:
                        # Same consent/room uses one delivery key across retries.
                        tx.enqueue("room.cleanup", identity + ":" + str(decision_version) + ":" + target["room_id"],
                                   {"entity_id": plan_id, "room_id": target["room_id"]})
        return {"choice": value, "cleanup": self.app.dispatch("room.cleanup") if choice == "close" else [],
                "worktrees_retained": True}

    def _accepted(self, plan_id):
        plan = self.store.read("plan", plan_id)
        if not plan or plan["state"] != "done" or not plan.get("acceptance"):
            raise HandrailError("REVIEW_RETENTION", "Accept the reviewed plan before completion cleanup")
        return plan

    def _summary_ready(self, plan_id):
        plan = self._accepted(plan_id)
        summary = self.store.read("summary_card", plan_id)
        if not summary:
            raise HandrailError("SUMMARY_REQUIRED", "Publish the Summary before clearing its AgentRooms")
        observed = self.app.summaries().read(summary["card_id"])
        if observed["content"]["record_status"] != "accepted" or observed["content"]["cycle"] != plan["cycle"]:
            raise HandrailError("SUMMARY_REQUIRED", "Finalize the current cycle Summary before cleanup")

    def deliver(self, room_id):
        room = self.store.read("room", room_id)
        if not room:
            raise HandrailError("NOT_FOUND", "Unknown room")
        if room["state"] == "closed":
            return room
        target = {"room_id": room_id, "workspace_id": room["workspace_id"],
                  "resource_scope": resource_scope(self.app.config, room), "owned_panes": room.get("owned_panes", {})}
        choices = [c for c in self.store.list("cleanup_choice") if c["plan_id"] == room["plan_id"] and
                   stable_target(target) in [stable_target(t) for t in c["rooms"]]]
        if not choices:
            raise HandrailError("CLEANUP_CHOICE_REQUIRED", "Ask whether to close or retain the plan's AgentRooms",
                                details=self.preview(room["plan_id"]))
        choice = max(choices, key=lambda c: c["at"])
        if choice["choice"] == "keep":
            return {"room_id": room_id, "retained": True}
        self._summary_ready(room["plan_id"])
        return self.app.room().close(room_id)
