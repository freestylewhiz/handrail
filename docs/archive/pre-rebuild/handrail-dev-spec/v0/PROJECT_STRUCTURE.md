# 소스 구조와 최종 플러그인 배포물

## 1. 구현 전략

현재 Python 코어를 유지한다. 스킬·내부 launcher·빌드 정의를 더해 Codex 플러그인으로 묶는다. CLI는 코어의 개발·진단용 인터페이스로 남으며, 최종 사용자가 Handrail Python 패키지를 별도로 설치해야 하는 구조는 만들지 않는다.

v0 런타임은 현재의 표준 라이브러리 중심 구조를 유지한다. Python과 Git, Codex는 호스트 의존성이다. Cursor는 위임을 선택했을 때의 의존성이다. Vikunja는 사용자가 준비한 외부 서비스다. Docker와 Node.js는 필수 런타임 의존성이 아니다.

Cursor 오케스트레이터 확장에서도 공통 소스와 portable 배포물을 우선 유지한다. 호스트별 설치·스킬 연동·지원 검증을 구분하고, 규격 차이가 실제로 요구할 때만 같은 소스에서 별도 산출물을 만든다. 판단 근거는 [PACKAGING_DECISION.md](PACKAGING_DECISION.md)에 있다.

## 2. 목표 소스 트리

```text
handrail/
├── pyproject.toml
├── README.md
├── handrail/                         # 유일한 Python 구현 소스
│   ├── __init__.py
│   ├── cli.py                       # argv/JSON, 서비스 호출
│   ├── core.py                      # 파일·시간·오류 공통부
│   ├── config.py                    # XDG 경로·schema·TokenStore
│   ├── connections.py               # 프로필·토큰 교체·연결 진단
│   ├── onboarding.py                # TTY 입력·단계별 setup
│   ├── projects.py                  # 로컬 repo 등록·선택·binding
│   ├── board.py                     # task·상태 매핑·소속 검사
│   ├── api.py                       # v2 HTTP adapter
│   ├── specs.py                     # 명세·승인·검증 계획
│   ├── context.py                   # packet·첨부 materialize
│   ├── workers.py                   # Codex/Cursor provider adapter
│   ├── runs.py                      # run store·잠금·복구·게시 상태
│   ├── supervisor.py                # 긴 프로세스 감독·취소
│   ├── workflow.py                  # start/verify/review/integrate
│   └── migrations.py                # 구형 설정·참조 이관
├── plugins/
│   └── handrail/
│       ├── plugin.json              # portable manifest 원본
│       ├── skills/
│       │   └── handrail/
│       │       ├── SKILL.md
│       │       └── references/
│       │           ├── setup.md
│       │           ├── workflow.md
│       │           └── recovery.md
│       ├── scripts/
│       │   └── handrail.py          # 번들 runtime을 여는 launcher
│       └── templates/
│           ├── TASK.md
│           ├── CONTEXT.md
│           ├── RESULT.md
│           └── WORKER.md
├── scripts/
│   ├── build_plugin.py
│   └── validate_distribution.py
├── tests/
│   ├── ...                         # 기존 회귀 사례 유지
│   ├── fixtures/
│   └── docker/                     # 개발 전용, 배포 제외
├── handrail-dev-spec/v0/
└── dist/                           # 생성물, Git 제외
```

위 구조는 목표 책임을 보여준다. 새 파일을 모두 빈 상태로 만든 뒤 전면 이동하지 않는다. 실제 기능 변경 때 해당 책임을 기존 모듈에서 추출한다. `api.py`를 package로 나눌 필요가 생기기 전에는 v2를 한 adapter로 유지한다.

## 3. 최종 산출물

