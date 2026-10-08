# Handrail v0 — Master Specification

상태: 구현을 위한 검토 제안. 사용자 확정 요구는 [README의 U1–U7](README.md)를 따른다.

## 1. 제품 목적

Handrail은 Codex가 Vikunja의 요구사항을 읽고, 승인된 명세를 기준으로 작업을 위임하고, 실제 결과를 검증·리뷰하는 데 사용하는 Codex 플러그인이다. 사람의 대화 상대는 Codex다. Vikunja는 작업·논의·첨부·진행 상태를, 로컬 Git은 명세·코드·변경 이력을 관리한다.

첫 지원 환경은 로컬 프로세스와 Git 저장소에 접근할 수 있는 Linux의 Codex다. 현재 Python 최소 버전 계약인 3.9 이상을 출발점으로 유지하되 릴리스 검증한 Python/Codex 조합을 지원표에 기록한다. macOS·Windows·웹 전용 Codex 환경까지 동작한다고 주장하지 않는다.

## 2. 책임 경계

| 주체 | 책임 |
| --- | --- |
| 사용자 | Vikunja 준비, 토큰 발급, 보드 선택, 작업 범위 합의, 최종 완료 확인 |
| Codex 오케스트레이터 | 사용자 대화, 맥락 해석, 계획·위임 판단, 의미 검토, 필요한 일반 개발 도구 실행 |
| Handrail 스킬 | Handrail 기능 선택, 설정·명세·위임·검증 절차 안내, 실제 사용자 의사 기록 |
| Handrail Python 코어 | 설정·비밀정보·보드 소속 검증, HTTP, 로컬 실행, 잠금, 산출물·검증·상태 관리 |
| Vikunja | 프로젝트·뷰·카드·댓글·첨부의 원본 |
| Git | 로컬 소스·명세·커밋·worktree·diff |
| 위임 worker | 승인된 worktree에서 구현하고 로컬 결과 반환 |

원격 Git은 Handrail 책임에 포함하지 않는다. 사용자가 “푸시해줘”라고 요청하면 Codex가 개발 저장소의 기존 remote와 인증을 이용해 일반 Git 작업으로 처리한다. Handrail은 원격 provider, origin URL, 토큰, SSH 키, push/PR 상태를 설정·저장·검사하지 않는다. 원격 설정이 없어도 모든 Handrail 로컬 기능을 사용할 수 있다.

## 3. 목표 아키텍처

```text
사용자 ↔ Codex
            │ Handrail 스킬
            ▼
      플러그인 내부 실행 도구
            │
       공통 Python 서비스
        ├─ 사용자 설정 / TokenStore
        ├─ 저장소 연결 / 명세 승인
        ├─ Vikunja v2 adapter → 외부 Vikunja
        └─ 실행 / 검증 / 리뷰
              ├─ 로컬 Git / worktree
              └─ provider adapter → Cursor 또는 Codex worker
```

CLI와 나중에 추가할 MCP는 같은 서비스를 호출한다. API 정책·승인 조건·상태 전이는 스킬 문장이나 별도 전송 계층에 중복 구현하지 않는다.

## 4. 범위

v0 필수 기능:

- 설치 가능한 Codex 플러그인, 번들 스킬·Python 실행 도구.
- 대화형 첫 설정과 기존 연결 변경, 토큰 교체·로컬 삭제.
- 외부 Vikunja v2 연결, 기존 프로젝트·Kanban 뷰 선택과 상태 매핑.
- 카드·댓글·첨부 읽기, 필요한 첨부 다운로드, 작업 요약과 상태 반영.
- Git에 남는 명세와 내용 해시 승인, TASK/CONTEXT/RESULT 계약.
- 저장소당 한 개의 쓰기 실행, worktree에서 Codex/Cursor worker 실행과 모델 선택.
- 한 호스트에서 여러 Handrail 프로젝트 사용, 프로젝트별 부모 보드·실행 기록 구분.
- 독립 검증, 사용자 의도에 따른 리뷰·로컬 통합·완료 처리.
- 중단·외부 게시 실패를 구분하는 로컬 실행 기록과 복구 조회.

