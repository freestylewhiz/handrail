# Handrail 재구현 계약

> 초기 v1 재구현의 계약·범위·결과 기록이다. 현재 alpha.5의 추가 범위와 공개 절차는 [구현 상태](status.md), [Summary와 기획 완료](summaries.md)를 우선한다.


2026년 10월 6일 요청의 구현 기준이다. 기존 제품의 두 실행 경로를 하나의 Herdr 기반 워크플로우로 대체한다. 과거 백로그 전체를 이월하지 않는다. 이번 논의에서 확인한 권한 반복, 실행 신원, 통신 결과, 카드 이력, 완료와 복구, worktree 보존을 이 구조 안에서 다룬다.

## 컴포넌트

| 폴더 | 책임 |
| --- | --- |
| `handrail/setup/` | 연결 설정, 저장소 바인딩, 설치 진단, 실제 자원 경로 사전 점검 |
| `handrail/workflow/` | 계획과 작업 카드, 승인, 상태 전이, 기준별 증거, 완료와 이력 |
| `handrail/agentroom/` | room, worker attempt, 명령 전달, 관찰, 복구, worktree 수명 |
| `handrail/interfaces/agentroom/` | Herdr CLI 프로토콜과 명시적 endpoint/target |
| `handrail/interfaces/vikunja/` | Vikunja v2 HTTP, 카드 관계와 외부 동기화 |
| `handrail/interfaces/git/` | Git worktree 생성, 소유권 확인, 통합 |
| `handrail/authorization/` | 승인 범위 기록과 재사용, 변경 범위 계산 |
| `handrail/shared/` | 구조화 오류, SQLite transaction/journal/outbox, 시각과 식별자 |
| `handrail/hooks/` | 등록된 내부 후처리, 실패 격리와 재시도 |
| `handrail/cli.py` | 인자와 출력만 담당하는 조립 지점 |

Python 3.9 이상, 표준 라이브러리만 사용한다. 과거 런타임을 import하는 호환 껍데기를 만들지 않는다. 기존 저장소/사용자 상태를 자동 변환하지 않는다. 새 상태 저장소는 별도 v1 namespace를 사용한다.

## 공통 구현 API

`shared.errors.HandrailError(code, message, *, details=None, retryable=False, uncertain=False)`.

`shared.store.Store(path)`는 읽기 시 파일을 생성하지 않는다. `read(kind, id) -> dict|None`, `list(kind) -> list[dict]`, `history(entity=None) -> list[dict]`, `transaction()`을 제공한다.

`with store.transaction() as tx:` 내부 API:

- `tx.get(kind, id) -> dict|None`, `tx.require(kind,id) -> dict`, `tx.list(kind)`
- `tx.put(kind,id,value)` (JSON dict), `tx.event(entity,kind,data) -> event_id`
- `tx.enqueue(topic,key,payload)` (동일 key의 동일 payload는 중복 생성하지 않음)

외부 I/O는 transaction 바깥에서 실행한다. 작업 전 intent와 고정 operation ID를 기록하고, 불명확한 응답은 unknown으로 남겨 재조회한다. 외부 부작용을 무조건 재실행하지 않는다. JSON dict가 컴포넌트 간 직렬화 계약이다. 현재 상태와 과거 사건은 분리한다.

## Workflow 계약

`WorkflowService(store)`는 순수 로컬 도메인 서비스다. setup/agentroom/외부 adapter를 import하지 않는다.

- `create_plan(title, criteria: dict, operation_id=None)`
- `approve_plan(plan_id, approval)`
- `create_work(plan_id, title, criteria: dict, operation_id=None)`
- `start_work(work_id, attempt_id)`
- `record_evidence(entity_id, criterion_id, evidence, revision)`
- `review_work(work_id, verdict, notes)`
- `complete_work(work_id, revision)`
- `verify_plan(plan_id, revision)`
- `submit_review(plan_id)`
- `accept_plan(plan_id, approval)`
- `reopen_plan(plan_id, reason)`
- `status(plan_id=None)`

