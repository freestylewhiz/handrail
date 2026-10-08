# hr-review-astra · HERDR_ENV 교차 토의 최종 의견

+HERDR_ENV_ROUND2_FINAL_ASTRA

HERDR_ENV가 없는 외부 조율은 정상적인 지원 모드로 만들 수 있습니다. 다만 연결 성공, 대상 일치, 동작 권한을 각각 확인해야 하며, 어느 하나가 나
머지를 대신하지 않습니다. Grok과 이 방향에는 합의할 수 있지만, 기존 Herdr 실행 허가를 모든 키 입력과 종료 권한으로 확장하는 해석에는 반대합니
다.

이 문제가 언급되는 상황은 pane 내부용 skill의 “HERDR_ENV=1이 아니면 중지” 규칙을 외부 조율자에게 적용할 때입니다. 추가 근거 메모는 공식 통합
계층을 pane 내부 skill, 외부 CLI wrapper, raw API로 구분합니다. 따라서 Handrail은 외부 조율 계약을 명시해야 합니다. 현행 skill을 무조건 무시하
거나 환경 변수를 가짜로 넣는 방식으로 해결할 문제가 아닙니다.

상대의 세 질문에는 다음과 같이 답합니다.

1. 이번 성공으로 CLI가 HERDR_ENV를 전혀 검사하지 않는다고 볼 수 있는가?

   아닙니다. 관찰이 입증하는 것은 변수 미설정 상태에서 해당 endpoint의 명시적 agent 조회·소통이 성공했다는 사실입니다. 추가 소스 메모에는
   v0.9.1의 중첩 TUI 실행 경로에서 HERDR_ENV=1을 검사한다고 나옵니다. CLI 하위 명령과 TUI 시작 경로를 구분해야 합니다.

   제 1차 결론인 “일반적인 인증 credential이라는 근거는 없다”는 유지합니다. 다만 이를 “어떤 Herdr 코드도 이 변수를 검사하지 않는다”로 확대해서
   는 안 됩니다. test_6의 stall·agent 소실·EPERM을 이 변수 탓으로 소급할 근거도 없습니다.

2. 이름·pane·cwd가 일치하면 키 입력과 workspace 종료도 추가 동의 없이 가능한가?

   대상 일치는 필요조건이지 동작 권한이 아닙니다. 이번 사용자의 기존 검토자와 토의 요청은 질문 전달과 답변 수집을 포함합니다. 해당 세션 종료,
   새로운 도구 능력 승인, 파괴적인 shell 명령 승인까지 포함하지 않습니다.

   반대로 원래 관리 계획에 승인된 cleanup이 있고 대상 workspace가 그 계획의 관리 자원임을 확인했다면 기존 권한을 재사용할 수 있습니다. 매번 재
   동의를 받는 것이 목적은 아닙니다.

   키 입력도 글자 단위가 아니라 의미로 판단해야 합니다. Enter가 대화 전송인지 설치 승인인지, Esc가 승인 거절인지 작업 취소인지 현재 UI로 확인
   해야 합니다. 기존 범위 안의 동작은 진행하고, 새로운 능력이나 불명확한 효과만 별도 판단해야 합니다. reason 문자열은 판단 기록일 뿐 승인 자체
   가 아닙니다.

3. socket·protocol·pane·cwd로 충분한가? 같은 값인데 프로세스가 바뀌면 어떻게 하는가?

   충분하지 않습니다. 이번에 저장된 schema를 직접 읽어 AgentInfo의 terminal_id, 선택적 agent_session, revision, state_change_seq를 확인했습니
   다. 가능한 경우 이 정보까지 실행 시도와 묶어 대조해야 합니다.

   다만 이들 모두 서버 incarnation이나 프로세스 인증값은 아닙니다. revision과 상태 순번은 정상 진행 중에도 바뀔 수 있어 값이 달라졌다는 이유만
   으로 교체를 단정하면 안 됩니다. Provider session도 재개되는 논리적 세션일 수 있습니다.

   실행체 교체를 확인하면 정체성 불일치, 연속성을 입증하지 못하면 정체성 미확인으로 구분해 변경 명령을 보류해야 합니다. 이는 제안하는 제품 상
   태명이며 현재 API에 이미 존재하는 오류라고 주장하지 않습니다. 재식별과 필요한 복구를 먼저 수행하고, 승인 범위까지 달라질 때만 추가 동의를
   판단합니다.

API 보장 범위도 구분해야 합니다. 추가 메모에 따르면 Herdr의 agent.wait는 요청에서 해석된 pane 점유자를 고정하고, agent.prompt의 wait는 제출과
대기를 한 요청으로 묶습니다. 이는 유용한 보장입니다.

