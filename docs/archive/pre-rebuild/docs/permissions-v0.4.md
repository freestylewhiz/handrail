# v0.4 권한과 일괄 위임

한 번 동의한 실행 범위에서 여러 계획의 구현·수정·검증을 이어가기 위한 기능이다. **권한 정책 → 계획 묶음 위임 → 개별 실행 기록**으로 연결한다. 기존 사용자 지시가 구체적인 권한과 작업 범위를 이미 승인했다면 그 지시를 기록하고 다시 질문하지 않는다.

## 처음 준비할 때

아래 `handrail`은 설치된 플러그인의 `python3 -I <plugin-root>/scripts/handrail.py`를 줄여 쓴 것이다.

```sh
handrail preflight --provider codex
handrail preflight --provider cursor
handrail permissions template
```

`preflight`는 저장소·Git 공통 디렉터리·Handrail 데이터/worktree·CLI 세션 저장소·Vikunja 주소를 보여준다. 호스트에서 실제 허용된 상태라고 단정하지 않는다. 이 경로의 쓰기, 로컬 테스트/브라우저의 loopback, 필요한 의존성 저장소·캐시를 조율자 세션을 시작할 때 함께 준비한다. Handrail은 부모 Codex/Cursor 프로세스의 샌드박스를 변경하지 않는다.

다음은 정책 파일 예시다. 모델, 추가 경로, 의존성 준비는 프로젝트에 맞게 선택한다.

```json
{
  "schema_version": 1,
  "providers": {
    "codex": {"models": ["gpt-6-luna"], "extra_read_paths": [], "extra_write_paths": [], "network": "disabled"},
    "cursor": {"models": ["*"], "extra_read_paths": [], "extra_write_paths": [], "network": "provider-default"}
  },
  "workflows": ["worker", "verify", "review", "integrate", "kanban", "prepare"],
  "preparation": {"dependency_mode": "copy"}
}
```

```sh
handrail permissions grant --file policy.json --approval '사용자가 실제로 승인한 범위'
handrail permissions delegate --plan 4 --plan 5 --plan 6 --grant GRANT_ID --max-runs 100 --approval '선택된 세 계획을 구현·검증·통합해달라는 실제 지시'
handrail worker profile set codex-luna-high --provider codex --model gpt-6-luna --autonomy workspace-auto
handrail worker profile set cursor-auto --provider cursor --model auto --autonomy workspace-auto
```

부모 계획은 먼저 `plan register`, 명세 승인을 마친 상태여야 한다. 정책은 기본적으로 프로젝트 전용이다. 명시적으로 `--scope global`을 선택해 저장한 정책도 다른 프로젝트의 계획 위임에서 해당 grant를 선택해야 적용된다. 등록되지 않은 저장소·계획에 자동 적용하지 않는다. `--expires-at`은 시간대가 있는 ISO 시각이다.

## 여러 작업을 진행할 때

`work create`/`work link`로 하위 작업을 연결한 뒤, 합의한 부모 범위 안의 상세 명세는 `spec approve ID --file SPEC --checks CHECKS --delegated`로 등록한다. 사용자에게 카드마다 별도로 명세 승인을 받았다고 기록하지 않는다. 명세와 검증 기준을 커밋하고 다음처럼 실행한다.

```sh
handrail run start 7 --provider codex --profile codex-luna-high --reasoning-effort high --instructions '승인한 범위 구현' --preview
handrail run start 7 --provider codex --profile codex-luna-high --reasoning-effort high --instructions '승인한 범위 구현'
```

유효한 위임이 있으면 `authorize ...` 왕복 없이 실행된다. 다음 계획과 새로운 하위 작업도 같은 방식이다. 권한 밖의 실행에는 기존 one-run 미리보기가 남아 있다. 저장소의 동시 쓰기 run은 여전히 하나이며 조율자가 순서대로 실행한다. 조율자 세션이 종료된 뒤 전체 계획을 자동 진행하는 별도 데몬은 제공하지 않는다.

## 검증과 복구

