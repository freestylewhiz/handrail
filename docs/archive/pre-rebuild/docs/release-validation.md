# Handrail release validation records

The source records development and acceptance checks below. The release asset `handrail-release-evidence.json` records final source/distribution revisions, the final test count, remote plugin installation and published artifact download checks. Publication is complete only after those external checks succeed.

## 0.3.0-rc.4 hierarchical workflow and orchestrator help

This candidate includes parent/child board registration, actual plan/work task relations, verified work completion, aggregate plan Review, user acceptance, new work for review feedback, and explicit reconciliation of human state changes. It also includes provider execution authorization previews, offline Korean help, and the Handrail philosophy and terminology documentation.

The acceptance suite uses a separate disposable Vikunja 2.6.0 instance with a deterministic worker CLI. The real HTTP API, supervisor process, isolated Git worktrees and integration execute end to end. It covers two child boards, work Done/plan Review, review corrections, no-change work, human state reconciliation, stale evidence rejection, lost write acknowledgements, duplicate prevention, and replaying completed work after plan Review. See [workflow-validation.md](workflow-validation.md) for the scenario details.

This RC does not claim a new paid Codex/Cursor model acceptance run. Provider argument and authorization contracts are covered by regression tests; the historical paid worker acceptance below belongs to its recorded candidate. The RC4 evidence asset records the final clean source commit, tests, artifact checksum, distribution commit, installed plugin version, and published download verification.

RC4 source verification on 2026-10-01: 108 tests passed with no skips, including the live Vikunja scenario. Plugin manifest validation, skill validation, and whitespace checks passed before the release commit.

Installation acceptance found that sparse checkout of only `plugins/handrail` omits the marketplace manifest. RC4 instructions therefore fetch the complete distribution and explicitly replace an existing pinned marketplace source when upgrading.

Earlier released tags and their release assets are preserved. Update to `plugin-v0.3.0-rc.4` and start a new Codex session to discover the updated skill. Existing connection profiles remain available; a new repository still needs its own parent-project binding.

## Historical RC1 validation

## Environment

- Rocky Linux 9.7, Python 3.9, Git, Codex CLI 0.157.1 and Cursor CLI 2026.09.28-64d2043.
- Separate official Vikunja 2.6.0 development container on loopback port 58820; restart preserved its SQLite data and the two acceptance parent boards. Unrelated services and legacy registries were preserved.
- Image digest and actual v2 OpenAPI SHA-256 are recorded in `IMPLEMENTATION_PLAN.md` and `vikunja-v2-contract.md`.

## Independently checked behavior

| Area | Evidence |
| --- | --- |
| Configuration | Real PTY setup and rotation: hidden token input, no echo, private 0600 credential files; readonly missing-credential lookup |
| Workspace identity | Two repositories use separate parent boards with one profile; onboarding left projects/views/buckets unchanged; linked worktrees share the canonical repository lock |
| Fresh-host attach | New profile explicitly associated with a cloned shared binding through a real PTY; exact binding bytes and workspace ID preserved; runtime resolution succeeded |
| API and cards | Live v2 pagination, scoped task reads, comments and bucket moves; repeated card creation with one operation ID returned one Todo card; uncertain writes are reconciled without blind resend |
| Diagnostics | Live valid profile exits 0; invalid token and offline API exit 1; missing setup exits 2; malformed config shapes produce safe errors |
| Context | Selected 49-byte attachment downloaded from live v2 with matching bytes/SHA-256 and numeric-ID filename; unit cases cover size limits, foreign IDs, symlinks, destination replacement and quoted typed evidence |
| Runs | Same-second stale writers rejected by integer revision; live processes block ownership release; a real fake-worker process was cancelled and a separate worker/supervisor pair was forcibly terminated for crash recovery |
| Recovery | Dead PIDs did not release the durable lock; a new run was refused until explicit recover/abandon; worktrees and evidence were preserved |
| Approval and checks | Changed spec/check plan is rejected; a failed or timed-out recheck invalidates an earlier pass at the same fingerprint; changed accepted artifacts block integration |
| Migration | Readonly preview, explicit profile association, private backup/journal, resumable apply, original spec/run archives, new schema approval compatibility and conflict-aware rollback; external services and Git remotes untouched |
| Packaging | Strict exact tree/ZIP inventory and byte checks; archive-only tampering with a recomputed checksum rejected; duplicate/traversal/symlink entries rejected |
| Launcher | Isolated Python ignores injected cwd/PYTHONPATH packages; paths containing spaces and a readonly plugin directory work; file hashes unchanged and no plugin bytecode created |

