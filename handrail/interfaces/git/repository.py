"""Git operations use argv, explicit roots and persisted worktree ownership."""
import subprocess
import os
from pathlib import Path
from handrail.shared.errors import HandrailError


class GitRepository:
    def __init__(self, path):
        self.path = Path(path).expanduser().resolve()
        self.root = Path(self.run("rev-parse", "--show-toplevel")).resolve()
        common = Path(self.run("rev-parse", "--git-common-dir"))
        self.common_dir = (self.path / common).resolve() if not common.is_absolute() else common.resolve()

    def run(self, *args, cwd=None):
        env = os.environ.copy()
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
            env.pop(key, None)
        try:
            result = subprocess.run(["git", "-C", str(cwd or self.path), *map(str, args)],
                                    capture_output=True, text=True, timeout=120, shell=False, env=env)
        except FileNotFoundError:
            raise HandrailError("GIT_MISSING", "Install Git") from None
        except subprocess.TimeoutExpired:
            raise HandrailError("GIT_TIMEOUT", "Inspect repository state before retrying", uncertain=True) from None
        if result.returncode:
            denied = any(value in (result.stderr or "").lower() for value in ("permission denied", "read-only file system", "operation not permitted"))
            raise HandrailError("GIT_PERMISSION" if denied else "GIT_FAILED", "Git operation failed; inspect repository status and actual host permissions",
                                details={"actor": "git", "operation": str(args[0]), "exit_code": result.returncode,
                                         "cwd": str(cwd or self.path), "common_dir": str(getattr(self, "common_dir", "unresolved")),
                                         "boundary": "host/filesystem" if denied else "git"})
        return result.stdout.strip()

    def revision(self):
        return self.run("rev-parse", "HEAD")

    def clean(self):
        return not self.run("status", "--porcelain", "--untracked-files=normal")

    def require_clean(self):
        if not self.clean():
            raise HandrailError("DIRTY_CHECKOUT", "Commit or preserve existing changes before this operation")

    def create_worktree(self, path, branch, base):
        path = Path(path)
        if not path.is_absolute() or path.is_symlink() or path.resolve() != path:
            raise HandrailError("WORKTREE_PATH", "Use an absolute, resolved, non-symlink worktree path")
        if path.exists():
            self.verify_worktree(path, branch)
            return str(path)
        self.require_clean()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.run("worktree", "add", "-b", branch, str(path), base)
        self.verify_worktree(path, branch)
        return str(path)

    def verify_worktree(self, path, branch=None):
        path = Path(path)
        if path.is_symlink() or path.resolve() != path:
            raise HandrailError("WORKTREE_IDENTITY", "Worktree path has changed")
        other = GitRepository(path)
        if other.root != path or other.common_dir != self.common_dir or path == self.root:
            raise HandrailError("WORKTREE_IDENTITY", "Checkout is not an owned linked worktree")
        if branch and other.run("branch", "--show-current") != branch:
            raise HandrailError("WORKTREE_IDENTITY", "Worker branch differs from the recorded branch")
        return other

    def integrate(self, path, branch, expected_head, expected_worker):
        self.require_clean()
        worker = self.verify_worktree(path, branch)
        worker.require_clean()
        if self.revision() != expected_head or worker.revision() != expected_worker:
            raise HandrailError("REVISION_CHANGED", "Source changed after integration intent was recorded")
        # An explicit merge preserves independent task commits and does not force-reset conflicts.
        self.run("merge", "--no-ff", "--no-edit", expected_worker)
        return self.revision()

    def contains(self, revision):
        env = os.environ.copy()
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
            env.pop(key, None)
        result = subprocess.run(["git", "-C", str(self.root), "merge-base", "--is-ancestor",
                                 revision, "HEAD"], capture_output=True, text=True, shell=False, env=env)
        if result.returncode not in (0, 1):
            raise HandrailError("GIT_FAILED", "Could not establish commit ancestry")
        return result.returncode == 0

    def remove_worktree(self, path, branch):
        worker = self.verify_worktree(path, branch)
        worker.require_clean()
        if not self.contains(worker.revision()):
            raise HandrailError("UNINTEGRATED_WORK", "Worktree contains commits absent from the canonical checkout")
        self.run("worktree", "remove", str(path))

    def has_worktree(self, path):
        expected = Path(path).resolve()
        for line in self.run("worktree", "list", "--porcelain").splitlines():
            if line.startswith("worktree ") and Path(line[len("worktree "):]).resolve() == expected:
                return True
        return False
