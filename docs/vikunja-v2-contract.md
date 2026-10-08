# Vikunja v2 contract

Verified against a fresh official Vikunja 2.6.0 development instance.

- OpenAPI: `/api/v2/openapi.json`
- SHA256: `47414f4a2bfb7e22469fc5b9d462b0182f96abf58f7fe37054dbb77fb00ee1dd`
- Collections use `{items, page, per_page, total, total_pages}`; empty `items` may be null. Server page limit is 50.
- API token permission names from `/routes` retain legacy names and may display v1 paths; v2 uses the operation-specific verbs below.
- Binding reads existing projects, views and buckets. After previewing the selected parent project/view and existing state mapping, it may create only a missing Review bucket with `POST /projects/{project}/views/{view}/buckets`; it rereads the list and verifies exactly one Review before saving the local binding. Permission denial does not prompt for wider token scope. A denied create directs the user to add Review manually. Uncertain writes are reconciled by rereading before any retry.
- Requested child areas use `POST /projects` with `parent_project_id`, then reuse one manual Kanban view or create one when missing. Worker boards map Todo/Doing/Done; Review is optional and is never created as a child-board prerequisite. Read back project ancestry, view defaults and bucket IDs before registering the local area. Project creation, view creation/update and bucket creation require their own project permissions and API token route permissions.
- A manual Kanban view has `view_kind=kanban`, `bucket_configuration_mode=manual`; a configured done bucket must match the done mapping.
- Task reads with `?expand=buckets` return per-view bucket membership; the scalar `bucket_id` alone is insufficient outside a view query.
- Task relation reads use `GET /tasks/{id}?expand=subtasks`. The response contains `related_tasks.subtask` and the inverse `related_tasks.parenttask`; `expand=related_tasks` is rejected with HTTP 422.
- `POST /tasks/{id}/relations` with `{"other_task_id": CHILD_ID, "relation_kind": "subtask"}` creates the actual relation, including across projects. Read back both cards to verify membership. This is separate from project ancestry. The parent task requires write access and the referenced task read access, plus the API token's relation-create route permission. Giving only task/project CRUD scopes does not imply every relation or bucket route is allowed.
- Actual conditional-write probe: `GET /tasks/1` returned an ETag, but a `PATCH` with deliberately stale `If-Match` returned HTTP 200. Do not claim atomic compare-and-set based on that read header. Check expected remote state before writing and read it back afterward; this server still has a concurrency window. Uncertain write responses require reconciliation before retry.

| Method | API-relative path | Operation |
| --- | --- | --- |
| `GET` | `/info` | `info` |
| `GET` | `/projects` | `projects-list` |
| `POST` | `/projects` | `projects-create` |
| `GET` | `/projects/{id}` | `projects-read` |
| `PATCH` | `/projects/{id}` | `patch-projects-read` |
| `PUT` | `/projects/{id}` | `projects-update` |
| `DELETE` | `/projects/{id}` | `projects-delete` |
| `GET` | `/projects/{id}` | `projects-read` |
| `PATCH` | `/projects/{id}` | `patch-projects-read` |
| `PUT` | `/projects/{id}` | `projects-update` |
| `GET` | `/projects/{project}/tasks` | `project-tasks-list` |
| `POST` | `/projects/{project}/tasks` | `tasks-create` |
| `GET` | `/projects/{project}/views` | `project-views-list` |
| `POST` | `/projects/{project}/views` | `project-views-create` |
| `DELETE` | `/projects/{project}/views/{view}` | `project-views-delete` |
| `GET` | `/projects/{project}/views/{view}` | `project-views-read` |
| `PATCH` | `/projects/{project}/views/{view}` | `patch-project-views-read` |
| `PUT` | `/projects/{project}/views/{view}` | `project-views-update` |
| `GET` | `/projects/{project}/views/{view}/buckets` | `buckets-list` |
| `POST` | `/projects/{project}/views/{view}/buckets` | `buckets-create` |
| `PUT` | `/projects/{project}/views/{view}/buckets/{bucket}/tasks` | `task-bucket-update` |
| `GET` | `/tasks/{task}/attachments` | `task-attachments-list` |
| `POST` | `/tasks/{task}/attachments` | `task-attachments-upload` |
| `DELETE` | `/tasks/{task}/attachments/{attachment}` | `task-attachments-delete` |
| `GET` | `/tasks/{task}/attachments/{attachment}` | `task-attachments-download` |
| `GET` | `/tasks/{task}/comments` | `task-comments-list` |
| `POST` | `/tasks/{task}/comments` | `task-comments-create` |
| `POST` | `/tasks/{task}/relations` | Create task relation |
| `DELETE` | `/tasks/{task}/relations/{relationKind}/{otherTask}` | Remove task relation |
| `GET` | `/user` | `user-show` |

| `DELETE` | `/tasks/{projecttask}` | `tasks-delete` |
| `GET` | `/tasks/{projecttask}` | `tasks-read` |
| `PATCH` | `/tasks/{projecttask}` | `patch-tasks-read` |
| `PUT` | `/tasks/{projecttask}` | `tasks-update` |
