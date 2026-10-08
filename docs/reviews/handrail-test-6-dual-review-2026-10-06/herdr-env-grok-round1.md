# hr-review-grok · HERDR_ENV 1차 분석

+HERDR_ENV_ROUND1_FINAL_GROK

설치 skill의 중지는 “pane 안에서만 제어하라”는 호출자 문맥 규칙이고, 이번 외부 조율자의 명시적 agent 제어가 실패한 증거는 없다. 그 규칙을
Handrail이 그대로 따르면 진척 관리가 멈추고, 규칙의 위험만 지우면 다른 세션의 같은 이름에 지시를 보낼 수 있다.

사용자는 HERDER_ENV라고 불렀지만, 설치된 Herdr 0.9.1 skill의 이름은 HERDR_ENV다. skill은 제어 명령 전에 test "${HERDR_ENV:-}" = 1을 하고,
실패하면 Herdr 밖에서 포커스된 세션을 보거나 조작하지 말고 멈추라고 한다. 설명은 “지금 이 프로세스가 Herdr가 관리하는 pane 안에서 떠
있는지”를 확인하라는 문장이다. CLI --help는 이 변수를 연결 주소나 인증으로 적지 않는다. 도움말에 있는 환경 변수는 HERDR_CONFIG_PATH이고,
대상 선택은 --session, --machine, --remote와 로컬 소켓이다. 관찰된 서버는 0.9.1, protocol 22, 소켓
/home/dyhwang23/.config/herdr/herdr.sock이다. 이 수준에서 HERDR_ENV는 인증 자격으로 확인되지 않았다. 서버가 그 값을 검사하는지는 이번
자료에 없다.

이번 조율자 프로세스에는 HERDR_ENV, HERDER_ENV, HERDR_WORKSPACE_ID, HERDR_TAB_ID, HERDR_PANE_ID가 모두 없다. 값을 만들어 넣지 않았다.
그런데 이름을 명시한 agent list는 hr-review-astra(wW:p1), hr-review-grok(wW:p2)를 돌려줬고, 그 앞의 prompt와 read도 성공했다. 사용자는
기존 Herdr 검토 세션과 토의하라고 명시했다. 그래서 “변수가 없으면 CLI가 거부한다”는 인과는 이 관찰과 맞지 않는다. skill 문장과 CLI 기술
요건이 어긋난 상황이다.

┌───────────────┬─────────────────────────────────────────────────────────────────────────────────┐
│ 구분          │ 이번 자료에서 보인 것                                                           │
├───────────────┼─────────────────────────────────────────────────────────────────────────────────┤
│ 이름          │ 사용자 표현은 HERDER_ENV, skill과 가드는 HERDR_ENV                              │
├───────────────┼─────────────────────────────────────────────────────────────────────────────────┤
│ 조율자 환경   │ 위 다섯 변수가 전부 비어 있음. 위조하지 않음                                    │
├───────────────┼─────────────────────────────────────────────────────────────────────────────────┤
│ skill         │ 변수가 1이 아니면 제어를 멈추라고 지시                                          │
├───────────────┼─────────────────────────────────────────────────────────────────────────────────┤
│ CLI           │ 0.9.1이 기본 소켓으로 동작. 도움말은 변수를 인증 항목으로 적지 않음             │
├───────────────┼─────────────────────────────────────────────────────────────────────────────────┤
│ 성공한 호출   │ 명시적 agent 이름의 list, get, read, prompt                                     │
├───────────────┼─────────────────────────────────────────────────────────────────────────────────┤
│ 사용자 권한   │ 기존 세션과의 토의를 명시적으로 요청                                            │
├───────────────┼─────────────────────────────────────────────────────────────────────────────────┤
│ Handrail 코드 │ HERDR_ENV를 읽지 않음. _client()는 HerdrClient()만 만들고 session을 넘기지 않음 │
└───────────────┴─────────────────────────────────────────────────────────────────────────────────┘

test_6의 agent_prompt_stalled, agent_not_found, pane EPERM은 이 변수 부재와 연결하지 않는다. 그 기록에는 HERDR_ENV 언급이 없고, stall은
skill이 설명하는 5초 activity gate와 맞닿아 있다. agent_prompt는 제출 뒤 5초 안에 working 또는 blocked가 없으면 agent_prompt_stalled를
돌려주고, timeout은 그 대기와 별개다. idle은 입력 가능이고, Kanban Done은 카드 상태다. 소켓 권한 거부는 host sandbox다.

무시할 수 있는 범위

skill의 무조건 중지를 외부 조율자가 따르는 것은 무시하면 안 되는 제품 충돌이다. Handrail 조율자는 worker pane 밖에서 herdr를 호출하도록
만들어져 있다. _client()가 그 프로세스에서 CLI를 실행한다. 가드를 그대로 적용하면 기록된 worker에게 지시, 수집, 복구, 종료를 할 수 없고,
카드는 진행 중으로 남는다. 사용자는 이미 Herdr workflow를 고른 상태인데 명령마다 “pane 안에 없다”는 이유로 다시 동의를 받는 꼴이 된다.

반대로 가드가 막으려는 행동을 지우는 것도 안 된다. skill은 HERDR_PANE_ID가 없으면 생략된 pane 대상이 포커스된 pane으로 갈 수 있다고 한다.
ID와 live agent 이름은 서버 하나 안에서만 유효하고, agent가 빠져나가면 이름이 지워졌다가 다시 쓰일 수 있다. --current와 상속된 caller
context는 외부 프로세스에 없다. 이름이 같다고 다른 세션이나 다른 기계의 w1:p1이 같은 대상인 것은 아니다.

