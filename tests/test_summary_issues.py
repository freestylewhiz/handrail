import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from handrail.cli import parser
from handrail.interfaces.vikunja.board import marked_description
from handrail.shared.errors import HandrailError
from handrail.shared.store import Store
from handrail.summary import format as fmt
from handrail.summary.service import SummaryService


def content(version=2, assessment="observed"):
    fields = fmt.FIELDS + (("handrail_issues",) if version == 2 else ())
    value = {"language": "ko", "sections": {lang: {k: lang + " " + k for k in fields} for lang in ("en", "ko")},
             "agent_context": {"scope": ["employee directory"], "decisions": [], "rules": [], "avoid": [],
                               "considerations": [], "verification": {}}}
    if version == 2:
        value["schema_version"] = 2
        value["agent_context"]["handrail_issues"] = {"assessment": assessment, "items": []}
        if assessment == "observed":
            value["agent_context"]["handrail_issues"]["items"] = [{
                "id": "channel-access", "stage": "recovery", "expected": "Worker can submit after recovery",
                "observed": "Report channel permission denied", "impact": "Completion handoff blocked",
                "recovery": "Applied the exact permitted channel; worker probe passed", "status": "recovered",
                "attribution": "unknown", "evidence": ["operation:recover-1"],
                "hypothesis": "New channel may be outside the applied launch scope"}]
        value["sections"]["en"]["handrail_issues"] = "channel-access: permission denied; recovered; cause unconfirmed."
        value["sections"]["ko"]["handrail_issues"] = "channel-access: 권한 거부; 작업 재개; 원인 미확정."
    return value


def context():
    return {"schema_version": 1, "type": "summary", "summary_revision": 1, "record_status": "draft",
            "cycle": 1, "plan_id": "plan", "workspace_id": "ws", "source_fingerprint": "basis",
            "sources": [{"card_id": 1, "url": "https://board.invalid/tasks/1"}]}


class FormatTests(unittest.TestCase):
    def test_languages_and_issue_selection_are_separate(self):
        value = content()
        value["sections"]["en"]["outcome"] = "<script>not HTML</script> & project only"
        html = fmt.render(value, context(), "marker")
        self.assertIn("<h2>Project results</h2>", html)
        self.assertIn("<h2>Handrail 수행 이슈</h2>", html)
        self.assertNotIn("<script>", html)
        self.assertEqual(fmt.content_from(html), fmt.validate(value))
        selected = fmt.select(html, "agent", ["handrail_issues"])
        self.assertEqual(set(selected["knowledge"]), {"handrail_issues"})
        self.assertNotIn("employee directory", json.dumps(selected))
        self.assertEqual(fmt.select(html, "ko", ["handrail_issues"]),
                         {"handrail_issues": value["sections"]["ko"]["handrail_issues"]})
        project = fmt.select(html, "agent", ["project_results"])
        self.assertNotIn("channel-access", json.dumps(project))

    def test_legacy_roundtrip_does_not_invent_issue_history(self):
        value = content(1)
        html = fmt.render(value, context(), "marker")
        self.assertEqual(fmt.content_from(html), fmt.validate(value))
        self.assertEqual(fmt.parse(html)[0]["schema_version"], 1)
        selected = fmt.select(html, "agent", ["handrail_issues"])
        self.assertEqual(selected["knowledge"]["handrail_issues"]["assessment"], "not_reviewed")
        with self.assertRaises(HandrailError):
            fmt.select(html, "ko", ["handrail_issues"])

    def test_invalid_or_unevidenced_issues_rejected(self):
        for mutation in (lambda v: v["agent_context"]["handrail_issues"].update(assessment="none_observed"),
                         lambda v: v["agent_context"]["handrail_issues"]["items"][0].update(evidence=[]),
                         lambda v: v["agent_context"]["handrail_issues"]["items"][0].update(attribution="application"),
                         lambda v: v["agent_context"]["handrail_issues"]["items"].append(
                             copy.deepcopy(v["agent_context"]["handrail_issues"]["items"][0])),
                         lambda v: v["sections"]["ko"].pop("handrail_issues")):
            value = content()
            mutation(value)
            with self.subTest(mutation=mutation), self.assertRaises(HandrailError):
                fmt.validate(value)
        for assessment in ("none_observed", "not_reviewed"):
            self.assertEqual(fmt.validate(content(assessment=assessment))["agent_context"]["handrail_issues"]["items"], [])

    def test_extra_author_text_is_not_silently_lost(self):
        html = fmt.render(content(), context(), "marker")
        modified = html.replace("<h2>Project results</h2>", "<h2>Project results</h2><p>User-added note</p>")
        with self.assertRaisesRegex(HandrailError, "Preserve text"):
            fmt.content_from(modified)

    def test_custom_language_headings(self):
        value = content()
        value.update(language="fr", language_name="Français")
        value["sections"]["fr"] = value["sections"].pop("ko")
        value["headings"] = {"fr": {k: "fr " + k for k in value["sections"]["fr"]}}
        value["project_headings"] = {"fr": "Résultats du projet"}
        html = fmt.render(value, context(), "marker")
        self.assertEqual(fmt.content_from(html), fmt.validate(value))


