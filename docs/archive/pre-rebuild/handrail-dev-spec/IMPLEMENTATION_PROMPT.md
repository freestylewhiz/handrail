# IMPLEMENTATION PROMPT
## Codex용 개발 착수 지시

당신은 이 repository의 Main Development Agent이다.

목표는 `MASTER_SPEC.md`에 정의된 **Agent Development Workflow MVP**를 실제로 구현하는 것이다.

처음부터 전체 구현을 시작하지 말고 반드시 아래 순서를 따른다.

---

# 1. 먼저 읽을 파일

1. `README.md`
2. `MASTER_SPEC.md`
3. `PROJECT_STRUCTURE.md`
4. `AGENTS.md`
5. `templates/TASK.md`
6. `templates/CONTEXT.md`
7. `templates/RESULT.md`
8. `roles/planner.md`
9. `roles/implementer.md`
10. `roles/reviewer.md`
11. `examples/`

---

# 2. Phase 0: 환경 Recon

기능 구현 전에 현재 로컬 환경을 실제로 조사한다.

## Codex

확인:

- Codex CLI version
- Plugin loading 방식
- root `plugin.json` Agent Plugin 지원 여부
- Skill discovery 방식
- MCP server 연결 방식
- repository/user scope 설치 방식

공식 문서와 실제 설치 상태가 다르면 실제 실행 환경을 우선한다.

## Cursor

직접 확인:

```bash
which agent || command -v agent
agent --version
agent --help
```

확인:

- non-interactive 실행
- `-p` / `--print`
- `--output-format`
- cwd/workspace 지정
- sandbox/permission 관련 옵션
- exit code 동작

Cursor command flag를 추측하지 않는다.

## Vikunja

사용자 설정에서 base URL 확보 후:

```text
<base-url>/api/v2/openapi.json
```

을 읽는다.

OpenAPI를 실제 endpoint 모델의 authority로 사용한다.

확인:

- project
- views
- task
- comments
- attachments
- labels
- Kanban bucket/task movement

API v2가 없으면 v1 fallback을 임의 구현하지 말고 blocker로 기록한다.

## Runtime

확인:

- Node.js
- npm/pnpm/yarn
- TypeScript
- Git

---

# 3. IMPLEMENTATION_PLAN.md 생성

Recon 뒤 실제 기능 구현 전에 `IMPLEMENTATION_PLAN.md`를 작성한다.

반드시 포함:

```markdown
# Implementation Plan

## Environment

## Confirmed Interfaces

### Codex
### Cursor
### Vikunja

## Proposed Technology

## Architecture

## Directory Structure

## MCP Tool Surface

## Skill Design

## Security Model

## Test Strategy

## Phase Plan

## Risks

## Open Questions

## Spec Deviations
```

`MASTER_SPEC.md`와 다른 구현이 필요하면 반드시 `Spec Deviations`에 이유를 기록한다.

---

# 4. 구현 원칙

## Small Core

MVP 범위를 벗어나지 않는다.

만들지 않는다:

- Web UI
- Chat UI
- DB server
- Gemini support
- Agent monitoring dashboard
- Native subagent tracking
- Parallel write worker
- Vector DB
- automatic PR/merge

## Deterministic code로 구현할 것

- Vikunja HTTP
- config
- path validation
- subprocess
- timeout
- stdout/stderr
- run IDs
- locking
- Git status/diff
- RESULT validation

## Agent reasoning에 맡길 수 있는 것

- 관련 Attachment 선택
- Context 요약
- FACT/HYPOTHESIS 분류
- 직접 구현 vs Cursor delegation 판단
- 최종 작업 요약

## Main Agent Authority

Cursor에게 Vikunja write credential을 전달하지 않는다.

Cursor process 환경은 parent environment 전체 복사가 아니라 가능하면 allowlist 방식으로 구성한다.

제거 대상:

- VIKUNJA_TOKEN
- API secrets
- 불필요한 cloud credentials

---

# 5. 구현 순서

## Phase 1

- package scaffold
- portable Agent Plugin manifest
- MCP server skeleton
- project/user config
- Git root resolver
- tests

Phase 1이 통과하기 전 Phase 2로 넘어가지 않는다.

## Phase 2

- Vikunja API v2 client
- Project binding
- Task Context
- Comments
- Attachments
- workflow state
- tests

## Phase 3

- run model
- run store
- lock
- TASK/CONTEXT/RESULT generation + validation
- tests

## Phase 4

- Cursor capability detection
- Cursor runner
- timeout
- stdout/stderr
- failure handling
- tests

## Phase 5

- setup-project skill
- work-task skill
- delegate-cursor skill
- record-result skill

## Phase 6

- integration test
- security test
- README usage
- example workflow

각 Phase 후 test를 실행하고 regression을 확인한다.

---

# 6. Cursor Delegation 완료 조건

Cursor가 "완료했다"고 출력했다고 완료로 처리하지 않는다.

Main Agent는 반드시 다음을 확인한다.

```text
git status
git diff
```

그리고:

- Scope
- Constraints
- Acceptance Criteria
- test
- RESULT.md

를 실제 repository 상태와 비교한다.

불일치하면 failed 또는 needs-review로 처리한다.

---

# 7. 테스트

최소 테스트:

- config parsing
- repo/project resolution
- safe attachment filename/path
- API error mapping
- Vikunja mock responses
- run directory
- write lock
- Cursor not installed
- Cursor timeout
- Cursor non-zero exit
- RESULT missing
- RESULT malformed
- secret environment stripping
- happy path
- failure path

가능하면 외부 Vikunja/Cursor 없이 대부분 unit/integration test가 실행되도록 adapter/mock 경계를 만든다.

실제 Cursor/Vikunja E2E는 optional integration test로 분리한다.

---

# 8. 코드 품질

- 명확한 type
- 최소 dependency
- secret masking
- structured errors
- subprocess shell interpolation 금지
- testable interfaces
- provider adapter 분리
- Vikunja adapter 분리
- 과도한 abstraction 금지

---

# 9. 완료 산출물

최종적으로 다음이 존재해야 한다.

```text
plugin.json
mcp.json
skills/
server/
templates/
roles/
tests/
README.md
MASTER_SPEC.md
IMPLEMENTATION_PLAN.md
```

README 사용 흐름:

```text
1. plugin 설치
2. VIKUNJA_TOKEN 설정
3. repository ↔ Vikunja Project 연결
4. Codex에서 Task 분석
5. Cursor delegation
6. Codex 검증
7. Vikunja Review 기록
```

---

# 10. 최종 보고

```markdown
# Implementation Result

## Implemented

## Architecture

## Files Added/Changed

## Tests

## Manual Verification

## Security Checks

## Known Limitations

## Spec Deviations

## Next Recommended Step
```

실제 확인되지 않은 기능을 "완료"로 표현하지 않는다.
