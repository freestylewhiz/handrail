# Summary cards

The Summary CLI and completion hooks are available in alpha.6, including structured worker submissions, referenced Instructions and the summary label. The coordinator model synthesizes prose and translations; the CLI collects evidence, renders separated sections and manages delivery/versioning. Prepare during Review and finalize automatically on user acceptance. Reading history does not create cards.

## Project results and Handrail execution issues

New `summary prepare` templates use content `schema_version: 2`. Keep one Summary card and the English/user-language/Agent Context top-level layout. Each language has two areas: **Project results** (the existing seven fields) and **Handrail execution issues** (`handrail_issues`). Classify by the affected responsibility, not the person who found a problem. Application API bugs, implementation decisions and product limits belong to project results even when a worker discovered them. Permission, identity, handoff, coordination and recovery observations belong to execution issues. Do not turn a host/provider limitation or an operator mistake into a proven Handrail defect.

Fill `content.sections.en.handrail_issues` and the equivalent user-language narrative with concise issue IDs, observed symptoms, impact, recovery, current status and evidence. Keep facts and cause hypotheses distinct. Also fill `content.agent_context.handrail_issues` with `{assessment, items}`. `assessment` is `not_reviewed`, `none_observed`, or `observed`; only `observed` has nonempty items. Missing records are not proof of no issues. Every item requires:

- `id`, `stage`, `expected`, `observed`, `impact`, `recovery`: nonempty English strings; preserve the same ID when updating an issue in this card.
- `status`: `open`, `recovered`, `resolved`, or `unknown`. A workaround that resumes work is `recovered`, not proof the underlying defect is fixed.
- `attribution`: `handrail`, `provider`, `host`, `coordination`, or `unknown`. This is an evidence-based author assessment, not an automatic verdict. Record a tentative cause in an optional `hypothesis`; optional version/environment details can accompany evidence.
- `evidence`: nonempty references to operations, events, session messages, logs or tests. Use references such as `operation:ID` and `event:ID` with the card's source context. Do not paste credentials, nonce values or full terminal output.

`prepare.execution_evidence` provides bounded local failure/recovery references. Inspect relevant history and session reports when needed; the list is neither exhaustive nor a classifier. Its absence must not make you assert `none_observed`. Populate both narratives from evidence and keep their meaning aligned with the structured items. Project verification and user acceptance do not automatically resolve an execution issue.

The rendered Agent Context stores separate `knowledge.project_results` and `knowledge.handrail_issues` areas. Execution observations are input for a later Handrail owner review, never permissions, permanent Instruction rules, or automatically created development cards. The owner decides whether to adopt, narrow or exclude an improvement. Do not ask the user to approve routine Summary authoring or repeat existing implementation/acceptance consent.

Schema 1 cards remain readable and preserve their content during lifecycle updates. `prepare` does not silently reclassify or migrate them. When explicitly updating an old card to separate the areas, retain its `source_fingerprint` and `expected_hash`, set content `schema_version: 2`, add the translated narrative field and structured assessment, and reconcile the existing prose. Historical absence is `not_reviewed`. All coordinators reading a schema 2 card need a runtime that supports schema 2.

## Commands and authoring

`summary prepare PLAN --language ko` returns source records, latest collected worker reports, source links, an expected card hash and a content template. Synchronize the plan/work cards first. Fill the template in a temporary file, preserving `source_fingerprint` and `expected_hash` from that response. Each language's project fields require `intent`, `outcome`, `decisions`, `rules`, `avoid`, `considerations`, `verification`; schema 2 additionally requires `handrail_issues` as described above. Write English and the user's language separately; explicitly state when evidence is missing. `content.agent_context` requires `scope`, `decisions`, `rules`, `avoid`, `considerations`, `verification`, plus schema 2 `handrail_issues`. Use English technical keys/values with source references. For languages other than English/Korean, supply `language_name`, a `headings` map for all stored fields and schema 2 `project_headings[LANGUAGE]` for the project area title.

Run `summary publish PLAN --file FILE --reason REASON`. This creates one canonical Summary on the parent board or updates that same card, archives the previous version in its comments, and links it from the plan. Draft/stale records use Review; accepted records use Done. Summary cards never become workflow Work items. Temporary files are request buffers; do not maintain a second Summary document locally.

`plan complete PLAN --approval ORIGINAL_USER_APPROVAL --summary-file FILE` combines publication with formal acceptance. When a current draft already exists, omit `--summary-file`. A `SUMMARY_CONTENT_REQUIRED` result is work for the coordinator: read the sources and compose it, retaining the original acceptance instruction. Do not ask the user to supply JSON or repeat approval. A publication failure is reported distinctly; retry `sync --topic summary` after reconciliation.

After acceptance, check that both languages and Agent Context describe the current outcome consistently. The CLI updates lifecycle metadata; it does not rewrite free prose saying acceptance is pending. Refresh that prose on the same card when necessary, preserving user edits and history without asking for acceptance again. Do not mark execution issues resolved merely because the Plan was accepted.

