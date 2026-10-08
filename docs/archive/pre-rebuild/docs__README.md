# Handrail 문서

현재 source 버전은 Handrail v0.5.0입니다. 기존 Handrail-managed run workflow의 역사적 검증 범위는 [v0.4 validation record](v0.4-validation.md)와 [implementation status](status.md)에 기록되어 있습니다. 설치 안내는 현재 source build와 과거 RC4 설치 예제를 구분합니다. Herdr 기반 오케스트레이션은 개발 중인 별도 workflow이며, [설계](herdr-workflow.md)와 [acceptance plan](testing/herdr-acceptance.md)은 검증 결과가 아닙니다.

| 문서 | 내용 |
| --- | --- |
| [프로젝트 철학](philosophy.md) | 공식 문구, 설계 의도, workflow 순서도, 역할과 용어 |
| [설치](installation.md) | 플러그인 설치, 외부 Vikunja 준비, 비밀 입력, repository binding |
| [사용 매뉴얼](manual.md) | 카드 context, 명세 승인, 실행·검증·리뷰·통합·복구 |
| [에이전트 사용](agent-integration.md) | Codex 매니저와 별도 worker CLI의 역할 |
| [기능 범위](feature-map.md) | 현재 CLI 기능과 경계 |
| [구조와 저장 위치](architecture.md) | 로컬·공유 데이터와 보안 경계 |
| [구현 현황](status.md) | 실제 구현과 확인된 환경 |
| [후속 작업](todo.md) | 릴리스 뒤 별도 합의가 필요한 항목 |
| [v0.4 권한 사용법](permissions-v0.4.md) | 정책 저장, 복수 계획 위임, 하위 명세, 사전 준비·재시도 |
| [권한 정책 검토](permission-policy-review.md) | 구현 전 검토안과 후속 후보; 실제 구현 범위는 v0.4 사용법 참조 |
| [승인 이력 조사](reviews/permission-audit-2026-10-01.md) | hello_handrail_express 세션 전체 조사와 승인·요청 근거 데이터 |
| [Herdr 개선 백로그](reviews/handrail-test-6-backlog-2026-10-06.md) | handrail_test_6 세션에 근거한 Handrail 개선 과제 10건과 수용 기준 |
| [Herdr 쓰기 권한 분석](reviews/handrail-test-6-permissions-2026-10-06.md) | 조율자 실행 경계와 worktree 권한 충돌 및 제품 수정 방향 |
| [Herdr 두 모델 독립 검토](reviews/handrail-test-6-dual-review-2026-10-06/report.md) | Codex Astra High·Cursor Grok High 검토, 최종 Done까지 반영한 기능 7건·사용성 7건 백로그 |
| [권한 요청 최소화 상세](reviews/handrail-test-6-dual-review-2026-10-06/permissions-detail.md) | 네 가지 권한 경계와 실제 쓰기 실패 근거, 사전 준비·승인 재사용 설계 |
| [Worktree 배치 교차 토의](reviews/handrail-test-6-dual-review-2026-10-06/worktree-placement-discussion.md) | 기존 두 모델의 2차례 토의: 신규 권장 구조·현행 기본값·권한 및 복구 정책 |
| [HERDR_ENV·외부 조율 토의](reviews/handrail-test-6-dual-review-2026-10-06/herdr-env-discussion.md) | 발생 조건·무시 가능 여부, 연결 고정·실행체 식별·소통·진척 관리 개선 5건 |
| [릴리스 검증](release-validation.md) | 후보 릴리스의 증거와 미통과 게이트 |
| [Workflow 검증](workflow-validation.md) | 개발 트리의 계층형 카드 흐름과 복구 검증 |
| [Vikunja v2 계약](vikunja-v2-contract.md) | 확인한 API 동작과 한계 |

처음 사용하는 경우 설치 안내를 읽은 다음 매뉴얼의 작은 작업 흐름을 따른다. 명령 옵션은 `handrail --help` 및 하위 명령의 도움말을 기준으로 확인한다. 설계 원문과 확정 요구는 저장소의 `handrail-dev-spec/v0/`에 있다.
