# Cursor Grok 4.7 High 독립 검토 원문

Herdr 터미널의 완료 응답을 보존한 자료다. 화면 줄바꿈을 포함하며, 아래 판단은 검토자 원문이다. 채택·수정 여부는 `report.md`를 따른다.

REVIEW_COMPLETE_GROK

이번 세션은 사원관리 구현 자체가 끝까지 갔고, 카드 23·24·25는 최종 Done이다. 다만 사용자가 겪은 마찰은 구현 난이도가 아니라, 승인이 네
층으로 갈라진 채 한 층만 대화에 보이고 나머지는 host escalation과 worker 터미널로 새어 나온 데 있다. 초기 실패와 나중 성공은 시간상 따로
봐야 한다.

실행 모델은 Grok 4.7이다. 이전 backlog·permission 보고서는 읽지 않았다. 읽은 자료는 review-brief, manifest, 세션
01a10e66·01a10e6c·01a10e6f의 conversation/commands/escalation/contexts, 카드 23 댓글 105–151, 카드 24·25, herdr-state, checks-plan-23과
checks-task-24/25, 그리고 현재 워크스페이스의 permissions.py, permission_adapters.py, herdr_workflow.py, specs.py, kanban.py, cli.py,
run_preparation.py, authorization.md, workflow.md, herdr.md다. 셸은 읽기 전용 모드에서 막혀서 파일 읽기로만 봤다. 클릭 수는 자료에 없어서
추정하지 않았다. escalation 98건은 tool call 수다.

핵심 판단

1. 사용자가 실제로 고른 결정은 범위, 작업자, Grok effort, 브라우저 확인 후 Done이다. 명세 승인 문구는 조율자가 “구현해 달라”는 말을
   그대로 승인 기록에 접어 넣었고, Handrail grant/delegation은 이 Herdr 사이클에서 한 번도 호출되지 않았다.
2. 반복 마찰의 실체는 같은 질문을 여러 번 한 것이라기보다, Vikunja 네트워크, .git 쓰기, Handrail data 디렉터리의 worktree, worker
   샌드박스, raw herdr CLI가 서로 다른 승인 표면으로 나타난 것이다.
3. Frontend 첫 시작(00:23)은 Codex CLI 자체 업데이트 때문에 지시가 전달되기 전에 끊겼다. 00:46에 같은 카드 24·같은 worktree로 지시가
   다시 들어갔고, 01:04에 빌드가 통과했다. 앞의 실패와 뒤의 Done을 한 결함으로 묶으면 안 된다.
4. 워커 완료는 herdr finish인데, 부모 완료는 plan submit-review와 plan accept였다. kanban.accept_plan은 Herdr workspace를 닫지 않는다.
   캡처된 herdr-state에 closed_at이 없고, 사용자는 워크트리 정리를 다시 물었다.
5. Backend worker가 rm -rf node_modules package-lock.json && npm install 승인을 띄운 것은 worker 샌드박스에서 better-sqlite3 네이티브
   빌드가 막힌 결과다. 조율자가 Escape로 거절하고 manager 설치로 분리한 판단은 맞다. Herdr 시작 경로가 설치 정책을 타지 않아서, 그
   승인이 사용자 화면에 먼저 나타날 수 있는 구조다.

승인 여정

범위 합의는 대화에 있다. 23:42에 최소 CRUD, Express, 프론트/백 분리가 나왔고, 23:46에 계획 카드와 하위 보드, Codex gpt-6-luna low, Cursor
Grok 4.7이 지정됐다. 카드 23 설명과 댓글 105가 그 범위를 받는다.

명세 승인은 그 다음 사용자 발화 없이 끝났다. 댓글 109는 “사용자의 구현 지시에 근거해 부모 명세를 승인”한다고 적고, 같은 댓글은 하위
명세를 카드별 사용자 승인으로 남긴다고 해 놓고 댓글 110·111이 곧바로 24·25를 승인 등록한다. 다음 사용자 메시지는 00:33의 “High로
진행해줘”뿐이다. specs.approve는 빈 문자열이 아니면 통과하고, 그 문자열이 실제 명세 확인인지는 검사하지 않는다. Herdr start는
get_approval_record만 보고 워커를 띄운다. 그래서 “카드 만들어 구현해”와 “이 해시의 명세와 검사를 승인한다”가 코드에서 한 문장으로
합쳐진다.

