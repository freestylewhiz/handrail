"""Worker-side file protocol: no manager database, board token or Herdr access."""
import json
import os
import tempfile
from pathlib import Path
from handrail.shared.errors import HandrailError
from handrail.shared.identity import now, digest
from handrail.interfaces.git.repository import GitRepository


def write_atomic(path, value):
    path = Path(path)
    if path.is_symlink():
        raise HandrailError("WORKER_REPORT_PATH", "Report path must not be a symlink")
    fd, temporary = tempfile.mkstemp(prefix=".report-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as out:
            json.dump(value, out, ensure_ascii=False)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def contract(path):
    path = Path(path).absolute()
    if path.is_symlink() or path.parent.resolve() != path.parent:
        raise HandrailError("WORKER_CONTRACT_INVALID", "Contract and channel must use their original non-symlink paths")
    path = path.resolve(strict=True)
    value = json.loads(path.read_text())
    required = ("attempt_id", "work_id", "plan_id", "cycle", "worktree", "git_dir", "common_dir", "nonce")
    if not isinstance(value, dict) or any(k not in value for k in required):
        raise HandrailError("WORKER_CONTRACT_INVALID", "Incomplete worker contract")
    git = GitRepository(value["worktree"])
    if (Path.cwd().resolve() != git.root or str(git.common_dir) != value["common_dir"] or
            git.run("rev-parse", "--absolute-git-dir") != value["git_dir"]):
        raise HandrailError("WORKER_LOCATION", "Run this command inside the assigned worktree")
    return value, path.parent, git


def probe(path):
    value, directory, git = contract(path)
    results = []
    for target in dict.fromkeys([value["worktree"], value["git_dir"], value["common_dir"], str(directory)]):
        try:
            fd, temporary = tempfile.mkstemp(prefix=".handrail-write-probe-", dir=target)
            os.close(fd)
            os.unlink(temporary)
            results.append({"path": target, "write": True})
        except OSError as exc:
            results.append({"path": target, "write": False, "errno": exc.errno})
    result = {"schema": 1, "attempt_id": value["attempt_id"], "nonce": value["nonce"],
              "observed_at": now(), "cwd": str(git.root), "results": results,
              "status": "ready" if all(r["write"] for r in results) else "blocked",
              "boundary": "worker-tool-execution", "commit_success": "not_tested"}
    write_atomic(directory / "readiness.json", result)
    return result


def submit(path, report):
    value, directory, git = contract(path)
    readiness = json.loads((directory / "readiness.json").read_text())
    if readiness.get("nonce") != value["nonce"] or readiness.get("status") != "ready":
        raise HandrailError("WORKER_NOT_READY", "Complete the scoped worker probe before submission")
    if not isinstance(report, dict):
        raise HandrailError("REPORT_INVALID", "Completion report must be a JSON object")
    for key in ("summary", "verification", "unverified", "blockers", "instruction_compliance"):
        if key not in report:
            raise HandrailError("REPORT_INVALID", "Report requires summary, verification, unverified, blockers and instruction_compliance")
    if not isinstance(report["summary"], str) or not report["summary"].strip() or any(
        not isinstance(report[k], list) for k in ("verification", "unverified", "blockers", "instruction_compliance")):
        raise HandrailError("REPORT_INVALID", "Summary must be nonempty text; verification, unverified, blockers and instruction_compliance must be lists")
    git.require_clean()
    commit = git.revision()
    result = {"schema": 1, **{k: value[k] for k in ("attempt_id", "work_id", "plan_id", "cycle", "nonce")},
              "commit": commit, "report": report}
    result["submission_id"] = "submission:" + digest(result)
    target = directory / "submission.json"
    if target.exists():
        old = json.loads(target.read_text())
        if old.get("submission_id") == result["submission_id"]:
            return old
        write_atomic(directory / ("previous-" + digest(old) + ".json"), old)
    result["submitted_at"] = now()
    write_atomic(target, result)
    return {"submission_id": result["submission_id"], "status": "submitted",
            "next": "Report submission ID and candidate commit to the coordinator; receipt is tracked separately"}