후속 범위:

- Cursor 오케스트레이터 지원과 Codex/Cursor CLI 공동 개발.
- MCP 도입 필요성 평가와 필요할 경우 로컬 전송 계층 구현, 다른 OS, 추가 worker provider.
- 여러 Git 저장소를 걸친 병렬 오케스트레이션과 강한 OS 격리.
- 요청에 따른 하위 프로젝트·보드 생성과 area 등록. 초기 설정에서는 하위 보드를 생성하지 않는다.
- 계층형 카드 workflow: 부모 프로젝트의 계획 카드, 등록된 하위 보드의 연결된 작업 카드, Review 제출 및 사람의 상태 변경 동기화. [PROJECT_WORKFLOW_AND_TERMS.md](PROJECT_WORKFLOW_AND_TERMS.md)에 목표 동작을 정의한다.

후속 항목의 상태·선행 조건·완료 기준은 [BACKLOG.md](BACKLOG.md)를 따른다.

제품 제외 범위:

- Vikunja 설치·업그레이드·컨테이너·계정·DB·백업 운영.
- 원격 Git 설정·인증·서버 안내·push·PR·원격 merge.
- 별도 채팅 UI, 자체 칸반, 자체 모델 서버, native subagent 추적.

기존 테스트용 컨테이너는 개발 fixture로 사용할 수 있다. 배포물과 사용자 설치 경로에는 포함하지 않는다.

## 5. 설치와 설정 완료의 의미

상태는 `installed → connection_ready → board_ready → repository_ready`로 구분한다.

- `installed`: Codex가 플러그인 스킬과 실행 도구를 사용할 수 있다.
- `connection_ready`: URL·토큰·지원 API의 읽기 접근을 확인했다.
- `board_ready`: 실제 프로젝트·Kanban 뷰·열 매핑을 저장했다.
- `repository_ready`: 현재 로컬 Git 저장소와 보드 연결을 확인했다.

설치는 저장소 밖에서 할 수 있다. 이때 URL·토큰은 연결 프로필에 저장하고, 선택한 부모 보드는 이름을 부여한 프로젝트의 설정 초안에 보관한 뒤 해당 저장소를 연결할 때 확정한다. 호스트 공통 기본 보드로 저장하지 않는다. Vikunja가 없는 사용자는 공식 설치 안내를 보고 설정을 중단·재개할 수 있다.

Codex 플러그인 설치 시 임의의 비밀 입력 폼이나 post-install hook이 반드시 실행된다고 가정하지 않는다. 첫 Handrail 요청이 미설정 상태를 감지해 설정을 이어가는 것을 기준 UX로 삼는다. 상세 계약은 [설정 문서](SETUP_AND_CONFIGURATION.md)에 있다.

## 6. 저장소와 보드 연결

각 Handrail 프로젝트는 로컬 Git repository 한 개와 자신의 부모 Vikunja project 한 개를 연결하고, 그 project의 manual Kanban view 한 개로 시작한다. 하위 보드가 없을 때 모든 작업은 이 부모 보드에서 관리한다.

한 호스트에는 이런 Handrail 프로젝트가 여러 개 존재할 수 있다. A 저장소는 A 부모 보드, B 저장소는 B 부모 보드를 갖는다. 부모라는 말은 각 Handrail 프로젝트의 기준점을 뜻하며, 호스트 전체를 묶는 공통 보드를 뜻하지 않는다. Vikunja 연결 프로필은 재사용할 수 있지만 binding·명세·run·worktree는 workspace별로 관리한다. 자세한 구조는 [PROJECT_HIERARCHY.md](PROJECT_HIERARCHY.md)를 따른다.

- 영구 식별: `instance_id + project_id + task_id`.
- 뷰·열 식별: 선택한 project의 `view_id`와 그 view의 `bucket_id`.
- 표시: 사용자 친화적인 이름·Vikunja identifier. 이름만으로 대상을 확정하지 않는다.
- 프로젝트가 허용 목록 밖인 task를 읽거나 변경하는 작업을 거부한다.
- 원격 토큰의 권한이 넓어도 Handrail은 연결된 프로젝트로 접근을 제한한다.
- 임의 URL을 task 입력으로 받아 다른 호스트에 토큰을 전달하지 않는다.

