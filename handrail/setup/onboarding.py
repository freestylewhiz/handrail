"""One repository setup flow: reuse connection, select project, prepare and bind."""
from pathlib import Path
from handrail.shared.errors import HandrailError
from handrail.shared.identity import digest
from handrail.shared.store import Store
from handrail.interfaces.vikunja.client import VikunjaClient
from handrail.interfaces.vikunja.projects import VikunjaProjects
from . import settings, discovery
from .project_selection import select_project
from .provisioning import Provisioner
from .write_access import check_writes


def setup_store():
    return Store(settings.data_root() / "setup.sqlite3")


def client_for(profile):
    saved = settings.connection(profile)
    return VikunjaClient(saved["url"], saved["token"], allow_insecure_http=saved["allow_insecure_http"])


def initialize(repo=".", connection=None, url=None, project=None, new_project=None,
               view=None, endpoint=None, worktree_root=None, allow_insecure_http=False,
               state_selection=None, confirm_project_selection=False):
    identity, _ = settings.project_identity(repo)
    with setup_store().exclusive("onboarding:" + identity):
        return _initialize(repo, connection, url, project, new_project, view, endpoint,
                           worktree_root, allow_insecure_http, state_selection, confirm_project_selection)


def _initialize(repo, connection, url, project, new_project, view, endpoint,
                worktree_root, allow_insecure_http, state_selection, confirm_project_selection):
    identity, git = settings.project_identity(repo)
    home = settings.data_root() / "projects" / identity
    previous = settings.read_json(home / "project.json")
    draft_path = home / "setup.json"
    draft = settings.read_json(draft_path, {})
    if previous:
        # Existing execution scopes and board mappings are never silently replaced.
        for supplied, actual in ((connection, previous["profile"]), (endpoint, previous["endpoint"]),
                                 (worktree_root, previous["worktree_root"])):
            if supplied is not None and supplied != actual:
                raise HandrailError("SETUP_ALREADY_BOUND", "This repository is already connected; keep its existing binding")
        if new_project:
            raise HandrailError("SETUP_ALREADY_BOUND", "This repository already has a parent board")
        client = client_for(previous["profile"])
        remote = VikunjaProjects(client).project(previous["project_id"])
        if project is not None and str(project) not in (str(remote["id"]), remote["title"], client.url + "/projects/" + str(remote["id"])):
            raise HandrailError("SETUP_ALREADY_BOUND", "Selected board differs from the stored binding")
        if url and url.rstrip("/") != client.url:
            raise HandrailError("SETUP_ALREADY_BOUND", "Selected server differs from the stored binding")
        if view is not None:
            current_view = VikunjaProjects(client).view(previous["project_id"], previous["view_id"])
            if str(view) not in (str(previous["view_id"]), current_view["title"]):
                raise HandrailError("SETUP_ALREADY_BOUND", "The existing view is pinned")
        if state_selection:
            columns = VikunjaProjects(client).buckets(previous["project_id"], previous["view_id"])
            for state, selected_column in state_selection.items():
                bucket = next((b for b in columns if b["id"] == previous["states"].get(state)), None)
                if not bucket or str(selected_column) not in (str(bucket["id"]), bucket["title"]):
                    raise HandrailError("SETUP_ALREADY_BOUND", "The existing column mapping is pinned")
        discovery.probe(previous["endpoint"])
        from handrail.interfaces.vikunja.board import VikunjaBoard
        VikunjaBoard(client, previous["project_id"], previous["view_id"], previous["states"]).validate()
        return summary(previous, remote["title"], client.url, reused=True)

    connection = connection or (draft.get("connection") if not url else None)
    selected = settings.connection_setup(connection, url, allow_insecure_http)
    connection = selected["connection"]
    if draft.get("connection") not in (None, connection):
        draft = {}
    draft["connection"] = connection
    settings.write_json(draft_path, draft)
    client = client_for(connection)
    api, provision = VikunjaProjects(client), Provisioner(client, setup_store())

    # Resolve host resources before any remote write; retain completed selections.
    root = Path(worktree_root or draft.get("worktree_root") or
                (git.root.parent / ".handrail-worktrees" / identity)).expanduser().resolve()
    if root == git.root or git.root in root.parents or root == Path("/tmp") or Path("/tmp") in root.parents:
        raise HandrailError("WORKTREE_LOCATION", "Select persistent storage outside the repository and /tmp")
    draft["worktree_root"] = str(root)
    settings.write_json(draft_path, draft)
    issues = []
    try:
        endpoint = discovery.discover(endpoint, draft.get("endpoint"))
        draft["endpoint"] = endpoint
        settings.write_json(draft_path, draft)
    except HandrailError as exc:
        if exc.code in ("SETUP_INPUT_REQUIRED", "SETUP_CANCELLED"):
            raise
        issues.append(exc.as_dict())
    try:
        check_writes([("canonical checkout", git.root), ("Git metadata", git.common_dir),
                      ("private state", home), ("worker sources", root)])
    except HandrailError as exc:
        issues.append(exc.as_dict())
    if issues:
        raise HandrailError("SETUP_ENVIRONMENT_REQUIRED", "Resolve the listed connection/access issues, then resume handrail init",
                            details={"issues": issues, "host_permission": "not_granted_by_handrail"})

    decision = select_project(api, client.url, project, new_project, confirm_project_selection,
                              draft.get("project_selection"))
    previous_decision = draft.get("project_selection", {})
    if (decision["kind"], decision["value"]) != (previous_decision.get("kind"), previous_decision.get("value")):
        draft.pop("project_id", None)
        draft.pop("view_id", None)
        draft.pop("states", None)
    draft.pop("new_project", None)
    draft["project_selection"] = decision
    settings.write_json(draft_path, draft)
    if decision["kind"] == "new":
        title = decision["value"]
        parent = provision.project("repository:" + identity + ":" + digest(title), title)
    else:
        parent = api.project(decision["value"])
    if draft.get("project_id") != parent["id"]:
        draft.pop("view_id", None)
        draft.pop("states", None)
    draft["project_id"] = parent["id"]
    settings.write_json(draft_path, draft)
    selected_states = dict(draft.get("states", {}))
    selected_states.update(state_selection or {})
    mapping = provision.board(parent["id"], view or draft.get("view_id"), selected_states)
    draft.update(mapping)
    settings.write_json(draft_path, draft)
    config = settings.bind(repo, connection, mapping["project_id"], mapping["view_id"], mapping["states"],
                           endpoint, str(root), child_projects=False)
    return summary(config, parent["title"], client.url)


def summary(config, title, url, reused=False):
    from .diagnostics import preflight
    return {"status": "connected", "reused": reused, "repo": config["repo"],
            "board": {"name": title, "url": url + "/projects/" + str(config["project_id"])},
            "project": {"title": title, "url": url + "/projects/" + str(config["project_id"])},
            "columns": list(config["states"]), "herdr": {"endpoint": config["endpoint"], "reachable": True},
            "worktree_root": config["worktree_root"], "child_projects": config.get("child_projects", False),
            "board_management": True, "board_routing": "explicit",
            "preflight": preflight(config["repo"]), "next": "Describe the implementation work you want to start"}
