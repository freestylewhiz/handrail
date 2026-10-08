# Herdr workflow acceptance design

This document defines the repeatable acceptance exercise and records the observed 2026-10-02 run below. Design expectations and measured results are separated.

## Isolated Vikunja fixture

- Use the host-accessible Vikunja test instance (this run: `http://192.168.0.172:58821`) and the dedicated project `handrail_v0.5`.
- Create or identify two child projects beneath it: `frontend` and `backend`. Use them only for this acceptance exercise.
- The scenario is an Express employee CRUD API and web interface. Prepare an approved parent plan and linked frontend/backend work cards with separate, observable scopes and checks.
- Use Cursor Auto workers for the assigned tasks. The user must explicitly name the worker/provider/model per task; no automated allocation or recommendation is part of the expected behavior.
- Use the test repository and isolated task worktrees. Do not point this scenario at a production Vikunja project or unrelated checkout.

## Expected path

1. Confirm the plan, child project registrations, linked cards, approved scopes, and checks. Confirm the test project and repository before any writes.
2. Create/reuse the plan space using the repository directory basename and numeric plan ID. Assign each work card its `work-<numeric-ID>` worker name and numeric pane label. Start each worker in its own worktree.
3. Verify that the parent plan receives an action comment before each instruction/delegation, revision, worker start, completion, and orchestrator action. Polling/read-only status checks need no comment.
4. Collect worker output, review the actual diffs, integrate accepted changes, and run the approved checks. Record only observed evidence.
5. Submit the plan to Review. Confirm that the plan remains in Review and the Herdr space and worker history remain available for user inspection.
6. Exercise both user outcomes in separate plan cycles or isolated fixture plans:
   - **Done path:** user explicitly accepts; the plan becomes Done, acceptance is logged, and the plan space is closed after acceptance.
   - **Revision path:** user requests changes; the plan returns from Review to Doing, new work cards capture the requested revisions, completed earlier work cards remain intact, and the existing plan space is retained or cleared only according to an explicit `clear_on_reopen` answer/policy.
7. With `clear_on_reopen=ask`, verify that reopening pauses for an explicit clear/retain answer. Also exercise configured `always` and `never` behavior if those modes are in scope for the run.

## Acceptance observations

Capture the following without inventing results:

- Vikunja parent and child project IDs, plan/work card IDs, and before/after states.
- Herdr plan space label/ID, worker names, pane labels/IDs, selected Cursor model, and per-task worktree paths.
- Parent comments corresponding to each required action, in order, including revision and completion events.
- Diffs reviewed and integrated, check IDs and raw outcomes/evidence, and any failures or recovery steps.
- Review behavior, explicit user decision, and resulting state transition for both Done and revision paths.
- Which work cards were created for the revision and confirmation that previous completed cards/evidence were preserved.
- Whether the Herdr space/workers remained inspectable during Review and the observed result of reopen cleanup policy.

Report failed or skipped expectations plainly. A passing write or worker response does not by itself establish acceptance; include verification evidence and final remote state.

## Scoped cleanup

After capturing evidence, clean up only resources created for this exercise under the `handrail_v0.5` test project and its `frontend`/`backend` children. Do not delete pre-existing cards, projects, repository content, or unrelated Herdr spaces. Preserve the acceptance record and any resources needed for user review unless the test owner explicitly directs cleanup. Record what was removed and what was intentionally retained.

## Observed run — 2026-10-02

Implementation branch: `support-herder`; runtime/package: `0.5.0`.
Implementation assistants used GPT-6-LUNA low. All live Herdr workers used Cursor Auto.
Existing locally stored credentials were loaded in memory; no token was placed in source, prompts, arguments, or these artifacts.

| Check | Cycle 1 | Cycle 2 |
| --- | --- | --- |
| Source repo | `/project_workspace/handrail_poc/herdr-employee-crud` | `/project_workspace/handrail_poc/herdr-employee-repeat` |
| Parent project / view | 13 / 56 | 13 / 56 |
| Frontend / backend projects | 14 / 15 | 16 / 17 |
| Plan task | 13 | 17 |
| Initial backend / frontend work | 14 / 15 | 18 / 19 |
| New correction work | 16, frontend count | 20, email normalization; 21, refresh button; 22, run guide |
| Workspace | `wQ`, `herdr-employee-crud (13)` | `wR`, cleared; `wS`, `herdr-employee-repeat (17)` |
| Review feedback policy | `ask` returned a question without changing state; explicit `no` retained space | persisted `always` cleared old space; restored `ask` afterward |
| Result | simulated user acceptance → Done; `wQ` closed | Review, all five required work cards Done; `wS` and workers 20/21/22 retained |
| Parent action comments at capture | 47 | 56 |

