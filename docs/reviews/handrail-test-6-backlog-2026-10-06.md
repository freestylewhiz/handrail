# Handrail 개선 백로그

`handrail_test_6`의 Codex 세션에서 관찰한 실패를 Handrail 제품의 개선 과제로 정리했다. 핵심은 Herdr workflow에 **실효 권한 준비, 사라진 worker 복구, 세션 재개 안내, 완료 조건과 검증의 연결**이 부족하다는 것이다. 대상 사원관리 프로젝트의 구현이나 복구를 수행하는 문서가 아니다.

분석 기준은 2026년 10월 6일 10:07:18 KST까지의 세션 기록과 Handrail v0.5.0 소스다. 실행 플러그인은 `0.5.0+codex.20261005232722`, source revision은 `58651c76808012ded0e828990fff3a45db3347eb`이다. 설치본과 개발 저장소의 `herdr_workflow.py`, `herdr_transport.py`가 동일함을 확인했다. 기록 수집 후에도 대상 세션이 진행될 수 있으므로 이 문서는 실시간 프로젝트 상태판이 아니다.

근거는 [선별 사건 30건](handrail-test-6-2026-10-06/evidence.csv)과 [분석 범위](handrail-test-6-2026-10-06/manifest.json)에 있다. 아래 E 번호는 CSV의 사건 식별자다. 쓰기 권한 원인과 Handrail 설계상의 책임은 [별도 보고서](handrail-test-6-permissions-2026-10-06.md)에 상세히 설명했다.

## 우선순위와 작업 목록

P0는 다음 Herdr 사용성 검증 전에 해결할 핵심 결함, P1은 반복 운영의 안정성 개선, P2는 사용성 개선이다. 우선순위는 제안이며 아래 ID는 백로그용 로컬 식별자다. 원격 카드 생성이나 구현 착수 승인을 의미하지 않는다.

| ID | 우선순위 | 카드 제목 | 책임 영역 | 기존 후보 연결 |
| --- | --- | --- | --- | --- |
| HR-HERDR-001 | P0 | Herdr 실행 경로에 맞는 권한 준비와 검사 제공 | CLI와 권한 계층 | HR-NEXT-005, 007 |
| HR-HERDR-002 | P0 | 권한 오류를 계층별로 분류하고 조율자의 다음 행동 제공 | 오류 모델과 스킬 | HR-NEXT-008 |
| HR-HERDR-003 | P0 | 사라진 worker의 복구와 pane 식별자 재연결 지원 | Herdr lifecycle | HR-NEXT-010 |
| HR-HERDR-004 | P0 | 완료 조건을 실제 검사와 연결하고 누락을 차단 | 명세와 검증 | 검증 품질 보완 |
| HR-HERDR-005 | P1 | 컨텍스트 압축과 새 세션에서 workflow 재개 정보 제공 | 상태 조회와 스킬 | HR-NEXT-011 |
| HR-HERDR-006 | P1 | CLI 업데이트와 시작 상태를 구분하는 worker 준비 단계 추가 | transport | HR-NEXT-007, 008 |
| HR-HERDR-007 | P1 | worker와 통합 저장소의 의존성 준비를 관리 | 실행 준비와 finish | HR-NEXT-007 |
| HR-HERDR-008 | P1 | 병렬 작업에 공유 API 계약과 실행 설정 전달 | 작업 패킷 | 작업 간 계약 보완 |
| HR-HERDR-009 | P1 | 단계별 상태와 행동 로그를 간결하고 일관되게 제공 | status와 이벤트 | HR-NEXT-008, 011 |
| HR-HERDR-010 | P2 | 연결 안내와 보드 이름 입력을 처음부터 실행 가능하게 제공 | 온보딩과 CLI | 설정 사용성 보완 |

### HR-HERDR-001 Herdr 실행 경로에 맞는 권한 준비와 검사 제공

**문제와 근거:** Handrail이 만드는 worktree는 프로젝트 밖 사용자 데이터 디렉터리에 있다. 조율자는 이를 읽을 수 있었지만 일반 빌드에서 쓰기가 거부됐다(E01, E15). 현재 `preflight`는 legacy run의 worktree 경로를 전달하며 Herdr plan/task의 실제 경로와 제어 채널을 다루지 않는다. `herdr start`는 명세·Git 상태를 검사한 뒤 worktree와 pane을 만들지만 host readiness나 기존 permission adapter를 호출하지 않는다. 단순히 “preflight가 없다”가 아니라 **기존 사전 준비 기능이 Herdr 흐름에 연결되지 않은 상태**다.

