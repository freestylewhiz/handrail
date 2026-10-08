# Handrail 설치와 설정

현재 소스 버전은 `1.0.0a6`다. 2026-10-08 이 호스트에 RC02 수정판 `1.0.0-alpha.6+codex.20261008041952`를 재설치했다. 설치 버전과 스킬 경로는 `handrail locate`로 확인한다. Linux, Python 3.9 이상, Git과 사용할 Codex/Cursor CLI 및 기존 Herdr/Vikunja 서비스를 준비한다.

## 권장 시작 방법

설치 후 저장소에서 새 Codex 또는 Cursor 세션을 열고 “Handrail 설정해줘”라고 요청하거나 `handrail init`을 실행한다. 연결이 없을 때만 URL과 토큰을 입력하며 기존 연결이 있으면 부모 보드를 선택한다. ID나 JSON 파일은 준비하지 않는다.

HTTP 서버는 대화형 흐름에서 한 번 허용하거나 `handrail setup --url http://서버주소 --allow-insecure-http`로 저장한다. [간단한 프로젝트 연결](onboarding.md)을 따른다. 스킬 경로는 `handrail locate`로 확인한다.

## 소스 실행과 설치

저장소에서 직접 실행할 수 있다.

```sh
python3 -m handrail --help
python3 -m handrail doctor
```

로컬 패키지 설치는 `bash install.sh`를 사용한다. 기본 설치 위치는 `~/.local/share/handrail/venv`와 `~/.local/bin/handrail`이다. 설치 위치는 `HANDRAIL_VENV`, `HANDRAIL_BIN`으로 지정한다.

## 플러그인 빌드

```sh
python3 scripts/build_plugin.py --output dist/rebuild
```

출력의 `handrail/`은 runtime과 skill을 포함한다. ZIP과 checksum도 생성한다. 이미 존재하는 출력 폴더에는 덮어쓰지 않으므로 새 출력 경로를 사용한다. 로컬 빌드는 게시된 플러그인 릴리스와 별개다.

RC02 수정판부터 빌드는 소스와 번들의 Python 구문 및 이름 지정 내부 import를 정적 분석한다. 모듈은 존재해도 참조 함수가 없으면 빌드를 중단한다. 정적 분석을 기능 테스트나 외부 API 확인으로 표현하지 않는다. 같은 기본 버전의 수정 배포는 단일 `+codex.<시각>` 식별자를 두 manifest와 활성 스킬에 일치시킨다.

플러그인 에이전트는 `handrail locate`의 버전과 활성 스킬을 대조하고 `stable_launcher`를 사용한다. 관리된 재설치는 이 고정 명령을 Codex 캐시 밖의 소유된 release runtime에 연결한다.

```sh
/home/USER/.local/bin/handrail --repo /absolute/repository status
```

## 고급 설정: 연결과 명시적 바인딩

토큰은 사용자 터미널의 숨김 입력으로 저장한다. 채팅, 명령 인자, 저장소 파일에 토큰을 전달하지 않는다.

```sh
handrail setup --name team --url https://vikunja.example.com
```

HTTP 서비스는 다음 명시 옵션이 필요하다. 이는 평문 HTTP 사용에 대한 선택이며 HTTPS 인증서 검사를 비활성화하지 않는다.

```sh
handrail setup --name team --url http://vikunja.internal:3456 --allow-insecure-http
```

일반 사용에서는 `init`이 열을 자동 준비한다. 명시적으로 매핑할 고급 사용자는 기존 보드의 Todo/Doing/Review/Done bucket ID로 `states.json`을 준비할 수 있다.

```json
{"todo": 11, "doing": 12, "review": 13, "done": 14}
```

Herdr endpoint는 실제 관찰한 소켓 절대경로 또는 명시 세션 이름을 사용한다. `default`라는 이름을 추정해서 넣지 않는다.

```sh
handrail --repo /workspace/app bind \
  --connection team --project 18 --view 72 --states-file /path/states.json \
  --socket /home/user/.config/herdr/herdr.sock \
  --worktree-root /workspace/.handrail-worktrees/app
handrail --repo /workspace/app preflight
```

