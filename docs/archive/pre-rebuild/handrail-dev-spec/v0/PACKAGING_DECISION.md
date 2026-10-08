# Codex·Cursor 패키징 판단

기준일: 2026-09-30. 공통 배포 구조를 선택하는 설계 판단이며 실제 플러그인 로딩·전체 작업 흐름의 통과 기록은 아니다.

사용자가 요청한 [Cursor CLI / Grok 4.7 검토](CURSOR_REVIEW.md)를 반영했다. 코어 공유와 호스트별 지원 검증 의견은 채택하고, 검증 전에 ZIP을 반드시 두 개 생성하자는 의견은 보류했다.

## 1. 권장 결론

**공통 Python 코어와 portable 플러그인 배포물 하나를 유지하고, 호스트별 설치 안내·연동 절차·지원 검증을 구분한다.** agent나 모델마다 별도 제품을 만들 필요는 없다. 첫 릴리스는 Codex 지원으로 한정하고, Cursor 오케스트레이터 지원은 후속 수용 기준을 통과한 뒤 표시한다.

| 구분 | 권장 방식 |
| --- | --- |
| 코어 소스 | Python 한 벌, 같은 설정·binding·run 계약 |
| 기본 배포물 | 루트 `plugin.json`을 가진 portable 플러그인 한 벌 |
| Codex 설정 | 현재 설계의 `.codex-plugin/plugin.json` 호환 manifest 생성 |
| Cursor 설정 | portable 형식을 우선 사용. native 기능이 필요할 때 `.cursor-plugin/plugin.json` 또는 전용 산출물 생성 여부 판단 |
| 설치 | Codex와 Cursor 각각의 설치·marketplace 경로로 등록 |
| 지원 판정 | 호스트와 CLI 버전별로 스킬 발견·실행·전체 작업 흐름 검증 |
| worker provider/모델 | 실행 프로필로 선택. worker나 모델별 플러그인 패키지는 불필요 |
| 호스트 의존성 | Python·Git·선택한 오케스트레이터 CLI·선택한 worker CLI. Cursor→Cursor에 Codex 설치를 강제하지 않음 |

공통 파일을 배포할 수 있어도 한쪽에 설치한 플러그인이 다른 쪽에 자동 등록되는 것은 아니다. worker는 승인된 packet을 받으므로 오케스트레이터용 플러그인을 worker 환경에 설치할 필요도 없다.

## 2. 확인한 근거

