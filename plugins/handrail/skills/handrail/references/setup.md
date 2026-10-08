# Setup and repository connection

The ordinary entry point is `handrail init` inside the selected Git repository. Agents use the absolute `stable_launcher` from `handrail locate`, followed by `--repo ABSOLUTE_REPO` before `init`. The shorter host command is for user terminal instructions. Both use the managed release outside the versioned Codex cache.

## Agent flow

1. Run `init` once. Saved connections and completed selections are reused. Do not ask for connection names, internal IDs, a states JSON file, or socket paths in advance.
2. For `SETUP_INPUT_REQUIRED`, ask only for the returned field and wait for the answer. For `field: project`, show **every returned board** with its name, parent path and link, plus creation of a new parent board. Do not filter by the repository name, preselect the first item, or skip the question when only one board exists. If a question tool limits option count, show the full list and accept a name/link/number as free text. A host execution approval is not a board decision. Resume only after an actual user choice, using `init --board NAME_OR_LINK --confirm-board-selection`, or `init --new-board NAME --confirm-board-selection`. If the user already explicitly named this repository's target board, reuse that decision without another question. The confirmation flag is internal; do not ask the user to type it or add a second confirmation question. Multiple views use `--view`, ambiguous columns use `--state review=NAME_OR_ID`, and endpoints use `--socket` or `--session`. Reuse already supplied options when resuming.
3. If no connection exists, obtain the server URL. Give the user one terminal command for hidden token entry. For HTTP, always include `--allow-insecure-http` and explain that it explicitly permits this HTTP connection. A saved HTTP choice is reused. Never request a token in chat or as an argument.

```sh
handrail setup --url https://vikunja.example.com
handrail setup --url http://vikunja.internal:3456 --allow-insecure-http
```

4. After token entry, resume `init` yourself when authorized to set up this repository. A single connection is reused automatically; multiple connections are shown by name and URL. Invalid credentials can be replaced with `setup --replace-token` in the user's terminal.
5. The selected parent's unfiltered manual Kanban is discovered. Missing Todo/Doing/Review/Done columns are prepared, existing ones reused, and default/done mapping saved. Reuse setup authorization instead of asking again for every necessary column. API/token permissions are still enforced. Retain unrelated columns/views.
6. Herdr discovery reads actual endpoints, never starts a session, and never injects `HERDR_ENV`. Saved/explicit endpoints are pinned. On access denial, report the actual IPC boundary and use the host's normal approval mechanism when needed. Do not ask the user to guess another socket.
7. Worktree storage defaults to persistent `.handrail-worktrees/<repository-identity>` next to the checkout. `--worktree-root` overrides it. Setup checks its own writes to checkout/common-directory/private-state/worktree paths and groups failures. This does not prove a worker's sandbox access. If the default lies outside an allowed root, select an authorized persistent external location or request the required path access.
8. Report the connected project link, Herdr connection, worktree path and remaining blockers. When connected, invite the implementation request without another command checklist.

## Terminal flow

`handrail init` prompts for only missing decisions, including a hidden token when first connecting. For HTTP it asks once whether to allow that saved connection. Users who already saved a connection only choose a parent board. Repeating `init` checks and reuses an existing binding.

Noninteractive `--board` and `--new-board` on an unbound repository require `--confirm-board-selection`. Without it, the CLI returns the full board list and `requires_user_response: true`, `allow_auto_select: false`; it does not provision or bind the board. The flag is an agent attestation, not proof that a conversation occurred or a grant of filesystem/API permissions. Follow the actual user decision. Interactive user terminals retain the ordinary menu and explicit argument flow.

## Child projects and recovery

After connection, use `board add NAME [NAME ...]` to add child boards on user request. See [boards.md](boards.md). Plan cards stay on the parent. New Work cards use an assigned or prepared default work board before first projection. Existing cards retain their recorded location, including legacy parent-board cards. Sync does not create child boards. The legacy `child_projects` field is retained for compatibility with existing card locations.

Setup stores partial selections and durable remote-write intents. Timeouts are not permission to create again. Inspect the actual resource, then use `setup-resolve OPERATION_ID --evidence REASON` only after confirming the previous write did not apply. Repeat the original init/sync command afterward. A permissions rejection can be retried after fixing the actual permission.

For filesystem or network denial, reuse an available host approval for the exact launcher/repository/operation. If host approval is needed, propose that narrow reusable prefix. An internal missing module/function is a package defect: report it with `locate` and preserve the setup draft for a corrected release. Repeating escalation or editing cached/installed Python does not repair the distributed product.

Confirmed board decisions are saved with the selected server and reused after an interrupted setup. Legacy unfinished drafts without a decision record ask again; completed bindings are kept, including those created before alpha.3.

Advanced `bind` remains available for explicit mappings. It is not the ordinary onboarding path. v0.5 data is preserved but not migrated. Existing alpha.1 bindings retain their original layout; never silently rebind or move existing cards.

User-facing terms are board/parent board/child board. `--board`, `--new-board`, and `--confirm-board-selection` are the preferred options; the older project-named options and JSON `field: project` remain compatibility aliases/fields.
