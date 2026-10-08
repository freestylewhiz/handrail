# Card authoring and project instructions

## Plan and task layout

Supply `--presentation-file` with each new Plan/Work. The coordinator writes this temporary JSON; the user need not author it. Use one complete English block followed by a complete block in the user's non-English language. Each block has overview, details grouped by concern, then a compact two-column criterion/expected-outcome table. Criteria are expectations, not evidence of passed checks.

```json
{
  "language": "ko",
  "en": {
    "overview": "Goal and reason.",
    "sections": [{"title": "Scope", "paragraphs": ["Concrete scope."], "items": ["Constraint."]}],
    "criteria": {"C1": "Preserve required behavior."}
  },
  "ko": {
    "language_name": "한국어",
    "overview": "작업의 목표와 이유.",
    "sections": [{"title": "범위", "paragraphs": ["구체적인 범위."], "items": ["제약."]}],
    "criteria": {"C1": "요구된 동작을 유지한다."}
  }
}
```

Both criteria maps contain exactly the IDs from `--criteria-file`. Preserve numbers, constraints, exceptions and source URLs; review translation meaning yourself. The renderer checks IDs and literal numbers/URLs, escapes input and produces HTML headings, paragraphs, lists and tables. For other languages supply translated `headings` keys `overview`, `criteria`, `expected`. Do not force sixteen criteria or mark normal new cards Done.

Existing text, manual edits, overrides and interrupted creation payloads remain intact. This is not a bulk rewrite. `card read CARD --language en [--section TITLE]` selects generated sections; legacy descriptions remain explicitly legacy.

## Type labels

Types are `plan`, `task`, `summary`, `instruction`; other labels remain. Plans, summaries and instructions live on the parent board; new tasks use assigned work boards. Conflicting type labels block projection rather than deleting a user label. Label creation/attachment use durable intents and readback. Resolve uncertain writes through the reported `setup-resolve` operation only after confirming non-application.

`card types` applies type labels to existing cards already linked to local Plan, Work or Summary records. It does not infer a type from titles, rewrite bodies, move cards or change workflow states. Moved cards and conflicting type labels need inspection. The `labels-sync` access group covers only this operation.

## Instruction cards

Read active parent-board Instructions at planning, assignment and review. Manually authored cards bearing `instruction` are discovered without local registration or internal JSON. They remain active without managed lifecycle metadata; card Done does not retire guidance. `instruction read CARD --language en [--section TITLE]` selects one language for managed cards and preserves manual text.

On a user request, `instruction publish --file FILE --reason USER_REQUEST --operation-id STABLE_ID` creates/updates guidance. Input: `title`, `language`, `scope` text, `status` (`active`, `superseded`, `retired`), plus `en` and user-language objects containing `purpose`, `rules`, `exceptions`, `verification` strings. Other languages also need translated `headings` and `detail_titles` for `rules`, `exceptions`, `verification`. Updates require `--card ID --expected-hash HASH` from a fresh read. Prior content is archived in a card comment. Reuse the operation ID after interruption.

All active references are passed by default, avoiding accidental loss of mandatory rules through keyword matching. References include scope, ID, hash, version and sections. Select task-relevant details in assignment prose. Failed lookup is a blocker, not an empty rule set. On change, read the revision and `instruction use ENTITY --phase planning|assignment|review --reason IMPACT_AND_SCOPED_EXCEPTIONS`. Use `instruction deliver WORK --reason ...` for an active worker and retain the delivery receipt. Resolve a currently blocked worker before sending new instructions.

The first use of each content revision stores its original title and body in a comment on that Instruction card, including manually authored cards. Repeated use reuses this snapshot. Comment permission is required; a failed snapshot remains a blocker with a durable retry identity. Comments and server timestamps alone do not trigger a guidance-change warning.

Record versions, compliance, scoped user exceptions and unknowns in reports/review notes. A current explicit user request can change guidance for its stated scope; record it and clarify genuine conflicts only. Instruction cards never grant filesystem/network permission, select models or authorize cleanup. Do not promote Summary history without user intent. Original text/history stay on Vikunja; local references and write intents support retrieval/recovery.
