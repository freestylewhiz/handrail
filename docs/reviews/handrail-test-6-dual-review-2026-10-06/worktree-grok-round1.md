# Cursor Grok High · Worktree 배치 1차 의견

+권장 기본은 E다. 후보가 비어 있을 때의 위치는 A, 즉 지금처럼 XDG 사용자 데이터 아래 프로젝트별 worktree다. C는 사용자가 한 번 지정한 영속
sibling일 때만 쓴다. B는 체크아웃 밖 영속 경로를 둘 수 없을 때의 명시적 예외다. D는 gitops.fingerprint가 이미 쓰듯 임시 인덱스와 짧은
산출물만 둔다.

전제는 다섯 가지다. 토큰, lock, run 기록, herdr 상태는 계속 XDG에 둔다. worktree 절대경로는 private 상태에만 pin하고
.handrail/project.json에는 넣지 않는다. worker에게 주는 쓰기 범위는 그 카드의 worktree 하나다. Git common dir 쓰기는 worktree 위치와
별개의 host 능력이다. herdr_workflow._worktree와 run_workflow가 만드는 runs.root(...) / "worktrees"는 같은 규칙을 쓴다.

조율자가 말한 <repo>/.handrail/worktrees 기본값은 test_6의 파일 쓰기 마찰만 보고 고른 안에 가깝다. 그 세션의 조율자 sandbox는 저장소
쓰기와 /tmp만 열려 있었고, ~/.local/share/handrail/.../herdr-worktrees는 밖이었다. .git은 저장소가 쓰기 가능해도 읽기 전용이었다. B로
옮기면 Vite가 worktree 안에 임시 파일을 쓰는 문제는 저장소 쓰기 권한 안으로 들어온다. git worktree add가 common dir의 worktrees
메타데이터를 고치는 문제, Vikunja 접속, worker 샌드박스 안의 네이티브 빌드는 그대로다. 승인 카드가 통째로 사라지는 배치가 아니다.

B를 기본으로 두면 제품 불변도 깨진다. worker-authorization-policy.md는 worktree를 사용자 checkout과 분리된 채로 검수·통합 게이트를
유지하라고 한다. docs/architecture.md는 명세와 binding만 저장소에 두고, run 상태·lock·credential은 XDG에 둔다. .handrail/worktrees는 추적
파일 project.json과 같은 디렉터리 아래다. worker sandbox가 실수로 저장소 루트면 binding 파일을 덮어쓸 수 있다. workspace.resolve는 이
파일과 symlink를 거부하는 쪽으로 무결성을 이미 가정한다.

사용하는 프로젝트에서도 B는 작아 보이지 않는다. gitignore가 있어도 watcher, Docker build context, 패키지 탐색은 멈추지 않는다. test_6은
Express 앱에 frontend/를 얹는 구조였고, 저장소 루트를 context로 복사하면 worker의 node_modules와 실험 파일이 이미지에 들어간다. 상위 설정
탐색은 .handrail/worktrees/<plan>/work-<task>/frontend에서 올라가 canonical 루트의 설정을 만난다. 사용자는 Done 뒤에 worktree가 남았는지
다시 물었다. 그 디렉터리가 소스 트리 안에 있으면 git clean -fdx와 IDE 검색이 작업 중인 트리를 지운다. 경로를 프로젝트 안에 두는 것과
worker에게 프로젝트 전체 쓰기를 주는 것은 다르지만, 조율자 sandbox가 저장소 전체면 둘 다 같은 쓰기 루프에 놓인다.

A부터 E

A. 제품 쪽에서는 추적 경로가 workspace_id로 모이고, checkout을 지워도 private 기록과 트리가 바로 따라 사라지지 않는다. 여러 checkout이 한
Git common dir를 공유해도 workspace.py의 registered root와 common dir 검사가 유지된다. 홈 쪽 실패는 test_6 그대로다. project-only
sandbox는 빌드·설치마다 그 경로 승인을 요구한다. worker가 디렉터리 밖으로 올라가면 herdr.json과 다른 계획의 트리가 같은 부모 아래에 있다.
홈과 /project_workspace가 다른 볼륨이면 용량과 quota가 저장소와 따로 놀다.

B. 조율자가 이미 저장소를 쓸 수 있으면 내용 쓰기의 추가 승인은 줄어든다. 실패는 checkout 오염이다. exclude가 없으면 herdr start의
HERDR_SOURCE_DIRTY가 먼저 막힌다. exclude가 있어도 감시·이미지·모노레포 glob은 그 트리를 소스의 일부로 본다. 등록된 checkout과 다른 작업
복사본은 디스크上的 트리를 공유하지 못한 채 common dir의 worktree 목록만 공유한다. 사용자가 .handrail을 메타데이터로 알고 지우면 진행 중
카드의 파일이 사라진다.

