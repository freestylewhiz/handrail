# 현재 구조 비교와 설계 판단

기준일: 2026-09-30. 파일 내용과 함수 동작을 읽어 비교했다. 아래에서 “있음”은 코드 존재를 뜻하며 이번 턴의 실행 검증을 뜻하지 않는다.

## 1. 세 가지 기준 비교

| 항목 | 기존 설계안 | 현재 코드 | v0 권장안 |
| --- | --- | --- | --- |
| 제품·배포 | `agent-dev-workflow` portable plugin | `handrail-workflow` Python 패키지 + 전역/프로젝트 스킬 | 제품명 Handrail, 배포물 Codex 플러그인 |
| 구현 언어 | TypeScript/Node 권장 | 표준 라이브러리 중심 Python | Python 재사용, JSON 유지 |
| Codex 진입점 | 여러 스킬 + MCP | 하나의 Handrail 스킬 + CLI | 하나의 플러그인 스킬 + 번들 도구, MCP 후속 |
| Vikunja 운영 | 외부 서비스 전제, 설치 UX 불명확 | Docker 관리형·외부 연결 모두 지원 | 외부 연결만 제공, 없으면 공식 설치 안내 |
| 초기 설정 | 환경변수·YAML 예시 | 소스·칸반 데이터 경로 요구, 원격 연결 때 토큰 입력 | URL·토큰·프로젝트·Kanban 뷰·상태 열 매핑 |
| 인증 | 토큰 환경변수 | 원격은 getpass와 파일 저장, 관리형은 계정·토큰 생성 | 사용자 프로필별 토큰 파일, 교체·삭제 지원 |
| API | v2 전용 | `/api/v1` 고정 | 새 플러그인 v2 전용, 구환경은 사전 진단·이관 |
| 저장소 연결 | `.agent-workflow/project.yaml` | `.handrail/project.json` + 사용자 registry의 보드 정보 | `.handrail` 유지, Git 공유 연결 정보와 로컬 프로필 매핑 분리 |
| 프로젝트·보드 | 1 repo ↔ 1 project, Development 뷰 | root/inbox/children 생성, Handrail 뷰·열 구성 | Handrail 프로젝트별 부모 보드 1개로 시작, 하위 area는 요청 시 확장 |
| 상태 | Brainstorm/Ready/Doing/Review/Done | To Do/In Progress/Review/Done | 의미 상태와 열 이름 분리, 기본 4개 상태 재사용 |
| 위임 | Cursor, 작업 디렉터리 고정, worktree 제외 | Codex/Cursor, 분리된 Git worktree, 모델 지정 | Codex→Codex 먼저, Codex→Cursor도 v0 수용 검증, Cursor 오케스트레이터 후속 |
| 명세 승인 | 계획·범위 중심 | 명세 해시와 승인 기록 | 기존 해시 승인 유지·검증 계획 고정 |
| 검증 | 실제 diff와 RESULT 비교 | diff fingerprint, 독립 검사, accept, 통합 | 현재 결과·필수 검사 목록·리뷰 기록을 함께 고정 |
| 동시성 | workspace당 1 write delegate | registry 잠금만 존재 | Git common directory 단위 실행 잠금 추가 |
| 원격 Git | 자동 PR/merge 제외 | provider 설정, origin 설정, Forgejo 설치 안내 | 원격 Git 전부 제품 범위에서 제외, Codex가 사용자 요청에 따라 처리 |
| 장애·기록 | 실패 상태·원시 로그 | 동기 실행, 요약 메타데이터, API 기록과 밀결합 | 로컬 결과 우선 보존, 원격 게시 상태 분리 |

기존 설계의 “worktree 제외”와 현재의 worktree 구현은 별개다. 동시 실행을 하나로 제한하면서 worktree를 활용할 수 있으므로, 이미 있는 안전한 변경 격리와 리뷰 경로를 제거할 이유가 적다.

## 2. 실제 코드에서 재사용할 것

