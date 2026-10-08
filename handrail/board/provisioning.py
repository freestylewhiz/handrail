"""Durable board preparation. Unknown writes are reconciled, never blindly repeated."""
from handrail.shared.errors import HandrailError
from handrail.shared.identity import digest, now
from handrail.interfaces.vikunja.projects import VikunjaProjects
from handrail.interfaces.vikunja.board import VikunjaBoard
from handrail.setup.interaction import choose

ALIASES = {"todo": {"todo", "to do", "backlog", "할 일", "할일"},
           "doing": {"doing", "in progress", "진행", "진행 중", "진행중"},
           "review": {"review", "in review", "검토", "검수", "리뷰"},
           "done": {"done", "completed", "완료"}}
TITLES = {"todo": "Todo", "doing": "Doing", "review": "Review", "done": "Done"}


def unfiltered(view):
    value = view.get("filter")
    if not value:
        return True
    if not isinstance(value, dict):
        return False
    presentation = {"sort_by", "order_by", "filter_include_nulls", "filter_concat", "page", "per_page", "expand"}
    return not any(v for k, v in value.items() if k not in presentation)


class Provisioner:
    def __init__(self, client, store):
        self.api, self.store = VikunjaProjects(client), store
        self.server = client.url

    def _ensure(self, key, request, find, write):
        key = "setup:" + digest({"server": self.server, "key": key})
        with self.store.exclusive("setup-provisioning"):
            with self.store.transaction() as tx:
                intent = tx.intent(key, "setup.provision", request)
            observed = find()
            if observed is not None:
                with self.store.transaction() as tx:
                    intent.update(status="complete", result=observed, completed_at=now())
                    tx.put("operation", key, intent)
                return observed
            if intent["status"] in ("sending", "unknown", "complete"):
                raise HandrailError("SETUP_WRITE_UNCERTAIN", "Inspect the previous setup write before retrying",
                                    details={"operation_id": key, "request": request,
                                             "next": "handrail setup-resolve OPERATION_ID --evidence REASON"}, uncertain=True)
            with self.store.transaction() as tx:
                intent.update(status="sending")
                tx.put("operation", key, intent)
            applied = False
            try:
                write()
                applied = True
                observed = find()
                if observed is None:
                    raise HandrailError("SETUP_READBACK_FAILED", "Creation/update was not confirmed", uncertain=True)
            except Exception as exc:
                with self.store.transaction() as tx:
                    intent.update(status="unknown" if applied or not isinstance(exc, HandrailError) or exc.uncertain else "rejected")
                    tx.put("operation", key, intent)
                if isinstance(exc, HandrailError):
                    if applied:
                        exc.uncertain = True
                    exc.details = dict(exc.details, operation_id=key, boundary="vikunja/setup")
                    if exc.code in ("VIKUNJA_HTTP_401", "VIKUNJA_HTTP_403"):
                        exc.details["next"] = "Check project write access and API token project/view/bucket scopes; retry the same command"
                raise
            with self.store.transaction() as tx:
                intent.update(status="complete", result=observed, completed_at=now())
                tx.put("operation", key, intent)
            return observed

    @staticmethod
    def _one(rows):
        if len(rows) > 1:
            raise HandrailError("SETUP_REMOTE_AMBIGUOUS", "Multiple resources match the same setup operation")
        return rows[0] if rows else None

    def project_marker(self, key):
        # Preserve existing markers so interrupted alpha.2/3 writes remain discoverable.
        return "[Handrail project " + digest({"server": self.server, "key": key}) + "]"

    def project(self, key, title, parent=0):
        if not isinstance(title, str) or not title.strip() or len(title) > 250:
            raise HandrailError("SETUP_TITLE_INVALID", "Board name must contain 1 to 250 characters")
        marker = self.project_marker(key)
        body = {"title": title.strip(), "description": marker, "parent_project_id": int(parent)}
        if parent:
            self.api.require_write(parent)
        def find():
            rows = [p for p in self.api.projects() if marker in (p.get("description") or "")]
            row = self._one(rows)
            if row and (row.get("parent_project_id", 0) != parent or row.get("title") != body["title"] or row.get("is_archived")):
                raise HandrailError("SETUP_REMOTE_CHANGED", "The marked board differs from the recorded request")
            return row
        return self._ensure("project:" + key, body, find, lambda: self.api.create_project(body))

    def board(self, project, view_selection=None, state_selection=None, review=True):
        self.api.require_write(project)
        views = [v for v in self.api.views(project) if v.get("view_kind") == "kanban"
                 and v.get("bucket_configuration_mode") == "manual" and unfiltered(v)]
        if views:
            vid = choose("view", [{"name": v["title"], "label": v["title"], "value": v["id"]} for v in views], view_selection)
        elif view_selection is not None:
            raise HandrailError("SETUP_VIEW_INVALID", "Choose an unfiltered manual Kanban view")
        else:
            body = {"title": "Handrail", "view_kind": "kanban", "bucket_configuration_mode": "manual"}
            def find_view():
                return self._one([v for v in self.api.views(project) if v.get("title") == body["title"]
                                  and v.get("view_kind") == "kanban" and v.get("bucket_configuration_mode") == "manual"
                                  and unfiltered(v)])
            vid = self._ensure(f"view:{project}", body, find_view,
                               lambda: self.api.create_view(project, body))["id"]
        view = self.api.view(project, vid)
        states, used = {}, set()
        for index, state in enumerate(("todo", "doing", "review", "done") if review else ("todo", "doing", "done")):
            buckets = self.api.buckets(project, vid)
            available = [b for b in buckets if b["id"] not in used]
            explicit = (state_selection or {}).get(state)
            pinned = view.get({"todo": "default_bucket_id", "done": "done_bucket_id"}.get(state, ""))
            hits = [b for b in available if b["id"] == pinned] if pinned else []
            if not hits:
                hits = [b for b in available if b["title"].strip().casefold() in ALIASES[state]]
            if explicit is not None or len(hits) > 1:
                selected = choose("state:" + state, [{"name": b["title"], "label": b["title"], "value": b["id"]}
                                                    for b in (available if explicit is not None else hits)], explicit)
            elif hits:
                selected = hits[0]["id"]
            else:
                body = {"title": TITLES[state], "position": (index + 1) * 65536}
                def find_bucket():
                    return self._one([b for b in self.api.buckets(project, vid) if b.get("title") == body["title"]])
                selected = self._ensure(f"bucket:{project}:{vid}:{state}", body, find_bucket,
                                        lambda: self.api.create_bucket(project, vid, body))["id"]
            if selected in used:
                raise HandrailError("SETUP_MAPPING_CONFLICT", "Each workflow state needs a different column")
            states[state] = selected
            used.add(selected)
        update = {"default_bucket_id": states["todo"], "done_bucket_id": states["done"]}
        def mapped():
            current = self.api.view(project, vid)
            return current if all(current.get(k) == v for k, v in update.items()) else None
        self._ensure(f"mapping:{project}:{vid}:" + digest(update), update, mapped,
                     lambda: self.api.update_view(project, vid, update))
        board = VikunjaBoard(self.api.client, project, vid, states)
        board.validate()
        return {"project_id": project, "view_id": vid, "states": states}


def resolve(store, operation_id, evidence):
    if not isinstance(evidence, str) or not evidence.strip():
        raise HandrailError("EVIDENCE_REQUIRED", "Record how non-application of the write was confirmed")
    with store.exclusive("setup-provisioning"), store.transaction() as tx:
        row = tx.require("operation", operation_id)
        if row["action"] != "setup.provision" or row["status"] not in ("unknown", "sending", "rejected"):
            raise HandrailError("SETUP_RESOLVE_INVALID", "Only an interrupted setup write may be resolved")
        row.update(status="prepared", resolution={"evidence": evidence, "at": now()})
        tx.put("operation", operation_id, row)
        tx.event(operation_id, "setup.reconciled", row["resolution"])
    return {"operation_id": operation_id, "next": "Run the same setup/init/sync command again", "external_writes": False}
