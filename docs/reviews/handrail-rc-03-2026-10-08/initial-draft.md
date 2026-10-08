# handrail_rc_03 세션 분석 — 작업자 신원·복구·완료 인계

상태: **초안 / 대상 조율자 의견 수렴 및 대조 중**. 아래 결론은 확정하지 않았으며, 대상 세션과의 독립 회고 및 초안 검토 대화 후 갱신한다.

분석일: 2026-10-08. 대상 버전: `1.0.0-alpha.6+codex.20261008041952` / CLI `1.0.0a6`.

**주요 결론:** 이 세션의 첫 중단은 Handrail의 작업자 신원 오탐과 불완전한 복구 전환에서 발생했다. Cursor 주 프로세스가 유지되는데 보조 프로세스 종료로 `IDENTITY_STALE`가 났고, `recover`가 기존 실행의 권한을 갱신하지 않은 채 새 보고 채널을 활성화했다. 기존 채널에 실제 완료 제출도 남았지만 현재 Work에는 수신되지 않았다. 프론트엔드는 사용자 재지시 없이 검토·병합·Work Done까지 진행했으므로, 이 사례 전체를 단순한 조율자 후속 실행 누락으로 설명하면 부정확하다.

## 1. 분석 범위와 시점

- 최초 의뢰부터 **14:50:07 KST의 중단 보고**까지를 원인 분석 대상으로 고정했다. 후속 요청 **14:50:51**, 진행 기록 **14:52:19 KST**까지는 별도 관찰했다. 대상 세션은 분석 중에도 진행 중이었다.
- 조율자: Codex `01a119f1-2380-71e0-9ffe-06ec8932d694`, `gpt-6-astra/high`, 세션 메타데이터 `source=vscode`, CLI 버전 `0.161.0`.
- 프론트엔드: Codex `01a119f9-d035-7e92-8f1b-fcb9b3b954e2`, `gpt-6-astra/low`.
- 백엔드: Cursor `96c33cb9-9a24-4edc-b528-c36bf25f0c31`, `grok-4.7-high-fast`, Herdr `w4Z:p3`.
- 저장소: `/project_workspace/handrail_poc/handrail_rc_03`. 상태 DB: `/home/dyhwang23/.local/share/handrail/v1/projects/b5b251bfb0bd864df14427f9/state.sqlite3`.
- 세션 로그, Cursor transcript, 보고 채널 파일, SQLite `mode=ro` 조회와 Handrail 소스를 사용했다. 실제 보드·Herdr를 재조회하지 않았고 프로젝트 코드·서비스·작업자·권한·상태를 수정하지 않았다.
- Handrail의 순수 신원 비교 함수에 저장된 전후 관측값을 입력해 오류를 재현했다. URL 렌더러도 순수 함수 입력으로 확인했다. 대상 서비스 테스트나 장애 복구는 수행하지 않았다.

주요 원본:

- [조율자 세션](/home/dyhwang23/.codex/sessions/2026/10/08/rollout-2026-10-08T14-16-36-01a119f1-2380-71e0-9ffe-06ec8932d694.jsonl)
- [프론트엔드 세션](/home/dyhwang23/.codex/sessions/2026/10/08/rollout-2026-10-08T14-26-04-01a119f9-d035-7e92-8f1b-fcb9b3b954e2.jsonl)
- [백엔드 transcript](/home/dyhwang23/.cursor/projects/project-workspace-handrail-poc-handrail-worktrees-b5b251bfb0bd864df14427f9-de750a059ada-11e2497e969349da/agent-transcripts/96c33cb9-9a24-4edc-b528-c36bf25f0c31/96c33cb9-9a24-4edc-b528-c36bf25f0c31.jsonl)
- [기존 채널 완료 제출](/project_workspace/handrail_poc/.handrail-worktrees/b5b251bfb0bd864df14427f9/de750a059ada/.channel-11e2497e969349da/submission.json)
- [당시 조율자가 남긴 차단 기록](/tmp/rc03/handrail-recovery-blocker.json): 조율자의 관찰 기록이며 본 분석의 독립 확인과 구분한다.

## 2. 진행 기록