Handrail의 재사용 권한은 이 사이클의 바깥에 있다. permissions.grant / delegate는 run start와 --delegated 하위 명세용이고,
herdr_workflow.py는 permissions 모듈을 호출하지 않는다. 세션 escalation에도 permissions 서브커맨드가 없다. 스킬은 Herdr에서도 기존 승인
경계를 지키라고 하지만, Herdr 구현은 그 저장소를 읽지 않는다. 결과적으로 네트워크·설치·검증은 매번 Codex host escalation의
justification으로 다시 설명됐다.

Host escalation은 98건이다. 그중 handrail.py prefix가 76건, env 6건, raw herdr 4건, npm 3건, git 2건, node 2건, curl 2건, cursor-agent
models 1건, codex --version 1건이다. 합이 97이라 나머지 1건의 prefix는 이 묶음으로 특정하지 못했다. 첫 요청(rollout 222)의 이유는
샌드박스에서 Vikunja GET /projects/18/tasks가 VIKUNJA_CONNECTION_FAILED인 것이다. 같은 prefix가 이후 task create, area create, task
comment, spec create, herdr start, herdr review, plan accept까지 덮는다. prefix가 세션에 붙으면 클릭은 줄지만, 사용자가 승인한 문장(“읽기
전용 task list”)과 이후 실제로 허용되는 명령(완료 처리 포함)이 달라진다. prefix가 안 붙으면 76개의 Handrail 호출이 각각 승인 카드가
된다. 어느 쪽이었는지는 이 evidence로 확정할 수 없다.

Worker UI 승인은 별도 층이다. 00:38 Backend 터미널이 삭제와 설치를 한 명령으로 승인받으려 했다. 조율자는 댓글 136에 거절을 적고 herdr
keys로 Escape를 보냈다(댓글 137, rollout 923·930). 사용자가 그 Cursor 카드를 봤는지는 기록이 없다. Frontend Codex는
approval_policy=on-request로 떠 있었고, 빌드 실패는 권한 프롬프트가 아니라 vite: command not found와 이후 worktree의 읽기 전용 오류였다.

마지막 사용자 승인은 깨끗하다. 01:10 댓글 151로 Review 제출, 01:14에 사용자가 서버 실행을 요청, 01:17 “잘 실행되는 것을 확인했어 이번
개발카드를 done으로 전환해”가 plan accept --approval에 그대로 들어갔다. 이 문장은 실제 사용자 발화와 일치한다.

반복해서 나타난 마찰

설정은 세션이 두 번 갈라졌다. 01a10e66에서 사용자는 토큰을 채팅에 붙였고, 조율자는 숨김 입력을 요구하며 폐기를 안내했다. 이건 스킬이 지킨
경우다. 다만 안내 명령이 0.5.0+codex.…/scripts/handrail.py 절대경로라, 사용자는 !를 붙여 다시 보냈다. 01a10e6c의 project bind는
대화형이다. 샌드박스 안에서 프로필 5를 고른 뒤 VIKUNJA_CONNECTION_FAILED로 끊겼고, escalation은 tty 1건이다. 사용자는 exit 후 명령을
채팅에 붙여 넣었다. project bind에는 --profile, --project-id, --view-id, --states가 있는데, 스킬은 대화형 선택만 안내한다.

모델 effort는 23:49에 이미 블로커였는데, 사용자에게 보이는 질문은 00:32 메시지 끝이다. 그 사이 조율자는 명세 승인, 기준 커밋, Frontend
시작, stall, agent_not_found 복구 실패를 진행했다. 00:33에야 “High로 진행해줘”가 온다. 스킬은 모델을 대신 고르지 말라고 하므로 질문은
맞다. 질문을 워커 시작보다 앞에 두지 않은 것은 조율 순서 문제다.

