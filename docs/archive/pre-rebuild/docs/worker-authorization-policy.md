# Worker authorization policy

This document defines the provider-neutral authorization contract for every CLI that Handrail may use as an implementation worker. Provider flags are adapters to this policy; they do not define the policy itself.

## Goals

- Let an approved implementation run finish without routine per-command prompts.
- Reuse explicit saved permission grants only through an explicit delegation of selected parent plan cycles.
- Keep each run pinned to one repository, isolated worktree, task/specification, provider, and permission provenance.
- Fail closed when a provider cannot enforce the selected boundary. Never silently broaden access to make a run proceed.
- Keep Vikunja manager credentials and Handrail configuration out of worker environments.

## Task approval and reusable permission authority

1. **Task approval** confirms the user wants the approved specification and check plan implemented. It is content-hash-bound and becomes stale if either document or the repository binding changes.
2. **Permission grant** records user-approved provider capabilities in private Handrail data: allowed models, extra read/write paths, network mode, workflow roles, and dependency preparation mode. It is separate from task approval and never stored in a repository-controlled file.
3. **Plan delegation** selects one or more approved parent plan cycles and permission grants, with expiry and a run budget. It is separate from both task approval and permission grant. A later reopened plan cycle or an unselected plan is not covered.

Neither a task card, comment, attachment, nor model-generated plan may grant or expand permissions or delegation. In-scope child specs can be registered with `spec approve --delegated`; this attributes the approval to the parent plan delegation without pretending the user separately approved model-authored child text. A run covered by current saved grants and a delegation proceeds without repeating the same consent prompt. An uncovered run still needs the explicit one-run authorization path. Any newly required capability pauses for an updated grant/delegation or explicit one-run authorization.

## Capability levels

| Level | Filesystem | Commands | Network | Routine prompts |
| --- | --- | --- | --- | --- |
| `confirm` | Provider defaults | Provider defaults | Provider defaults | Provider may ask |
| `workspace-auto` | Handrail requests source reads/writes in its isolated worktree. Provider CLI session state is a separate host requirement; it is not automatically added to worker writable roots. Effective roots may be broader under user/team CLI settings, which Handrail does not enumerate. | Non-interactive implementation and approved checks; provider policy remains active | Provider default/blocked unless a separately approved network capability exists; configured tools may add destinations | Suppressed according to provider mode; effective provider integrations may be broader than Handrail's requested source scope |
Saved grants add individually named paths, selected network mode, model IDs, workflow roles, and preparation mode. Command classes remain subject to the provider and outer host policies; Handrail does not manufacture general shell allowlists.

`workspace-auto` must never disable the provider sandbox or grant arbitrary host filesystem/network access. Cursor's `--force` is explicitly broad Run Everything tool mode, not a narrow shell rule. It must not use Codex `danger-full-access`, Codex approval-and-sandbox bypass, Cursor `--sandbox disabled`, or equivalent sandbox-bypass flags. The outer host sandbox cannot be lifted by either adapter.

## Preflight and consent record

Before a worker launch, the orchestrator must:

1. Read the approved spec and check plan; validate command working directories are inside the repository.
2. Resolve the selected provider/model and current grant/delegation; validate repository identity, parent plan spec/check hashes, delegation cycle, expiry, revocation, workflow, and run budget.
3. Run adapter preflight for supported paths/network behavior and report unsupported requests without widening them. `preflight` separately previews likely host roots and destinations; it never edits host settings.
4. If delegated coverage is valid, reserve the run and persist exact provenance. Otherwise, show the one-run preview and wait for the user's explicit response.
5. Apply supported provider settings immediately before worker launch, record the application result, and clean only Handrail-generated settings after execution. Saved grants, delegation, run reservation, applied settings, and approval evidence remain distinct records.

The record must not contain credentials. It should include policy version, grant timestamp, task and binding identity, spec/check hashes, provider/profile/model, capability list, normalized paths/destinations, expiry or one-run scope, and a hash of the normalized grant.

## Enforcement and escalation

- Provider adapters receive only the flags/config needed to enforce the recorded grant.
- The worktree remains separate from the user's checkout; Handrail retains its existing result, verification, review, and integration gates.
- Provider-owned session state is identified in the host preview, but its exact path is CLI-version-dependent. Do not grant the worker a broad provider home or assume Handrail's host preview enforces it.
- Network is off or follows provider defaults unless an explicit network grant is selected. Dependency installation or remote API access is not inferred from a test command. An install preparation policy must include `execution_boundary: "orchestrator-host"`; install argv runs under Handrail's outer host policy, not the worker provider sandbox.
- If a provider lacks an enforceable capability boundary, Handrail reports `unsupported` or `requires_setup`; it must not silently fall back to unrestricted mode. Codex `--add-dir` is writable and cannot implement extra read-only paths. Cursor network disable is unsupported where merged user rules can retain network allows.
- Dependency copy/install and command checks run under the Handrail manager process and outer host policy, not inside the provider worker sandbox. Copying `node_modules` requires baseline manifest identity but does not prove lockfile/install consistency. Installation requires a separately granted `prepare` workflow and explicit argv.
- If execution hits a denied path, command, or destination, stop and report the attempted capability. The orchestrator may request a new grant with a concrete reason; it must not auto-approve escalation.