선택 순서는 명시적 repository 인자 → 현재 Git root의 연결 정보다. 저장소 밖에서는 명시적으로 대상을 고른다. 전역 마지막 선택만으로 다른 저장소에 쓰기를 실행하지 않는다. `enter/leave`를 유지할 경우 탐색 편의 상태이며 실행 대상의 유일한 근거로 쓰지 않는다.

Git worktree에서는 canonical Git common directory와 workspace ID로 원래 Handrail 프로젝트를 찾는다. worktree 경로를 새로운 프로젝트로 자동 등록하지 않는다. Cursor의 `--workspace`는 CLI 작업 디렉터리이며 Handrail workspace ID와 구분한다. 명시적 대상과 현재 checkout이 충돌하면 대상·경로를 먼저 확정한다.

신규 연결은 부모 binding 하나만 만들며 inbox나 컴포넌트 보드를 자동 생성하지 않는다. 부모 보드는 프로필 전역 기본값으로 저장하거나 다른 신규 프로젝트에 자동 재사용하지 않는다.

기존 root/inbox/children은 이관 때 `areas`로 보존한다. 추가 area는 같은 instance에 속하고 해당 부모 아래의 하위 프로젝트임을 확인하며 project/view/열을 각각 기록한다. 기존 데이터가 이 조건과 다르면 이관 충돌로 보고하고 자동 이동하지 않는다. 향후 명시적 추가 요청에서만 새 하위 프로젝트·보드를 생성할 수 있다. 상위 보드가 하위 task를 자동 집계한다고 가정하지 않고 등록된 areas를 대상으로 목록·요약을 집계한다.

이 계층은 저장소당 부모 binding 하나를 유지한다. 목표 workflow에서는 부모 프로젝트의 계획 카드와 등록된 하위 보드의 작업 카드를 구분하며, 보드 소속만으로 작업 관계를 추정하지 않는다. 실제 하위 task 관계, 상태 전이, 개정 이력, 외부 상태 변경 동기화는 [PROJECT_WORKFLOW_AND_TERMS.md](PROJECT_WORKFLOW_AND_TERMS.md)에 정의한다. 이는 현재 구현 기능이 아니라 승인된 후속 설계 범위다.

## 7. 작업 상태와 사용자 승인

핵심 상태는 `todo`, `doing`, `review`, `done`이다. 화면 열 이름과 분리한다.

| 의미 상태 | 기존 열 예시 | 전환 조건 |
| --- | --- | --- |
| todo | To Do / Ready / 대기 | 계획 또는 작업이 실행 대기 |
| doing | In Progress / Doing / 작업 중 | 계획 조율 또는 승인된 작업 실행·수정 진행 |
| review | Review / 검토 | 전체 하위 작업과 최종 통합 검증을 마친 계획 카드가 사용자 검토 대기 |
| done | Done / 완료 | 작업 카드는 조율자의 검수·통합·검증 완료, 계획 카드는 사용자의 명시적 최종 완료 의사 |

명세 승인 여부는 별도 기록이다. `todo` 열에 있다는 사실만으로 구현을 승인하지 않는다. Brainstorm·Blocked가 있는 기존 보드는 그대로 두고 필요하면 부가 매핑/라벨로 표현한다.

구현 CLI의 종료는 작업 카드 완료가 아니다. 조율자는 결과를 검수하고 필요한 변경을 통합한 뒤, 최종 통합 결과의 검증까지 통과했을 때 작업 카드를 Done으로 처리한다. 계획 카드는 필수 작업 전체가 끝나고 최종 통합 검증이 최신 상태에서 통과한 경우에만 Review로 제출한다. 사용자가 결과를 확인하기 전에는 계획 카드를 Done으로 바꾸지 않는다. Review 이후 개선은 기존 완료 작업 카드를 다시 열지 않고 새 작업 카드를 하위 task로 추가한다.

기존 `done_bucket_id`, 필터·자동 bucket 모드와 상태 매핑이 충돌하면 설정 오류로 보여준다. 기본 연결 동작으로 뷰 설정을 고치지 않는다. done bucket으로 이동할 때 실제 `task.done` 의미가 맞는지도 검증한다.

