"""Project board operations with marker readback and no automatic write retry."""
from __future__ import annotations

from handrail.shared.errors import HandrailError

_REQUIRED_STATES = ("todo", "doing", "done")
_OPTIONAL_STATES = ("review",)


def _positive_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise HandrailError("BOARD_MAPPING_INVALID", label + " must be a positive integer")
    return value


def _operation_id(value):
    if not isinstance(value, str) or not value or len(value) > 160 or any(
            char.isspace() or ord(char) < 32 or ord(char) == 127 or not char.isprintable() for char in value):
        raise HandrailError(
            "VIKUNJA_OPERATION_INVALID",
            "operation_id must be a printable token of at most 160 characters without whitespace",
        )
    return value


def _marker(operation_id):
    return "[Handrail operation " + operation_id + "]"


def marked_description(description, operation_id):
    """Description body create_task stores, including its single operation marker."""
    operation_id = _operation_id(operation_id)
    if not isinstance(description, str):
        raise HandrailError("VIKUNJA_DESCRIPTION_INVALID", "description must be text")
    base = description.rstrip()
    return (base + "\n\n" if base else "") + _marker(operation_id)


def _related(task, kind):
    related = task.get("related_tasks") if isinstance(task, dict) else None
    values = related.get(kind) if isinstance(related, dict) else None
    return values if isinstance(values, list) else []


def _ids(rows):
    found = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw = row.get("id", row.get("other_task_id"))
        if isinstance(raw, bool) or not isinstance(raw, int):
            continue
        found.add(raw)
    return found


