# Execution and scoped approvals

Use the absolute `stable_launcher` returned by `handrail locate`; place `--repo ABSOLUTE_REPO` before the operation. Keep that argv order across sessions. The managed release is independent of Codex's cache. The installer connects Cursor through `~/.cursor/skills/handrail` and preserves unrelated configuration.

## Coordinator

Record observed identity with `coordinator register --provider codex|cursor --model EXACT_ID --evidence OBSERVATION [--effort LEVEL] [--surface CLI|IDE] [--session ACTUAL_ID]`. Use host session context or the provider model picker. A marketing name is not a CLI identifier. For Cursor, select the advertised identifier including its reasoning variant; do not pass a separate effort. Capability/catalog checks precede room and worktree creation. An unavailable catalog is an explicit blocker; never silently change the model.

On an actual host denial, explain the denied resource and obtain only necessary authority through the host approval tool. Propose a stable exact prefix where supported. `access plan --provider PROVIDER --group read --group board-sync` produces reviewable rules. Other groups are `summary-sync`, `labels-sync`, `monitor`, `cleanup`, `onboarding`. Select only needed groups. `access apply ... --approval EXISTING_HOST_POLICY_CONSENT` writes them when that scope is authorized. Plan approval, board selection and Instruction text do not authorize host policy changes. Reuse actual prior consent; host sandbox rules still govern writing policy files. `access revoke` removes only additions tracked as Handrail-owned and preserves prior rules.

Codex uses argv prefixes; Cursor CLI uses `Shell(command:args)` patterns while preserving existing allow/deny entries. Rules do not cover arbitrary Python, shell, raw Herdr, all Handrail, `command`, `permissions` or `access apply`. Managed policies and deny rules can override them. CLI rules do not configure IDE policy. `access record --kind host-approval|user-choice|wait --evidence OBSERVATION [--category intent|board|model|host-execution|acceptance|cleanup] [--duration-ms INTEGER]` and `access metrics` count recorded observations, not complete host telemetry.

## Worker readiness

`worker start` records requested arguments and exact writable roots: owned worktree, actual worktree Git directory, shared Git directory and dedicated report channel. Codex requests legacy workspace-write; Cursor requests sandbox enabled; both add these directories. This does not grant arbitrary host access. Codex permission profiles do not compose with legacy settings. Managed requirements can reject or supersede the request. Inspect policy observations and worker failures rather than disabling policy.

Only the worker runs `worker probe --contract CONTRACT` from its normal sandbox. It creates/removes temporary files in those roots and does not change commits. A passing directory probe does not prove hooks, signing or every Git operation. On denial, preserve work and report the exact path/boundary. Do not repeat the denial, escalate the probe, disable sandboxing or fabricate `HERDR_ENV=1`. The report is a worker observation, not authenticated host telemetry.

`worker continue ATTEMPT` sends deferred implementation only after readiness, reusing the original start grant. Replacement attempts require fresh readiness. Shared Git storage has repository-wide effects, not per-branch isolation. The report channel is outside the source tree; never add manager state, credentials, another worktree or Herdr control as writable roots.

## Monitoring and identity

Run `coordinator tick PLAN --owner ACTUAL_SESSION` during the active turn, then schedule the next call at its returned interval. Each call is one bounded pass; it does not leave a daemon. Failures increase suggested delay up to 300 seconds. Report worker/Work, observation time and blocker. On reconnect, tick and inspect `coordinator inbox`; durable files recover missed terminal notifications.

Kernel boot identity, process birth time, executable/argv fingerprint, terminal and provider identity support late session enrichment. Same pane, path or PID alone is insufficient. Unavailable evidence remains `IDENTITY_UNPROVEN`. Real replacement uses `worker recover` during active work; Done cleanup uses the separate flow in [recovery.md](recovery.md).
