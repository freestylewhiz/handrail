# Handrail 문서

현재 소스와 호스트 설치 기준 버전은 **1.0.0a6 (alpha.6)**다. DEV-01~10 종료 후 **DEV-11 저장소 최초 승인·조율자 자동 후속 실행**을 설계했고 구현·수용 검증은 대기다. 후속 **DEV-12 Summary 결과/수행 이슈 분리**는 소스·로컬/번들 검증을 마쳤으며 설치본에는 아직 반영하지 않았다. 실제 반영 범위는 [구현 상태](status.md)로 구분한다.

| 문서 | 내용 |
| --- | --- |
| [alpha.6 구현 기록](alpha6-implementation.md) | DEV-01~10 반영 위치, 실제 계약·지원 범위·트레이드오프·확인 기록 |
| [RC02 분석·수정](reviews/handrail-rc-02-2026-10-08.md) | 신규 설정의 함수 누락 회귀, 권한 오류 구분, 배포·스킬 개선 |
| [RC03 책임자 최종 점검](reviews/handrail-rc-03-2026-10-08.md) | 조율자 회고·초안 대조, 최종 복구 결과, 철학에 따른 채택·축소·제외 및 DEV-11 선행 수정 |
| [개선 체크리스트](checklist-v1-host-test.md) | DEV-11 수용·RC03 보완 21개, DEV-12 구현 확인 5개·호스트 수용 대기 1개 및 기존 종료 142개 |
| [DEV-11 설계](designs/dev-11-project-automation.md) | 저장소 최초 승인 재사용, 자동 검토·병합·테스트·수정, 턴 종료 후 재개 계약 |
| [개발 순서 요약](todo.md) | DEV-11 개발 순서와 기존 종료·확인 기록 |
| [이번 범위](rebuild-scope.md) | 포함 기능, 외부 제품 경계, 브랜치와 초기화 범위 |
| [아키텍처](architecture.md) | 컴포넌트 구조도, 상태와 통신, 영속성 |
| [상세 아키텍처](architecture-detailed.md) | 컴포넌트 관계·데이터 모델·권한 경계와 단계별 워크플로우 시퀀스 |
| [Philosophy](philosophy.md) | 조율과 승인, 진행 관리의 설계 원칙 |
| [설치](installation.md) | 소스/플러그인과 신규 설정 |
| [간단한 저장소 연결](onboarding.md) | init, 연결 재사용, 부모 보드 선택과 Review 열 준비 |
| [보드·카드 관리](boards.md) | 하위 보드 추가, 사용자 요청 카드 강제 전환과 관리 이력 |
| [Summary와 기획 완료](summaries.md) | 정식 수락, 카드 원본, 언어 영역, 선택 조회와 room 정리 |
| [운영](manual.md) | 계획에서 사용자 수락까지 명령 흐름 |
| [에이전트 스킬](agent-integration.md) | 조율자와 작업자의 계약 |
| [상태](status.md) | 구현 수준과 검증 제한 |
| [재구현 결과](rebuild-report.md) | 두 모델의 작업 분담과 이번 개선의 반영 |

`reviews/`, `archive/`, 버전이 명시된 기존 문서는 과거 근거다. 이번 구현 backlog로 자동 편입하지 않는다. 초기 협업 API 계약은 [재구현 계약](rebuild-contract.md)에 기록되어 있으며 실제 공개 명령은 운영 문서를 따른다.
