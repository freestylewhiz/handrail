"""Route cards to explicitly assigned boards, retaining existing card locations."""
from handrail.shared.errors import HandrailError
from handrail.setup.onboarding import client_for
from handrail.interfaces.vikunja.board import VikunjaBoard
from .board import BoardProjection


class BoardRouter:
    def __init__(self, store, config, parent):
        self.store, self.config, self.parent = store, config, parent

    def _board(self, item, create=True):
        doc = item["payload"]["document"]
        card = self.store.read("board_card", doc["id"])
        if card and card.get("project_id"):
            binding = card
        elif doc["kind"] != "work":
            return self.parent
        else:
            legacy = self.store.read("child_board", doc["plan_id"])
            # Existing alpha.1/2/3 cards retain their original location.
            if card:
                binding = legacy if self.config.get("child_projects") else None
            else:
                binding = (self.store.read("board_target", doc["id"]) or
                           self.store.read("board_target", doc["plan_id"]) or
                           (legacy if self.config.get("child_projects") else None))
            if not binding:
                if not card:
                    raise HandrailError("BOARD_ASSIGNMENT_REQUIRED", "Prepare this Work's board before its first card",
                                        details={"work_id": doc["id"], "next": "board prepare-work WORK"})
                if self.config.get("child_projects"):
                    from handrail.setup.onboarding import setup_store
                    from handrail.shared.identity import digest
                    client = client_for(self.config["profile"])
                    key = "project:plan:" + self.config["workspace_id"] + ":" + doc["plan_id"]
                    operation = setup_store().read("operation", "setup:" + digest({"server": client.url, "key": key}))
                    if operation:
                        raise HandrailError("BOARD_LEGACY_SETUP_PENDING", "Register and assign the previously requested child board before sync",
                                            details={"operation_id": operation["id"], "plan_id": doc["plan_id"]})
                return self.parent
        root = binding.get("root_board_id", binding.get("parent_project_id", self.config["project_id"]))
        if root != self.config["project_id"]:
            raise HandrailError("BOARD_SCOPE_CHANGED", "Stored board belongs to another connection scope")
        client = client_for(self.config["profile"])
        from handrail.board.catalog import BoardCatalog
        BoardCatalog(client, self.config, self.store).select(str(binding["project_id"]))
        return VikunjaBoard(client, binding["project_id"], binding["view_id"], binding["states"])

    def __call__(self, item):
        return BoardProjection(self.store, self._board(item))(item)

    def resolve(self, event_key, evidence):
        with self.store.exclusive("outbox-delivery"):
            items = [row for row in self.store.outbox() if row["key"] == event_key and row["topic"] == "board"]
            if len(items) != 1:
                raise HandrailError("NOT_FOUND", "Unknown board event")
            return BoardProjection(self.store, self._board(items[0], create=False)).resolve(event_key, evidence)
