"""Project choices and resumable records of an explicit user decision."""
import sys
from urllib.parse import urlsplit
from handrail.shared.errors import HandrailError
from .interaction import ask, choose


def project_choices(projects, url):
    by_id = {p["id"]: p for p in projects}

    def ancestry(project):
        names, seen = [], {project["id"]}
        parent_id = project.get("parent_project_id") or 0
        while parent_id and parent_id not in seen:
            seen.add(parent_id)
            parent = by_id.get(parent_id)
            if parent is None:
                names.append("Parent #" + str(parent_id))
                break
            names.append(parent["title"])
            parent_id = parent.get("parent_project_id") or 0
        return list(reversed(names))

    rows = []
    for project in projects:
        if project.get("is_archived") or project.get("id", 0) <= 0:
            continue
        path = " / ".join(ancestry(project) + [project["title"]])
        link = url + "/projects/" + str(project["id"])
        rows.append({"name": project["title"], "label": path + " — " + link,
                     "value": project["id"], "url": link, "path": path,
                     "parent_project_id": project.get("parent_project_id") or 0})
    rows.sort(key=lambda row: (row["path"].casefold(), row["value"]))
    rows.append({"name": "new", "label": "Create a new parent board", "value": "new"})
    return rows


def project_value(value, url):
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        parsed, base = urlsplit(value), urlsplit(url)
        prefix = base.path.rstrip("/") + "/projects/"
        if (parsed.scheme, parsed.netloc) != (base.scheme, base.netloc) or not parsed.path.startswith(prefix):
            raise HandrailError("SETUP_PROJECT_URL", "Board link must belong to the selected server")
        return parsed.path[len(prefix):].split("/")[0]
    return value


def select_project(api, url, project=None, new_project=None, confirmed=False, saved=None):
    rows = project_choices(api.projects(), url)
    # Legacy drafts have no decision record. A candidate or inferred ID is not a decision.
    if project is None and new_project is None and isinstance(saved, dict):
        if saved.get("server") == url and saved.get("source") in ("user_terminal", "user_confirmed_argument"):
            if saved.get("kind") == "new" and isinstance(saved.get("value"), str) and saved["value"].strip():
                return saved
            if saved.get("kind") == "existing" and any(row["value"] == saved.get("value") and row["value"] != "new" for row in rows):
                return saved

    explicit = project is not None or new_project is not None
    if not sys.stdin.isatty() and (not explicit or not confirmed):
        raise HandrailError(
            "SETUP_INPUT_REQUIRED", "Show the board list and wait for the user's selection",
            details={"field": "project", "server": url, "choices": rows,
                     "requires_user_response": True, "allow_auto_select": False,
                     "execution_approval_is_selection": False,
                     "next": "Show every board name, parent path and link plus the new-board option. "
                             "Wait for the user's answer, then use --board VALUE or --new-board NAME "
                             "with --confirm-board-selection. Never infer a choice from a single candidate, "
                             "repository name or command execution approval."})
    source = "user_confirmed_argument" if confirmed and explicit else "user_terminal"
    if new_project is not None:
        title = new_project.strip()
        if not title:
            raise HandrailError("SETUP_SELECTION_INVALID", "Provide a nonempty new board name")
        return {"kind": "new", "value": title, "source": source, "server": url}
    chosen = choose("project", rows, project_value(project, url), automatic=False)
    if chosen == "new":
        title = ask("new_project", "New board name:")
        return {"kind": "new", "value": title, "source": source, "server": url}
    return {"kind": "existing", "value": chosen, "source": source, "server": url}
