# Cursor Grok High · Worktree 배치 교차 토의 최종 의견

+WORKTREE_ROUND2_FINAL_GROK

Astra의 세 질문

B를 기본으로 두지 않는 쪽에 동의해. gitignore 밖의 IDE, watcher, 패키징 간섭은 도구마다 달라서 Handrail이 한 번 테스트로 닫을 수 있는
조건이 아니다. 소스 노트도 .gitignore가 Docker context를 빼 준다고 보장하지 않고, Node가 상위 node_modules를 찾을 수 있다고 적는다. 그
제외 설정을 저장소마다 유지하는 비용은 사용자 프로젝트에 남는다. 그래서 B는 “간섭을 감수한다”는 명시적 선택일 때만 허용하는 게 맞다.

project-only sandbox에서 C의 초기 설정이 B의 장기 간섭보다 크다고 볼 사용자군은 test_6만으로 확정하지 않겠어. 그 세션은 저장소 쓰기와
.git 읽기 제한이 동시에 있었고, 외부 worktree 쓰기와 common dir 쓰기는 다른 실패였다. 그 환경에서 C도 저장소 밖이면 호스트 경로 승인이 한
번 필요하다. B로 기본을 바꿀 조건은 “외부 영속 루트를 등록할 수 없고, 사용자가 그 저장소의 도구 간섭을 승인 문구로 남긴 때”로 한정한다.
그 전에도 기본 전환은 하지 않는다.

기존 실행 경로를 고정하고 새 실행만 새 배치를 쓰는 정책에 동의해. Review 중 자동 이동은 하지 않는다. 이동을 허용하려면 사용자 동의, Git
관리 명령으로 맞춘 worktree 등록, private pin 갱신, 같은 baseline의 fingerprint 재확인이 모두 있어야 한다. 디렉터리만 옮기는 것은 그
범위가 아니다.

무설정 동작과 신규 권장 배치

이 둘을 나누면 합의할 수 있다. 설정이 없으면 A를 유지한다. 신규 사용자에게 보여줄 권장 구조는 C다. canonical checkout은 <개발루트>/app,
작업 소스는 <개발루트>/.handrail-worktrees/<workspace-id>/…처럼 checkout 밖의 영속 경로는 사용자가 이름을 남긴 뒤 쓴다. 토큰, lock, run
기록, herdr 상태는 XDG에 둔다. worker 쓰기 범위는 그 카드의 worktree 하나다.

C를 모든 환경의 무설정 기본값으로 만드는 주장에는 반대해. 승인된 개발 루트 기록이 없으면 A를 보존한다. 부모가 있거나 OS상 쓰기 가능하다는
사실만으로 C를 고르지 않는다. os.access나 0o700은 sandbox 허용을 증명하지 않는다. 호스트 적용은 그 pin된 경로에서 worktree 생성이
성공하거나, 거부가 그대로 보고되는 것으로 확인한다. 실패하면 위치를 바꾸지 않는다.

조율자의 “저장소 안을 기본, 홈은 옵션”에는 동의하지 않아. B가 project-only sandbox에서 내용 쓰기를 이미 열린 저장소 권한 안에 두는 이득은
있다. 1차에서 그 이득을 우회나 숨김으로 단정한 것은 정정한다. 그 이득이 있어도 기본값의 근거가 되지 않는다. common dir, private 상태,
설치 네트워크는 위치에 따라 사라지지 않는다.

project-only sandbox에서 A와 C가 모두 막힐 때

첫 계획 시작에서 한 번만 차이를 보여 준다. 보여줄 자원은 지금 쓰려는 A 경로, Git common dir, private 상태 경로, 그리고 권장안으로
제시하는 C의 빈 자리다. 매 계획마다 다시 묻지 않고, B나 /tmp로 바꾸지도 않는다. 사용자는 셋을 고른다. A 경로가 열리도록 호스트를 맞춘 뒤
같은 경로로 재시도한다. 또는 정확한 C 디렉터리 하나를 private 설정에 등록한다. 부모 전체를 권한 범위로 넓히지 않는다. 또는 이 저장소에
한해 B를 명시적으로 고르고, 도구 간섭을 감수한다는 문장을 승인 기록에 남긴다.

