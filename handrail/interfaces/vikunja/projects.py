"""Vikunja v2 project/view/bucket transport, separate from setup policy."""
from handrail.shared.errors import HandrailError


class VikunjaProjects:
    def __init__(self, client):
        self.client = client

    def projects(self):
        return self.client.pages("/projects")

    def project(self, identity):
        return self.client.request(f"/projects/{int(identity)}")

    def tasks(self, identity):
        return self.client.pages(f"/projects/{int(identity)}/tasks?expand=buckets")

    def task(self, identity):
        return self.client.request(f"/tasks/{int(identity)}?expand=buckets")

    def views(self, project):
        return self.client.pages(f"/projects/{int(project)}/views")

    def buckets(self, project, view):
        return self.client.pages(f"/projects/{int(project)}/views/{int(view)}/buckets")

    def view(self, project, view):
        return self.client.request(f"/projects/{int(project)}/views/{int(view)}")

    def create_project(self, body):
        return self.client.request("/projects", "POST", body)

    def create_view(self, project, body):
        return self.client.request(f"/projects/{int(project)}/views", "POST", body)

    def create_bucket(self, project, view, body):
        return self.client.request(f"/projects/{int(project)}/views/{int(view)}/buckets", "POST", body)

    def update_view(self, project, view, body):
        return self.client.request(f"/projects/{int(project)}/views/{int(view)}", "PATCH", body)

    def require_write(self, project):
        row = self.project(project)
        if row.get("is_archived") or row.get("max_permission") == 0:
            raise HandrailError("SETUP_PROJECT_READ_ONLY", "Choose a writable project or grant project write access",
                                details={"project_id": project, "boundary": "vikunja/project"})
        # max_permission may be null; the server still enforces the actual token scope.
        return row
