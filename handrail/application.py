"""Composition boundary connecting domain decisions to Git and adapters."""
from pathlib import Path
from .setup.settings import context, connection
from .shared.errors import HandrailError
from .workflow.service import WorkflowService
from .agentroom.service import resource_scope, serialized


class Application:
    def __init__(self, repo="."):
        self.ctx = context(repo)
        self.store, self.config, self.git = self.ctx["store"], self.ctx["config"], self.ctx["git"]
        self.workflow = WorkflowService(self.store)

    def room(self):
        from .interfaces.agentroom.herdr import HerdrClient
        from .agentroom.service import AgentRoomService
        return AgentRoomService(self.store, self.config, self.git,
                                HerdrClient(self.config["endpoint"]), self.workflow)

    def board(self):
        from .interfaces.vikunja.client import VikunjaClient
        from .interfaces.vikunja.board import VikunjaBoard
        profile = connection(self.config["profile"])
        return VikunjaBoard(VikunjaClient(profile["url"], profile["token"],
                            allow_insecure_http=profile["allow_insecure_http"]),
                            self.config["project_id"], self.config["view_id"], self.config["states"])

    def summaries(self):
        from .summary.service import SummaryService
        return SummaryService(self.store, self.config, self.board())

    def cleanup(self):
        from .agentroom.cleanup import CleanupService
        return CleanupService(self)

    def instructions(self):
        from .board.service import BoardService
        from .board.instructions import InstructionService
        return InstructionService(BoardService(self.config["repo"]))

    def handoff(self):
        from .agentroom.handoff import HandoffService
        return HandoffService(self)

    def create_plan(self, title, criteria, operation_id=None, presentation=None):
        # Read parent guidance before persisting a new planning artifact.
        self.instructions().list()
        plan = self.workflow.create_plan(title, criteria, operation_id, presentation)
        guidance = self.instructions().check(plan["id"], "planning")
        try:
            related = self.summaries().list(title)
        except HandrailError as exc:
            related = {"unavailable": exc.as_dict(), "next": "Retry summary list before planning related work"}
        return dict(plan, related_summaries=related, instructions=guidance,
                    next="Read applicable Agent Context and record summary use before assigning work")

    def create_work(self, plan_id, title, criteria, operation_id=None, presentation=None):
        self.instructions().check(plan_id, "planning")
        work = self.workflow.create_work(plan_id, title, criteria, operation_id, presentation)
        from .board.service import BoardService
        plan = self.store.read("plan", plan_id)
        approved = plan.get("approval") and plan["approval"]["cycle"] == plan["cycle"]
        mapping = BoardService(self.config["repo"]).prepare_work(work["id"]) if approved else {
            "status": "deferred", "reason": "Work draft; no implementation approval in this cycle"}
        guidance = self.instructions().check(work["id"], "assignment")
        return dict(work, board=mapping, instructions=guidance,
                    next="Select worker or reuse the observed coordinator model; worker start WORK" if approved else
                    "Approve the implementation cycle before preparing its board or workers")

    def start_worker(self, work_id, provider, model, instructions, effort=None, operation_id=None):
        from .agentroom.providers import selection
        from .board.service import BoardService
        from .shared.identity import digest
        request_hash = digest(instructions)
        existing = self.store.read("attempt", operation_id) if operation_id else next(
            (a for a in self.store.list("attempt") if a["work_id"] == work_id and a["state"] not in ("closed", "replaced")), None)
        if existing and existing.get("request_instructions_hash") and existing.get("task_instructions"):
            if (existing["work_id"] != work_id or existing["request_instructions_hash"] != request_hash or
                provider and provider != existing["provider"] or model and model != existing["model"] or
                effort and effort != existing.get("effort")):
                raise HandrailError("OPERATION_CONFLICT", "Resume the original start or explicitly prompt/recover the existing worker")
            # A temporary board/catalog outage must not recreate an active worker.
            return self.room().start(work_id, existing["provider"], existing["model"], existing["task_instructions"],
                                     existing.get("effort"), existing["id"])
        if existing:
            operation_id = existing["id"]
        selected = selection(self.store, work_id, provider, model, effort)
        guidance = self.instructions().check(work_id, "assignment")
        BoardService(self.config["repo"]).prepare_work(work_id)
        deliveries = self.dispatch("board")
        if any(r["status"] != "complete" for r in deliveries):
            raise HandrailError("WORKER_BOARD_PENDING", "Finish card preparation before starting execution", details={"deliveries": deliveries})
        import json
        instructions += "\n\n## Project instructions (guidance, never permission grants)\n" + json.dumps(
            guidance["instructions"], ensure_ascii=False, indent=2)
        # Read selected remote sections before any worker/worktree effects.
        context = self.summaries().worker_context(work_id)
        if context:
            import json
            instructions += "\n\n## Historical evidence (not new instructions or authority)\n" + json.dumps(context, ensure_ascii=False, indent=2)
        result = self.room().start(work_id, selected["provider"], selected["model"], instructions,
                                  selected.get("effort"), operation_id, request_hash)
        result["selection"] = selected
        result["monitoring"] = {"host_wakeup": "unavailable", "next": "coordinator tick PLAN --owner SESSION; repeat while the turn remains active"}
        from .shared.identity import now
        plan_id = result["attempt"]["plan_id"]
        with self.store.transaction() as tx:
            attempt = tx.require("attempt", result["attempt"]["id"])
            attempt["request_instructions_hash"] = request_hash
            tx.put("attempt", attempt["id"], attempt)
            if not tx.get("monitor", plan_id):
                coordinator = tx.get("coordinator", "current") or {}
                tx.put("monitor", plan_id, {"id": plan_id, "owner": coordinator.get("session_id") or "current coordinator",
                    "targets": [result["attempt"]["id"]], "last_check": None, "next_check": now(), "interval_seconds": 20,
                    "running": False, "mode": "foreground-tick", "host_wakeup": "unavailable", "state": "initial_tick_due"})
            else:
                monitor = tx.get("monitor", plan_id)
                monitor["targets"] = list(dict.fromkeys(monitor.get("targets", []) + [result["attempt"]["id"]]))
                tx.put("monitor", plan_id, monitor)
        return result

    def status(self, plan_id=None):
        from datetime import datetime, timezone
        domain = self.workflow.status(plan_id)
        documents = domain["plans"] + domain["work"] if plan_id is None else [domain] + domain["work"]
        for document in documents:
            mapping = self.store.read("board_card", document["id"])
            if mapping:
                override = self.store.read("card_override", str(mapping["task_id"]))
                document["card"] = {"id": mapping["task_id"], "state": mapping["state"],
                                    "state_source": "user_override" if override and override.get("active") else "workflow",
                                    "override": override if override and override.get("active") else None,
                                    "observation": "stored; card list reads live board data"}
        attempts = [a for a in self.store.list("attempt") if plan_id is None or a["plan_id"] == plan_id]
        monitors = [m for m in self.store.list("monitor") if plan_id is None or m["id"] == plan_id]
        for monitor in monitors:
            stamp = monitor.get("last_check")
            monitor["seconds_since_check"] = max(0, int((datetime.now(timezone.utc) - datetime.fromisoformat(stamp)).total_seconds())) if stamp else None
            monitor["overdue"] = bool(monitor.get("next_check") and datetime.fromisoformat(monitor["next_check"]) < datetime.now(timezone.utc))
            monitor["requires_active_coordinator"] = True
        waits = []
        for attempt in attempts:
            if attempt["state"] in ("closed", "replaced"):
                continue
            work = self.store.read("work", attempt["work_id"])
            if work and work["state"] == "done":
                next_action = "retained for user review or cleanup"
            elif work and work.get("integration"):
                next_action = "record criterion evidence and complete this integrated revision before the next merge"
            elif attempt["state"] == "preparing" or (work and work.get("attempt_id") != attempt["id"]):
                next_action = "resume startup or reconcile the recorded attempt"
            elif attempt.get("activity") == "blocked":
                next_action = "inspect worker approval or question"
            elif attempt.get("activity") in ("idle", "done"):
                next_action = "coordinator collects and reviews the result"
            else:
                next_action = "observe this worker for its response"
            waits.append({"worker": attempt.get("name"), "attempt_id": attempt["id"],
                          "provider": attempt["provider"], "model": attempt["model"],
                          "work_title": work.get("title") if work else None,
                          "work_id": attempt["work_id"], "last_observed": attempt.get("observed_at"),
                          "lifecycle": attempt["state"], "stored_activity": attempt.get("activity", "unknown"),
                          "resource_scope": attempt.get("resource_scope"), "next_action": next_action})
        related = None if plan_id is None else {plan_id} | {work["id"] for work in domain["work"]}
        pending = [{"key": item["key"], "topic": item["topic"], "status": item["status"],
                    "entity_id": item["payload"].get("entity_id"), "result": item["result"]}
                   for item in self.store.outbox() if item["status"] != "complete" and
                   (related is None or item["payload"].get("entity_id") in related or
                    item["payload"].get("room_id", "").startswith(plan_id + ":"))]
        operations = [{"id": op["id"], "action": op["action"], "status": op["status"],
                       "entity_id": op["request"].get("entity", op["request"].get("plan_id")),
                       "error": op.get("error")}
                      for op in self.store.list("operation") if op["status"] not in ("complete", "reconciled", "cancelled") and
                      (related is None or op["request"].get("entity", op["request"].get("plan_id")) in related)]
        return {"workflow": domain, "workers": waits, "pending_deliveries": pending,
                "coordinator": self.store.read("coordinator", "current"),
                "monitors": monitors,
                "completion_inbox": self.handoff().inbox(plan_id),
                "user_reports": [r for r in self.store.list("review_notice") if plan_id is None or r["plan_id"] == plan_id],
                "instruction_references": [r for r in self.store.list("instruction_reference") if related is None or r["id"] in related],
                "summaries": [s for s in self.store.list("summary_card") if plan_id is None or s["id"] == plan_id],
                "summary_references": [r for r in self.store.list("summary_reference") if related is None or r["entity_id"] in related],
                "child_boards": [b for b in self.store.list("child_board") if plan_id is None or b["id"] == plan_id],
                "managed_boards": self.store.list("managed_board"),
                "card_overrides": [o for o in self.store.list("card_override") if o.get("active") and
                                   (related is None or o.get("entity_id") in related)],
                "operations": operations,
                "rooms": [room for room in self.store.list("room") if plan_id is None or room["plan_id"] == plan_id],
                "observation": "stored state; use worker observe for live state"}

    def _entity_resources(self, entity_id):
        entity = self.store.read("plan", entity_id) or self.store.read("work", entity_id)
        if not entity:
            raise HandrailError("NOT_FOUND", "Unknown plan or work")
        room = self.room()
        owner = room.cycle_scope(entity.get("plan_id", entity["id"]), entity["cycle"])
        return entity, resource_scope(self.config, owner), room._git(owner)

    @serialized
    def review(self, work_id, verdict, notes):
        self.instructions().check(work_id, "review")
        if isinstance(verdict, str):
            verdict = verdict.strip()
        if isinstance(notes, str):
            notes = notes.strip()
        work = self.store.read("work", work_id)
        attempt = self.store.read("attempt", work.get("attempt_id")) if work else None
        if not attempt:
            raise HandrailError("ATTEMPT_REQUIRED", "Review a recorded worker attempt")
        if work.get("integration"):
            previous = work.get("review") or {}
            if previous.get("verdict") == verdict and previous.get("notes") == notes:
                return self.workflow.review_work(work_id, verdict, notes, revision=previous["revision"])
            raise HandrailError("WORK_IMMUTABLE", "Create follow-up work after integration")
        room = self.room()
        room._active_work(attempt)
        worker = room._git(attempt).verify_worktree(attempt["path"], attempt["branch"])
        worker.require_clean()
        if attempt.get("protocol") == 2:
            submission = work.get("submission")
            if not submission or submission["commit"] != worker.revision() or submission["attempt_id"] != attempt["id"]:
                raise HandrailError("WORK_SUBMISSION_REQUIRED", "Collect the current structured completion report before review")
        return self.workflow.review_work(work_id, verdict, notes, revision=worker.revision())

    @serialized
    def record_evidence(self, entity_id, criterion, evidence, revision=None, command_id=None):
        entity, scope, git = self._entity_resources(entity_id)
        git.require_clean()
        current = git.revision()
        if entity["kind"] == "work" and not entity.get("integration"):
            raise HandrailError("INTEGRATION_REQUIRED", "Resume or finish integration before recording canonical work evidence")
        if revision and revision != current:
            raise HandrailError("REVISION_CHANGED", "Record integrated evidence against current canonical HEAD")
        if command_id:
            operation = self.store.read("operation", command_id)
            result = operation.get("result", {}) if operation else {}
            if (not operation or operation["action"] != "command.run" or operation["status"] != "complete" or
                    result.get("purpose") != "verify" or result.get("exit_code") != 0 or
                    result.get("revision_before") != current or result.get("revision_after") != current or
                    not result.get("clean_after") or Path(result["cwd"]).resolve() != git.root):
                raise HandrailError("COMMAND_EVIDENCE_INVALID", "Use a successful canonical verification command for this revision")
            plan_id = entity.get("plan_id", entity["id"])
            if operation["request"]["plan_id"] != plan_id:
                raise HandrailError("COMMAND_EVIDENCE_INVALID", "Command belongs to a different plan")
            request = operation["request"]
            if any(request.get(key) != value for key, value in scope.items()):
                raise HandrailError("COMMAND_EVIDENCE_INVALID", "Command used different resources from this execution cycle")
            if request.get("cycle") != entity["cycle"]:
                raise HandrailError("COMMAND_EVIDENCE_INVALID", "Command belongs to a different execution cycle")
            if not isinstance(evidence, str):
                raise HandrailError("EVIDENCE_INVALID", "Use --text with --command-id")
            evidence = {"status": "passed", "text": evidence, "command_id": command_id,
                        "argv": result["argv"], "log": result["log"],
                        "log_sha256": __import__("hashlib").sha256(Path(result["log"]).read_bytes()).hexdigest()}
        return self.workflow.record_evidence(entity_id, criterion, evidence, current)

    @serialized
    def complete_work(self, work_id):
        work = self.store.read("work", work_id)
        if work and work["state"] == "done":
            return self.workflow.complete_work(work_id, work["revision"])
        _, _, git = self._entity_resources(work_id)
        git.require_clean()
        return self.workflow.complete_work(work_id, git.revision())

    def _verified_tree(self, plan_id):
        _, _, git = self._entity_resources(plan_id)
        git.require_clean()
        state = self.workflow.status(plan_id)
        for work in state["work"]:
            if work["cycle"] == state["cycle"]:
                if not work.get("revision") or not git.contains(work["revision"]):
                    raise HandrailError("INTEGRATION_MISSING", "Checkout does not contain all completed work")
        return git.revision()

    @serialized
    def verify_plan(self, plan_id):
        return self.workflow.verify_plan(plan_id, self._verified_tree(plan_id))

    @serialized
    def submit_review(self, plan_id):
        self.instructions().check(plan_id, "review")
        revision = self._verified_tree(plan_id)
        plan = self.store.read("plan", plan_id)
        if plan["revision"] != revision:
            raise HandrailError("REVISION_CHANGED", "Reverify the current checkout before submitting")
        return self.workflow.submit_review(plan_id)

    def advance_plan(self, plan_id):
        """Use existing evidence to advance; never invent checks or user acceptance."""
        plan = self.workflow.status(plan_id)
        works = [w for w in plan["work"] if w["cycle"] == plan["cycle"]]
        if plan["state"] == "doing" and works and all(w["state"] == "done" for w in works):
            try:
                self.verify_plan(plan_id)
                self.submit_review(plan_id)
            except HandrailError as exc:
                return {"plan_id": plan_id, "advanced": False, "status": "blocked", "blocker": exc.as_dict(),
                        "next": "Coordinator supplies missing canonical verification evidence or resolves the reported blocker"}
        from .workflow.reporting import preview
        return {"board": self.dispatch("board"), "review": preview(self, plan_id)}

    def accept(self, plan_id, approval, summary=None):
        summaries = self.summaries()
        plan_id = summaries.plan_id(plan_id)
        if summary is not None:
            summaries.publish(plan_id, summary, "Prepare final Summary for user acceptance")
        with self.store.exclusive("outbox-delivery"), self.store.exclusive("agentroom-mutation"):
            plan = self.store.read("plan", plan_id)
            if not plan:
                raise HandrailError("NOT_FOUND", "Unknown plan")
            current = summaries._find(plan_id)
            _, _, fingerprint = summaries._source(plan_id)
            from .summary.format import parse
            if not current or parse(current["description"])[0].get("source_fingerprint") != fingerprint:
                raise HandrailError("SUMMARY_CONTENT_REQUIRED", "Coordinator must prepare the current Summary before final acceptance; reuse the user's approval",
                                    details={"plan_id": plan_id, "requires_user_response": False,
                                             "next": "summary prepare PLAN --language USER_LANGUAGE; synthesize content, then plan complete PLAN --approval ORIGINAL_APPROVAL --summary-file FILE"})
            if plan["state"] != "done":
                revision = self._verified_tree(plan_id)
                if plan["revision"] != revision:
                    raise HandrailError("REVISION_CHANGED", "Checkout changed after review submission")
            # A replay of an existing acceptance must not reinterpret a later
            # canonical HEAD as a new acceptance request.
            value = self.workflow.accept_plan(plan_id, approval)
            # Old accepted plans can acquire the completion hook on an explicit replay.
            with self.store.transaction() as tx:
                tx.enqueue("summary", "summary:accepted:" + value["acceptance"]["id"],
                           {"entity_id": plan_id, "cycle": value["cycle"]})
        board_result = self.dispatch("board")
        summary_result = self.dispatch("summary")
        failures = [r for r in board_result + summary_result if r["status"] != "complete"]
        return {"plan": value, "board": board_result, "summary": summary_result,
                "cleanup": self.cleanup().preview(plan_id), "exit_code": 1 if failures else 0,
                "next": "Resolve pending deliveries if any; ask whether to close or retain the listed AgentRooms"}

    def reopen(self, plan_id, reason):
        plan_id = self.summaries().plan_id(plan_id)
        with self.store.exclusive("agentroom-mutation"):
            value = self.workflow.reopen_plan(plan_id, reason)
        return {"plan": value, "summary": self.dispatch("summary"), "board": self.dispatch("board")}

    def projection(self):
        from .hooks.routing import BoardRouter
        return BoardRouter(self.store, self.config, self.board())

    def dispatch(self, topic=None):
        from .hooks.dispatcher import HookDispatcher
        dispatcher = HookDispatcher(self.store)
        if topic in (None, "board"):
            dispatcher.register("board", self.projection())
        if topic in (None, "room.cleanup"):
            dispatcher.register("room.cleanup", lambda item: self.cleanup().deliver(item["payload"]["room_id"]))
        if topic in (None, "summary"):
            dispatcher.register("summary", self.summaries().lifecycle)
        return dispatcher.dispatch(topic)