아래 시각은 KST이며 로그의 UTC에 9시간을 더했다. 보드 상태는 로컬 기록과 전송 이력 기준이다.

| 시각 | 확인 사실 | 의미 |
| --- | --- | --- |
| 14:18 | 사용자 선택으로 부모 보드 35 연결 | 최초 보드 선택을 임의 추정하지 않음 |
| 14:20 | 지침 카드 45 생성 | Bun·최소 디자인/의존성·JSON 저장 요구 |
| 14:22:41 | 사원정보 서비스 및 두 제공자 작업 의뢰 | 이 의뢰를 구현·통합의 승인 근거로 재사용 |
| 14:26:18 / 14:26:37 | frontend/backend의 최초 probe ready | 원래 보고 채널 쓰기는 Shell 실행 문맥에서 확인됨 |
| 14:31:46 | backend `IDENTITY_STALE` | 주 프로세스 외 보조 프로세스가 비교 집합에서 사라짐 |
| 14:32:39 | backend `worker recover` 완료 | 같은 pane·세션을 새 Attempt로 바꾸고 새 보고 채널 생성 |
| 14:32:57 / 14:33:05 | frontend 제출 / 조율자 수신 | 인계 약 8.2초, 완료 수집은 정상 동작 |
| 14:33:20 / 14:33:34 | frontend 검토 / 통합 | 후보 `574682ed…` → 통합 `d209dc03…` |
| 14:34:45 | frontend Work Done | 소스·빌드 근거로 처리; 실제 backend 연동 검증은 Plan에 남김 |
| 14:35:30 / 14:40:42 | 새 backend Attempt `WORKER_WRITE_NOT_READY` | 복구된 계약이 작업자에게 아직 전환되지 않았음 |
| 14:45:35 | Cursor가 기존 채널 `report.json`의 Write 승인 대기 | sandbox probe 성공과 제공자 Write 도구 승인이 다름 |
| 14:47:35 | 기존 backend 채널에 실제 `submission.json` 저장 | 후보 `6dc1e772…`, 현재 Work에는 수신 기록 없음 |
| 14:47:48 | 조율자가 새 계약 준비 지시 전송 | 복구 기록 생성 후 약 15분 9초 경과 |
| 14:48:09 | 새 채널 probe의 `LOCAL_ACCESS_FAILED`, errno 13 관측 | 보고 채널에 `.report-*`를 쓸 수 없음 |
| 14:49:21 | tick 실패, `readiness: null`, backoff 300초 | 구체적인 worker 차단 정보가 구조화된 readiness에 전달되지 않음 |
| 14:50:07 | 조율자가 Handrail 결함으로 중단 보고 | 전체 Plan은 Review에 도달하지 않음 |
| 14:50:51 이후 | 사용자 후속 요청으로 원 세션이 복구 재개 | 최초 중단 원인과 분리; 아래 관측 시점에서 최종 성공 미확인 |

14:52:19 KST DB 관측: Plan `plan-ddf1e9975118436d87e5f65f84c5b982` Doing, frontend Work Done, backend Work Doing/새 Attempt, backend 제출·검토·통합 기록 없음. Plan/Work 카드 매핑은 각각 46/47/48이다. 최초 중단 당시 보드 outbox 15건은 모두 complete였다. 이후 보드의 실시간 상태를 단정하지 않는다.

## 3. 수정 항목

P1은 실행·완료 인계를 막는 결함, P2는 반복 개입·진단·준비 흐름의 결함, P3는 표시 결함이다. 아래 번호는 이번 분석의 식별자이며 기존 DEV 항목의 완료 상태를 변경하지 않는다.

### RC03-01 / P1 — 보조 프로세스 종료를 작업자 교체로 오판

