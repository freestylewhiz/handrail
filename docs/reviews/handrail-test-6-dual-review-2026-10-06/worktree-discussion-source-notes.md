# 조율자의 Worktree 배치 근거 메모

2026-10-06, 읽기 전용 조사. 아래 외부 동작은 공식 문서를 확인했으며 이 프로젝트에서 실행 실험을 하지 않았다.

## 소스에서 확인한 결합

- `herdr_workflow._worktree`는 XDG data 아래 `herdr-worktrees/<plan>/work-<task>`를 고정한다.
- `run_workflow`는 `runs.root(workspace_id)/worktrees/<run_id>`를 사용한다.
- `run_preparation.owned_worktree`는 위 legacy 경로와 정확히 일치해야 하고, symlink와 Git common directory도 검사한다. 경로 설정 도입 시 이 소유권 검증을 함께 바꿔야 한다.
- `workspace.resolve`는 Git common directory, private registry, canonical checkout, 각 checkout의 portable binding을 대조한다. basename만으로 프로젝트 identity를 정하면 안 된다.
- `gitops.fingerprint`는 임시 index에서 `git add -A -- .`를 수행하고 `.handrail/runtime`만 명시적으로 제외한다. repo 내부 worktree를 넣는다면 ignore 누락에 따른 nested repository 포함 가능성을 별도로 처리해야 한다.
- `herdr_workflow.start`는 canonical checkout의 dirty 상태를 검사한다. 잘못 배치·제외된 작업 디렉터리가 다음 worker 시작을 막을 수 있다.
- `herdr_workflow.finish`는 canonical checkout에서 검사한다. 그 하위에 다른 worker checkout을 넣으면 검사 도구의 탐색 범위에 영향을 줄 수 있다.
- `permission_adapters.host_preview`는 worktree storage와 Git common directory, 관리자 데이터, provider session 요구를 별도로 보여준다. 위치 이동만으로 전부 해결되지는 않는다.

## 외부 동작과 설계 추론

1. Git linked worktree는 지정 경로에 생성되지만 저장소의 관리 메타데이터와 연결된다. 따라서 worktree 파일 쓰기와 common directory 관리는 별도 요구다. 이동·제거는 Git의 관리 명령과 상태 정합성을 고려해야 한다. [Git worktree](https://git-scm.com/docs/git-worktree)
2. Docker의 로컬 build context 제외는 `.dockerignore`로 제어된다. **설계 추론:** canonical checkout 내부의 ignored worktree는 `.gitignore`만으로 Docker context에서 빠진다고 보장할 수 없다. [Docker build context](https://docs.docker.com/build/concepts/context/#dockerignore-files)
3. Node CommonJS는 로컬에 모듈이 없으면 상위 디렉터리의 `node_modules`를 탐색한다. **설계 추론:** worktree를 canonical checkout 하위에 두면 원본 의존성을 우연히 사용하는 검증 오염 경로가 생길 수 있다. 실제 발생 여부는 런타임·설치 상태·샌드박스 읽기 범위에 따라 달라진다. [Node modules](https://nodejs.org/api/modules.html#loading-from-node_modules-folders)
4. sibling 위치도 상위 개발 workspace에 별도 package/config가 있으면 영향을 받을 수 있다. 외부 배치는 canonical checkout의 ancestor 관계를 없애지만 실행 환경의 완전한 독립성을 보장하지 않는다.
5. writable root를 알고 있다는 것과 git/설치/worker 모든 작업이 허용됐다는 것은 다르다. `os.access` 같은 OS 접근 검사만으로 외부 샌드박스 적용을 확정해서는 안 된다.

## 2차 토의에서 확인할 쟁점

- B(repo 내부)의 권한 이득과 도구별 제외·의존성 오염 비용 중 무엇이 기본값 결정에 더 중요한가?
- C(sibling)를 선호할 때 project-only sandbox에서는 어떤 초기 설정이 필요한가? 이미 승인된 범위만 재사용하며 조용히 부모 디렉터리 전체를 열지 않아야 한다.
- A(XDG)를 현행 호환 기본으로 유지하는 것과 C를 신규 workspace 권장 구조로 제공하는 것을 구분할 수 있는가?
- E(정책)에 사용자에게 보여줄 결정 순서와 중단 조건이 있는가? 실패 때 위치를 조용히 바꾸면 경로에 고정된 승인과 resume 기록이 깨질 수 있다.