**개선 범위:** workflow와 plan/task를 입력받아 조율자, Handrail 관리 프로세스, worker별 요구를 산출한다. 실제 Herdr worktree, Git common directory, 관리 상태·잠금, provider 상태, 의존성·빌드 쓰기, Herdr 제어 채널, Vikunja 접근을 나눈다. 저장된 동의와 현재 실행 환경의 허용 여부를 별도 필드로 반환한다. 호스트 설정을 직접 바꿀 수 없으면 필요한 추가 범위와 적용 주체를 반환한다.

**수용 기준:** 프로젝트만 writable인 환경에서 Herdr worktree의 미충족 쓰기 요구를 worker 시작 전에 표시한다. 검증된 실행 경로와 미확인 요구를 구분하고 미확인을 ready로 표시하지 않는다. 동일 범위의 승인과 실행 경로는 재사용하되 홈 전체 또는 Handrail 관리 원장 전체를 worker writable root로 확장하지 않는다. 쓰기 probe는 승인된 최소 임시 파일로 제한하며 read-only 진단 명령에 숨기지 않는다.

**수정 후보:** `handrail/cli.py`의 preflight dispatch, `permission_adapters.py`, `herdr_workflow.py:start`, Herdr 스킬의 실행 전 준비 절차. 기존 run lifecycle과 Herdr lifecycle은 별도로 유지한다.

### HR-HERDR-002 권한 오류를 계층별로 분류하고 다음 행동 제공

**문제와 근거:** Vite의 파일 쓰기 `EROFS`, Herdr 제어 명령의 `PermissionDenied`, Vikunja 연결 실패가 서로 다른 경계에서 발생했다(E15, E20, E21, E24). 조율자는 원인을 “Herdr worktree가 읽기 전용”으로 일반화하고 여러 빌드 변형을 시도한 뒤 중단했다. 이후 같은 빌드의 escalation 실행은 성공했다(E22, E23). `HerdrClient._run`은 주로 문자열 `Error`를 반환하며 `doctor`는 API 오류까지 `repository_binding` 실패로 묶는다.

**개선 범위:** `actor`, `operation`, `resource`, `execution_boundary`, `error_code`, `confidence`, `delivery_state`, `next_action`을 가진 진단 결과를 제공한다. 파일 쓰기, Git metadata, IPC, API 연결, provider 승인 대기, 도구 옵션 오류를 구분한다. 스킬에는 관측된 오류와 추정을 구별하고, host 제약이면 지원되는 승인 경로로 원래 동작을 재시도하도록 명시한다. prompt 전달이 불명확한 경우에는 재전송 전 관찰 절차를 유지한다.

**수용 기준:** E15의 재현에서 경로와 조율자 경계를 표시한다. E20의 단순 EPERM만으로 IPC 세부 원인을 확정하지 않는다. 같은 미지원 CLI 옵션을 반복 제안하지 않는다. 이미 승인된 작업이라도 호스트의 추가 실행 승인이 필요한 경우 그 이유만 설명하고 구현 범위를 다시 승인받지 않는다.

**수정 후보:** `herdr_transport.py:_run`, `cli.py:doctor`, 스킬의 `references/herdr.md`, 권한 진단 모델. **의존성:** 001의 요구 경로 정보.

### HR-HERDR-003 사라진 worker 복구와 pane 재연결 지원

**문제와 근거:** agent가 사라지자 `collect`와 `recover`가 모두 `agent_not_found`로 실패했다(E06, E07). `recover`는 살아 있는 agent를 조회해야만 진행할 수 있고 `start`는 `unknown` 상태를 차단한다. 조율자가 직접 Herdr tab과 agent를 재생성한 후에야 복구했다(E08, E09). 복구 응답은 `wV:p4`를 관측했지만 Handrail 저장 레코드의 `pane_id`는 `wV:p2`로 남았다. 소스에서도 `recover`는 관측한 pane ID를 worker에 반영하지 않는다.

**개선 범위:** 전달 불확실성 해소와 process/pane 소실 복구를 별도 상태 전이로 모델링한다. 기록된 pane, live agent, provider session, worktree, 기존 지시 해시를 대조하고 동일 카드의 새 attempt를 만든다. 이전 pane과 이벤트는 이력으로 보존하며 현재 identity를 원자적으로 갱신한다. agent 부재만으로 과거 지시가 미전달됐다고 단정하지 않는다.