- **근거:** 기존 process identity의 PID는 `[1839511, 1839966]`, 오류 후 관측은 `[1839511]`이다. 주 프로세스의 PID·start ticks `768949552`·실행 파일·argv hash·cwd가 동일하고 provider session·pane·terminal도 동일하다. 저장된 전후 값으로 `reconcile_identity`를 호출하면 실제 `IDENTITY_STALE`가 재현된다.
- **원인:** [process.py](../../../handrail/agentroom/process.py:32)는 Cursor 설치 경로를 가진 node 실행을 공급자 프로세스로 포함하고, 70행에서 전체 process identity의 동등성을 요구한다. 보조 프로세스의 생성·종료가 주 실행 교체와 같은 오류가 된다.
- **영향:** 정상 구현 중인 작업을 복구 대상으로 전환해 채널·권한·보고 흐름까지 흔든다. 실제로 정상 세션을 새 Attempt로 바꿨다.
- **수정:** 주 에이전트 실행을 launch receipt·프로세스 계보·provider session·boot/start identity로 식별하고 보조 프로세스 관측을 분리한다. 일부 PID가 겹친다는 이유만으로 무조건 연속성을 인정하지 않는다. 확정할 수 없는 경우 `unproven`으로 남기되, 확인된 동일 실행의 관측 보강과 실제 교체를 다른 경로로 처리한다.
- **수용 기준:** helper 생성/종료는 기존 Attempt 유지; 주 프로세스 재시작·PID 재사용·provider session 교체는 차단; 이번 저장 전후 값은 동일 실행으로 판별.

### RC03-02 / P1 — 복구 계획의 경로를 실제 실행 권한으로 적용하지 않음

- **근거:** 원래 Cursor 실행은 `.channel-11e2497e969349da`만 `--add-dir`에 포함했다. 복구된 Attempt는 `.channel-4500521ae8d2f64a`를 새 launch argv에 기록하지만 동일 PID `1839511`을 사용한다. 14:48의 worker probe는 새 채널의 `.report-ujmvsg0b`에서 errno 13으로 실패했다.
- **원인:** [service.py](../../../handrail/agentroom/service.py:635)의 `recover`는 `prepare()`로 새 채널/launch 설정을 만들지만 실제 프로세스 재실행이나 실행 중 경로 갱신을 수행하지 않는다. **새 launch 계획 저장과 실행 적용이 분리되지 않았다.**
- **영향:** 복구 명령이 성공해도 작업자는 새 결과 경로에 쓸 수 없어 계속 진행하지 못한다.
- **수정:** 동일 실행 신원 보강은 채널을 유지한다. 실제 교체는 대상 제공자가 지원하는 정확한 경로 추가 또는 승인된 재실행으로 권한을 적용하고 worker probe로 확인한 뒤 활성화한다. `requested_launch`와 `applied_launch`를 분리하고 미적용 경로를 실효 권한처럼 기록하지 않는다. 필요한 경우 처음부터 해당 Attempt 전용 보고 루트 안에서 계약 세대를 교체한다.
- **수용 기준:** 같은 실행 복구에서 권한 확대 없이 제출 가능; 실제 교체는 새 채널 적용과 probe 성공을 확인; 적용 실패 시 기존 유효 기록을 먼저 폐기하지 않음.

### RC03-03 / P1 — 복구 계약 전환 전 기존 제출 경로를 폐기

- **근거:** 14:32:39에 old Attempt가 replaced로 바뀌었으나 새 계약은 14:47:48에 전달됐다. 그 사이 작업자는 기존 지시로 구현을 마쳤다. 기존 채널에 `submission:4f72bd9c…`가 14:47:35 실제 저장돼 있고 backend transcript 27행도 같은 제출 ID와 커밋을 보고한다. DB에는 frontend 제출 한 건만 있다.
- **원인:** `recover`는 새 계약의 전달·수신·readiness보다 먼저 Work의 active Attempt를 전환한다. [tick](../../../handrail/agentroom/handoff.py:189)은 active Attempt만 훑으며, [collect_submission](../../../handrail/agentroom/handoff.py:116)은 직접 이전 Attempt를 읽어도 stale로 분류한다. 기존 제출의 보관·연결 및 계약 전환 상태가 없다.
- **영향:** 작업자는 제출 성공을 보지만 조율자는 제출 없음으로 기다린다. 수행한 코드를 잃지는 않았으나 정식 검토로 이어지는 인계가 끊겼다.
- **수정:** `recovery_prepared → contract_delivered → worker_ack/probe → active`의 단계적 전환을 둔다. 동일 실행이면 기존 계약 유지가 우선이다. 기존 제출을 발견하면 원문을 보존하고 lineage·SHA·의뢰·검토 근거를 확인해 재제출 또는 명시적 조정 경로로 연결한다. 이전 nonce를 현재 계약으로 무조건 인정하지 않는다. 장시간 구현 중인 작업자에게 계약 변경을 알리지 않고 기다리는 흐름을 스킬에서도 금지한다.
- **수용 기준:** 전환 전/중/후 제출이 모두 누락 없이 기록되며 중복 통합은 없음; 계약 미전달 상태를 즉시 표시; 오래된 유효 제출의 발견/조정 가능.

