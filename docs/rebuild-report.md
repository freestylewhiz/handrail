# Handrail 재구현 결과

> 초기 v1 재구현의 계약·범위·결과 기록이다. 현재 alpha.5의 추가 범위와 공개 절차는 [구현 상태](status.md), [Summary와 기획 완료](summaries.md)를 우선한다.


이번 재구현은 `rebuild/handrail-agentroom-v1`에서 진행했다. 기존 분석에 참여한 Herdr 공간 `wW`의 두 대화를 재개해 구현과 통합 검토에 활용했다. 테스트 구현 프로젝트의 공간과 기존 Vikunja 칸반은 변경하지 않았다.

## 협업

| 역할 | 실제 사용 모델 | 구현과 검토 |
| --- | --- | --- |
| `hr-review-astra` | Codex GPT-6-Astra High | workflow, 기준별 증거와 검수 커밋, agentroom과 application의 실행·복구·정리 경계 |
| `hr-review-grok` | Cursor Grok 4.7 High | Herdr/Vikunja 연동 어댑터, board projection과 불확실한 쓰기 재조정 |
| 조율자 | 현재 Codex 세션 | 아키텍처 확정, 저장·설정·진단·권한·Git·CLI·배포·문서·스킬, 통합 연결 |

두 worker는 기존 대화 이력을 유지한 채 구현 모드로 재개했다. 작업 파일의 소유권을 나누고 공유 계약으로 연결했다. 직접 실행한 협업 제어는 기존 Herdr CLI를 사용했다. 개발 중인 새 Handrail을 이미 검증된 조율 도구처럼 사용하지 않았다.

## 바뀐 구조

기존 모듈을 감싸는 호환 계층을 남기지 않고 새로운 `setup`, `workflow`, `agentroom`, `interfaces`, `authorization`, `hooks`, `shared`를 구현했다. 새로운 공개 CLI와 플러그인 runtime은 이 컴포넌트만 사용한다.

Vikunja 자체 구현은 포함하지 않는다. 기존 v2 API로 카드·관계·상태·댓글을 연결한다. Herdr도 기존 서비스에 대한 어댑터다.

## 이번 논의의 반영

- 이미 받은 구현 지시와 승인 범위를 재사용하며, 자원·동작이 달라진 부분을 출력한다.
- 실제 canonical checkout, Git common directory, 관리 상태, 현재 worktree와 endpoint를 진단한다.
- HERDR_ENV를 조작하지 않고 외부 조율을 명시 endpoint로 지원한다.
- 실행 신원, lifecycle, 관찰 activity, 지시 제출과 업무 완료를 분리한다.
- 통합할 커밋을 검수에 고정하고, 통합된 revision의 criterion별 증거를 요구한다.
- 카드 상태·이력·외부 전송 의도를 함께 저장하고 중단 후 재조정한다.
- Review 동안 자원을 보존하며 수락과 자원 정리를 독립적으로 기록한다.

## 검증과 이력 경계

Python 구문, 내부 모듈 참조, 현재 문서 링크와 diff 형식을 정적으로 확인했다. Grok의 초기 어댑터 작업에는 일부 격리된 서명·동작 확인이 포함됐으며, 전체 테스트나 실서비스 수락 검증으로 해석하지 않는다. 세부 제한은 [구현 상태](status.md)에 있다.

이 보고서 작성 당시에는 기존 메인과 브랜치 이력을 보존했고 이력 초기화용 커밋은 만들지 않았다. 이후 2026-10-08 사용자의 별도 명시 요청으로 현재 결과를 새 `main`의 최초 커밋으로 삼아 이전 로컬 Git 이력·브랜치를 제거했다. 현재 기준은 [구현 상태](status.md)를 따른다.
