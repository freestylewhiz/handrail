"""v1 configuration is private and separate from worker source trees."""
import getpass
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from handrail.shared.errors import HandrailError
from handrail.shared.identity import digest
from handrail.shared.store import Store


def data_root():
    base = os.environ.get("HANDRAIL_HOME")
    if base:
        return Path(base).expanduser().absolute()
    xdg = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    if not xdg.is_absolute():
        raise HandrailError("CONFIG_PATH_INVALID", "XDG_DATA_HOME must be absolute")
    return xdg / "handrail/v1"


def read_json(path, default=None):
    path = Path(path)
    if path.is_symlink():
        raise HandrailError("CONFIG_PATH_INVALID", "Configuration cannot be a symlink")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except (ValueError, UnicodeError):
        raise HandrailError("CONFIG_INVALID", "Configuration is not valid JSON") from None
    if not isinstance(value, dict):
        raise HandrailError("CONFIG_INVALID", "Configuration must be an object")
    return value


def write_json(path, value):
    path = Path(path)
    if path.is_symlink():
        raise HandrailError("CONFIG_PATH_INVALID", "Configuration cannot be a symlink")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    fd, temporary = tempfile.mkstemp(prefix=".handrail-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def connection_setup(name=None, url=None, allow_insecure_http=False, replace_token=False):
    import re
    from .interaction import ask, choose
    path = data_root() / "connections.json"
    value = read_json(path, {})
    if not url:
        if name and name in value:
            url = value[name]["url"]
        elif value:
            name = choose("connection", [{"name": key, "label": key + " — " + row["url"], "value": key}
                                          for key, row in value.items()], name)
            url = value[name]["url"]
        else:
            url = ask("url", "Vikunja server URL:")
    url = url.strip().rstrip("/")
    matches = [key for key, row in value.items() if row["url"] == url]
    name = name or (matches[0] if len(matches) == 1 else "server-" + digest(url)[:10])
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,47}", name):
        raise HandrailError("INVALID_NAME", "Use a lowercase connection identifier")
    url = url.rstrip("/")
    parsed = urlsplit(url)
    if (parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or
            parsed.password or parsed.query or parsed.fragment):
        raise HandrailError("INVALID_URL", "Use an HTTP(S) service URL without credentials or query")
    if name in value and value[name]["url"] != url:
        raise HandrailError("CONNECTION_PINNED", "Use a new connection name for a different server URL")
    previous = value.get(name, {})
    allow_insecure_http = allow_insecure_http or previous.get("allow_insecure_http", False)
    if parsed.scheme == "http" and not allow_insecure_http:
        if not __import__("sys").stdin.isatty():
            import shlex
            raise HandrailError("HTTP_OPT_IN_REQUIRED", "This server uses HTTP; explicit HTTP permission is needed once",
                                details={"next": "handrail setup --url " + shlex.quote(url) + " --allow-insecure-http",
                                         "url": url})
        choice = ask("http", "This URL uses unencrypted HTTP. Allow this saved connection?",
                     [{"label": "Allow HTTP for this connection", "value": True},
                      {"label": "Cancel", "value": False}])
        if not choice:
            raise HandrailError("SETUP_CANCELLED", "HTTP connection was not enabled")
        allow_insecure_http = True
    from handrail.interfaces.vikunja.client import VikunjaClient
    if previous and not replace_token:
        try:
            VikunjaClient(url, previous["token"], allow_insecure_http=allow_insecure_http).request("/user")
        except HandrailError as exc:
            if exc.code in ("VIKUNJA_HTTP_401", "VIKUNJA_HTTP_403"):
                exc.details = dict(exc.details, connection=name,
                                   next="Check token scope, or run handrail setup --name " + name + " --replace-token in your terminal")
            raise
        return {"connection": name, "url": url, "credential_stored": True, "reused": True,
                "next": "Run handrail init inside your repository"}
    if not __import__("sys").stdin.isatty():
        import shlex
        raise HandrailError("SECRET_INPUT_REQUIRED", "Enter the token once in your own terminal, not in chat",
                            details={"next": "handrail setup --url " + shlex.quote(url) + " --name " + shlex.quote(name)
                                     + (" --allow-insecure-http" if allow_insecure_http else "")
                                     + (" --replace-token" if replace_token else "")})
    token = getpass.getpass("Vikunja API token: ").strip()
    if not token:
        raise HandrailError("TOKEN_REQUIRED", "An API token is required")
    VikunjaClient(url, token, allow_insecure_http=allow_insecure_http).request("/user")
    value[name] = {"url": url, "token": token, "allow_insecure_http": bool(allow_insecure_http)}
    write_json(path, value)
    return {"connection": name, "url": url, "credential_stored": True,
            "next": "Run handrail init inside your repository"}


