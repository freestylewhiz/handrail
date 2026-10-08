# Authorization

Record the user's already-provided authorization; do not ask again for covered scope. A grant binds the plan cycle to exact resource values and explicit actions. `permissions preview` reports uncovered values. Avoid expanding a narrow action into a global shell or tool permission.

Common scope fields are `endpoint`, `repo`, `worktree_root`; worker start/prompt also use `provider`, `model`. Command execution additionally uses exact `argv`, `cwd`, `purpose`. Key input uses the inspected `screen_hash` and key sequence. `room.close` and `worktree.remove` are separate actions from worker conversation.

Scope is JSON passed to `permissions grant PLAN --scope-file FILE --approval SOURCE`. The source is evidence of user intent, not an authentication credential. Grants may expire or be revoked. New plan cycles do not silently inherit execution authority.

Host sandbox, filesystem, Git common-directory writes, socket IPC and network access remain separate. App grants and provider flags cannot lift the outer sandbox. `preflight` lists actual paths but its `os_access_hint` does not prove sandbox authority. On denied access, report actor/resource/action/boundary and use the host's supported permission mechanism for the necessary scope.

Keep private credentials and manager state outside worker source trees. The process account and actual host sandbox enforce isolation; Handrail does not claim same-user filesystem secrecy from a malicious process.