**수용 기준:** `unknown + agent_not_found`에서 내부 JSON 수정이나 직접 Herdr 명령 없이 복구 가능한 공식 절차가 있다. 살아 있는 중복 agent가 있으면 중복 시작하지 않는다. 복구 후 status/collect/keys가 동일한 live pane을 가리킨다. 미완료 변경·명세·사용자 모델 배정을 보존하며 새 모델을 임의 선택하지 않는다.

**수정 후보:** `herdr_workflow.py:start/collect/recover`, transport의 pane fallback, CLI recovery 옵션. **의존성:** 002의 오류 및 전달 상태 구분.

### HR-HERDR-004 완료 조건을 실제 검사와 연결하고 누락 차단

**문제와 근거:** 계획의 완료 조건에는 브라우저 CRUD, 입력 오류 처리, 재시작 후 데이터 유지가 있지만 등록된 계획 검사에는 `backend_syntax`와 `frontend_build`만 있다. Backend 카드도 entry point 구문 검사 한 개로 `verified=true`가 됐다(E10). 이 성공 표시는 등록된 검사가 통과했다는 의미로는 맞지만 기능 완료의 증거가 충분하다는 의미는 아니다. 이번 세션의 최종 허위 완료를 단정하는 것이 아니라, 검증 누락을 제품이 막지 못하는 점을 지적한다.

**개선 범위:** 명세의 acceptance 항목에 안정적인 ID를 부여하고 command/manual check 및 관측 증거를 연결한다. spec 승인과 plan 검증에서 연결되지 않은 필수 항목을 표시한다. 사람의 기능 검증을 자동화하지 않아도 실제 결과를 기록해야 통과하도록 한다. 조율자 스킬에 구문 검사와 build만으로 CRUD·영속성을 충족시킬 수 없다는 작성 기준을 추가한다.

**수용 기준:** 기능 acceptance가 있는데 syntax/build 검사만 등록된 명세는 누락 항목을 노출한다. 계획 Review 제출 전에 필수 acceptance가 모두 충족돼야 한다. 미실행 항목은 `not_run`, 환경 차단은 `blocked`로 남으며 성공으로 변환되지 않는다. 사용자 최종 Done 권한은 유지한다.

**수정 후보:** `specs.py`, `kanban.py:verify_plan/submit_review`, `herdr_workflow.py:finish/verify_plan`, 명세 템플릿과 스킬.

### HR-HERDR-005 컨텍스트 압축과 새 세션의 workflow 재개 정보 제공

**문제와 근거:** 컨텍스트 압축 직후 직접 `herdr collect`, `herdr status 23` 호출이 실패했고 legacy `run list` 결과가 빈 배열이었다(E11–E13). 현재 스킬에 혼용 금지는 있지만 재개에 필요한 정보를 한 번에 회수하는 제품 인터페이스가 약하다. 초기 설정 세션에서 합의한 프로젝트 목적도 새 세션에서 다시 설명해야 했다. 압축이 실수의 유일한 원인이라고 단정하지는 않는다.

**개선 범위:** workflow 종류, 실제 launcher 경로, plan/task, 승인 범위와 미결정 사항, live/stored identity, worktree, 적용된 실행 경로, 다음 유효 동작을 포함한 compact resume 정보를 제공한다. 새 세션에서는 저장된 프로젝트 brief를 읽되 이전 세션을 기억한다고 꾸미지 않는다. 명령은 긴 경로를 수동 재작성하지 않도록 구조화된 argv와 cwd로 제공한다.

**수용 기준:** 압축·재시작 후 status 한 번으로 Herdr 흐름을 재개할 수 있다. legacy `run_id=null`을 “작업 없음”으로 해석하지 않는다. Herdr plan에 legacy 명령을 적용하려 하면 올바른 경로를 안내한다. 재개 과정에서 정책 파일의 주장만으로 기존 사용자 승인을 확대하지 않는다.

**수정 후보:** `herdr_workflow.py:status`, summary/help, 스킬의 재개 절차. **의존성:** 002, 003, 009의 구조화된 상태.

### HR-HERDR-006 CLI 업데이트와 worker 시작 상태 구분