그래서 규칙은 이렇게 나눈다. 사용자 권한으로 기록된 workspace, pane, agent 이름을 그대로 쓰는 읽기와, 그 기록이 살아 있는 대상과 일치할
때의 지시 전송은 HERDR_ENV 없이도 계속한다. 환경 변수를 1로 넣어서 가드를 통과하는 것은 하지 않는다. 대상이 비어 있거나 --current이거나,
live 조회가 기록된 pane, 이름, cwd와 다르면 멈추고 다른 곳으로 보내지 않는다. 이 중지는 기술 실패가 아니라 대상 불일치다. 소켓 EPERM,
agent 없음, prompt stall, timeout, idle, 카드 Done은 각각 다른 상태로 남긴다.

HerdrClient._run은 env를 지정하지 않아서 조율자 환경을 그대로 물려받는다. 지금은 그 환경에 Herdr caller 변수가 없어서 기본 소켓으로 갔다.
나중에 조율자가 pane 안에서 뜨거나 셸에 오래된 HERDR_PANE_ID가 있으면, 생략된 대상은 그 pane을 따른다. _client()는 session=을 넣지
않으므로 --session도 붙지 않는다. 시작 때 herdr.json에 적는 것은 workspace id, root pane, agent 이름, worktree다. collect,
_send_instruction, keys, recover는 그 이름으로 agent_get과 prompt를 다시 호출할 뿐, 서버 소켓이나 protocol, cwd를 다시 대조하지 않는다.
관찰된 herdr status에는 incarnation 필드가 없다. 없는 세대를 저장했다고 말하고 해결됐다고 하지 않겠다. 지금 대조할 수 있는 것은 status에
있는 버전, protocol, 소켓 경로와, agent 조회가 돌려주는 pane과 cwd다.

읽기와 변경도 나눈다. list, get, read, status는 명시 이름이 있을 때 이번처럼 성공할 수 있다. 그래도 진척 댓글에 쓰기 전에 기록과 응답이
같은지 본다. prompt, send-keys, workspace close는 같은 확인을 통과한 뒤에만 한다. 사용자가 이미 그 worker의 Herdr 실행을 허용했다면,
확인이 맞는 동안 키 입력이나 종료를 위해 동의를 반복하지 않는다. 확인이 실패하면 그 변경만 중단한다.

고칠 것

P1. 외부 조율 모드를 skill과 코드에 고정한다. 근거는 설치 skill의 중지 문장, herdr_workflow._client, herdr_transport.HerdrClient._argv다.
조율자 문서에는 HERDR_ENV가 없는 것이 정상이라고 적고, 값을 만들지 말며, --current와 생략 대상을 금지한다. 수용 기준은 변수가 없는
조율자가 기록된 work-<id>로 prompt까지 가고, 대상이 없는 raw herdr pane 호출은 Handrail이 만들기 전에 거절하는 것이다.

P1. 지시 전에 live 대상을 기록과 비교한다. 근거는 start가 저장하는 pane과 이름, _send_instruction, keys, recover, _close_space다. 비교
항목은 저장된 agent 이름, pane id, worktree cwd, 그리고 status에서 읽은 소켓 경로와 protocol이다. 하나라도 다르면 HERDR_IDENTITY_STALE로
멈추고 비슷한 이름에 다시 보내지 않는다. 수용 기준은 test_6처럼 agent가 사라진 뒤 같은 work-24가 다른 pane에 생겨도, cwd와 pane이 기록과
같기 전에는 prompt가 나가지 않는 것이다.

P1. 진척 상태를 원인별로 남긴다. 근거는 _send_instruction이 agent_not_ready만 재시도하고 stall은 HERDR_PROMPT_UNKNOWN으로 올린다는
점이다. 보드에 보이는 한 줄은 “대상 work-24, pane 불일치”, “소켓 권한”, “5초 안에 활동 없음”, “idle이라 입력 가능” 중 하나여야 한다.
HERDR_ENV 부재를 이 문장에 넣지 않는다. 수용 기준은 사용자가 카드만 봐도 다음 행동이 호스트 권한인지, 화면 확인인지, 이미 끝난 카드인지
갈린다.

P2. 세션을 private 상태에 고정하고 caller 환경은 물려받지 않는다. 근거는 _run의 환경 상속과 _argv의 조건부 --session이다. workspace를
만든 뒤 기본 세션 이름을 저장할 수 있으면 이후 호출에 --session을 붙인다. 자식 프로세스에는 HERDR_WORKSPACE_ID, HERDR_TAB_ID,
HERDR_PANE_ID를 넘기지 않는다. 수용 기준은 조율자 셸에 오래된 pane id가 있어도 Handrail 호출의 생략 대상이 그 pane으로 가지 않는 것이다.
status가 세션 이름을 주지 않으면 그 항목은 비워 두고, 추측한 세션 이름을 성공으로 기록하지 않는다.

상대에게 물을 것

1. 이번 성공만으로 CLI가 HERDR_ENV를 전혀 검사하지 않는다고 볼 것인지. 나는 skill 가드와 CLI 인증을 아직 구분할 뿐, 서버 구현은
   확인하지 않았다.
2. live 이름, pane, cwd가 기록과 같으면 workspace close와 send-keys까지 추가 동의 없이 허용할 것인지. 나는 기존 Herdr 실행 허가가 그
   범위를 포함한다고 본다.
3. status에 incarnation이 없는 지금, 소켓 경로와 protocol, pane, cwd로 충분한지. 그 넷이 같아도 프로세스가 바뀐 경우를 어느 오류로 남길
   것인지.

HERDR_ENV_ROUND1_COMPLETE_GROK
