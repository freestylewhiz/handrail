# Agent Development Workflow
## MASTER SPEC v0.2

Status: Draft for implementation
Primary Main Agent: Codex CLI
Primary Delegated Agent: Cursor CLI
Project UI / Work History: Vikunja
Source History: Git

---

# 1. 목적

이 프로젝트는 로컬 소프트웨어 개발 과정에서 사람이 **Codex CLI를 Main Agent**로 사용하고,
Codex가 Vikunja의 Task/첨부자료/댓글을 개발 Context로 활용하며 필요할 때
**Cursor CLI에 특정 개발 작업을 위임**할 수 있도록 한다.

사람은 별도 AI 프로젝트 관리 프로그램과 대화하지 않는다.

사람의 주 대화 상대는 Codex CLI이다.

Vikunja는 다음을 담당한다.

- Project 및 Task 관리
- Kanban
- 버그 리포트와 요구사항
- 댓글
- 이미지/PDF/로그/JSON 등 첨부자료
- Agent 실행 결과 요약
- 상태 및 작업 이력

Git repository는 다음을 담당한다.

- 실제 소스코드
- 변경 diff
- branch / commit
- 테스트
- 코드 이력

본 프로젝트가 추가하는 핵심 기능:

1. 현재 로컬 Git repository와 Vikunja Project를 연결한다.
2. Codex가 Vikunja Task를 읽고 개발 Context를 구성한다.
3. Codex가 Cursor CLI에 표준화된 Task Packet으로 작업을 위임한다.
4. Cursor의 결과를 Codex가 다시 검증한다.
5. Codex가 검증 결과와 실행 이력을 Vikunja에 기록한다.

---

# 2. Non-Goals

MVP에서는 다음을 구현하지 않는다.

- 별도 Web UI
- 별도 Chat UI
- 자체 Kanban
- 자체 Issue Tracker
- 자체 사용자 관리
- Gemini CLI 지원
- Claude Code 지원
- Provider 내부 Native Subagent 추적
- 실시간 Agent Tree UI
- Agent별 Vikunja 사용자 계정
- 다수 Write Agent의 동시 코드 수정
- Git worktree 기반 병렬 작업
- 자동 merge
- 자동 PR 생성
- 자동 Done
- Vector DB / RAG
- Sprint / Epic / Story Point
- 토큰 비용 대시보드
- 원격 Agent Fleet

---

# 3. 용어

## Main Agent

사용자와 직접 대화하며 현재 Task의 전체 흐름을 지휘하는 CLI Agent.

MVP: Codex CLI

책임:

- Vikunja Context 수집
- 개발 계획
- 위임 판단
- Delegated Agent 실행
- 결과 검증
- 상태 변경
- Vikunja 이력 기록

## Delegated Agent

Main Agent가 외부 CLI 프로세스로 실행하여 특정 Task를 위임하는 작업자.

MVP: Cursor CLI

## Native Subagent

Codex 또는 Cursor가 내부 기능으로 생성하는 자체 Subagent.

MVP에서는 추적하지 않는다.

## Task Packet

Delegated Agent에게 전달되는 표준 입력:

- TASK.md
- CONTEXT.md
- 필요한 Attachment
- Role instruction

## Run

Main Agent 또는 Delegated Agent가 수행한 하나의 실행 단위.

---

# 4. 전체 아키텍처

```text
                         Vikunja
                  Task / Comment / File
                           ▲
                           │
                     read / write
                           │
                        Codex CLI
                      (Main Agent)
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
       Project Bind      Git Repo      Run Store
            │              │              │
            └──────────────┼──────────────┘
                           │
                    Task Packet 작성
                           │
                           ▼
                      Cursor CLI
                   (Delegated Agent)
                           │
                           ▼
                       RESULT.md
                           │
                           ▼
                        Codex
                 diff/test/constraint 검증
                           │
                           ▼
                 Vikunja Review 기록
```

---

# 5. 패키징 전략

MVP 패키지는 **portable Agent Plugin** 형식을 우선한다.

목표 구조:

```text
agent-dev-workflow/
├── plugin.json
├── mcp.json
├── skills/
├── server/
├── templates/
├── roles/
└── tests/
```

현재 Agent Plugins 표준의 root `plugin.json`은 Skills와 MCP server 설정을 함께 패키징할 수 있고,
Cursor도 Agent Plugins 형식을 지원하므로 공통 Core 재사용에 적합하다.

