"""Separate internal Review, board delivery and the coordinator's user report."""
from handrail.shared.errors import HandrailError
from handrail.shared.identity import now


def preview(app, plan_id):
    plan = app.store.read("plan", plan_id)
    if not plan:
        raise HandrailError("NOT_FOUND", "Unknown Plan")
    submission = plan.get("submission")
    if not submission:
        return {"plan_id": plan_id, "ready": False, "next": "Complete integration and criterion evidence before Plan Review"}
    card = app.store.read("board_card", plan_id)
    pending = [r["key"] for r in app.store.outbox("board") if r["payload"].get("entity_id") == plan_id and r["status"] != "complete"]
    notice = app.store.read("review_notice", submission["id"])
    from handrail.setup.settings import connection
    url = connection(app.config["profile"])["url"] + "/tasks/" + str(card["task_id"]) if card else None
    reports = [r for r in app.store.list("worker_submission") if r["plan_id"] == plan_id and
               r["cycle"] == plan["cycle"] and r.get("verdict") == "accept"]
    return {"plan_id": plan_id, "submission_id": submission["id"], "ready": plan["state"] in ("review", "done"),
            "internal_state": plan["state"], "board_state": card.get("state") if card else None,
            "board_delivery": "pending" if pending or not card else "complete", "pending_events": pending,
            "card_url": url, "user_report": notice or {"status": "pending"},
            "draft": {"title": plan["title"], "revision": plan["revision"],
                      "outcomes": [r["report"]["summary"] for r in reports],
                      "worker_unverified": [item for r in reports for item in r["report"]["unverified"]],
                      "request": "Review the implementation and tell the coordinator whether to accept this Plan"},
            "next": "Send the outcome, Review URL and limitations to the user; then coordinator report PLAN --message ACTUAL_REPORT"}


def acknowledge(app, plan_id, message):
    if not isinstance(message, str) or not message.strip():
        raise HandrailError("REPORT_EVIDENCE_REQUIRED", "Record the actual user-facing report after sending it")
    value = preview(app, plan_id)
    if not value["ready"]:
        raise HandrailError("REVIEW_NOT_SUBMITTED", "Submit Plan Review before recording its user report")
    record = {"id": value["submission_id"], "plan_id": plan_id, "message": message,
              "status": "reported", "reported_at": now(), "board_delivery_at_report": value["board_delivery"],
              "source": "coordinator attestation; not host delivery telemetry"}
    previous = app.store.read("review_notice", record["id"])
    if previous and previous["message"] == message:
        return previous
    with app.store.transaction() as tx:
        tx.put("review_notice", record["id"], record)
        tx.event(plan_id, "plan.user_reported", record)
    return record
