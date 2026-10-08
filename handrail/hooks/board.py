"""Project domain events to Vikunja without making the board the workflow engine.

Creation, relation, move and comment each persist an intent before any write.
A sending or unknown intent is resumed by reading only. Absence does not send
the write again. BoardProjection.resolve records a user-confirmed absence and
sets status to retry; the next dispatch is what may write.
"""
from handrail.interfaces.vikunja.board import marked_description
from handrail.shared.errors import HandrailError
from handrail.shared.identity import now

_BLOCKED = ("sending", "unknown", "rejected")


class BoardProjection:
    def __init__(self, store, board):
        self.store, self.board = store, board

    def _mapping(self, entity_id):
        return self.store.read("board_card", entity_id)

    def _put(self, kind, identity, value):
        with self.store.transaction() as tx:
            tx.put(kind, identity, value)

    def _description(self, document, identity):
        from handrail.board.format import render
        return render(document)

    def _comment_text(self, payload, document, target, operation_id):
        text = f"{payload['event_kind']} · cycle {document['cycle']} · {target}\nHandrail event: {operation_id}"
        if payload["event_kind"] == "work_submitted":
            text += "\n\nEnglish\nWaiting for coordinator review. Next: inspect the submitted commit and report, then accept or request changes. Integration and verification follow acceptance."
            text += "\nSubmission: " + str(payload.get("data", {}).get("submission_id", ""))
            if (document.get("presentation") or {}).get("language") == "ko":
                text += "\n\n한국어\n조율자 검토 대기입니다. 제출 커밋과 보고서를 검토하여 승인하거나 수정을 요청합니다. 승인 뒤 통합과 검증을 진행합니다."
        if payload["event_kind"] == "evidence_recorded":
            data = payload.get("data", {})
            text += "\nCriterion: " + str(data.get("criterion_id", ""))
            text += "\nEvidence: " + str(data.get("evidence", {}).get("observation", {}))
        return text

    def _matches_card(self, task, title, description, operation_id):
        return task["title"] == title and task["description"] == marked_description(description, operation_id)

    def _intent_conflict(self, kind, identity, detail):
        raise HandrailError(
            "BOARD_INTENT_CONFLICT",
            detail,
            details={"kind": kind, "id": identity},
            retryable=False,
            uncertain=True,
        )

    def __call__(self, item):
        payload = item["payload"]
        identity = payload["entity_id"]
        document = payload["document"]
        operation_id = item["key"]
        mapping = self._mapping(identity)
        if not mapping:
            task = self._sync_creation(identity, document, allow_write=True)
            mapping = {"id": identity, "task_id": task["task_id"], "state": task["state"],
                       "created_at": now(), "relation": False, "project_id": self.board.project_id,
                       "view_id": self.board.view_id, "states": self.board.states}
            self._put("board_card", identity, mapping)
        from handrail.board.labels import TypeLabels
        TypeLabels(self.board.client).ensure(mapping["task_id"], "task" if document["kind"] == "work" else document["kind"])
        if document["kind"] == "work" and not mapping["relation"]:
            parent = self._mapping(document["plan_id"])
            if not parent:
                raise HandrailError("BOARD_PARENT_PENDING", "Synchronize the parent card before child work", retryable=True)
            self._sync_relation(identity, parent["task_id"], mapping["task_id"], allow_write=True)
            mapping["relation"] = True
            self._put("board_card", identity, mapping)
        target = document["state"]
        override = self.store.read("card_override", str(mapping["task_id"])) or {}
        held = override.get("active") or operation_id in override.get("suppressed_events", [])
        if override.get("active") and override.get("status") != "complete":
            raise HandrailError("CARD_MOVE_UNCERTAIN", "Finish or reconcile the user-requested card move first",
                                details={"operation_id": override["operation_id"]}, uncertain=True)
        if held and (override.get("server"), override.get("board_id"), override.get("view_id")) != (
                self.board.client.url, self.board.project_id, self.board.view_id):
            raise HandrailError("BOARD_SCOPE_CHANGED", "Card override belongs to a different board mapping")
        if not held:
            self._sync_move(operation_id, mapping["task_id"], target, mapping["state"], allow_write=True)
            mapping["state"] = target
        self._put("board_card", identity, mapping)
        previous_comment = self.store.read("board_comment", operation_id)
        text = previous_comment["text"] if previous_comment else self._comment_text(payload, document, target, operation_id)
        if held and not previous_comment:
            text += "\nCard state retained by user request; workflow state above is separate."
        self._sync_comment(operation_id, mapping["task_id"], text, allow_write=True)
        return {"task_id": mapping["task_id"], "event_id": operation_id, "state": mapping["state"],
                "workflow_state": target, "state_sync": "held" if held else "automatic"}

    def _sync_creation(self, identity, document, allow_write, evidence=None):
        operation_id = "card:" + identity
        title = document["title"].strip()
        description = self._description(document, identity)
        previous = self.store.read("board_creation", identity) or {}
        # A renderer upgrade must not change an interrupted creation's payload.
        description = previous.get("description", description)
        if previous.get("title") and (previous["title"] != title or previous["description"] != description):
            self._intent_conflict("board_creation", identity, "Stored card intent does not match this event")
        expected_title = previous.get("title", title)
        expected_description = previous.get("description", description)
        task = self.board.find_task(operation_id)
        if task:
            if not self._matches_card(task, expected_title, expected_description, operation_id):
                self._intent_conflict("board_creation", identity, "Visible card marker does not match the stored intent")
            self._put("board_creation", identity, {**previous, "status": "complete", "operation_id": operation_id,
                                                   "title": expected_title, "description": expected_description})
            return task
        status = previous.get("status")
        if status == "complete":
            raise HandrailError("BOARD_REMOTE_CHANGED", "Previously confirmed card is missing; do not recreate a deleted card",
                                details={"entity_id": identity, "operation_id": operation_id})
        if not allow_write:
            if status in ("sending", "unknown", "rejected", "retry"):
                self._put("board_creation", identity, {**previous, "status": "retry", "operation_id": operation_id,
                                                       "title": expected_title, "description": expected_description,
                                                       "evidence": evidence, "resolved_at": now()})
                return None
            raise HandrailError(
                "BOARD_CREATE_UNKNOWN",
                "Creation marker is not visible; it was not sent again",
                details={"entity_id": identity, "operation_id": operation_id},
                retryable=False,
                uncertain=True,
            )
        if status in _BLOCKED:
            raise HandrailError(
                "BOARD_CREATE_UNKNOWN",
                "Creation marker is not visible; it was not sent again",
                details={"entity_id": identity, "operation_id": operation_id},
                retryable=False,
                uncertain=True,
            )
        record = {"status": "sending", "operation_id": operation_id, "title": title, "description": description}
        self._put("board_creation", identity, record)
        try:
            task = self.board.create_task(title, description, operation_id)
        except HandrailError as exc:
            record["status"] = "unknown" if exc.uncertain else "rejected"
            self._put("board_creation", identity, record)
            raise
        if not self._matches_card(task, title, description, operation_id):
            record["status"] = "unknown"
            self._put("board_creation", identity, record)
            self._intent_conflict("board_creation", identity, "Created card does not match the stored intent")
        record["status"] = "complete"
        self._put("board_creation", identity, record)
        return task

    def _sync_relation(self, identity, parent_id, child_id, allow_write, evidence=None):
        previous = self.store.read("board_relation", identity) or {}
        if previous.get("parent_id") and (previous["parent_id"] != parent_id or previous["child_id"] != child_id):
            self._intent_conflict("board_relation", identity, "Stored relation intent points at different cards")
        if previous.get("status") == "complete":
            return "complete"
        exists = self.board.relation_exists(parent_id, child_id)
        record = {**previous, "parent_id": parent_id, "child_id": child_id}
        if exists:
            record["status"] = "complete"
            self._put("board_relation", identity, record)
            return "complete"
        status = previous.get("status")
        if not allow_write:
            if status in ("sending", "unknown", "rejected", "retry"):
                record.update(status="retry", evidence=evidence, resolved_at=now())
                self._put("board_relation", identity, record)
                return "retry"
            raise HandrailError(
                "BOARD_RELATION_UNKNOWN",
                "Relation is not visible on both cards; it was not sent again",
                details={"entity_id": identity, "parent_id": parent_id, "child_id": child_id},
                retryable=False,
                uncertain=True,
            )
        if status in _BLOCKED:
            raise HandrailError(
                "BOARD_RELATION_UNKNOWN",
                "Relation is not visible on both cards; it was not sent again",
                details={"entity_id": identity, "parent_id": parent_id, "child_id": child_id},
                retryable=False,
                uncertain=True,
            )
        record["status"] = "sending"
        self._put("board_relation", identity, record)
        try:
            self.board.ensure_relation(parent_id, child_id)
        except HandrailError as exc:
            record["status"] = "unknown" if exc.uncertain else "rejected"
            self._put("board_relation", identity, record)
            raise
        record["status"] = "complete"
        self._put("board_relation", identity, record)
        return "complete"

    def _sync_move(self, event_key, task_id, target, expected_state, allow_write, evidence=None):
        previous = self.store.read("board_move", event_key) or {}
        if previous.get("target") and (previous["task_id"] != task_id or previous["target"] != target):
            self._intent_conflict("board_move", event_key, "Stored move intent has a different card or target")
        if previous.get("status") == "complete":
            return "complete"
        observed = self.board.get_task(task_id)
        record = {**previous, "task_id": task_id, "target": target}
        if observed["state"] == target:
            record["status"] = "complete"
            self._put("board_move", event_key, record)
            return "complete"
        status = previous.get("status")
        if not allow_write:
            if status in ("sending", "unknown", "rejected", "retry"):
                record.update(status="retry", expected_state=observed["state"], evidence=evidence, resolved_at=now())
                self._put("board_move", event_key, record)
                return "retry"
            raise HandrailError(
                "BOARD_MOVE_UNKNOWN",
                "Move is not visible in the target bucket; it was not sent again",
                details={"event_id": event_key, "task_id": task_id, "state": observed["state"], "target": target},
                retryable=False,
                uncertain=True,
            )
        if status in _BLOCKED:
            raise HandrailError(
                "BOARD_MOVE_UNKNOWN",
                "Move is not visible in the target bucket; it was not sent again",
                details={"event_id": event_key, "task_id": task_id, "state": observed["state"], "target": target},
                retryable=False,
                uncertain=True,
            )
        expected = previous.get("expected_state", expected_state) if status == "retry" else expected_state
        record.update(status="sending", expected_state=expected)
        self._put("board_move", event_key, record)
        try:
            self.board.move_task(task_id, target, expected_state=expected)
        except HandrailError as exc:
            record["status"] = "unknown" if exc.uncertain else "rejected"
            self._put("board_move", event_key, record)
            raise
        record["status"] = "complete"
        self._put("board_move", event_key, record)
        return "complete"

    def _sync_comment(self, event_key, task_id, text, allow_write, evidence=None):
        previous = self.store.read("board_comment", event_key) or {}
        if previous.get("status") == "complete":
            return {"task_id": task_id, "event_id": event_key}
        if previous.get("text") and previous["text"] != text:
            self._intent_conflict("board_comment", event_key, "Stored comment intent does not match this event")
        if previous.get("task_id") and previous["task_id"] != task_id:
            self._intent_conflict("board_comment", event_key, "Stored comment intent points at a different card")
        expected = previous.get("text", text)
        found = self.board.find_comment(task_id, event_key, text=expected)
        record = {**previous, "task_id": task_id, "text": expected}
        if found:
            record["status"] = "complete"
            record["comment_id"] = found["comment_id"]
            self._put("board_comment", event_key, record)
            return {"task_id": task_id, "event_id": event_key}
        status = previous.get("status")
        if not allow_write:
            if status in ("sending", "unknown", "rejected", "retry"):
                record.update(status="retry", evidence=evidence, resolved_at=now())
                self._put("board_comment", event_key, record)
                return "retry"
            raise HandrailError(
                "BOARD_COMMENT_UNKNOWN",
                "Comment marker is not visible; it was not sent again",
                details={"event_id": event_key, "task_id": task_id},
                retryable=False,
                uncertain=True,
            )
        if status in _BLOCKED:
            raise HandrailError(
                "BOARD_COMMENT_UNKNOWN",
                "Comment marker is not visible; it was not sent again",
                details={"event_id": event_key, "task_id": task_id},
                retryable=False,
                uncertain=True,
            )
        record["status"] = "sending"
        self._put("board_comment", event_key, record)
        try:
            saved = self.board.ensure_comment(task_id, expected, event_key)
        except HandrailError as exc:
            record["status"] = "unknown" if exc.uncertain else "rejected"
            self._put("board_comment", event_key, record)
            raise
        record.update(status="complete", comment_id=saved["comment_id"])
        self._put("board_comment", event_key, record)
        return {"task_id": task_id, "event_id": event_key}

    def resolve(self, event_key, evidence):
        """Read one event's unknown board intents and record local retry permission.

        This never calls a Vikunja write. A visible matching result becomes
        complete. A confirmed absence becomes status retry, which a later
        dispatch may send. Payload mismatches stay blocked.
        """
        if not isinstance(event_key, str) or not event_key.strip():
            raise HandrailError("BOARD_RESOLVE_INVALID", "event_key is required")
        if not isinstance(evidence, str) or not evidence.strip():
            raise HandrailError("EVIDENCE_REQUIRED", "Record how the absence was confirmed")
        evidence = evidence.strip()
        with self.store.exclusive("outbox-delivery"):
            result = self._resolve(event_key, evidence)
            with self.store.transaction() as tx:
                tx.event(self._event(event_key)["payload"]["entity_id"], "board.reconciled",
                         {"event_key": event_key, "evidence": evidence, "result": result})
            return result

    def _event(self, event_key):
        matches = [item for item in self.store.outbox() if item["key"] == event_key]
        if len(matches) != 1 or matches[0]["topic"] != "board":
            raise HandrailError("NOT_FOUND", "Unknown board event", details={"event_key": event_key})
        return matches[0]

    def _resolve(self, event_key, evidence):
        item = self._event(event_key)
        payload = item["payload"]
        document = payload["document"]
        identity = payload["entity_id"]
        result = {"event_key": event_key, "creation": "absent", "relation": "absent",
                  "move": "absent", "comment": "absent"}
        creation = self.store.read("board_creation", identity)
        if creation:
            if creation.get("status") == "complete":
                result["creation"] = "complete"
            else:
                task = self._sync_creation(identity, document, allow_write=False, evidence=evidence)
                result["creation"] = "complete" if task else "retry"
                if task:
                    current = self._mapping(identity) or {"id": identity, "created_at": now(), "relation": False}
                    current.update(task_id=task["task_id"], state=task["state"])
                    self._put("board_card", identity, current)
        relation = self.store.read("board_relation", identity)
        if relation and document.get("kind") == "work":
            if relation.get("status") == "complete":
                result["relation"] = "complete"
            elif not relation.get("parent_id") or not relation.get("child_id"):
                raise HandrailError("BOARD_RELATION_UNKNOWN", "Relation intent has no card ids", uncertain=True)
            else:
                result["relation"] = self._sync_relation(
                    identity, relation["parent_id"], relation["child_id"], allow_write=False, evidence=evidence)
                if result["relation"] == "complete":
                    current = self._mapping(identity)
                    if current:
                        current["relation"] = True
                        self._put("board_card", identity, current)
        move = self.store.read("board_move", event_key)
        override = self.store.read("card_override", str(move["task_id"])) if move else None
        if move and override and (override.get("active") or event_key in override.get("suppressed_events", [])):
            result["move"] = "superseded_by_user_request"
        elif move:
            if move.get("status") == "complete":
                result["move"] = "complete"
            elif not move.get("task_id") or not move.get("target"):
                raise HandrailError("BOARD_MOVE_UNKNOWN", "Move intent has no card or target", uncertain=True)
            else:
                result["move"] = self._sync_move(
                    event_key, move["task_id"], move["target"], move.get("expected_state"),
                    allow_write=False, evidence=evidence)
                if result["move"] == "complete":
                    current = self._mapping(identity)
                    if current:
                        current["state"] = move["target"]
                        self._put("board_card", identity, current)
        comment = self.store.read("board_comment", event_key)
        if comment:
            if comment.get("status") == "complete":
                result["comment"] = "complete"
            elif not comment.get("task_id") or not isinstance(comment.get("text"), str):
                raise HandrailError("BOARD_COMMENT_UNKNOWN", "Comment intent has no card or text", uncertain=True)
            else:
                outcome = self._sync_comment(
                    event_key, comment["task_id"], comment["text"], allow_write=False, evidence=evidence)
                result["comment"] = "complete" if isinstance(outcome, dict) else outcome
        return result
