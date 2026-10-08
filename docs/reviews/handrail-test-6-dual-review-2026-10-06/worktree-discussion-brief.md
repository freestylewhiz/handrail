# Worktree 배치 토의 의뢰

사용자는 기존 검토 스페이스의 Codex Astra High와 Cursor Grok High가 계속 토의하도록 요청했다. 기존 분석 문맥을 활용하되 Handrail의 목표·구조와 실제 사용자 프로젝트 양쪽에서 배치를 판단한다. 읽기 전용 토의이며 파일·프로젝트·카드·설정 변경, 테스트/서버/설치 실행, 추가 에이전트 실행은 하지 않는다. 토의 결과만 터미널에 출력한다. 쉘 명령은 rtk 접두사를 사용한다.

## 반드시 고려할 근거

- docs/philosophy.md: 요구·실행·변경·검증·사용자 결정의 추적성, 검수 후 통합, Review 보존, 다중 프로젝트.
- docs/architecture.md, docs/worker-authorization-policy.md: private 관리자 데이터/권한 기록과 worker source 분리, 실행 주체별 권한, 영속 복구.
- handrail/herdr_workflow.py _worktree/start/review/integrate/finish; handrail/runs.py, workspace.py, permission_adapters.py, gitops.py; 필요 시 run_preparation.py.
- 이 폴더의 기존 evidence와 독립 검토. 실제 test_6에서는 홈 아래 worktree 쓰기가 조율자 sandbox 밖이었고 .git은 별도 읽기 제한이었다.

조율자의 직전 잠정 제안은 기본을 <repo>/.handrail/worktrees로 하고 홈은 선택 옵션, /tmp는 임시 산출물로 두자는 것이었다. 이 제안을 결론으로 전제하지 말고 반박할 수 있다.

## 비교할 배치

A. 현재 XDG 사용자 데이터 아래 프로젝트별 worktree.
B. canonical checkout 내부의 .handrail/worktrees 같은 ignored 하위 디렉터리.
C. canonical checkout 밖이면서 함께 승인된 영속 개발 workspace 아래 sibling 전용 worktree 루트.
D. /tmp 같은 임시 루트.
E. 고정 기본값보다 host capability와 명시적 설정으로 고르는 정책(결정 규칙을 구체화).

## 두 관점

1. Handrail 제품: 추적성, worker 격리, manager 신뢰 상태, 검수·통합, resume, 여러 repo/checkout/계획, 삭제·이동·migration, 경로 pinning, cross-workflow 일관성.
2. 사용하는 프로젝트: 기존 checkout 오염, IDE 인덱싱·파일 감시, 모노레포/패키지 탐색/상위 설정 탐색, Docker build context와 배포, disk/성능, project-only sandbox와 부모 workspace sandbox, 사용자의 추가 승인 횟수와 이해 가능성.

gitignore가 watcher/build/package 탐색까지 막는다고 가정하지 말 것. 작업 경로를 프로젝트 안에 넣는 것과 worker에 전체 프로젝트 쓰기를 주는 것은 별개다. sibling도 project-only sandbox에서는 추가 권한이 필요할 수 있다. /tmp의 영속성은 보장하지 말 것. Git common dir와 private manager state 권한은 worktree 위치와 별개다.

## 1차 응답

1000~1600 단어 이내 한국어. 마지막에 WORKTREE_ROUND1_COMPLETE_ASTRA 또는 WORKTREE_ROUND1_COMPLETE_GROK 표식.

- 권장 기본 배치와 명시적 예외. 하나를 고르되 전제조건을 적는다.
- A~E 비교, 양쪽 관점의 tradeoff와 구체적 실패 시나리오.
- 현재 소스에서 바뀌어야 할 부분과 근거 함수.
- 실제 추가 승인 최소화 원칙. 사용자 추가 동의와 host 적용을 구분.
- 상대 모델에게 묻거나 반론을 요청할 3가지 쟁점.

이후 상대의 응답을 전달받아 2차 토의에서 합의·반론·최종 정책을 정리할 예정이다.