| 근거 | 재사용 대상 | 필요한 변경 |
| --- | --- | --- |
| [core.py](../../handrail/core.py): `atomic`, `edit_registry` | 원자적 JSON 기록, 로컬 registry | 사용자 config 경로 분리, 스키마 버전, 실행 잠금 |
| [cli.py](../../handrail/cli.py): `kanban connect` | `getpass` 입력과 토큰 저장 | 통합 설정 흐름, 비TTY 차단, 토큰 교체 |
| [api.py](../../handrail/api.py): `Api` | HTTP 경계, 리다이렉트 거부, 오류 축약 | v2 verbs·페이지 envelope·오류·조건부 쓰기 |
| [board.py](https://github.com/freestylewhiz/handrail/blob/673c29a022e01dec1d4102f665aa0d0afdd1fd12/handrail/board.py): `resolve`, `move` | 카드 소속 검사, 상태 변경 readback | 선택한 project/view/bucket ID 기준으로 일반화 |
| [specs.py](../../handrail/specs.py) | 명세 생성, SHA256 승인 | 승인된 검증 목록과 복합 task identity |
| [workflow.py](https://github.com/freestylewhiz/handrail/blob/673c29a022e01dec1d4102f665aa0d0afdd1fd12/handrail/workflow.py): `fingerprint`, `verify`, `review`, `integrate` | untracked 포함 diff, 검증 fingerprint, 로컬 통합 | 필수 검사 충족, report 검증, 게시 실패 분리 |
| [workers.py](../../handrail/workers.py) | 두 provider 어댑터, timeout·프로세스 그룹 종료 | 환경 allowlist, capability probe, 지속 가능한 실행 상태 |
| [skills.py](https://github.com/freestylewhiz/handrail/blob/673c29a022e01dec1d4102f665aa0d0afdd1fd12/handrail/skills.py) | 관리 파일 소유권·사용자 수정 보존 원칙 | 별도 설치형 스킬의 플러그인 이관 |
| [tests/test_handrail.py](../../tests/test_handrail.py) | 명세 변경·오염된 통합·다른 프로젝트 접근 회귀 사례 | 새 config/API/패키징 계약에 맞게 조정 |

Python을 유지해도 파일을 한꺼번에 재배치할 필요는 없다. 먼저 서비스 경계를 추출한 뒤 해당 기능을 바꾸는 단계에서 모듈을 나눈다.

## 3. 현재 구현에서 보완해야 할 점

### 연결과 서비스 운영이 묶여 있다

`projects.init()`은 외부 Vikunja만 사용해도 `kanban_dir`를 필수로 받는다. `board.up()`은 컨테이너·계정·토큰을 만들고 `board.init()`은 프로젝트·하위 프로젝트·열을 구성한다. `ensure_view()`는 기존 열의 이름·순서를 바꾸거나 일부 기본 열을 삭제할 수 있다.

U1–U3를 반영하려면 원격 연결을 기본 경로로 승격하고 `bind_existing()`과 보드 생성 기능을 분리해야 한다. 신규 설정에서 칸반 데이터 폴더, 관리자 비밀번호, 공개 초기 비밀번호는 필요하지 않다.

### 대화형 토큰 입력은 이미 일부 있다

현재 `kanban connect`는 `getpass.getpass()`로 입력받고 `credentials.json`을 mode 0600으로 저장한다. 처음부터 새 비밀정보 저장기를 만드는 대신 이 경로를 초기 설정·갱신·삭제로 확장한다. 입력 프롬프트를 에이전트가 대신 조작하면 기록에 남을 수 있으므로 사용자가 직접 입력하는 터미널을 계약으로 정한다.

### registry 잠금은 실행 잠금이 아니다

`core.edit_registry()`의 파일 잠금은 registry 갱신 동안만 유지된다. `workflow.delegate()`에서 위임 전체를 보호하는 저장소 잠금은 확인되지 않는다. 두 Codex 세션이나 두 worktree에서 동시에 같은 baseline을 기준으로 작업을 시작할 수 있으므로 Git common directory 단위 잠금과 실행 소유자 기록이 필요하다.

### 검증 기준과 결과 파싱을 더 명확히 해야 한다

현재 worker 반환은 exit code 0과 비어 있지 않은 `result.md`로 판정한다. `review(accept)`는 현재 diff에 대응하는 성공 검사가 있는지 확인하지만, 승인 명세에 적힌 필수 검사가 모두 실행됐는지는 강제하지 않는다. structured result와 승인된 validation ID 목록을 추가하고, 테스트 없이 문서 검토만 필요한 작업은 명시적 manual check로 처리한다.

### 외부 장애가 로컬 상태를 가릴 수 있다

실행과 Vikunja 댓글·상태 변경이 같은 함수에 결합돼 있다. 프로세스가 성공해도 이후 API 호출 실패가 결과 반환을 막을 수 있다. 로컬 run 기록을 먼저 확정하고 `sync_state`를 별도로 관리한다. timeout으로 응답만 유실된 쓰기는 중복 생성 가능성이 있으므로 원격 확인 후 재시도한다.

### 문서와 작업 트리가 다르다

[docs/status.md](../../docs/status.md)는 doctor의 실패 종료 코드가 미비하다고 쓰지만 현재 미커밋 `cli.py`는 required check와 `exit_code` 집계를 이미 추가했다. 이를 “아직 없음”으로 재구현하지 말고, 현재 개선을 외부 연결 중심 진단에 맞춰 확장한다. 이번 설계 작업은 그 변경을 수정하거나 검증 완료로 간주하지 않는다.

### 원격 Git은 오케스트레이터에 맡긴다

현재 `projects.remote()`, `remote_guide()`와 CLI의 `--git-provider`, `--forgejo-base`, `project remote`는 Handrail의 핵심 작업 흐름에 필요하지 않다. 사용자 추가 결정 U5에 따라 새 제품 경로에서 제외한다. 저장소에 설정된 origin·credential helper·SSH 인증은 기존 개발 환경의 책임이며, “푸시해줘” 요청은 Codex가 일반 Git 도구로 수행한다. Handrail은 로컬 commit SHA·diff·통합 여부까지만 기록하고 원격 URL이나 push 여부를 추적하지 않는다.

## 4. 대안 판단

| 대안 | 장점 | 비용·제약 | 판단 |
| --- | --- | --- | --- |
| A. 현재 CLI 설치 흐름만 보완 | 변경량이 가장 작음 | 최종 배포물이 플러그인이라는 U4를 충족하지 못함 | 단독 최종안으로 제외 |
| B. 스킬 + 번들 Python 실행 도구 플러그인 | 현재 코어·테스트 재사용, 별도 서버·패키지 설치 불필요 | Codex의 로컬 shell 실행 가능 환경 필요 | **v0 권장** |
| C. Python 코어 + 로컬 MCP 플러그인 | 구조화된 도구 호출, 입출력 스키마 | MCP 런타임 의존성, 시작·취소·배포 검증 추가 | B 뒤에 같은 코어로 확장 |
| D. TypeScript/MCP 전면 재작성 | 기존 설계 디렉터리와 바로 일치 | 현재 승인·리뷰·Git·설정 코드를 다시 작성하고 회귀 검증 | 현재 요구만으로는 비용을 정당화하기 어려움 |

MCP의 가치가 커지는 조건은 shell을 쓸 수 없는 호스트 지원, 도구 발견·입출력 스키마의 표준화, 여러 클라이언트에 같은 도구 API를 제공해야 할 때다. 대상 호스트가 외부 기능을 MCP로만 호출할 수 있을 때는 필수다. 긴 실행·취소·복구는 CLI에서도 필요한 공통 코어 책임이다. [후속 평가](BACKLOG.md)에서 필요성이 확인되면 전송 계층을 추가하고, 토큰·보드 정책과 작업 상태는 재구현하지 않는다.

## 5. 의도적인 기존 설계 변경

- `.agent-workflow` 대신 `.handrail`과 기존 UUID를 유지한다. 경로·이력의 이중화를 줄인다.
- 스킬 4개를 필수로 만들지 않는다. 하나의 진입 스킬과 목적별 참고 문서로 시작한다.
- 환경변수 토큰만 허용하던 규칙을 사용자 전용 토큰 파일 기본값으로 바꾼다.
- 새 5열 보드를 강제하지 않는다. Ready는 명세 승인 조건으로 표현할 수 있다.
- API v2 선택은 유지한다. v1 경로를 문자열 치환하는 이관은 금지한다.
- worktree와 명시적 로컬 통합은 현재 코드의 장점으로 유지한다. 자동 병렬 실행·자동 merge는 범위에 넣지 않는다.
- 원격 저장소 생성·연결·인증·push·PR·Forgejo 설치 안내는 제거한다. 기존 `.git/config`의 remote를 변경하는 이관도 하지 않는다.

## 6. 확인이 남은 사항

- 새 산출물의 root manifest/호환 manifest가 실제 Codex에서 각각 한 번만 로딩되는지.
- 플러그인 캐시 안의 Python 코드 실행과 새 채팅에서의 스킬 발견.
- 대상 Vikunja 인스턴스의 v2·토큰 권한·수동 Kanban 뷰 기능. 현재 코드가 사용했다는 버전 번호만으로 지원을 보증하지 않는다.
- 설치된 Cursor 버전의 실제 옵션과 공급자 인증 전달 방식.
- 기존 여러 area를 가진 프로젝트의 이관 결과와 진행 중 run 보존.

이 항목들은 구현·릴리스 검증 조건이며 설계 문서 작성을 막는 질문은 아니다.