구현 시 설치된 Codex/Cursor 버전의 실제 동작을 검증한다.

과거 호환 형식인 `.codex-plugin/plugin.json`은 기본 구조로 사용하지 않는다.
필요한 경우에만 compatibility layer로 추가한다.

---

# 6. Repository ↔ Vikunja Project 연결

기본 관계:

```text
1 Git Repository
        ↕
1 Vikunja Project
```

Repository를 Kanban View 자체에 직접 연결하지 않는다.

Vikunja Project가 작업의 논리 단위이며 Kanban은 Project 내부의 View이다.

각 개발 repository root:

```text
.agent-workflow/
└── project.yaml
```

예:

```yaml
version: 1

workspace_id: "jdx-data"

vikunja:
  project_identifier: "JDXDATA"
  development_view: "Development"

workflow:
  brainstorm: "Brainstorm"
  ready: "Ready"
  doing: "Doing"
  review: "Review"
  done: "Done"
```

`workspace_id`는 실제 directory path와 분리한다.

---

# 7. 사용자 설정

사용자별 설정은 repository 밖에 둔다.

예:

```text
~/.config/agent-dev-workflow/config.yaml
```

예시:

```yaml
vikunja:
  base_url: "http://localhost:3456"
  token_env: "VIKUNJA_TOKEN"

delegates:
  cursor:
    executable: "agent"
    default_timeout_seconds: 1800
```

실제 secret은 환경변수로 전달한다.

```bash
export VIKUNJA_TOKEN="..."
```

다음 위치에 Token 저장 금지:

- Git tracked file
- Task Packet
- Cursor prompt
- RESULT.md
- stdout log
- Vikunja Comment

---

# 8. Vikunja 연동

신규 연동은 Vikunja API v2를 사용한다.

Endpoint/request/response 구조를 추측하지 않는다.

실제 대상 인스턴스에서 다음을 authority로 사용한다.

```text
/api/v2/openapi.json
```

API v2가 없는 인스턴스는 오류를 반환한다.
MVP에서 v1 fallback을 구현하지 않는다.

인증은 Bearer API token을 사용한다.

최소 기능:

- Project 조회
- Project identifier 조회
- Project View 조회
- Task 조회
- Task comments 조회
- Task comment 생성
- Task labels 조회/변경
- Task attachments 목록 조회
- Attachment 다운로드
- Kanban bucket 또는 상태에 해당하는 Task 위치 변경

실제 API 모델은 OpenAPI에 따라 구현한다.

---

# 9. Vikunja Workflow

MVP 표준 상태:

```text
Brainstorm
Ready
Doing
Review
Done
```

Blocked는 bucket 대신 label을 권장한다.

```text
blocked
```

상태 전환:

```text
Brainstorm
    │ Human
    ▼
Ready
    │ Codex 작업 시작
    ▼
Doing
    │ 구현 완료 및 검증
    ▼
Review
    │ Human
    ▼
Done
```

Agent는 Done을 자동 수행하지 않는다.

Review 통과 표시는 label 또는 Comment로 남긴다.

---

# 10. Vikunja Task 권장 포맷

```markdown
## Problem

## Goal

## Constraints

## Acceptance Criteria

- [ ] ...

## Evidence

## Notes
```

정보가 없을 경우 Main Agent가 UNKNOWN으로 분류한다.

---

# 11. Context 모델

Task Context 구성 시 반드시 다음을 구분한다.

## FACT
코드, 로그, 테스트, 파일에서 확인한 사실.

## HUMAN_CONSTRAINT
사람이 명시한 변경 금지/운영 조건.

## HUMAN_HYPOTHESIS
사람이 제시한 원인 추측.

## AGENT_FINDING
Agent가 코드/자료를 분석해 발견한 내용.

## ACCEPTANCE_CRITERIA
완료 판단 조건.

## UNKNOWN
구현에 영향을 줄 수 있지만 확인되지 않은 사항.

`HUMAN_HYPOTHESIS`를 FACT로 자동 승격하지 않는다.

---

# 12. Attachment

지원 우선순위:

1. text / log
2. JSON / YAML / CSV
3. images
4. PDF
5. 기타 파일

Main Agent는 모든 Attachment를 무조건 Cursor에게 전달하지 않는다.