C. 제품이 원하는 분리에 가장 가깝다. 경로는 private 설정에 pin하고, 모드 0o700인 사용자 소유 디렉터리로 둔다. 부모 workspace sandbox가 그
sibling을 이미 포함하면 추가 승인 없이 내용 쓰기가 된다. project-only sandbox에서는 A의 좁은 경로 승인과 같은 한 번의 동의가 필요하다.
실패는 추론이다. 저장소 부모를 자동으로 workspace로 보면, 그 부모에 다른 저장소가 있을 때 한 승인이 여러 프로젝트 트리를 덮는다.
sibling을 다른 저장소 안에 두면 B의 오염이 옆 프로젝트로 옮아간다.

D. /tmp는 test_6 sandbox에 열려 있었다. 재부팅, tmp 청소, 공용 개발 서버의 노출을 견디지 못한다. Review 동안 세션을 유지하는 지금 정책과
맞지 않고, integrate·finish·retry seed가 시각을 건너뛴 뒤 트리를 다시 연다. 임시 인덱스 이상은 여기 두면 안 된다.

E. 배치를 코드에 박지 않고 규칙을 박는 안이다. 오늘 host_preview는 루트를 나열만 하고 host_ready를 항상 거짓으로 둔다. 그래서 “쓸 수 있는
곳이면 어디든”은 구현이 체크아웃에 디렉터리를 만들어 보는 순간 B가 조용한 기본값이 된다. 규칙은 써야 한다. private 상태는 XDG다. 기본
worktree 루트는 A다. 첫 계획에서 그 절대경로와 Git common dir을 구분해 한 번 보여 준다. 사용자가 영속 경로를 주면 C로 pin한다. B는 그 두
경로를 둘 수 없다는 명시적 선택일 때만, exclude 설정과 watcher·이미지 경고를 같이 기록한다. 프로브는 checkout 안에 시험 디렉터리를 만들지
않는다.

소스에서 같이 움직일 곳

herdr_workflow._worktree만 바꾸면 run 계열과 어긋난다. run_workflow는 runs.root(workspace_id) / "worktrees" / identifier를 만들고,
run_preparation.owned_worktree는 그 경로가 아니면 PREPARATION_PATH_INVALID로 거부한다. Herdr 경로를 저장소 안으로 옮기면 소유권 검사가
옛날 XDG 경로를 정답으로 남긴다. cli.py preflight는 runs.root(...) / "worktrees"를 host_preview에 넘긴다. Herdr의 실제 경로인
herdr-worktrees/<plan>/work-<task>는 그 미리보기에 없다. 배치를 고쳐도 이 인자를 실제 루트로 바꾸지 않으면 사용자는 다른 경로를 승인한다.

permission_adapters.host_preview의 worker_worktree_storage와 handrail_data, git_common_directory는 이미 세 줄로 나뉘어 있다. 이 구분을
유지하고, worktree 루트만 private 설정의 pin으로 바꾸면 된다. workspace.resolve가 binding 파일에서 절대경로를 읽게 만들면 architecture의
“project.json에 절대경로를 두지 않는다”와 충돌한다. gitops.fingerprint의 임시 인덱스는 tempfile에 남는 것이 맞다. B 예외를 구현한다면
.git/info/exclude에만 경로를 넣고, 저장소에 커밋되는 ignore를 사용자 대신 추가하지 않는다. capture_seed는 .handrail/ 변경을 retry 소스로
거부한다. worktree가 .handrail 아래에 있으면 이 검사가 작업 파일과 관리 파일을 같은 접두어로 볼 수 있으니, 예외 경로를 두기 전에 검사
대상을 “관리 파일”과 “worktree 내용”으로 나눠야 한다.

승인 최소화

사용자가 동의하는 것과 host가 그 동의를 적용하는 것은 따로다. 줄여야 하는 것은 명령마다 바뀌는 justification이다. 남길 동의는 계획 시작
때의 두 능력, 즉 pin된 worktree 루트 쓰기와 Git common dir 쓰기다. 네트워크와 설치 argv는 그 목록의 다른 줄이다. B를 기본으로 넣어 저장소
쓰기 하나를 재사용하는 방식은, 이미 열린 권한 안에 작업 트리를 숨기는 쪽이다. A 또는 C의 좁은 경로를 한 번 동의하고 prefix로 재사용하는
쪽이 경계가 분명하다. 그 동의가 host에 적용되지 않으면 배치를 바꿔도 escalation은 남는다. 적용 여부는 Handrail이 sandbox를 고쳐 확인할 수
없고, 다음 쓰기 결과로만 본다.

상대에게 물을 세 가지

1. B가 줄인다고 보는 승인이 worktree 내용 쓰기인지, git worktree add가 고치는 common dir까지인지. test_6은 저장소 쓰기와 .git 읽기
   제한이 동시에 있었다.
2. policy의 checkout 분리를 불변으로 둘 것인지. 사용성 때문에 푼다면 worker 쓰기 루트를 worktree 하나로 고정하는 계층이 adapter인지
   host 미리보기인지.
3. C의 영속 루트를 저장소 부모에서 추론할지, 사용자 명시 경로로만 받을지. 추론은 project-only sandbox에서 실패하고, 부모에 저장소가
   여러 개면 한 동의가 다른 프로젝트 트리까지 포함한다.

WORKTREE_ROUND1_COMPLETE_GROK
