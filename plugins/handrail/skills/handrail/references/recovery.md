# Recovery

## Broken runtime during setup

`INSTALLATION_BROKEN`, or an internal `ImportError` in an older release, requires a corrected Handrail package. Keep the version/path from `locate`, the failed command and saved setup/write intents. Report that setup is blocked; never present a partial binding as connected. Do not reinterpret this as denied filesystem/network authority or send the same failing initialization repeatedly.

Ordinary repository setup does not include developing a patch in release/cache directories. For an explicit Handrail repair request, fix the source, pass the build's static named-import audit, create a consistent bundle and replace the managed release. Then the original coordinator can resume setup with its existing selections. Do not delete configuration, recreate remote resources or alter build-info hashes to hide a local patch. The audit covers named internal imports, not functional behavior; report actual verification limits.

## Done cleanup in alpha.6

Use `plan cleanup PLAN --inspect` to observe pinned/current identities and obtain an observation token. Continuous process evidence can enrich a late provider conversation ID automatically. For a legacy missing identity, inspect its completed launch receipt and owned-worktree process evidence; then use `--reconcile TOKEN --evidence OBSERVATION`. Actual changes or unavailable evidence stay blocked. This does not create Work/Attempt, reset the cycle or undo acceptance.

Use `plan cleanup PLAN --resume` to retry the existing close choice; then `sync --topic room.cleanup` reconciles pending delivery receipts. Identity enrichment does not expand the resource scope or require another close choice. Changed room/pane/terminal/ownership does. Never substitute direct Herdr close to clear an identity error. A parsed workspace-not-found result can reconcile an already authorized closure; generic connection errors cannot. Nested failed/unknown cleanup returns nonzero while Plan Done remains recorded. Shared, busy and unproven occupants remain protected; worktrees remain.

Start from local `status` and `history`, then inspect the explicitly recorded endpoint and attempt. Reads do not require rerunning a failed write.

Keep stable operation IDs. A process interrupted after intent persistence may have sent the request. `sending/unknown` is not evidence of non-delivery. Do not generate a new ID to bypass an unresolved instruction.

- Prompt: inspect the actual response, then `worker resolve-message OPERATION --outcome delivered|not_delivered --evidence ...`. Confirmed non-delivery prepares the same operation for an exact retry. Resume `worker start` or `worker continue` with the original request; for an explicit prompt, keep its message ID and text. Changed instructions use a new message ID after the earlier delivery is resolved.
- Worker loss: inspect the replacement's room, pane, terminal, provider conversation and original worktree, then `worker recover OLD_ATTEMPT --target LIVE_TARGET --evidence ...`. Do not mark business work complete based on recovery.
- Room creation response loss: inspect the exact room and original creation intent before using `room adopt PLAN WORKSPACE --origin-operation OP --owned-pane PANE --evidence ...`. Select only owned panes and bind those IDs and the origin operation in the recovery scope. Do not adopt an unrelated space just because its cwd matches.
- Board response loss: `sync` reads existing operation markers before completing delivery. Missing or ambiguous markers require reconciliation; do not blindly create another card or comment.
- Integration conflict: preserve the repository and resolve the actual Git state. Do not reset unrelated changes. The reviewed candidate and resulting integration commit must remain connected.
- Cleanup: user acceptance remains recorded if cleanup fails. Retain resources and resolve the cleanup boundary separately. Never delete a worktree with uncommitted or unintegrated work.

Configuration changes do not relocate existing attempt paths. Historical failures remain in the journal; live observations and workflow state describe the current situation separately.

## Summary and completion

Use `summary resolve OPERATION_ID --evidence ...` for uncertain Summary writes, then repeat publication or `sync --topic summary`. Preserve external edits with a fresh `summary prepare`; never invent an expected hash. `plan complete` records workflow acceptance separately from board/Summary delivery outcomes. Cleanup is resumed only after recorded close consent; keep preserves resources. The previous version is archived in the same Summary card's comments.
