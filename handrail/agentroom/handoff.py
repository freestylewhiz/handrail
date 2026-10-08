"""Prepared worker channel, durable result receipts and coordinator follow-through."""
import json
import secrets
import shlex
from datetime import datetime, timedelta, timezone
from pathlib import Path
from handrail.shared.errors import HandrailError
from handrail.shared.identity import digest, now
from .worker_io import write_atomic
from .providers import launch_settings


def prepare(attempt, git, instructions):
    worker = git.verify_worktree(attempt["path"], attempt["branch"])
    git_dir = worker.run("rev-parse", "--absolute-git-dir").strip()
    channel = Path(attempt["path"]).parent / (".channel-" + digest(attempt["id"])[:16])
    if channel.is_symlink():
        raise HandrailError("WORKER_REPORT_PATH", "Worker channel must not be a symlink")
    channel.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = channel / "contract.json"
    value = {"schema": 1, "attempt_id": attempt["id"], "work_id": attempt["work_id"],
             "plan_id": attempt["plan_id"], "cycle": attempt["cycle"], "nonce": secrets.token_hex(32),
             "worktree": attempt["path"], "git_dir": git_dir, "common_dir": str(worker.common_dir)}
    write_atomic(path, value)
    launcher = str(Path.home() / ".local/bin/handrail")
    probe = shlex.join([launcher, "worker", "probe", "--contract", str(path)])
    submit = shlex.join([launcher, "worker", "submit", "--contract", str(path), "--report-file", str(channel / "report.json")])
    bootstrap = ("Handrail readiness phase. Do not implement yet. In your normal sandbox tool, from " +
                 shlex.quote(attempt["path"]) + ", run: rtk " + probe +
                 "\nDo not escalate the probe or disable sandboxing. If blocked, report the exact error and wait. "
                 "A ready result is an observation of these paths; it is not permission for other paths. "
                 "Then report readiness and wait for the coordinator's implementation instruction.")
    packet = instructions + ("\n\n## Completion handoff\nKeep to this assigned worktree. Commit authorized work. "
        "Write a JSON report outside the worktree with summary (text), verification (list of actual checks), "
        "unverified (list), blockers (list), and instruction_compliance (list referencing the supplied cards). "
        "Do not invent checks. Use a report path inside " + str(channel) + ". Then run from the worktree: rtk " +
        submit + ". Report the returned submission_id and commit. Wait for coordinator review; do not set the Plan Done. "
        "The channel submission persists if a notification is missed. You have no manager database, board token or Herdr write grant.")
    paths = [str(worker.root), git_dir, str(worker.common_dir), str(channel)]
    return {"worker_contract": value, "channel": str(channel), "protocol": 2, "bootstrap": bootstrap,
            "task_instructions": instructions,
            "implementation_instructions": packet, "execution_phase": "readiness",
            "launch": launch_settings(attempt["provider"], attempt["model"], attempt.get("effort"), paths)}


