# Handrail v0 설계안

작성일: 2026-09-30
상태: 검토 제안. 이 문서의 작성은 제품 구현·배포 승인을 뜻하지 않는다.
대상: 현재 Handrail 0.2 코드를 Codex 플러그인으로 전환하는 첫 설계 기준선.

`v0`는 이 설계안의 디렉터리 이름이다. 기존 Python 패키지 버전 `0.2.0`을 낮추거나 다음 릴리스 버전을 확정하는 의미는 아니다.

## 권장안

**현재 Python 코어를 재사용하는 Codex 플러그인을 만들고, 첫 설정에서 외부 Vikunja의 API 토큰과 사용할 프로젝트·Kanban 뷰를 연결한다.**

첫 배포는 스킬과 플러그인 내부 실행 도구로 구성한다. 사용자는 Codex에 자연어로 요청하고, 스킬이 번들된 도구를 호출한다. MCP는 같은 코어 위에 나중에 추가할 수 있게 경계를 만들되 첫 배포의 필수 조건에서는 제외한다. 이렇게 하면 현재 구현과 다른 TypeScript 서버를 동시에 새로 만들지 않아도 된다.

## 사용자와 합의한 요구

| ID | 요구 | 설계 위치 |
| --- | --- | --- |
| U1 | Handrail이 Vikunja를 설치하지 않는다. 없으면 설치를 안내한다. | [설정 흐름](SETUP_AND_CONFIGURATION.md) |
| U2 | 설치·초기 설정 과정에서 연결 정보와 사용할 보드를 받는다. | [설정 흐름](SETUP_AND_CONFIGURATION.md) |
| U3 | API 토큰을 대화형으로 받아 홈 디렉터리의 파일에 저장한다. | [설정과 비밀정보 저장](SETUP_AND_CONFIGURATION.md) |
| U4 | 빌드된 최종 배포물은 Codex 플러그인이다. | [배포 구조](PROJECT_STRUCTURE.md) |
| U5 | 원격 Git 설정·push는 Codex 오케스트레이터가 처리한다. Handrail은 원격 Git을 관리하지 않는다. | [책임 경계](MASTER_SPEC.md) |
| U6 | 한 호스트에서 여러 Handrail 프로젝트를 개발할 수 있다. 각 프로젝트는 자신의 부모 보드 1개로 시작한다. | [프로젝트 계층](PROJECT_HIERARCHY.md) |
| U7 | 구현 CLI의 모델을 선택할 수 있어야 한다. Cursor 오케스트레이터 지원은 다음 개발 항목으로 기록한다. | [실행 계약](MASTER_SPEC.md), [후속 개발](BACKLOG.md) |

여기서 대화형 설정은 일반 정보에 대한 Codex 대화와, 실제 토큰을 받는 사용자 터미널의 숨김 입력으로 구성한다. 토큰 문자열을 채팅이나 에이전트 도구 인자로 전달하지 않는다.

## 이번 검토에서 제안하는 결정

1. Python 코어와 기존 명세 승인·worktree·검증·리뷰 기능을 유지한다.
2. 사용자 연결 프로필, 비밀정보, 저장소의 보드 연결 정보를 구분한다.
3. 보드는 이름 대신 `project_id + view_id + bucket_id`로 연결한다. 이름은 표시·검색용이다.
4. 기존 보드의 열을 매핑한다. 연결만으로 프로젝트·열·계정·권한을 생성하거나 수정하지 않는다.
5. 신규 플러그인은 API v2를 사용한다. 기존 v1 실행 기록과 설정은 명시적 이관 대상으로 보존한다.
6. worktree를 유지하면서 Git 저장소당 쓰기 실행은 하나로 제한한다.
7. Codex 플러그인 설치 완료와 Vikunja 설정 완료를 별도 상태로 관리한다.
8. 외부 반영 실패는 로컬 실행 결과와 별도로 기록하고, 결과가 불명확한 쓰기는 자동 재전송하지 않는다.

이 결정들은 새 권장안이며, 사용자와 이미 합의한 U1–U7과 구분한다. 선택 이유와 비용은 [현재 구조 비교](COMPARISON.md)에 있다.

## 후속 논의 반영

- v0는 Codex 오케스트레이터에서 Codex worker를 먼저 수용 검증하고, 같은 릴리스에서 Cursor worker도 검증하는 순서를 권장한다. 두 worker 모두 모델을 지정할 수 있다.
- Cursor 오케스트레이터와 MCP 필요성 평가는 [후속 개발 항목](BACKLOG.md)으로 관리한다. Cursor 연동 계층은 구현 착수 시 Codex와 Cursor CLI가 공동 개발하는 방식을 제안한다.
- 각 Handrail 프로젝트는 **독립된 부모 프로젝트의 Kanban 보드 하나**로 시작한다. 호스트 공통 부모 보드를 만들지 않는다. 하위 프로젝트·보드는 필요할 때 해당 프로젝트 아래에 추가하는 선택 확장이다.
- 연결 프로필을 여러 프로젝트에서 재사용하더라도 보드·명세·실행 기록·선택 상태는 프로젝트별로 구분한다. 호스트 공통 `default_board`는 두지 않는다.

