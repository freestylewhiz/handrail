# 후속 작업 후보

아래 항목은 현재 후보의 완료 주장이나 자동 착수 권한이 아닙니다. 우선순위와 범위는 후속 작업에서 별도 합의합니다.

`handrail_test_6` 세션을 근거로 한 [Herdr 개선 백로그 10건](reviews/handrail-test-6-backlog-2026-10-06.md)과 [쓰기 권한 문제 분석](reviews/handrail-test-6-permissions-2026-10-06.md)을 추가했다. 실제 실행 경계 준비, 오류 진단, 소실 worker 복구, 완료 조건과 검사 연결을 우선 검토한다.

후속 완료 기록과 칸반 댓글까지 포함한 [두 모델 독립 검토 종합본](reviews/handrail-test-6-dual-review-2026-10-06/report.md)에 기능 개선 `HR6-F01~F07`, 사용성 개선 `HR6-U01~U07`을 정리했다. 권한 요청 감소의 우선 묶음은 실제 경로 사전 점검(U01), Herdr 의존성 준비(F05), 기존 승인 재사용(U02)이다. [별도 권한 상세 보고](reviews/handrail-test-6-dual-review-2026-10-06/permissions-detail.md)를 함께 참조한다. 이전 10건은 1차 분석 기록이며 후속 우선순위는 종합본을 기준으로 검토한다.

[Worktree 배치 교차 토의](reviews/handrail-test-6-dual-review-2026-10-06/worktree-placement-discussion.md)는 `HR6-W01~W03`으로 위 항목을 구체화한다. 신규 환경은 원본 checkout 밖의 영속 작업 루트를 권장하고, 무설정 기존 환경은 XDG 위치를 유지한다. 프로젝트 내부는 명시적 예외이며 실행 중 경로는 자동 이전하지 않는다. 구현은 공통 배치·소유권 계약, 실제 권한 준비, 재개·이동·정리 순으로 검토한다.

[HERDR_ENV·외부 조율 교차 토의](reviews/handrail-test-6-dual-review-2026-10-06/herdr-env-discussion.md)는 `HR6-E01~E05`로 외부 모드·endpoint 고정, 실행 identity, 지시 전달 상태, 관찰과 업무 진척 구분, 키 입력·종료 권한을 구체화한다. HERDR_ENV 미설정만으로 외부 조율을 중단하지 않도록 하되 연결·대상·동작별 권한을 검증하며 기존 승인 범위를 재사용한다.

| 영역 | 후속 검토 |
| --- | --- |
| Host 지원 | macOS, Windows, WSL, 웹 전용 Codex 환경의 실제 지원 가능성과 검증 기준 |
| Orchestrator | Cursor 오케스트레이터 adapter 및 Codex 플러그인과 분리된 설치·인증·복구 절차 |
| Provider 조합 | 각 manager/worker 조합별 result, sandbox, credential 경계와 취소 검증 |
| Vikunja 호환 | 2.6.0 외 v2 release와 hosted deployment의 OpenAPI/permission contract 검증 |
| 데이터 이관 | 재시작 가능한 backup/restore, 토큰 교체, 여러 repository 마이그레이션 실험 |
| 설정 초기화 | 호스트 전역 설정·connection profile·credential과 단일 프로젝트의 연결정보를 범위별로 확인하고 초기화하는 안전한 절차. 실행 전 대상 미리보기와 확인을 제공하고, 로컬 credential 제거와 Vikunja 토큰 폐기는 구분하며, 원격 프로젝트·카드 데이터는 삭제하지 않음 |
| 강화된 격리 | 같은 OS 계정 CLI에서 벗어나는 별도 사용자 또는 검증된 sandbox 경계 |
| 요약 | diff 기반 이력/증분 summary와 유저가 원하는 내보내기 범위 |
| 배포 | final tag, artifact checksum, 서명 및 clean host 설치 검증 |

후속 범위에서 제외해 온 remote Git operation은 사용자가 직접 기존 Git 도구로 수행합니다. Handrail이 remote URL, token, push/PR, remote merge 상태를 관리하는 계획은 이 문서에 포함하지 않습니다.