class HandoffService:
    def __init__(self, app):
        self.app, self.store = app, app.store

    def _read(self, attempt, name):
        channel = Path(attempt["channel"])
        path = channel / name
        if channel.is_symlink() or path.is_symlink():
            raise HandrailError("WORKER_REPORT_PATH", "Channel files must not be symlinks")
        try:
            if path.stat().st_size > 1024 * 1024:
                raise HandrailError("WORKER_REPORT_INVALID", "Worker report exceeds 1 MiB")
            value = json.loads(path.read_text())
        except FileNotFoundError:
            return None
        except (ValueError, UnicodeError):
            raise HandrailError("WORKER_REPORT_INVALID", "Worker report must be valid UTF-8 JSON", details={"path": str(path)}) from None
        except OSError as exc:
            raise HandrailError("WORKER_REPORT_ACCESS", "Could not read this worker's channel",
                                details={"path": str(path), "errno": exc.errno, "boundary": "host/filesystem"}) from None
        contract = attempt["worker_contract"]
        if not isinstance(value, dict) or any(value.get(k) != contract[k] for k in ("attempt_id", "nonce")):
            raise HandrailError("WORKER_REPORT_STALE", "Report belongs to a different launch")
        return value

    def continue_worker(self, attempt_id):
        with self.store.exclusive("agentroom-mutation"):
            room = self.app.room()
            attempt = room._require("attempt", attempt_id)
            room._active_work(attempt)
            room._live(attempt)
            if not attempt.get("worker_contract"):
                raise HandrailError("WORKER_PROTOCOL_LEGACY", "Existing worker uses the earlier protocol; preserve its active work")
            readiness = self._read(attempt, "readiness.json")
            required = set(attempt["launch"]["requested_paths"])
            if readiness and (not isinstance(readiness.get("results"), list) or any(
                not isinstance(r, dict) or not isinstance(r.get("path"), str) or not isinstance(r.get("write"), bool)
                for r in readiness["results"])):
                raise HandrailError("WORKER_REPORT_INVALID", "Readiness needs path/write observations")
            observed = {r.get("path") for r in (readiness or {}).get("results", []) if r.get("write") is True}
            if not readiness or readiness.get("status") != "ready" or observed != required or readiness.get("cwd") != attempt["path"]:
                raise HandrailError("WORKER_WRITE_NOT_READY", "Wait for the worker's sandbox probe or address its scoped denial",
                                    details={"attempt_id": attempt_id, "requested": sorted(required), "readiness": readiness,
                                             "next": "Inspect host permissions for these paths; never widen the global sandbox"})
            # Reuse the start authority for its deferred initial instruction.
            grant = room._authorize(attempt, "worker.start", provider=attempt["provider"], model=attempt["model"])
            previous_message = self.store.read("message", attempt_id + ":implementation")
            if previous_message:
                message = previous_message
            else:
                text = attempt.get("implementation_message_text")
                if not text:
                    guidance = self.app.instructions().check(attempt["work_id"], "assignment")
                    text = attempt["implementation_instructions"] + "\n\nCurrent instruction references (supersede earlier versions):\n" + json.dumps(
                        guidance["instructions"], ensure_ascii=False, sort_keys=True)
                    # Freeze the message before sending. A lost receipt must
                    # replay the same payload even if remote timestamps change.
                    with self.store.transaction() as tx:
                        current = tx.require("attempt", attempt_id)
                        current["implementation_message_text"] = text
                        tx.put("attempt", attempt_id, current)
                message = room._prompt(attempt, text, attempt_id + ":implementation", grant)
            with self.store.transaction() as tx:
                current = tx.require("attempt", attempt_id)
                current.update(execution_phase="implementation", readiness=readiness)
                tx.put("attempt", attempt_id, current)
                tx.event(current["work_id"], "worker.ready", {"attempt_id": attempt_id,
                         "source": "worker sandbox probe report", "authenticated_host_attestation": False})
            return {"attempt_id": attempt_id, "message": message, "next": "coordinator tick PLAN --owner SESSION"}

    def collect_submission(self, attempt_id):
        with self.store.exclusive("agentroom-mutation"):
            room = self.app.room()
            attempt = room._require("attempt", attempt_id)
            if not attempt.get("worker_contract"):
                return {"attempt_id": attempt_id, "status": "legacy", "next": "worker collect; explicitly review the candidate"}
            report = self._read(attempt, "submission.json")
            if report is None:
                return {"attempt_id": attempt_id, "status": "waiting", "next": "Wait for the structured worker submission"}
            contract = attempt["worker_contract"]
            if any(report.get(k) != contract[k] for k in ("work_id", "plan_id", "cycle")):
                raise HandrailError("WORKER_REPORT_STALE", "Report does not match the assigned work and cycle")
            fingerprint = {k: report.get(k) for k in ("schema", "attempt_id", "work_id", "plan_id", "cycle", "nonce", "commit", "report")}
            if report.get("submission_id") != "submission:" + digest(fingerprint):
                raise HandrailError("WORKER_REPORT_INVALID", "Submission fingerprint does not match its content")
            identity = report["submission_id"]
            previous = self.store.read("worker_submission", identity)
            if previous:
                return previous
            current_work = self.store.read("work", attempt["work_id"])
            current_plan = self.store.read("plan", attempt["plan_id"])
            if (attempt["state"] != "active" or not current_work or current_work.get("attempt_id") != attempt_id or
                current_work.get("integration") or current_work["state"] == "done" or not current_plan or
                current_plan["cycle"] != attempt["cycle"] or current_plan["state"] != "doing"):
                stale = {"id": identity, "attempt_id": attempt_id, "work_id": attempt["work_id"],
                         "plan_id": attempt["plan_id"], "cycle": attempt["cycle"], "commit": report.get("commit"),
                         "report": report.get("report"), "delivery": "stale", "received_at": now(),
                         "processed_at": None, "reason": "Attempt/cycle no longer accepts new submissions"}
                with self.store.transaction() as tx:
                    tx.put("worker_submission", identity, stale)
                    tx.event(attempt["work_id"], "worker.submission_stale", {"submission_id": identity, "attempt_id": attempt_id})
                return stale
            room._active_work(attempt)
            room._live(attempt)
            worker = room._git(attempt).verify_worktree(attempt["path"], attempt["branch"])
            worker.require_clean()
            if worker.revision() != report.get("commit"):
                raise HandrailError("WORKER_REPORT_STALE", "Submission candidate is no longer the worker HEAD")
            details = report.get("report")
            if not isinstance(details, dict) or not isinstance(details.get("summary"), str) or not details["summary"].strip() or any(
                not isinstance(details.get(k), list) for k in ("verification", "unverified", "blockers", "instruction_compliance")):
                raise HandrailError("WORKER_REPORT_INVALID", "Use the documented completion report schema")
            value = {"id": identity, "attempt_id": attempt_id, "work_id": attempt["work_id"],
                     "plan_id": attempt["plan_id"], "cycle": attempt["cycle"], "commit": report["commit"],
                     "report": details, "submitted_at": report.get("submitted_at"), "received_at": now(),
                     "delivery": "received", "processed_at": None, "verification_authority": "worker claim; coordinator review required"}
            with self.store.transaction() as tx:
                work = tx.require("work", attempt["work_id"])
                if work["attempt_id"] != attempt_id or work.get("integration") or work["state"] == "done":
                    raise HandrailError("WORKER_REPORT_STALE", "Current Work cannot receive this report")
                old = work.get("submission")
                if old and old["id"] != identity:
                    prior = tx.require("worker_submission", old["id"])
                    prior.update(delivery="superseded", superseded_by=identity)
                    tx.put("worker_submission", prior["id"], prior)
                tx.put("worker_submission", identity, value)
                work.update(state="review", submission={"id": identity, "commit": report["commit"], "attempt_id": attempt_id},
                            review=None, verified=False, verification=None)
                self.app.workflow._invalidate_plan(tx, tx.require("plan", attempt["plan_id"]), "worker_submission_received")
                self.app.workflow._emit(tx, work, "work_submitted", {"submission_id": identity, "reviewer": "coordinator"})
            return value

    def inbox(self, plan_id=None):
        results = []
        for record in self.store.list("worker_submission"):
            if (plan_id and record["plan_id"] != plan_id) or record["delivery"] != "received" or record.get("processed_at"):
                continue
            plan = self.store.read("plan", record["plan_id"])
            work = self.store.read("work", record["work_id"])
            if plan and work and plan["cycle"] == record["cycle"] and work.get("attempt_id") == record["attempt_id"]:
                results.append(record)
        return results

    def tick(self, plan_id, owner, interval=20):
        if not isinstance(owner, str) or not owner.strip() or not 5 <= interval <= 300:
            raise HandrailError("MONITOR_INVALID", "Specify coordinator session owner and interval from 5 to 300 seconds")
        # Only an executing command owns a monitor. No imaginary daemon or
        # promise to wake a coordinator after the tool call/turn has ended.
        with self.store.exclusive("monitor:" + plan_id):
            if not self.store.read("plan", plan_id):
                raise HandrailError("NOT_FOUND", "Unknown Plan")
            old = self.store.read("monitor", plan_id) or {}
            results = []
            for attempt in self.store.list("attempt"):
                if attempt["plan_id"] != plan_id or attempt["state"] != "active":
                    continue
                work = self.store.read("work", attempt["work_id"])
                if not work or work["state"] == "done" or work.get("integration"):
                    continue
                try:
                    observation = self.app.room().collect(attempt["id"])
                    if attempt.get("execution_phase") == "readiness":
                        result = self.continue_worker(attempt["id"])
                    else:
                        result = self.collect_submission(attempt["id"])
                    results.append({"attempt_id": attempt["id"], "activity": observation["agent_status"],
                                    "status": "complete", "result": result})
                except HandrailError as exc:
                    results.append({"attempt_id": attempt["id"], "status": "failed", "error": exc.as_dict()})
            failures = any(r["status"] == "failed" for r in results)
            delay = min(300, max(interval, old.get("backoff_seconds", interval) * 2)) if failures else interval
            value = {"id": plan_id, "owner": owner, "last_check": now(), "interval_seconds": interval,
                     "backoff_seconds": delay, "next_check": (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat(),
                     "running": False, "mode": "foreground-tick", "host_wakeup": "unavailable",
                     "targets": [r["attempt_id"] for r in results],
                     "resume": "Coordinator must schedule the next tick while its turn is active, and tick immediately on reconnect"}
            with self.store.transaction() as tx:
                tx.put("monitor", plan_id, value)
                tx.event(plan_id, "coordinator.checked", {"owner": owner, "previous_owner": old.get("owner"), "results": results})
            deliveries = self.app.dispatch("board")
            return {"monitor": value, "results": results, "board": deliveries, "inbox": self.inbox(plan_id),
                    "followthrough": self.app.advance_plan(plan_id),
                    "next_actions": self.next_actions(plan_id)}

    def next_actions(self, plan_id):
        status = self.app.workflow.status(plan_id)
        actions = []
        for work in status["work"]:
            if work["cycle"] != status["cycle"] or work["state"] == "done":
                continue
            if work.get("integration"):
                action = "Record integrated criterion evidence, then work complete"
            elif (work.get("review") or {}).get("verdict") == "accept":
                action = "worker integrate; verify the integrated revision"
            elif (work.get("review") or {}).get("verdict") in ("revise", "reject"):
                action = "Send scoped review feedback; receive a fresh worker submission before reviewing again"
            elif work.get("submission"):
                action = "Read submission and instruction references; inspect commit; work review with verdict and notes"
            else:
                action = "Continue readiness or monitor worker; report blockers to the user"
            actions.append({"work_id": work["id"], "action": action})
        if not actions and status["state"] == "doing":
            actions.append({"plan_id": plan_id, "action": "Record final canonical evidence; plan verify; plan submit-review; report the Review card URL and remaining limitations to the user"})
        elif status["state"] == "review":
            notice = self.store.read("review_notice", status["submission"]["id"])
            actions.append({"plan_id": plan_id, "action": "Wait for user review acceptance" if notice else
                            "Report implementation outcome and Plan Review URL to the user; record coordinator report"})
        return actions
