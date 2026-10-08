# Board and card administration

Use the absolute stable launcher for agent execution. Examples use the concise host command. `--repo PATH` goes before `board` or `card`. Reuse the connected parent board, credentials and saved HTTP choice. These commands do not require Herdr, a clean Git checkout, a worker, Plan approval or implementation evidence.

## Child boards

For “add frontend and backend child boards”, run one command:

```sh
handrail board add frontend backend
handrail board list
```

`add` prepares a manual Kanban view and Todo/Doing/Done columns, records management history, and returns links. It creates no Plan/Work cards. Preserve the user's spelling. A repeated request reuses a managed board. On `BOARD_EXISTS`, show existing links and ask whether to use the existing board or a different name; use `--reuse-existing` only after that choice. If multiple matches exist, use the selected link with `board register BOARD`. Do not invent new names or duplicate an uncertain write.

`board register BOARD [--view VIEW] [--state todo=COLUMN]` prepares/registers an existing descendant board. Only request mapping choices the command reports as ambiguous. Existing pinned mappings are retained. `board history` reads the local administration journal. Partial batch results retain completed boards; retry the same names after addressing the returned error. Unknown setup writes use the operation ID and existing `setup-resolve` procedure after inspecting actual remote resources.

## Card states requested by the user

Distinguish a display-state request from final review acceptance. When the user says they reviewed and approve/complete a managed plan, use `plan complete PLAN_OR_CARD --approval ...` and the Summary/cleanup flow in [workflow.md](workflow.md). Reserve `card move --force` for explicit status-only changes; never treat a forced Done as user acceptance or automatically clear its sync hold.

Resolve a card from its link, ID, exact title, local Plan/Work ID, or prior conversation. If needed, `card list [--board NAME_OR_LINK]` lists live cards in the connected parent hierarchy. Same-title cards require a user choice. Do not ask for an internal ID when the target is already clear.

```sh
handrail card move CARD --state done --force --reason 'User asked to move this card to Done'
```

The reason records the actual user instruction; it is an attestation, not authentication or host permission. Supported states are todo, doing, review and done, subject to the selected board's existing columns. Never use this command autonomously to get past development verification errors. An explicit user request is sufficient: do not require worker execution, a model, a clean checkout, integration, or a second approval question. Do not also run `work complete` or `plan accept` to manufacture development completion.

The result includes previous/new card state and the local workflow state when managed. Report “카드를 Done으로 변경했습니다” and the link. Do not claim implementation was verified. It holds automatic **state** sync for that card until the user asks to resume it. Workers and resource lifecycles continue independently; the command does not stop workers, close rooms, or remove worktrees. Ongoing workflow comments may still sync.

For a timeout, keep the returned operation ID. The same move reconciles a visible target state without sending it twice. If uncertain and not observed at the target, inspect the remote card and then use `card resolve OPERATION_ID --evidence REASON` only when the earlier write is confirmed not applied. Resolution makes no remote writes. A definite rejection can retry after its actual cause is fixed.

When the user requests automatic state sync again:

```sh
handrail card resume CARD --reason 'User requested automatic state sync again'
handrail sync --topic board
```

`resume` queues the current workflow state for managed cards. Older pending state events are suppressed. An uncertain move must be reconciled first. An unmanaged card has no workflow to resume. Do not resume sync merely because a worker reports progress.

## Connecting implementation work to boards

Use existing boards for real implementation tasks. `board assign PLAN --board frontend` sets the destination for future Work cards under that Plan; the Plan card remains on the parent board. `board assign WORK --board backend` selects that Work's destination before its first sync. Multiple Plans may share a board. Assignments do not relocate existing cards. Legacy card locations remain pinned.

In alpha.6, Work creation/start prepares a missing shared default board with Todo/Doing/Review/Done before projection. `board prepare-work WORK` resumes that preparation. An unrelated board named default requires one explicit selection using `board default BOARD --reason USER_SELECTION`. Registry identity includes server and parent and is shared across repositories on this host. New work is never placed on the parent because assignment was missing. Existing cards keep their location; adding Review retains existing column mappings. Sync does not create boards.

## Host permissions

Reuse existing authorization. If the host blocks private-state or API access, use its supported approval mechanism for the concrete `board add` or `card move` command. Keep one batch of child boards in one invocation. Never request general Python or shell access. User intent recorded by Handrail does not lift the host sandbox or Vikunja token scope.
