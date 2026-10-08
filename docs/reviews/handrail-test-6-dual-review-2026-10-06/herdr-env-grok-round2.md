# hr-review-grok · HERDR_ENV 교차 토의 최종 의견

+HERDR_ENV_ROUND2_FINAL_GROK

HERDR_ENV가 비어 있다는 말은 조율자가 pane 안에 없다는 뜻이지, 이번 연결이 실패했다는 뜻은 아니다. 설치 skill의 중지는 pane 안
에이전트용으로 남기고, Handrail의 외부 CLI 조율은 별도 계약으로 둔다. 현행 skill을 통째로 무시하는 결론은 아니다.

이 변수는 사용자가 HERDER_ENV라고 부른 것과 같은 기능이 아니다. 설치 skill과 CLI 문서는 HERDR_ENV를 pane 프로세스 안의 신호로 적고,
연결은 --session, HERDR_SESSION, HERDR_SOCKET_PATH, 기본 소켓 순서로 고른다. 이번 조율자에는 그 변수들이 없었고, 기본 세션 하나의
소켓으로 이름을 명시한 list, get, read, prompt가 성공했다. 그 성공은 이 연결의 관찰이지 모든 외부 제어의 안전 증명은 아니다. test_6의
EPERM, agent_not_found, stall을 이 변수 때문에 생겼다고 소급하지 않는다.

무시해도 되는 것은 외부 조율자가 변수가 없다고 승인된 명시 대상을 멈추는 행동, 그리고 변수를 1로 넣어 pane 문맥을 만드는 행동이다.
확인해야 하는 것은 어느 소켓인지, live agent가 기록된 pane·cwd·provider session과 같은지, 이번 명령이 기존 허가의 어느 작업인지다. 읽기가
됐다고 키 입력과 workspace 종료까지 허가된 것은 아니다.

Astra의 세 질문

명시적 외부 지시를 skill의 blanket stop 대신 무엇으로 바꾸냐는 질문에는 이렇게 답한다. pane 안 skill, 외부 CLI 조율, raw API는 다른
계층이다. Handrail 계약은 CLI 계층만 연다. 조율자는 HERDR_ENV 없이도 기록된 workspace, pane, agent 이름으로 조회와, 허가가 덮는 지시를
보낸다. --current와 생략된 pane은 쓰지 않는다. 연결이 실패하면 다른 서버나 Local로 바꾸지 않는다. pane 안에서 Herdr skill을 따르는
에이전트는 지금처럼 변수가 없으면 멈춘다. 여기까지는 Astra와 같다.

incarnation이 없을 때 최소 식별은 이름만이나 cwd만이 아니다. 1차에서 그 둘에 가깝게 말한 것은 보완한다. 제어 전에 agent get이 돌려주는
workspace, pane, 이름, cwd가 저장된 값과 같아야 한다. agent_session이 응답에 있으면 시작 때 저장하고 나중에 값이 바뀌면 멈춘다. 필드가
없는 것은 실패가 아니다. schema상 선택이다. terminal_id가 바뀌면 같은 이름의 새 점유자로 보고 제어를 멈추고 복구로 간다. revision과
state_change_seq는 작업 중 증가할 수 있어서 동일성 검사에 쓰지 않는다. 서버 재시작을 가리는 instance ID는 SessionSnapshot에 없다.
endpoint_protocol_generation도 그 ID가 아니다.

사전 get과 Herdr wait의 차이도 남긴다. agent.wait는 그 요청 안에서 해석한 pane occupant를 고정한다. agent.prompt의 wait는 제출과 대기를
한 요청으로 묶는다. AgentPromptParams에는 expected session이나 revision이 없다. Handrail이 get으로 비교한 뒤 따로 prompt를 보내면, 그
사이에 점유자가 바뀌는 경합을 API가 막아 주지 않는다. 이 한계를 검사로 없앴다고 기록하지 않는다.