상태 설명도 사용자가 끌어내야 했다. 00:57 “개발이 완료된거야?”, 00:58 “그럼 어떻게 해야해?”, 01:18 “워크트리는 정리된건가?”. 그 시점의
보드 상태는 댓글 47개가 부모 카드 23에만 있고 24·25 댓글은 0건이다. herdr_workflow._event는 이벤트 전문을 Vikunja 댓글로 쓰고, 댓글
111·113처럼 명세 전문이 댓글에 다시 들어간다. 스킬은 댓글을 짧게 두라고 한다. 구현은 매 상태 전이를 네트워크 쓰기로 만든다. 네트워크가
샌드박스 밖이면 그 쓰기마다 Handrail escalation 이유가 하나 더 생긴다.

실행 확인은 Review 제출 후에 사용자가 다시 요청했다. 01:10 조율자는 스모크 테스트를 끝내고 서버를 끈 뒤 “개발은 완료”라고 했다. 댓글
151은 사용자 검토를 요청하는 문장이다. 01:14 실행 요청에서 3001은 이미 점유되어 3201로 바뀌었다. 사용자는 01:17에 화면을 확인하고 Done을
말했다. 검토 대기와 “이미 끝남”이 같은 턴에 겹친 것이다.

권한 경계별 UX

조율자 Codex의 실효 프로필은 세션 내내 approval_policy=on-request, 프로젝트 쓰기, .git 읽기 전용이다. git commit은 샌드박스에서 Read-only
file system으로 실패하고(commands line 553), rollout 560에서 prefix rtk git commit으로 나갔다. Herdr는 커밋된 HEAD 없이 worktree를 못
만든다(HERDR_SOURCE_DIRTY). 기준 커밋 한 번은 이 호스트 정책에서 예상되는 승인이다.

Worktree는 config.data_dir()/projects/<workspace>/herdr-worktrees/ 아래다. 조율자 쓰기 허용 경로에는 프로젝트와 /tmp만 있다. Frontend
빌드는 의존성 설치 뒤에도 Vite가 worktree 안에 임시 파일을 쓰다 막혔고, rollout 1574에서 그 경로 쓰기를 따로 승인받았다. 홈 전체를 여는
해결과는 별개로, Handrail이 검사와 설치를 올려 두는 디렉터리가 조율자 샌드박스의 쓰기 루트 밖이다.

Worker 경계는 더 좁다. Cursor는 --sandbox enabled이고, adapter는 바깥 샌드박스를 들어 올리지 못한다(permission_adapters.HOST_BOUNDARY).
better-sqlite3 빌드 실패는 그 경계다. run_preparation.prepare_dependencies의 install은 execution_boundary: orchestrator-host와 승인된
argv가 있을 때만 manager가 실행한다. Herdr start는 이 준비를 호출하지 않아서, 워커가 먼저 npm install과 삭제를 시도하고 조율자가 사후에
막는다.

복구 경계는 Handrail CLI 밖으로 나갔다. recover는 worker status가 unknown일 때만 동작하고, 그 안에서 agent_get을 호출한다. 수집 결과가
agent_not_found이면 이 API는 막힌다(00:24 commands). 조율자는 rollout 1064에서 herdr agent start work-24를 직접 호출했다. 스킬은 관리
인터페이스 안에서 복구하라고 한다. 제품은 agent가 사라진 뒤 같은 worktree에 다시 붙는 명령을 제공하지 않는다. 그래서 복구가 handrail.py
prefix와 다른 herdr prefix가 된다.

preflight는 Vikunja URL, data 디렉터리, worktree 저장 위치를 읽기 전용으로 보여 주고 OS 규칙은 고치지 않는다. 이 세션은 doctor의 연결
실패 뒤 task list escalation으로 바로 들어갔고, 시작 전에 필요한 쓰기 루트와 설치 경계를 한 장으로 보여 주지 않았다.

기능 개선

P1. Herdr 완료가 workspace를 닫게 할 것. 현상: 카드는 01:17:49에 Done인데 herdr-state workspace에는 closed_at이 없고 worktree
work-24·work-25가 남는다. 원인: 워커 수명은 herdr accept → _close_space인데, 실행된 명령은 plan accept → kanban.accept_plan이다. plan
accept는 Vikunja Done과 approval 문장만 기록한다. 근거: escalation line 1968, cli.py의 plan/herdr dispatch 분기, herdr_workflow.accept,
댓글 151, 대화 line 1981–1998. 제안: 열린 Herdr space가 있으면 plan accept/plan submit-review가 Herdr 명령으로 이어지거나, 닫힘을
건너뛴다는 오류를 내고 멈추게 한다. 수용: 이 세션과 같은 순서면 Done 기록과 workspace.closed_at이 같이 남고, 사용자 답변 전에 “pane은
닫히고 git worktree는 유지된다”가 상태에 나온다. 분류: 제품 결함에 조율자의 명령 선택이 겹친 것.