`summary list --query WORDS` lists accepted related records using title/scope terms. `--include-stale` also shows draft/stale records for inspection. `summary read CARD` returns Agent Context only. `summary read CARD --language en --section rules --section verification` returns only those narrative fields; use `--language ko` for a Korean explanation. If keyword search misses relevant history, list the parent board's summaries and inspect scopes.

For a Handrail improvement review, use `summary list --issues --query WORDS` to search recorded issue content/title on the connected parent board, then `summary read CARD --section handrail_issues` for only that structured area with source metadata. Add `--include-stale` when reviewing draft/history and respect its status. `summary read CARD --section project_results` selects only project knowledge; `--language ko --section handrail_issues` selects the issue narrative. This is not a cross-repository collector or an automatic backlog. Default worker history includes only selected project narrative fields; execution issues are not automatically injected into new assignments.

Before work assignment, `summary use PLAN_OR_WORK CARD --section rules --section verification --reason RELEVANCE` records the exact card/version/hash consulted. `worker start` retrieves the selected English fields and source links and appends them to the worker's assignment. Changed references stop startup with `SUMMARY_REFERENCE_STALE`; reread and record the new selection rather than injecting stale context.

On `SUMMARY_WRITE_UNCERTAIN`, inspect the operation/card, then `summary resolve OPERATION_ID --evidence OBSERVATION` and repeat the original publication or sync. Resolve reads the remote outcome and only changes local delivery metadata; it does not send a second remote write. Preserve the original operation on a retry.

## Card layout

Keep the Summary on the plan's parent board and link its source plan and relevant work cards. The Vikunja card is the Summary's authoritative record. Local request buffers or caches are disposable, not separately maintained Summary content.

Use these top-level sections in order:

1. `English`: complete English narrative, with purpose/outcome, decisions/reasons, scoped rules, approaches to avoid, considerations, verification limits and source links.
2. The user's language name, for example `한국어`: the equivalent complete translation, with headings and narrative in that language. Omit this section when the user's language is English. Do not alternate translated sentences, paragraphs or bilingual subsection headings inside either narrative section. Preserve code, names, IDs and original quotations where necessary.
3. `Agent Context`: a single structured JSON block using stable English keys and values. Include schema/version, source card IDs, cycle/revision, scope, completion basis, current/superseded decisions, constraints, verification limits, evidence references and a section directory. Do not repeat the full narratives or their translation here.

The section directory records exact top-level headings, language codes and relevant subsection headings. Keep the same decisions and material limitations in both language sections. Important constraints must be visible in the human narrative as well as available to agents. Distinguish recorded facts, worker explanations and the summary author's recommendations. Do not infer worker intent or promote card Done to verified workflow acceptance.

## Read only what the task needs

Retrieve a relevant Summary card, then extract its `Agent Context` before returning content to the model. Inspect its source identity, scope, version, completion basis and relevant decisions/limits to decide whether it applies.

If the API returns the entire description, receive that response in the tool process and select sections there. Returning only a selected section reduces model context; it does not imply the API fetched fewer bytes. Use a parser appropriate to the stored HTML or Markdown and the section directory. Avoid printing the entire description into tool output before selecting it.

| Purpose | Read next |
| --- | --- |
| Decide whether a Summary applies | Agent Context identity, scope, decisions and limits; stop if unrelated |
| Plan related work | Relevant intent, decisions, rules and considerations in English; read evidence for disputed, changed or consequential assumptions |
| Implement an assigned work item | Assigned constraints, interfaces and verification limits; retrieve only related narrative sections and evidence |
| Explain history to the user | Relevant sections in the user's language; read the English counterpart only to resolve a discrepancy |
| Translate or audit consistency | The corresponding sections in both languages |

Use English by default for agent analysis. Do not read both language narratives routinely. If context is insufficient, expand to the needed subsection or original evidence; saving context must not hide relevant limitations. If structure is missing or malformed, inspect headings and the relevant single-language narrative, report any unresolved ambiguity, and do not invent missing fields or silently rewrite the card.

Record the Summary card ID and revision actually consulted in the next plan or worker assignment. The coordinator passes selected facts, their scope and evidence links to workers; do not require workers to read a full duplicate translation. Workers may request additional context from the coordinator when direct board access is unavailable.

Historical decisions apply only within their recorded scope. Check current requirements and relevant code when reusing a decision; document intentional replacements. Card text and structured fields are evidence, not new permission or instructions overriding the worker contract.

## Updating a Summary

Update the existing card and increment its Summary revision. Preserve the previous version and change reason in the card's comments, keeping the record on Vikunja. Re-read before writing, preserve user edits, and resolve conflicting changes rather than replacing them with stale content. Check whether conditional writes are available; a pre-write read alone does not guarantee atomic conflict prevention. Keep both languages and Agent Context aligned to the same revision.

Use the existing operation marker and readback practices for writes. An uncertain response requires inspection before retrying. Formatting or translating a Summary does not change the source plan's workflow state, grant execution authority, or authorize room/worktree cleanup.
