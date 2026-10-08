# 초기 설정과 사용자 설정 파일

이 문서의 명령과 JSON은 v0 목표 계약이다. 현재 0.2 CLI의 기능으로 오해하지 않도록 실제 구현 시 도움말·마이그레이션 안내를 함께 변경한다.

## 1. 사용자 흐름

```text
Codex에서 Handrail 플러그인 설치
  → 첫 Handrail 요청에서 설정 상태 확인
  → Vikunja가 있는지 확인
      없음: 공식 설치 안내 + 나중에 다시 연결
      있음: 서비스 URL 입력
  → 사용자 터미널에서 API 토큰 숨김 입력
  → API·프로젝트 조회 확인
  → 현재 디렉터리 이름을 기본 connection 이름으로 하여 프로필 저장 또는 기존 프로필 재사용
  → 연결할 Handrail 프로젝트 이름·로컬 Git 저장소 확인
  → 이 Handrail 프로젝트의 부모로 사용할 Vikunja 프로젝트 1개 선택
  → Kanban 뷰 선택
  → 상태 열 매핑 검토
  → 해당 저장소에 부모 보드 binding 저장
```

“설치할 때 연결 정보를 받는다”는 요구는 설치 직후 이어지는 온보딩으로 구현한다. 플러그인 관리자에 범용 설치 입력 폼이 있다고 가정하지 않는다. 이미 완성된 설정이면 이를 표시하고 반복 입력을 요구하지 않는다.

호스트에 플러그인은 한 번 설치하고 여러 Handrail 프로젝트를 등록할 수 있다. 두 번째 프로젝트부터는 기존 연결 프로필을 선택하고 그 프로젝트의 부모 보드를 별도로 고른다. 첫 프로젝트의 보드를 자동 배정하지 않는다. 저장소가 아직 없으면 연결 프로필까지만 확정하고, 선택한 보드는 이름을 부여한 해당 프로젝트의 로컬 설정 초안에 보관한다. 초안은 다른 신규 프로젝트의 전역 기본값으로 사용하지 않는다.

연결 설정에서 이름을 생략하면 명령을 실행한 현재 디렉터리의 마지막 경로 구성요소를 connection 이름으로 사용한다. 예를 들어 `/project_workspace/handrail_workspace`에서 실행하면 `handrail_workspace`다. 명시한 `--name`은 기본값을 덮어쓴다. 여러 프로필의 이름이 같을 수 있으므로 프로필을 선택·나열할 때는 `이름 (profile-id)` 형식으로 표시한다.

## 2. Vikunja가 없는 경우

사용자가 아직 서비스를 준비하지 않았다고 답했거나 URL이 비어 있으면 다음과 같이 안내한다.

> Handrail을 연결하려면 사용할 Vikunja가 필요합니다. Vikunja 설치 안내에 따라 서비스를 준비한 뒤 URL과 API 토큰을 등록해 주세요. 준비되면 “Handrail 연결 설정해줘”로 계속할 수 있습니다.