먼저 relevance를 판단하고 필요한 파일만 Run directory에 materialize한다.

Attachment role 예:

- Evidence
- Expected Result
- Actual Result
- Constraint
- Reference
- Reproduction Data

파일명은 신뢰하지 않는다. Path traversal 방지 필수.

---

# 13. Role 모델

MVP role:

- Planner
- Implementer
- Reviewer

실제 Cursor delegation은 우선 Implementer role을 구현한다.

Role은 provider와 분리한다.

잘못된 설계:

```text
cursor-implementer
codex-implementer
```

권장:

```text
role = implementer
provider = cursor
```

---

# 14. Task Packet Protocol

Run directory:

```text
.agent-workflow/
└── runs/
    └── <TASK-ID>/
        └── <RUN-ID>/
            ├── run.json
            ├── TASK.md
            ├── CONTEXT.md
            ├── attachments/
            ├── stdout.log
            ├── stderr.log
            └── RESULT.md
```

`runs/`는 기본적으로 `.gitignore` 대상이다.

---

# 15. TASK.md 계약

Delegated Agent가 “무엇을 해야 하는지” 정의한다.

필드:

- Task ID
- Role
- Goal
- Scope
- Do Not
- Required Validation
- Result Path

불필요한 전체 대화 이력을 포함하지 않는다.

---

# 16. CONTEXT.md 계약

Delegated Agent가 “무엇을 알아야 하는지” 정의한다.

필드:

- Problem
- Facts
- Human Constraints
- Human Hypotheses
- Agent Findings
- Acceptance Criteria
- Relevant Files
- Evidence
- Unknowns

---

# 17. RESULT.md 계약

Delegated Agent의 응답은 자연어 채팅만으로 끝내지 않는다.

반드시 RESULT.md를 생성한다.

필드:

- Status: completed | blocked | failed
- Summary
- Files Changed
- Tests
- Findings
- Risks
- Unresolved
- Suggested Next Step

Cursor stdout의 “완료” 표현만으로 성공 처리하지 않는다.

---

# 18. Cursor CLI Runner

Runner 책임:

- Cursor executable 탐색
- 설치 여부 확인
- version 확인
- `--help` 기반 capability 확인
- cwd 고정
- non-interactive process 실행
- stdout/stderr 수집
- timeout
- exit code
- RESULT.md 생성 여부 확인
- run.json 갱신

현재 Cursor CLI의 비대화형 실행을 사용한다.

구현 시 실제 설치 버전의 help를 먼저 확인한다.

현재 기준 예시:

```bash
agent -p "..." --output-format json
```

CLI option은 adapter 내부에만 위치시킨다.

Cursor prompt 예:

```text
You are a delegated Implementer.

Read:
- <run>/TASK.md
- <run>/CONTEXT.md
- <role>/implementer.md

Implement only the requested scope in the current repository.

Write the final structured result to:
<run>/RESULT.md
```

---

# 19. Main Agent 검증

Cursor가 completed를 반환해도 Main Agent는 반드시 검증한다.

최소 검증:

1. `git status`
2. `git diff`
3. 변경 파일이 Scope와 일치하는지 확인
4. Human Constraint 위반 확인
5. Acceptance Criteria 검토
6. Cursor가 보고한 test command/result 확인
7. 가능하면 relevant test 재실행
8. RESULT.md와 실제 repository 상태 비교

검증 실패 시 Task를 Review로 보내지 않는다.

---

# 20. Run 모델

예:

```json
{
  "schema_version": 1,
  "run_id": "RUN-20260930-0001",
  "task_id": "JDXDATA-42",
  "workspace_id": "jdx-data",
  "parent_run_id": null,
  "main_agent": {
    "provider": "codex",
    "role": "orchestrator"
  },
  "delegated_agent": {
    "provider": "cursor",
    "role": "implementer"
  },
  "status": "running",
  "base_sha": "abc123",
  "head_sha": null,
  "started_at": "2026-09-30T00:00:00Z",
  "finished_at": null
}
```

---

# 21. Vikunja 이력

Vikunja에는 모든 raw output을 기록하지 않는다.

요약 Comment 예:

```markdown
## 🤖 Agent Implementation

Main Agent: Codex
Delegated Agent: Cursor CLI
Role: Implementer
Run: RUN-20260930-0001

### Summary
...

### Files Changed
...

### Verification
...

### Git
Base: ...
Head: ...

### Findings
...

### Remaining Risks
...
```