### Functional and lifecycle checks

- Express scaffolds were generated with `express . --no-view` in separate Git repositories.
- Both child boards have Todo/Doing/Done only. Their creation did not add or require Review.
- The orchestrator created parent/child cards, approved scoped specs/checks and emitted manual worker-selection guidance before explicit Cursor Auto assignment.
- API checks passed: list/create/get/update/delete, validation failure 400, missing record 404, create 201, delete 204.
- Actual headless Chromium checks passed: create/read/update/delete from the UI, user HTML displayed as text, no injected image element, API error feedback and no JavaScript errors.
- Cycle 1 correction: browser verified employee count 0 → 1 → 0. A further orchestrator instruction requested `aria-live="polite"`; its revision request is in the parent comments.
- Cycle 2 correction: browser/API checks verified lowercase email on create and update and Refresh loading a record created externally.
- Workers 20 and 21 were observed working concurrently in the same `wS` space, in separate tabs/worktrees. Their shared-base patches integrated sequentially without overwriting each other.
- Review was submitted only after accepted diffs, integration commits, child checks and parent aggregate verification. Review retained the real worker sessions.
- Both simulated user outcomes ran: accepting closed the owned space; reopening created new work while preserving prior completed cards.
- After cycle 1 evidence capture, the first repository was unbound and only children 14/15 under parent 13 were deleted. The repeat created fresh children 16/17 and a fresh binding. Parent project 13 and completed plan 13 were retained. Historical child evidence was exported before deletion.

### Faults found and corrected

1. Vikunja ignores an empty description PATCH. Area creation now reports successful registration with `recovery_marker_retained=true` when the exact operation marker is the only remaining text; other mismatches still fail. Both new cycle 2 boards created successfully.
2. Herdr responses use nested workspace/pane handles. The adapter now extracts native handles and uses a tab per worker, so a closed initial pane or narrow split does not prevent adding workers.
3. Herdr may report an idle agent before its input widget is ready. Startup now requires stable visible input as well as reported readiness. The final fresh worker 22 started and received its task without manual recovery.
4. A prompt can be rejected before input (`agent_not_ready`) or remain unsubmitted in the terminal (`agent_prompt_stalled`). Only definite pre-input rejection has a bounded retry. For ambiguous delivery, the orchestrator inspected the screen, used audited Enter for the exact buffered instruction where appropriate, and recorded explicit recovery. No blind resend is treated as success.
5. Review and integration require an idle/done worker, accepted unchanged diff and Git ancestry. New parallel work can integrate after earlier work from the same base. Integration intents and close/reopen intents are persisted for recovery.
6. New runtime modules and the Herdr skill reference are included in the distribution allowlists; version assertions derive from the current runtime version.

### Evidence and reproduction

- [Cycle 1 API/card evidence](evidence/herdr-v0.5-cycle1.json)
- [Cycle 2 API/card/Herdr evidence](evidence/herdr-v0.5-cycle2.json)
- Functional test sources remain in each test repository's `tests/api.test.js` and `tests/browser.cjs`.
- Run API checks with `node --test tests/api.test.js` from the test repository.
- Browser checks use Playwright installed outside the tested app: `HANDRAIL_PLAYWRIGHT=/tmp/handrail-browser-tool/node_modules/playwright node tests/browser.cjs`. For a future host, provide its own Playwright installation and Chromium; this temporary path is not a runtime dependency of Handrail.
- Unit/integration suite: `python3 -m unittest discover -s tests`. The two opt-in tests requiring separately configured disposable services are reported as skipped, independently of the live host scenario above.
- Final observed suite: 202 tests run, 200 passed, 2 skipped, no failures (20.714 seconds). Includes real Git integration, manual recommendation, busy worker guard, uncertainty without resend, close/reopen recovery, child Done gate, CLI and distribution tests.
- Build: `python3 scripts/build_plugin.py --output dist/v0.5.0`; validate: `python3 scripts/validate_distribution.py dist/v0.5.0`.

The evidence captures observed comments and state, not a claim that Herdr exports a permanent full CLI transcript. Review sessions remain available until explicit close; clearing a space removes that live terminal access. Worker worktrees and Handrail's local journal are retained.
