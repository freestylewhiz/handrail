# Handrail v0 구현 착수 지시

이 문서는 사용자가 제품 구현을 요청했을 때 적용한다. 현재 요청이 설계 검토·문서 작성이라면 여기 적힌 구현·서비스 연결·설치를 실행하지 않는다.

## 1. 먼저 읽을 자료

1. 작업 저장소에 적용되는 AGENTS.md와 사용자의 현재 지시.
2. 이 디렉터리의 [README](README.md), [비교 검토](COMPARISON.md), [Master Spec](MASTER_SPEC.md).
3. [초기 설정 계약](SETUP_AND_CONFIGURATION.md), [배포 구조](PROJECT_STRUCTURE.md), [이관 계획](MIGRATION_PLAN.md).
4. 실제 `handrail/` 구현, `pyproject.toml`, 기존 테스트, 현재 Git diff.
5. [프로젝트 계층](PROJECT_HIERARCHY.md)과 [후속 개발 항목](BACKLOG.md).
6. [패키징 판단](PACKAGING_DECISION.md)과 [Cursor 검토 반영 결과](CURSOR_REVIEW.md). 검토 원문보다 채택·수정된 계약을 따른다.

상위 `handrail-dev-spec`의 문서는 이전 설계다. 새 구현의 기준은 v0와 이후 사용자의 수정 지시다. 현재 워크스페이스와 Handrail 전역 선택 프로젝트가 다르면 전역 선택을 따라 다른 프로젝트를 수정하지 않는다.

## 2. 반드시 지킬 사용자 결정

- Handrail은 Vikunja를 설치·운영하지 않는다. 서비스가 없으면 설치 안내와 재개 경로를 제공한다.
- 설치 직후 초기 설정에서 URL·API 토큰·사용할 프로젝트와 Kanban 뷰·열 매핑을 받는다.
- 토큰은 사용자 터미널의 숨김 입력과 사용자 홈 설정 파일로 처리한다. 실제 값을 채팅·도구 인자·출력에 넣지 않는다.
- 최종 사용자 배포물은 Codex 플러그인이다.
- Handrail은 원격 Git을 관리하지 않는다. 원격 설정·인증·push·PR·Forgejo 안내를 제품 흐름에 넣지 않는다. Codex는 사용자 요청에 따라 기존 저장소에서 일반 Git 작업을 수행할 수 있다.
- 한 호스트에서 여러 Handrail 프로젝트를 사용할 수 있고, 각 프로젝트는 자신의 부모 보드 하나로 시작한다. 초기 inbox·컴포넌트 생성이나 호스트 공통 기본 보드를 두지 않는다.
- worker 모델을 선택할 수 있어야 한다. Cursor 오케스트레이터 지원은 후속 항목으로 관리한다.

Python 코어 재사용, 첫 버전의 스킬+번들 도구, MCP 후속 확장은 이 설계의 권장 구현 방향이다. 기술적 근거 때문에 바꿔야 한다면 원인·대안·이관 비용을 먼저 문서화한다.

## 3. P0 조사와 계획

작업 시작 시 dirty 파일·현재 branch/revision·기존 데이터 위치를 확인한다. 사용자 변경을 reset하거나 덮어쓰지 않는다.

조사 대상:

- 실제 Codex version과 plugin command help, manifest와 스킬 발견 방식.
- 현재 공식 OpenAI 문서와 설치된 플러그인 형식의 차이.
- Python·Git 및 요청받은 worker 실행 파일·help.
- 사용자가 지정한 대상 Vikunja의 v2 OpenAPI와 최소 권한.
- 기존 registry/schema/spec/run/worktree와 구형 스킬 소유권.

설정 파일 전체를 출력하지 말고 필요한 비밀 아닌 필드만 읽는다. 서비스 URL이 없으면 mock/fixture 기반 코어 구현을 진행하면서 실제 연결 검증을 미확인으로 남긴다. 임의의 인스턴스·토큰·프로젝트를 선택하지 않는다.

`IMPLEMENTATION_PLAN.md`에는 다음을 적는다.

