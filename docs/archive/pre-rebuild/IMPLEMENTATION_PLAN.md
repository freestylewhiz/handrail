# Handrail v0 implementation and release

## Baseline and authorization

- Source baseline: `673c29a022e01dec1d4102f665aa0d0afdd1fd12`, branch `main`.
- Existing changes: doctor improvements in `handrail/cli.py`, `.gitignore`, design documents, and unfinished Docker fixtures. Preserve useful behavior while replacing obsolete product interfaces.
- User authorized implementation, repeated tests, project cleanup, a clean local development Vikunja, GitHub push and release. Detail implementation uses GPT-6 Luna high; the main agent owns architecture, review and release. Cursor invocations use `cursor-grok-4.6-high`.
- Current target: private GitHub prerelease `v0.3.0-rc.3`; its plugin distribution tag is `plugin-v0.3.0-rc.3`. The prior `v0.3.0-rc.1` and `plugin-v0.3.0-rc.1` references are historical and immutable; never move or overwrite those tags. Cursor orchestration is the authorized follow-on below; MCP and child-board creation remain backlog items.

### Authorized follow-on

After completing the Codex-first release, branch `feat/cursor-orchestrator` from its source revision and implement HR-NEXT-001 with Cursor CLI `cursor-grok-4.6-high`. The main agent reviews the architecture and independently verifies real Cursor orchestration, both worker providers and shared locks. Push the separate branch without changing the v0 release tag or automatically merging it into main. MCP and child-board creation remain unstarted backlog items.

## Architecture and user requirements

| Requirement | Implementation boundary |
| --- | --- |
| U1 External Vikunja | Product only connects; development fixture independently runs Docker |
| U2 Interactive credentials | TTY hidden input, user configuration, private atomic token storage |
| U3 Codex plugin | Portable manifest plus Codex compatibility manifest, bundled Python runtime |
| U4 Remote Git excluded | No product remote setup, hosting, push or PR management |
| U5 One root per workspace | Shared binding with local profile mapping; no host-wide default board |
| U6 Worker model selection | Run/project/profile/provider-default precedence, no silent substitution |
| U7 Host extensibility | Common core; Codex orchestrator and Codex/Cursor workers in this release |

Retain stdlib Python >=3.9, reusable Git fingerprint/commit-tree mechanics and spec approval hashes. Replace v1 network contracts using the target v2 OpenAPI. Isolate configuration, onboarding, bindings, provider adapters, run state/supervision, sync recovery and migration services. Plugin cache is immutable; mutable state lives in user paths or workspace runtime directories.

## Stages and acceptance

1. Plugin build/launcher and configuration: isolated bundled execution; no global pip installation; readonly onboarding; two repositories with separate root boards and shared connection profile.
2. v2 cards/context and run workflow: scoped task access, pinned approval/check IDs/binding/build, allowlisted worker environment, structured results, common-Git-directory durable single-writer lock, supervisor cancellation/recovery.
3. Review/integration/sync: current fingerprint and all required checks plus semantic review; clean unchanged integration baseline; preserve local results on remote failure and reconcile uncertain writes before retrying.
4. Migration: preview, private backup/journal, conflict-aware apply/rollback, preserve legacy identity/spec hashes and external services. Active legacy runs block migration.
5. Acceptance and release: targeted regression loops, full suite, live Vikunja contracts, real Codex/Cursor worker flows, actual Codex plugin discovery, reproducible archive, secret/content audit, remote installation and release download verification.

## Development environment

- Existing unrelated services and Handrail registries are retained.
- Dedicated container: `handrail-v0-vikunja`, loopback `http://127.0.0.1:58820`.
- Official Vikunja `2.6.0` image index: `sha256:417ada6f94e81f0267aa2f007d0a811fc82d38dd2aa58351e3ea520ca01c2ea5`.
- Private fixture data: `~/.local/share/handrail-development/v0`; credentials never committed or printed.
- Actual `/api/v2/openapi.json` SHA256: `47414f4a2bfb7e22469fc5b9d462b0182f96abf58f7fe37054dbb77fb00ee1dd`.
- Baseline suite: 52 cases, 51 passed, 1 old managed-container opt-in skipped. This is baseline evidence, not v0 acceptance.

## Release transaction

Commit reviewed source to `main` and tag `v0.3.0-rc.3`; build that exact revision. Publish the generated marketplace and ready-to-run plugin to `plugin-dist`, tagged `plugin-v0.3.0-rc.3`. Verify installation from the remote distribution tag before publishing the GitHub prerelease with ZIP, SHA256SUMS, build information and test/migration notes. Do not force-push or overwrite release tags. Re-download and verify published artifacts.

No required gate is considered passed from mock evidence alone when it explicitly calls for live execution. Record actual unsupported behavior and resolve it before release.
