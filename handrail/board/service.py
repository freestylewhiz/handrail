"""Administrative board use cases, independent of workflow execution."""
from handrail.setup.settings import context
from handrail.setup.onboarding import client_for, setup_store
from handrail.shared.errors import HandrailError
from handrail.shared.identity import digest, now
from .catalog import BoardCatalog
from .provisioning import Provisioner


class BoardService:
    def __init__(self, repo="."):
        ctx = context(repo)
        self.store, self.config = ctx["store"], ctx["config"]
        self.client = client_for(self.config["profile"])
        self.catalog = BoardCatalog(self.client, self.config, self.store)
        self.provision = Provisioner(self.client, setup_store())

    def list(self):
        return {"parent_board_id": self.config["project_id"], "boards": self.catalog.boards()}

    def _save(self, remote, mapping, kind):
        value = dict(mapping, id=str(remote["id"]), name=remote["title"],
                     parent_board_id=remote.get("parent_project_id") or None,
                     root_board_id=self.config["project_id"], url=self.catalog.url("projects", remote["id"]))
        with self.store.transaction() as tx:
            old = tx.get("managed_board", value["id"])
            if old != value:
                tx.put("managed_board", value["id"], value)
                tx.event("board:" + value["id"], kind, {"before": old, "after": value})
        return value

    def add(self, names, reuse_existing=False):
        if not names or any(not isinstance(n, str) or not n.strip() or len(n.strip()) > 250 for n in names):
            raise HandrailError("BOARD_NAME_INVALID", "Supply board names of 1 to 250 characters")
        names = list(dict.fromkeys(n.strip() for n in names))
        results = []
        with self.store.exclusive("outbox-delivery"):
            parent = self.catalog.select()
            self.catalog.api.require_write(parent["id"])
            for name in names:
                try:
                    key = "board:" + self.config["workspace_id"] + ":" + digest({"parent": parent["id"], "name": name})
                    marker = self.provision.project_marker(key)
                    rows = self.catalog.api.projects()
                    owned = [p for p in rows if marker in (p.get("description") or "")]
                    matches = [p for p in rows if p.get("parent_project_id") == parent["id"]
                               and p["title"] == name and not p.get("is_archived")]
                    registered = [p for p in matches if self.store.read("managed_board", str(p["id"]))]
                    if not owned and matches:
                        if len(matches) != 1 or (not registered and not reuse_existing):
                            raise HandrailError("BOARD_EXISTS", "Choose whether to use an existing board or supply a different name",
                                                details={"choices": [{"id": p["id"], "name": p["title"],
                                                         "url": self.catalog.url("projects", p["id"])} for p in matches],
                                                         "next": "Use board register BOARD, or board add NAME --reuse-existing"})
                        remote = matches[0]
                    else:
                        remote = self.provision.project(key, name, parent["id"])
                    if self.store.read("managed_board", str(remote["id"])):
                        self.catalog.adapter(remote["id"])
                        mapping = self.catalog.mapping(remote["id"])
                    else:
                        mapping = self.provision.board(remote["id"], review=True)
                    board = self._save(remote, mapping, "board.added")
                    results.append({"name": name, "status": "complete", "board": board})
                except HandrailError as exc:
                    results.append({"name": name, "status": "unknown" if exc.uncertain else "failed", "error": exc.as_dict()})
                    break
        return {"boards": results, "remaining": names[len(results):],
                "exit_code": 1 if any(r["status"] != "complete" for r in results) else 0}

    def register(self, selection, view=None, states=None):
        with self.store.exclusive("outbox-delivery"):
            row = self.catalog.select(selection)
            if row["id"] == self.config["project_id"]:
                raise HandrailError("BOARD_ALREADY_BOUND", "Use the existing parent board mapping")
            pinned = self.store.read("managed_board", str(row["id"]))
            legacy = next((b for b in self.store.list("child_board") if b["project_id"] == row["id"]), None)
            assigned = next((b for kind in ("board_card", "board_target") for b in self.store.list(kind)
                             if b.get("project_id") == row["id"]), None)
            pinned = pinned or legacy or assigned
            if pinned:
                adapter = self.catalog.adapter(row["id"])
                if view is not None and str(view) != str(adapter.view_id):
                    raise HandrailError("BOARD_MAPPING_PINNED", "Existing board mapping is pinned")
                if states and any(str(v) != str(adapter.states.get(k)) for k, v in states.items()):
                    raise HandrailError("BOARD_MAPPING_PINNED", "Existing board columns are pinned")
                mapping = self.catalog.mapping(row["id"])
            else:
                mapping = self.provision.board(row["id"], view, states, review=bool(states and "review" in states))
            return self._save(self.catalog.api.project(row["id"]), mapping, "board.registered")

    def assign(self, entity_id, selection):
        with self.store.exclusive("outbox-delivery"):
            entity = self.store.read("plan", entity_id) or self.store.read("work", entity_id)
            if not entity:
                raise HandrailError("NOT_FOUND", "Select a local Plan or Work")
            row = self.catalog.select(selection)
            adapter = self.catalog.adapter(row["id"])
            card = self.store.read("board_card", entity_id)
            if entity["kind"] == "work" and card:
                current, _, _ = self.catalog.card(entity_id)
                if current.project_id != adapter.project_id or current.view_id != adapter.view_id:
                    raise HandrailError("CARD_BOARD_PINNED", "An existing card stays on its board; assign future work instead")
            value = dict(self.catalog.mapping(row["id"]), id=entity_id, root_board_id=self.config["project_id"])
            with self.store.transaction() as tx:
                before = tx.get("board_target", entity_id)
                if before != value:
                    tx.put("board_target", entity_id, value)
                    tx.event(entity_id, "board.assigned", {"before": before, "after": value, "at": now()})
            return {"entity_id": entity_id, "board": row,
                    "applies_to": "future Work cards" if entity["kind"] == "plan" else "this Work card"}

    def history(self):
        return [row for row in self.store.history() if row["kind"].startswith(("board.", "card."))]

    def prepare_work(self, work_id):
        """Resolve a work board before its first projection or worker launch."""
        with self.store.exclusive("outbox-delivery"):
            work = self.store.read("work", work_id)
            if not work:
                raise HandrailError("NOT_FOUND", "Unknown Work")
            plan = self.store.read("plan", work["plan_id"])
            if (not plan or plan["state"] not in ("todo", "doing") or work["cycle"] != plan["cycle"] or
                not plan.get("approval") or plan["approval"]["cycle"] != plan["cycle"]):
                raise HandrailError("WORKFLOW_APPROVAL_REQUIRED", "Approve the active implementation cycle before preparing its work board")
            card = self.store.read("board_card", work_id)
            target = (card or self.store.read("board_target", work_id) or
                      self.store.read("board_target", work["plan_id"]))
            if target:
                board_id = target.get("project_id", self.config["project_id"])
                self.catalog.select(str(board_id))
                mapping = ({k: target[k] for k in ("project_id", "view_id", "states")}
                           if all(k in target for k in ("project_id", "view_id", "states")) else self.catalog.mapping(board_id))
                if "review" not in mapping["states"]:
                    mapping = self.provision.board(board_id, mapping["view_id"], mapping["states"], review=True)
                    self._save(self.catalog.api.project(board_id), mapping, "board.review_prepared")
                # A legacy card retains its exact board/view and existing columns.
                with self.store.transaction() as tx:
                    if card:
                        card.update(mapping)
                        tx.put("board_card", work_id, card)
                    else:
                        tx.put("board_target", work_id, dict(mapping, id=work_id,
                               root_board_id=self.config["project_id"]))
                return mapping
            parent = self.config["project_id"]
            registry = self.provision.store
            key = "default-work-board:" + digest({"server": self.client.url, "parent": parent})
            # Shared registry serializes all repositories bound to the same parent.
            with registry.exclusive("setup-provisioning"):
                saved = registry.read("default_board", key)
                if saved:
                    remote = self.catalog.api.project(saved["project_id"])
                    if remote.get("parent_project_id") != parent or remote.get("is_archived"):
                        raise HandrailError("BOARD_DEFAULT_CHANGED", "Registered default board moved or was archived")
                else:
                    marker = self.provision.project_marker(key)
                    rows = self.catalog.api.projects()
                    marked = [r for r in rows if marker in (r.get("description") or "")]
                    candidates = [r for r in rows if r.get("parent_project_id") == parent and
                                  r.get("title", "").casefold() == "default" and not r.get("is_archived")]
                    if len(marked) > 1 or (not marked and candidates):
                        raise HandrailError("BOARD_SELECTION_REQUIRED", "Choose one default work board",
                                            details={"choices": candidates, "requires_user_response": True,
                                                     "next": "board default BOARD --reason USER_SELECTION"})
                    remote = (marked or candidates or [None])[0]
                    if remote is None:
                        remote = self.provision.project(key, "default", parent)
                    if remote.get("parent_project_id") != parent or remote.get("is_archived"):
                        raise HandrailError("BOARD_DEFAULT_CHANGED", "Marked default board moved or was archived; select an active child explicitly")
                mapping = self.provision.board(remote["id"],
                    (saved or {}).get("view_id"), (saved or {}).get("states"), review=True)
                with registry.transaction() as tx:
                    tx.put("default_board", key, dict(mapping, id=key, parent_board_id=parent))
                self._save(remote, mapping, "board.default_prepared")
            with self.store.transaction() as tx:
                value = dict(mapping, id=work_id, root_board_id=parent)
                tx.put("board_target", work_id, value)
                tx.event(work_id, "board.assigned", {"after": value, "reason": "default work board"})
            return mapping

    def set_default(self, selection, reason):
        if not isinstance(reason, str) or not reason.strip():
            raise HandrailError("USER_SELECTION_REQUIRED", "Record the user's selected default work board")
        row = self.catalog.select(selection)
        if row["parent_board_id"] != self.config["project_id"]:
            raise HandrailError("BOARD_DEFAULT_SCOPE", "Choose an immediate child of the bound parent")
        saved = self.register(selection)
        mapping = self.provision.board(row["id"], (saved or {}).get("view_id"), (saved or {}).get("states"), review=True)
        key = "default-work-board:" + digest({"server": self.client.url, "parent": self.config["project_id"]})
        with self.provision.store.exclusive("setup-provisioning"), self.provision.store.transaction() as tx:
            previous = tx.get("default_board", key)
            tx.put("default_board", key, dict(mapping, id=key, parent_board_id=self.config["project_id"]))
            tx.event(key, "board.default_selected", {"before": previous, "after": mapping, "reason": reason})
        return {"board": self._save(self.catalog.api.project(row["id"]), mapping, "board.default_registered"),
                "applies_to": "future unassigned work only"}