카드 작성, 명세 합의, 위임, 로컬 통합, 최종 완료는 각각의 행위다. 이미 받은 사용자의 범위·권한은 유지하고 같은 승인을 반복해서 요구하지 않는다. Handrail의 approval 필드는 오케스트레이터가 확인한 의사 기록이며, 사용자 본인 인증이나 위변조 방지 서명으로 표현하지 않는다.

## 8. 명세와 검증 계약

Git에 저장하는 명세에는 목표·범위·제약·완료 조건과 검증 계획이 있어야 한다. 승인은 명세의 SHA256과 함께 보관한다. 승인 이후 내용이 바뀌면 그 내용에 대한 승인으로 재사용할 수 없다.

검증 계획은 각 항목에 안정적인 `check_id`, `kind`(`command` 또는 `manual`), 통과 조건을 갖는다. command는 argv 배열과 작업 위치를 명시한다. manual은 검토한 파일·근거·판정을 기록한다. 문서만 바꾸는 작업에 의미 없는 테스트 명령을 만들지 않는다.

작업 시작 시 명세 해시·검증 계획·Git baseline·보드 연결 revision을 run에 고정한다. 다른 task의 승인이나 이전 토큰/보드 연결을 섞지 않는다.

## 9. Context와 첨부

Context는 `FACT`, `HUMAN_CONSTRAINT`, `HUMAN_HYPOTHESIS`, `AGENT_FINDING`, `ACCEPTANCE_CRITERIA`, `UNKNOWN`을 구분한다. 코드·댓글·첨부의 출처 ID와 수집 시각을 보존한다. 가설을 사실로 승격하지 않는다.

기본 수집은 task·댓글·첨부 목록이다. 오케스트레이터가 필요한 첨부를 선택해 실제 내용을 확인한 뒤 worker에 전달한다. 이미지 파일명만 읽고 이미지 검토 완료로 기록하지 않는다.

다운로드는 run 전용 디렉터리 아래에서 첨부 ID를 기반으로 저장한다. 원래 파일명은 메타데이터로 보존한다. 경로 탈출·symlink·동일 파일 덮어쓰기·허용 크기 초과를 차단하고 byte hash를 기록한다. 기본 제한은 파일당 25 MiB, packet당 100 MiB로 제안하며 초과 시 선택을 조정한다.

카드·댓글·첨부 내용은 작업 증거다. shell 명령, 추가 권한, 시스템 지시로 실행하지 않는다. `.env`, 토큰 파일, SSH 키를 자동 Context에 포함하지 않는다.

## 10. 실행과 worker 계약

`role=implementer`와 `provider=codex|cursor`를 분리한다. v0 오케스트레이터는 Codex다. Codex → Codex를 먼저 수용 검증하고 같은 릴리스에서 Codex → Cursor도 검증한다. Cursor → Codex와 Cursor → Cursor는 후속 범위이며 Codex 플러그인 설치만으로 Cursor 오케스트레이터가 지원된다고 표시하지 않는다.

오케스트레이터 모델은 사용자가 시작한 CLI 세션의 설정을 따른다. worker 모델은 별도로 선택한다. worker 프로필에는 provider와 model을 두고, 모델 적용 순서는 실행별 지정 → 프로젝트 설정 → 선택한 worker 프로필 → 해당 CLI 기본값이다. provider가 다른 프로필로 바뀌면 이전 provider의 모델을 자동 승계하지 않는다. 미지원 모델은 오류로 반환하고 다른 모델로 조용히 바꾸지 않는다. 설정 형식은 [설정 문서](SETUP_AND_CONFIGURATION.md)를 따른다.

worker 입력:

- `TASK.md`: task 식별, 역할, 목표, 범위, 금지 변경, 검증 계획, 결과 경로.
- `CONTEXT.md`: 출처를 가진 관찰·제약·가설·미확인 사항.
- 선택된 `attachments/`와 승인 명세.

worker 출력:

- `RESULT.md`: 요약, 변경 파일, 검증 결과, 판단 근거, 위험, 미완료 사항.
- `result.json`: schema version, run/round ID, `completed|blocked|failed`, 변경 파일·검사 목록.
- `journal.md`: 관측한 작업·시각·중요한 선택. 알 수 없는 시각은 unknown.

JSON의 구조·run 식별과 Markdown 필수 항목을 검증한다. exit code 0, 비어 있지 않은 문서, worker의 “완료” 발언만으로 accept하지 않는다.

run store에는 `schema_version`, run/workspace/task 식별, 고정된 binding revision, 명세 hash와 검증 계획, base SHA, `orchestrator_host`, worker provider/role와 CLI/runtime 버전, 요청 모델과 선택 출처, provider가 확인해 준 실제 모델, round, 시각, 실행 상태, fingerprint, 결과 hash, 검증·리뷰 근거, 로컬 통합 commit, Vikunja 게시 상태를 기록한다. 실제 모델·commit·종료 시각을 확인하지 못하면 null로 둔다. CLI 기본값을 구체적인 모델명으로 추측하지 않는다. 실제 토큰은 저장하지 않는다.

실행은 argv 배열, 명시적 cwd, timeout, 프로세스 그룹 종료를 사용한다. provider 옵션은 해당 어댑터에 한정하고 설치된 버전의 help로 capability를 확인한다. 실행 파일·인증이 없으면 안내하며 자동 설치·로그인이나 유료 모델 호출 진단을 하지 않는다.

worker 환경은 필요한 실행 환경과 승인된 provider 인증만 전달하는 allowlist로 구성한다. Vikunja 토큰·Handrail 관리 설정 경로는 전달하지 않는다. 같은 OS 사용자와 HOME을 사용하는 모델은 파일 권한 0600만으로 관리자 비밀에서 격리되지 않는다. sandbox 접근 범위를 검증하고 강한 격리를 보장한다고 표현하지 않는다.

호스트별 실행 권한은 역할에 따라 확인한다. 오케스트레이터의 관리 호출에는 대상 Vikunja 연결, 사용자 config/run/lock 경로, 소스와 worktree 접근이 필요하다. worker에는 승인 worktree의 쓰기와 필요한 provider 인증만 전달하며 manager 권한을 그대로 복사하지 않는다. CLI sandbox가 실제로 적용하는 경계는 수용 검증에서 확인한다. `--trust`는 workspace 신뢰 옵션이며 명세 승인이나 최종 완료 확인을 대신하지 않는다. 비대화형 세션은 사용자 TTY 설정 뒤 재개한다.

## 11. 로컬 실행 상태와 동시성

run의 로컬 상태:

```text
prepared → running → returned → verified → accepted → integrated
                  └→ blocked / failed / cancelled / interrupted
returned / verified → needs_revision → 다음 round
```

`returned`는 결과를 수집했다는 뜻이고 `verified`는 필수 검증을 마쳤다는 뜻이다. 최종 수용은 오케스트레이터의 의미 검토를 요구한다. 명령 진입점에서 허용된 전이를 검사한다.

저장소 잠금 키는 canonical Git common directory로 만든다. 같은 repo의 별칭·여러 worktree가 잠금을 우회하지 못해야 한다. 한 쓰기 run이 prepared부터 integrated 또는 명시적 abandon까지 점유한다. 수정 대기·검증 대기에도 점유를 유지한다. 읽기·다른 repo의 작업은 가능하다.

짧은 OS 파일 잠금은 상태 갱신을 직렬화하고, durable active-run 레코드는 명령 프로세스가 끝난 뒤에도 점유를 보존한다. PID, 시작 시각, run ID, 실행 소유자를 함께 기록한다. PID가 없다는 이유만으로 잠금을 삭제하지 않고 산출물·통합 상태를 확인해 recover/abandon으로 해제한다.

Codex와 후속 Cursor 호스트는 같은 잠금 경로·schema를 사용한다. run에는 runtime 버전과 build revision을 고정하고 호환되지 않는 설치본은 갱신·재개를 거부한다. 저장소의 `.handrail` ID와 registry의 common directory 관계가 충돌해도 전역 선택으로 대체하지 않는다. 새 잠금을 모르는 구 CLI와의 동시 운영은 지원하지 않으며 이관 때 활성 실행을 정리한 뒤 전환한다.

