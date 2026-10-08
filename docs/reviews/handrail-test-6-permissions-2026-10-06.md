# Handrail Herdr 쓰기 권한 문제 분석

`handrail_test_6`에서 드러난 핵심 결함은 **Handrail이 조율자의 실행 경계와 자체 생성 worktree 경로를 연결해 준비·진단하지 못한 것**이다. 제한된 조율자 셸은 프로젝트 밖 worktree를 읽을 수 있었지만 빌드에 필요한 파일을 쓸 수 없었다. 같은 worktree에서 승인된 샌드박스 밖 빌드는 성공했다. 따라서 관측된 오류만으로 Herdr 디렉터리 자체나 OS 소유권이 잘못됐다고 결론 내릴 수 없다.

이 보고서는 Handrail의 설계·구현·스킬 개선을 위한 분석이다. 대상 프로젝트의 복구나 설정 변경을 수행하지 않았다. 분석 기준은 2026년 10월 6일 10:07:18 KST까지의 기록이며, 관련 개선 작업은 [Handrail 백로그](handrail-test-6-backlog-2026-10-06.md)에 정리했다.

## 확인된 사실과 시간 순서

대상은 계획 #23, Frontend #24, Backend #25다. 시간은 모두 2026년 10월 6일 KST다. 원본 UTC 시각·세션 ID·로그 행은 [근거 CSV](handrail-test-6-2026-10-06/evidence.csv)에 있다.

| 시각 | 관측 결과 | 의미 |
| --- | --- | --- |
| 08:51:24 | `.git/index.lock` 생성이 read-only 오류로 실패 | 프로젝트 내부도 Git metadata는 별도 제한 가능 |
| 09:53:46 | Frontend worktree의 npm install 성공 | 일부 명령의 성공만으로 모든 후속 명령의 쓰기를 보장할 수 없음 |
| 09:53:55 | Vite 설정 옆 timestamp 임시 파일 생성에서 `EROFS` | 조율자가 실행한 빌드의 파일 쓰기 차단 |
| 09:54:02 | `--outDir /tmp/...`를 지정해도 같은 실패 | 최종 산출물 경로와 설정 로딩 중간 파일 경로가 다름 |
| 09:55:19 | 설정을 `/tmp`로 복사하자 `ERR_MODULE_NOT_FOUND` | 설정 이동으로 모듈 해석 기준이 바뀜 |
| 09:55:29, 09:55:36 | `--configLoader`가 미지원 옵션으로 두 차례 실패 | 권한 문제와 별개의 도구 사용 오류 |
| 09:56:21 | 직접 Herdr prompt 명령이 `PermissionDenied` | Herdr 제어 동작에서도 별도 접근 실패 발생 |
| 09:59:17 | `herdr pane run ... pwd`도 `PermissionDenied` | 단순 대상 명령도 제어 경로를 통과하지 못함 |
| 09:59:32 | 원래 build 명령을 `require_escalated`로 요청 | 조율자 명령의 실행 경계를 바꾸는 공식 경로 사용 |
| 10:02:11 | Vite 5.4.21, 32 modules, build 10.82초 성공 | 동일 worktree에 필요한 쓰기가 가능한 실행 경로 존재 |
| 10:03:27 | Vikunja `GET /tasks/23` 연결 실패 | 원격 API 접근도 별도 요구 |
| 10:03:44 | escalation 재시도 후 댓글과 review 기록 성공 | 파일 쓰기와 원격 접근을 각각 진단해야 함 |
| 10:04:20 | 통합본 검사에서 `vite: command not found` | 권한과 별개로 통합 checkout 의존성 준비 누락 |
| 10:04:59 | 의존성 설치 후 Frontend Done·verified 기록 | 이번 빌드 차단은 후속 기록에서 해소됨 |

