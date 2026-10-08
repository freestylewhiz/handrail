# 설치와 첫 연결

현재 소스 버전은 v0.5.0입니다. `python3 scripts/build_plugin.py --output dist/v0.5.0`으로 빌드하고
`python3 scripts/validate_distribution.py dist/v0.5.0`으로 배포 묶음을 검증할 수 있습니다. 이는 로컬 source build 절차이며 공개 게시 또는 호스트 설치를 뜻하지 않습니다.
아래 GitHub 설치 명령은 역사적인 RC4 후보를 설치합니다. v0.4 권한 기능과 v0.4.1 하위 작업 보드는 해당 후보에 포함되지 않습니다. v0.4 실제 기능은 [권한 사용법](permissions-v0.4.md)을 참조하세요.
v0.5.0의 Herdr 연동 경로는 개발 중이며, 기존 `run` 흐름과 별도입니다. [Herdr workflow](herdr-workflow.md)와 [acceptance 설계](testing/herdr-acceptance.md)는 목표 동작과 검증 절차를 설명하며 완료된 수용 검증 결과를 뜻하지 않습니다.

아래 설치/연결 안내의 기존 acceptance evidence는 Handrail 0.4.1 기준 기록입니다. 그 당시 검증 환경은 Rocky Linux 9.7, Python 3.9, Codex CLI 0.157.1, Cursor CLI 2026.09.28, Vikunja 2.6.0입니다. 이는 v0.5.0 또는 Herdr 경로의 검증 결과가 아니며, 다른 OS와 버전을 지원한다고 주장하지 않습니다.

## 준비