Raw stdout/stderr는 local run directory에 둔다.

---

# 22. Vikunja Identity

Delegated Agent별 Vikunja user를 생성하지 않는다.

필요하면 API 전용 system account 하나를 사용한다.

실제 작업자 identity는 Comment body와 run metadata에 남긴다.

---

# 23. Git

Task reference는 Vikunja Project identifier 기반 사용을 권장한다.

예:

```text
JDXDATA-42
```

권장 branch:

```text
feature/JDXDATA-42-short-description
bugfix/JDXDATA-42-short-description
```

권장 commit:

```text
fix(replay): preserve pause state [JDXDATA-42]
```

MVP에서 자동 commit은 필수 기능이 아니다.

---

# 24. Concurrency

MVP에서는 workspace당 Write Delegation 1개만 허용한다.

```text
max_write_delegate_per_workspace = 1
```

lock 파일 또는 OS file lock 사용.

---

# 25. 보안

필수:

- Vikunja token 로그 금지
- Cursor child process에 Vikunja token 전달 금지
- 최소 환경변수만 child process에 전달
- `.env` 자동 Context 포함 금지
- SSH key/private key 접근 금지
- attachment filename sanitization
- download destination 고정
- Task text를 shell command로 직접 실행 금지
- Agent output을 shell code로 eval 금지
- subprocess argument 배열 사용
- timeout
- process termination
- symlink/path traversal 검증
- run directory 외 삭제 금지

가능하면 Cursor 실행 environment allowlist를 사용한다.

---

# 26. 실패 처리

정상 실패 상태:

- Cursor 미설치
- Cursor authentication failure
- unsupported CLI version
- timeout
- non-zero exit
- RESULT.md missing
- malformed RESULT
- test failure
- constraint violation
- Vikunja unavailable
- attachment download failure

Delegated Agent 실패 시:

- Run = failed
- Task = Doing 유지
- raw log 저장
- Vikunja에는 간략한 실패 기록
- 사용자에게 다음 조치 보고

---

# 27. MCP Tool 최소 설계

권장:

```text
project_status
project_bind

task_context
task_set_workflow_state
task_add_comment

delegate_cursor
delegate_result
```

필요 이상으로 Vikunja CRUD endpoint를 그대로 tool 하나씩 노출하지 않는다.

---

# 28. Skill 최소 설계

MVP Skill:

```text
setup-project
work-task
delegate-cursor
record-result
```

## setup-project

- Git root 확인
- workspace config 확인
- Vikunja Project 연결
- View / Workflow bucket 확인
- project.yaml 생성

## work-task

- Task Context 수집
- Human/Agent 정보 분류
- 관련 코드 조사
- 계획 수립
- Doing 전환
- 직접 구현 vs Cursor 위임 선택

## delegate-cursor

- Run 생성
- Task Packet 생성
- Cursor 실행
- Result 수집
- 검증

## record-result

- 검증 결과 요약
- Vikunja Comment
- Review 상태 이동
- Done 금지

---

# 29. 목표 Project 구조

```text
agent-dev-workflow/
├── plugin.json
├── mcp.json
├── README.md
├── AGENTS.md
├── package.json
├── tsconfig.json
│
├── skills/
│   ├── setup-project/
│   │   └── SKILL.md
│   ├── work-task/
│   │   └── SKILL.md
│   ├── delegate-cursor/
│   │   └── SKILL.md
│   └── record-result/
│       └── SKILL.md
│
├── server/
│   ├── index.ts
│   ├── config/
│   ├── project/
│   ├── vikunja/
│   ├── context/
│   ├── runs/
│   ├── git/
│   └── delegates/
│       ├── types.ts
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
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
```

TypeScript/Node.js는 권장안이며 절대 요구사항은 아니다.

---

# 30. Acceptance Criteria

## Plugin / Skills

- [ ] root `plugin.json` 기반 Agent Plugin skeleton
- [ ] Skills가 Codex에서 인식 가능한 구조
- [ ] MCP server를 plugin에서 연결 가능

## Project Binding

- [ ] 현재 Git root 검색
- [ ] `.agent-workflow/project.yaml` 읽기
- [ ] Vikunja Project identifier 검증
- [ ] Development View 검증

## Vikunja