09:53:55의 첫 빌드 차단부터 escalation 요청까지 약 5분 37초, 성공 결과까지 약 8분 16초가 흘렀다. 이는 로그 사건 사이의 경과 시간이며 전부를 제품 장애 시간이나 사용자 승인 대기 시간으로 환산할 수는 없다.

## 실제로 충돌한 경로와 실행 주체

조율자의 작업 디렉터리는 다음과 같았다.

```text
/project_workspace/handrail_poc/handrail_test_6
```

Handrail이 #24를 위해 만든 worktree는 다음 위치다.

```text
/home/dyhwang23/.local/share/handrail/projects/
  be9720f2a8734176a14bd91aecc5b7ea/herdr-worktrees/23/work-24
```

로그의 실효 permission profile은 루트를 read로 두고 프로젝트, `/tmp`, 임시 디렉터리에 write 예외를 부여했다. 프로젝트 `.git`, `.agents`, `.codex`는 별도 read 항목이었다. Handrail의 사용자 데이터 경로는 이 프로젝트 write 범위에 포함되지 않았다(E01).

Vite는 `frontend/vite.config.js`를 읽는 데 그치지 않고 같은 디렉터리에 `vite.config.js.timestamp-*.mjs`를 쓰려 했다. 따라서 산출물만 `/tmp`로 바꿔도 최초 실패 지점은 그대로였다. 이것은 해당 Vite 5.4.21 실행 로그로 확인한 동작이며 다른 버전의 전체 동작에 대한 일반화는 아니다.

| 주체 또는 계층 | 역할 | 이번 사례에서의 의미 |
| --- | --- | --- |
| 조율자 Codex의 shell | 설치, 빌드, Git, Handrail 실행 | 각 명령이 실제 실행된 sandbox 또는 승인 경로가 중요 |
| Handrail 관리 프로세스 | worktree·상태 기록·카드·검증 관리 | 자체 승인 원장으로 부모 shell 권한을 넓힐 수 없음 |
| Herdr 제어 채널 | pane/agent 조회와 입력 전달 | 파일 쓰기와 별개의 제어 자원 접근 필요 |
| Herdr가 실행한 provider worker | 해당 worktree에서 구현 | worker에 적용한 sandbox 설정은 조율자의 정책 변경이 아님 |
| OS 파일 권한과 mount | 각 프로세스의 실제 파일 접근 강제 | EROFS만으로 전역 OS 디렉터리 상태를 단정할 수 없음 |
| Vikunja 연결 | 상태·댓글·관계 API | 파일 권한 또는 worker 모델 통신과 별개 |