P1. 지시 미전달 복구가 agent 소실 이후에도 관리 명령으로 끝날 것. 현상: 00:23 Frontend는 Codex 0.160.0→0.160.1 업데이트 로그만 보인 채
agent_prompt_stalled(5초, idle)와 agent_not_found가 됐다. 00:46에야 빈 프롬프트를 확인하고 not-delivered로 맞춘 뒤 지시가 갔다. 원인:
stall 감지는 Herdr이고, Handrail recover는 살아있는 agent의 화면을 요구한다. 근거: commands line 623–657, 댓글 114·145–149,
herdr_workflow.recover. 제안: 같은 worktree·같은 work-<id>에 대해 “agent 없음, 화면은 빈 프롬프트”를 증거로 받는 재연결을 herdr recover
안에 둔다. 자동 업데이트 중이면 5초 stall을 실패로 확정하지 않는다. 수용: raw herdr agent start 없이 카드 24와 같은 경우가 herdr recover
한 번으로 not-delivered 후 재전달된다. 분류: 제품 결함. CLI 업데이트 자체는 host 동작이다.

P1. 명세 승인을 구현 지시와 분리할 것. 현상: 댓글 109–111이 사용자 추가 답변 없이 부모·자식 명세를 승인했다. 원인: specs.approve는 비어
있지 않은 문자열만 요구하고, Herdr start는 그 기록의 출처를 사용자 턴과 대조하지 않는다. 근거: specs.py 80–88행, 댓글 109–111, 사용자
턴은 23:46 다음이 00:33. 제안: 승인 명령이 명세 해시, 검사 ID, 한 줄 요약을 보여 주고, 직전 사용자 메시지에 그 해시에 대한 확인이 있을
때만 approval_kind=user로 기록한다. Herdr에서는 부모 위임이 있을 때만 --delegated를 허용한다. 수용: “구현해 달라”만으로는 spec approve가
실패하고, 실패한 채 herdr start도 실패한다. 분류: 제품 결함. 이번 조율자는 그 빈틈으로 승인을 기록했다.

P2. 검사 실행 위치를 의존성이 있는 트리와 맞출 것. 현상: worker 빌드는 worktree에서 vite 부재로 실패하고, 통합 뒤 canonical
frontend_build도 node_modules 없이 exit 127이었다. 댓글 147·148에 verification_started가 두 번 찍힌 뒤 149에서 통과했다. 원인: 자식
검사는 working_directory: frontend, 부모 검사는 npm --prefix frontend이며, 둘 다 설치 준비를 포함하지 않는다. 근거: checks-task-24,
checks-plan-23, herdr-state의 failed check와 이후 passed evidence, 대화 line 1671. 제안: command check에 준비 단계(이미 승인된 install
argv)를 묶거나, 실패한 첫 시도를 검증 시작 이벤트로 남기기 전에 준비 실패로 구분한다. 수용: 의존성 없는 첫 실행이 “검사 실패”와 “검증
시작”으로 두 번 기록되지 않고, 통과 기록은 설치 이후의 exit 0만 담는다. 분류: 제품 결함. 통과 자체를 조작한 기록은 아니다. 나중 출력에
Vite 5.4.21, 32 modules가 있다.

P2. 네이티브 의존성을 워커 시작 전에 manager가 설치할 것. 현상: Backend는 코드를 냈지만 HTTP·재시작 저장은 리뷰 시점(댓글 130, 00:50)에
미검증이었고, 설치는 워커의 삭제 겸 설치 프롬프트 이후다. 스모크는 01:09 댓글 150에야 올라온다. 원인: Herdr start가
prepare_dependencies를 타지 않는다. 근거: run_preparation.py 91–106행, authorization.md의 orchestrator-host 경계, 댓글 136–137. 제안:
카드 검사나 package manager가 네이티브 빌드를 포함하면, 워커 시작 전에 승인된 argv만 manager가 실행하고 워커 지시에는 그 명령을 다시 하지
말라고 넣는다. 수용: better-sqlite3 류 작업에서 worker 터미널에 rm -rf && npm install 승인 카드가 나오지 않고, 설치 승인은 manager 쪽 한
건으로 남는다. 분류: 제품 결함. Escape로 거절한 것은 조율자가 경계를 지킨 행동이다.