길게 실행되는 worker는 `run start`가 run ID를 반환하고 `run inspect`, `run cancel`로 조회·취소할 수 있는 감독 프로세스 방식으로 전환한다. 기존 동기 `delegate`는 같은 서비스의 wait 옵션으로 호환할 수 있다. 취소와 비정상 종료 후에도 결과·로그·worktree를 보존한다.

## 12. 검증·리뷰·통합

검증은 tracked·untracked 소스 변경을 모두 포함하는 fingerprint를 사용하고 runtime 산출물을 제외한다. 사용자 실제 Git index를 바꾸지 않는 현재 임시 index 방식을 재사용한다.

accept 조건:

1. worker 실행이 정상 종료했고 result 계약이 유효하며 `result.status=completed`다.
2. 승인된 모든 `check_id`가 현재 fingerprint에서 통과했다.
3. 검사 도중 내용이 바뀌지 않았다.
4. 명세 해시·run/round·reviewed result 해시가 일치한다.
5. 범위·제약·완료 조건을 오케스트레이터가 검토하고 근거를 남겼다.

수정은 같은 worktree의 새 round로 남기고 이전 결과를 보존한다. 기본 최대 수정 횟수 2회를 유지하되 초과 시 자동 반복하지 않는다.

로컬 통합은 accepted fingerprint와 원본 checkout의 깨끗한 동일 baseline을 요구한다. 기존 commit-tree/cherry-pick 접근을 재사용한다. 작업 트리가 바뀌었으면 자동 stash/reset/rebase하지 않고 충돌 정보를 반환한다. 통합 뒤 명세가 요구한 검증을 수행하고 계획 카드를 Review에 둔다.

계층형 workflow에서는 각 작업 카드를 검수·통합·검증 증거와 함께 완료 처리한다. 모든 필수 작업을 통합한 뒤 계획 카드의 전체 완료 조건을 최종 상태에서 다시 검증하고, 통과했을 때 계획 카드만 Review로 제출한다. Review 제출 회차에는 계획 개정, 하위 작업 집합, 최종 통합 fingerprint와 검증 결과를 고정한다. Review 이후 수정 요청은 새 작업 카드로 처리해 이전 완료 작업과 제출 기록을 보존한다.

`candidate_commit`, `integrated_commit`, `integration_verified`는 로컬 사실이다. 원격 커밋 링크나 push 상태로 확장하지 않는다. 사용자가 최종 완료를 확인하면 기록된 권한 안에서 Done을 반영한다.

## 13. Vikunja adapter와 게시 실패

새 플러그인은 API v2 계약으로 구현한다. 실제 대상 인스턴스의 OpenAPI와 검증된 fixture를 기준으로 routes·요청·응답을 고정한다. URL 접두사만 바꿔 현재 v1 adapter를 재사용하지 않는다.

run의 로컬 상태와 외부 반영 상태 `in_sync|pending|conflict|unknown`을 분리한다. 실행 결과를 저장한 뒤 댓글·상태를 반영하고 readback 결과를 기록한다.

각 게시 작업에는 `operation_id`, 대상 instance/project/task, run/round, payload hash, 단계·결과를 기록한다. Handrail 댓글에 operation ID를 포함해 재조회할 수 있게 한다. timeout/네트워크 단절로 응답을 못 받은 쓰기는 `unknown`이며 재전송 전에 원격 상태를 확인한다. 서버 전체의 exactly-once 보장은 주장하지 않는다.

외부 상태 변경은 최신 값을 읽고 충돌을 확인한다. API가 지원하는 조건부 요청을 사용하고 충돌을 사용자 변경 위로 덮어쓰지 않는다. 실패 시 로컬 검증·리뷰 기록은 유지하며 “로컬 리뷰 완료, 보드 반영 대기”처럼 구분해 보고한다.

