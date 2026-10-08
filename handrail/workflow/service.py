"""Transactional plan/work lifecycle, criterion evidence and board intents.

Revision strings are opaque Git revision identities supplied by the caller.
This service never runs Git, checks commands, authenticates a user, or grants
filesystem/network access. mark_integrated is an attestation from the trusted
integration boundary that the accepted candidate was integrated at that revision.

Typical work order: start -> review accept with worker commit revision ->
mark_integrated -> integrated evidence -> complete. Source work evidence is
optional for review; it is not plan verification evidence. A new integrated
revision requires fresh evidence; it does not pretend pre-integration checks
ran on the new tree. The caller must compare the live worker commit against
review.revision before executing Git integration.
Plan checks use the final revision, while completed children retain their own
integration revisions. The external Git boundary must verify their ancestry.
"""

import copy

from ..shared.identity import digest, new_id, now
from . import validation as valid


class WorkflowService:
    """Serialize domain transitions and their journal/outbox in one transaction.

    Approval strings/dicts are caller attestations, never host authorization.
    Criteria are immutable within a document. Evidence strings assert a passing
    observation; dictionaries may explicitly record failed/blocked/not_run/missing.
    Reuse creation operation IDs and execution attempt IDs when retrying.
    The execution boundary owns stale callback rejection, stopping superseded
    workers, validating actual Git revisions and checking integrated ancestry.
    """

    def __init__(self, store):
        self.store = store

    @staticmethod
    def _document(kind, title, criteria, **fields):
        timestamp = now()
        return {"id": new_id(kind + "-"), "kind": kind, "title": title,
                "state": "todo", "cycle": 1, "criteria": criteria,
                "evidence": {}, "revision": None, "verified": False,
                "verification": None, "created_at": timestamp,
                "updated_at": timestamp, **fields}

    @staticmethod
    def _load(tx, kind, identity):
        identity = valid.text(identity, kind + "_id")
        value = tx.require(kind, identity)
        if value.get("kind") != kind or value.get("id") != identity:
            valid.fail("WORKFLOW_STATE_INVALID", "Stored identity does not match its document")
        return value

    @classmethod
    def _entity(cls, tx, identity):
        identity = valid.text(identity, "entity_id")
        plan, work = tx.get("plan", identity), tx.get("work", identity)
        if bool(plan) == bool(work):
            valid.fail("WORKFLOW_ENTITY_INVALID", "Expected exactly one plan or work", entity_id=identity)
        return cls._load(tx, "plan" if plan else "work", identity)

    @staticmethod
    def _emit(tx, document, event_kind, data=None):
        """Commit state, history and one stable board intent in the caller's tx."""
        document["updated_at"] = now()
        tx.put(document["kind"], document["id"], document)
        event_data = {"entity_kind": document["kind"], "entity_id": document["id"],
                      "cycle": document["cycle"], "revision": document["revision"],
                      "state": document["state"], "data": copy.deepcopy(data or {}),
                      "document": copy.deepcopy(document)}
        event_id = tx.event(document["id"], event_kind, event_data)
        tx.enqueue("board", event_id, {**event_data, "event_id": event_id,
                   "event_kind": event_kind, "title": document["title"],
                   "plan_id": document.get("plan_id")})
        return event_id

    @staticmethod
    def _creation(tx, operation_id, action, request):
        existing = tx.get("workflow_operation", operation_id)
        fingerprint = digest({"action": action, "request": request})
        if existing and existing["fingerprint"] != fingerprint:
            valid.fail("OPERATION_CONFLICT", "Operation ID belongs to another creation request")
        return existing, fingerprint

    @staticmethod
    def _save_creation(tx, operation_id, fingerprint, document):
        tx.put("workflow_operation", operation_id,
               {"id": operation_id, "fingerprint": fingerprint, "status": "complete",
                "entity_kind": document["kind"], "entity_id": document["id"]})

    @staticmethod
    def _active(plan):
        if plan["state"] not in ("todo", "doing"):
            valid.fail("WORKFLOW_PLAN_NOT_ACTIVE", "Reopen the plan before adding or changing work")

    @staticmethod
    def _approved(plan):
        approval = plan.get("approval")
        if (not approval or approval.get("cycle") != plan["cycle"] or
                approval.get("criteria_sha256") != digest(plan["criteria"])):
            valid.fail("WORKFLOW_APPROVAL_REQUIRED", "Approve this plan cycle before starting work")

    @classmethod
    def _work_parent(cls, tx, work):
        plan = cls._load(tx, "plan", work["plan_id"])
        if work["id"] not in plan["work_ids"]:
            valid.fail("WORKFLOW_PARENT_MISMATCH", "Work is not registered under its parent plan")
        if work["cycle"] != plan["cycle"]:
            valid.fail("WORKFLOW_CYCLE_STALE", "Earlier-cycle work is immutable; create new work")
        cls._active(plan)
        cls._approved(plan)
        return plan

    @staticmethod
    def _unfinished(work):
        if work["state"] not in ("doing", "review") or not work.get("attempt_id"):
            valid.fail("WORKFLOW_WORK_NOT_ACTIVE", "Start an unfinished work attempt first")

    @classmethod
    def _invalidate_plan(cls, tx, plan, reason):
        previous = plan.get("verification")
        plan["verified"] = False
        plan["verification"] = None
        plan["updated_at"] = now()
        tx.put("plan", plan["id"], plan)
        if previous:
            cls._emit(tx, plan, "verification_invalidated", {"reason": reason, "previous": previous})

    @staticmethod
    def _require_evidence(document, revision):
        if document["revision"] != revision:
            valid.fail("WORKFLOW_REVISION_STALE", "Evidence belongs to a different revision",
                       expected=revision, observed=document["revision"])
        missing = []
        for criterion in document["criteria"]:
            row = document["evidence"].get(criterion)
            if (not row or row.get("revision") != revision or
                    row.get("cycle") != document["cycle"] or
                    row.get("criteria_sha256") != digest(document["criteria"]) or
                    row.get("observation", {}).get("status") != "passed" or
                    (document["kind"] == "work" and row.get("attempt_id") != document["attempt_id"])):
                missing.append(criterion)
        if missing:
            valid.fail("WORKFLOW_EVIDENCE_INCOMPLETE", "Every criterion needs passing evidence for this revision",
                       criteria=missing, revision=revision)

    @staticmethod
    def _review_valid(work):
        review = work.get("review") or {}
        if (review.get("verdict") != "accept" or review.get("attempt_id") != work.get("attempt_id") or
                review.get("cycle") != work["cycle"] or
                review.get("criteria_sha256") != digest(work["criteria"]) or
                not review.get("revision")):
            valid.fail("WORKFLOW_REVIEW_REQUIRED", "Accept the current work attempt before integration or completion")
        integration = work.get("integration")
        candidate = integration.get("source_revision") if integration else review["revision"]
        evidence_sha256 = (integration.get("source_evidence_sha256") if integration
                           else digest(work["evidence"] if work["revision"] == candidate else {}))
        if review["revision"] != candidate or review.get("evidence_sha256") != evidence_sha256:
            valid.fail("WORKFLOW_REVIEW_STALE", "The review belongs to a different candidate or evidence")
        return review

    @classmethod
    def _completion_valid(cls, work):
        completion = work.get("completion") or {}
        if work["state"] != "done" or not work.get("verified") or not completion:
            valid.fail("WORKFLOW_WORK_INCOMPLETE", "Every work item in this cycle must be verified Done",
                       work_id=work["id"])
        cls._require_evidence(work, work["revision"])
        review = cls._review_valid(work)
        integration = work.get("integration") or {}
        verification = work.get("verification") or {}
        if (integration.get("revision") != work["revision"] or
                integration.get("review_id") != review["id"] or
                integration.get("cycle") != work["cycle"] or
                integration.get("attempt_id") != work["attempt_id"] or
                completion.get("revision") != work["revision"] or
                completion.get("cycle") != work["cycle"] or
                completion.get("attempt_id") != work["attempt_id"] or
                completion.get("review_id") != review["id"] or
                completion.get("verified") is not True or
                completion.get("evidence_sha256") != digest(work["evidence"]) or
                completion.get("integration_id") != integration.get("id") or
                verification.get("revision") != work["revision"] or
                verification.get("evidence_sha256") != digest(work["evidence"])):
            valid.fail("WORKFLOW_COMPLETION_STALE", "Work completion no longer matches its integration and checks")
        return completion

    @classmethod
    def _current_work(cls, tx, plan):
        result = []
        for identity in plan["work_ids"]:
            work = cls._load(tx, "work", identity)
            if work["plan_id"] != plan["id"]:
                valid.fail("WORKFLOW_PARENT_MISMATCH", "Plan contains work owned by another plan")
            if work["cycle"] == plan["cycle"]:
                result.append(work)
        if not result:
            valid.fail("WORKFLOW_WORK_REQUIRED", "Create at least one work item in the current cycle")
        return result

    @classmethod
    def _plan_basis(cls, tx, plan, revision):
        cls._approved(plan)
        cls._require_evidence(plan, revision)
        children = cls._current_work(tx, plan)
        return {"cycle": plan["cycle"], "revision": revision,
                "criteria_sha256": digest(plan["criteria"]),
                "evidence_sha256": digest(plan["evidence"]),
                "approval_id": plan["approval"]["id"],
                "work": [{"work_id": work["id"], "revision": work["revision"],
                          "completion_sha256": digest(cls._completion_valid(work))}
                         for work in children]}

    @classmethod
    def _verified_plan(cls, tx, plan):
        verification = plan.get("verification")
        if not plan.get("verified") or not verification:
            valid.fail("WORKFLOW_VERIFICATION_REQUIRED", "Verify the current plan revision first")
        if verification["basis"] != cls._plan_basis(tx, plan, plan["revision"]):
            valid.fail("WORKFLOW_VERIFICATION_STALE", "Plan or child evidence changed after verification")
        return verification

    def create_plan(self, title, criteria, operation_id=None, presentation=None):
        title, criteria = valid.text(title, "title"), valid.criteria(criteria)
        from handrail.shared.presentation import validate
        presentation = validate(presentation, criteria)
        operation_id = new_id("op-") if operation_id is None else valid.text(operation_id, "operation_id")
        with self.store.transaction() as tx:
            request = {"title": title, "criteria": criteria}
            if presentation is not None:
                request["presentation"] = presentation
            old, fingerprint = self._creation(tx, operation_id, "create_plan", request)
            if old:
                return self._load(tx, "plan", old["entity_id"])
            plan = self._document("plan", title, criteria, work_ids=[], approval=None,
                                  approvals=[], submissions=[], submission=None,
                                  acceptance=None, cycles=[], last_reopen=None,
                                  operation_id=operation_id, presentation=presentation)
            self._emit(tx, plan, "plan_created", {"operation_id": operation_id})
            self._save_creation(tx, operation_id, fingerprint, plan)
            return copy.deepcopy(plan)

    def approve_plan(self, plan_id, approval):
        approval = valid.approval(approval)
        with self.store.transaction() as tx:
            plan = self._load(tx, "plan", plan_id)
            old = plan.get("approval")
            if old and old["cycle"] == plan["cycle"]:
                if old["attestation"] != approval or old["criteria_sha256"] != digest(plan["criteria"]):
                    valid.fail("OPERATION_CONFLICT", "This cycle already has a different approval")
                return plan
            self._active(plan)
            record = {"id": new_id("approval-"), "cycle": plan["cycle"],
                      "criteria_sha256": digest(plan["criteria"]),
                      "attestation": approval, "approved_at": now()}
            plan["approval"] = record
            plan["approvals"].append(copy.deepcopy(record))
            self._emit(tx, plan, "plan_approved", {"approval": record})
            return copy.deepcopy(plan)

    def create_work(self, plan_id, title, criteria, operation_id=None, presentation=None):
        plan_id, title = valid.text(plan_id, "plan_id"), valid.text(title, "title")
        criteria = valid.criteria(criteria)
        from handrail.shared.presentation import validate
        presentation = validate(presentation, criteria)
        operation_id = new_id("op-") if operation_id is None else valid.text(operation_id, "operation_id")
        with self.store.transaction() as tx:
            request = {"plan_id": plan_id, "title": title, "criteria": criteria}
            if presentation is not None:
                request["presentation"] = presentation
            old, fingerprint = self._creation(tx, operation_id, "create_work", request)
            if old:
                return self._load(tx, "work", old["entity_id"])
            plan = self._load(tx, "plan", plan_id)
            self._active(plan)
            work = self._document("work", title, criteria, cycle=plan["cycle"],
                                  plan_id=plan_id, attempt_id=None, attempts=[], review=None,
                                  reviews=[], integration=None, completion=None,
                                  operation_id=operation_id, presentation=presentation)
            plan["work_ids"].append(work["id"])
            self._invalidate_plan(tx, plan, "required_work_added")
            self._emit(tx, work, "work_created", {"operation_id": operation_id, "plan_id": plan_id})
            self._emit(tx, plan, "work_linked", {"work_id": work["id"]})
            self._save_creation(tx, operation_id, fingerprint, work)
            return copy.deepcopy(work)

    def start_work(self, work_id, attempt_id):
        attempt_id = valid.text(attempt_id, "attempt_id")
        with self.store.transaction() as tx:
            work = self._load(tx, "work", work_id)
            if work.get("attempt_id") == attempt_id:
                return work
            if any(row["id"] == attempt_id for row in work["attempts"]):
                valid.fail("WORKFLOW_ATTEMPT_STALE", "An older attempt cannot replace the current attempt")
            owner = tx.get("workflow_attempt", attempt_id)
            if owner and owner["work_id"] != work["id"]:
                valid.fail("WORKFLOW_ATTEMPT_CONFLICT", "Attempt belongs to another work item")
            plan = self._work_parent(tx, work)
            if work["state"] == "done" or work.get("integration"):
                valid.fail("WORKFLOW_WORK_IMMUTABLE", "Create new work for changes after integration")
            previous = {key: copy.deepcopy(work.get(key)) for key in
                        ("attempt_id", "revision", "evidence", "review", "integration")}
            if work["attempts"]:
                work["attempts"][-1]["status"] = "superseded"
                work["attempts"][-1]["snapshot"] = previous
                work["attempts"][-1]["ended_at"] = now()
            work.update(state="doing", attempt_id=attempt_id, revision=None,
                        evidence={}, review=None, integration=None, verified=False,
                        verification=None, completion=None, submission=None)
            work["attempts"].append({"id": attempt_id, "status": "active", "started_at": now()})
            tx.put("workflow_attempt", attempt_id, {"id": attempt_id, "work_id": work["id"]})
            self._invalidate_plan(tx, plan, "work_attempt_started")
            if plan["state"] == "todo":
                plan["state"] = "doing"
                self._emit(tx, plan, "plan_started", {"work_id": work["id"]})
            self._emit(tx, work, "work_started", {"attempt_id": attempt_id, "previous": previous})
            return copy.deepcopy(work)

    def record_evidence(self, entity_id, criterion_id, evidence, revision):
        criterion_id, revision = valid.text(criterion_id, "criterion_id"), valid.text(revision, "revision")
        observation = valid.evidence(evidence)
        with self.store.transaction() as tx:
            document = self._entity(tx, entity_id)
            # Explicit callback context must agree with the live attempt/cycle.
            # The caller must reject late callbacks that omit their identity.
            context = {"revision": revision, "cycle": document["cycle"]}
            if document["kind"] == "work":
                context["attempt_id"] = document["attempt_id"]
            for key, expected in context.items():
                if key in observation and observation[key] != expected:
                    valid.fail("WORKFLOW_EVIDENCE_STALE", "Evidence context differs from the current target",
                               field=key, expected=expected, observed=observation[key])
            if criterion_id not in document["criteria"]:
                valid.fail("WORKFLOW_CRITERION_UNKNOWN", "Evidence must name an approved criterion", criterion_id=criterion_id)
            prior = document["evidence"].get(criterion_id)
            if (prior and prior["revision"] == revision and prior["cycle"] == document["cycle"] and
                    prior["observation"] == observation):
                return document
            if document["kind"] == "work":
                plan = self._work_parent(tx, document)
                self._unfinished(document)
                if document.get("integration") and document["integration"]["revision"] != revision:
                    valid.fail("WORKFLOW_REVISION_STALE", "Integrated work requires evidence for its integration revision")
                self._invalidate_plan(tx, plan, "work_evidence_changed")
            else:
                self._active(document)
                self._approved(document)
                if document["state"] != "doing":
                    valid.fail("WORKFLOW_PLAN_NOT_STARTED", "Start work before recording plan verification evidence")
            if document["revision"] != revision:
                previous = {"revision": document["revision"], "evidence": copy.deepcopy(document["evidence"])}
                document["evidence"] = {}
                document["revision"] = revision
            else:
                previous = {"evidence": copy.deepcopy(prior)}
            if document["kind"] == "work" and not document.get("integration"):
                previous["review"] = copy.deepcopy(document.get("review"))
                document["review"] = None
            document["verified"] = False
            document["verification"] = None
            document["evidence"][criterion_id] = {
                "criterion_id": criterion_id, "revision": revision, "cycle": document["cycle"],
                "attempt_id": document.get("attempt_id"), "criteria_sha256": digest(document["criteria"]),
                "observation": observation, "recorded_at": now()}
            self._emit(tx, document, "evidence_recorded", {"criterion_id": criterion_id,
                       "evidence": document["evidence"][criterion_id], "previous": previous})
            return copy.deepcopy(document)

    def review_work(self, work_id, verdict, notes, revision=None):
        """Pin the reviewed worker commit independently of verification evidence.

        Pass the actual worker commit as revision even when source evidence is
        absent. Without it, existing source work evidence can supply the commit;
        an unchanged prior review also supports idempotent retries. Plan evidence
        never supplies a worker revision or satisfies work completion criteria.
        A different explicit commit creates a new review, preserving the old one.
        """
        verdict, notes = valid.text(verdict, "verdict"), valid.text(notes, "notes")
        if revision is not None:
            revision = valid.text(revision, "revision")
        if verdict not in ("accept", "revise", "reject"):
            valid.fail("WORKFLOW_VERDICT_INVALID", "Review verdict must be accept, revise or reject")
        with self.store.transaction() as tx:
            work = self._load(tx, "work", work_id)
            prior = work.get("review")
            candidate = revision
            if candidate is None:
                if prior:
                    candidate = prior["revision"]
                elif not work.get("integration") and work["evidence"]:
                    candidate = work["revision"]
            if verdict == "accept" and not candidate:
                valid.fail("WORKFLOW_REVISION_REQUIRED", "Supply the current worker commit revision for review acceptance")
            source_evidence = work["evidence"] if work["revision"] == candidate else {}
            evidence_sha256 = digest(source_evidence)
            # After integration, source evidence is retained by the integration
            # record; live work evidence now describes the integrated revision.
            if work.get("integration") and prior and candidate == prior["revision"]:
                evidence_sha256 = work["integration"]["source_evidence_sha256"]
            if (prior and prior["verdict"] == verdict and prior["notes"] == notes and
                    prior["attempt_id"] == work["attempt_id"] and prior["revision"] == candidate and
                    prior["evidence_sha256"] == evidence_sha256):
                return work
            plan = self._work_parent(tx, work)
            self._unfinished(work)
            if work.get("integration"):
                valid.fail("WORKFLOW_WORK_IMMUTABLE", "Review changes after integration need a new work item")
            record = {"id": new_id("review-"), "verdict": verdict, "notes": notes,
                      "cycle": work["cycle"], "attempt_id": work["attempt_id"],
                      "revision": candidate, "criteria_sha256": digest(work["criteria"]),
                      "evidence_sha256": evidence_sha256, "evidence_kind": "work_source",
                      "source_evidence_present": bool(source_evidence),
                      "reviewed_at": now()}
            work["review"] = record
            work["state"] = "review" if verdict == "accept" else "doing"
            work["reviews"].append(copy.deepcopy(record))
            submission = work.get("submission")
            if submission:
                receipt = tx.require("worker_submission", submission["id"])
                receipt.update(delivery="processed", processed_at=now(), review_id=record["id"], verdict=verdict)
                tx.put("worker_submission", receipt["id"], receipt)
            self._invalidate_plan(tx, plan, "work_review_changed")
            self._emit(tx, work, "work_reviewed", {"review": record})
            return copy.deepcopy(work)

    def mark_integrated(self, work_id, revision):
        revision = valid.text(revision, "revision")
        with self.store.transaction() as tx:
            work = self._load(tx, "work", work_id)
            old = work.get("integration")
            if old:
                if old["revision"] != revision:
                    valid.fail("OPERATION_CONFLICT", "Work already has a different integration revision")
                return work
            plan = self._work_parent(tx, work)
            self._unfinished(work)
            review = self._review_valid(work)
            integration = {"id": new_id("integration-"), "revision": revision,
                           "review_id": review["id"], "source_revision": review["revision"],
                           "source_evidence_sha256": review["evidence_sha256"],
                           "cycle": work["cycle"], "attempt_id": work["attempt_id"],
                           "integrated_at": now()}
            prior = {"revision": work["revision"], "evidence": copy.deepcopy(work["evidence"])}
            if work["revision"] != revision:
                work["evidence"] = {}
            work.update(integration=integration, revision=revision, verified=False, verification=None)
            self._invalidate_plan(tx, plan, "work_integrated")
            self._emit(tx, work, "work_integrated", {"integration": integration, "previous": prior})
            return copy.deepcopy(work)

    def complete_work(self, work_id, revision):
        revision = valid.text(revision, "revision")
        with self.store.transaction() as tx:
            work = self._load(tx, "work", work_id)
            if work["state"] == "done":
                if work["revision"] != revision:
                    valid.fail("OPERATION_CONFLICT", "Completed work belongs to a different revision")
                self._completion_valid(work)
                return work
            plan = self._work_parent(tx, work)
            self._unfinished(work)
            review = self._review_valid(work)
            integration = work.get("integration") or {}
            if (integration.get("revision") != revision or integration.get("review_id") != review["id"] or
                    integration.get("attempt_id") != work["attempt_id"]):
                valid.fail("WORKFLOW_INTEGRATION_REQUIRED", "Integrate the reviewed attempt at this revision first")
            self._require_evidence(work, revision)
            record = {"id": new_id("completion-"), "revision": revision, "cycle": work["cycle"],
                      "attempt_id": work["attempt_id"], "integration_id": integration["id"],
                      "review_id": review["id"], "evidence_sha256": digest(work["evidence"]),
                      "verified": True, "completed_at": now()}
            work.update(state="done", verified=True, completion=record,
                        verification={"revision": revision, "evidence_sha256": record["evidence_sha256"],
                                      "verified_at": record["completed_at"]})
            work["attempts"][-1].update(status="complete", ended_at=record["completed_at"])
            self._invalidate_plan(tx, plan, "work_completed")
            self._emit(tx, work, "work_completed", {"completion": record})
            return copy.deepcopy(work)

    def verify_plan(self, plan_id, revision):
        revision = valid.text(revision, "revision")
        with self.store.transaction() as tx:
            plan = self._load(tx, "plan", plan_id)
            if plan["state"] not in ("doing", "review", "done"):
                valid.fail("WORKFLOW_PLAN_NOT_STARTED", "An active plan cycle is required")
            basis = self._plan_basis(tx, plan, revision)
            previous = plan.get("verification")
            if previous and plan.get("verified") and previous["basis"] == basis:
                return plan
            if plan["state"] != "doing":
                valid.fail("WORKFLOW_VERIFICATION_STALE", "Submitted or accepted verification cannot be replaced")
            verification = {"id": new_id("verification-"), "basis": basis, "verified_at": now()}
            plan.update(verified=True, verification=verification)
            self._emit(tx, plan, "plan_verified", {"verification": verification})
            return copy.deepcopy(plan)

    def submit_review(self, plan_id):
        with self.store.transaction() as tx:
            plan = self._load(tx, "plan", plan_id)
            if plan["state"] not in ("doing", "review", "done"):
                valid.fail("WORKFLOW_PLAN_NOT_STARTED", "Verify the active plan before submission")
            verification = self._verified_plan(tx, plan)
            submission = plan.get("submission")
            if plan["state"] in ("review", "done"):
                if not submission or submission["verification_id"] != verification["id"]:
                    valid.fail("WORKFLOW_SUBMISSION_STALE", "Submission differs from current verification")
                return plan
            submission = {"id": new_id("submission-"), "cycle": plan["cycle"],
                          "revision": plan["revision"], "verification_id": verification["id"],
                          "basis": copy.deepcopy(verification["basis"]),
                          "criteria": copy.deepcopy(plan["criteria"]),
                          "evidence": copy.deepcopy(plan["evidence"]), "submitted_at": now()}
            plan["submission"] = submission
            plan["submissions"].append(copy.deepcopy(submission))
            plan["state"] = "review"
            self._emit(tx, plan, "plan_submitted", {"submission": submission})
            return copy.deepcopy(plan)

    def accept_plan(self, plan_id, approval):
        approval = valid.approval(approval)
        with self.store.transaction() as tx:
            plan = self._load(tx, "plan", plan_id)
            if plan["state"] not in ("review", "done"):
                valid.fail("WORKFLOW_REVIEW_REQUIRED", "Only the current submitted Review can be accepted")
            verification = self._verified_plan(tx, plan)
            submission = plan.get("submission")
            if (not submission or submission["cycle"] != plan["cycle"] or
                    submission["verification_id"] != verification["id"] or
                    submission["basis"] != verification["basis"]):
                valid.fail("WORKFLOW_SUBMISSION_STALE", "Accept only the current verified submission")
            if plan["state"] == "done":
                if not plan.get("acceptance") or plan["acceptance"]["attestation"] != approval:
                    valid.fail("OPERATION_CONFLICT", "Plan already has a different final acceptance")
                return plan
            acceptance = {"id": new_id("acceptance-"), "cycle": plan["cycle"],
                          "revision": plan["revision"], "submission_id": submission["id"],
                          "attestation": approval, "accepted_at": now()}
            plan.update(state="done", acceptance=acceptance)
            self._emit(tx, plan, "plan_accepted", {"acceptance": acceptance})
            tx.enqueue("summary", "summary:accepted:" + acceptance["id"],
                       {"entity_id": plan_id, "cycle": plan["cycle"]})
            return copy.deepcopy(plan)

    def reopen_plan(self, plan_id, reason):
        reason = valid.text(reason, "reason")
        with self.store.transaction() as tx:
            plan = self._load(tx, "plan", plan_id)
            if plan["state"] == "doing" and plan.get("last_reopen"):
                if plan["last_reopen"]["reason"] != reason:
                    valid.fail("OPERATION_CONFLICT", "Current cycle was reopened with another reason")
                return plan
            if plan["state"] not in ("review", "done"):
                valid.fail("WORKFLOW_REOPEN_INVALID", "Reopen a submitted or accepted plan with new work")
            archive = {key: copy.deepcopy(plan[key]) for key in
                       ("cycle", "state", "revision", "criteria", "evidence", "approval",
                        "verification", "submission", "acceptance")}
            archive["work_ids"] = [work["id"] for work in self._current_work(tx, plan)]
            plan["cycles"].append(archive)
            plan.update(cycle=plan["cycle"] + 1, state="doing", revision=None, evidence={},
                        verified=False, verification=None, approval=None, submission=None, acceptance=None,
                        last_reopen={"reason": reason, "from_cycle": archive["cycle"], "at": now()})
            self._emit(tx, plan, "plan_reopened", {"reason": reason, "previous_cycle": archive})
            tx.enqueue("summary", f"summary:reopened:{plan_id}:{plan['cycle']}",
                       {"entity_id": plan_id, "cycle": plan["cycle"]})
            return copy.deepcopy(plan)

    def status(self, plan_id=None):
        """Read stored domain state only; no file creation, live poll or mutation."""
        if plan_id is None:
            return {"plans": self.store.list("plan"), "work": self.store.list("work")}
        plan_id = valid.text(plan_id, "plan_id")
        plan = self.store.read("plan", plan_id)
        if plan is None:
            valid.fail("NOT_FOUND", "Unknown plan", plan_id=plan_id)
        work = [self.store.read("work", identity) for identity in plan["work_ids"]]
        if any(row is None or row["plan_id"] != plan_id for row in work):
            valid.fail("WORKFLOW_PARENT_MISMATCH", "Plan references unavailable work")
        return {**plan, "work": work, "current_work_ids": [row["id"] for row in work if row["cycle"] == plan["cycle"]],
                "observation": "stored_domain_state; not_live_worker_or_board_state"}

    def history(self, entity_id=None):
        """Return the append-only journal, optionally for one plan/work ID."""
        if entity_id is not None:
            entity_id = valid.text(entity_id, "entity_id")
        return self.store.history(entity_id)