진척의 최소 계약은 이렇다. 지시마다 내용 해시, 대상 이름, 시각을 남긴다. _send_instruction의 반환에 blocked가 있으면 running으로 덮지
않는다. 지금 start와 prompt는 그 반환을 보지 않고 running을 저장한다. stall과 timeout은 재전송하지 않는 기존 방어를 유지한다. 그 결과는
미전달 증명도, 업무 실패도 아니다. idle과 Herdr done은 입력 가능이지 검수·통합·카드 Done이 아니다. collect는 visible이 비어 있지 않으면
그 화면만 반환하므로, 진척 문장에 viewport 스냅샷이라고 적는다. 화면 밖 답을 못 봤다고 실패로 만들지 않는다. status는 저장 상태와
Kanban만 반환하고 live worker를 조회하지 않으니, 연결 가능이나 작업 완료라는 말을 붙이지 않는다. 조회 실패는 마지막 확정 상태를 두고 관찰
불가로 남긴다.

키 입력과 종료

1차의 “기존 Herdr 실행 허가면 키 입력과 종료도 다시 묻지 않는다”는 작업별로 줄인다. 이번 사용자가 기존 검토자와 토의하라고 한 범위는 그
agent에 대한 대화와 화면 읽기다. 그 세션을 닫거나, 새 능력을 승인하거나, 임의 파괴 키를 보내는 허가는 포함하지 않는다. 반대로 원래 관리
계획에서 사용자가 완료를 말해 accept가 그 계획의 workspace만 닫는 동작은 그 완료 허가를 재사용한다. keys의 reason 문자열은 승인 증거가
아니다. 화면에 보인 질문이 이미 정한 범위와 같을 때만 그 키를 보낸다. test_6에서 삭제와 설치가 한 명령으로 보인 뒤 Escape를 보낸 것은 그
경우에 가깝고, 새 설치를 허용하는 키와는 다르다.

세션 고정의 우선순위

endpoint를 계획에 고정하는 거부는 P1이다. 관찰된 소켓 경로, 버전, protocol을 저장하고, 다음 제어 전에 status의 소켓이 다르면 멈춘다.
HerdrClient(session=...)를 flow가 안 쓰는 것은 사실이고, _run이 환경을 상속하는 것도 사실이다. 다만 기본 세션의 이름을 추측해 --session을
붙이는 것은 P1이 아니다. 저장돼 있거나 status가 실제로 준 이름만 전달한다. 조율자가 pane 안이든 밖이든 같은 계획은 그 pin된 endpoint만
쓴다. PATH나 사용자가 둔 HERDR_CONFIG_PATH까지 지우는 일괄 제거는 하지 않는다. 상속을 막을 항목은 생략 대상을 포커스로 보내는
HERDR_PANE_ID, HERDR_TAB_ID, HERDR_WORKSPACE_ID다. 관리형 transport는 이미 workspace, pane, 이름을 대부분 넘기므로, 모든 현재 동작이
focus에 의존한다고 말하지 않는다. 공백은 raw skill의 생략 대상과, 관리형 호출이 명시 ID 뒤의 provider session과 terminal을 다시 보지 않는
데 있다.

우선 수정은 다섯 가지다. 외부 모드 계약을 skill 무시와 분리해 문서화한다. 있는 필드로 대상을 저장하고 제어 전에 비교하되 CAS가 없다고
적는다. 키 입력과 종료를 작업별 허가로 제한한다. prompt 반환의 blocked를 남기고 timeout 재전송 금지를 유지한다. status와 collect가 관찰의
한계를 그대로 말하게 한다.

Astra와 갈리는 부분은 세션 이름의 자동 부여뿐이다. 소켓 pin과 불일치 시 중지는 같이 가고, 없는 세션 이름을 만들어 --session에 넣는 구현은
받아들이지 않는다.

HERDR_ENV_ROUND2_COMPLETE_GROK
