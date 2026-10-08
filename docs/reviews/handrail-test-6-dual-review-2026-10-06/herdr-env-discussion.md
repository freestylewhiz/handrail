# HERDR_ENV: 발생 상황, 영향, 외부 조율과 진척 관리 개선

2026-10-06. 기존 Herdr workspace `wW`의 Codex GPT-6-Astra High와 Cursor Grok 4.7 High를 재사용해 1차 독립 분석과 2차 교차 토의를 진행했다. 이번 보고는 Handrail 제품 개선 관점의 분석이며 구현 변경은 아니다.

## 결론

실제 이름은 **`HERDR_ENV`**다. 사용자가 언급한 `HERDER_ENV`라는 별도 변수의 기능은 확인되지 않았다.

**`HERDR_ENV` 미설정은 외부 조율자에게 정상일 수 있다.** 설치된 Herdr 스킬은 pane 내부 실행을 전제로 이 값을 검사한다. Handrail이 외부에서 CLI로 작업자를 관리할 때에는 명시적인 연결·대상·권한 계약이 필요하다.

따라서 미설정만으로 통신 장애라고 판단할 필요는 없다. 대신 **같은 서버·세션의 같은 실행체에, 허용된 동작을 수행하는지** 확인해야 한다. 환경 변수 값을 수동으로 `1`로 만드는 방식은 해결책이 아니다.

이번 실제 관찰에서는 조율자의 관련 환경 변수가 없는데도 지정된 기존 검토 에이전트에 질문을 전달하고 답변을 수집했다. 그러나 현행 Handrail 코드가 외부 조율에 필요한 연결 고정·실행체 재검증을 모두 구현한 상태는 아니다.

## 1. 이 변수는 무엇인가