class MemoryBoard:
    """Only external persistence is faked; service, format and SQLite are real."""
    def __init__(self):
        self.project_id = 1
        self.client = SimpleNamespace(url="https://board.invalid")
        self.cards = {1: {"task_id": 1, "id": 1, "title": "Plan", "description": "", "state": "review"}}
        self.comments = {}

    def get_task(self, identity):
        return copy.deepcopy(self.cards[identity])

    def create_task(self, title, body, operation_id):
        identity = max(self.cards) + 1
        self.cards[identity] = {"task_id": identity, "id": identity, "title": title,
                                "description": marked_description(body, operation_id), "state": "todo"}
        return self.get_task(identity)

    def replace_description(self, identity, body, expected):
        assert self.cards[identity]["description"] == expected
        self.cards[identity]["description"] = body
        return self.get_task(identity)

    def find_comment(self, identity, operation_id, text=None):
        return self.comments.get((identity, operation_id))

    def ensure_comment(self, identity, text, operation_id):
        self.comments[(identity, operation_id)] = text

    def move_task(self, identity, target, expected_state):
        assert self.cards[identity]["state"] == expected_state
        self.cards[identity]["state"] = target


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "state.sqlite3")
        self.board = MemoryBoard()
        self.service = SummaryService(self.store, {"workspace_id": "ws"}, self.board)
        self.service.api = SimpleNamespace(tasks=lambda _: list(self.board.cards.values()))
        labels = patch("handrail.board.labels.TypeLabels.ensure")
        labels.start()
        self.addCleanup(labels.stop)
        with self.store.transaction() as tx:
            tx.put("plan", "plan", {"id": "plan", "title": "Employee directory", "state": "review", "cycle": 1,
                                     "work_ids": [], "criteria": {"ui": "Works"}, "evidence": {}, "revision": "sha"})
            tx.put("board_card", "plan", {"id": "plan", "task_id": 1})

    def publish(self, version=2):
        prepared = self.service.prepare("plan", "ko")
        prepared["content"] = content(version)
        return self.service.publish("plan", prepared, "Reviewed the evidence")

    def test_publication_replay_acceptance_search_and_worker_isolation(self):
        result = self.publish()
        self.assertEqual(self.publish(), result)
        card_id = result["card_id"]
        original = self.board.cards[card_id]["description"]
        with self.store.transaction() as tx:
            plan = tx.get("plan", "plan")
            plan.update(state="done", acceptance={"id": "approval"})
            tx.put("plan", "plan", plan)
        self.service.lifecycle({"payload": {"entity_id": "plan"}})
        final = self.board.cards[card_id]["description"]
        self.assertEqual(fmt.parse(final)[0]["record_status"], "accepted")
        self.assertEqual(fmt.issue_knowledge(fmt.parse(final)[0]), fmt.issue_knowledge(fmt.parse(original)[0]))
        self.assertTrue(any(original in text for text in self.board.comments.values()))
        self.assertEqual(self.service.list("permission", issues_only=True)[0]["issue_count"], 1)
        self.assertEqual(self.service.list("permission"), [])
        with self.store.transaction() as tx:
            tx.put("work", "work", {"id": "work", "plan_id": "plan", "cycle": 1})
        self.service.use("work", card_id, None, "Relevant implementation history")
        worker = self.service.worker_context("work")
        self.assertNotIn("channel-access", json.dumps(worker))
        self.assertEqual(worker[0]["scope"], ["employee directory"])
        self.assertEqual(self.store.list("grant"), [])
        self.assertEqual(self.store.list("instruction_write"), [])

    def test_existing_card_prepare_and_lifecycle_remain_legacy(self):
        result = self.publish(1)
        prepared = self.service.prepare("plan", "ko")
        self.assertNotIn("schema_version", prepared["content"])
        self.assertNotIn("handrail_issues", prepared["content"]["agent_context"])
        self.assertEqual(self.service.list(include_stale=True, issues_only=True), [])
        with self.store.transaction() as tx:
            plan = tx.get("plan", "plan")
            plan.update(state="done", acceptance={"id": "approval"})
            tx.put("plan", "plan", plan)
        self.service.lifecycle({"payload": {"entity_id": "plan"}})
        self.assertEqual(fmt.parse(self.board.cards[result["card_id"]]["description"])[0]["schema_version"], 1)

    def test_source_candidates_do_not_leak_payloads_or_change_verification_basis(self):
        before = self.service.prepare("plan", "ko")
        self.assertEqual(before["content"]["schema_version"], 2)
        with self.store.transaction() as tx:
            tx.put("operation", "error-1", {"id": "error-1", "action": "worker.prompt", "status": "complete",
                                             "request": {"entity": "plan", "text": "SECRET"},
                                             "error": {"error": "HERDR_STALLED", "secret": "SECRET"}})
            tx.put("operation", "unrelated", {"id": "unrelated", "action": "worker.prompt", "status": "failed",
                                               "request": {"entity": "different-plan"}})
            tx.event("plan", "worker.recovered", {"nonce": "SECRET"})
        prepared = self.service.prepare("plan", "ko")
        self.assertEqual(before["source_fingerprint"], prepared["source_fingerprint"])
        refs = prepared["execution_evidence"]
        self.assertEqual(len(refs["operations"]), 1)
        self.assertEqual(len(refs["events"]), 1)
        self.assertNotIn("SECRET", json.dumps(refs))
        self.assertEqual(prepared["content"]["agent_context"]["handrail_issues"]["assessment"], "not_reviewed")

    def test_external_edit_is_preserved(self):
        result = self.publish()
        prepared = self.service.prepare("plan", "ko")
        self.board.cards[result["card_id"]]["description"] += "<p>User edit</p>"
        prepared["content"]["sections"]["ko"]["handrail_issues"] += " Updated."
        with self.assertRaisesRegex(HandrailError, "Card changed"):
            self.service.publish("plan", prepared, "Update")
        self.assertTrue(self.board.cards[result["card_id"]]["description"].endswith("<p>User edit</p>"))

    def test_cli_exposes_issue_search_and_selective_read(self):
        args = parser().parse_args(["summary", "list", "--issues", "--include-stale", "--query", "permission"])
        self.assertTrue(args.issues)
        args = parser().parse_args(["summary", "read", "2", "--section", "handrail_issues"])
        self.assertEqual(args.language, "agent")
        self.assertEqual(args.section, ["handrail_issues"])


if __name__ == "__main__":
    unittest.main()
