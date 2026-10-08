# DEV-11 — 저장소 최초 승인과 조율자 자동 후속 실행 설계

작성일: 2026-10-08. 상태: **설계 작성 / 구현·호스트 적용·수용 검증 대기**. 추적 항목: [체크리스트 DEV-11](../checklist-v1-host-test.md#9-신규-개발--dev-11).

사용자가 같은 저장소의 Handrail 운영 범위를 처음에 승인하면, 이후 작업 의뢰마다 조율자가 작업자 실행부터 변경 검토·병합·테스트·수정·사용자 Review 보고까지 이어간다. 새 Plan이나 회차라는 이유만으로 운영 권한을 다시 묻지 않는다. 최종 결과의 사용자 수락은 유지한다.

이 문서의 명령·문서 kind·상태는 개발 계약 제안이다. 현재 CLI에 추가됐거나 자동 실행이 활성화됐다는 뜻이 아니다. 이번 요청은 체크리스트와 설계 문서에 반영하며 테스트 프로젝트·보드·룸·호스트 정책을 변경하지 않는다.

## 1. 현재 근거와 설계 결정

| 현재 구현 | 공백 | 결정 |
| --- | --- | --- |
| [setup/access.py](../../handrail/setup/access.py)의 저장소별 명령 규칙 | read/monitor 등의 그룹에 작업 생성·최초 실행·통합·검증 전체가 없음 | 동작별 의미가 고정된 workflow 규칙 묶음과 등록 테스트 실행 경로 추가 |
| [authorization/service.py](../../handrail/authorization/service.py)의 Plan/cycle별 exact grant | 새 기획·회차에 지속 운영 동의를 적용할 근거 없음 | 저장소 정책을 별도로 저장하고 작업 의뢰에 묶인 exact grant를 파생 |
| [providers.py](../../handrail/agentroom/providers.py), [handoff.py](../../handrail/agentroom/handoff.py)의 경로 요청·probe | 요청 권한과 실효 권한이 다르고 양쪽 역할의 준비가 분리됨 | 최초 설정에서 조율자·작업자 준비 상태를 함께 표시; 매 Attempt probe는 자동 수행 |
| `HandoffService.tick/next_actions` | 다음 행동을 반환하고 활성 조율자가 수행해야 함 | 실행 가능한 durable action과 조율자 모델의 검토 응답을 연결 |
| `Application.advance_plan` | 기존 증거로 Review를 제출할 뿐 테스트를 실행하지 않음 | 테스트 실행 결과와 기준별 판단이 쌓인 뒤 기존 도메인 관문 호출 |
| [agentroom/service.py](../../handrail/agentroom/service.py)의 `integrate`, [workflow/service.py](../../handrail/workflow/service.py)의 완료 조건 | 미완료 통합이 다른 통합을 막고 병합된 Work는 수정 불가 | 병합 후 실패를 같은 통합 배치의 수정 Work로 처리; 검증 revision을 별도 기록 |
| 현재 monitor의 `host_wakeup=unavailable` | 턴 종료 후 조율자를 깨우는 구현 없음 | 지원 확인된 호스트 재개 어댑터와 foreground 실행을 구분 |

범위는 [아키텍처](../architecture.md)의 컴포넌트를 확장한다. Herdr/Vikunja 서버나 UI를 변경하지 않는다. 과거 런타임, 조율자의 별도 직접 구현 경로, 전체 outbox 개편을 복원하지 않는다.

## 2. 사용자가 겪는 절차

1. **최초 준비:** 연결된 저장소·보드·Herdr, 통합 브랜치, 작업자 저장 경로, 조율자/작업자 제공자, 테스트 명령, 수정 한도, 대화 종료 후 재개 가능 여부를 하나의 계획으로 제시한다. 저장된 유효한 선택과 승인은 채운다. 빠진 선택만 받는다.
2. **운영 정책 동의:** 표시한 범위의 지속 사용 동의를 한 번 기록하고 지원되는 호스트 설정을 적용한다. 이미 이 범위를 승인했다면 근거를 재사용한다. 설정 파일 저장을 곧바로 실효 권한으로 표시하지 않는다.
3. **작업 의뢰:** 사용자의 목표·범위·기준을 Plan의 구현 의도로 기록하고 정책에서 필요한 권한만 파생한다. 사용자가 의뢰한 일을 시작하기 위해 같은 운영 범위를 다시 확인하지 않는다.
4. **자동 후속 처리:** 작업자 완료 → 조율자 검토 → 병합 전 테스트 → 통합 → 통합 테스트 → 기준별 증거 → Work 완료 → Plan Review → 보드·사용자 보고를 수행한다. 수정은 같은 의뢰 범위와 한도 안에서 반복한다.
5. **예외·최종 수락:** 범위 확대나 해결되지 않는 차단만 사용자에게 전달한다. Plan Review 이후 Done은 사용자의 실제 수락으로 결정한다.

“1회”는 저장소 운영 범위에 대한 한 번의 동의다. 서로 다른 호스트 권한 UI를 Handrail이 하나의 클릭으로 합칠 수 있다고 약속하지 않는다. 최초 준비의 실제 클릭 수를 별도 기록하고, **준비 완료 후 동일 범위의 추가 운영 질문·호스트 승인 0회**를 검증한다. 작업 의뢰와 최종 수락은 이 지표에 포함하지 않는다.

## 3. 저장소 정책과 권한 경계

정책은 소스 트리 밖의 기존 비공개 Handrail 저장소에 둔다. 보드 Instruction·Summary·작업자 제출은 정책을 만들거나 확대할 수 없다. 같은 OS 계정의 악성 프로세스까지 격리하는 새 보안 경계라고 주장하지 않는다.

| 기록 | 주요 필드 | 소유 컴포넌트 |
| --- | --- | --- |
| `project_policy` | id/version/schema, repo realpath·Git common dir, board binding fingerprint, Herdr endpoint, worktree_root, integration checkout·ref, 허용 동작·역할, provider/model 선택 정책, check profile 참조, 한도, approval source, revoked/expiry | authorization |
| `host_access_plan` | policy hash, 역할·provider·surface·version, launcher·operation manifest hash, 명령 규칙·경로·endpoint, 기존/추가/철회 차이, 적용 및 관측 근거 | setup |
| `task_intent` | 사용자 의뢰 근거·범위·기준 hash, Plan/cycle, 정책 id/version, 선택 모델 근거 | workflow |
| 기존 `grant` 확장 | 현재 exact resource scope + source policy id/version·intent id, revoked/expiry | authorization |
| `check_profile` | version, check id, 단계, argv, cwd role, timeout, env 이름/비밀 참조, network 범위, 결과 판정 방식, 기준 매핑, 실행 정의 fingerprint | setup/authorization |

동작 범위는 보드 조회·투영, 소유 룸 생성·통신, 작업자 실행, 소유 worktree 생성, 검토, 지정 ref 통합, 등록 검사 실행, 결과 기록이다. room 종료·worktree 삭제·push·PR·배포는 별도 권한이며 기본 운영 정책에서 제외한다. 보드 임의 생성이나 카드 강제 이동도 개발 동작에 섞지 않는다.

### 정책 적용과 파생 grant

- 기존 exact grant 검사를 유지한다. 새 정책은 `task_intent`가 있는 현재 Plan/cycle에 대해서만 구체적인 자원값을 해석해 grant를 파생한다. 정책만 존재하는 상태에서는 새 개발 작업을 시작하지 않는다.
- 다음 cycle도 명시적인 수정 의뢰 또는 원래 의뢰의 승인된 수정 루프라는 근거가 있어야 한다. 새로운 목표를 과거 승인에서 만들어내지 않는다.
- repo는 realpath만 아니라 Git common directory와 관리 바인딩을 확인한다. worktree는 승인된 루트 아래 Handrail 소유 Attempt로 생성하고 symlink·다른 Git 저장소·다른 Attempt 경로를 거부한다.
- 동적 worktree의 정확한 경로가 달라져도 이 생성 규칙 안이면 새 정책 동의를 요구하지 않는다. worker에는 해당 worktree·실제 Git 경로·보고 채널만 전달하며 다른 작업자 경로와 관리자 DB·토큰을 쓰기 루트에 넣지 않는다.
- 모델은 이번 명시적 선택 → 해당 Work의 유효 선택 → 확인된 조율자 모델 순서를 유지한다. 지속 정책은 이 선택 규칙 및 허용 제공자 범위를 승인하며 모델을 추정하거나 임의 교체하지 않는다.
- 모든 부작용 직전에 원본 정책과 파생 grant의 유효성을 재확인한다. 철회·만료·범위 축소는 파생 grant에도 적용한다. 이미 시작한 작업은 상태를 수집하고 새 부작용을 멈추며 실행 중 명령의 즉시 중단 여부는 별도 정책에 따른다.
- 정책 갱신은 새 버전으로 저장하고 추가 범위만 승인한다. 이전 버전의 기록을 바꾸지 않는다. 같은 허용 범위의 갱신·재시작은 기존 동의를 재사용한다.
- 호스트 규칙 철회는 Handrail 소유 추가분만 제거한다. 기존 세션이 이전 규칙을 유지할 수 있으므로 호스트 반영은 별도 표시하며 Handrail 도메인은 즉시 실행을 차단한다.

## 4. 최초 권한 준비와 테스트 등록

기존 `access plan/apply/revoke`를 확장한다. 조율자용 규칙은 고정 절대 런처 + `--repo` + 명시한 하위 명령 접두어로 생성하고 RTK 형식을 함께 다룬다. `handrail` 전체, 임의 `command`, Python·shell 전체, `permissions grant`, 정책 설치 명령 자체를 자동 허용 묶음에 넣지 않는다.

새 `workflow` 그룹에는 Plan/Work 작성·상태 조회·검토·증거·보고, 작업자 준비·시작·수집·통합 및 **등록된 check id 실행**에 필요한 명령만 열거한다. 사용자 수락·자원 삭제 명령은 제외한다. 새로운 명령의 뒤쪽 인수로 임의 실행 파일·정책 파일·다른 저장소를 전달할 수 없도록 런타임에서도 검사한다. 의미가 확대된 릴리스는 operation manifest 차이로 기존 허용 범위를 다시 판단한다.

| 역할 | 최초 준비 | 이후 자동 확인 |
| --- | --- | --- |
| 조율자 | 보드/Herdr 연결, 관리자 상태, 지정 checkout·Git 저장 영역, 정책에 등록된 실행 명령 | 실제 적용 규칙·버전·경로를 기록하고 동일 거부를 반복하지 않음 |
| 작업자 | 제공자별 sandbox 설정과 소유 경로 생성 규칙 | 각 Attempt의 normal sandbox probe 및 실제 작업 결과 |
| 지속 실행 담당 | 읽기·알림·재개에 필요한 범위와 등록된 조율자 시작 설정 | 실제 수신 확인·session identity·lease·heartbeat |

준비 상태는 `planned → consented → configured → verified`로 구분하고 `unsupported/unknown/blocked`를 별도 표시한다. CLI 설정을 IDE에 적용했다고 보지 않는다. 최초 동의가 있어도 관리 정책의 거부를 우회하지 않는다. 새 세션 필요 여부와 검증하지 못한 경계는 사용자가 작업을 맡기기 전에 표시한다.

테스트 실행은 다음 계약을 사용한다.

- 조율자가 저장소의 테스트 설정을 읽어 check 후보를 만들고 최초 운영 계획에 포함한다. 사용자가 내부 JSON을 직접 작성할 필요는 없다. 누락된 검사 정의는 준비 단계에서 확정한다.
- `check run PLAN --check ID --target ATTEMPT|integration`은 비공개 등록 정의로 argv·cwd·env·timeout을 해석한다. 자유 argv·cwd·shell 문자열 옵션을 받지 않는다. 실제 값으로 exact `command.run` grant와 기존 명령 intent/log를 만든다.
- 등록 명령도 저장소 코드를 실행한다. 런처의 호스트 allow 규칙이나 `shell=False`가 자식 프로세스의 파일·네트워크 권한까지 제한한다고 보지 않는다. 검사는 승인한 경계를 집행하는 호스트 실행 컨텍스트에서 수행하도록 실행 어댑터를 두고, 현재 `commands.py`의 무조건적인 상속 subprocess 실행을 그대로 무승인 경로에 연결하지 않는다. 제공자가 이 경계를 지원하지 않으면 최초 준비에서 해당 check를 `unsupported`로 표시한다.
- 동일 argv라도 스크립트·패키지 설정·훅·env·네트워크 사용이 바뀔 수 있다. 조율자는 실행 전에 관련 변경을 검토하고 정의 fingerprint와 검토한 revision을 기록한다. 승인된 구현 범위 안의 테스트 수정은 자동 검토로 계속하고, 새로운 외부 접속·비밀·권한 확대는 정책 차이로 처리한다.
- 설치가 필요한 경우 `prepare` 검사를 별도로 등록한다. 테스트 명령의 허용이 임의 패키지 설치나 새 서버 접속 권한이 되지 않는다. 비밀값은 로그나 작업 지시에 기록하지 않는다.
- 명령 종료 코드 0, timeout 없음, 같은 revision, 요구한 clean 상태를 확인한다. 종료 코드만으로 의미적 수용 기준을 통과시키지 않는다. 기준별 필수 check와 조율자의 관찰을 함께 기록한다. 검사 누락·skip·실행 불가는 통과가 아니다.
- 재실행은 재시도 번호를 가진 새 실행으로 남긴다. 같은 action 재전달은 기존 결과를 반환하며, unknown 실행은 종료·부작용을 확인하기 전 다시 시작하지 않는다.

## 5. 조율자의 후속 실행 계약

기존 Plan/Work의 Todo·Doing·Review·Done은 유지한다. 아래 phase는 `continuation`의 내부 진행이며 보드 열을 추가하지 않는다. 코드 의미 검토는 조율자 모델이 담당하고, CLI가 작업자 완료 주장이나 exit code만 보고 검토를 승인하지 않는다.

| phase | 실행/판단 | 다음 단계와 기록 |
| --- | --- | --- |
| `waiting_submission` | 채널 제출 수집·현재 Attempt·commit 검증 | inbox → `reviewing` |
| `reviewing` | 조율자가 실제 diff·지침·의뢰 범위 검토 | 구조화된 verdict·이유·candidate SHA·참조 버전; 수정 또는 `source_checks` |
| `source_checks` | 후보 revision에서 등록 검사 | 성공 시 근거를 반영한 최종 Work 검토 기록 후 `integrating`, 실패 시 `repairing` |
| `integrating` | 검토된 SHA·통합 ref·expected HEAD·clean 상태 재확인 | 기존 Git 어댑터로 통합, intent 및 integration 기록 |
| `integration_checks` | 통합 revision에서 필수 검사·기준 검증 | 성공 시 Work 완료, 실패 시 통합 배치의 `repairing` |
| `repairing` | 실패 근거와 동일 범위의 수정 지시 | 새 제출부터 검토·검사 재시작; 횟수/시간 소진 시 `blocked` |
| `plan_verification` | 모든 Work와 최종 canonical HEAD 검증 | Plan 기준별 증거 → 기존 submit Review 관문 |
| `reporting` | 보드 투영·Summary 준비·사용자 보고 | 각각 전달 근거 기록 → `awaiting_user_acceptance` |
| `blocked` / `paused` | 범위·충돌·권한·불확실성 또는 사용자 중지 | 이유·owner·필요 조치·재개 지점 보존 |

리뷰는 candidate SHA·기준 hash·Instruction 참조·check profile 버전에 묶는다. 후보 SHA가 바뀌면 다시 검토한다. 이전 통합으로 base HEAD가 바뀌면 병합 가능성과 관련 diff/검사를 다시 판단한다. worker가 계속 편집하는 상태는 안정된 제출로 취급하지 않는다.

`reviewing`의 모델 판단은 먼저 받은 검토 응답으로 보존하고, source evidence를 기록한 뒤 그 응답과 검사 근거로 최종 `work review`를 확정한다. 현재 도메인이 source evidence 변경 시 기존 review를 무효화하는 규칙을 유지하며, 검토 후 증거를 추가한 상태로 곧바로 통합하지 않는다.

최초 설정 제안값은 Work당 수정 2회, 검사당 timeout 10분, Plan/cycle 자동 실행 누적 2시간이다. 사용자가 다른 한도를 정하면 이를 사용하고 최초 정책에 보여준다. wall-clock 만료 시각도 별도로 기록할 수 있다. 재시작·새 Attempt가 카운터를 초기화하지 않는다. 한도 변경은 조율자가 임의로 늘리지 않는다.

### 병합 후 실패와 수정

현재는 미완료 통합이 다음 통합을 차단하고 Work의 통합 revision을 변경할 수 없다. 단순히 새 수정 Work를 만드는 것만으로는 복구되지 않는다. 이 관문을 다음과 같이 명시적으로 확장한다.

1. 첫 통합에서 `integration_batch`를 열고 저장소 canonical checkout/ref를 점유한다. `base_revision`, 순서가 있는 `integration_ids`, 원래 Work와 관련 수정 Work, 현재 HEAD, 실패 검사, 원래 기준, 정책 버전을 기록한다.
2. 병합 후 검사 실패 시 원래 Work는 미완료로 보존한다. 실패에서 직접 파생된 `repair_of` Work만 같은 배치에 추가한다. 무관한 Work/Plan 통합은 계속 차단한다. 수정 작업자는 현재 배치 HEAD에서 시작한다.
3. 수정 Work도 별도 제출·검토·병합 전 검사를 거친다. canonical HEAD가 배치의 expected HEAD와 일치할 때만 병합한다. 원래 integration record나 실패 기록은 변경하지 않는다.
4. 최종 HEAD에서 원래 Work와 모든 수정 Work의 필수 기준을 다시 검증한다. 후보 커밋들이 이 HEAD의 조상임을 확인한다. 통과하면 배치의 `validation_revision`과 evidence를 확정하고 관련 Work를 도메인 transaction에서 완료한다.
5. Work에는 최초 `integration.revision`과 별도로 `completion.validation_revision`, `integration_batch_id`를 둔다. `_completion_valid`, `_plan_basis`, 증거 등록·전체 검증도 이 계약을 검사하도록 함께 변경한다. 기존 v1 Work는 자기 integration revision을 validation revision으로 해석해 읽는다.

최종 Plan 검증 실패는 원래 의뢰 안의 새 수정 Work로 처리하고 최종 HEAD에서 Plan 검사를 재실행한다. 이미 Done인 Work의 과거 증거를 새 결과로 덮어쓰지 않는다.

Git 충돌, dirty canonical checkout, 외부 HEAD 변경, 결과 불명 통합은 자동 reset/강제 병합 없이 `blocked`로 남긴다. v1의 자동 수정 대상은 검토 지적과 재현 가능한 테스트 실패다. 충돌 자동 해결은 이번 범위에 넣지 않으며 판단 근거와 재개 담당을 보고한다.

## 6. 활성 턴 실행과 종료 후 재개

한 번의 `tick`이 모델 판단까지 수행하는 것처럼 만들지 않는다. `continuation`은 실행할 action과 필요한 근거를 제공하고 활성 조율자가 검토 응답을 제출한다. 기계적으로 처리할 단계는 기존 application/agentroom 경로로 실행한다. 스킬은 작업자 시작이나 다음 행동 목록만 보고 턴을 끝내지 않고 Review 보고 또는 명시적 차단까지 이어가도록 갱신한다.

| 실행 모드 | 동작 | 완료 판단 |
| --- | --- | --- |
| foreground | 활성 조율자가 action을 처리하고 반환된 주기에 tick | 턴 내 전체 흐름 확인; 턴 종료 뒤 감시를 약속하지 않음 |
| durable | 명시적으로 준비한 지속 실행 담당이 채널/상태를 확인하고 호스트 어댑터로 조율자 세션을 재개 | 턴 종료 뒤 실제 모델 실행·수신·후속 처리·보고를 확인 |

지속 실행 담당은 Handrail `agentroom`의 제한된 monitor이며 Git 권한 broker나 별도 개발 실행 엔진이 아니다. policy가 허용한 연결·채널만 관측하고 모델 판단이 필요한 때 조율자를 깨운다. 기존 Herdr 및 제공자가 지원하는 프로토콜을 `interfaces/agentroom`에서 사용한다. 임의 stdin 키 주입이나 새 raw provider subprocess 경로로 우회하지 않는다.

재개 어댑터 계약은 `probe / ensure_monitor / request_resume / observe_resume / stop_monitor`로 정의한다. 실제 제공자별 메서드·지원 버전은 D11-04 초기 조사와 실행 검증으로 확정한다. 현재 Codex/Cursor/Herdr에 이 계약이 이미 구현됐다고 가정하지 않는다. 필요한 기능이 없으면 `unsupported`이며 해당 환경의 durable 완료 기준은 미충족이다. 기존 서비스 수정이 필요하다면 별도 범위 결정 대상으로 남긴다.

재개에는 등록된 조율자의 실제 session identity·provider·model/effort와 정책을 사용한다. 원 세션 재개가 불가능한 경우 새 조율 세션 생성이 최초 정책에 포함되어 있고 지원되는 Herdr 경로가 확인됐을 때만 그 경로로 복구한다. 새 세션은 durable inbox·의뢰·정책·검토 근거를 읽으며 모델을 임의 변경하지 않는다.

깨우기 성공 응답은 실행 성공이 아니다. 요청·수신·모델 실행·action 처리·결과 보고를 각각 기록한다. 알림 유실은 주기 확인으로 복구하고, 호스트 종료 중에는 진행하지 못했음을 표시한 뒤 재연결 시 미처리 action부터 재개한다.

사용자 보고도 호스트가 지원하는 전달 경로와 실제 수신 근거가 필요하다. 보드 Review나 내부 `coordinator report` 기록만으로 채팅 전달을 완료 처리하지 않는다. 전달 어댑터가 없으면 `report_pending`과 재개 담당을 남기고 durable 전체 완료로 표시하지 않는다.

## 7. 영속성·경합·복구

기존 SQLite documents/events/outbox를 사용하며 외부 I/O는 transaction 밖에서 수행한다. 새 문서 kind는 다음과 같다.

| 기록 | 필수 식별·상태 |
| --- | --- |
| `continuation` | Plan/cycle, policy version, phase, Work/Attempt/submission, candidate/base SHA, action id, lease owner/epoch/expiry, retry·시간 집계, blocker |
| `continuation_action` | action type, 입력 hash, expected 상태/revision, policy/intent 참조, prepared/running/succeeded/failed/unknown, operation id, 실행 근거 |
| `integration_batch` | repo/ref, owner, Work 및 repair 관계, 통합 순서, expected HEAD, validation revision, 상태·근거 |
| `resume_delivery` | 목적 조율자 신원, continuation/action, 중복 제거 key, 요청·ack·처리 시각, 결과 |

- 이벤트는 최소 한 번 전달을 가정한다. action key는 Plan/cycle + Work/Attempt + submission/candidate + 단계 + check version + retry 번호로 구성한다. 같은 입력의 재전달은 같은 intent를 사용한다.
- lease를 transaction에서 획득하고 epoch를 증가시킨다. 모든 결과 제출은 epoch와 expected 상태를 비교한다. 오래된 조율자의 응답은 현재 실행을 진행시키지 못한다.
- lease 만료만으로 실행 중 외부 명령을 다시 시작하지 않는다. 현재 PID/실행 신원·intent를 확인하고 종료 여부가 불명확하면 `unknown`으로 남긴다. 테스트의 exactly-once 실행을 약속하지 않는다.
- canonical repo/ref별 잠금과 expected HEAD를 함께 사용한다. 호스트 내 여러 Handrail 저장소/프로세스에서도 Git common dir를 기준으로 같은 잠금을 찾도록 shared 잠금 위치를 고정한다. 같은 Git 저장소를 여러 호스트에서 쓰는 분산 통합은 지원 범위에서 제외하고 진단한다.
- 기존 `agentroom-mutation` 잠금은 실행 보호에 재사용하되 monitor lease 갱신·중지 기록이 긴 테스트에 막히지 않도록 분리한다. 검사 subprocess는 영속 operation으로 추적하고 heartbeat는 별도 짧은 transaction에서 기록한다.
- 잠금 순서는 repo integration → agentroom mutation → 짧은 DB transaction으로 고정한다. 모델 응답 대기 동안 파일 잠금이나 DB transaction을 유지하지 않는다.
- 통합 의도 후 프로세스가 끊기면 ancestry·expected HEAD·실제 clean 상태로 기존 복구 절차를 수행한다. 불확실한 결과를 미실행으로 바꾸거나 새 operation id로 중복 병합하지 않는다.
- 사용자 중지는 새 action의 시작을 중단한다. 진행 중 테스트의 종료와 작업자 중단은 정책과 프로세스 신원을 확인해 수행하고 데이터·worktree는 보존한다. 재개 시 정책·HEAD·실제 실행 상태를 다시 확인한다.

## 8. 제안 CLI와 컴포넌트 변경

아래 명령은 아직 제공되지 않는 제안이다. `ABSOLUTE_LAUNCHER --repo ABSOLUTE_REPO`와 저장소가 요구하는 RTK 접두어는 유지한다.

| 명령 | 계약 |
| --- | --- |
| `policy plan` | 연결·역할·명령·검사·한도·재개 설정의 검토 가능한 차이 출력 |
| `policy apply --proposal ID --approval SOURCE` | 승인한 proposal hash에만 지속 동의 기록; 호스트 적용은 해당 host access proposal과 연결 |
| `policy status / policy revoke ID --reason TEXT` | 실효 준비·유효 범위 조회 및 철회 이력 |
| `check list / check run PLAN --check ID --target TARGET` | 등록 검사 조회·고정 정의 실행 |
| `coordinator run PLAN / coordinator resume PLAN` | 유효한 task intent로 후속 action 수행·복구; 모델 검토가 필요하면 구조화된 요청 반환 |
| `coordinator pause PLAN --reason TEXT` | 소유권·실행 상태를 보존한 중지 |

일반 사용자는 명령을 직접 입력할 필요가 없다. 조율자가 최초 설정과 의뢰를 이 계약으로 기록한다. 지속 정책의 설정·변경 자체는 지속 정책에서 자동 승인하지 않는다.

| 위치 | 변경 책임 |
| --- | --- |
| `setup/access.py`, 신규 policy/check 설정 모듈 | 좁은 operation manifest·규칙, 제안 diff, check profile, 양쪽 역할 준비·지원 판정 |
| `authorization/service.py`, 신규 정책 서비스 | 지속 동의, exact scope 파생, 모든 실행 시 원본 정책 철회·만료 검사 |
| `workflow/service.py`, `validation.py` | task intent, 검토 응답 검증, integration batch·validation revision·완료 근거 |
| `agentroom/handoff.py`, 신규 continuation/monitor 모듈 | durable action, 수정 루프, lease·heartbeat·재개·보고 추적 |
| `agentroom/commands.py`, `service.py` | 등록 검사 해석·실행, 같은 배치 수정 통합, 기존 보호 관문 유지 |
| `interfaces/agentroom`, `interfaces/git`, 신규 검사 실행 어댑터 | 지원 확인된 호스트 재개·제한된 검사 실행 프로토콜, expected ref/HEAD와 통합·복구 |
| `application.py`, `cli.py` | 도메인 조립·출력, 도메인 관문을 우회하지 않는 명령 연결 |
| 공통 스킬·execution/workflow/authorization 문서 | 최초 동의 재사용, 실제 후속 실행, 실패·재개·지원 한계 안내 |

## 9. 개발·검증 순서

RC03의 [개발 책임자 최종 점검](../reviews/handrail-rc-03-2026-10-08.md)을 선행 신뢰성 근거로 적용한다. 자동 진행을 연결하기 전에 동일 실행의 신원 보강과 실제 교체를 구분하고, 실제 보고 경로 적용·계약 전달·worker probe가 확인된 뒤 active 계약을 전환한다. 전환 중 기존 제출은 발견·보존하되 오래된 nonce로 현재 계약을 통과시키지 않는다. 준비 실패가 진단 결과를 잃거나 과거 readiness를 현재 상태로 표시해서도 안 된다.

이 사례의 개선 범위는 현재 계약과 스킬의 보완으로 제한한다. 제공자 제어 명령의 불확실 전달은 기존 관측·resolve 경로를 사용하고, 범용 Cursor/Herdr 제어기나 피드백 예약 큐는 추가하지 않는다. Work 완료 후 Plan 증거 미등록은 정확히 진단하되 후속 차단의 exit code를 일괄 성공으로 바꾸지 않는다. Summary 본문·번역의 정합성은 조율자가 수락 후 확인하며 CLI가 자유 서술을 자동 의미 수정하지 않는다. 대상 앱의 API·저장소 구현 문제는 Handrail 기능으로 일반화하지 않는다.

1. **D11-01:** 정책 schema·범위 비교·철회 전파와 task intent/파생 grant부터 구현한다. 동시에 D11-04의 실제 호스트 재개·보고 가능성을 조사해 지원표를 고정한다.
2. **D11-02:** operation manifest와 check profile을 구현하고 최초 설정에서 양쪽 역할의 실효 권한을 확인한다. 전체 shell 허용 없이 모든 예정 workflow 동작의 커버리지를 확인한다.
3. **D11-03:** foreground continuation을 연결한다. 실제 모델 검토와 기존 완료 관문을 유지하면서 통합 배치·테스트 실패 수정 경로를 구현한다.
4. **D11-04:** 검증된 호스트 어댑터에 monitor·wake·lease·중복 방지를 연결한다. 턴 종료·프로세스 재시작 후 복구까지 확인한다. 미지원 환경을 foreground 성공으로 대체하지 않는다.
5. **D11-05:** 스킬·설치·배포를 맞추고 아래 수용 시나리오를 확인한다. DEV-01~10을 다시 열거나 과거 미실행 테스트를 통과 처리하지 않는다.

| 검증 묶음 | 필수 시나리오 | 체크리스트 대응 |
| --- | --- | --- |
| 정책·호스트 | 최초 동의, Plan 2개·새 cycle·새 세션·동적 worktree, 범위 변경·만료·철회, RTK/버전·관리 정책·IDE 차이 | A01~04, A11 |
| 정상 실행 | 제출부터 실제 diff 검토·후보 검사·통합·통합 검사·기준별 증거·Review 실제 보고까지 사용자 운영 개입 없음 | A05, A10 |
| 수정 실행 | 검토 거절, 병합 전 실패, 병합 후 실패와 같은 배치 수정, 최종 Plan 검사 실패, 재시작 후 한도 유지 | A06~07 |
| 복구·경합 | 중복 신호, lease 만료 중 명령 실행, 늦은 모델 응답, 병합 직후 crash, 검사 종료 직전 crash, 사용자 중지·재개 | A07~09 |
| 호환 | 이전 grant/진행 중 Plan/미확정 intent/완료 이력, 보드 override, 정책 미설정 시 현재 수동 흐름 | A12 |

도메인·어댑터 검증은 임시 저장소와 제어된 가짜 외부 서비스로 수행하고, 그 결과만으로 실제 호스트 승인을 증명하지 않는다. 실제 Codex/Cursor 네 조합은 사용자가 허용한 테스트 환경에서 별도 확인한다. 요청/클릭/자동 허용/거부/대기와 의도 확인/최종 수락을 분리해 측정한다.

최종 개발 완료 기준은 DEV-11의 A01~12, 체크리스트에 등록한 RC03 보완 R01~09와 지원표의 실제 근거다. R01~03은 하나의 복구 계약 묶음, R04~06은 진단·현재 상태, R07은 독립 URL 표시 수정, R08~09는 보고 도구·Summary 스킬 보완이다. 특히 foreground 완료, 지속 정책 저장, 재개 요청 전송만으로 **대화 종료 후 자동 병합·테스트·보고 완료**를 주장하지 않는다.

## 10. 호환성과 남은 확인 사항

기존 grant는 독립적인 명시 승인으로 유지한다. 진행 중 Plan은 정책 미설정 상태로 보존하며 사용자의 해당 작업 의도와 정책 범위를 확인한 후에만 자동화에 편입한다. 기존 v1 검증 기록은 변환해 덮어쓰지 않고 읽기 호환으로 처리한다. 기존 호스트 allow 규칙은 재사용하되 Handrail 소유가 아닌 규칙은 철회 시 삭제하지 않는다.

설계로 확정한 것은 운영 동의의 저장소 범위, 실제 task intent 필요, 등록 검사, 조율자 모델 검토, 통합 배치 수정, 최종 사용자 수락 유지다. 구현 전에 실측할 것은 제공자/호스트별 지속 규칙 적용, 보호된 Git 경로, 조율자 재개와 사용자 보고 프로토콜이다. 이 항목들은 기능 개발의 필수 검증 과제이며 현재 지원으로 간주하지 않는다.