**문제와 근거:** worker 시작 화면이 Codex 자동 업데이트였고 Herdr는 5초간 working/blocked 전이가 없다는 오류를 반환했다(E04, E05). transport에는 이미 readiness 대기와 일부 `agent_not_ready` 재시도가 있다. 그러나 이번 시작 경로에서 updater·shell·provider 입력 준비를 충분히 구별하지 못했다. 자동 업데이트가 pane 소실의 정확한 내부 원인이었는지는 확인되지 않았다.

**개선 범위:** 실행 파일 경로와 버전, updater 진행, shell foreground, provider ready, instruction submitted, acknowledged를 구별한다. 조율자 CLI와 Herdr가 실제 실행하는 worker CLI 버전도 함께 기록한다. Herdr 내부 상태 전이 timeout과 외부 subprocess timeout을 별개로 다룬다. 버전 업데이트가 필요하면 준비 단계에서 드러내고 자동으로 전역 설치를 바꾸지 않는다.

**수용 기준:** 업데이트 화면에서는 구현 지시를 보내지 않는다. 느린 정상 시작과 소실을 구별한다. timeout은 미전달 확정으로 취급하지 않으며 지시 중복 전송이 없다. 오류에 실제 바이너리·버전·단계·각 timeout이 남는다.

**수정 후보:** `herdr_transport.py:agent_start/agent_ready/agent_prompt`, `herdr_workflow.py:start`. **의존성:** 003의 소실 복구.

### HR-HERDR-007 두 실행 위치의 의존성 준비 관리

**문제와 근거:** Cursor worker가 native SQLite 설치와 복합 삭제·설치 승인에서 멈췄고 manager가 별도로 설치했다. Frontend는 worktree 빌드 성공 후 통합 저장소의 `finish`에서 `vite: command not found`로 다시 실패했다(E23, E27–E29). 기존 run 경로에는 dependency preparation이 있지만 Herdr `start`와 `finish`는 이를 연결하지 않는다.

**개선 범위:** 작업별 package root와 lockfile을 기준으로 worktree 준비와 통합 checkout 준비를 각각 관리한다. manager/worker 실행 주체, registry·cache·native build 요구, 승인된 설치 명령을 기록한다. 새 manifest 생성 후에도 준비 단계를 재진입할 수 있게 한다. 설치 결과의 보안 경고는 영향 검토 항목으로 남기며 강제 major upgrade를 자동 실행하지 않는다.

**수용 기준:** worktree에만 설치된 상태를 integration-ready로 표시하지 않는다. `finish` 전 준비 누락을 구조적으로 진단한다. 삭제와 설치가 결합된 worker 요청은 기존 권한과 별도로 판단한다. 같은 승인 범위의 설치를 새 카드라는 이유로 반복 승인받지 않는다. 원본 lockfile 변경과 환경 준비 결과를 구분한다.

**수정 후보:** `run_preparation.py`의 재사용 가능한 부분, `herdr_workflow.py:start/finish`, 실행 준비 스키마. **의존성:** 001.

### HR-HERDR-008 공유 API 계약과 실행 설정 전달

**문제와 근거:** Backend 기본 포트는 3001이었고 Frontend는 3000을 전제로 작업하다 조율자가 추가 지시했다. 이후 검증 서버에서도 포트 충돌이 발생했다(E30). 현재 start 패킷은 해당 task 승인 명세를 넣고, 지시문에서 언급하는 부모 명세·다른 작업 계약은 명시적으로 고정해 넣지 않는다.

**개선 범위:** API 경로·필드·오류 응답·포트 및 환경변수 계약을 공유 산출물로 정하고 각 work packet에 revision/hash를 연결한다. 검증용 포트는 구현 기본 포트와 별도로 관리한다. 계약 변경이 발생하면 영향받는 작업을 표시한다.

**수용 기준:** 두 worker가 같은 계약 revision을 입력받는다. 포트나 필드 변경을 통합 전에 검출한다. 계약 변경 없이 검증용 가용 포트를 설정할 수 있으며 기존 서비스를 임의 종료하지 않는다.

**수정 후보:** 명세 템플릿, `herdr_workflow.py:start/prompt`의 packet 생성, integration checks. **의존성:** 004의 acceptance 연결.

### HR-HERDR-009 단계별 상태와 행동 로그 일관성

**문제와 근거:** 사용자가 “개발이 완료된 것인지 문제를 해결해야 하는지”를 다시 물었다. 로컬 binding 상태, worker 상태, build 성공, 통합 여부, task Done, plan 검증이 서로 다른 의미인데 한눈에 파악하기 어렵다. `herdr status`는 저장된 worker JSON과 `orchestrator` 같은 포괄적 next 값을 반환한다. 행동 댓글은 조율자가 수동으로 남기고 `_event`도 자동 작성하는 사례가 있었다.

