from datetime import datetime, timezone
from handrail.shared.errors import HandrailError
from handrail.shared.identity import new_id, now

ACTIONS = {"room.create", "worker.start", "worker.prompt", "worker.keys", "worker.recover",
           "room.close", "worktree.remove", "work.integrate", "command.run"}


class Authorization:
    def __init__(self, store):
        self.store = store

    def grant(self, plan_id, scope, approval, expires_at=None, cycle=None):
        if not isinstance(approval, str) or not approval.strip():
            raise HandrailError("APPROVAL_REQUIRED", "Record the user's existing instruction or approval")
        if not isinstance(scope, dict) or not isinstance(scope.get("actions"), list) or not scope["actions"]:
            raise HandrailError("SCOPE_INVALID", "A grant needs explicit actions")
        if not set(scope["actions"]) <= ACTIONS:
            raise HandrailError("SCOPE_INVALID", "Unknown action in grant")
        if expires_at:
            try:
                expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
                    raise ValueError()
            except ValueError:
                raise HandrailError("EXPIRY_INVALID", "Use a future timestamp with timezone") from None
        with self.store.transaction() as tx:
            plan = tx.require("plan", plan_id)
            selected_cycle = plan["cycle"] if cycle is None else cycle
            if selected_cycle != plan["cycle"]:
                archived = next((item for item in plan.get("cycles", []) if item["cycle"] == selected_cycle), None)
                final_room_cleanup = (plan["state"] == "done" and plan.get("acceptance") and
                                      set(scope["actions"]) == {"room.close"})
                if not archived or (not archived.get("acceptance") and not final_room_cleanup) or not set(scope["actions"]) <= {"room.close", "worktree.remove"}:
                    raise HandrailError("SCOPE_INVALID", "Earlier accepted cycles support cleanup grants only")
            value = {"id": new_id("grant-"), "plan_id": plan_id, "cycle": selected_cycle,
                     "scope": scope, "approval": approval, "expires_at": expires_at,
                     "created_at": now(), "revoked": False}
            tx.put("grant", value["id"], value)
            tx.event(plan_id, "permission.granted", {"grant_id": value["id"], "scope": scope})
        return value

    def revoke(self, grant_id):
        with self.store.transaction() as tx:
            value = tx.require("grant", grant_id)
            if not value["revoked"]:
                value["revoked"] = True
                tx.put("grant", grant_id, value)
                tx.event(value["plan_id"], "permission.revoked", {"grant_id": grant_id})
        return value

    def preview(self, plan_id, action, resources, cycle=None):
        plan = self.store.read("plan", plan_id)
        if not plan:
            raise HandrailError("NOT_FOUND", "Unknown plan")
        cycle = plan["cycle"] if cycle is None else cycle
        candidates = []
        for grant in self.store.list("grant"):
            if grant["plan_id"] != plan_id or grant["cycle"] != cycle or grant["revoked"]:
                continue
            if grant.get("expires_at") and datetime.fromisoformat(grant["expires_at"].replace("Z", "+00:00")) <= datetime.now(timezone.utc):
                continue
            scope = grant["scope"]
            missing = {k: v for k, v in resources.items() if scope.get(k) != v}
            if action not in scope.get("actions", []):
                missing["action"] = action
            if not missing:
                return {"authorized": True, "grant_id": grant["id"], "missing": {}, "host_authority": False}
            candidates.append(missing)
        missing = min(candidates, key=len) if candidates else dict(resources, action=action)
        return {"authorized": False, "missing": missing, "host_authority": False}

    def require(self, plan_id, action, resources, cycle=None):
        value = self.preview(plan_id, action, resources, cycle=cycle)
        if not value["authorized"]:
            raise HandrailError("AUTHORIZATION_REQUIRED", "Record approval for the uncovered action or resources",
                                details=value)
        return value["grant_id"]
