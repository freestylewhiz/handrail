# 기능 범위

이 문서는 0.3.0-rc.4 CLI와 plugin skill의 기능을 정리합니다. 릴리스 후보의 검증 여부는 [release-validation.md](release-validation.md)를 봅니다.

| 영역 | 제공 기능 | 경계 |
| --- | --- | --- |
| 연결 | hidden terminal token setup/rotate, profile list/forget, Vikunja v2 read | 서비스 설치·token 발급·server revoke는 사용자가 수행 |
| Repository binding | 현재 Git repository 하나를 기존 parent project/manual Kanban view에 결합 | binding 과정은 원격 board를 생성·수정하지 않음 |
| 도움말 | offline `help workflow`, `help terms`, `help sync`, JSON 선택 출력 | 설정·토큰·Git 저장소 없이 조회 |
| Area | 부모 아래 기존 프로젝트·manual board 명시 등록 및 조회 | 등록된 하위 프로젝트만 관리; 원격 보드 자동 생성 없음 |
| Task | 부모·등록된 area의 list/context/show/create/comment/move와 operation sync | 다른 부모·미등록 project는 접근 거부 |
| 계획·작업 | 실제 하위 task 관계, 작업 완료, 종합 검증, 계획 Review/Done, 보완 회차 | 워커 종료만으로 완료하지 않음; 보완은 새 작업 카드 |
| 외부 상태 변경 | `task reconcile` preview/adopt/apply | 사람의 상태 변경을 자동 원복하지 않음; 증거를 만들어내지 않음 |
| Context | task/comment/attachment metadata와 선택 attachment bytes를 source ID, timestamp, hash와 기록 | 파일은 자동 전부 다운로드하지 않음; 25 MiB/file, 100 MiB/run packet 제한 |
| Specification | Git spec 초안과 task별 content hash approval, stable check IDs | task 상태 열은 approval을 뜻하지 않음 |
| Worker | Codex 오케스트레이터에서 Codex 또는 Cursor CLI worker 실행 | Cursor 오케스트레이터는 follow-on; 별도 CLI 인증 필요 |
| Run | 비동기 start/list/inspect/cancel/recover/resume/abandon, verify/revise/review | worker 성공만으로 accept되지 않으며 max two revision rounds |
| Integration | accepted fingerprint에서 clean pinned baseline으로 local integrate 및 통합 후 command check | push/PR/remote merge 수행 안 함 |
| External sync | 검증된 통합 근거의 작업 Done 또는 단일 카드 Review, 계획 제출 기록 | timeout 후 자동 exactly-once 보장이나 무검토 retry 없음 |
| Summary | bound parent tasks/runs의 결정적 Markdown snapshot과 notes 보존 | Vikunja 원본을 대체하지 않고 추측 URL·생성시각을 넣지 않음 |
| Migration | legacy Handrail 로컬 데이터의 preview/apply/resume/rollback | 외부 Vikunja board·Git remote 이관/변경 아님 |

CLI 도움말은 launcher에서 확인합니다. 예: `python3 -I <plugin-root>/scripts/handrail.py run --help`.