고급 `bind`는 기존 manual Kanban과 mapping을 읽고 단일 보드 방식을 유지한다. `init`은 필요한 Kanban·열을 준비한다. 하위 보드는 `board add/register`로 관리하며 `sync`는 생성하지 않는다. 두 경로 모두 기존 외부 서버를 사용한다.

## 저장과 권한

신규 상태는 `$XDG_DATA_HOME/handrail/v1` 또는 `~/.local/share/handrail/v1`에 저장된다. 기존 v0.5 기록은 자동 변환하지 않는다. `HANDRAIL_HOME`은 별도의 명시 상태 루트를 선택한다.

Worktree 루트를 생략하면 고급 `bind`는 XDG 기반 영속 경로를, 일반 `init`은 checkout 옆 `.handrail-worktrees/<저장소 식별자>`를 사용한다. `bind`의 저장소 내부 예외는 `--allow-inside-repository`로 선택한다. 실행 중인 worktree는 설정 변경으로 이동하지 않는다.

`doctor`와 `preflight`는 읽기만 수행한다. OS 접근 힌트는 outer sandbox 허용을 입증하지 않는다. 조율자는 canonical checkout, Git common directory, private state, worktree, Herdr IPC, Vikunja 네트워크에 대한 실제 권한을 구분한다.

## alpha.6 호스트 교체 설치

관리된 설치는 새 버전으로 빌드한 뒤 `python3 scripts/reinstall_plugin.py --build <새 빌드 디렉터리>`로 교체한다. 이번 수정판의 실제 빌드 경로는 `dist/alpha6-rc02-fix`다. `--dry-run`은 변경 대상을 확인한다. 새 번들과 Codex 캐시의 무결성을 대조한 뒤 공통 런처를 release runtime에 연결하고 `~/.cursor/skills/handrail`을 같은 스킬로 연결한다. 소유하지 않은 기존 Cursor 스킬은 덮어쓰지 않는다. 새 설치 확인 전 이전 release를 보존하고 실패 시 등록·런처·Cursor 연결을 복구한다. 연결 토큰·바인딩·workflow 이력·worktree·외부 서비스 데이터는 기본 보존한다.

`--reset-settings`는 사용자가 자격 증명·바인딩·로컬 이력 삭제를 별도 요청했을 때만 사용한다. 서버의 Summary/Instruction 원본은 유지되지만 로컬 실행 기록이 없어지므로 일반 업데이트에는 사용하지 않는다. 설치 후 새 Codex/Cursor 세션에서 스킬을 다시 읽는다. 새 절차는 [alpha.6 구현 기록](alpha6-implementation.md)을 따른다.

유형 라벨의 조회·생성·부착과 Instruction 카드·댓글 쓰기에 필요한 Vikunja 토큰 범위를 확인한다. API 권한 부족은 호스트 네트워크 승인과 다른 오류다. 필요 없는 권한까지 포괄 허용하지 않는다.

`access plan --provider codex|cursor --group read --group board-sync`는 고정 런처·저장소·동작으로 제한한 규칙을 제시한다. 승인된 범위만 `access apply --approval ...`로 저장하며, `access revoke`는 Handrail이 추가했다고 기록한 규칙만 제거한다. 기존 설정·deny 규칙과 관리자 정책은 유지한다. 실제 새 세션에서 적용됐는지는 별도 관측한다.

## 내부 설치 결함

`INSTALLATION_BROKEN` 또는 이전 버전의 내부 `ImportError`는 호스트 승인으로 해결되는 오류가 아니다. 버전·오류·원래 명령을 보존하고 검증된 수정 번들로 교체한다. 일반 설정 과정에서 release/cache의 Python을 직접 패치하거나 build-info를 고쳐 불일치를 숨기지 않는다. 원본 소스의 수정과 관리된 재설치 후 저장된 설정으로 재개한다. [handrail_rc_02 분석](reviews/handrail-rc-02-2026-10-08.md)을 참고한다.
