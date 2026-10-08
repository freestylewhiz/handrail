# Handrail first-connection test design

**Purpose:** Reuse a small, safe routine to check Handrail installation and first repository binding in a fresh Git project. The routine covers setup guidance, optional repository documents, project/view discovery, state mapping, diagnostics, and recovery. Child-board checks verify creation with Todo/Doing/Done only. Plans live on the parent board; every additional implementation or correction is a new linked work card.

## Test boundary

- Use a disposable Git repository and a clearly named Vikunja test project.
- Enter a validation token only through a hidden terminal prompt. Never record it in this plan, a shell command, a source file, a repository file, or test output.
- Keep connection config and credentials in a private, isolated XDG config/data directory. Verify they are not copied to the repository. Remove that temporary credential store after validation; do not delete the remote test project or revoke a user token without an explicit request.
- Read-only discovery must not create or edit remote resources. A confirmed parent binding may create only a missing Review bucket. It must preview the target and mapping first, verify the result by rereading, and avoid duplicate creation after an uncertain response.
- Do not create plan or work cards, delegate workers, or run implementation work as part of this install check.

## Procedure

1. Resolve the installed plugin root from the installed skill location or plugin metadata; do not assume a fixed cache path. Invoke its bundled `scripts/handrail.py` launcher.
2. Inspect the test repository root, Git status, and optional documents such as `AGENTS.md`, `.agents/AGENTS.md`, and README. A missing optional file is recorded as absent and does not stop other checks.
3. Scaffold an Express project with `express .`, initialize Git, and record generator/runtime versions and the full command exit status.
4. Create a uniquely named Vikunja v2 project using the one-time connection token. Record only its returned project ID/name and API status.
5. In isolated XDG directories, configure the bundled Handrail CLI through its hidden token prompt. Record only profile ID, label, API host if appropriate, and project count; never read or print credential contents.
6. Run `help setup`, `status`, and `doctor` before binding. Capture stdout, stderr, exit code, repository root, and whether each call is read-only. An unbound repository should report the next binding action.
7. Discover one existing parent project and a manual Kanban view. Map Todo, Doing, Review, and Done for the parent workflow. Confirm the project/view/state mapping before creating a missing parent Review bucket, then reread and verify it before saving `.handrail/project.json`.
8. Optionally request a child board. Verify it is created under the bound parent, its manual Kanban has Todo/Doing/Done, no Review bucket is required, and `area list` registers the IDs. Create a linked work card there and confirm its state/history flow does not depend on Review.
9. Confirm `project status`, `status`, and `doctor`. Verify repository path, project/view IDs, required unique state IDs (four on parent, at least three on child), and read-only checks. Check the repository for token strings without printing secrets.
9. Remove only the test's temporary local connection/credential directories after the result is recorded. Keep the requested test project, Express files, and safe `.handrail/project.json` binding unless the user asks for their removal.

## Acceptance matrix

| Case | Expected result |
| --- | --- |
| Plugin has nested or versioned install path | Skill-relative launcher resolves; no fixed path is required. |
| Optional repository guide is absent | Absence is recorded; root/status/setup checks continue. |
| No connection profile | Help names the hidden-input setup command; no token is requested in chat or arguments. |
| Repository is unbound | Status/doctor identify the binding requirement and show the next command. |
| One exact Todo/Doing/Done title each | IDs map automatically; no per-state prompt. |
| One existing Review bucket | It is reused; no remote write is made. |
| Parent Review is missing | The command previews project/view and known mappings, asks before one POST, rereads, and saves only after exactly one Review is confirmed. |
| Child Review is missing | Child setup succeeds with Todo/Doing/Done; no Review creation is attempted. |
| User declines parent Review creation | No remote POST, local binding, or registry entry is written; instructions name the project/view and manual next action. |
| Parent Review bucket POST is denied | No retry or expanded-scope request; direct manual Review instructions are shown. |
| POST result is uncertain | Reread before retry; reuse a discovered Review or stop with inspection instructions. |
| Duplicate/unknown state bucket names | Do not choose silently; request a choice or actionable correction. |
| Setup succeeds | Binding stores only instance/project/view/bucket identifiers; `status` and `doctor` confirm the same test repository. |

## Evidence to record on each run

- Date, operating system/runtime versions, source revision, packaged runtime version, and plugin root resolution method.
- Test repository path and Git status before/after.
- Command, working directory, exit code, stdout/stderr, and expected/actual result for each phase.
- Vikunja test project ID, manual view ID, bucket IDs/titles, and any confirmed remote change.
- Whether the binding and XDG registry were written; whether credentials stayed outside the repository.
- Defect, recovery action, regression case, and unresolved uncertainty. Redact tokens and other credentials before saving logs.

## Extending this routine

Keep setup checks read-only until the user reaches the explicit binding decision. Add a failure case to the matrix before implementing a recovery path. Prefer disposable projects and mocked API responses for permission failures, duplicate responses, network loss, and invalid bucket mappings; reserve live writes for one confirmed test project. Record the server version and exact response status so results can be compared across Vikunja releases. Separate source tests, packaged-plugin validation, and live-instance results in every report.