- [ ] API v2 compatibility 확인
- [ ] Task 읽기
- [ ] Comment 읽기
- [ ] Attachment metadata 읽기
- [ ] Attachment 안전 다운로드
- [ ] Agent summary Comment 작성
- [ ] Ready → Doing → Review 처리
- [ ] Done 자동 처리 금지

## Context

- [ ] FACT / HUMAN_CONSTRAINT / HUMAN_HYPOTHESIS / AGENT_FINDING / UNKNOWN 구분
- [ ] 모든 Attachment 무조건 위임 금지
- [ ] TASK.md 생성
- [ ] CONTEXT.md 생성

## Cursor

- [ ] Cursor CLI 존재 검증
- [ ] version/help 확인
- [ ] non-interactive 실행
- [ ] cwd 명시
- [ ] stdout/stderr 저장
- [ ] timeout
- [ ] RESULT.md 검사
- [ ] Cursor에 Vikunja Token 미전달

## Main Agent Verification

- [ ] git diff 확인
- [ ] git status 확인
- [ ] Scope violation 검사
- [ ] Constraint violation 검사
- [ ] test 확인
- [ ] 검증 후 Vikunja Review 기록

## Run History

- [ ] run.json 저장
- [ ] base/head SHA 저장
- [ ] failed/completed 구분
- [ ] workspace write lock

## Tests

- [ ] Config unit test
- [ ] Project resolver unit test
- [ ] Vikunja client mock test
- [ ] Attachment path security test
- [ ] Cursor runner mock process test
- [ ] Cursor timeout test
- [ ] RESULT missing test
- [ ] happy-path integration test
- [ ] failure-path integration test

---

# 31. 구현 단계

## Phase 0 — Recon

실제 코드를 작성하기 전에:

1. 설치된 Codex CLI version 및 Plugin/Skill/MCP loading 확인
2. 설치된 Cursor CLI version / executable / `--help` 확인
3. 대상 Vikunja의 `/api/v2/openapi.json` 확인
4. Node/TypeScript 환경 확인
5. Git 초기 상태 확인

결과: `IMPLEMENTATION_PLAN.md`

## Phase 1 — Core Skeleton

- plugin manifest
- MCP hello/status
- config
- project resolver
- tests

## Phase 2 — Vikunja

- API v2 client
- Project binding
- Task Context
- Attachment
- Comment
- workflow state

## Phase 3 — Run Protocol

- Run model
- TASK
- CONTEXT
- RESULT
- local run store
- lock

## Phase 4 — Cursor

- capability discovery
- non-interactive runner
- timeout
- stdout/stderr
- RESULT validation

## Phase 5 — Skills

- setup-project
- work-task
- delegate-cursor
- record-result

## Phase 6 — Integration

- happy path
- Cursor failure
- Vikunja failure
- secret propagation check
- documentation

---

# 32. 변경 금지 핵심 결정

1. Human ↔ Codex가 기본 대화 구조다.
2. 별도 Chat UI를 만들지 않는다.
3. Vikunja를 Project UI로 사용한다.
4. Main Agent만 Vikunja write를 수행한다.
5. Cursor는 Delegated Agent다.
6. Native Subagent 추적은 범위 밖이다.
7. Repo ↔ Vikunja Project를 연결한다.
8. Provider와 Role을 분리한다.
9. TASK / CONTEXT / RESULT 계약을 유지한다.
10. Done은 사람만 수행한다.
11. workspace당 Write Delegation은 하나만 허용한다.
12. API/CLI 옵션은 실행 환경에서 검증한 뒤 adapter에 한정한다.

변경 필요 시 `IMPLEMENTATION_PLAN.md > Spec Deviations`에 이유를 먼저 기록한다.

---

# 33. 공식 기술 참고

구현 당시 최신 문서를 다시 확인한다.

- OpenAI Plugins / Skills
  - https://developers.openai.com/plugins/build/plugins
  - https://developers.openai.com/plugins/concepts/skills

- Cursor CLI / Plugins
  - https://cursor.com/docs/cli/overview
  - https://cursor.com/docs/cli/using
  - https://cursor.com/docs/cli/mcp
  - https://cursor.com/docs/plugins

- Vikunja API v2
  - https://vikunja.io/docs/api-v2/

Vikunja endpoint shape는 대상 인스턴스의 `/api/v2/openapi.json`을 최우선으로 한다.