- `run verify`, `run review`, `run integrate`, `run sync`: 위임된 동작 권한을 확인하고 기존 증거 조건을 검사한다.
- `run check RUN --argv-json '["node","tests/regression.cjs"]'`: 추가 회귀 검증의 인자·경로·결과·소스 fingerprint를 기록한다. 승인된 필수 검증을 대신하지 않는다.
- `run revise`: 같은 run의 수정 회차를 진행한다. 이전 `CONTEXT.md`와 제출물을 보관하고 새 패킷을 생성한다.
- `run retry RUN --instructions '남은 문제 수정'`: 정지한 실패 후보를 해시가 있는 Git patch로 보존하고, 새 worktree에 복원·의존성 준비를 완료한 뒤 워커를 시작한다. 새 run도 같은 위임에서 한도를 사용한다. 기준 커밋이 바뀌거나 이전 프로세스가 살아 있으면 중단한다.
- `run inspect`: 프로세스 출력의 활동 시각·양, 준비 로그, 다음 명령을 표시한다. 활동이 있다는 사실은 구현 진척이나 테스트 성공을 뜻하지 않는다.

결과 JSON 템플릿은 `blocked`/`not_run` 예시로 제공하며 성공 결과를 자동 작성하지 않는다. worker가 실제 결과를 제출해야 한다. copy 준비는 동일한 package manifest를 확인해 로컬 `node_modules`를 복사하며, 그 설치가 lockfile과 일치한다고 보장하지 않는다. 설치가 필요하면 정책의 preparation을 `{"dependency_mode":"install","install_argv":["npm","ci","--ignore-scripts"],"execution_boundary":"orchestrator-host"}`처럼 명시한다. 이 값은 조율자 호스트에서의 명령 실행을 별도로 승인하며, worker의 network 설정이 설치 명령을 제한하지 않는다. 설치 hook이 필요한 프로젝트는 그 실행까지 설명하고 승인된 argv를 사용한다.

## 추가 권한·철회

`permissions grant --grant-id ID --file policy.json --approval '새로 승인한 변경분'`은 이력을 보존하며 revision을 올린다. 기존 계획 위임의 새 run은 승인된 최신 권한을 사용한다. 이미 시작한 run에는 확대된 권한을 주입하지 않고 원래 허용 범위로 계속한다. 기존 범위를 더 이상 포함하지 않는 축소·철회는 후속 동작을 막는다. 새 권한이 필요한 실패 run은 보존 후 `run retry`로 이어간다. `permissions revoke ID`와 `permissions revoke-delegation ID`로 이후 사용을 막을 수 있다. 실행 중인 프로세스 중지는 별도 `run cancel`이 필요하다.

Review에서 재개한 계획은 새 회차에 대해 위임한다. 사용자 피드백에 이미 구현 위임이 포함되어 있고 저장된 권한이 충분하면 그 지시를 기록하면 된다. 기존 권한에 대한 질문을 반복하지 않는다. 계획의 최종 Done은 사용자가 결정한다.

## 적용 범위와 한계

| 구분 | v0.4 동작 |
| --- | --- |
| 저장 | 사용자 Handrail data의 `projects/<workspace_id>/permissions.json`, 전역 `permission-grants.json`; private 파일·잠금·원자적 갱신 |
| 계획 식별 | canonical repo/common Git 경로, workspace, Vikunja 부모, 부모 명세/check 해시, reopen 회차 |
| 권한 합성 | 명시적으로 선택한 allow grant의 합집합. 별도 deny 규칙/프로젝트 제한 우선 합성은 아직 없음 |
| Codex worker | workspace-write, workspace-auto의 no-prompt, 추가 writable roots와 네트워크 설정. 추가 read-only roots는 미지원 |
| Cursor worker | sandbox enabled 유지, workspace-auto의 `--force`는 Run Everything 도구 모드. 필요할 때만 새 worktree 설정을 만들고 종료 후 원본 해시 확인 후 정리 |
| Cursor 네트워크 | 사용자/팀 설정과 병합되므로 강제 disabled는 미지원. provider-default 또는 명시적 enabled만 사용 |
| 관리자 명령 | 설치·검증·통합은 조율자 호스트 정책으로 실행. worker sandbox가 보호한다고 표현하지 않음 |
| 호스트 승인 | 기존 Codex/Cursor/조직 권한의 적용을 자동 확인하거나 해제하지 않음. 전역 prefix rule도 생성하지 않음 |

권한 원장과 `HANDRAIL_ROLE=worker`는 애플리케이션 정책이다. 같은 OS 사용자 권한의 악의적인 프로세스로부터 자격증명을 격리하는 기능은 아니다. 목적지별 네트워크 제한, 모든 provider 설정의 실효 권한 열거, 자동 차단 분류와 상주 조율자는 후속 범위다.

근거: [실제 승인 이력 조사](reviews/permission-audit-2026-10-01.md), [초기 검토안](permission-policy-review.md). 검토안에 나온 모든 후보 기능을 v0.4 구현으로 간주하지 않는다.