def connection(name):
    value = read_json(data_root() / "connections.json", {}).get(name)
    if not value:
        raise HandrailError("CONNECTION_REQUIRED", "Configure the named Vikunja connection in your terminal")
    return value


def project_identity(repo):
    from handrail.interfaces.git.repository import GitRepository
    git = GitRepository(repo)
    common = str(git.common_dir)
    return digest(common)[:24], git


def bind(repo, profile, project_id, view_id, states, endpoint, worktree_root=None,
         allow_inside_repository=False, child_projects=False):
    from handrail.interfaces.vikunja.client import VikunjaClient
    from handrail.interfaces.vikunja.board import VikunjaBoard
    identity, git = project_identity(repo)
    if not isinstance(endpoint, dict) or len(endpoint) != 1 or not set(endpoint) <= {"session", "socket"}:
        raise HandrailError("ENDPOINT_REQUIRED", "Choose one explicit Herdr session or absolute socket")
    if "socket" in endpoint and not Path(endpoint["socket"]).is_absolute():
        raise HandrailError("ENDPOINT_INVALID", "Socket path must be absolute")
    if not next(iter(endpoint.values()), ""):
        raise HandrailError("ENDPOINT_INVALID", "Endpoint must not be empty")
    if not isinstance(states, dict) or not {"todo", "doing", "review", "done"} <= set(states):
        raise HandrailError("BOARD_MAPPING_REQUIRED", "Parent board needs todo, doing, review and done mappings")
    config = connection(profile)
    board = VikunjaBoard(VikunjaClient(config["url"], config["token"],
                        allow_insecure_http=config["allow_insecure_http"]), project_id, view_id, states)
    board.validate()
    root = Path(worktree_root).expanduser().absolute() if worktree_root else data_root().parent / "worktrees" / identity
    root = root.resolve()
    inside = root == git.root or git.root in root.parents
    if inside and not allow_inside_repository:
        raise HandrailError("WORKTREE_LOCATION", "Repository-internal storage requires explicit --allow-inside-repository")
    if root == Path("/tmp") or Path("/tmp") in root.parents:
        raise HandrailError("WORKTREE_LOCATION", "Use persistent storage for review and resume worktrees")
    state_path = data_root() / "projects" / identity / "state.sqlite3"
    previous = read_json(state_path.parent / "project.json")
    if previous and previous["repo"] != str(git.root):
        raise HandrailError("CANONICAL_CHECKOUT_PINNED", "Run binding changes from the original canonical checkout")
    if previous and (previous["profile"], previous["project_id"], previous["view_id"], previous["endpoint"], previous["states"]) != (
            profile, int(project_id), int(view_id), endpoint, states):
        if any(Store(state_path).list(kind) for kind in ("plan", "room", "managed_board", "board_target", "card_override")):
            raise HandrailError("BINDING_IN_USE", "Active history pins its board and endpoint; use a separate project context")
    value = {"schema": 1, "workspace_id": identity, "repo": str(git.root), "common_dir": str(git.common_dir),
             "profile": profile, "project_id": int(project_id), "view_id": int(view_id), "states": states,
             "endpoint": endpoint, "worktree_root": str(root), "allow_inside_repository": inside,
             "child_projects": previous.get("child_projects", child_projects) if previous else child_projects,
             "board_routing": "explicit"}
    write_json(state_path.parent / "project.json", value)
    return value


def context(repo="."):
    identity, git = project_identity(repo)
    home = data_root() / "projects" / identity
    config = read_json(home / "project.json")
    if not config:
        raise HandrailError("PROJECT_NOT_BOUND", "Run handrail init in this repository to select a project and connect",
                            details={"next": "handrail init"})
    if config.get("schema") != 1 or config.get("common_dir") != str(git.common_dir):
        raise HandrailError("PROJECT_IDENTITY", "Stored Git identity does not match this checkout")
    # Commands issued from a worker checkout still resolve the canonical manager.
    from handrail.interfaces.git.repository import GitRepository
    canonical = GitRepository(config["repo"])
    if canonical.common_dir != git.common_dir:
        raise HandrailError("PROJECT_IDENTITY", "Canonical repository has been replaced")
    return {"config": config, "store": Store(home / "state.sqlite3"), "git": canonical}
