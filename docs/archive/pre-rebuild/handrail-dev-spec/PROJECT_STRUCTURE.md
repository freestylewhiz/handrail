# PROJECT STRUCTURE

목표 Repository 구조:

```text
agent-dev-workflow/
│
├── plugin.json
├── mcp.json
├── package.json
├── tsconfig.json
├── README.md
├── MASTER_SPEC.md
├── IMPLEMENTATION_PLAN.md
├── AGENTS.md
│
├── skills/
│   ├── setup-project/SKILL.md
│   ├── work-task/SKILL.md
│   ├── delegate-cursor/SKILL.md
│   └── record-result/SKILL.md
│
├── server/
│   ├── index.ts
│   ├── config/
│   ├── project/
│   ├── vikunja/
│   ├── context/
│   ├── git/
│   ├── runs/
│   └── delegates/
│       ├── types.ts
│       ├── environment.ts
│       └── cursor.ts
│
├── templates/
│   ├── TASK.md
│   ├── CONTEXT.md
│   └── RESULT.md
│
├── roles/
│   ├── planner.md
│   ├── implementer.md
│   └── reviewer.md
│
├── examples/
│   ├── project.yaml
│   ├── user-config.yaml
│   └── run.json
│
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
```

## 책임 경계

### `skills/`
Agent가 언제 어떤 MCP tool을 사용하고 어떤 순서로 작업할지 정의한다.
비즈니스 로직을 Skill prompt에 과도하게 넣지 않는다.

### `server/config`
로컬 사용자 설정과 project config를 읽는다.
Secret을 출력하지 않는다.

### `server/project`
현재 cwd가 어떤 workspace인지 결정한다.
Git root를 기준으로 동작한다.

### `server/vikunja`
Vikunja API v2 전용 adapter.
OpenAPI에 없는 field/endpoint를 추측하지 않는다.

### `server/context`
Task/Comment/Attachment metadata를 Context Pack으로 정리한다.
파일 다운로드/path 처리는 deterministic code에서 수행한다.

### `server/git`
Main Agent 검증에 필요한 Git 상태를 제공한다.

### `server/runs`
Delegation 감사 이력:
- run metadata
- Task Packet
- RESULT
- logs
- lock

### `server/delegates`
Provider-neutral interface와 Cursor adapter.
향후 다른 CLI 추가 지점이다.

## 우선순위

1. config
2. project binding
3. Vikunja task context
4. run protocol
5. Cursor process
6. Skills