그 다음 작업 디렉터리는 같은 pin 아래이고 기록이 그 루트를 포함하며, 실제 쓰기가 성공할 때만 재질문 없이 진행한다. 쓰기가 거부되면
중단하고 호스트가 적용되지 않았다고 말한다. 넓은 명령 prefix를 재사용 계약으로 쓰지 않는다. 재사용 단위는 기록된 루트와 검증된 작업
범위다. 사용자 의도 문장, private 기록, 호스트 적용 결과는 서로 대신하지 않는다.

B와 제품 규칙

B가 Git linked worktree의 논리적 독립을 반드시 깨지는 않는다. 별도 index와 HEAD, 공유 object store는 경로가 checkout 안이어도 유지될 수
있다. 제품 규칙과 충돌하는 조건은 따로다. worktree 경로가 canonical checkout의 하위일 때 물리적으로 사용자 checkout과 분리되지 않고, 상위
탐색과 빌드 문맥이 그 트리를 원본의 일부로 볼 수 있다. worker-authorization-policy.md의 분리 문장은 이 조상 관계에 적용된다. Git 명령이
worktree를 하나 더 인식한다는 사실만으로 그 문장을 충족한다고 보지 않는다.

1차 정정

git clean -fdx가 중첩 worktree를 지운다는 일반화는 실험하지 않았고 거둔다. IDE 검색이 파일을 지운다는 말도 틀렸다. 검색이나 인덱스가
파일을 포함할 수는 있어도, 삭제는 보이지 않았다. capture_seed의 .handrail/ 검사는 worktree 안 git diff --name-only의 상대경로다. 작업
파일이 frontend/...이면 부모 디렉터리가 <repo>/.handrail/worktrees라는 이유만으로 걸리지 않는다. worktree 안의 .handrail/project.json
변경은 위치와 무관하게 기존처럼 거부된다.

최종 정책

기존 실행은 저장된 절대경로를 유지한다. 기본값이나 호스트가 바뀌어도 Review 중 트리를 옮기지 않는다. 경로가 없으면 복구 대상으로 남긴다.

신규 경로 순서는 이렇게 고정한다. 이미 pin된 경로, private에 등록된 C 또는 명시적 B, 등록이 없으면 A. 저장소 파일의 배치는 제안이지 권한
근거가 아니다. 선택한 경로의 호스트 쓰기가 실패하면 중단하고 위 세 선택지만 보여 준다.

private 상태는 XDG에 둔다. 소스 루트만 배치 설정으로 바뀐다. runs.root 전체를 소스 위치로 옮기지 않는다.

승인 최소화는 같은 루트의 새 작업 디렉터리를 기존 기록이 덮을 때 질문을 생략하는 것이다. 능력, 저장소 identity, pin이 바뀌면 다시 묻는다.

구현은 세 가지를 먼저 한다. Herdr와 run이 같은 resolver와 소유권 검사를 쓰고, 기존 경로는 유지한다. host_preview가 실제 소스 루트, common
dir, private 데이터를 나눠 보여 주고, 실패 시 위치를 바꾸지 않는다. herdr_workflow._worktree가 이미 있는 경로를 검사 없이 반환하지 않게
하고, common dir와 symlink를 owned_worktree 수준으로 확인한다.

남아 있는 차이는 하나다. C의 자동 사용은 private 설정이 그 정확한 디렉터리를 이미 가리킬 때로 제한하는 쪽이다. 쓰기 가능한 부모
workspace가 있다는 사실만으로 C를 만드는 동작은 합의하지 않는다.

WORKTREE_ROUND2_COMPLETE_GROK