## 문서 순서

| 문서 | 내용 |
| --- | --- |
| [COMPARISON.md](COMPARISON.md) | 기존 설계·현재 코드·권장안 비교와 재사용 판단 |
| [MASTER_SPEC.md](MASTER_SPEC.md) | 책임 경계, 작업 상태, 실행·검증 계약, 완료 기준 |
| [SETUP_AND_CONFIGURATION.md](SETUP_AND_CONFIGURATION.md) | 실제 초기 설정 UX, 파일 형식, 토큰·보드·실패 처리 |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | 소스와 최종 플러그인 구조, 빌드·실행 방식 |
| [MIGRATION_PLAN.md](MIGRATION_PLAN.md) | 구현 순서, 기존 데이터 이관, 검증 시나리오 |
| [IMPLEMENTATION_PROMPT.md](IMPLEMENTATION_PROMPT.md) | 후속 구현 에이전트용 지시 |
| [PROJECT_HIERARCHY.md](PROJECT_HIERARCHY.md) | 호스트 내 여러 프로젝트, 각 부모 보드, Vikunja 하위 프로젝트 조사와 확장안 |
| [PROJECT_WORKFLOW_AND_TERMS.md](PROJECT_WORKFLOW_AND_TERMS.md) | 계획·작업 카드 workflow, 조율자/작업자 용어, Review/Done 및 사람의 상태 변경 동기화 정책 |
| [BACKLOG.md](BACKLOG.md) | Cursor 오케스트레이터·공동 개발·MCP 검토·선택 확장의 후속 항목 |
| [PACKAGING_DECISION.md](PACKAGING_DECISION.md) | 공통 플러그인 배포물과 호스트별 설치·연동·지원 검증의 구분 |
| [CURSOR_REVIEW.md](CURSOR_REVIEW.md) | 실제 Cursor CLI / Grok 4.7 검토 결과, 원문, 채택·수정 판단 |

U1–U7이 최우선이다. 기능 계약은 MASTER_SPEC, 설정 형식은 SETUP_AND_CONFIGURATION, 배포 형식은 PROJECT_STRUCTURE를 기준으로 한다. 상위 폴더의 이전 설계는 비교 자료로 보존한다.

## 조사 범위와 근거

- 현재 체크아웃: `673c29a022e01dec1d4102f665aa0d0afdd1fd12` 및 작업 트리의 기존 미커밋 변경.
- [이전 MASTER_SPEC](../MASTER_SPEC.md), [이전 구조](../PROJECT_STRUCTURE.md), [이전 구현 지시](../IMPLEMENTATION_PROMPT.md).
- [현재 패키지](../../pyproject.toml), [현재 구현](../../handrail/), [현재 문서](../../docs/), [테스트 코드](../../tests/).
- 로컬에서 확인한 실행 환경: Codex CLI `0.157.1`, Python `3.9.25`. `codex plugin --help`에서 플러그인 관리 명령을 확인했다. 실제 플러그인 로딩은 이번 문서 작업에서 시험하지 않았다.
- `handrail status/project list`는 현재 작업 폴더와 다른 등록 프로젝트를 가리켰다. 비교 대상은 사용자가 지정한 이 체크아웃이며, 그 등록 프로젝트의 보드·서비스를 변경하지 않았다.
- 사용자가 요청한 Cursor CLI / Grok 4.7 읽기 검토를 실제 수행했다. [실행 기록과 반영 판단](CURSOR_REVIEW.md)을 참고한다. 애플리케이션 테스트·제품 위임 흐름·플러그인 설치·사용자 Vikunja 변경은 수행하지 않았다. 공식 문서와 공개 데모 API 명세는 읽기로 확인했다.

## 외부 문서에서 확인한 전제

공식 문서는 스킬만 포함한 플러그인도 지원한다고 설명한다. 따라서 MCP를 필수로 두지 않는 것은 플러그인 배포 요구와 양립한다. [OpenAI Plugin architecture](https://developers.openai.com/plugins/concepts/plugins)

현재 권장 패키징은 루트 `plugin.json`이며 `.codex-plugin/plugin.json` 호환 형식도 지원한다. 설치만으로 임의의 초기 설정 스크립트가 실행된다고 가정하지 않는다. [OpenAI Package your plugin](https://developers.openai.com/plugins/build/plugins)

Vikunja는 API 토큰 인증과 API v2를 문서화한다. 구현 시 대상 인스턴스의 OpenAPI로 필요한 기능을 확인한다. [Vikunja API](https://vikunja.io/docs/api-documentation/), [Vikunja API v2](https://vikunja.io/docs/api-v2/)