```text
dist/
├── handrail-<release-version>.zip
├── SHA256SUMS
└── handrail/
    ├── plugin.json
    ├── .codex-plugin/
    │   └── plugin.json             # 생성된 Codex 호환 manifest
    ├── skills/handrail/...
    ├── scripts/handrail.py
    ├── runtime/handrail/...
    ├── templates/...
    ├── README.md                   # 사용자용 설치·초기 설정 안내
    ├── LICENSE
    └── build-info.json             # 버전·소스 revision·파일 checksum
```

ZIP 최상위 디렉터리와 plugin name은 `handrail`로 통일한다. `runtime/handrail`은 Python 원본에서 빌드 시 복사한 산출물이다. 사람이 두 번째 구현으로 수정하지 않는다. 현재 패키지 리소스를 참조하는 코드가 남아 있다면 필요한 리소스를 명시적으로 포함하고 누락 검사를 한다.

배포 버전은 프로젝트 릴리스 버전에서 생성한다. root manifest, 호환 manifest, Python 버전, build-info가 달라지면 빌드를 실패시킨다. 설계 디렉터리 이름 `v0`를 배포 semver로 사용하지 않는다.

포함 파일은 allowlist로 지정한다. 테스트·개발 Compose·로컬 registry·credentials·run·worktree·`.env`·Git 메타데이터·가상환경은 배포물에서 제외한다.

## 4. Manifest 정책