- Linux 호스트에서 Git과 Python 3.9 이상을 사용할 수 있어야 합니다.
- Codex CLI에 로그인하고, Codex 대화를 시작할 repository가 있어야 합니다.
- Vikunja v2는 사용자가 준비하고 운영합니다. 설치 방법은 [Vikunja 공식 설치 안내](https://vikunja.io/docs/installing/)를 따르세요. Handrail은 Docker나 Vikunja 계정·서버를 설치하거나 관리하지 않습니다.
- 각 repository에 연결할 Vikunja 부모 프로젝트 하나와 manual Kanban view 하나가 있어야 합니다. 계획 카드는 부모 보드에서 목표·범위·완료 기준 및 사용자 Review를 관리합니다. 구현·조사·후속 보완은 계획에 연결된 새 작업 카드로 기록합니다. 필요할 때 `area create`로 하위 프로젝트와 작업용 Kanban을 추가할 수 있으며, 하위 보드는 Todo/Doing/Done만 필수이고 Review 없이 작업 이력을 보존합니다. 부모의 Review가 없으면 선택한 프로젝트·view와 상태 매핑을 보여준 뒤 확인을 받고 생성합니다.

GitHub의 고정 후보 태그에서 플러그인을 설치합니다.

```sh
codex plugin marketplace add freestylewhiz/handrail --ref plugin-v0.3.0-rc.4
codex plugin add handrail@handrail
codex plugin list
```

Codex에서 연결할 Git repository를 열고 Handrail 스킬을 사용할 수 있는 새 대화를 시작합니다. 플러그인에는 Python runtime이 포함되어 있으므로 별도 Handrail pip 설치가 필요하지 않습니다. 호스트에는 Python 3.9+와 Git이 필요합니다.

## 기존 공개 플러그인 업데이트

이미 `handrail` 마켓플레이스를 다른 태그로 등록했다면 먼저 등록된 소스를 제거하고 새 태그로 다시 등록합니다. 이 명령은 Handrail의 연결 프로필이나 Vikunja 데이터를 삭제하지 않습니다.

```sh
codex plugin marketplace remove handrail
codex plugin marketplace add freestylewhiz/handrail --ref plugin-v0.3.0-rc.4
codex plugin add handrail@handrail
codex plugin list --marketplace handrail
```

RC4 공개 버전인지 확인하고 **새 Codex 세션**을 시작합니다. 이전 세션은 예전 스킬 경로를 유지할 수 있습니다. 플러그인 설치에는 마켓플레이스 메타데이터도 필요하므로 위 명령은 전체 배포 저장소를 받습니다.

## 연결 토큰 입력

토큰은 Codex 채팅이나 명령 인자에 붙여 넣지 않습니다. 사용자가 직접 일반 terminal을 열고 플러그인 설치 경로의 launcher를 실행해 숨김 입력합니다. HTTPS를 지원하는 서버를 우선 사용하세요. URL 입력에는 scheme을 생략하고 `192.168.0.172:58821`처럼 host와 port만 입력할 수 있으며, 기본값은 HTTPS입니다.

```sh
python3 -I <plugin-root>/scripts/handrail.py setup
```

LAN의 Vikunja 서버가 HTTP만 제공하면 `--allow-insecure-http`를 추가합니다. 이 경우 scheme 없이 입력한 host는 HTTP로 해석됩니다.

```sh
python3 -I <plugin-root>/scripts/handrail.py setup --allow-insecure-http
```

`<plugin-root>`는 설치된 Handrail 플러그인 폴더의 실제 절대 경로로 바꿉니다. 프로필 이름은 명령을 실행한 현재 디렉터리의 마지막 경로 이름을 기본값으로 사용하며, `--name`으로 바꿀 수 있습니다. launcher는 URL을 입력받고 API token은 terminal echo 없이 읽습니다. 성공하면 연결 프로필과 token을 사용자 전용 설정 경로에 저장합니다. 프로필 목록과 선택 화면은 `이름 (id)` 형식으로 표시합니다.

토큰은 프로젝트 목록·읽기·생성·수정, Kanban view와 bucket 목록·생성·설정, task 읽기·생성·수정·bucket 이동 권한이 필요합니다. 계획카드와 작업카드를 연결하려면 task relation 생성 권한도 필요합니다. Vikunja의 API route 권한과 프로젝트별 사용자 역할을 모두 부여해야 합니다. 초기 `setup`은 읽기만 확인하므로 생성 권한은 사용 시점에 별도로 확인됩니다. 전역 관리자 권한 대신 필요한 프로젝트 범위만 허용하세요.

## Repository binding

연결할 repository를 Codex의 현재 작업 디렉터리로 연 다음 다음을 요청합니다.

```text
이 repository를 Handrail에 연결해줘. 사용 가능한 연결 프로필과 Vikunja 프로젝트를 보여주고,
프로젝트 하나와 그 프로젝트의 manual Kanban view를 고르게 해줘. Todo/Doing/Done은
이름으로 확인하고 Review가 없으면 원격 변경 전에 생성 여부를 물어봐. binding을 저장하기 전에
선택한 프로젝트·view·열 ID를 보여줘.
```

CLI를 직접 호출하려면 플러그인 launcher를 사용합니다.

```sh
python3 -I <plugin-root>/scripts/handrail.py connection list
python3 -I <plugin-root>/scripts/handrail.py project bind --repo /absolute/path/to/git/repository
python3 -I <plugin-root>/scripts/handrail.py status
python3 -I <plugin-root>/scripts/handrail.py doctor
```

Binding은 repository의 `.handrail/project.json`에 remote ID와 상태 mapping만 둡니다. 연결 URL과 token은 repository에 복사하지 않습니다. 각 Git repository는 자신의 부모 프로젝트 하나에 결합됩니다. 다른 repository에 마지막 선택을 자동 적용하지 않습니다.

## Worker CLI와 model

Codex worker는 호스트의 로그인된 Codex CLI를 사용합니다. Cursor worker를 선택할 때는 사용자가 Cursor CLI와 인증을 별도로 준비해야 합니다. 두 worker는 사용자 호스트에 설치된 CLI이며 플러그인 안에 포함되지 않습니다.

```sh
python3 -I <plugin-root>/scripts/handrail.py worker profile set codex-default --provider codex --model <model-id>
python3 -I <plugin-root>/scripts/handrail.py worker profile set cursor-default --provider cursor --model <model-id>
```

run별 `--model` 지정 → repository 기본 worker 설정 → 선택한 provider profile의 model → 해당 CLI 기본값 순으로 결정합니다. Codex의 `--reasoning-effort`는 Codex worker에서만 사용합니다. Cursor의 reasoning 설정은 선택한 Cursor model ID의 일부입니다. 실제로 보고된 모델이 없으면 Handrail은 모델명을 추측하지 않습니다.

Codex가 오케스트레이터이고 Codex/Cursor CLI가 구현 worker입니다. Cursor 오케스트레이터는 현재 후보에서 지원 범위가 아니며, 별도 후속 작업으로 다룹니다.

## 연결 상태 확인

```sh
python3 -I <plugin-root>/scripts/handrail.py connection list
python3 -I <plugin-root>/scripts/handrail.py project status
python3 -I <plugin-root>/scripts/handrail.py doctor
```

setup이 중단되면 `status`와 `connection list`로 저장된 단계만 확인하고 이어서 진행합니다. token 교체에는 `connection rotate <profile-id>`를 사용합니다. 기존 연결 제거는 `connection forget <profile-id>`입니다. 서버에서 발급한 토큰 자체를 폐기하려면 Vikunja에서 별도로 revoke해야 합니다.

v0.2 등 과거 Handrail 로컬 데이터를 옮길 때는 먼저 `migrate preview`로 읽기 전용 계획을 확인하고 선택한 profile/repository에 대해서만 apply합니다. 결과를 검토하고 필요하면 `migrate rollback <migration-id>`를 사용합니다. 원본을 백업 없이 삭제하지 않습니다.
