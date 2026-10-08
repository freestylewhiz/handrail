# Herdr rooms and workers

The coordinator calls the Handrail agentroom component, which controls existing Herdr using a pinned session selector or absolute socket path. This supports external orchestration as well as a coordinator inside a Herdr pane. `HERDR_ENV` indicates inherited execution context; it is not a credential or filesystem grant. Do not set it manually to bypass an in-pane skill guard.

Every target is explicit. Each attempt records room, pane, terminal, available provider conversation identity, and worktree. Do not substitute the focused pane or a reused name after identity mismatch. Recover with observed evidence. Herdr does not expose an atomic prior-identity compare-and-send operation; before/after checks mitigate rather than eliminate that race.

Distinguish:

- endpoint connectivity;
- command submitted or outcome uncertain;
- worker activity `working/blocked/idle/done/unknown`;
- response collected;
- changes reviewed and verified;
- card state and user acceptance.

A blocked worker may display a question or approval. Inspect the content before responding. `keys` requires a stored observation and the approved key action; a reason string alone is not permission to accept a new capability. Visible output does not cover all recent history. Use recent output to collect completed responses without equating a nonempty screen with the full answer.

Worktree retention and room closure are independent. Do not close another task's room or blindly press Enter to clear a dialog. Preserve active resources through Review.