```text
현재 기준 revision과 기존 변경
확인한 실행 환경과 외부 계약
사용자 요구 U1–U7의 구현 위치
재사용·수정·제거할 코드
단계별 산출물과 수용 기준
설정·데이터 이관과 rollback
검증 계획과 실제 호출 범위
미확인 사항
설계와 다른 선택 및 이유
```

## 4. 구현 순서

[이관 계획](MIGRATION_PLAN.md)의 P1–P7을 따른다. 작동하는 기존 서비스를 추출하고 plugin launcher를 연결한 뒤 기능을 단계적으로 바꾼다. TypeScript 재작성·Node runtime·MCP server를 기본 선행 작업으로 넣지 않는다.

첫 plugin milestone은 깨끗한 환경에서 번들 `status`가 실행되는 것이다. 전체 완료는 설정·v2·이관·실행·검증·복구·실제 플러그인 로딩까지 요구한다.

v0는 Codex → Codex를 먼저 검증하고 Codex → Cursor도 같은 릴리스의 수용 범위로 둔다. Cursor 오케스트레이터 구현과 하위 보드 생성은 후속 항목이며 기록만으로 착수하지 않는다. Cursor 연동 구현을 요청받으면 BACKLOG의 공동 개발 절차와 실제 Cursor 세션의 수용 기준을 적용한다.

기존 API 호출을 v2로 옮길 때 route inventory를 만들고 HTTP verb·pagination·error·conditional update를 각기 확인한다. 단순 `/api/v1` 문자열 치환으로 마이그레이션하지 않는다.

기존 보드 연결과 새 보드 생성 로직을 섞지 않는다. 온보딩의 네트워크 요청은 읽기만 허용한다. 계정·프로젝트·뷰·열을 생성하거나 정렬하는 코드는 새 설정 경로에서 호출되지 않아야 한다.

## 5. 승인·실행·리뷰

실제 사용자 합의, 승인 명세 hash, 필수 검증 ID, task/repo identity를 run에 고정한다. 이미 주어진 승인을 같은 범위에서 반복 요구하지 않는다. 승인 기록을 임의로 만들어 내지 않는다.

쓰기 run은 Git common directory 단위로 하나만 허용한다. worker는 격리된 worktree와 승인 packet으로 실행하며 Vikunja에 직접 접근하지 않는다. 같은 사용자 환경이 OS 격리를 보장하는 것처럼 설명하지 않는다.

RESULT·실제 diff·검증 결과·명세를 비교하고 현재 fingerprint에서 필수 검증이 모두 통과해야 accept한다. 사용자의 최종 완료 의사 없이 Done을 수행하지 않는다. local integrate는 source checkout의 변경을 자동 정리하지 않는다.

Vikunja 실패와 worker 실패는 별도 상태다. 로컬 결과를 먼저 보존하고 모호한 외부 쓰기는 원격 상태 확인 전 재전송하지 않는다. Handrail 실행 중 코드가 통합됐다는 이유로 push를 호출하지 않는다.

## 6. 검증과 보고

변경한 기능에 필요한 의미 있는 테스트를 실행하고, 기존 명세 승인·diff·리뷰·통합 회귀 사례를 유지한다. 제품에서 제외한 관리형 Vikunja/원격 Git 기능의 테스트는 새 기본 동작을 요구하는 근거로 삼지 않는다. 유용한 이전 fixture는 개발 전용으로 남길 수 있다.

플러그인 패키징 정적 검사, 새 Codex 대화의 발견·실행, 실제 외부 서비스·worker 호출을 각각 기록한다. 모델 호출과 네트워크가 필요한 검증은 실행 범위를 분명히 하고 실제 수행한 것만 통과로 보고한다.

최종 보고에는 다음을 포함한다.

- 사용자에게 달라진 설치·연결·작업 흐름.
- 플러그인 산출물과 핵심 변경 파일.
- 설정·기존 데이터에 대한 이관 결과.
- 검증 명령·결과와 확인하지 못한 지원 범위.
- 설계에서 달라진 선택과 남은 작업.

기존 remote 설정을 바꾸거나 Handrail 기능으로 push를 시험하지 않는다. 원격 Git 동작은 별도 사용자 요청에 대한 Codex 작업이다.