사용성 개선

P1. 계획 시작 전에 호스트 준비 한 장. 현상: 연결 실패, .git 읽기 전용, data 디렉터리 빌드 실패, 모델 카탈로그 EPERM이 작업 중간에 각각
승인 문장으로 나타났다. 원인: preflight가 있어도 시작 절차가 그것을 사용자 확인으로 고정하지 않는다. 근거: doctor 실패(commands line
215), contexts의 프로필, rollout 222·384·560·1574, cli.py preflight. 제안: plan register 다음 화면에 “Vikunja 호스트 접속, 이 저장소 git
커밋, Handrail data 디렉터리의 이 계획 worktree 쓰기, 승인된 npm argv”만 나열하고, 그 범위의 세션 prefix를 한 번 받는다. 홈 전체 쓰기나
샌드박스 해제는 넣지 않는다. 수용: 같은 계획에서 위 네 경계 밖의 명령은 여전히 개별 승인이고, 네 경계 안의 Handrail·git·npm은 새
justification마다 다시 묻지 않는다. 분류: 제품 설계. 호스트가 prefix를 기억하는지와 별도로, 제품이 그 목록을 먼저 제시해야 한다.

P1. 부모 카드 댓글을 사용자 상태와 기계 저널로 나눌 것. 현상: 댓글 47건이 한 카드에 있고, 사용자는 완료 여부를 채팅에서 다시 물었다.
원인: _event가 댓글 쓰기를 상태 전이를 거치는 조건으로 두고, 본문에 명세 전체를 넣는다. 근거: herdr_workflow._event 117–157행, 댓글
105–151, 카드 24·25 comment 0. 제안: 사용자에게는 단계 전이당 한 줄(누가, 무엇을, 다음 사용자 행동)만 남기고, 이벤트 전문은 로컬
herdr.json에 둔 뒤 주기적으로 한 댓글로 동기화한다. 읽기 전용 collect는 지금처럼 댓글 생략. 수용: 같은 작업이면 부모 댓글이 단계당 1개
수준이고, 카드 24·25를 열어도 “증거는 부모 댓글 몇 번”이 보인다. 분류: 제품 결함이자 스킬(짧은 댓글)과 구현의 불일치.

P1. 블로커 질문을 워커 시작 전에 고정할 것. 현상: Grok 4.7 effort가 45분 가까이 사용자 질문으로 나오지 않았다. 원인: 카탈로그에 effort별
ID가 있는데 herdr assign이 모호한 모델명을 거절하지 않고, 스킬도 “긴 작업 전에 물어라”를 시작 조건으로 강제하지 않는다. 근거: 대화 line
407과 784, 사용자 턴 00:33, 댓글 112. 제안: 모델 ID가 카탈로그에서 여러 effort로 갈라지면 assign이 선택지와 함께 실패한다. 스킬에는
미해결 선택 동안 herdr start와 기준 커밋 escalation을 하지 않는다고 적는다. 수용: 이번처럼 effort가 비어 있으면 Frontend 시작 로그가
생기기 전에 사용자 질문이 대화에 있다. 분류: 스킬 공백과 조율 순서. assign이 모호한 모델을 받은 것은 제품 구멍이다.