## Provider adapter contract

Each provider adapter must declare:

- how to enforce read/write roots and additional paths;
- how to restrict command execution and network access;
- how to suppress routine approval prompts within an already approved boundary;
- where provider session state is stored and whether it is required;
- which flags disable sandboxing or otherwise broaden access;
- version detection and a startup self-check that rejects unsupported or unknown enforcement modes.

For the current experimental adapters:

- **Codex** can use `workspace-write` with `--ask-for-approval never` for `workspace-auto`; this is not a sandbox bypass. Extra writable roots must be explicit. Never add `--dangerously-bypass-approvals-and-sandbox` for this level.
- **Cursor** print mode requires `--force` for file writes. The installed CLI documents `--force` as Run Everything tool mode. Thus Cursor `workspace-auto` suppresses approval for all agent tool calls that Cursor auto-runs; this is broader than workspace-only shell permission. It must be shown as such in the preview, including any configured MCP/Fetch capabilities. Retain `--sandbox enabled` to keep terminal filesystem/network restrictions; do not use `--sandbox disabled`. CLI flags/config must be validated against the installed version. This mode requires explicit user approval, either through a matching saved plan delegation or one-run preview.
- Cursor uses project-scoped generated `.cursor/sandbox.json` for selected additional read/write paths and network policy, while keeping `--sandbox enabled`. The adapter never edits `~/.cursor`, overwrites a project setting file, or disables the sandbox. It removes its generated file only if the contents still match; modified settings are retained for inspection. Cursor `--force` may run broad configured agent tools and must be disclosed.
- New CLIs must implement the same capability semantics before they can be selected for unattended runs. Unknown or unsupported settings are not treated as ready.

## Separate workflow approvals remain

Saved grants can authorize running the delegated `verify`, `review`, `integrate`, `kanban`, or `prepare` workflow operations. They do not prove that checks passed, accept a run, skip state/evidence gates, authorize remote Git push, submit a parent plan for Review, or mark a plan Done. Those remain distinct Handrail workflow decisions, and the user makes the final parent-plan Done decision.

## Current Handrail run flow

For a delegated plan, `run start TASK_ID --instructions '...' --preview` shows saved coverage and adapter readiness without consuming a run or moving the Kanban card. A covered start reserves the delegation budget and creates a run without asking for the same consent again. An uncovered start returns the one-run preview, request ID, and confirmation code without creating a worktree or changing Kanban state. After actual user consent, repeat with `--authorization-request-id <id> --authorize "authorize <code>" --authorization-approval '<user text>'`. The code binds the request; it does not authenticate its caller. Handrail rereads the task, spec/check plan, profile, baseline, CLI version, binding, and applicable permission provenance before accepting it. The initial todo-to-doing move remains explicit in the preview. Provider and host setup are separate: `preflight --provider ...` only describes likely outer roots/destinations and cannot change or bypass the active host sandbox.

Each run stores its private permission provenance, delegation/run reservation, and execution authorization snapshot. The supervisor revalidates these pins before worker launch. The task's initial move from todo to doing is explicitly shown in the preview. Additive grant updates never broaden old runs; an older run may remain valid under its narrower pinned permissions. Narrowing/revoking a grant or changing/revoking its delegation may invalidate the old provenance. A grant may authorize delegated workflow operations, but does not prove successful checks, accept a run, bypass state/evidence gates, or mark the parent plan Done. Remote push remains outside these grants, and the user makes the final parent-plan Done decision.

`run retry` first snapshots a stopped worktree diff, including binary files, and requires the repository baseline to match. It then creates a fresh run under current delegated permission scope; it does not mutate the old run's pinned provenance and does not accept the one-run fallback. If coverage is absent, update the grant and explicitly delegate the plan cycle. An additive grant update does not invalidate or widen old provenance, while narrowing/revocation may invalidate it. Inspect the retry preview before launch. The candidate snapshot is applied before dependency preparation; packet regeneration archives previous packet/results in private run data. The new result template starts `blocked` with checks `not_run`; it is not evidence of a completed worker.

## Current limits

- Host setup preview does not enumerate every active OS, container, team, or provider setting; effective enforcement remains subject to those layers.
- Cursor's `network: disabled` is unsupported when merged user allow rules could continue to permit destinations. Existing project `.cursor/sandbox.json` is not overwritten.
- Cursor's provider session directory is version-managed and may be shared among workspaces. Do not grant all of `~/.cursor` to a worker.
- Installation and test commands use Handrail's manager execution environment and the outer host policy; they are not automatically sandboxed by the selected provider adapter.
