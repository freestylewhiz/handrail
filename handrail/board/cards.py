"""User-directed card state overrides with a durable audit and sync hold."""
from handrail.shared.errors import HandrailError
from handrail.shared.identity import new_id, now


def _reason(value):
    if not isinstance(value, str) or not value.strip():
        raise HandrailError("USER_REQUEST_REQUIRED", "Record the user's state change request")
    return value.strip()


class CardService:
    def __init__(self, boards):
        self.boards, self.store, self.catalog = boards, boards.store, boards.catalog

    def _pending_keys(self, entity):
        return [item["key"] for item in self.store.outbox("board")
                if item["status"] != "complete" and item["payload"].get("entity_id") == entity]

    def _save(self, operation):
        with self.store.transaction() as tx:
            tx.put("operation", operation["id"], operation)
            key = str(operation["request"]["card_id"])
            override = tx.get("card_override", key)
            if override and override["operation_id"] == operation["id"]:
                override["status"] = operation["status"]
                tx.put("card_override", key, override)

    def _finish(self, operation, after):
        request = operation["request"]
        entity_id = request["entity_id"]
        entity = (self.store.read("plan", entity_id) or self.store.read("work", entity_id)) if entity_id else None
        result = {"operation_id": operation["id"], "card_id": request["card_id"],
                  "url": self.catalog.url("tasks", request["card_id"]),
                  "before": operation["before"]["state"], "state": after["state"],
                  "source": "user_override", "reason": request["reason"],
                  "workflow_state": entity["state"] if entity else None,
                  "workflow_verification_changed": False, "automatic_state_sync": "held"}
        with self.store.transaction() as tx:
            override = tx.require("card_override", str(request["card_id"]))
            if override["operation_id"] != operation["id"]:
                raise HandrailError("CARD_OPERATION_CONFLICT", "A newer card override exists")
            override.update(status="complete", state=after["state"], completed_at=now())
            tx.put("card_override", str(request["card_id"]), override)
            if entity_id:
                mapping = tx.require("board_card", entity_id)
                mapping["state"] = after["state"]
                tx.put("board_card", entity_id, mapping)
            operation.update(status="complete", result=result, after=after, completed_at=now())
            tx.put("operation", operation["id"], operation)
            tx.event(entity_id or "card:" + str(request["card_id"]), "card.state_forced", result)
        return result

    def move(self, selection, state, reason, force=False, board_selection=None, operation_id=None):
        reason = _reason(reason)
        if not force:
            raise HandrailError("CARD_FORCE_REQUIRED", "User-directed transitions require --force and the user's request as --reason")
        if operation_id is not None and (not operation_id or len(operation_id) > 160 or
                                         any(c.isspace() or not c.isprintable() for c in operation_id)):
            raise HandrailError("OPERATION_ID_INVALID", "Use a printable operation ID without whitespace")
        with self.store.exclusive("outbox-delivery"):
            adapter, before, entity = self.catalog.card(selection, board_selection)
            if state not in adapter.states:
                raise HandrailError("CARD_STATE_UNAVAILABLE", "Choose an existing state on this board",
                                    details={"available_states": list(adapter.states)})
            self.catalog.api.require_write(adapter.project_id)
            request = {"card_id": before["task_id"], "board_id": adapter.project_id, "view_id": adapter.view_id,
                       "states": adapter.states, "entity_id": entity, "target": state, "reason": reason,
                       "authority": "explicit_user_request", "server": self.boards.client.url}
            old_override = self.store.read("card_override", str(before["task_id"])) or {}
            pending = self.store.read("operation", old_override.get("operation_id", ""))
            if pending and pending["status"] not in ("complete", "cancelled"):
                if pending["request"] != request or (operation_id and operation_id != pending["id"]):
                    raise HandrailError("CARD_OPERATION_PENDING", "Resolve the previous card move first",
                                        details={"operation_id": pending["id"]})
                operation_id = pending["id"]
            operation_id = operation_id or new_id("card-move-")
            with self.store.transaction() as tx:
                operation = tx.intent(operation_id, "card.force", request)
                if operation["status"] == "complete":
                    return operation["result"]
                if operation["status"] == "cancelled":
                    raise HandrailError("OPERATION_CONFLICT", "This move was cancelled; use a new operation ID")
                if "before" not in operation:
                    operation["before"] = before
                    tx.event(entity or "card:" + str(before["task_id"]), "card.move_requested",
                             {"operation_id": operation_id, "before": before, "request": request})
                override = {"id": str(before["task_id"]), "operation_id": operation_id, "active": True,
                            "status": operation["status"], "state": state, "reason": reason,
                            "entity_id": entity, "board_id": adapter.project_id, "view_id": adapter.view_id,
                            "server": self.boards.client.url,
                            "suppressed_events": sorted(set(old_override.get("suppressed_events", [])) |
                                                        set(self._pending_keys(entity))), "requested_at": operation["created_at"]}
                tx.put("card_override", str(before["task_id"]), override)
                tx.put("operation", operation_id, operation)
            if before["state"] == state:
                return self._finish(operation, before)
            if operation["status"] in ("sending", "unknown"):
                raise HandrailError("CARD_MOVE_UNCERTAIN", "Inspect the previous move before retrying",
                                    details={"operation_id": operation_id,
                                             "next": "handrail card resolve OPERATION_ID --evidence REASON"}, uncertain=True)
            if before["state"] != operation["before"]["state"]:
                raise HandrailError("CARD_STATE_CHANGED", "The card changed since the request; reconcile before retrying",
                                    details={"operation_id": operation_id, "state": before["state"]})
            operation["status"] = "sending"
            self._save(operation)
            move_returned = False
            try:
                adapter.move_task(before["task_id"], state, expected_state=before["state"], allow_unmapped=True)
                move_returned = True
                after = adapter.get_task(before["task_id"])
                if after["state"] != state:
                    raise HandrailError("CARD_MOVE_UNCERTAIN", "Card readback differs from the requested state", uncertain=True)
            except Exception as exc:
                definite = (not move_returned and isinstance(exc, HandrailError) and not exc.uncertain
                            and exc.code.startswith("VIKUNJA_HTTP_4"))
                operation["status"] = "rejected" if definite else "unknown"
                operation["error"] = exc.as_dict() if isinstance(exc, HandrailError) else {"type": type(exc).__name__}
                self._save(operation)
                if isinstance(exc, HandrailError):
                    exc.details = dict(exc.details, operation_id=operation_id,
                                       next="Retry the same command" if definite else "handrail card resolve OPERATION_ID --evidence REASON")
                    exc.uncertain = not definite
                raise
            return self._finish(operation, after)

    def resolve(self, operation_id, evidence):
        evidence = _reason(evidence)
        with self.store.exclusive("outbox-delivery"):
            operation = self.store.read("operation", operation_id)
            if not operation or operation["action"] != "card.force":
                raise HandrailError("NOT_FOUND", "Unknown card move operation")
            if operation["status"] == "complete":
                return operation["result"]
            if operation["status"] == "cancelled":
                raise HandrailError("OPERATION_CONFLICT", "This move was cancelled")
            request = operation["request"]
            if request["server"] != self.boards.client.url:
                raise HandrailError("BOARD_SCOPE_CHANGED", "Move belongs to another server")
            adapter, current, _ = self.catalog.card(str(request["card_id"]), str(request["board_id"]))
            if adapter.view_id != request["view_id"] or adapter.states != request["states"]:
                raise HandrailError("BOARD_MAPPING_PINNED", "Card mapping changed during the pending move")
            if current["state"] == request["target"]:
                return self._finish(operation, current)
            with self.store.transaction() as tx:
                operation.update(status="retry", retry_before=current,
                                 resolution={"evidence": evidence, "observed": current, "at": now()})
                # Preserve original before; the conflict check prevents overwriting later third-party moves.
                tx.put("operation", operation_id, operation)
                tx.event(request["entity_id"] or "card:" + str(request["card_id"]), "card.move_reconciled",
                         {"operation_id": operation_id, "resolution": operation["resolution"]})
            return {"operation_id": operation_id, "external_writes": False,
                    "next": "Retry the original move if the previous state is unchanged, or use card resume to cancel it"}

    def resume(self, selection, reason, board_selection=None):
        reason = _reason(reason)
        with self.store.exclusive("outbox-delivery"):
            adapter, current, entity = self.catalog.card(selection, board_selection)
            override = self.store.read("card_override", str(current["task_id"]))
            if not override or not override.get("active"):
                return {"card_id": current["task_id"], "automatic_state_sync": "not_held"}
            if (override["server"], override["board_id"], override["view_id"]) != (
                    self.boards.client.url, adapter.project_id, adapter.view_id):
                raise HandrailError("BOARD_SCOPE_CHANGED", "Override belongs to another board mapping")
            operation = self.store.read("operation", override["operation_id"])
            if operation and operation["status"] in ("sending", "unknown"):
                raise HandrailError("CARD_MOVE_UNCERTAIN", "Resolve the pending move before resuming automatic sync",
                                    details={"operation_id": operation["id"]}, uncertain=True)
            with self.store.transaction() as tx:
                if operation and operation["status"] != "complete":
                    operation.update(status="cancelled", cancellation={"reason": reason, "at": now()})
                    tx.put("operation", operation["id"], operation)
                override.update(active=False, resumed_at=now(), resume_reason=reason,
                                suppressed_events=sorted(set(override.get("suppressed_events", [])) |
                                                         set(self._pending_keys(entity))))
                tx.put("card_override", str(current["task_id"]), override)
                event = tx.event(entity or "card:" + str(current["task_id"]), "card.sync_resumed",
                                 {"card_id": current["task_id"], "reason": reason, "observed": current})
                if entity:
                    mapping = tx.require("board_card", entity)
                    mapping["state"] = current["state"]
                    tx.put("board_card", entity, mapping)
                    document = tx.get("plan", entity) or tx.require("work", entity)
                    tx.enqueue("board", event, {"entity_id": entity, "event_kind": "card_sync_resumed", "document": document})
            return {"card_id": current["task_id"], "automatic_state_sync": "enabled" if entity else "not_managed",
                    "next": "handrail sync --topic board" if entity else None}