plan/work kind의 문서에 `id`, `state`, `cycle`, `criteria`, `evidence`, `revision`을 포함한다. work에는 `plan_id`, `attempt_id`, review와 integration 증거를 보존한다. integration은 root가 연결할 별도 `mark_integrated(work_id, revision)` API로 명시한다. criteria는 stable ID -> 설명. evidence는 기준별 nonempty 관찰 근거, Git revision에 묶인다. 모든 완료/accept는 동일 상태 재시도에 안전해야 한다. plan의 Review/Done은 모든 해당 cycle 작업이 verified Done이고 plan 증거가 같은 revision일 때만 허용한다. reopen은 기존 work를 보존하고 새 cycle을 연다.

외부 카드 동기화는 `tx.enqueue('board', event_id, {entity_kind, entity_id, event_kind, ...})`로 처리한다. 도메인이 외부 card ID를 강제하지 않는다. 계획/작업 생성/전이/핵심 증거와 승인만 동기화하고 단순 관찰은 로컬 이력에 둔다.

## 외부 adapter 계약

`interfaces.agentroom.herdr.HerdrClient(endpoint: dict, executable='herdr', timeout=30)`.
endpoint는 정확히 `{session: name}` 또는 `{socket: absolute_path}`. 함수별 explicit ID 필수. `.agent_get(target)`, `.agent_prompt(target,text)`, `.agent_read(target,source='visible',lines=120)`, `.agent_keys(target,keys)`, `.agent_start(name,provider,pane_id,model,effort=None)`, `.workspace_create(cwd,label)`, `.workspace_get(id)`, `.workspace_close(id)`, `.tab_create(workspace_id,cwd,label)`, `.pane_get(id)`. 반환은 Herdr envelope를 푼 dict(상세 nested record는 root가 정규화). 읽기만 text str 가능. timeout/stall 시 `.uncertain=True`, pre-input rejection은 false. 자동 재전송 금지. HERDR_ENV를 추가/변조하지 않는다. 라우팅 env만 명시 endpoint로 고정하고 인증용 다른 환경은 보존한다.

`interfaces.vikunja.client.VikunjaClient(base_url,token,allow_insecure_http=False,timeout=30)`의 `request(path,method='GET',body=None)`, `pages(path)`.
`interfaces.vikunja.board.VikunjaBoard(client,project_id,view_id,states)`의 `validate()`, `get_task(id)`, `create_task(title,description,operation_id)`, `find_task(operation_id)`, `ensure_relation(parent_id,child_id)`, `move_task(id,state,expected_state=None)`, `ensure_comment(id,text,operation_id)`.
V2 계약은 `docs/vikunja-v2-contract.md`를 참고. redirect/auth 노출 금지, 응답 불명확시 자동 write 재시도 금지, marker readback 재조정. child Review bucket 필수화 금지.

## 실행과 권한

내부 pane/외부 조율자는 지원 모드다. HERDR_ENV는 context 힌트이고 권한이나 delivery 증거가 아니다. 실행마다 endpoint + workspace/pane/terminal/provider session + Git worktree identity를 고정한다. 관찰 결과와 작업 완료는 별도로 기록한다. unknown delivery는 재전송 전에 확인한다. close/keys는 해당 동작의 승인 범위로 확인한다.

신규 worktree는 설정한 외부 영속 루트 또는 XDG fallback. 기존 실행 경로는 고정한다. private 관리 상태는 worker tree와 분리한다. host sandbox의 쓰기/IPC/네트워크 권한을 앱 내부 승인으로 부여할 수 없다. 실제 실행에 필요한 경로·Git common dir·소켓·보드 endpoint를 사전 출력한다.

## 협업 작업 소유권

- Astra: `handrail/workflow/`만 구현. 기준별 증거, 상태/이력, 재시도와 outbox 담당.
- Grok: `handrail/interfaces/agentroom/`, `handrail/interfaces/vikunja/`만 구현.
- 조율자: 나머지 foundation/setup/agentroom/Git/authorization/CLI/문서/배포 및 최종 연결.

모든 작업은 현재 새 브랜치에서 수행한다. 다른 agent 파일은 수정하지 않는다. 테스트 추가/실행, 외부 테스트 프로젝트 변경, 설치/배포, 커밋/푸시/브랜치 변경은 worker 작업에 포함하지 않는다.