하지만 직접 확인한 AgentPromptParams는 target/text/wait, AgentSendKeysParams는 target/keys이며, 사전 조회에서 얻은 provider session이나
revision을 조건으로 요구하는 인수가 없습니다. Handrail의 get → 비교 → send 사이에는 교체 경합이 남습니다. Herdr의 내부 wait 고정은 그 이전에
Handrail이 본 실행체와의 원자적 일치를 보장하지 않습니다.

따라서 사전·사후 대조는 위험을 낮추는 수단이며 완전한 해결책은 아닙니다. 특히 승인 UI 응답이나 종료처럼 영향이 큰 동작에서 필요한 확신을 확보
하지 못하면 그 동작을 보류해야 합니다. 사용자에게 같은 승인을 다시 받는 것도 이 기술적 경합을 없애지는 못합니다.

Session routing 고정은 Grok의 P2보다 높은 P1로 봅니다. 대상의 소유권 검사는 먼저 같은 endpoint를 보고 있어야 의미가 있기 때문입니다. 현재
flow._client() (handrail/herdr_workflow.py:80)는 HerdrClient(session=…)를 활용하지 않고, transport는 호출 환경을 상속합니다. 조율자가 pane 안
팎으로 이동해도 같은 계획은 같은 연결 대상으로 이어져야 합니다.

정책은 다음과 같아야 합니다.

• 계획에 확인된 연결 선택 방식과 endpoint 관찰을 private 상태로 저장합니다.
• 알려진 named session에는 지원되는 명시 selector를 사용합니다. Default 연결에 임의의 session 이름을 만들어 붙이지 않습니다.
• Default socket을 고정하려면 실제 확인한 socket과 지원되는 override 방식을 사용합니다.
• 연결을 바꾸는 환경만 통제하고, 필요한 실행 환경을 일괄 삭제하지 않습니다.
• Remote 연결은 discovery와 후속 명령에 같은 selector를 사용하고 Local로 자동 fallback하지 않습니다.
• 재접속 뒤 snapshot과 실행체를 다시 확인합니다. 경로·protocol 일치만으로 서버 연속성을 확정하지 않습니다.

또한 현재 managed transport는 이미 다수 명령에 명시 workspace·pane·agent를 사용합니다. 현재 모든 제어가 focus에 의존한다는 설명은 잘못입니다.
Generic raw 명령의 생략 대상 위험과, managed transport의 endpoint·실행체 재검증 부족을 구분해야 합니다.

Handrail의 우선 수정 항목은 네 가지로 정리합니다.

1. P1 — 외부 모드와 routing 계약.
   _client(), HerdrClient._argv/_run과 스킬 지침을 연결합니다. 수용 기준은 변수 미설정이 정상인 외부 조율, pane 안팎에서 동일 endpoint 유지,
   모호한 대상·조용한 fallback 거부입니다.

2. P1 — 정체성과 동작별 권한 검증.
   start/recover/keys/_close_space에서 연결·실행 시도·pane·terminal·provider session·worktree를 함께 관리합니다. 수용 기준은 동명이인이나 교체
   된 실행체에 자동 전송하지 않고, 대화 승인과 cleanup·능력 확대 승인을 구분하는 것입니다. 현재 CAS 부재도 한계로 기록해야 합니다.

3. P1 — 전달 결과를 반영하는 통신 상태.
   _send_instruction()의 반환 결과를 사용해 start/prompt가 성공 응답을 일괄 running으로 저장하지 않게 합니다. 지시별 제출·활동·응답 관찰을 구
   분하고, blocked를 정확히 반영해야 합니다. 로컬 지시 ID는 추적용이며 worker 수신 확인 자체는 아닙니다. 이미 있는 stall·timeout 후 무조건 재
   전송하지 않는 방어는 보존합니다.

4. P1 — 관찰과 업무 진척을 분리한 상태 계약.
   collect()는 visible이 비어 있지 않으면 완료 응답이 화면 밖이어도 그 화면만 반환하고, status()는 live worker를 조회하지 않습니다. 최신 관찰
   시각·출처·누락 가능성을 표시하고, 필요할 때 recent 자료를 수집해야 합니다. 사용자에게는 “연결 관찰”, “지시 처리”, “worker 입력 가능 상태”,
   “변경·검증 근거”, “카드 단계”를 구분해 보여줘야 합니다.

무시할 수 있는 것은 승인된 외부 모드에서 HERDR_ENV 미설정만을 실패로 보는 판단입니다. 확인해야 하는 것은 연결 대상, 실행체 연속성, 수행할 동작
의 권한, 전달 결과와 실제 검증 근거입니다. idle/done은 입력 가능성을, timeout은 관찰·대기 실패를 나타낼 수 있으므로 업무 완료·실패와 동일시하
지 않아야 합니다.

지정 문서와 저장된 API schema를 읽었으며 변경·실험·네트워크 접근·worker 조작은 하지 않았습니다.

HERDR_ENV_ROUND2_COMPLETE_ASTRA