### RC03-04 / P2 — probe 성공 후에도 결과 작성 도구에서 다시 승인 대기

- **근거:** 기존 채널은 14:26:37 Shell probe에서 write=true였다. 하지만 같은 경로의 `report.json`을 Cursor `Write` 도구로 작성할 때 14:45 승인 선택 화면이 발생했다. worker transcript 24행의 도구는 `Write`다. 이후 Shell 작성과 submit 기록이 있으므로 이를 단순한 OS 경로 쓰기 불가로 설명할 수 없다.
- **원인:** 준비 검사는 Shell의 파일 접근만 관찰한다. 완료 지시는 별도 편집/Write 도구를 사용하게 될 수 있으나 이 도구 권한까지 준비하지 않는다.
- **수정:** 보고 작성·제출에 사용할 실제 도구 경로를 최초 준비에 포함한다. 예를 들어 스키마를 검증하는 제한된 `worker submit` 입력 경로로 작성과 전송을 묶거나, 필요한 Write 정책을 명시적으로 준비한다. 거부된 Write를 임의 도구로 우회하는 절차로 만들지 않는다.
- **수용 기준:** Codex/Cursor 각각 probe뿐 아니라 실제 보고 작성→submit까지 승인 재요청 없이 수행; 역할·도구별 준비 관측을 구분.

### RC03-05 / P2 — 보고 채널이 막히면 probe의 진단 결과까지 사라짐

- **근거:** worker가 새 채널 접근 거부를 보고했지만 조율자 tick은 `readiness: null`과 일반적인 `WORKER_WRITE_NOT_READY`만 반환했다. 새 채널에는 contract만 있었고 readiness 파일은 없었다.
- **원인:** [worker_io.py](../../../handrail/agentroom/worker_io.py:43)는 경로별 probe 결과를 계산한 뒤, 거부될 수 있는 바로 그 채널에 `write_atomic(readiness.json)`을 호출한다. 이 마지막 쓰기가 실패하면 계산한 blocked 결과 대신 상위 `LOCAL_ACCESS_FAILED`만 남는다.
- **수정:** readiness 계산 결과와 채널 전달 실패를 별개로 출력·기록한다. 채널을 못 쓰면 stdout의 구조화된 실패 결과를 전달할 수 있어야 한다. 조율자는 이 결과를 worker 관측으로 보관하고 실제 probe 없이 ready를 만들지 않는다.
- **수용 기준:** 새 채널 쓰기 거부에도 어떤 경로가 통과/실패했는지와 보고 실패 경로를 보존; 대기 중인 미실행 probe와 실제 실패를 구분; probe를 승격 실행하지 않음.

### RC03-06 / P2 — 복구 상태와 사용자 안내가 모순됨

- **근거:** 복구된 Attempt는 `execution_phase=readiness`, 새 채널에는 readiness 없음인데, 문서 안에는 old Attempt의 `readiness.status=ready`가 그대로 복사돼 있다. provider activity는 `done`이다. 현재 [status](../../../handrail/application.py:155)는 idle/done을 보고 “collects and reviews”를 안내하며, tick은 “Continue readiness or monitor worker”라는 일반 지시를 반환한다.
- **원인:** `dict(old, ...)` 복사 시 실행별 readiness를 제거하지 않는다. status는 phase·현재 계약·구체적인 blocker보다 provider activity에 의존한다. tick의 실패는 재시도 불가 상태도 backoff로만 다룬다.
- **수정:** 새 계약에는 이전 readiness를 과거 근거로만 보존한다. `activity`, `execution_phase`, `handoff_status`, `blocked_resource`, `resumer`를 분리하고 현재 계약의 관측만 준비 상태에 사용한다. 미전달·경로 미적용·probe 실패는 각각 필요한 행동을 반환한다.
- **수용 기준:** 이번 상태에서 “새 채널 권한 미적용 / probe 실패 / 호스트 설정 담당”을 표시; old ready와 현재 ready를 혼동하지 않음; polling을 반복해도 해결되지 않는 차단은 자동 재시도 대상으로 두지 않음.