P2. 연결과 바인딩을 채팅에 붙이지 않게. 현상: 토큰이 채팅에 들어왔고, 바인딩은 새 세션에서 대화형으로 실패했다. 원인: setup은 숨김 입력을
요구하면서 버전 디렉터리 절대경로를 사용자가 복사하게 하고, bind의 비대화형 플래그를 절차에서 빼 두었다. 근거: 01a10e66 대화 line
125–130, 01a10e6c commands line 84와 escalation line 89, setup.md. 제안: 플러그인이 짧은 안정 명령(handrail setup, handrail project
bind)을 제공하고, 프로필을 고른 뒤에는 --profile과 프로젝트·뷰 ID로 재실행할 수 있는 한 줄을 보여 준다. 토큰 문자열이 사용자 메시지에
보이면 명령 실행 없이 폐기 안내만 한다. 수용: 설정 안내가 cache 해시 경로를 포함하지 않고, 바인딩 재시도가 대화형 프롬프트를 다시 열지
않는다. 분류: 사용성. 토큰을 실행에 넣지 않은 것은 올바른 조율이다.

P2. Review 제출이 사용자가 열 주소와 남은 프로세스를 같이 말할 것. 현상: 제출 직후 서버가 꺼져 있어서 사용자가 실행을 다시 요청했고, 기본
포트는 이미 쓰이고 있었다. 원인: 스모크를 조율자 임시 프로세스로 끝내고, 제출 댓글은 검사 ID만 말한다. 근거: 대화 line 1892·1901·1923,
댓글 150–151. 제안: submit-review 출력에 통합 HEAD, 통과한 check, 그리고 “검토용 서버는 꺼져 있음 / 켜려면 이 포트”를 넣는다. 포트 충돌은
기존 프로세스를 죽이지 않고 대체 포트를 상태에 적는다. 수용: 제출 메시지 안에 사용자가 열 URL이 있거나, 서버가 꺼져 있다는 문장이 검사
결과와 같이 있다. 분류: 스킬 문구와 제출 명령의 출력 공백.

권한 요구를 줄이는 방안

짧게는 계획마다 준비 목록을 한 번만 받는다. 대상은 바인딩된 Vikunja origin, 이 저장소의 git 커밋, 이 계획의 Handrail worktree 디렉터리,
카드에 적힌 설치 argv다. 이미 있는 preflight 결과를 그 목록으로 쓰고, Codex prefix는 handrail.py 전체가 아니라 그 계획에 필요한
서브커맨드로 좁힌다. 댓글 동기화는 로컬에 모았다가 한 번 보낸다. effort·명세 확인처럼 사람만 답할 질문은 그 목록보다 먼저 묻는다.

중간에는 Herdr가 grant/delegation을 읽게 한다. 설치는 execution_boundary=orchestrator-host인 argv만, 칸반 전이는 workflows에 kanban이
있을 때만 재사용한다. 위임은 부모 명세 해시와 사이클에 고정하고, reopen은 새 위임이 필요하다. 이 저장소는 이미 permissions.py에 있다.
Herdr가 우회하기 때문에 세션이 host 문장으로 되돌아갔다. 복구와 완료도 herdr recover·herdr accept로만 닫히면 raw herdr와 plan accept
prefix가 사라진다.

한계는 분명하다. 바깥 샌드박스는 provider 설정으로 열리지 않는다. prefix를 세션이 기억하지 않는 host에서는 준비 목록도 한 번의 클릭으로
끝나지 않는다. 네이티브 빌드와 브라우저 확인은 그 목록에 넣어 둔 argv와 포트 밖으로 나가면 다시 승인이 필요하다. 사용자 홈 전체를 쓰기
가능하게 두거나 샌드박스를 끄는 방식은 이 세션의 실패를 줄이는 설계가 아니다.

단정하지 못한 것

실제 승인 클릭 수, prefix가 중간에 자동 허용됐는지, 사용자가 Cursor의 삭제 겸 설치 카드를 봤는지는 evidence에 없다. plan accept가
workspace close를 시도하지 않은 것은 코드와 closed_at 부재로 볼 수 있고, Herdr 서버가 pane을 따로 닫았는지는 캡처만으로 알 수 없다. 5초
stall 임계값이 Handrail 코드가 아니라 Herdr 응답인 것은 오류 문자열로 확인된다. 변경하려면 Herdr 쪽 확인이 필요하다. 댓글 150의 HTTP
201/409/200/204와 재시작 저장은 조율자 기록이며, 이 검토에서 다시 실행하지 않았다. 01:04 이후 빌드 통과와 01:17 Done은 그 기록과 카드
done_at으로 확인된다. 00:23의 Frontend 실패를 최종 품질 실패로 보면 안 된다.
