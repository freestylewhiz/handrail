# HERDR_ENV 2차 교차 토의

상대의 `herdr-env-*-round1.md`와 `herdr-env-source-notes.md`를 읽고 700~1100 단어 이내 한국어로 최종 의견을 보고한다. 읽기 전용 토의다. 변경·실험·네트워크·worker 조작은 하지 않는다. 처음 HERDR_ENV_ROUND2_FINAL_ASTRA 또는 GROK, 마지막 HERDR_ENV_ROUND2_COMPLETE_ASTRA 또는 GROK.

1. 상대가 제기한 세 질문에 답하고 합의·반론을 구분하라. 공식 문서는 pane 내부 skill, 외부 CLI 조율, raw API를 서로 다른 통합 계층으로 구분한다. 미설정이 정상인 외부 모드를 만들되 현행 스킬을 무조건 무시하라는 결론은 피한다.
2. 읽기 성공과 제어 대상 일치가 모든 키 입력·종료의 권한인가? Grok 1차의 기존 Herdr 실행 허가면 키 입력·종료도 반복 동의 없이 가능하다는 표현을 작업별로 제한하라. 이번 사용자의 기존 검토자와 토의 요청은 대화는 포함하지만 해당 세션 종료, 새 능력 승인, 임의 파괴 명령 승인은 포함하지 않는다. 반대로 원래 관리 계획의 승인된 cleanup 등은 기존 권한을 재사용할 수 있다.
3. AgentInfo에는 provider agent_session, terminal_id, revision, state_change_seq가 있지만 모두 영속 서버 incarnation은 아니다. AgentPromptParams에는 expected identity CAS가 없다. 사전 get 비교와 Herdr 자체 wait occupant pin의 차이를 정확히 설명하라. 문자열 이름/cwd만으로 충분하다는 주장은 보완하라. 현재 schema에 없는 필드를 있다고 하지 말 것.
4. session routing 고정은 P1인가 P2인가? HerdrClient(session=...) 지원은 있지만 flow._client에서 미사용, subprocess 환경 상속은 사실이다. manager가 pane 내부/외부 어느 쪽에서 실행돼도 동일한 계획이 같은 endpoint로 이어지도록 할 정책을 적어라. default 세션에 named 옵션을 추측해 적용하거나 필요한 모든 환경을 무조건 지우지 말 것.
5. 실제 managed 명령은 이미 대부분 명시 ID를 사용한다. 모든 현재 동작이 focus에 의존한다고 과장하지 말고, generic raw skill의 위험과 관리형 transport의 identity 공백을 구분하라.
6. start/prompt가 성공 결과의 blocked 등을 읽지 않고 running을 저장하는 부분, collect가 visible만 반환하는 부분, status가 live worker를 조회하지 않는 부분을 소스와 대조해 최소한의 진척 계약을 제안하라. agent idle/done 및 prompt wait timeout을 업무 완료/실패와 동일시하지 말 것. 타임아웃 후 자동 재전송 방어는 이미 있으니 보존할 것.

최종 보고는 사용자 질문에 직접 답하라: 어떤 상황에서 언급되는가, 어떤 실제/잠재 문제가 생기는가, 무엇을 무시할 수 있고 무엇은 확인해야 하는가, Handrail이 우선 수정할 3~5개 항목. 미확정 원인은 미확정으로 남기고 이번 test_6 실패를 환경변수 때문이라고 소급해 단정하지 않는다.