### RC03-07 / P2 — 최초 준비가 전체 workflow 승인과 완료까지 연결되지 않음

- **근거:** 최초 중단까지 조율자 실행 셀 80개에서 `require_escalated` 지정 코드가 70곳, `prefix_rule` 제안이 20곳 발견됐다. 배열 map 등 동적 호출은 한 코드 위치로 센다. **실제 승인창·사용자 클릭 수는 이 로그만으로 확정하지 않는다.** 실행 기록에 `access plan`의 실제 미리보기나 `access apply`는 없고 후반 `access plan --help`만 있다.
- **원인:** 현재 [access.py](../../../handrail/setup/access.py:14)의 그룹은 전체 Plan/Work·최초 실행·통합·evidence·등록 검사를 포함하지 않는다. 스킬도 거부 뒤 개별 명령 승인을 유도한다. 복구 중 raw Herdr 조회·키 조작·내부 소스 읽기까지 필요해진다.
- **수정:** DEV-11의 저장소 운영 정책 준비에 정상 실행뿐 아니라 관측·진단·계약 전환·결과 제출·등록 검증을 포함한다. 실제 적용된 정책과 호출 형식을 진단하고 이후 동일 범위는 재사용한다. 제공자/호스트 및 CLI/IDE 적용은 관측으로 구분한다.
- **수용 기준:** 동일 저장소의 정상 흐름 및 승인 범위 내 복구에서 추가 운영 의도 질문·호스트 승인 0회 실측; 저장된 prefix 재사용과 사용자 클릭 지표를 혼동하지 않음.

### RC03-08 / P3 — 괄호 안 URL의 닫는 괄호가 링크에 포함됨

- **근거:** 작업자에게 전달된 Instruction 본문에 `href="https://bun.sh)"`가 들어 있다. [format.py](../../../handrail/board/format.py:10)의 `rich_text("Use Bun (https://bun.sh) for this project.")` 호출로 같은 결과를 재현했다.
- **수정:** URL 끝의 문장부호·짝이 맞지 않는 닫는 괄호를 분리하고 유효한 URL 내부 괄호와 구분한다.
- **수용 기준:** 괄호로 감싼 URL, 문장 끝 마침표, query/fragment, URL 자체의 짝 괄호에서 정확한 링크 생성. 카드 표시를 확인하지 않았으므로 이번 결론은 생성된 HTML 기준이다.

## 4. 구분해서 볼 사항

### 정상 동작 및 유지할 관문

- 보드 선택·지침 생성·frontend/backend 보드 배정은 진행됐다. 사용자 요청에 명시된 모델을 사용했고 frontend 완료 인계는 약 8초 안에 수집됐다.
- 조율자는 frontend 소스 검토·병합·빌드·화면 검사를 실제 이어갔다. backend 미완료 상태에서 Plan Done이나 전체 테스트 통과를 만들지 않았다.
- 신원 확인, 검토된 SHA 통합, probe를 승격 실행하지 않는 관문 자체는 유지한다. 수정 대상은 신원 판단의 정확성과 복구·권한 적용·제출 프로토콜이다.
- 최초 세션이 Handrail 소스 수정을 별도 범위로 요청한 것은 대상 서비스 구현과 플러그인 개발의 경계를 지킨 것이다. 이 분석 요청도 대상 세션의 수동 복구를 대신 수행하는 권한으로 해석하지 않았다.

### 구현 프로젝트의 문제와 Handrail 개선 근거

