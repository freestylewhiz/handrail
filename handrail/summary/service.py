"""Board-owned summaries, durable hash-only delivery intents and context references."""
import json
import re
from urllib.parse import urlsplit
from handrail.shared.errors import HandrailError
from handrail.shared.identity import digest, now
from handrail.interfaces.vikunja.board import marked_description
from handrail.interfaces.vikunja.projects import VikunjaProjects
from . import format as fmt
from . import issues


class SummaryService:
    def __init__(self, store, config, board):
        self.store, self.config, self.board = store, config, board
        self.client = board.client
        self.api = VikunjaProjects(self.client)

    def plan_id(self, selection):
        selection = str(selection)
        if self.store.read("plan", selection):
            return selection
        if selection.startswith(("http://", "https://")):
            link, base = urlsplit(selection), urlsplit(self.client.url)
            if (link.scheme, link.netloc) != (base.scheme, base.netloc):
                raise HandrailError("SUMMARY_SERVER_MISMATCH", "Use a card ID or the connected server's URL")
            match = re.fullmatch(re.escape(base.path.rstrip("/")) + r"/tasks/(\d+)/?", link.path)
            selection = match.group(1) if match else ""
        found = [c["id"] for c in self.store.list("board_card") if str(c["task_id"]) == selection and self.store.read("plan", c["id"])]
        if len(found) != 1:
            raise HandrailError("PLAN_SELECTION_REQUIRED", "Choose a managed plan ID or its card ID")
        return found[0]

    def marker(self, plan_id):
        return f"[Handrail summary workspace={self.config['workspace_id']} plan={plan_id}]"

    def _find(self, plan_id):
        marker = self.marker(plan_id)
        rows = self.api.tasks(self.board.project_id)
        found = [r for r in rows if marker in (r.get("description") or "")]
        if len(found) > 1:
            raise HandrailError("SUMMARY_AMBIGUOUS", "Multiple Summary cards claim this plan", details={"card_ids": [r["id"] for r in found]})
        if found:
            mapping = self.store.read("summary_card", plan_id)
            if mapping and mapping["card_id"] != found[0]["id"]:
                raise HandrailError("SUMMARY_IDENTITY_CHANGED", "Summary marker now points to a different card")
            card = self.board.get_task(found[0]["id"])
            ctx, _ = fmt.parse(card["description"])
            if (ctx.get("plan_id"), ctx.get("workspace_id")) != (plan_id, self.config["workspace_id"]):
                raise HandrailError("SUMMARY_SCOPE_MISMATCH", "Summary marker and context identity disagree")
            return card
        mapping = self.store.read("summary_card", plan_id)
        if mapping:
            raise HandrailError("SUMMARY_CARD_MISSING", "Mapped Summary was moved, deleted or edited; inspect before creating another card",
                                details={"card_id": mapping["card_id"]})
        return None

    def _source(self, plan_id):
        plan = self.store.read("plan", plan_id)
        if not plan:
            raise HandrailError("NOT_FOUND", "Unknown plan")
        works = [self.store.read("work", i) for i in plan["work_ids"]]
        work = [{k: w.get(k) for k in ("id", "title", "cycle", "criteria", "evidence", "review", "revision", "completion")} for w in works]
        source = {"plan_id": plan_id, "title": plan["title"], "cycle": plan["cycle"], "revision": plan["revision"],
                  "criteria": plan["criteria"], "evidence": plan["evidence"], "work": work,
                  "last_reopen": plan.get("last_reopen"),
                  "previous_cycles": [{k: c.get(k) for k in ("cycle", "revision", "criteria", "evidence")} for c in plan.get("cycles", [])]}
        refs = [self.store.read("instruction_reference", identity) for identity in [plan_id] + plan["work_ids"]]
        # Old plans without this feature keep their existing Summary fingerprint.
        if any(refs):
            source["instructions"] = [{k: r[k] for k in ("id", "references", "fingerprint", "reason")} for r in refs if r]
        submissions = [r for r in self.store.list("worker_submission") if r["plan_id"] == plan_id and r["cycle"] == plan["cycle"] and
                       r["delivery"] in ("received", "processed")]
        if submissions:
            source["worker_submissions"] = [{k: r[k] for k in ("id", "work_id", "attempt_id", "commit", "report", "delivery")} for r in submissions]
        return plan, source, digest(source)

    def _sources(self, plan):
        result = []
        for identity in [plan["id"]] + plan["work_ids"]:
            mapping = self.store.read("board_card", identity)
            if mapping:
                result.append({"entity_id": identity, "card_id": mapping["task_id"],
                               "url": self.client.url + "/tasks/" + str(mapping["task_id"])})
        if not result or result[0]["entity_id"] != plan["id"]:
            raise HandrailError("SUMMARY_SOURCE_CARD_REQUIRED", "Synchronize the plan card first", details={"next": "handrail sync --topic board"})
        return result

    def prepare(self, selection, language="en", language_name=None):
        plan_id = self.plan_id(selection)
        plan, source, fingerprint = self._source(plan_id)
        current = self._find(plan_id)
        content = fmt.content_from(current["description"]) if current else {
            "schema_version": 2,
            "language": language, "language_name": language_name or {"en": "English", "ko": "한국어"}.get(language, language),
            "sections": {lang: {field: "" for field in fmt.FIELDS + (fmt.ISSUE_FIELD,)} for lang in dict.fromkeys(("en", language))},
            "agent_context": {"scope": [], "decisions": [], "rules": [], "avoid": [], "considerations": [], "verification": {},
                              "handrail_issues": issues.template()}}
        reports = []
        for attempt in self.store.list("attempt"):
            if attempt["plan_id"] == plan_id and attempt.get("observation_id"):
                observed = self.store.read("observation", attempt["observation_id"])
                if observed:
                    reports.append({"work_id": attempt["work_id"], "cycle": attempt["cycle"],
                                    "observation_id": observed["id"], "observed_at": observed["observed_at"],
                                    "worker_report": observed["text"], "authority": "untrusted_observation"})
        return {"plan_id": plan_id, "source_fingerprint": fingerprint, "expected_hash": digest(current["description"]) if current else None,
                "content": content, "sources": self._sources(plan), "source_records": source, "worker_reports": reports,
                "execution_evidence": self._execution_evidence(plan), "issue_guidance": issues.guidance(),
                "current_card_description": current["description"] if current else None,
                "workflow_state": plan["state"], "next": "Complete both narrative sections from evidence; summary publish PLAN --file FILE --reason REASON",
                "instructions": "Separate requirement-driven project results from Handrail execution issues. "
                                "Record worker intent only when evidenced; label recommendations and unknowns. "
                                "Preserve legacy card content until the author explicitly separates it using schema 2. "
                                "Do not copy a superseded decision as current or treat execution observations as policy or a backlog."}

    def _execution_evidence(self, plan):
        """Bounded references for author investigation, not inferred incident reports."""
        attempts = [a for a in self.store.list("attempt") if a["plan_id"] == plan["id"] and a["cycle"] == plan["cycle"]]
        entities = {plan["id"], *plan["work_ids"], *(a["id"] for a in attempts)}
        operations = []
        for op in self.store.list("operation"):
            request = op.get("request", {})
            if request.get("cycle", plan["cycle"]) != plan["cycle"]:
                continue
            if not any(request.get(key) in entities for key in ("plan_id", "entity", "attempt_id")):
                continue
            if not op.get("error") and op.get("status") not in ("rejected", "failed", "unknown", "sending"):
                continue
            operations.append({"operation_id": op["id"], "action": op["action"], "status": op["status"],
                               "at": op.get("created_at"), "error_code": (op.get("error") or {}).get("error"),
                               "reference": "operation:" + op["id"]})
        events = [{"event_id": e["id"], "entity": e["entity"], "at": e["at"], "kind": e["kind"],
                   "reference": "event:" + e["id"]} for e in self.store.history()
                  if e["entity"] in entities and ("recover" in e["kind"] or "fail" in e["kind"] or "reconcil" in e["kind"])]
        return {"authority": "untrusted_observation_references", "operations": operations[-50:], "events": events[-50:],
                "truncated": len(operations) > 50 or len(events) > 50,
                "coverage": "Selected local operation errors and recovery events only; absence does not prove no issues. "
                            "Inspect relevant history and session reports; do not copy secrets or full terminal output into the Summary."}

    def _context(self, plan, fingerprint, version, status):
        return {"schema_version": 1, "type": "summary", "summary_revision": version,
                "workspace_id": self.config["workspace_id"], "plan_id": plan["id"], "cycle": plan["cycle"],
                "source_revision": plan["revision"], "source_fingerprint": fingerprint,
                "record_status": status, "workflow_state": plan["state"],
                "completion_basis": "user_acceptance" if plan.get("acceptance") else "not_accepted",
                "acceptance_id": (plan.get("acceptance") or {}).get("id"), "sources": self._sources(plan)}

    def _put(self, kind, key, value):
        with self.store.transaction() as tx:
            tx.put(kind, key, value)

    def _effect(self, key, plan_id, request, observe, write):
        """Secondary writes also use hash-only intents and readback reconciliation."""
        with self.store.transaction() as tx:
            op = tx.intent(key, "summary.effect", dict(request, plan_id=plan_id, server=self.client.url, board_id=self.board.project_id))
        if observe():
            op.update(status="complete", completed_at=now())
            self._put("operation", key, op)
            return
        if op["status"] in ("sending", "unknown", "complete"):
            raise HandrailError("SUMMARY_WRITE_UNCERTAIN", "Inspect the Summary effect before retrying", details={"operation_id": key}, uncertain=True)
        op.update(status="sending")
        self._put("operation", key, op)
        try:
            write()
            if not observe():
                raise HandrailError("SUMMARY_WRITE_UNCERTAIN", "Summary effect was not confirmed", uncertain=True)
        except Exception as exc:
            definite = isinstance(exc, HandrailError) and not exc.uncertain and exc.code.startswith("VIKUNJA_HTTP_4")
            op.update(status="rejected" if definite else "unknown")
            self._put("operation", key, op)
            raise
        op.update(status="complete", completed_at=now())
        self._put("operation", key, op)

    def _comment(self, plan_id, card_id, text, key):
        self._effect(key, plan_id, {"kind": "comment", "card_id": card_id, "text_hash": digest(text)},
                     lambda: self.board.find_comment(card_id, key, text),
                     lambda: self.board.ensure_comment(card_id, text, key))

    def _write(self, plan, content, context, current, reason, expected_hash):
        if not isinstance(reason, str) or not reason.strip():
            raise HandrailError("SUMMARY_REASON_REQUIRED", "Record why this version is being published")
        create_op = "summary-create:" + digest({"workspace": self.config["workspace_id"], "plan": plan["id"]})
        body = fmt.render(content, context, self.marker(plan["id"]))
        description = marked_description(body, create_op)
        target_hash = digest(description)
        if (not current or digest(current["description"]) != target_hash) and (digest(current["description"]) if current else None) != expected_hash:
            raise HandrailError("SUMMARY_EDIT_CONFLICT", "Card changed; prepare again and preserve the user's edits")
        operation_id = "summary-write:" + digest({"plan": plan["id"], "from": expected_hash, "to": target_hash})
        request = {"plan_id": plan["id"], "server": self.client.url, "board_id": self.board.project_id,
                   "expected_hash": expected_hash, "target_hash": target_hash, "version": context["summary_revision"],
                   "cycle": context["cycle"], "source_fingerprint": context["source_fingerprint"], "reason": reason}
        with self.store.transaction() as tx:
            pending = [op for op in tx.list("operation") if op["action"] == "summary.write" and op["request"]["plan_id"] == plan["id"]
                       and op["id"] != operation_id and op["status"] not in ("complete", "cancelled")]
            if pending:
                raise HandrailError("SUMMARY_WRITE_PENDING", "Reconcile the previous summary write first", details={"operation_id": pending[0]["id"]})
            operation = tx.intent(operation_id, "summary.write", request)
        matches_target = current and digest(current["description"]) == target_hash
        if not matches_target:
            if (digest(current["description"]) if current else None) != expected_hash:
                raise HandrailError("SUMMARY_EDIT_CONFLICT", "Card changed; prepare again and preserve the user's edits")
            if operation["status"] in ("sending", "unknown"):
                raise HandrailError("SUMMARY_WRITE_UNCERTAIN", "Inspect and resolve before retrying", details={"operation_id": operation_id}, uncertain=True)
            if current:
                # The previous full version is archived remotely, never in the local intent.
                self._comment(plan["id"], current["task_id"], "Summary revision archive\nReason: " + reason + "\n\n" + current["description"], operation_id + ":archive")
                if self.board.get_task(current["task_id"])["description"] != current["description"]:
                    raise HandrailError("SUMMARY_EDIT_CONFLICT", "Card changed during archival; inspect before writing")
            operation.update(status="sending")
            self._put("operation", operation_id, operation)
            try:
                if current:
                    observed = self.board.replace_description(current["task_id"], description, current["description"])
                else:
                    observed = self.board.create_task("[Summary] " + plan["title"], body, create_op)
                if digest(observed["description"]) != target_hash:
                    raise HandrailError("SUMMARY_WRITE_UNCERTAIN", "Readback differs; inspect before retrying", uncertain=True)
            except Exception as exc:
                definite = isinstance(exc, HandrailError) and not exc.uncertain and exc.code.startswith("VIKUNJA_HTTP_4")
                operation.update(status="rejected" if definite else "unknown")
                self._put("operation", operation_id, operation)
                raise
        else:
            observed = current
        result = {"id": plan["id"], "card_id": observed["task_id"], "url": self.client.url + "/tasks/" + str(observed["task_id"]),
                  "version": context["summary_revision"], "cycle": context["cycle"], "content_hash": target_hash,
                  "source_fingerprint": context["source_fingerprint"], "record_status": context["record_status"]}
        with self.store.transaction() as tx:
            operation.update(status="complete", result=result, completed_at=now())
            tx.put("operation", operation_id, operation)
            tx.put("summary_card", plan["id"], result)
            tx.event(plan["id"], "summary.published", result)
        return result

    def publish(self, selection, payload, reason):
        plan_id = self.plan_id(selection)
        with self.store.exclusive("outbox-delivery"), self.store.exclusive("agentroom-mutation"):
            plan, _, fingerprint = self._source(plan_id)
            if payload.get("source_fingerprint") != fingerprint:
                raise HandrailError("SUMMARY_SOURCE_CHANGED", "Prepare from the current cycle and evidence before publishing")
            content = fmt.validate(payload.get("content"))
            current = self._find(plan_id)
            previous = fmt.parse(current["description"])[0] if current else {}
            # Repeated identical publication does not create another revision.
            if current and previous.get("source_fingerprint") == fingerprint and fmt.content_from(current["description"]) == content:
                return self._reconcile_current(plan, current)
            version = previous.get("summary_revision", 0) + 1
            status = "accepted" if plan.get("acceptance") and plan["state"] == "done" else "draft"
            context = self._context(plan, fingerprint, version, status)
            # A retry uses the original target version stored in its hash-only intent.
            for op in self.store.list("operation"):
                if op["action"] == "summary.write" and op["request"]["plan_id"] == plan_id and op["status"] not in ("complete", "cancelled"):
                    context["summary_revision"] = op["request"]["version"]
            result = self._write(plan, content, context, current, reason, payload.get("expected_hash"))
            self._place(plan, result)
            return result

    def _reconcile_current(self, plan, current, place=True):
        context = fmt.parse(current["description"])[0]
        result = {"id": plan["id"], "card_id": current["task_id"], "url": self.client.url + "/tasks/" + str(current["task_id"]),
                  "version": context["summary_revision"], "cycle": context["cycle"], "content_hash": digest(current["description"]),
                  "source_fingerprint": context["source_fingerprint"], "record_status": context["record_status"]}
        with self.store.transaction() as tx:
            for op in tx.list("operation"):
                if op["action"] == "summary.write" and op["request"]["plan_id"] == plan["id"] and op["request"]["target_hash"] == result["content_hash"]:
                    op.update(status="complete", result=result, completed_at=now())
                    tx.put("operation", op["id"], op)
            tx.put("summary_card", plan["id"], result)
        if place:
            self._place(plan, result)
        return result

    def _place(self, plan, result):
        from handrail.board.labels import TypeLabels
        TypeLabels(self.client).ensure(result["card_id"], "summary")
        card = self.board.get_task(result["card_id"])
        target = "done" if result["record_status"] == "accepted" else "review"
        if card["state"] != target:
            self._effect(f"summary-move:{card['task_id']}:{result['version']}", plan["id"],
                         {"kind": "move", "card_id": card["task_id"], "target": target},
                         lambda: self.board.get_task(card["task_id"])["state"] == target,
                         lambda: self.board.move_task(card["task_id"], target, expected_state=card["state"]))
        source = self._sources(plan)[0]
        self._comment(plan["id"], source["card_id"], "Summary: " + result["url"] + "\nRecord type: summary; separate from implementation work.",
                      "summary-link:" + plan["id"])

    def lifecycle(self, item):
        plan_id = item["payload"]["entity_id"]
        with self.store.exclusive("agentroom-mutation"):
            plan, _, fingerprint = self._source(plan_id)
            current = self._find(plan_id)
            if not current:
                if plan["state"] != "done":
                    return {"status": "no_summary", "plan_id": plan_id}
                raise HandrailError("SUMMARY_CONTENT_REQUIRED", "Coordinator must synthesize and publish the Summary; acceptance is already recorded",
                                    details={"plan_id": plan_id, "next": "handrail summary prepare PLAN --language USER_LANGUAGE"})
            previous = fmt.parse(current["description"])[0]
            status = ("accepted" if plan["state"] == "done" and plan.get("acceptance") else
                      "draft" if previous.get("source_fingerprint") == fingerprint else "stale")
            if status == "accepted" and (previous.get("cycle") != plan["cycle"] or previous.get("source_fingerprint") != fingerprint):
                raise HandrailError("SUMMARY_CONTENT_REQUIRED", "Update the Summary from current cycle evidence", details={"plan_id": plan_id})
            if previous.get("record_status") == status:
                return self._reconcile_current(plan, current)
            mapping = self.store.read("summary_card", plan_id)
            if mapping and mapping["content_hash"] != digest(current["description"]):
                # A crashed write already visible remotely is reconciled, not overwritten.
                pending = [op for op in self.store.list("operation") if op["action"] == "summary.write" and
                           op["request"]["plan_id"] == plan_id and op["request"]["target_hash"] == digest(current["description"])]
                if pending:
                    return self._reconcile_current(plan, current)
                raise HandrailError("SUMMARY_EDIT_CONFLICT", "Summary has external edits; prepare and preserve them before lifecycle update")
            context = dict(previous, record_status=status, summary_revision=previous["summary_revision"] + 1,
                           workflow_state=plan["state"], completion_basis="user_acceptance" if status == "accepted" else "historical",
                           acceptance_id=(plan.get("acceptance") or {}).get("id"))
            result = self._write(plan, fmt.content_from(current["description"]), context, current,
                                 "Workflow lifecycle: " + status, digest(current["description"]))
            self._place(plan, result)
            return result

    def read(self, card_id, language="agent", fields=None):
        card = self.board.get_task(int(card_id))
        context, _ = fmt.parse(card["description"])
        if context.get("workspace_id") != self.config["workspace_id"]:
            raise HandrailError("SUMMARY_SCOPE_MISMATCH", "Summary belongs to another repository context")
        content = fmt.select(card["description"], language, fields)
        status = self._effective_status(context)
        if language == "agent":
            content = dict(content, stored_record_status=context["record_status"], record_status=status)
        return {"card_id": int(card_id), "version": context["summary_revision"], "content_hash": digest(card["description"]),
                "record_status": status, "language": language, "content": content}

    def _effective_status(self, context):
        plan = self.store.read("plan", context.get("plan_id", ""))
        if plan:
            _, _, fingerprint = self._source(plan["id"])
            if context.get("source_fingerprint") != fingerprint:
                return "stale"
            if context.get("record_status") == "accepted" and not (plan["state"] == "done" and plan.get("acceptance")):
                return "stale"
        return context["record_status"]

    def list(self, query=None, include_stale=False, issues_only=False):
        rows = self.api.tasks(self.board.project_id)
        result = []
        terms = set(re.findall(r"\w+", (query or "").casefold()))
        for row in rows:
            if f"[Handrail summary workspace={self.config['workspace_id']} " not in (row.get("description") or ""):
                continue
            try:
                ctx, _ = fmt.parse(row["description"])
            except HandrailError:
                result.append({"card_id": row["id"], "title": row["title"], "status": "format_invalid"})
                continue
            ctx["record_status"] = self._effective_status(ctx)
            if not include_stale and ctx["record_status"] != "accepted":
                continue
            execution_issues = fmt.issue_knowledge(ctx)
            if issues_only and execution_issues["assessment"] != "observed":
                continue
            scope = fmt.project_knowledge(ctx).get("scope", [])
            searchable = execution_issues if issues_only else scope
            text = (row["title"] + " " + json.dumps(searchable, ensure_ascii=False)).casefold()
            score = sum(word in text for word in terms)
            if terms and not score:
                continue
            result.append({"card_id": row["id"], "title": row["title"], "plan_id": ctx["plan_id"],
                           "version": ctx["summary_revision"], "status": ctx["record_status"], "scope": scope,
                           "issue_assessment": execution_issues["assessment"], "issue_count": len(execution_issues["items"]),
                           "score": score, "url": self.client.url + "/tasks/" + str(row["id"])})
        return sorted(result, key=lambda row: (-row.get("score", 0), row["card_id"]))

    def use(self, entity_id, card_id, fields, reason):
        entity = self.store.read("plan", entity_id) or self.store.read("work", entity_id)
        if not entity:
            entity_id = self.plan_id(entity_id)
            entity = self.store.read("plan", entity_id)
        if not reason or not reason.strip():
            raise HandrailError("SUMMARY_REASON_REQUIRED", "Record why this history applies")
        value = self.read(card_id)
        context = value["content"]
        if context["record_status"] != "accepted":
            raise HandrailError("SUMMARY_NOT_CURRENT", "Use an accepted Summary or inspect its source before proceeding")
        fields = list(dict.fromkeys(fields or ("decisions", "rules", "avoid", "considerations", "verification")))
        self.read(card_id, "en", fields)
        record = {"id": entity_id + ":" + str(card_id), "entity_id": entity_id, "cycle": entity["cycle"],
                  "card_id": int(card_id), "version": value["version"], "content_hash": value["content_hash"],
                  "fields": fields, "reason": reason, "at": now()}
        with self.store.transaction() as tx:
            tx.put("summary_reference", record["id"], record)
            tx.event(entity_id, "summary.consulted", record)
        return record

    def worker_context(self, work_id):
        work = self.store.read("work", work_id)
        if not work:
            raise HandrailError("NOT_FOUND", "Unknown work")
        refs = [r for r in self.store.list("summary_reference") if r["entity_id"] in (work_id, work["plan_id"]) and r["cycle"] == work["cycle"]]
        result = []
        for ref in refs:
            value = self.read(ref["card_id"])
            if value["version"] != ref["version"] or value["content_hash"] != ref["content_hash"] or value["content"]["record_status"] != "accepted":
                raise HandrailError("SUMMARY_REFERENCE_STALE", "Re-read changed history and record a new summary use before worker startup", details={"card_id": ref["card_id"]})
            result.append({"card_id": ref["card_id"], "version": ref["version"], "reason": ref["reason"],
                           "scope": fmt.project_knowledge(value["content"]).get("scope"), "sources": value["content"]["sources"],
                           "sections": self.read(ref["card_id"], "en", ref["fields"])["content"]})
        return result

    def resolve(self, operation_id, evidence):
        if not evidence or not evidence.strip():
            raise HandrailError("EVIDENCE_REQUIRED", "Record inspection of the previous write")
        with self.store.exclusive("outbox-delivery"):
            op = self.store.read("operation", operation_id)
            if not op or op["action"] not in ("summary.write", "summary.effect"):
                raise HandrailError("NOT_FOUND", "Unknown Summary write")
            request = op["request"]
            if (request["server"], request["board_id"]) != (self.client.url, self.board.project_id):
                raise HandrailError("SUMMARY_SCOPE_MISMATCH", "Operation belongs to another server/board")
            if op["action"] == "summary.effect":
                card = self.board.get_task(request["card_id"])
                if request["kind"] == "comment":
                    observed = self.board.find_comment(request["card_id"], operation_id)
                    if observed:
                        original_text = observed["comment"].split("\n", 1)[1]
                        if digest(original_text) != request["text_hash"] and digest(original_text.rstrip("\n")) != request["text_hash"]:
                            raise HandrailError("SUMMARY_EDIT_CONFLICT", "Comment marker exists with different content")
                else:
                    observed = card["state"] == request["target"]
                op.update(status="complete" if observed else "retry", resolution={"at": now(), "evidence": evidence})
                self._put("operation", operation_id, op)
                return {"operation_id": operation_id, "status": op["status"], "external_writes": False, "next": "Repeat the original publication or sync command"}
            if (request["server"], request["board_id"]) != (self.client.url, self.board.project_id):
                raise HandrailError("SUMMARY_SCOPE_MISMATCH", "Operation belongs to another server/board")
            current = self._find(request["plan_id"])
            if current and digest(current["description"]) == request["target_hash"]:
                return dict(self._reconcile_current(self.store.read("plan", request["plan_id"]), current, place=False),
                            external_writes=False, next="Repeat the original publication or sync command to finish placement")
            op.update(status="cancelled", resolution={"at": now(), "evidence": evidence,
                      "observed_hash": digest(current["description"]) if current else None})
            self._put("operation", operation_id, op)
            return {"operation_id": operation_id, "status": "cancelled", "external_writes": False,
                    "next": "Prepare again, preserve the current card, then publish with the new expected_hash"}