**개선 범위:** 구현·리뷰·통합·검증·사용자 검토 상태와 각 blocker, 증거 범위, 다음 담당자를 요약한다. 저장 상태와 live 관측에는 확인 시각을 붙인다. 자동 행동 댓글과 조율자의 추가 설명 역할을 문서화하고 같은 동작의 중복 댓글을 줄인다. 긴 과거 오류는 이력에 보존하고 현재 장애와 구별한다.

**수용 기준:** “task Done, plan acceptance 미충족”을 명확히 표시한다. binding-only ready를 worker 실행 준비 완료로 표현하지 않는다. 복구된 오류는 현재 blocker로 남지 않는다. 한 동작에는 하나의 canonical action event가 생기며 불확실한 원격 쓰기는 operation ID로 조정한다.

**수정 후보:** onboarding status 표현, `herdr_workflow.py:status/_event`, 스킬의 action-comment 안내. **의존성:** 002, 003, 004.

### HR-HERDR-010 연결 안내와 보드 이름 사용성

**문제와 근거:** 사용자는 복사 가능한 bind 명령을 다시 요청했고 초기 설정 대화에 토큰을 붙여 넣었다. 조율자는 숨김 입력을 안내하고 노출 토큰 교체를 권고했다. 또 `area create --name '사원관리 Frontend'`는 ASCII slug 제약으로 실패했다. 이 사례가 Handrail이 토큰을 유출했다는 뜻은 아니며, 설정 인터페이스 개선 근거다.

**개선 범위:** 실제 설치 경로를 이용한 복사 가능한 명령과 터미널 숨김 입력을 일관되게 제공한다. credential 입력 채널과 일반 명령 입력을 명확히 나눈다. 보드 표시 이름과 내부 slug를 분리하거나, 현재 제약을 도움말과 스킬에 명시한다.

**수용 기준:** 최초 안내만으로 setup/bind 명령을 복사할 수 있다. 토큰을 채팅이나 명령 인자에 넣도록 안내하지 않는다. 한글 표시 이름을 지원하거나 변경 전 명확한 입력 오류를 제공한다. 비밀값이 진단·백로그·댓글로 복제되지 않는다.

**수정 후보:** setup/bind 도움말, area CLI와 onboarding 스킬. 독립 실행 가능한 P2 항목이다.

## 권장 구현 순서와 검증 범위

1. 001과 002로 요구 권한과 오류를 구조화한다. 스킬의 원인 설명·다음 동작 안내도 함께 고친다.
2. 003으로 공식 복구 경로를 완성하고, 006으로 시작 과정의 불확실성을 줄인다.
3. 004와 007로 기능 검증 누락과 통합 환경 준비 누락을 막는다.
4. 005, 008, 009로 긴 조율 세션의 재개·계약·상태 전달을 안정화한다. 010은 독립 개선한다.

구현 후 수용 검증은 **제한된 조율자 환경 + 별도 Herdr worker 환경**에서 수행해야 한다. 테스트 사례에는 파일 쓰기 거부, IPC 거부, API 거부, updater 시작, agent 소실, 컨텍스트 재개, 통합본 의존성 누락, 기능 acceptance 미연결을 포함한다. 단위 테스트만으로 host 권한 문제가 해결됐다고 판정하지 않는다. 이번 작업은 기록·소스 분석으로 백로그를 작성한 것이며 대상 프로젝트나 Handrail 런타임을 변경하거나 테스트를 실행하지 않았다.

## 근거가 확인된 코드 위치

- [Herdr worktree와 시작 경로](../../handrail/herdr_workflow.py): `_worktree`, `start`.
- [복구와 완료 처리](../../handrail/herdr_workflow.py): `recover`, `finish`, `status`.
- [Herdr transport](../../handrail/herdr_transport.py): `_run`, `agent_ready`, `agent_prompt`.
- [CLI](../../handrail/cli.py): `doctor`, `dispatch`의 `preflight` 분기.
- [기존 권한 adapter](../../handrail/permission_adapters.py)와 [v0.4 적용 범위](../permissions-v0.4.md).
- [기존 백로그](../../handrail-dev-spec/v0/BACKLOG.md)와 [권한 정책 검토](../permission-policy-review.md).
