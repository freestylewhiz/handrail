# Handrail 운영

아래 순서는 alpha.6 공개 CLI를 설명한다. 명령은 JSON을 출력하며 `--repo`는 하위 명령 앞에 둔다. 에이전트는 `handrail locate`가 반환하는 고정 절대 런처를 사용한다. 식별자는 이전 명령의 결과를 재사용한다. 새 계약·제약은 [구현 기록](alpha6-implementation.md)을 따른다.

## 계획과 승인

최초 연결은 저장소에서 `handrail init`을 실행한다. [설정 흐름](onboarding.md)은 연결 재사용과 부모 보드 준비를 자동 처리한다. 하위 보드 추가와 사용자 요청 카드 강제 전환은 [보드·카드 관리](boards.md)의 독립 기능으로 처리한다. 개발 작업을 아래 과정으로 진행하기 위해 보드를 미리 만들 필요는 없다.

기준 파일은 안정적인 criterion ID와 설명의 JSON 객체다.

```json
{"create": "새 항목을 생성하고 목록에서 확인할 수 있다", "persist": "재시작 뒤에도 항목이 남는다"}
```

```sh
handrail plan create --title '항목 관리' --criteria-file /path/criteria.json --operation-id plan-request-1
handrail plan approve PLAN_ID --approval '사용자가 이 범위의 구현을 요청한 대화 참조'
handrail work create PLAN_ID --title '기능 구현' --criteria-file /path/criteria.json --operation-id work-request-1
```

카드 생성은 로컬 기록을 만든다. Work 생성은 첫 투영 전에 배정 보드 또는 공용 default 작업보드를 준비한다. init/Plan 생성만으로 default를 만들지는 않는다. `sync --topic board`가 원격 카드를 반영하고 worker start는 실행 전에 이를 확인한다. 같은 생성 요청은 같은 operation ID로 재개한다. 승인 문자열은 실제 사용자 지시의 기록이다.

Plan/Work에는 `--presentation-file`로 영어 블록과 사용자 언어 블록을 분리한 개요·상세·2열 기준표를 전달한다. 조율자가 파일을 작성한다. [카드 작성 스킬](../plugins/handrail/skills/handrail/references/cards-and-instructions.md)의 스키마를 사용한다. 새 카드의 유형 라벨은 plan/task다.

새 기획 응답의 `related_summaries`를 확인하고 `summary read`로 필요한 영역을 읽는다. 적용할 이력은 `summary use`로 기록하면 작업자 시작 시 전달된다.

## 실행 범위 재사용

`preflight`로 실제 경로를 확인하고 `config`의 값을 사용해 scope 파일을 만든다.

```json
{
  "actions": ["room.create", "worker.start", "worker.prompt", "worker.recover", "work.integrate", "room.close"],
  "endpoint": {"socket": "/home/user/.config/herdr/herdr.sock"},
  "repo": "/workspace/app",
  "worktree_root": "/workspace/.handrail-worktrees/app",
  "provider": "codex",
  "model": "USER_SELECTED_MODEL"
}
```

범위에 포함할 동작은 사용자의 기존 지시와 일치해야 한다. `keys`, worktree 삭제, 임의 명령은 별도 동작이다. `--approval`에는 이미 받은 지시를 기록하므로 같은 범위에 다시 확인을 요구하지 않는다.

```sh
handrail permissions grant PLAN_ID --scope-file /path/scope.json --approval '사용자의 실행 및 정리 지시 참조'
handrail permissions list
handrail permissions preview PLAN_ID --action worker.start --resources-file /path/request-resources.json
```

preview의 `missing`만 새로운 범위다. 앱 grant는 host sandbox 설정을 바꾸지 않는다. 새 plan cycle에는 그 회차의 승인과 grant가 필요하다.

## 작업자 실행과 소통

지시 파일에는 목표, 수정 범위, 기준, 제약과 결과 보고 형식을 포함한다. 사용자 명시 모델→저장된 선택→관측한 조율자 모델 순서로 사용한다. `coordinator register --provider ... --model ... --evidence ...`로 실제 세션 정보를 남기면 worker start의 모델 인자를 생략할 수 있다. Cursor는 정확한 모델 식별자에 추론 변형을 포함하며 별도 effort를 받지 않는다.

```sh
handrail worker start WORK_ID --provider codex --model USER_SELECTED_MODEL \
  --effort high --instructions-file /path/task.txt --operation-id attempt-request-1
handrail worker observe ATTEMPT_ID
handrail worker collect ATTEMPT_ID --recent
handrail worker prompt ATTEMPT_ID --instructions-file /path/followup.txt --message-id followup-1
```

start는 readiness만 전달한다. 작업자가 자기 sandbox에서 `worker probe --contract FILE`을 실행한 후 `worker continue ATTEMPT`가 준비 결과를 확인해 구현을 지시한다. `observe`는 라이브 조회와 증명된 신원 보강, `collect`는 관찰·구조화 제출 수신과 보드 반영이다. 상태 조회만으로 Done이 되지는 않는다.

활성 대화에서 `coordinator tick PLAN --owner SESSION`을 반환된 주기로 실행한다. tick은 지속 데몬을 만들지 않으며 마지막/다음 확인과 backoff를 기록한다. 작업자는 commit 후 별도 채널에 JSON 보고를 쓰고 `worker submit --contract FILE --report-file FILE`로 제출한다. 수신 후 Work는 조율자 Review로 이동한다. 재접속 시 tick과 `coordinator inbox`로 미처리 인계를 찾는다.

Plan Review의 내부 상태·보드 전송·사용자 보고는 `coordinator report PLAN`으로 확인한다. 사용자에게 실제 결과·미검증·Review 링크를 전달한 뒤 `--message 실제보고`로 남긴다. 시작 보고만 하고 조율을 끝내지 않는다.

