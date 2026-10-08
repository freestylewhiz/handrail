"""Read board scope, mappings and cards without starting agents or preparing Git."""
from urllib.parse import urlsplit
from handrail.interfaces.vikunja.projects import VikunjaProjects
from handrail.interfaces.vikunja.board import VikunjaBoard
from handrail.shared.errors import HandrailError
from .provisioning import ALIASES, unfiltered


class BoardCatalog:
    def __init__(self, client, config, store):
        self.client, self.config, self.store = client, config, store
        self.api = VikunjaProjects(client)
        self.root = config["project_id"]

    def url(self, kind, identity):
        return self.client.url + "/" + kind + "/" + str(identity)

    def identifier(self, value, kind):
        value = str(value)
        if value.startswith(("http://", "https://")):
            parsed, base = urlsplit(value), urlsplit(self.client.url)
            prefix = base.path.rstrip("/") + "/" + kind + "/"
            if (parsed.scheme, parsed.netloc) != (base.scheme, base.netloc) or not parsed.path.startswith(prefix):
                raise HandrailError("BOARD_URL_INVALID", "Use a link from the connected server")
            value = parsed.path[len(prefix):].split("/")[0]
        return int(value) if value.isdigit() and int(value) > 0 else value

    def boards(self):
        projects = self.api.projects()
        by_id = {row["id"]: row for row in projects}
        if self.root not in by_id:
            raise HandrailError("BOARD_NOT_ACCESSIBLE", "The connected parent board is unavailable")
        result = []
        for row in projects:
            current, ancestors, seen = row, [], set()
            while current and current["id"] not in seen:
                seen.add(current["id"])
                ancestors.append(current["title"])
                if current["id"] == self.root:
                    result.append({"id": row["id"], "name": row["title"],
                                   "parent_board_id": row.get("parent_project_id") or None,
                                   "path": " / ".join(reversed(ancestors)),
                                   "archived": bool(row.get("is_archived")),
                                   "url": self.url("projects", row["id"])})
                    break
                current = by_id.get(current.get("parent_project_id"))
        return sorted(result, key=lambda row: (row["path"].casefold(), row["id"]))

    def select(self, selection=None):
        value = self.root if selection is None else self.identifier(selection, "projects")
        rows = [row for row in self.boards() if not row["archived"]]
        hits = [row for row in rows if value == row["id"] or value in (row["name"], row["path"])]
        if len(hits) != 1:
            raise HandrailError("BOARD_SELECTION_REQUIRED", "Select one board inside the connected parent",
                                details={"choices": hits or rows, "requires_user_response": True})
        return hits[0]

    def mapping(self, identity):
        if identity == self.root:
            return {k: self.config[k] for k in ("project_id", "view_id", "states")}
        saved = self.store.read("managed_board", str(identity))
        if saved:
            return {k: saved[k] for k in ("project_id", "view_id", "states")}
        legacy = [row for row in self.store.list("child_board") if row["project_id"] == identity]
        if legacy:
            return {k: legacy[0][k] for k in ("project_id", "view_id", "states")}
        known = [row for kind in ("board_card", "board_target") for row in self.store.list(kind)
                 if row.get("project_id") == identity]
        mappings = []
        for row in known:
            mapping = {k: row[k] for k in ("project_id", "view_id", "states")}
            if mapping not in mappings:
                mappings.append(mapping)
        if len(mappings) == 1:
            return mappings[0]
        if mappings:
            raise HandrailError("BOARD_MAPPING_REQUIRED", "Existing cards refer to different mappings for this board")
        views = [v for v in self.api.views(identity) if v.get("view_kind") == "kanban"
                 and v.get("bucket_configuration_mode") == "manual" and unfiltered(v)]
        if len(views) != 1:
            raise HandrailError("BOARD_MAPPING_REQUIRED", "Register this board's Kanban mapping first",
                                details={"board_id": identity, "next": "handrail board register BOARD --view VIEW"})
        view = views[0]
        buckets = self.api.buckets(identity, view["id"])
        states = {}
        for state in ("todo", "doing", "review", "done"):
            pinned = view.get({"todo": "default_bucket_id", "done": "done_bucket_id"}.get(state, ""))
            hits = [b for b in buckets if b["id"] == pinned] if pinned else []
            if not hits:
                hits = [b for b in buckets if b["title"].strip().casefold() in ALIASES[state]]
            if len(hits) == 1:
                states[state] = hits[0]["id"]
            elif hits or state != "review":
                raise HandrailError("BOARD_MAPPING_REQUIRED", "Choose this board's columns with board register",
                                    details={"board_id": identity, "state": state, "columns": buckets})
        return {"project_id": identity, "view_id": view["id"], "states": states}

    def adapter(self, identity):
        mapping = self.mapping(identity)
        board = VikunjaBoard(self.client, **mapping)
        board.validate()
        return board

    def cards(self, selection=None):
        boards = [self.select(selection)] if selection is not None else [b for b in self.boards() if not b["archived"]]
        result = []
        for row in boards:
            # Listing works even for boards whose columns have not been registered.
            for task in self.api.tasks(row["id"]):
                result.append({"id": task["id"], "title": task["title"], "board_id": row["id"],
                               "board": row["path"], "done": bool(task.get("done")),
                               "buckets": task.get("buckets") or [], "url": self.url("tasks", task["id"])})
        return result

    def card(self, selection, board_selection=None):
        local = self.store.read("board_card", str(selection))
        value = local["task_id"] if local else self.identifier(selection, "tasks")
        scope = [self.select(board_selection)] if board_selection is not None else self.boards()
        if isinstance(value, int):
            task = self.api.task(value)
            hits = [row for row in scope if row["id"] == task["project_id"] and not row["archived"]]
            if len(hits) != 1:
                raise HandrailError("CARD_OUTSIDE_BOARD", "Card is outside the selected active board scope")
        else:
            matches = [row for row in self.cards(board_selection) if row["title"] == value]
            if len(matches) != 1:
                raise HandrailError("CARD_SELECTION_REQUIRED", "Choose a unique card by its link or ID",
                                    details={"choices": matches, "requires_user_response": True})
            task = self.api.task(matches[0]["id"])
            if task["project_id"] != matches[0]["board_id"]:
                raise HandrailError("CARD_OUTSIDE_BOARD", "Card moved while resolving its identity")
        board = self.adapter(task["project_id"])
        snapshot = board.get_task(task["id"])
        entities = [row["id"] for row in self.store.list("board_card") if row["task_id"] == task["id"]]
        if len(entities) > 1:
            raise HandrailError("CARD_MAPPING_CONFLICT", "Multiple local entities refer to this card")
        return board, snapshot, entities[0] if entities else None