The stdlib regression suite is run with `python3 -m unittest discover -s tests -v`. Obsolete managed-service, remote-Git and global-selection test expectations were replaced by v0 behavior tests. The original baseline had 52 cases (one opt-in skip); final counts are recorded in the release evidence asset.

## Actual worker acceptance

Both paid worker routes completed on immutable candidate ZIP SHA-256 `19ff19e39b3036a09e27fd1803218dd4af028e84a4d339aa3f4ae03b6b04b4b3`:

| Orchestrator | Requested worker | Result |
| --- | --- | --- |
| Codex | `gpt-6-luna`, reasoning `high` | Structured return, independent checks, semantic review, local integration, post-integration checks and Review synchronization passed |
| Codex | Cursor `cursor-grok-4.6-high` | Structured return, independent checks, semantic review, local integration, post-integration checks and Review synchronization passed |

Each worker changed only the approved source file. The main reviewer read the full diff and report and reran all approved command/manual checks. The CLI did not separately report an actual model ID, so that field remains null. Neither task was automatically marked Done. Final source additionally includes setup, model precedence, task creation and cleanup corrections covered by subsequent regression and live checks.

## Plugin installation and release checks

A new actual Codex session installed and discovered the early built plugin, read its skill and invoked the bundled isolated launcher. Final distribution-tag installation, a new Codex discovery session, exact final artifact checksums and GitHub asset re-download verification are recorded in the release evidence asset because they require published refs or assets.

Cursor orchestration is a separate follow-on branch, `feat/cursor-orchestrator`; it is not included in this release tag.

## Observed external limitation

Vikunja 2.6.0 returned task ETags but accepted an intentionally stale `If-Match` update. Read/check/write/readback detects many conflicts but is not atomic compare-and-set. The v2 contract document records this observed server behavior.

## 0.3.0-rc.2 report-contract correction

The immutable `v0.3.0-rc.1` and `plugin-v0.3.0-rc.1` tags and their recorded artifact/evidence references remain historical and unchanged. The next candidate uses `0.3.0-rc.2` (PEP 440 `0.3.0rc2`).

Two real worker runs surfaced ambiguity in the `result.json.changed_files` instructions: workers listed generated `.handrail/runtime/` report and packet files along with their source edits. The RC2 prompt and worker template now define that field as the exact repository-relative source paths changed from baseline, excluding ignored files and all generated or report artifacts. The strict source/result validator is unchanged; it continues to reject invalid worker output. Focused packet-contract regressions cover both prompt and template wording.

RC2 full suite: 76 tests passed. The pre-commit development candidate archive was built at `/tmp/handrail-rc2/handrail-0.3.0-rc.2.zip`, SHA-256 `e48602e25e62ff3fcb895977c0b932f4ae8399c0dc7523206be853a0b02af8ae`; `scripts/validate_distribution.py` accepted the complete tree and ZIP.

Final clean-commit build metadata, remote installation and published download checks are recorded in the RC2 release evidence asset.


## 0.3.0-rc.3 scheme-free service URL input

RC3 allows entering a bare Vikunja host (optionally with a port) without a URL scheme. The setup defaults to HTTPS. For a LAN-only HTTP endpoint, the user must explicitly pass `--allow-insecure-http`; in that case a scheme-free host is interpreted as HTTP. Explicit `http://` and `https://` URLs keep their stated scheme and the existing HTTP safety check remains in force.

The focused setup suite passed 11 tests and the full regression suite passed 77 tests before the version-only release metadata bump. Final clean-build verification and published artifact checks are recorded in the RC3 release evidence asset.