현재 공식 문서는 root `plugin.json`을 portable entry로 설명하며 기존 `.codex-plugin/plugin.json`을 호환 형식으로 지원한다. OpenAI 전용 설정을 두 위치에 동시에 중복 정의하지 않도록 한다. [공식 패키징 문서](https://developers.openai.com/plugins/build/plugins)

v0 빌드의 기준:

1. 루트 `plugin.json`에서 portable identity와 schema를 정의한다.
2. 같은 메타데이터로 `.codex-plugin/plugin.json`을 생성한다.
3. 첫 버전의 OpenAI 표시 정보는 호환 manifest에 두고, root의 `extensions.com.openai`는 생략해 우선순위 충돌을 피한다.
4. portable 패키지는 root `skills/`를 자동 발견한다. 호환 manifest의 `skills: ./skills/`는 legacy 호환 정보이며 portable 발견 규칙을 바꾸지 않는다.
5. 존재하지 않는 MCP·app·hook 파일을 manifest에서 참조하지 않는다.
6. 실제 지원 Codex 버전에서 스킬이 중복으로 나타나지 않고 번들 경로가 해석되는지 검사한다.

이 정책은 현행 설치 환경과 portable 문서 사이의 호환을 위한 제안이다. root와 overlay의 실제 검증기는 구분하고, 한 형식용 검증기를 다른 형식의 유효성 근거로 사용하지 않는다.

## 5. 실행 도구 찾기와 실행

스킬은 자신의 설치 파일 위치에서 `../../scripts/handrail.py`를 찾는다. Codex가 로드한 SKILL.md의 실제 경로를 기준으로 canonical path를 계산하고 파일을 확인한다. 사용자 개발 저장소를 cwd로 둔 채 설치 위치와 실행 위치를 구분한다.

대표 호출 형태:

```text
python3 -I <plugin-root>/scripts/handrail.py status
python3 -I <plugin-root>/scripts/handrail.py setup
python3 -I <plugin-root>/scripts/handrail.py project bind --repo <absolute-git-root>
```

위 명령은 문법 설명용이다. 실제 도구는 경로를 인자 단위로 전달해 공백·한글·shell 메타문자가 실행 문자열로 해석되지 않게 한다. 토큰 값은 인자에 넣지 않는다.

launcher는 자신의 파일 위치에서 번들 `runtime`을 찾고 그 안의 `handrail`만 로딩한다. 설치된 글로벌 `handrail`, PYTHONPATH, 현재 저장소의 같은 이름 모듈에 의존하지 않는다. Python 버전·런타임 리소스가 맞지 않으면 설치 안내와 명확한 오류를 출력한다.

플러그인 cache는 읽기 전용 배포물로 취급한다. `.pyc`, 설정, token, 가상환경, 실행 결과를 그 안에 쓰지 않는다. 바이트코드 기록은 끄고 모든 가변 데이터는 사용자 경로와 작업용 runtime에 둔다. 업데이트로 cache 경로가 바뀌어도 기존 설정과 실행 기록이 살아 있어야 한다.

## 6. 스킬과 worker

첫 버전은 `handrail` 스킬 하나로 시작한다. 설정·작업·복구의 세부 절차는 목적별 reference로 분리한다. 스킬은 사용자가 명령어를 외우게 하지 않고 자연어 요청을 해당 기능으로 연결한다.

Cursor 지원 시 공통 스킬과 `references/hosts/` 아래 호스트별 안내를 사용한다. 두 호스트가 공통 사용자 config·registry·workspace 기록을 읽으며 캐시 안에 호스트별 사용자 데이터를 복제하지 않는다. 호스트별 승인 UI가 공통 코어의 승인 조건을 대신하지 않는다.

provider별 worker는 Codex 플러그인 설치를 전제로 하지 않는다. 필요한 role 지시·TASK·CONTEXT·명세를 worktree packet으로 전달하고 기존 저장소의 AGENTS.md를 읽게 한다. 플러그인 설치가 사용자 저장소 AGENTS.md를 무조건 수정하거나 manager 스킬 전체를 복사하는 동작을 포함하지 않는다.

기존 전역/프로젝트 스킬의 자동 삭제는 하지 않는다. 이관 때 소유권과 내용 hash를 확인하고, 사용자 수정이 있으면 비교 결과를 제공한다. 같은 이름의 구형 스킬이 실행 우선순위를 가리는 경우 설정 진단에서 설명한다.

## 7. 배포·업데이트

빌드는 플러그인 디렉터리와 검증 가능한 ZIP·checksum을 만든다. 첫 배포 경로는 Codex가 지원하는 로컬/개인 marketplace에서 설치해 검증하는 방식이다. 카탈로그의 `source.path`는 실제 marketplace root 기준으로 만든다. 사용자의 Codex 설정을 설치 프로그램이 임의로 덮어쓰지 않는다.

현재 환경에서 `codex plugin --help`에 add/list/marketplace/remove가 있다는 것만 확인했다. 세부 설치 인자는 구현 시 해당 버전 help로 확정한다. ZIP 생성만으로 Codex 설치 성공·공개 디렉터리 게시 완료를 선언하지 않는다.

재설치는 버전·cache 갱신 규칙을 따르고 새 대화에서 스킬·번들 runtime 버전이 맞는지 확인한다. 진행 중 run은 시작한 runtime 버전을 기록하고, 그 버전이 제거되면 다른 버전으로 조용히 재개하지 않는다. 완료·보존·명시적 이관 중 적합한 경로를 선택한다.

Handrail 자체 배포 저장소에 빌드·릴리스 설정이 있을 수는 있다. 이는 Handrail을 사용하는 개발 프로젝트의 remote를 제품이 관리한다는 뜻이 아니다.

## 8. MCP 확장 지점

MCP가 필요해지면 `handrail/mcp_server.py`와 검증된 SDK 의존성을 추가하고 동일 서비스에 연결한다. HTTP 서버를 상시 운영하는 구조를 기본으로 도입하지 않는다.

후속 작업에서 확정할 사항:

- stdio 서버 시작, plugin root 해석, 실제 호스트가 지원하는 configuration 형식.
- MCP SDK와 Python 의존성의 번들·설치·업데이트 방식.
- 긴 run 조회·취소, 구조화된 오류, host가 허용한 repository 범위.
- 토큰을 tool argument나 응답으로 전달하지 않는 초기 설정 경로.

v0에는 비어 있는 `mcp.json`, `.mcp.json`, 가짜 MCP status server를 넣지 않는다. MCP가 추가돼도 승인·보드 제한·상태 전이를 우회할 수 없다.