통신이 불명확하면 operation을 확인하고 기록된 근거로 재조정한다. 전달됐을 가능성이 남아 있는 지시를 새 ID로 무조건 반복하지 않는다.

```sh
handrail status PLAN_ID
handrail history WORK_ID
handrail worker resolve-message MESSAGE_OPERATION_ID --outcome delivered --evidence '응답에서 해당 지시 처리 확인'
```

보드 쓰기가 불명확한 채 남으면 먼저 실제 카드와 댓글을 확인한다. 기존 요청이 적용되지 않았다는 근거가 있으면 `sync --resolve EVENT_KEY --evidence ...`로 로컬 의도를 재조정한 뒤 동기화한다. 이 재조정 명령 자체는 외부 쓰기를 수행하지 않는다.

작업자가 소실되거나 교체되면 동일 room과 worktree의 대상을 명시적으로 확인한 뒤 `worker recover ATTEMPT_ID --target LIVE_PANE_OR_NAME --evidence ...`를 사용한다. 새 attempt가 이전 attempt를 대체하고, 이전 이력은 보존된다.

시작 응답 유실로 생긴 room은 `room adopt PLAN_ID WORKSPACE_ID --origin-operation ROOM_CREATE_OPERATION --owned-pane PANE_ID --evidence ...`로 연결한다. 생성 의도와 label을 대조하고, 실제 소유를 확인한 pane만 선택한다. 해당 `worker.recover` scope에는 `workspace_id`, `origin_operation_id`, `owned_panes`도 포함한다. 발견한 모든 pane을 자동으로 소유 처리하지 않는다.

`worker keys`에는 저장된 observation, 화면 hash와 키 목록을 포함한 grant, 실제 행동 이유가 필요하다. Enter가 대화를 전송하는지 새로운 권한을 승인하는지 먼저 판단한다.

## 준비 명령과 검증

의존성 준비는 작업자 worktree와 통합 checkout에 각각 필요할 수 있다. `command`는 shell 문자열 대신 JSON argv를 받는다. scope에는 공통 자원 외에 `argv`, `cwd`, `purpose`와 `command.run`을 정확히 포함한다.

```json
["npm", "ci"]
```

```sh
handrail command PLAN_ID --argv-file /path/argv.json --cwd /absolute/checkout --purpose prepare
```

검증 명령은 사용자가 요청한 검증 범위 안에서 `--purpose verify`로 실행한다. 출력은 비공개 로그에 저장되고 실행 ID, 종료 코드, 전후 revision이 반환된다. 재실행은 별도 의도이므로 새 operation ID로 구분한다.

중단된 명령은 실제 프로세스와 부수효과를 확인하고 `resolve-command OPERATION_ID --evidence ...`로 기록한 후 재실행한다. 이 기록은 검증 성공으로 취급되지 않는다.

## 검수와 통합

작업자는 수정 내용을 작업 branch에 커밋하고 결과·남은 문제를 보고한다. 조율자는 실제 diff를 검수한다. `work review`는 그때의 worker commit을 고정한다.

```sh
handrail work review WORK_ID --verdict accept --notes '검수한 변경과 판단 근거'
handrail worker integrate ATTEMPT_ID
handrail evidence WORK_ID --criterion create --text '직접 확인한 구체적 결과'
handrail evidence WORK_ID --criterion persist --text '재시작 후 확인한 결과'
handrail work complete WORK_ID
```

통합은 깨끗한 canonical checkout에서 검수한 커밋을 merge한다. 충돌 시 자동 reset하지 않는다. 통합 revision의 기준마다 증거가 필요하다. 실행 로그를 연결하려면 `evidence ... --command-id COMMAND_ID --text ...`를 사용한다. 실패/차단/미실행 증거는 `--file`의 `{ "status": "failed", "text": "관찰 내용" }`처럼 기록한다.

## 사용자 검토와 수락

모든 작업을 마친 뒤 현재 canonical revision에서 계획 기준을 검증한다. 서로 다른 작업의 완료 커밋은 최종 revision에 포함되어 있어야 한다.

```sh
handrail evidence PLAN_ID --criterion create --text '통합된 결과의 확인 근거'
handrail evidence PLAN_ID --criterion persist --text '통합된 결과의 재시작 확인 근거'
handrail plan verify PLAN_ID
handrail plan submit-review PLAN_ID
handrail sync --topic board
```

사용자에게 변경 내용, 검증 결과, 미확인 항목, 접근 가능한 실행 URL과 보존 중인 자원을 보고한다. 사용자가 수락하면 다음을 수행한다.

```sh
handrail summary prepare PLAN_ID --language ko
# 조율자가 반환된 템플릿을 근거로 작성한 뒤 실행
handrail plan complete PLAN_ID --approval '이번 제출 결과에 대한 사용자의 수락 참조' --summary-file /path/summary.json
```

조율자는 Review 중 Summary 초안을 준비하고, 사용자 최종 승인에 `plan complete`를 사용한다. 현재 초안이 이미 있으면 `--summary-file`을 생략한다. 완료 명령은 내부 수락, 보드 동기화와 Summary 확정을 진행한 뒤 room 정리 범위를 반환한다. close/keep 선택을 받아 `plan cleanup`으로 기록하며, 미응답·보존은 완료를 막지 않는다. Worktree 삭제는 별도 범위다. 상세 명령·필드·재시도는 [Summary와 기획 완료](summaries.md)를 따른다.

보완 요청은 `plan reopen PLAN_ID --reason ...` 후 새 작업으로 기록한다. 이전 회차의 완료와 증거를 수정하지 않는다.