OpenAI 공식 문서도 sandbox가 파일·네트워크의 기술적 경계를 정하고 approval policy는 그 경계를 넘는 승인 절차를 정한다고 설명한다. Git·package manager·test runner 같은 자식 명령도 실행 환경의 경계를 적용받는다. [공식 Sandbox 문서](https://learn.chatgpt.com/docs/sandboxing)

## 확정할 수 있는 원인과 남은 불확실성

**높은 확신:** Frontend 빌드 실패는 제한된 조율자 실행 환경에서 외부 worktree의 쓰기가 차단된 사례다. 이를 뒷받침하는 근거는 실효 경로 정책, `EROFS`의 구체적인 대상 파일, 동일 worktree의 escalation build 성공이다. 이 조합은 소스 변경이나 worktree 재생성이 해결의 필수 조건이 아니었음을 보여준다.

**별도 조사 필요:** Herdr prompt/pane 명령의 EPERM에는 실패한 syscall이나 자원이 기록돼 있지 않다. 제어 소켓·IPC 또는 실행 정책 차단 가능성이 있지만 어느 하나를 확정할 수 없다. 이 오류를 Vite 파일 쓰기와 같은 원인으로 묶는 것도 근거가 부족하다. Handrail transport가 실패 계층과 자원 정보를 보존하도록 개선할 필요가 있다.

**명령별 결과의 한계:** 앞선 npm install 성공은 “그 설치 명령이 성공했다”는 증거다. 같은 프로세스 경계에서 모든 명령이 허용됐다는 뜻은 아니다. 저장된 prefix 승인이나 명령 실행 경로 차이가 영향을 줄 수 있으나 해당 install의 호스트 결정 경로를 이번 분석에서 확정하지 않았다. 마찬가지로 build escalation 성공은 영구 writable-root 변경이나 모든 Herdr 제어 권한 해결의 증거가 아니다.

**확인하지 않은 주장:** OS 소유권 오류, Herdr의 전역 read-only 설정, 자동 승인 리뷰의 거부, 사용자가 권한을 의도적으로 취소했다는 주장은 뒷받침할 기록이 없다. 이번 자료만으로 그런 원인을 추가하지 않는다.

## Handrail의 구체적인 부족점

### 실제 Herdr 경로와 기존 preflight 경로가 연결되지 않음

`herdr_workflow.py:_worktree`는 `projects/<workspace-id>/herdr-worktrees/<plan>/work-<task>`를 사용한다. 반면 `cli.py`의 `preflight`는 `runs.root(...)/worktrees`를 host preview에 전달한다. provider와 repo만 받으므로 실제 Herdr plan/task 경로와 제어 채널을 구체화하지 못한다. 일반 Handrail 데이터 루트 안내가 있더라도 어떤 주체가 어느 하위 자원을 필요로 하는지는 충분하지 않다.

기존 preflight는 요구 사항 미리보기이고 호스트 실효 권한을 검증했다고 주장하지 않는다. 따라서 고칠 부분은 기존 기능을 없애거나 “현재 preflight가 권한을 보장한다”고 간주하는 것이 아니라, **Herdr에 맞는 요구 산출과 실제 적용 확인 단계를 연결하는 것**이다. 백로그 001에 해당한다.

### Herdr 시작과 검증에 준비 단계를 강제하지 않음

`start`는 승인 명세와 깨끗한 Git 기준점을 확인하지만 permission adapter와 dependency preparation을 호출하지 않는다. `finish`는 통합 checkout에서 command check를 직접 실행한다. 어느 경계에서 빌드할지와 그곳의 의존성·쓰기 요구를 별도로 준비하는 계약이 없다.

v0.4의 `permissions grant`와 provider 설정 적용 기능이 있다는 사실만으로 Herdr 경로에도 동일하게 적용된다고 기대해서는 안 된다. 현재 구현의 차이를 문서화하고 재사용 가능한 준비 기능을 Herdr lifecycle에 연결해야 한다. 백로그 001, 007에 해당한다.

### 실행 오류에서 제품이 제공하는 판단 정보가 부족함

현재 transport는 Herdr 실패를 문자열로 감싼다. 이 때문에 조율자가 로그만 보고 “파일 쓰기”, “제어 채널 접근”, “지시 전달 불확실”, “도구 옵션 오류”를 다시 해석해야 한다. `doctor`도 API 접근 실패를 binding 실패 항목에 넣을 수 있다.

Handrail은 확정된 계층과 미확정 원인을 함께 반환해야 한다. 예를 들어 파일 경로가 있는 EROFS는 파일 쓰기 실패로, 자원 정보 없는 EPERM은 제어 명령 접근 실패로 표시하고 구체적 원인은 unknown으로 남길 수 있다. 명령 실행 권한이 부족한 경우와 제품 상태가 깨진 경우에 서로 다른 다음 동작을 제공해야 한다. 백로그 002에 해당한다.

### 조율자 스킬이 권한 문제의 대응을 충분히 안내하지 못함

Herdr reference는 host 정책의 한계와 worker delivery 복구를 설명하지만 manager가 설치·build·검증을 하다 host 경계에 막힌 경우의 절차가 구체적이지 않다. 이번 조율자는 `/tmp` 이동과 미지원 옵션을 시도하고 “현재 환경에서 더 진행 불가”로 보고한 뒤, 후속 질문에서야 원래 build를 escalation으로 실행했다.

이는 조율자의 판단·도구 사용 실수도 포함한다. Handrail이 모든 agent 실수를 통제할 수는 없지만, 공식 검사 실행 인터페이스와 구조화된 blocker, 올바른 명령을 제공하면 모델의 추측에 의존하는 부분을 줄일 수 있다. 백로그 002, 005에 해당한다.

## 제품 수정 방향

**단기:** Herdr 전용 요구 경로를 산출하고 스킬의 manager 권한 오류 절차를 보강한다. 권한이 필요한 원래 명령·cwd·대상·이유를 제공하며, 기존 승인 범위와 추가 host 승인을 구분한다. 지원되는 host 승인 절차를 통해 실행하고 실패 원인이 바뀌면 진단도 갱신한다. Handrail 자체가 외부 sandbox를 해제했다고 표현하지 않는다.

**중기:** 승인된 검사·설치 동작을 실행하고 증거를 기록하는 관리 인터페이스를 제공한다. worktree 위치는 등록된 repo와 plan/task에서 해석하고 임의 경로나 셸 문자열 실행으로 확장하지 않는다. 호스트가 실효 정책을 제공하지 못하면 `unverified` 상태를 유지한다. 동일 사용자의 승인을 재사용하되 새 자원·작업 범위는 구별한다.

**저장 위치 설계:** 현재 private data 아래의 worktree를 유지하면서 조율자에게 필요한 하위 경로만 허용하는 방법과, 프로젝트별 별도 작업 루트를 명시적으로 등록하는 방법을 비교할 수 있다. 경로를 프로젝트 안으로 옮기는 것만으로 Git metadata, 제어 채널, API, provider 상태 요구가 모두 해결되지는 않는다. 관리 원장과 credential을 worker가 편집하는 소스 트리와 분리하는 원칙도 유지해야 한다.

## 수정 후 확인할 수용 시나리오

1. 프로젝트만 writable인 조율자에서 Herdr worktree build 요구가 미충족임을 시작 전에 보고한다.
2. 동일 작업 범위의 승인된 실행 경로가 있으면 재사용하고, 적용 불가한 기존 승인과 신규 동의 필요를 구분한다.
3. Vite 설정 임시 파일 EROFS를 파일 쓰기 문제로 분류하며 불필요한 build 옵션 변경을 요구하지 않는다.
4. Herdr EPERM과 Vikunja 연결 거부를 별도 blocker로 표현하고 모르는 세부 원인은 단정하지 않는다.
5. 승인된 실행으로 build가 성공하면 해당 blocker만 해소하고 실제 commit·명령·cwd·결과를 연결한다.
6. worktree 성공 후에도 통합 checkout의 의존성과 기능 acceptance 검증을 별도로 요구한다.

이 시나리오는 Handrail 개선의 완료 기준이다. 실제 실패 프로젝트를 이 분석 세션에서 수정하거나 실행시키는 절차가 아니다.

## 근거 위치

- 주 세션: `01a10e6f-4986-7c83-8bf1-cccea315c958`; E01–E30은 [근거 CSV](handrail-test-6-2026-10-06/evidence.csv) 참조.
- [분석 범위와 설치 revision](handrail-test-6-2026-10-06/manifest.json).
- [Herdr workflow 소스](../../handrail/herdr_workflow.py): `_worktree`, `start`, `recover`, `finish`, `status`.
- [CLI 소스](../../handrail/cli.py): `doctor`, preflight dispatch.
- [권한 adapter 소스](../../handrail/permission_adapters.py): `preflight`, `host_preview`.
- [Herdr transport 소스](../../handrail/herdr_transport.py): `_run`, `agent_start`.
- [기존 권한 검토](../permission-policy-review.md), [v0.4 권한 적용 범위](../permissions-v0.4.md), [Herdr 스킬 reference](../../plugins/handrail/skills/handrail/references/herdr.md).
