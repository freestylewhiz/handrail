# HERDR_ENV 토의: 조율자의 추가 근거

2026-10-06. 이 문서는 읽기 전용 코드·API 계약 조사이며 제어 실패를 재현하는 실험은 하지 않았다.

## 설치본에서 확인

- Herdr client/server 0.9.1, protocol 22, endpoint_protocol_generation 1, 호환 상태 yes. `endpoint_protocol_generation`은 호환성 정보이며 서버 재시작마다 변하는 instance ID로 간주하지 않는다.
- 조율자 프로세스의 HERDR_ENV/HERDER_ENV/HERDR_PANE_ID/HERDR_TAB_ID/HERDR_WORKSPACE_ID 및 HERDR_SESSION/HERDR_SOCKET_PATH/HERDR_CONFIG_PATH는 모두 미설정이다.
- 읽기 전용 session list에는 현재 default session 하나가 running으로 보이며, status의 실제 socket은 `/home/dyhwang23/.config/herdr/herdr.sock`이다. 알려진 검토 agent 이름을 명시한 list/get/read와 사용자가 요청한 토의 prompt가 성공했다. 이는 이 연결의 관찰이며 모든 외부 연결을 보장하지 않는다.
- 설치된 schema를 `/tmp/handrail-herdr-api-schema-20261006.json`에 저장했다. AgentInfo에는 workspace/tab/pane/terminal ID, revision, state_change_seq, 선택적 provider agent_session과 cwd가 있다. SessionSnapshot에는 version/protocol과 상태 목록이 있지만 server_instance_id/epoch 필드는 확인되지 않았다.
- AgentPromptParams는 target/text/wait, AgentSendKeysParams는 target/keys다. 별도 expected provider-session/revision 인수는 확인되지 않았다. 따라서 클라이언트 get 후 send 사이 교체 경합을 완전히 막는 CAS 계약이 있다고 주장하면 안 된다.

## 공식 문서에서 확인

- CLI reference는 HERDR_ENV를 pane 프로세스 내부 신호, HERDR_SESSION을 named session 선택, HERDR_SOCKET_PATH를 socket override로 구분한다. https://herdr.dev/docs/cli-reference/#environment-variables
- Socket API 문서는 통합 계층을 pane 내부 agent skill / 단순 조율용 CLI wrapper / custom client용 raw API로 구분한다. 따라서 pane 내부 skill의 사용 조건을 모든 외부 CLI 호출의 기술적 전제와 동일시할 수 없다. https://herdr.dev/docs/socket-api/#choose-an-integration-layer
- 문서의 socket 선택 순서는 explicit --session, HERDR_SOCKET_PATH, HERDR_SESSION, default다. optional pane_id가 없는 일부 메서드는 focused pane을 선택한다. https://herdr.dev/docs/socket-api/#socket-paths
- agent.wait는 해석된 pane occupant를 고정한다. agent.prompt의 wait는 제출과 대기를 한 요청으로 묶는다. 이 보장은 별도 사전 get 결과의 identity와 원자적으로 비교하는 expected-identity 인수가 있다는 뜻은 아니다. https://herdr.dev/docs/socket-api/
- snapshot은 관찰 시점의 상태이며 재접속 후 다시 조회해야 한다. 이벤트는 캐시 갱신을 촉발하는 자료로 사용하고 snapshot 위에 무조건 재생하지 않는다. https://herdr.dev/docs/socket-api/#event-subscriptions
- v0.9.1 main.rs에는 HERDR_ENV=1에 따른 중첩 TUI 실행 제한이 있다. CLI 하위 명령 처리와 TUI launch 경로를 구분해야 한다. 변수를 수동 주입하는 것은 실제 pane 문맥이나 권한을 만들어 주지 않는다. https://github.com/herdrdev/herdr/blob/v0.9.1/src/main.rs

Herdr /llms.txt와 /agent-guide.md 직접 가져오기는 실패했으나 공식 HTML 문서와 버전 고정 GitHub 소스를 확인했다. 설치 CLI help/schema를 현재 환경의 계약 근거로 우선한다.

## Handrail 소스에서 확인

- HerdrClient는 session 인수를 지원하지만 flow._client는 인수 없이 만든다. _run은 subprocess.run에 env를 별도로 넘기지 않아 호출 프로세스 환경을 상속한다.
- Handrail managed 제어는 이미 다수 명령에서 명시 workspace/pane/name을 사용한다. 현재 모든 동작이 focused pane에 의존한다는 주장은 잘못이다.
- startup은 pane/worktree/model을 기록하지만 반환 agent_session/terminal_id/revision을 실행 identity로 저장하지 않는다. 이후 collect/prompt/keys는 저장 이름으로 호출하고 전체 identity를 매번 비교하지 않는다.
- recover는 observed agent를 가져와 반환하지만 저장 pane/session identity를 정합화하지 않는다. status는 원격 카드와 저장 Herdr 상태를 반환하며 실제 worker 상태를 조회하지 않는다.
- _send_instruction은 agent_not_ready처럼 입력 전 거절된 경우만 재시도한다. stalled/timeout을 무조건 재전송하지 않는 방어는 이미 있다. 이 장점을 보존해야 한다.
- handrail_test_6 수집 evidence에서 HERDR_ENV/HERDER_ENV 문자열은 검색되지 않았다. 이번 일반 문제 분석을 원본 test_6의 모든 EPERM/timeout 원인으로 소급해 단정하지 않는다.

## 토의에서 유의할 점

외부 모드는 제품 개선안이다. 현재 구현이 연결·신원·권한 계약을 이미 모두 충족한다고 말하지 않는다. 사용자 지시가 충분한 동일 제어 범위는 재승인하지 않되, 대상 연결이나 실행체가 달라지면 재식별한다. 키 입력은 사용자가 요청한 모든 개발 행위에 대한 포괄 승인 수단이 아니다. observed UI와 기존 승인 범위에 맞는 응답인지 확인한다.