공식 링크: [Vikunja 설치 안내](https://vikunja.io/docs/installing/).

Handrail은 Docker 존재 여부로 Vikunja 설치 유무를 판정하지 않는다. 서비스가 다른 호스트에 있을 수 있기 때문이다. URL 접속 실패도 설치되지 않았다는 증거는 아니다. 연결 거부·DNS·TLS·timeout·인증 실패를 각각 안내한다.

새 기본 설치에는 Docker, kanban data directory, DB 경로, 계정 생성, 기본 비밀번호가 없다. 기존 테스트 fixture의 Docker는 제품 의존성으로 표시하지 않는다.

## 3. 입력 항목

| 항목 | 입력 방식 | 저장 위치 |
| --- | --- | --- |
| 연결 이름 | 실행한 현재 디렉터리의 마지막 이름 (선택적으로 `--name` 지정) | 사용자 config |
| Vikunja 서비스 URL | Codex 대화 또는 터미널 | 사용자 config |
| API 토큰 | 사용자가 직접 조작하는 터미널의 숨김 입력 | 사용자 credentials 파일 |
| 토큰 권한 | 설치 안내를 보고 Vikunja token에서 project·view·bucket 관리와 task read/create/update/move, 필요 시 task relation create 허용 | Vikunja token policy |
| Handrail 프로젝트 | 이름과 로컬 Git 저장소 확인 | 로컬 registry, repo 설정 |
| 부모 Vikunja 프로젝트 | 접근 가능한 목록에서 1개 선택, ID·상위 경로 함께 표시 | 해당 repo binding |
| 부모 Kanban 뷰 | 선택한 프로젝트의 뷰 목록에서 1개 선택 | 해당 repo binding |
| 상태 열 | 기존 열 목록을 의미 상태에 매핑 | 해당 repo binding |
| 로컬 Git 저장소 | 현재 Git root 확인, 필요할 때만 경로 입력 | 로컬 registry |
| 계정 표시명 | 필요할 경우 별칭 또는 허용된 API 조회 결과 | 사용자 config, 선택 사항 |

API 토큰이 인증 수단이므로 사용자명·비밀번호를 필수 입력으로 받지 않는다. 계정 표시명은 인증에 사용하지 않는다. 프로젝트 이름이 같은 항목이 있으면 ID·경로를 보고 선택해야 한다.

## 4. 토큰 입력 경계

스킬은 URL·프로젝트 같은 일반 정보를 대화로 수집할 수 있다. 실제 토큰 입력은 사용자 터미널에서 번들 도구의 `setup` 또는 `connection rotate`를 직접 실행해 받는다.

입력 터미널은 Handrail이 실행될 호스트와 사용자 파일 시스템에 있어야 한다. 원격 Codex 환경에 연결했다면 사용자의 노트북 홈에 저장한 토큰을 원격 환경이 자동으로 읽을 수 있다고 가정하지 않는다. 설정 결과에는 비밀값 없이 실행 호스트와 저장 위치를 표시한다.

- `getpass`가 echo를 끌 수 있는 TTY인지 확인한다. 숨김 입력을 제공할 수 없으면 입력 전에 `INTERACTIVE_SECRET_INPUT_REQUIRED`로 종료한다.
- 에이전트가 토큰을 받아 PTY의 stdin에 대신 써 넣지 않는다. 그 도구 호출 자체가 기록에 남을 수 있다.
- token CLI 인자, 채팅 입력, 승인 질문의 텍스트 필드로 비밀값을 요구하지 않는다.
- 입력 후 메모리에서 읽기 검증을 하고 저장한다. 터미널·JSON 결과에는 token 문자열이나 마지막 몇 글자도 출력하지 않는다.
- 원격 사용자 UI가 비밀 입력을 안전하게 지원하지 않으면 실행 위치와 터미널 명령을 안내하고 `setup_pending`을 유지한다.
- 자동화는 기존에 준비한 비밀 파일 또는 명시적으로 선택한 환경변수를 사용할 수 있다. 값이 포함된 명령을 생성하지 않으며, 이 방식은 일반 사용자 기본 흐름이 아니다.

사용자는 비밀값을 직접 입력하고 에이전트는 성공 여부와 연결 상태를 확인한다. 현재 API 토큰은 웹 UI의 Settings → API Tokens에서 발급하는 방식으로 안내한다. [Vikunja 인증 문서](https://vikunja.io/docs/api-documentation/)

## 5. URL·API·권한 확인

URL은 서비스 기준 주소로 받는다. subpath 배포는 경로 prefix를 유지하고, task URL이나 `/api/v1`, `/api/v2` URL을 받으면 정규화한 서비스 주소를 보여준다. 내장 사용자명·비밀번호·query·fragment가 있는 URL은 거부한다.

HTTPS를 기본으로 안내한다. loopback HTTP는 로컬 사용으로 허용하고, 그 외 HTTP는 토큰이 암호화되지 않음을 보여준 뒤 사용자가 선택한 연결에만 `allow_insecure_http`를 기록한다. 인증된 요청에서 리다이렉트를 자동으로 따라가지 않는다.

연결 점검 순서:

1. 대상 인스턴스의 `/api/v2/openapi.json`과 필요한 API 기능을 확인한다.
2. 토큰으로 프로젝트 목록을 페이지 끝까지 읽는다.
3. 선택한 project의 접근·수정 권한 정보를 확인한다.
4. 해당 project의 views와 선택한 view의 buckets를 읽는다.
5. 기능별 capability를 `verified|declared|unknown|missing`으로 기록한다.

공개 OpenAPI가 인증을 요구하는 서버라면 같은 origin에만 인증을 붙여 재조회한다. HTML 로그인 페이지, 프록시 404, 네트워크 실패를 “v2 미지원”으로 단정하지 않는다. 실제 계약을 확인하지 못하면 해당 사유를 반환하고 설정을 이어갈 조치를 안내한다.

읽기 성공만으로 댓글·상태 쓰기 권한이 있다고 표시하지 않는다. 서버가 노출하는 프로젝트 권한·토큰 scope를 확인하고, 실제 쓰기 성공은 최초 승인된 작업에서 판정한다. 권한 검사용 임시 task/comment를 자동 생성하지 않는다.

필요 권한은 프로젝트·뷰·열·task·댓글·첨부 읽기와, 사용할 기능의 task 상태 변경·댓글 작성이다. 새 카드 작성·첨부 업로드·label 변경은 그 기능을 사용하는 경우만 요구한다. 사용자 생성·공유 권한 관리·서버 관리 권한은 필요하지 않다. 구체 scope 이름은 대상 서버가 제공하는 권한 목록에 맞춘다.

후속 하위 보드 생성 기능을 선택하면 부모 쓰기 권한과 프로젝트·뷰·bucket 생성/설정 권한을 별도로 확인한다. 기본 연결에 이 확장 권한을 강제하지 않는다. [권한별 작업](PROJECT_HIERARCHY.md)을 참고한다.

v0는 API v2를 사용한다. v2 부재가 확인되면 업그레이드·관리자 문의 안내를 제공한다. 자동으로 v1에 전환하거나 서버를 업그레이드하지 않는다. v2의 구조와 대상 인스턴스 명세 확인 원칙은 [공식 API v2 문서](https://vikunja.io/docs/api-v2/)를 따른다.

## 6. 기존 보드 선택과 매핑

Vikunja의 보드는 project 안의 Kanban view다. 프로젝트만 선택하고 임의의 뷰를 만드는 방식으로 연결을 완료하지 않는다. [Vikunja Views](https://vikunja.io/help/views/)

초기 설정은 **읽기 요청만** 수행한다.

1. 해당 Handrail 프로젝트의 부모가 될 프로젝트 하나를 선택한다. 목록이 없으면 권한 확인 또는 Vikunja UI에서 프로젝트 준비를 안내한다.
2. 해당 프로젝트의 Kanban 뷰를 선택한다. 지원되지 않는 필터/자동 bucket 방식은 그 이유를 보여준다.
3. todo/doing/review/done에 사용할 기존 bucket ID를 각각 선택한다.
4. 이름·ID·현재 done/default bucket 설정을 요약하고 매핑을 저장한다.

이름이 일치하면 후보를 제안할 수 있지만 중복·다국어·필터·done 의미를 검증해야 한다. 기본 4개 의미 상태는 서로 다른 bucket에 연결한다. 상태 열이 부족하면 사용자가 Vikunja에서 열이나 별도 뷰를 준비한 뒤 다시 조회한다. 연결 명령은 기존 열을 rename/reorder/delete하거나 task를 이동하지 않는다.

view/project가 삭제되거나 ID가 바뀌면 `BOARD_MAPPING_INVALID`로 중단하고 다시 선택한다. 표시 이름 변경만으로는 연결이 끊기지 않는다. 수용한 매핑 revision과 다른 뷰로 활성 run을 조용히 이동시키지 않는다.

초기 연결에서는 부모 보드 하나만 등록한다. inbox·frontend·backend를 기본 생성하지 않는다. 개발 중 사용자가 요청하면 `area create`로 부모 아래 하위 프로젝트와 작업용 Kanban을 생성·등록한다. 하위 보드의 필수 상태는 todo/doing/done이며 review bucket은 요구하거나 만들지 않는다. 부모만으로도 계획/작업 흐름을 사용할 수 있다. 기존 하위 프로젝트가 보여도 자동으로 작업 대상으로 포함하지 않는다. 다른 Handrail 프로젝트가 이미 사용하는 부모 또는 그 아래 프로젝트를 고르면 소유 범위 충돌을 보고하며 자동 재사용하지 않는다.

## 7. 파일 위치

| 기본 위치 | 역할 | Git 공유 |
| --- | --- | --- |
| `~/.config/handrail/config.json` | 연결 프로필·URL·credential 참조, worker 프로필 | 아니오 |
| `~/.config/handrail/credentials/<credential-id>.json` | API 토큰 | 아니오 |
| `~/.local/share/handrail/registry.v2.json` | workspace 경로와 로컬 연결 프로필 매핑 | 아니오 |
| `~/.local/share/handrail/projects/<workspace-id>/runs/` | run·round·검증·게시 기록 | 아니오 |
| `~/.local/share/handrail/projects/<workspace-id>/worktrees/` | 위임 checkout | 아니오 |
| `~/.local/share/handrail/setup/<workspace-id>.json` | 저장소 연결 전 프로젝트별 설정 초안, 비밀값 제외 | 아니오 |
| `~/.local/share/handrail/locks/` | Git common directory 기준 잠금 | 아니오 |
| `<repo>/.handrail/project.json` | 공유 가능한 프로젝트·보드 식별과 상태 매핑 | 예 |
| `<repo>/.handrail/specs.json` | 명세 승인과 해시 | 예 |
| `<repo>/docs/specs/` | 작업 명세 | 예 |
| `<worktree>/.handrail/runtime/` | worker에게 전달한 packet과 결과 | 아니오 |

`XDG_CONFIG_HOME`과 `XDG_DATA_HOME`이 있으면 그 아래 `handrail`을 사용한다. 새 경로 규칙은 한 모듈에서 계산한다. 기존 `HANDRAIL_HOME`은 구형 데이터 위치로 인식하고 이관 입력으로 사용한다. 임의로 HOME을 덮어써 경로를 맞추지 않는다.

config·credentials·registry 디렉터리는 0700, 파일은 0600을 사용한다. 파일 쓰기는 임시 파일·fsync·atomic replace로 처리한다. 소유자·symlink·파일 유형·부모 경로를 검사하고 다른 사용자 파일이나 연결된 경로를 덮어쓰지 않는다. Git에 공유되는 파일에는 토큰과 로컬 절대 경로를 넣지 않는다.

## 8. JSON 예시

### 사용자 config

```json
{
  "schema_version": 2,
  "profiles": {
    "profile-example": {
      "instance_id": "instance-example",
      "label": "팀 Vikunja",
      "base_url": "https://tasks.example.com",
      "api_version": "v2",
      "credential_id": "credential-example",
      "allow_insecure_http": false
    }
  },
  "worker_profiles": {
    "codex-default": {"provider": "codex", "model": null},
    "cursor-default": {"provider": "cursor", "model": null}
  }
}
```

예시 ID는 설명용이다. 실제 workspace/profile/instance/credential ID는 충돌을 피하는 UUID를 쓴다. `instance_id`는 Handrail이 연결을 구분하는 논리 ID이며 Vikunja가 인증한 서버 고유 ID라고 주장하지 않는다.

`credential_id`는 지정 디렉터리 안의 파일 이름을 결정하는 식별자다. 임의 파일 경로를 config에서 받아 읽지 않는다. 한 인스턴스에 여러 계정 프로필을 만들 수 있고 profile은 각자의 credential을 참조한다.

`profiles`는 Vikunja 연결용이고 `worker_profiles`는 구현 CLI 선택용이다. 서로 다른 종류의 프로필을 혼용하지 않는다. worker의 `model`은 해당 provider가 지원하는 모델 식별자를 저장하며 null이면 CLI 기본값을 뜻한다. 현재 지원 모델명을 문서에서 고정하지 않는다.

### 토큰 파일의 구조

```json
{
  "schema_version": 1,
  "profile_id": "profile-example",
  "token": "<interactive-input-only>",
  "expires_at": null
}
```

위 문자열은 문서용 자리표시자이며 실제 설정 예제로 실행·배포하지 않는다. API가 만료 정보를 확인해 주지 않으면 `expires_at`은 null이다. 토큰의 내용을 해석해 만료나 권한을 추정하지 않는다.

### 저장소의 공유 연결 정보

```json
{
  "schema_version": 2,
  "id": "workspace-example",
  "name": "atlas",
  "binding_revision": 1,
  "binding": {
    "instance_id": "instance-example",
    "project_id": 42,
    "view_id": 7,
    "states": {"todo": 11, "doing": 12, "review": 13, "done": 14}
  },
  "worker": {"profile": "codex-default", "model": null},
  "snapshot": "docs/handrail-summary.md"
}
```

실제 접근에는 로컬 registry의 `workspace_id → profile_id`가 추가로 필요하다. Git clone만으로 다른 사람의 연결 프로필을 자동 선택하지 않는다. 같은 logical instance를 사용할 로컬 URL·프로필을 사용자가 연결하고 실제 project/view를 확인한다. 두 값이 충돌하면 쓰기를 거부한다.

`binding`은 이 Handrail 프로젝트의 부모 보드 하나를 뜻한다. 연결 프로필에는 `default_board`를 두지 않는다. 같은 프로필을 쓰는 다른 저장소에는 별도 workspace ID와 부모 binding을 지정한다. 기존 config에 전역 기본 보드가 있다면 이관 시 후보로만 표시하고 저장소별 연결을 확인한다. 부모 보드를 바꾸려면 해당 저장소의 binding을 명시적으로 갱신하고 활성 run이 없는지 확인한다.

기존 다중 area는 선택적 `areas` 객체로 표현한다. 각 항목은 부모 binding과 같은 project/view/states 구조에 `parent_project_id`를 추가하며 같은 instance의 해당 부모 아래에 속해야 한다. 신규 연결에서는 `areas`를 생략한다. 기존 area의 계층이 다르면 서버에서 자동 이동하지 않고 이관 충돌로 보고한다. 후속 추가 흐름은 [프로젝트 계층 문서](PROJECT_HIERARCHY.md)를 따른다.

`worker`는 선택 사항이다. 실행별 선택이 없으면 이 프로젝트의 프로필을 사용하고, 없으면 v0 기본 `codex-default`를 사용한다. 모델은 실행별 지정 → 같은 선택 프로필에 대한 프로젝트 설정 → 프로필 설정 → CLI 기본값 순서로 적용한다. null은 다음 단계로 넘긴다는 뜻이다. 다른 프로필로 변경한 실행에는 기존 프로젝트의 모델 덮어쓰기를 적용하지 않는다. 참조한 프로필이 없으면 재선택을 안내하며 임의 provider로 대체하지 않는다.

### 같은 호스트의 두 프로젝트

로컬 registry는 최소한 다음 관계를 유지한다. 경로와 ID는 설명용이다.

| workspace | 로컬 Git root | 연결 프로필 | 부모 project/view | run 경로 |
| --- | --- | --- | --- | --- |
| atlas | `/work/atlas` | `profile-example` | `42 / 7` | `projects/<atlas-id>/runs/` |
| beacon | `/work/beacon` | `profile-example` | `84 / 19` | `projects/<beacon-id>/runs/` |

현재 Git root 또는 명시적 인자로 프로젝트를 결정하고 대화·run에 고정한다. 다른 터미널에서 전역 선택을 변경해도 실행 중인 프로젝트는 바뀌지 않는다. 저장소 밖에서 대상이 모호하면 프로젝트를 선택하도록 한다. 두 프로젝트는 서로 다른 Git common directory일 때 독립적으로 실행할 수 있다.

## 9. 저장·재설정·삭제

설정은 초안을 메모리에서 검증한 뒤 기록한다. 토큰 파일을 먼저 안전하게 생성하고 config가 그 credential ID를 참조하도록 atomic replace한다. 시작 중 중단으로 참조되지 않는 파일이 생기면 진단에서 알려주고 확실히 미참조인 파일만 정리한다. config가 없는 토큰 파일을 참조하는 상태를 성공으로 반환하지 않는다.

토큰 교체는 새 credential ID에 기록 → 새 토큰 읽기 접근 검증 → profile 참조 교체 → 이전 로컬 토큰 파일 정리 순서다. 실패하면 기존 연결을 유지한다. token generation을 바꿀 때 실행 중인 작업이 어느 세대를 사용하는지 기록하고, 이후 요청은 명확한 경계에서 새 토큰을 로드한다.

`connection forget`은 해당 로컬 연결과 토큰만 제거한다. 연결된 저장소가 있으면 목록과 사용 불가 상태를 설명하고 명시적인 삭제 요청 범위에서 처리한다. 서버의 토큰 폐기는 Vikunja UI에서 별도로 해야 한다. 플러그인 업데이트는 설정 파일을 덮어쓰지 않고, 플러그인 제거도 사용자 데이터가 자동 삭제된다고 가정하지 않는다.

진단·요약·export·run·게시 payload에는 토큰을 포함하지 않는다. 오류 본문과 subprocess 출력에도 등록한 secret 값을 기준으로 masking을 적용한다. 문자열 prefix 정규식만으로 모든 비밀 제거가 보장된다고 판단하지 않는다.

## 10. 실패 UX

| 상황 | 사용자에게 보여줄 결과 | 저장·재시도 |
| --- | --- | --- |
| Vikunja 미준비 | 설치 링크, 준비 후 연결 방법 | installed 유지 |
| 연결 실패 | 주소·네트워크·TLS 중 확인할 항목 | 기존 정상 config 유지 |
| 토큰 거부 | 인증 실패, 새 토큰 발급·교체 안내 | 실패 토큰을 정상 연결로 저장하지 않음 |
| 권한 부족 | 부족한 기능과 선택 프로젝트 | 전체 관리자 권한을 일괄 요구하지 않음 |
| v2 부재 확인 | 지원 API 필요, 관리자 문의 | v1 자동 fallback 없음 |
| 프로젝트/뷰 없음 | 목록 재조회·UI에서 준비 안내 | connection_ready까지 보존 가능 |
| bucket 매핑 충돌 | 충돌하는 상태·ID 설명 | board_ready로 처리하지 않음 |
| 사용자가 취소 | 완료한 설정 단계와 재개 방법 | 기존 정상 설정 보존 |
| 터미널 입력 불가 | 사용자 터미널에서 수행할 명령 | 토큰을 채팅으로 받지 않음 |
| 보드 변경·삭제 | 재연결 필요 | 다른 ID로 자동 대체하지 않음 |

GitHub·Forgejo 선택, 원격 URL, SSH 키, push 테스트는 이 설정 흐름에 포함하지 않는다.