로그아웃·삭제 요청의 Content-Type/body 합의 차이, JSON 파일의 private mode, root 환경에서 쓰기 실패 검증이 어려웠던 문제는 대상 서비스의 구현·테스트 사항이다. 이를 Handrail 서버 기능 결함으로 분류하지 않는다.

다만 Handrail 자동 검수 설계에는 다음을 반영할 근거가 된다.

- 병렬 작업자에게 전달하는 API 계약에 body 없는 요청·헤더·오류·권한 시나리오까지 포함하고 통합 검사에서 확인한다.
- frontend Work의 넓은 UI 기준에 소스/빌드 통과를 기록하면서 실제 연동을 Plan에 미룬 점은 거짓 Plan 완료가 아니다. 그러나 어떤 동작 검증이 어느 기준에서 대기 중인지 구조화하지 않으면 Work Done을 완전한 UI 검증으로 오해할 수 있다. DEV-11의 기준별 필수 검사·미검증 분리를 보강한다.
- browser candidate 검사는 병합된 frontend와 당시 backend를 임시 환경에서 조합해 수행했다. 그 결과를 최종 canonical revision 검증으로 재사용하지 않아야 한다. 조율자 세션의 외부 실행 로그와 공식 `command.run` 기록도 연결해야 한다.

### 후속 진행에 대한 한계

14:50:51에 사용자가 원 세션에 경로 문제 해결과 Review 진행을 다시 요청했다. 14:51:29 조율자는 Cursor `/add-dir`로 정확한 채널을 추가하겠다고 보고했고, 14:52:19 DB에는 후속 message 제출이 기록됐다. 이는 **후속 복구 시도**이며 본 분석 시점에는 새 경로 적용·probe 통과·backend 수신·Plan Review 성공을 확인하지 않았다. 이 보고서는 이후 진행을 중단하거나 이미 복구된 것을 다시 실패로 변경하지 않는다.

## 5. 개발 우선순위와 DEV-11 연결

| 순서 | 수정 묶음 | 연결 |
| --- | --- | --- |
| 1 | RC03-01 신원 판단 + RC03-02 실제 권한 적용 + RC03-03 계약 전환 | DEV-11 D11-02/03/04의 선행 신뢰성 작업; A04/08/12 회귀 시나리오 |
| 2 | RC03-04 제출 도구 준비 + RC03-05 실패 보고 + RC03-06 상태 진단 | D11-02/03, A04/05/07 |
| 3 | RC03-07 최초 정책·명령 커버리지 및 실제 승인 측정 | D11-01/02/05, A01/02/11 |
| 4 | RC03-08 링크 렌더링 | 독립적인 작은 board 표시 수정 |

DEV-11의 자동 실행 범위를 넓히기 전에 1번 묶음을 먼저 해결해야 한다. 이번처럼 정상 세션을 교체로 판별하거나 적용되지 않은 채널을 활성화하는 상태에서는 자동 재시도가 실패를 반복한다. DEV-01~10의 과거 종료는 유지하며 이 보고서만으로 기능 수정·배포·수용 완료를 기록하지 않는다.

## 6. 검증 근거와 미실행 범위

- `process.py`, `service.py`, `handoff.py`, `worker_io.py`, `setup/access.py`, `application.py`의 소스 SHA-256과 설치본이 모두 일치했다. 따라서 위 실행 결함은 오래된 설치본만의 차이로 설명되지 않는다.
- 저장된 전후 process identity를 순수 함수에 넣어 `IDENTITY_STALE` 재현, 주 프로세스 레코드 일치, 새 채널의 원래 launch 범위 미포함, 새 Attempt에 old readiness 잔존을 확인했다.
- worker 제출 파일과 DB 수신 기록을 각각 읽어 “기존 채널 제출 있음 / 현재 backend 수신 없음”을 확인했다. nonce나 비밀값은 보고서에 복사하지 않았다.
- URL 렌더러의 순수 함수 재현을 확인했다. live 보드 표시·Cursor 권한 설정 재현·통합 서비스 테스트는 수행하지 않았다.
- 코드를 수정하지 않았으며 대상 저장소의 서버 실행, worker 지시·복구, 보드 쓰기, 권한 추가, Git 병합을 수행하지 않았다.