사람이 Vikunja에서 상태를 직접 강제 전환한 경우는 자동으로 원복하지 않는다. Handrail은 원격 상태를 다시 읽어 외부 변경 충돌로 표시하고, 조율자는 원격 변경을 채택해 로컬 관리 기록을 갱신할지, 사용자가 확인한 뒤 Handrail workflow 상태를 다시 적용할지 안내한다. 과거 `in_sync` operation은 현재 원격 상태의 증거로 취급하지 않는다.

새 실행은 task 읽기·doing 전환을 확인한 뒤 worker를 시작한다. 이미 실행 중인 worker는 Vikunja 장애만으로 강제 종료하지 않고 로컬 결과를 보존한다. 게시 대기를 이유로 worker를 다시 실행하지 않는다.

## 14. 명령·오류 경계

아래는 신규 목표 인터페이스이며 현재 구현된 명령 목록이 아니다. 플러그인 내부 launcher와 개발용 `handrail` CLI가 같은 dispatch를 사용한다.

| 용도 | 대표 명령 |
| --- | --- |
| 초기 설정·진단 | `setup`, `status`, `doctor` |
| 토큰 관리 | `connection list`, `connection rotate`, `connection forget` |
| 저장소 연결 | `project bind`, `project list`, `project status` |
| 카드·맥락 | `task list`, `task context`, `task comment`, `task move` |
| 명세 | `spec create`, `spec approve` |
| 실행 | `run start`, `run inspect`, `run cancel`, `run recover`, `run abandon` |
| 검증·리뷰 | `run verify`, `run revise`, `run review`, `run integrate` |
| 게시·요약 | `run sync`, `summarize` |

일반 호출은 JSON 결과와 안정적인 오류 code를 제공한다. 예: `SETUP_REQUIRED`, `AUTH_FAILED`, `PERMISSION_DENIED`, `API_UNSUPPORTED`, `BOARD_MAPPING_INVALID`, `PROJECT_MISMATCH`, `RUN_BUSY`, `APPROVAL_STALE`, `VALIDATION_INCOMPLETE`, `VIKUNJA_UPDATE_UNKNOWN`.

정상 종료 0, 실행 오류 1, 설정 필요 2를 기준으로 CLI와 문서를 통일한다. `doctor`는 모델을 호출하지 않으며 Docker나 원격 Git을 필수 검사로 삼지 않는다.

## 15. 수용 기준

- [ ] Codex 플러그인을 설치한 새 대화에서 스킬과 번들 실행 도구가 동작한다.
- [ ] 별도 Handrail pip 설치 없이 번들 코드가 실행되고 캐시 위치가 바뀌어도 동작한다.
- [ ] Vikunja가 없어도 플러그인은 설치되며 설치 안내·설정 재개 경로를 제공한다.
- [ ] API 토큰은 사용자 직접 숨김 입력으로 받아 전용 파일에 저장하며 출력·packet에 나타나지 않는다.
- [ ] 기존 프로젝트·뷰·열을 선택해 연결하고 준비 과정에서 원격 쓰기를 하지 않는다.
- [ ] 같은 호스트의 A/B 저장소가 각각 부모 보드 하나로 시작하며 보드·기록·선택이 섞이지 않는다.
- [ ] Codex → Codex와 Codex → Cursor에서 모델 지정·결과 반환·검증·리뷰·로컬 통합을 확인한다.
- [ ] 기존 remote가 있거나 없어도 동일한 로컬 작업 흐름이 가능하다.
- [ ] 승인 해시·필수 검증·현재 fingerprint가 맞아야 accept/통합할 수 있다.
- [ ] 같은 Git 저장소에 두 쓰기 실행이 생기지 않는다.
- [ ] 취소·timeout·result 누락·외부 장애 후 결과와 복구 판단 근거가 남는다.
- [ ] 계획 카드는 사용자 최종 의사 없이 Done으로 변경하지 않는다. 작업 카드는 조율자가 검수·통합·검증한 뒤 완료 처리한다.
- [ ] 구형 관리형 인스턴스·데이터·기존 remote를 이관이 삭제하거나 수정하지 않는다.

세부 시나리오와 단계별 완료 조건은 [MIGRATION_PLAN.md](MIGRATION_PLAN.md)를 따른다.
