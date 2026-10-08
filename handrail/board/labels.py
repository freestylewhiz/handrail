"""Type labels are additive and use the shared durable remote-write journal."""
from handrail.shared.errors import HandrailError
from handrail.setup.onboarding import setup_store
from .provisioning import Provisioner

TYPES = {"plan", "task", "summary", "instruction"}


class TypeLabels:
    def __init__(self, client):
        self.client = client
        self.provision = Provisioner(client, setup_store())

    def task_labels(self, task_id):
        return self.client.pages(f"/tasks/{int(task_id)}/labels")

    def ensure(self, task_id, kind):
        if kind not in TYPES:
            raise HandrailError("CARD_TYPE_INVALID", "Choose plan, task, summary or instruction")
        with self.provision.store.exclusive("setup-provisioning"):
            attached = self.task_labels(task_id)
            conflicts = [r for r in attached if r.get("title", "").casefold() in TYPES - {kind}]
            if conflicts:
                raise HandrailError("CARD_TYPE_CONFLICT", "Resolve conflicting type labels on this card; other labels are preserved",
                                    details={"card_id": task_id, "expected": kind, "conflicts": conflicts})
            if any(r.get("title", "").casefold() == kind for r in attached):
                return {"card_id": task_id, "type": kind}
            def find_label():
                rows = [r for r in self.client.pages("/labels") if r.get("title", "").casefold() == kind]
                return self.provision._one(rows)
            label = self.provision._ensure("type-label:" + kind, {"title": kind}, find_label,
                         lambda: self.client.request("/labels", "POST", {"title": kind}))
            def find_attached():
                return next((r for r in self.task_labels(task_id) if r["id"] == label["id"]), None)
            self.provision._ensure(f"type-label:{kind}:task:{task_id}:{label['id']}",
                {"task_id": task_id, "label_id": label["id"]}, find_attached,
                lambda: self.client.request(f"/tasks/{int(task_id)}/labels", "POST", {"label_id": label["id"]}))
        return {"card_id": task_id, "type": kind}


def synchronize_managed(boards):
    """Backfill only identities already linked to local workflow records."""
    service = TypeLabels(boards.client)
    rows, results = {}, []
    for mapping in boards.store.list("board_card"):
        kind = "plan" if boards.store.read("plan", mapping["id"]) else "task" if boards.store.read("work", mapping["id"]) else None
        if kind:
            rows[mapping["task_id"]] = (kind, mapping.get("project_id"))
    for summary in boards.store.list("summary_card"):
        identity = summary["card_id"]
        if identity in rows and rows[identity][0] != "summary":
            raise HandrailError("CARD_TYPE_CONFLICT", "One remote card is linked to multiple managed types")
        rows[identity] = ("summary", boards.config["project_id"])
    allowed = {row["id"] for row in boards.catalog.boards() if not row["archived"]}
    with boards.store.exclusive("outbox-delivery"):
        for identity, (kind, pinned_board) in rows.items():
            try:
                card = boards.catalog.api.task(identity)
                if card["project_id"] not in allowed or pinned_board and card["project_id"] != pinned_board:
                    raise HandrailError("CARD_OUTSIDE_BOARD", "Managed card moved from its recorded board")
                result = service.ensure(identity, kind)
                results.append({"status": "complete", **result})
            except HandrailError as exc:
                results.append({"card_id": identity, "status": "unknown" if exc.uncertain else "failed", "error": exc.as_dict()})
        with boards.store.transaction() as tx:
            tx.event("boards", "card.types_synchronized", {"results": results})
    return {"results": results, "preserved": ["body", "state", "board", "user labels", "workflow completion"]}