Herdr는 관리하는 pane의 프로세스에 `HERDR_ENV=1`과 workspace/tab/pane 문맥을 제공한다. 연결 선택용 `HERDR_SESSION`, `HERDR_SOCKET_PATH`는 별도 항목이다. `HERDR_ENV`를 인증 토큰이나 파일 쓰기 권한으로 해석할 근거는 없다. [공식 CLI reference](https://herdr.dev/docs/cli-reference/#environment-variables)

설치된 Herdr 0.9.1 스킬은 다음 조건을 확인하고, 충족하지 않으면 Herdr 밖에서 제어하지 말고 중지하라고 지시한다.

```sh
test "${HERDR_ENV:-}" = 1
```

이 스킬의 적용 범위를 이해해야 한다. 공식 문서는 **pane 내부 에이전트용 스킬**, **조율 스크립트용 CLI wrapper**, **custom client용 socket API**를 구분한다. pane 내부 스킬의 조건을 모든 외부 CLI 호출의 기술적 요건과 동일시하면 안 된다. [공식 통합 계층 설명](https://herdr.dev/docs/socket-api/#choose-an-integration-layer)

또한 v0.9.1의 TUI 중첩 실행 제한도 `HERDR_ENV`를 사용한다. “어떤 Herdr 코드도 이 변수를 검사하지 않는다”는 주장은 틀리다. CLI 제어와 TUI 시작 경로를 구분해야 한다. [버전 고정 main.rs](https://github.com/herdrdev/herdr/blob/v0.9.1/src/main.rs)

## 2. 어떤 상황에서 언급되나

| 상황 | 변수·문맥 상태 | 나타날 수 있는 현상 | 판단 |
| --- | --- | --- | --- |
| Herdr pane 안에서 시작한 에이전트 | Herdr가 제공한 caller 문맥 | 현재 pane 중심의 제어를 수행 | 문맥과 대상이 실제로 일치하는지 확인 |
| 일반 Codex/IDE/외부 프로세스가 Herdr를 조율 | 미설정일 수 있음 | 스킬을 읽은 조율자가 “Herdr 밖이므로 중지”라고 보고 | 외부 조율 계약의 적용 여부를 판단 |
| 환경이 걸러지거나 다른 프로세스로 이동 | 일부 문맥이 없어질 수 있음 | `--current`를 결정할 근거가 부족 | 가능한 발생 경로이며 이번 사례에서 재현하지 않음 |
| 예전 연결·caller 환경을 상속 | 값은 있지만 현재 대상과 다를 수 있음 | 다른 endpoint 또는 오래된 문맥을 사용할 위험 | 변수 존재만으로 정상 판정 불가 |
| caller 없이 대상이 생략된 raw 제어 | 명시 대상 없음 | 일부 명령이 화면에서 포커스된 pane을 선택할 수 있음 | 외부 관리 명령은 대상을 명시해야 함 |
| socket 접근 거부 또는 서버 미연결 | 변수와 별개 | EPERM·연결 실패 | 호스트 접근·서버 상태를 별도 진단 |
| agent 소실 또는 지시 대기 시간 초과 | 변수와 별개 | agent_not_found·stalled·timeout | 연결, 실행체, 전달·관찰 상태를 구분 |

현재 Handrail transport는 **이미 대부분의 관리 명령에서 명시 workspace/pane/agent를 사용한다.** 따라서 모든 현행 동작이 UI 포커스에 의존한다는 설명은 과장이다. 핵심 공백은 명시 ID의 유효 범위인 endpoint와 그 ID의 현재 실행체를 충분히 고정·재확인하지 않는 점이다.

## 3. 이번에 직접 확인한 사실

- 조율자에서 `HERDR_ENV`, `HERDER_ENV`, `HERDR_WORKSPACE_ID`, `HERDR_TAB_ID`, `HERDR_PANE_ID`가 모두 없었다. routing 변수 `HERDR_SESSION`, `HERDR_SOCKET_PATH`, `HERDR_CONFIG_PATH`도 없었다.
- Herdr client/server는 0.9.1, protocol 22였고 호환 상태가 확인됐다. session list에는 실행 중인 default 세션 하나가 있었다.
- 환경 변수를 위조하지 않고 명시한 두 검토 에이전트와 통신했다. 사용자에게는 이미 이들과 토의하라는 권한을 받았다.
- 테스트 세션 `handrail_test_6`의 수집 evidence에서는 `HERDR_ENV`/`HERDER_ENV` 문자열이 검색되지 않았다. 원문 전체에서 한 번도 언급되지 않았다고 확대하지 않는다.
- test_6의 EROFS·EPERM·agent 소실·prompt stall이 `HERDR_ENV` 부재 때문에 발생했다는 근거는 없다.

[관찰 기록](herdr-env-observations.json), [추가 소스·문서 메모](herdr-env-source-notes.md), [설치 API 계약 발췌](herdr-env-api-contract.json)를 보존했다. 성공 관찰은 이 환경의 해당 명령에 한정되며 다른 대상의 제어 권한을 뜻하지 않는다.

## 4. 어떤 문제를 야기하나

### 불필요한 중단과 반복 확인

외부 조율자가 pane 내부용 스킬의 중지 규칙만 적용하면, 이미 사용자에게 맡겨진 질문 전달·응답 수집·진척 관리가 멈출 수 있다. 이후 같은 외부 제어 허가를 반복해서 물으면 사용자의 부담이 커진다. 이번 이전 토의 시작 때 조율자가 추가 확인을 요청한 사례도 이 적용 범위 혼동과 관련 있다.

이 문제는 upstream 스킬을 무조건 제거해서 해결할 일이 아니다. Handrail 스킬에 내부 caller 모드와 명시적인 외부 조율 경로를 구분하고, 기존 사용자 지시를 어떻게 재사용하는지 적어야 한다.

### 잘못된 연결 또는 교체된 실행체에 대한 제어

`HerdrClient`는 session 인수를 지원하지만 `herdr_workflow._client()`는 인수 없이 생성한다. `_run()`도 별도 env를 넘기지 않아 호출 환경을 상속한다. 계획을 재개한 조율자의 실행 환경이 달라지면 같은 저장 ID를 다른 연결에서 사용할 수 있는 위험이 있다.

공식 연결 우선순위는 **명시 `--session` → `HERDR_SOCKET_PATH` → `HERDR_SESSION` → default socket**이다. 이 선택을 호출 때마다 주변 환경에 맡기지 않고 계획의 연결 정보로 관리할 필요가 있다. [공식 socket 경로 설명](https://herdr.dev/docs/socket-api/#socket-paths)

같은 이름·pane·cwd도 실행체 연속성의 완전한 증거는 아니다. 현재 `start()`는 반환되는 provider session·terminal identity를 충분히 저장하지 않고, `collect/prompt/keys`는 주로 저장된 agent 이름으로 접근한다. `recover()`도 관찰한 새 identity 전체를 저장 상태에 반영하지 않는다.

이는 **코드에서 확인한 설계 위험**이다. 이번 토의에서 다른 세션에 오지시했다는 관찰은 없다.

### 통신 상태를 개발 진척으로 잘못 표시

`start()`와 `prompt()`는 `_send_instruction()`의 성공 반환 상태를 사용하지 않고 `running`을 저장한다. 반환이 blocked 등을 나타내는 경우 현재 상태를 부정확하게 표시할 수 있다. 이 결과 해석 공백은 소스에서 확인했으며 별도 재현 실행은 하지 않았다.

`collect()`는 화면과 저장 상태를 반환한다. transport의 `agent_read()`는 visible 화면이 비어 있지 않으면 최근 전체 응답을 추가로 수집하지 않는다. `status()`는 live worker를 조회하지 않는다. 따라서 “현재 화면에서 답이 안 보임”, “저장 상태가 running”, “에이전트가 idle”만으로 개발 진척을 단정할 수 없다.

## 5. 무시해도 되는가

| 조건 | 권장 처리 |
| --- | --- |
| 승인된 외부 조율이며 연결·대상·작업 범위가 확인됨 | **HERDR_ENV 미설정만을 중단 사유로 삼지 않는다.** 같은 동의를 반복해서 묻지 않는다. |
| pane 내부 caller 문맥이 필요한데 없거나 불명확함 | 현재 pane을 추측하지 않는다. 적용 모드와 대상을 먼저 확인한다. |
| 연결 대상이 바뀌거나 실행체가 교체됨 | 변경 명령을 보류하고 재식별·복구한다. 비슷한 이름으로 자동 전환하지 않는다. |
| EPERM·연결 실패 | 해당 접근 실패를 해결한다. 환경 변수 설정으로 대체하지 않는다. |
| stalled·timeout | 미전달이나 업무 실패로 단정하지 않고 관찰·전달 상태를 확인한다. 자동 중복 전송을 하지 않는다. |
| agent idle/done | 입력 가능 상태와 결과 검수 단계를 구분한다. 카드 완료로 자동 승격하지 않는다. |
| 사용자가 대화만 요청한 기존 agent | 질문·답변 수집 범위를 재사용한다. 종료·새 능력 승인까지 확대하지 않는다. |

`HERDR_ENV=1`을 수동 주입해 스킬 조건을 통과시키는 방식은 권장하지 않는다. 실제 caller pane, socket 접근 권한, 올바른 대상이나 사용자 동의를 생성하지 않는다.

## 6. 조율자의 소통·진척 계약

조율자는 다음 상태를 별도로 기록해야 한다.

| 층 | 기록할 정보 | 상태의 의미 |
| --- | --- | --- |
| 연결 | 고정한 endpoint·선택 방식, 마지막 접속 관찰 | 어느 Herdr와 통신하는가 |
| 실행체 | 실행 시도, workspace/pane/terminal, provider session, worktree | 어느 worker 실행을 관리하는가 |
| 지시 | 로컬 ID·내용 해시, 제출 결과, 활동·응답 관찰 | 어떤 요청이 어디까지 확인됐는가 |
| 관찰 | agent 상태, 시각, visible/recent 출처, 수집 범위 | 지금 무엇을 알고 무엇을 모르는가 |
| 업무 | 변경·검수·통합·검사 증거와 카드 단계 | 개발 결과가 어느 단계인가 |

로컬 지시 ID는 추적용이다. 그것만으로 worker의 수신 확인이 생기지는 않는다. 조회 실패는 마지막 확정 상태를 보존하면서 관찰 불가로 표시하고, 침묵 시간으로 실패나 진행률을 만들어내지 않는다.

사용자에게는 예를 들어 **“작업자 응답 대기: 지시 제출은 확인했으며 마지막 관찰은 실행 중, 다음 단계는 결과 검수”** 또는 **“작업 상태 관찰 불가: Herdr 연결 실패, 마지막 확인 상태는 실행 중”**처럼 대상·근거·다음 행동을 설명해야 한다.

## 7. 우선 개선 백로그

### HR6-E01 · P1 · 외부 조율 모드와 endpoint 고정

- **근거:** generic skill의 내부 caller 조건, `HerdrClient.__init__/_argv/_run`, `flow._client`.
- **변경:** Handrail의 외부 모드와 사용자 지시 출처를 명시한다. 실제 연결 선택·endpoint를 private 계획 기록에 저장하고 이후 명령에도 동일하게 적용한다. 연결을 바꾸는 환경만 통제한다. default에 추측한 named-session 인수를 붙이지 않는다.
- **수용 기준:** pane 안팎에서 같은 계획이 같은 endpoint를 사용한다. 미설정 env만으로 불필요한 중단·재승인 없음. 모호한 current/focus 대상과 조용한 다른 서버 fallback 없음.
- **연결:** 기존 U02·U05를 구체화한다.

### HR6-E02 · P1 · 실행 identity 저장·재검증

- **근거:** `_ensure_space/start/collect/recover/keys/_close_space` 및 API AgentInfo.
- **변경:** endpoint와 Handrail 실행 시도, workspace/pane/terminal, 가능한 provider session, 승인 worktree를 묶는다. 정상 상태 변화와 실행체 교체를 구분하고, 복구 시 identity를 정합화한다.
- **수용 기준:** 다른 서버의 같은 이름 또는 교체된 실행체를 자동 채택하지 않는다. 선택적 identity 필드가 없으면 다른 근거로 연속성을 판단하고 확신이 부족한 제어는 보류한다. cwd 하위 이동이나 revision 증가만으로 교체라고 단정하지 않는다.
- **한계:** 현재 설치 API에는 사전 조회한 expected provider-session/revision과 제어 대상을 원자적으로 비교하는 인수가 확인되지 않았다. get 후 send 사이 교체 가능성은 남는다. Herdr의 wait 내부 occupant 고정과 이 보장을 혼동하지 않는다. 향후 조건부 제어 지원은 Herdr 연동 요구로 별도 검토한다.
- **연결:** 기존 F02·F03을 구체화한다.

### HR6-E03 · P1 · 지시 전달 결과와 실행 상태 분리

- **근거:** `_send_instruction`, transport `agent_prompt`, workflow `start/prompt`.
- **변경:** 반환된 agent 상태를 반영한다. 제출 의도, 제출 결과, 활동 관찰, 응답 수집을 기록한다. 오류를 구조적으로 해석한다.
- **수용 기준:** blocked를 running으로 덮지 않는다. timeout/stall이 미전달 증거로 둔갑하지 않는다. 입력 전 거절이 확인된 경우만 제한적으로 재시도하는 기존 방어를 보존한다. 재시도마다 지시가 중복 실행되지 않도록 불확실성을 먼저 해소한다.
- **연결:** 기존 F02 및 진척 신뢰성을 보완한다.

### HR6-E04 · P1 · 관찰과 업무 진척을 분리한 상태 출력

- **근거:** `agent_read`, `collect`, `status`, `_idle`, `review/finish`.
- **변경:** 저장 상태와 live 관찰, 시각·출처·수집 범위를 구분한다. 승인 UI 확인은 visible, 완료 응답 수집은 필요한 recent 자료를 사용한다. 재접속 후 재조회한다.
- **수용 기준:** 연결 실패를 업무 실패로, idle/done을 카드 완료로 표시하지 않는다. 답변이 화면 밖에 있다는 이유로 미응답 판정하지 않는다. 사용자는 누구의 무엇을 기다리는지 알 수 있다. 순수 조회·저장·원격 동기화의 분리는 U03과 함께 진행한다.
- **후속:** 지원되는 변화 정보나 이벤트를 이용한 관찰 효율화는 가능하지만, 최신 근거 없는 진행률 생성은 하지 않는다.

### HR6-E05 · P1 · 키 입력·종료의 동작별 권한

- **근거:** `keys`의 reason 문자열, `accept/_close_space`의 관리 자원 종료.
- **변경:** 현재 UI에서 키가 뜻하는 행동과 기존 승인 범위를 연결한다. agent와 대화할 권한, 설치·삭제 등을 승인할 권한, workspace를 종료할 권한을 구분한다.
- **수용 기준:** 기존 요청에 포함된 동작은 재질문하지 않는다. 대화 요청으로 세션 종료나 새로운 능력을 승인하지 않는다. 원래 관리 계획의 합의된 cleanup은 기존 권한을 재사용한다. 반복 동의 질문을 기술적인 대상 불확실성의 해결책으로 삼지 않는다.
- **연결:** 기존 U02·F01·F07과 함께 적용한다.

## 8. 두 모델의 합의와 조율자의 정정

| 논점 | 최종 판단 |
| --- | --- |
| 외부에서 HERDR_ENV가 없는 상태 | 정상 지원 모드로 만들 수 있음. 지침과 연결 계약을 분리 |
| 현재 CLI 성공의 의미 | 해당 연결·명령의 성공만 확인. 모든 외부 제어의 안전·권한을 보장하지 않음 |
| endpoint 고정 우선순위 | 두 모델 모두 최종적으로 P1로 판단 |
| 키 입력·종료 | Cursor가 1차의 포괄적 표현을 제한. 기존 동작 범위가 실제로 포함하는지 확인 |
| 이름·pane·cwd만의 identity | 부족. 제공되는 terminal/provider session까지 활용하되 선택적 필드와 경합 한계 인정 |
| timeout 자동 재전송 | 하지 않음. 이미 있는 Handrail 방어 보존 |
| 현재 managed 명령이 전부 focus 의존 | 사실 아님. 대부분 명시 대상을 사용 |

원문 검토에는 다음 정정이 필요하다.

- Cursor 최종 응답의 socket 우선순위에서 `HERDR_SESSION`과 `HERDR_SOCKET_PATH` 순서가 뒤바뀌었다. 이 보고서는 공식 문서 순서로 수정했다.
- `HERDER_ENV`를 별도 기능의 변수처럼 읽을 수 있는 Cursor 표현은 채택하지 않았다. 확인한 변수는 `HERDR_ENV`다.
- “변수를 1로 넣는 행동을 무시해도 된다”는 모호한 문구는 채택하지 않았다. 두 검토의 취지는 수동 위조를 해결책으로 쓰지 말자는 것이다.
- Cursor가 남은 차이로 적은 “Astra의 세션 이름 자동 부여”는 Astra 최종 의견과 일치하지 않는다. Astra도 추측한 이름을 붙이지 말라고 명시했다. 최종 정책상 이 부분의 실질적 이견은 없다.

## 9. 범위와 자료

정확한 모든 socket EPERM 원인, 모든 Herdr 배포 환경의 인증 구조, 서버 재시작 후 identity 연속성을 확정하지 않았다. 설치 API의 version/protocol/endpoint_protocol_generation을 server incarnation으로 사용하지 않는다. 이번에는 프로젝트·카드·환경을 변경하거나 테스트·설치·서버를 실행하지 않았다. 기존 두 분석 agent와의 사용자 승인된 대화 및 읽기 전용 진단을 수행했다.

- [1차 의뢰](herdr-env-discussion-brief.md), [2차 교차 질문](herdr-env-round2-brief.md)
- [Codex 1차](herdr-env-astra-round1.md), [Cursor 1차](herdr-env-grok-round1.md)
- [Codex 2차](herdr-env-astra-round2.md), [Cursor 2차](herdr-env-grok-round2.md)
- [관찰 기록](herdr-env-observations.json), [추가 근거](herdr-env-source-notes.md), [API 계약](herdr-env-api-contract.json), [실행 provenance](herdr-env-discussion-provenance.json)
