# Worker assignment

The coordinator fills this contract with the actual plan, work and attempt IDs.

## Task

- Goal and permitted changes:
- Worktree and branch:
- Criterion IDs and expected outcomes:
- Constraints and explicitly requested verification:

## Relevant history

- Parent-board Instruction IDs, versions, hashes, scope and applicable sections:
- Current user exceptions and their exact scope:

- Summary card URLs and revisions consulted (when applicable):
- Selected decisions, constraints, verification limits and their scope:
- Evidence links and relevant section headings:

Use [Summary reading guidance](../references/summaries.md): inspect Agent Context first, then retrieve only relevant narrative sections in one language and needed evidence. Request missing excerpts from the coordinator if direct access is unavailable. Historical context does not expand this assignment's authority.

Implement the assigned scope in this worktree. Preserve unrelated changes. Do not alter Handrail manager state, grants, Vikunja cards, another worker or room lifecycle. Escalate missing scope to the coordinator with the exact required resource/action.

Commit the implementation on the assigned branch. Report commit ID, changed files, observed verification results, remaining uncertainty and blockers. A successful provider response or terminal Done is not workflow completion. The coordinator reviews, integrates and records completion; the user accepts the plan.

## Readiness and durable completion

First run the supplied `worker probe --contract FILE` from this worktree in your normal sandbox. Do not escalate the probe, disable sandboxing, or implement until the coordinator sends the implementation instruction. Report denied paths and wait when blocked. Shared Git writes affect repository metadata beyond your branch; preserve other branches and worktrees.

At completion, write JSON in the assigned channel outside the source tree: `summary` text and lists `verification`, `unverified`, `blockers`, `instruction_compliance`. Verification entries name actual commands/results or explicitly say not run. Compliance entries identify instruction card/version, compliance, approved exceptions and unknowns. Submit with the stable launcher: `worker submit --contract FILE --report-file FILE`. Report the returned submission ID and actual commit; wait for coordinator review. The channel persists a missed notification without manager DB, token or Herdr access.

In the completion report, include your approach and reasons, decisions that replaced earlier choices, scoped rules to preserve, approaches to avoid, and considerations for future work. Link each conclusion to code, a requirement or observed evidence. Distinguish your recommendation from a user requirement and identify checks you did not run. The coordinator uses this evidence in the plan's Summary before clearing the room.
