# Herdr-backed plan workflow

Use this Herdr-backed plan workflow when the user chooses Herdr to coordinate workers. It is separate from the existing Handrail-managed `run` workflow; do not mix their commands or completion records within one work cycle. The CLI syntax below matches the current source interface. Release and acceptance status are tracked separately.

## CLI commands

Every command accepts `--repo`.

| Command | Arguments and flags |
| --- | --- |
| `status` | `PLAN_ID` |
| `recommend` | `PLAN_ID [--task-id TASK_ID]` |
| `assign` | `PLAN_ID TASK_ID --provider codex\|cursor --model MODEL [--reasoning-effort EFFORT]` |
| `start`, `prompt` | `PLAN_ID TASK_ID` and exactly one of `--instructions TEXT` or `--instructions-file PATH` |
| `collect` | `PLAN_ID TASK_ID` |
| `keys` | `PLAN_ID TASK_ID --key KEY` (repeatable) `--reason TEXT` |
| `recover` | `PLAN_ID TASK_ID --resolution delivered\|not-delivered --evidence TEXT` |
| `review` | `PLAN_ID TASK_ID --decision accept\|revise\|reject --notes TEXT` |
| `integrate` | `PLAN_ID TASK_ID` |
| `finish` | `PLAN_ID TASK_ID --evidence TEXT` |
| `verify`, `submit-review` | `PLAN_ID` |
| `accept` | `PLAN_ID --approval TEXT` |
| `reopen` | `PLAN_ID --reason TEXT [--clear yes\|no]` |
| `settings` | `[--clear-on-reopen ask\|always\|never]` |

Do not add flags by analogy or infer defaults beyond this contract. `recommend` is limited to neutral manual-assignment guidance; it must not choose or suggest an allocation.

`keys` is an explicit response to an inspected worker terminal prompt; record the prompt and authority in `--reason`. `recover` reconciles uncertain prompt delivery only after inspecting the worker terminal and records that inspection in `--evidence`.

## Workspace and worker identity

- Each registered parent plan has one Herdr space. Its label is the repository directory basename followed by the numeric plan ID in parentheses, for example `express-crud (314)`.
- Workers share that plan space. Each worker handles one linked work card, has the stable name `work-<numeric-work-ID>`, and uses its numeric work ID as its Herdr tab/pane label.
- Each task gets its own isolated Git worktree. A worker's edits stay in that worktree until the orchestrator reviews and integrates them.
- During user Review, retain the space and its worker sessions so the user can inspect them. Do not close the space on submission to Review; close only after the user accepts completion.
- A Herdr space is not a guaranteed complete transcript export or an indefinite archive. Workspace lifetime and transcript retention depend on Herdr behavior/configuration.

## Comments as an action log

Before every orchestrator action, add a comment to the parent plan card describing the intended action and its target. This applies to instruction/delegation, revision requests, worker start, completion, and every orchestrator operation such as review, integration, plan verification, review submission, acceptance, or reopening. Polling and read-only status checks are exempt. Comments should make the action and its task/worker identifiable, without copying secrets or unbounded terminal output. A failed or uncertain write must be reconciled before retrying to avoid duplicate actions.

## Manual worker selection

Worker allocation is manual. The orchestrator may explain available tasks and collect the user's choices, but it must not recommend workers/providers/models or make automatic selections. Ask the user to name the provider and model for every task before assignment. For example:

> Assign work card 421 to Cursor, model [model I specify] and work card 422 to Cursor, model [model I specify]. Start only after the approved task scopes are ready; ask each worker to implement its card and report changed files and verification performed.

The user can specify different providers and models per task. Do not infer a provider or model from a prior plan or worker assignment.

## Approval boundaries and lifecycle

Keep the existing user approval boundaries for plan scope, work-card specifications, and other approvals required by the active workflow. Each worker runs in its task worktree. Review the worker's output and diff before integration; run the approved checks and record actual evidence. A worker response alone is not completion.

When all required work is integrated and verified, submit the plan for user Review. Keep its Herdr space and worker history available while waiting. The user's explicit acceptance completes the plan and may close its Herdr space.

If the user requests changes during Review, reopen the plan from Review to Doing. Create new linked work cards for the revision round and preserve earlier completed cards and their evidence. Reassess needed roles and workers from the revised scope; never automatically copy the earlier allocation. The plan space remains the same unless the configured reopen behavior clears it.

Project setting `clear_on_reopen` controls that behavior:

- `ask` (default): ask whether to clear the worker space and require an explicit answer before reopening proceeds.
- `always`: clear the existing worker space on reopen.
- `never`: retain the existing worker space on reopen.

An unanswered question under `ask` is not consent to either choice and must not be treated as a default to clear or retain.
The setting is persisted in `XDG_DATA_HOME/handrail/projects/<workspace-id>/herdr.json` as project-local workflow state.

## Startup stalls and uncertain prompt delivery

Herdr may report `agent_not_ready`, a stalled startup, or uncertain prompt delivery. Collect and inspect the visible terminal before taking action. Never blindly resend an instruction after an ambiguous timeout or stall.

If the exact approved instruction is visibly waiting in the input buffer, and there is no indication it was already accepted, submit that input once and record the inspection:

```sh
handrail herdr keys PLAN_ID TASK_ID --key enter --reason 'Inspected the visible terminal: the exact approved instruction is in the input buffer; no response indicates delivery.'
handrail herdr recover PLAN_ID TASK_ID --resolution delivered --evidence 'Inspected the visible terminal and confirmed the exact approved instruction was submitted; worker output shows it is being processed.'
```

Use `--resolution not-delivered` only when inspection shows the instruction was not delivered. If input is partial, differs from the approved instruction, or delivery remains ambiguous, do not send Enter and do not mark it delivered; continue inspection or ask the user. `keys` requires repeatable `--key KEY` plus `--reason TEXT`; `recover` requires `--resolution delivered|not-delivered` plus `--evidence TEXT`.

## Legacy workflow

The established Handrail run workflow remains available for repositories and tasks that are not using Herdr orchestration. It uses Handrail-managed run worktrees, saved grants and delegation, verification, review, integration, and synchronization. Follow the bundled skill's existing run workflow instructions for that path; do not silently mix legacy run lifecycle commands with a Herdr-managed task.