OpenAI 공식 문서는 루트 `plugin.json`과 `skills/`를 사용하는 portable 패키지를 설명하고 `.codex-plugin/plugin.json`을 호환 경로로 지원한다. root의 `extensions.com.openai`를 정의하면 호환 overlay와 합치지 않고 그 설정을 대신 사용한다. portable 패키지의 스킬은 root `skills/`에서 발견되며 overlay의 `skills`로 바꾸지 않는다. [OpenAI 패키징](https://developers.openai.com/plugins/build/plugins)

Cursor 공식 문서는 같은 Agent Plugins 형식과 Cursor native 형식을 모두 지원한다고 설명한다. native 형식은 rules·agents·commands·hooks 등의 추가 구성에 사용한다. 공식 사용자 안내는 CLI에서도 플러그인을 사용할 수 있다고 명시한다. [Cursor 형식](https://cursor.com/docs/reference/plugins), [Cursor 플랫폼 지원](https://cursor.com/help/customization/plugins)

로컬 Cursor CLI `2026.09.28-64d2043`의 도움말에서 `--plugin-dir`, `--workspace`, `--model`, `--mode ask/plan`, `--print`, `--sandbox`를 확인했다. 이 옵션의 존재와 특정 Handrail 산출물의 정상 로딩은 별도로 검증해야 한다.

따라서 현재의 스킬 + 번들 실행 도구 범위에서는 패키지 분리가 필수라는 근거가 없다. 서로 다른 설치 카탈로그나 안내 파일이 필요하다는 이유만으로 runtime과 정책을 복제하지 않는다.

## 3. 공통 계층과 호스트별 계층

공통 스킬에는 프로젝트 선택·보드 제한·명세·위임·리뷰의 의미를 둔다. 호스트 이름이 필요한 설치 방법, 실행 도구 경로 발견, TTY 설정 재개, 세션별 권한·취소 방식은 `references/hosts/codex.md`와 `references/hosts/cursor.md` 같은 호스트별 안내로 분리한다. 이 경로는 구현 시 생성할 목표 구조다.

스킬이 자신을 무조건 Codex라고 부르거나 Codex 전용 도구명을 공통 정책에 넣지 않도록 한다. 실제 명령은 같은 Python 서비스로 들어가며 호스트별 문서에서 승인·상태 전이를 재정의하지 않는다.

사용자 config·credentials·registry는 플러그인 cache 밖의 공통 Handrail 경로를 사용한다. Codex에서 등록한 A/B 프로젝트를 Cursor가 별도 복제하지 않는다. 동시 실행 잠금과 schema 검사는 두 호스트에 동일하게 적용한다. 호스트별로 설치된 runtime 버전이 다르면 run을 만든 버전과 호환되는지 확인하고 다른 버전으로 조용히 재개하지 않는다.

## 4. 별도 산출물이 필요한 조건

아래 상황이 실제로 확인되면 공통 소스에서 `handrail-codex`와 `handrail-cursor` 빌드 변형을 생성할 수 있다.

- 지원할 CLI 버전에서 portable 형식이나 혼합 manifest 발견 방식이 맞지 않는다.
- Cursor native rule·hook·agent 또는 Codex 전용 lifecycle 기능이 필수이고 하나의 디렉터리에서 양쪽 발견 규칙을 충족할 수 없다.
- 배포 카탈로그·서명·의존성 요구가 달라 같은 artifact를 등록할 수 없다.
- 후속 MCP 도입 시 환경변수·configuration 형식 차이를 공통 파일에서 처리할 수 없다.

MCP 경로 변수 차이는 이미 문서상 확인된다. Cursor는 표준 `${PLUGIN_ROOT}`·`${PLUGIN_DATA}`를 그대로 확장하지 않으므로 호스트별 구성을 검토해야 한다. 현재 v0에는 MCP 설정 파일이 없어 이 차이 때문에 지금 배포물을 나눌 필요는 없다. [Cursor MCP 설정](https://cursor.com/docs/reference/plugins#mcp-servers)

분리하더라도 core·schema·버전·명세·worker 정책은 같은 원본에서 생성한다. 두 패키지에서 공통 소스를 따로 유지하지 않는다.

## 5. Cursor 지원 선언 전 확인할 항목

1. 같은 artifact를 Codex와 Cursor CLI 각각에서 설치·발견하고 스킬이 한 번씩 나타나는지 확인한다.
2. Cursor CLI의 `--plugin-dir`로 임시 로딩한 경우와 실제 설치 경로를 각각 확인한다. IDE 동작만으로 CLI 검증을 대체하지 않는다.
3. plugin cache를 읽기 전용으로 두고 공백 경로·cache 갱신 뒤에도 번들 `status`가 동작하는지 확인한다.
4. 현재 repo·worktree·명시적 workspace 선택과 프로젝트별 부모 보드가 정확한지 확인한다.
5. 사용자 터미널에서 토큰 입력을 마친 뒤 해당 CLI 대화에서 설정을 이어갈 수 있는지 확인한다.
6. Cursor → Codex와 Cursor → Cursor의 모델 지정·취소·복구·검증·리뷰를 확인한다.
7. 서로 다른 호스트·runtime 버전에서 같은 repo의 쓰기 잠금과 진행 중 run 보호를 확인한다.

v0의 Codex 배포 형식을 유지하면서 이 항목들을 HR-NEXT-001에서 수행한다. 이번 설계 검토에서 Cursor CLI로 모델을 호출한 것은 리뷰 도구 사용의 증거이며 Handrail 플러그인 호환성 시험은 아니다.
