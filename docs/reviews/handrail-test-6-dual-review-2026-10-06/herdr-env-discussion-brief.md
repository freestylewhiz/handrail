# HERDR_ENV와 Handrail 외부 조율 토의

사용자는 기존 두 검토자와 다음을 논의해 달라고 요청했다: HERDER_ENV로 언급되는 문제의 실제 상황, 영향, 무시 가능한지, 조율자가 agent와 소통하고 개발 진척을 관리하는 관점의 제품 수정 사항. 실제 설치 skill에서 확인한 이름은 HERDR_ENV다.

기존 Codex Astra High / Cursor Grok 4.7 High 세션을 재사용한다. 읽기 전용 분석이다. 프로젝트·카드·설정·환경·파일 변경, 테스트·서버·설치, env 위조, worker 조작, 추가 에이전트 실행을 하지 않는다. 필요한 파일 읽기만 한다. 명령을 사용하면 rtk 접두사를 붙인다.

## 근거

- `/tmp/herdr-control-skill-20261006.md`: 설치된 Herdr 0.9.1 CLI skill. 첫 부분에서 HERDR_ENV=1이 아니면 중지하도록 지시한다. 뒤에는 caller context, --current, explicit IDs, session/server별 ID scope, remote routing, prompt wait의 5초 activity gate, timeout의 의미가 있다.
- 이 폴더의 `herdr-env-observations.json`: 이번 조율자의 알려진 env와 실제 CLI 관찰. 조율자는 HERDR_ENV/HERDER_ENV/HERDR_WORKSPACE_ID/HERDR_TAB_ID/HERDR_PANE_ID가 모두 없지만 기존 이름을 명시한 agent list/get/read/prompt가 성공했다. 명시적으로 사용자가 기존 Herdr 세션과 토의하라고 승인했다. env 값을 가짜로 넣지 않았다. 이것은 설치 skill의 지침과 CLI 기술 요건을 구분하는 근거이며 외부 제어가 항상 안전하다는 증거는 아니다.
- `handrail/herdr_transport.py`: __init__/session, _argv, _run subprocess env inheritance, 명시 ID 사용, agent_prompt/agent_read.
- `handrail/herdr_workflow.py`: _client, _plan, _ensure_space, worker identity, start, _send_instruction, collect, recover, status, review/finish.
- `plugins/handrail/skills/handrail/references/herdr.md`, `docs/herdr-workflow.md`, `docs/worker-authorization-policy.md`, 기존 세션 evidence와 report.

## 구분할 것

1. HERDR_ENV 존재는 pane 내부에서 시작한 프로세스라는 문맥 신호인지, 연결 주소인지, 실제 인증·권한인지. 확인한 자료 수준을 표시할 것.
2. in-pane caller 제어와 explicit external orchestrator 제어를 구분. generic skill의 외부 중지 규칙을 Handrail이 무조건 따를 때와 무시할 때 각각 어떤 문제가 있는지.
3. ENV 미설정 / 세션·서버 선택 잘못됨 / socket EPERM / agent 없음 / prompt timeout / worker idle / Kanban 완료는 별개다. 실제 증거 없는 인과를 연결하지 말 것.
4. 명시 workspace·pane·agent 이름만 있으면 충분한가? 다른 server/session에서 ID나 이름이 같거나 프로세스가 교체될 수 있다. cwd·provider session·실행시도 등 identity 검증을 고려할 것.
5. 현재 HerdrClient(session=...)를 flow가 실제 설정하는지, env inheritance 때문에 다른 세션으로 붙을 가능성, startup에서 기록하는 식별자와 이후 재검증의 차이.
6. 상태·화면 읽기와 지시 전송·키 입력·workspace 종료를 구분. 원격/서버 식별 정보·기능 점검과 명시 승인으로 외부 모드를 지원할 수 있을지. 현재 API가 서버 incarnation을 노출하지 않는다면 없는 필드를 만들어 해결됐다고 하지 말 것.

## 1차 출력

1000~1400단어 한국어 이내. 처음 HERDR_ENV_ROUND1_FINAL_ASTRA 또는 GROK, 끝 HERDR_ENV_ROUND1_COMPLETE_ASTRA 또는 GROK.

- 한 문장 결론과 발생 상황 표.
- 무시 가능/불가 판단 규칙. 지침 충돌과 기술적 실패를 구분.
- 조율자의 소통·진척 관리에서 수정할 백로그(우선순위, 근거 함수, 수용 기준).
- 상대 모델에게 요청할 반론 3개.

이후 서로의 1차 의견을 전달해 2차 교차 토의를 진행한다. 사용자에게 추가 동의를 반복 요구하는 방향으로 자동 결론을 내리지 말고 기존 사용자 지시와 정확한 제어 범위 재사용을 우선한다.
