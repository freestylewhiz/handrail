# 구현 현황

현재 소스 버전: **0.5.0**. v0.4 권한 기능과 v0.4.1 하위 작업 보드의 검증 기록은 이전 기준에 대한 기록입니다. v0.5.0은 Herdr 기반 워커 오케스트레이션 경로를 개발 중이며, 이 경로의 구현/수용 상태를 이전 릴리스의 검증 결과로 간주하지 않습니다. 로컬 source build, 배포 검증, 원격 게시 및 호스트 설치는 각각 별도 상태입니다. 세부사항은 [Herdr workflow](herdr-workflow.md)와 [acceptance 설계](testing/herdr-acceptance.md)를 참조하세요.

## 구현 영역

- Codex 플러그인 bundle에 Python 3.9+ 표준 라이브러리 runtime과 launcher 포함
- 사용자 XDG 경로에 connection profiles와 token credentials 저장; hidden terminal setup/rotate
- repository별 기존 Vikunja v2 parent project/manual Kanban view binding
- bound parent task/comment/attachment metadata reads, reconciled comment/state writes
- Git spec, task-bound SHA256 approval, command/manual check plan
- 선택 ID 첨부 packet(25 MiB/file, 100 MiB/run)과 typed/source-attributed context
- Codex manager가 Codex 또는 Cursor CLI worker를 isolated worktree에서 감독
- run state/lock, cancel/recover/resume, structured worker output, check/fingerprint verification, review, local integration
- review comment/Review state sync와 deterministic task/run summary
- legacy local data migration preview/apply/resume/rollback

## 0.3.0-rc.4의 새 workflow

다음 항목은 `0.3.0-rc.4` 후보에 포함됩니다. 이전 `0.3.0-rc.3` 설치본은 플러그인을 업데이트해야 사용할 수 있습니다.

- 부모 프로젝트 하나와 명시 등록된 하위 보드(`area bind/list`)
- 계획 카드와 실제 Vikunja 하위 task 관계를 가진 작업 카드
- 검수·통합·통합 검증 이후 작업 Done, 전체 검증 이후 계획 Review
- 사용자 확인에 따른 계획 Done, Review 보완 시 신규 작업 카드 및 제출 이력 보존
- 사람의 상태 변경 preview/adopt/apply와 오래된 원격 쓰기 재시도 차단
- 연결 설정 없이 조회 가능한 한국어 `help workflow`, `help terms`, `help sync`

기본 실행은 저장소당 작업자 한 개의 순차 실행입니다. `area bind`는 기존 하위 보드를 등록하며, 원격 하위 프로젝트 자동 생성은 포함하지 않습니다. Git push/PR은 계속 조율자의 별도 작업입니다.

## 확인된 환경

이번 후보의 수용 테스트 환경은 Rocky Linux 9.7, Python 3.9, Codex CLI 0.157.1, Cursor CLI 2026.09.28, Vikunja 2.6.0입니다. 다른 OS/provider 조합은 지원된다고 주장하지 않습니다. Cursor는 worker로 검증 중이며 Cursor 오케스트레이터는 이 후보 범위에 없습니다.

모든 candidate gate의 근거와 아직 남은 검증은 [release-validation.md](release-validation.md)에 기록합니다. 실제 배포·tag 다운로드·final artifact 설치를 확인하기 전에는 문서의 prerelease tag를 릴리스 완료 근거로 표현하지 않습니다.