class VikunjaBoard:
    def __init__(self, client, project_id, view_id, states):
        if not callable(getattr(client, "request", None)) or not callable(getattr(client, "pages", None)):
            raise HandrailError("VIKUNJA_CLIENT_INVALID", "board client must provide request and pages")
        self.client = client
        self.project_id = _positive_int(project_id, "project_id")
        self.view_id = _positive_int(view_id, "view_id")
        if not isinstance(states, dict):
            raise HandrailError("BOARD_MAPPING_INVALID", "states must map todo, doing, and done")
        allowed = set(_REQUIRED_STATES + _OPTIONAL_STATES)
        if any(key not in allowed for key in states) or any(key not in states for key in _REQUIRED_STATES):
            raise HandrailError("BOARD_MAPPING_INVALID", "states require todo, doing, and done; review is optional")
        self.states = {key: _positive_int(states[key], key) for key in states}
        if len(set(self.states.values())) != len(self.states):
            raise HandrailError("BOARD_MAPPING_INVALID", "each state must use a distinct bucket")

    def _request(self, path, method="GET", body=None):
        return self.client.request(path, method=method, body=body)

    def validate(self):
        view = self._request("/projects/" + str(self.project_id) + "/views/" + str(self.view_id))
        if not isinstance(view, dict):
            raise HandrailError("BOARD_MAPPING_INVALID", "project view response was not an object")
        try:
            view_project = int(view.get("project_id", -1))
            done_bucket = int(view.get("done_bucket_id") or -1)
            default_bucket = int(view.get("default_bucket_id") or -1)
        except (TypeError, ValueError):
            raise HandrailError("BOARD_MAPPING_INVALID", "project view identity was not numeric") from None
        if isinstance(view.get("done_bucket_id"), bool) or isinstance(view.get("default_bucket_id"), bool):
            raise HandrailError("BOARD_MAPPING_INVALID", "bucket ids must be integers")
        if (view_project != self.project_id or view.get("view_kind") != "kanban"
                or view.get("bucket_configuration_mode") != "manual" or done_bucket != self.states["done"]
                or default_bucket != self.states["todo"]):
            raise HandrailError(
                "BOARD_MAPPING_INVALID",
                "view must be manual kanban, its done bucket must match, and its default bucket must be todo",
            )
        buckets = self.client.pages("/projects/" + str(self.project_id) + "/views/" + str(self.view_id) + "/buckets")
        bucket_ids = set()
        for row in buckets:
            try:
                bucket_ids.add(int(row.get("id", -1)))
            except (TypeError, ValueError):
                raise HandrailError("BOARD_MAPPING_INVALID", "bucket id was not numeric") from None
        if not set(self.states.values()).issubset(bucket_ids):
            raise HandrailError("BOARD_MAPPING_INVALID", "a mapped bucket does not exist on the view")
        return {
            "project_id": self.project_id,
            "view_id": self.view_id,
            "states": dict(self.states),
            "view_kind": "kanban",
            "bucket_configuration_mode": "manual",
            "done_bucket_id": done_bucket,
            "default_bucket_id": default_bucket,
            "review_required": False,
        }

    def _state_of(self, task):
        buckets = task.get("buckets") or []
        if not isinstance(buckets, list):
            raise HandrailError("BOARD_MAPPING_INVALID", "task bucket membership was not a list")
        membership = []
        for row in buckets:
            if not isinstance(row, dict):
                continue
            try:
                if int(row.get("project_view_id", -1)) == self.view_id:
                    membership.append(int(row["id"]))
            except (TypeError, ValueError, KeyError):
                raise HandrailError("BOARD_MAPPING_INVALID", "task bucket membership was invalid") from None
        if len(membership) != 1:
            raise HandrailError("BOARD_MAPPING_INVALID", "task has no unique bucket in the bound view")
        matches = [name for name, bucket_id in self.states.items() if bucket_id == membership[0]]
        return matches[0] if len(matches) == 1 else "unmapped"

    def _snapshot(self, task, operation_id=None):
        if not isinstance(task, dict):
            raise HandrailError("VIKUNJA_INVALID_RESPONSE", "task response must be an object")
        try:
            task_id = int(task.get("id", -1))
            project_id = int(task.get("project_id", -1))
        except (TypeError, ValueError):
            raise HandrailError("VIKUNJA_INVALID_RESPONSE", "task identity must be numeric") from None
        if task_id <= 0:
            raise HandrailError("VIKUNJA_INVALID_RESPONSE", "task identity must be numeric")
        if project_id != self.project_id:
            raise HandrailError("VIKUNJA_TASK_PROJECT_MISMATCH", "task does not belong to the bound project")
        state = self._state_of(task)
        done = bool(task.get("done"))
        if state != "unmapped" and done != (state == "done"):
            raise HandrailError("BOARD_MAPPING_INVALID", "task done flag does not match its bucket")
        snapshot = {
            "task_id": task_id,
            "title": task.get("title", ""),
            "description": task.get("description") or "",
            "project_id": project_id,
            "done": done,
            "state": state,
        }
        if operation_id is not None:
            snapshot["operation_id"] = operation_id
        return snapshot

    def get_task(self, id):
        task_id = _positive_int(id, "task id")
        task = self._request("/tasks/" + str(task_id) + "?expand=buckets")
        snapshot = self._snapshot(task)
        if snapshot["task_id"] != task_id:
            raise HandrailError("VIKUNJA_INVALID_RESPONSE", "task response id did not match the request")
        return snapshot

    def _marked_description(self, description, operation_id):
        body = marked_description(description, operation_id)
        return _marker(operation_id), body

    def replace_description(self, task_id, description, expected_description):
        """Update only the description. Read checks are not an atomic server CAS."""
        current = self.get_task(task_id)
        if current["description"] == description:
            return current
        if current["description"] != expected_description:
            raise HandrailError("SUMMARY_EDIT_CONFLICT", "Card changed immediately before description update")
        self._request(f"/tasks/{task_id}", method="PATCH", body={"description": description})
        observed = self.get_task(task_id)
        if observed["description"] != description:
            raise HandrailError("VIKUNJA_WRITE_UNCERTAIN", "Description readback differs from requested content", uncertain=True)
        return observed

    def _tasks_with_marker(self, operation_id):
        marker = _marker(operation_id)
        rows = self.client.pages("/projects/" + str(self.project_id) + "/tasks?expand=buckets")
        return [row for row in rows if marker in str(row.get("description") or "")]

    def find_task(self, operation_id):
        operation_id = _operation_id(operation_id)
        matches = self._tasks_with_marker(operation_id)
        if not matches:
            return None
        if len(matches) != 1:
            raise HandrailError(
                "VIKUNJA_MARKER_AMBIGUOUS",
                "more than one card contains the operation marker",
                details={"operation_id": operation_id, "matches": len(matches)},
                retryable=False,
                uncertain=True,
            )
        return self._snapshot(matches[0], operation_id)

    def create_task(self, title, description, operation_id):
        operation_id = _operation_id(operation_id)
        if not isinstance(title, str) or not title.strip():
            raise HandrailError("VIKUNJA_TITLE_REQUIRED", "task title is required")
        marker, body = self._marked_description(description, operation_id)
        existing = self.find_task(operation_id)
        if existing is not None:
            if existing["title"] != title.strip() or existing["description"] != body:
                raise HandrailError(
                    "VIKUNJA_OPERATION_CONFLICT",
                    "operation marker already exists with a different payload",
                    details={"operation_id": operation_id, "task_id": existing["task_id"]},
                    uncertain=False,
                )
            return existing
        payload = {"title": title.strip(), "description": body}
        try:
            created = self._request("/projects/" + str(self.project_id) + "/tasks", method="POST", body=payload)
        except HandrailError as exc:
            if not exc.uncertain:
                raise
            return self._reconcile_created(operation_id, title.strip(), body, exc)
        if not isinstance(created, dict) or isinstance(created.get("id"), bool) or not isinstance(created.get("id"), int):
            return self._reconcile_created(
                operation_id, title.strip(), body,
                HandrailError("VIKUNJA_WRITE_UNCERTAIN", "task create response had no id", uncertain=True),
            )
        try:
            observed = self.get_task(int(created["id"]))
        except HandrailError as exc:
            raise HandrailError(
                "VIKUNJA_WRITE_UNCERTAIN",
                "task create was not confirmed by readback",
                details={"operation_id": operation_id},
                retryable=False,
                uncertain=True,
            ) from exc
        if marker not in observed["description"] or observed["title"] != title.strip() or observed["description"] != body:
            raise HandrailError(
                "VIKUNJA_OPERATION_CONFLICT",
                "created task readback did not match the requested payload",
                details={"operation_id": operation_id, "task_id": observed["task_id"]},
                uncertain=False,
            )
        observed["operation_id"] = operation_id
        return observed

    def _reconcile_created(self, operation_id, title, body, original):
        try:
            found = self.find_task(operation_id)
        except HandrailError as exc:
            raise HandrailError(
                "VIKUNJA_WRITE_UNCERTAIN",
                "task create may have landed; readback did not resolve it",
                details={"operation_id": operation_id},
                retryable=False,
                uncertain=True,
            ) from exc
        if found is None or found["title"] != title or found["description"] != body:
            raise HandrailError(
                "VIKUNJA_WRITE_UNCERTAIN",
                "task create was not confirmed; it was not sent again",
                details={"operation_id": operation_id},
                retryable=False,
                uncertain=True,
            ) from original
        return found

    def _load_relation(self, task_id):
        task = self._request("/tasks/" + str(task_id) + "?expand=subtasks")
        if not isinstance(task, dict):
            raise HandrailError("VIKUNJA_INVALID_RESPONSE", "relation readback must be an object", uncertain=True)
        return task

    def _reject_cycle(self, parent_id, child_id):
        seen = set()
        current = parent_id
        while current not in seen and len(seen) < 32:
            seen.add(current)
            task = self._load_relation(current)
            parents = _ids(_related(task, "parenttask"))
            if not parents:
                return
            if len(parents) != 1:
                raise HandrailError("VIKUNJA_RELATION_CONFLICT", "task ancestry has more than one parent", uncertain=False)
            current = next(iter(parents))
            if current == child_id:
                raise HandrailError("VIKUNJA_RELATION_CONFLICT", "linking would create a task relation cycle", uncertain=False)
        if len(seen) >= 32:
            raise HandrailError("VIKUNJA_RELATION_CONFLICT", "task ancestry is too deep to verify", uncertain=False)

    def _relation_view(self, parent_id, child_id):
        parent_id = _positive_int(parent_id, "parent id")
        child_id = _positive_int(child_id, "child id")
        if parent_id == child_id:
            raise HandrailError("VIKUNJA_RELATION_CONFLICT", "a task cannot be its own subtask")
        parent = self._load_relation(parent_id)
        child = self._load_relation(child_id)
        parent_ids = _ids(_related(child, "parenttask"))
        child_ids = _ids(_related(parent, "subtask"))
        if parent_ids and parent_ids != {parent_id}:
            raise HandrailError(
                "VIKUNJA_RELATION_CONFLICT",
                "child task already has another parent",
                details={"parent_id": parent_id, "child_id": child_id},
                uncertain=False,
            )
        linked = parent_id in parent_ids and child_id in child_ids
        partial = (parent_id in parent_ids) != (child_id in child_ids)
        return parent_id, child_id, linked, partial

    def relation_exists(self, parent_id, child_id):
        """Read both cards. True only when each side shows the same subtask link."""
        parent_id, child_id, linked, partial = self._relation_view(parent_id, child_id)
        if partial:
            raise HandrailError(
                "VIKUNJA_RELATION_UNCERTAIN",
                "relation is visible on only one card",
                details={"parent_id": parent_id, "child_id": child_id},
                retryable=False,
                uncertain=True,
            )
        return linked

    def ensure_relation(self, parent_id, child_id):
        parent_id, child_id, linked, partial = self._relation_view(parent_id, child_id)
        if linked:
            return {"parent_id": parent_id, "child_id": child_id, "relation_kind": "subtask", "linked": True}
        if partial:
            raise HandrailError(
                "VIKUNJA_RELATION_UNCERTAIN",
                "relation is visible on only one card; it was not sent again",
                details={"parent_id": parent_id, "child_id": child_id},
                retryable=False,
                uncertain=True,
            )
        self._reject_cycle(parent_id, child_id)
        try:
            self._request(
                "/tasks/" + str(parent_id) + "/relations",
                method="POST",
                body={"other_task_id": child_id, "relation_kind": "subtask"},
            )
        except HandrailError as exc:
            if not exc.uncertain and not str(exc.code).startswith("VIKUNJA_HTTP_409"):
                raise
        parent = self._load_relation(parent_id)
        child = self._load_relation(child_id)
        if parent_id in _ids(_related(child, "parenttask")) and child_id in _ids(_related(parent, "subtask")):
            return {"parent_id": parent_id, "child_id": child_id, "relation_kind": "subtask", "linked": True}
        raise HandrailError(
            "VIKUNJA_RELATION_UNCERTAIN",
            "relation write was not confirmed on both cards and was not sent again",
            details={"parent_id": parent_id, "child_id": child_id},
            retryable=False,
            uncertain=True,
        )

    def move_task(self, id, state, expected_state=None, allow_unmapped=False):
        task_id = _positive_int(id, "task id")
        if state not in self.states:
            raise HandrailError("VIKUNJA_STATE_UNAVAILABLE", "the bound board has no " + str(state) + " bucket")
        current = self.get_task(task_id)
        if current["state"] == state:
            return {"task_id": task_id, "state": state, "previous_state": current["state"], "reconciled": True}
        if expected_state is not None and expected_state not in self.states and not (allow_unmapped and expected_state == "unmapped"):
            raise HandrailError("VIKUNJA_STATE_UNAVAILABLE", "expected_state is not mapped on this board")
        if expected_state is not None and current["state"] != expected_state:
            raise HandrailError(
                "VIKUNJA_UPDATE_CONFLICT",
                "task state changed before the move",
                details={"task_id": task_id, "state": current["state"]},
                uncertain=False,
            )
        if current["state"] == "unmapped" and not allow_unmapped:
            raise HandrailError("BOARD_MAPPING_INVALID", "task is not in a mapped bucket", uncertain=False)
        self.validate()
        path = ("/projects/" + str(self.project_id) + "/views/" + str(self.view_id)
                + "/buckets/" + str(self.states[state]) + "/tasks")
        try:
            self._request(path, method="PUT", body={"task_id": task_id})
        except HandrailError as exc:
            if not exc.uncertain:
                raise
            return self._reconcile_move(task_id, state, exc)
        try:
            observed = self.get_task(task_id)
        except HandrailError as exc:
            raise HandrailError(
                "VIKUNJA_WRITE_UNCERTAIN",
                "bucket update was not confirmed by readback",
                details={"task_id": task_id, "state": state},
                retryable=False,
                uncertain=True,
            ) from exc
        if observed["state"] != state:
            raise HandrailError(
                "VIKUNJA_UPDATE_CONFLICT",
                "bucket readback did not match the requested state",
                details={"task_id": task_id, "state": observed["state"]},
                uncertain=False,
            )
        return {"task_id": task_id, "state": state, "previous_state": current["state"]}

    def _reconcile_move(self, task_id, state, original):
        try:
            observed = self.get_task(task_id)
        except HandrailError as exc:
            raise HandrailError(
                "VIKUNJA_WRITE_UNCERTAIN",
                "bucket update may have landed; readback failed",
                details={"task_id": task_id, "state": state},
                retryable=False,
                uncertain=True,
            ) from exc
        if observed["state"] == state:
            return {"task_id": task_id, "state": state, "previous_state": None, "reconciled": True}
        raise HandrailError(
            "VIKUNJA_WRITE_UNCERTAIN",
            "bucket update was not confirmed and was not sent again",
            details={"task_id": task_id, "state": observed["state"]},
            retryable=False,
            uncertain=True,
        ) from original

    def _comments(self, task_id):
        return self.client.pages("/tasks/" + str(task_id) + "/comments")

    def find_comment(self, task_id, operation_id, text=None):
        task_id = _positive_int(task_id, "task id")
        operation_id = _operation_id(operation_id)
        marker = _marker(operation_id)
        matches = [row for row in self._comments(task_id) if marker in str(row.get("comment") or "")]
        if not matches:
            return None
        if len(matches) != 1:
            raise HandrailError(
                "VIKUNJA_MARKER_AMBIGUOUS",
                "more than one comment contains the operation marker",
                details={"operation_id": operation_id, "task_id": task_id, "matches": len(matches)},
                retryable=False,
                uncertain=True,
            )
        raw_id = matches[0].get("id")
        if isinstance(raw_id, bool) or not isinstance(raw_id, int) or raw_id <= 0:
            raise HandrailError(
                "VIKUNJA_INVALID_RESPONSE",
                "comment id was missing",
                details={"operation_id": operation_id, "task_id": task_id},
                uncertain=True,
            )
        observed = str(matches[0].get("comment") or "")
        if text is not None:
            if not isinstance(text, str) or not text.strip():
                raise HandrailError("VIKUNJA_COMMENT_REQUIRED", "comment text is required")
            expected = marker + "\n" + text
            if observed != expected and observed != expected + "\n":
                raise HandrailError(
                    "VIKUNJA_OPERATION_CONFLICT",
                    "comment marker does not match the stored text",
                    details={"operation_id": operation_id, "task_id": task_id},
                    uncertain=False,
                )
        return {
            "task_id": task_id,
            "comment_id": raw_id,
            "operation_id": operation_id,
            "comment": observed,
        }

    def ensure_comment(self, id, text, operation_id):
        task_id = _positive_int(id, "task id")
        operation_id = _operation_id(operation_id)
        if not isinstance(text, str) or not text.strip():
            raise HandrailError("VIKUNJA_COMMENT_REQUIRED", "comment text is required")
        self.get_task(task_id)
        marker = _marker(operation_id) + "\n"
        comment = marker + text
        matches = [row for row in self._comments(task_id) if marker in str(row.get("comment") or "")]
        existing = self._one_comment(matches, comment, operation_id, task_id)
        if existing is not None:
            return existing
        try:
            created = self._request("/tasks/" + str(task_id) + "/comments", method="POST", body={"comment": comment})
        except HandrailError as exc:
            if not exc.uncertain:
                raise
            return self._reconcile_comment(task_id, comment, marker, operation_id, exc)
        if not isinstance(created, dict):
            return self._reconcile_comment(
                task_id, comment, marker, operation_id,
                HandrailError("VIKUNJA_WRITE_UNCERTAIN", "comment response was not an object", uncertain=True),
            )
        matches = [row for row in self._comments(task_id) if marker in str(row.get("comment") or "")]
        confirmed = self._one_comment(matches, comment, operation_id, task_id)
        if confirmed is None:
            raise HandrailError(
                "VIKUNJA_WRITE_UNCERTAIN",
                "comment write was not confirmed by marker readback",
                details={"operation_id": operation_id, "task_id": task_id},
                retryable=False,
                uncertain=True,
            )
        return confirmed

    def _one_comment(self, matches, comment, operation_id, task_id):
        if not matches:
            return None
        if len(matches) != 1:
            raise HandrailError(
                "VIKUNJA_MARKER_AMBIGUOUS",
                "more than one comment contains the operation marker",
                details={"operation_id": operation_id, "task_id": task_id, "matches": len(matches)},
                retryable=False,
                uncertain=True,
            )
        observed = str(matches[0].get("comment") or "")
        if observed != comment and observed != comment + "\n":
            raise HandrailError(
                "VIKUNJA_OPERATION_CONFLICT",
                "comment marker already exists with a different payload",
                details={"operation_id": operation_id, "task_id": task_id},
                uncertain=False,
            )
        raw_id = matches[0].get("id")
        if isinstance(raw_id, bool) or not isinstance(raw_id, int) or raw_id <= 0:
            raise HandrailError("VIKUNJA_INVALID_RESPONSE", "comment id was missing", uncertain=True)
        return {"task_id": task_id, "comment_id": raw_id, "operation_id": operation_id, "comment": observed}

    def _reconcile_comment(self, task_id, comment, marker, operation_id, original):
        try:
            matches = [row for row in self._comments(task_id) if marker in str(row.get("comment") or "")]
            found = self._one_comment(matches, comment, operation_id, task_id)
        except HandrailError as exc:
            if exc.uncertain or exc.code in {"VIKUNJA_OPERATION_CONFLICT", "VIKUNJA_MARKER_AMBIGUOUS"}:
                raise
            raise HandrailError(
                "VIKUNJA_WRITE_UNCERTAIN",
                "comment may have been created; readback failed",
                details={"operation_id": operation_id, "task_id": task_id},
                retryable=False,
                uncertain=True,
            ) from exc
        if found is None:
            raise HandrailError(
                "VIKUNJA_WRITE_UNCERTAIN",
                "comment write was not confirmed and was not sent again",
                details={"operation_id": operation_id, "task_id": task_id},
                retryable=False,
                uncertain=True,
            ) from original
        return found
