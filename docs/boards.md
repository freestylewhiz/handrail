# 보드 구성과 카드 관리 — alpha.6

Vikunja의 project는 사용자에게 **보드(board)**라고 부른다. 부모 보드·하위 보드는 계층, 칸반 뷰는 표시 방식, 열은 상태 구성이다. API 경로와 기존 저장 필드인 `project_id`는 호환성을 위해 유지한다.

## 하위 보드 추가

저장소를 연결한 뒤 “하위 보드로 frontend와 backend를 추가해줘”라고 요청한다. 에이전트는 다음 명령 하나로 처리한다.

```sh
handrail board add frontend backend
handrail board list
```

연결된 부모 보드 아래에 요청한 이름 그대로 추가하고 칸반 뷰와 Todo/Doing/Done 열을 준비한다. 결과는 이름·부모 관계·링크를 포함한다. Plan·Work·작업자·worktree를 만들지 않으며, Herdr 가용성이나 Git 미커밋 변경을 검사하지 않는다. 저장소 바인딩을 읽기 위한 Git 식별 조회만 필요하다.

같은 관리 요청은 기존 보드를 재사용한다. 별도로 만들어진 동명 보드가 있으면 재사용 여부를 질문하고, 사용자가 선택한 경우 `--reuse-existing`을 사용한다. 여러 동명 보드 중 하나를 지정하거나 기존 하위 보드를 등록할 때는 `board register 보드링크`를 사용한다. 이 명령은 필요하면 칸반 뷰·열도 준비한다. 모호한 뷰·열은 `--view`, `--state todo=열이름`으로 선택한다. 완료된 매핑은 고정한다.

일괄 처리 중 하나가 실패하면 이전 성공 결과와 아직 처리하지 않은 이름을 반환한다. 동일 요청으로 재개하며, 응답이 유실된 쓰기는 실제 상태를 먼저 조회한다. 불명확한 생성은 기존 `setup-resolve` 절차를 따른다. 성공한 보드를 롤백 삭제하지 않는다.

## 사용자 요청에 따른 카드 강제 전환

“이 카드를 Done으로 바꿔줘”라는 사용자 지시를 다음과 같이 처리한다.

```sh
handrail card list --board frontend
handrail card move CARD --state done --force --reason '사용자가 이 카드를 Done으로 변경하도록 요청함'
```

`CARD`는 링크·ID·정확한 제목 또는 Handrail의 Plan/Work ID다. 동명이면 `--board` 또는 링크로 구분한다. 연결된 부모 보드와 그 하위 범위의 활성 보드만 대상으로 한다. 상태는 todo/doing/review/done 중 해당 보드에 실제 매핑된 열이어야 한다. 매핑되지 않은 기존 열에서 지원 상태로 이동하는 것도 가능하다.

사용자의 명시적 요청을 사유로 기록하므로 별도의 두 번째 확인 질문은 필요 없다. `--force`와 사유는 조율자가 요청을 기록하는 수단이며 사용자 인증이나 호스트 권한을 대신하지 않는다. 조율자 판단만으로 개발 완료 관문을 우회하기 위해 사용해서는 안 된다.

강제 전환은 변경 전후 상태, 요청, 시간, operation ID와 실제 조회 결과를 이력에 남긴다. 카드가 Done이 되어도 개발 작업의 검증·통합·수락 기록은 새로 만들지 않는다. `status`는 개발 상태와 `card.state`를 각각 표시한다. 실행 중인 작업자는 계속 실행되며 자원 정리도 발생하지 않는다.

해당 카드에는 자동 **상태** 동기화 보류를 설정한다. 이후 개발 진행 이벤트나 이전에 대기 중이던 이벤트가 사용자 지정 상태를 덮어쓰지 않는다. 개발 이력 댓글은 계속 투영될 수 있다.

## 재개와 복구

강제 전환이 불명확하면 같은 operation ID와 요청으로 조회·재조정한다. 목표 상태가 확인되면 중복 쓰기 없이 완료 기록을 마친다. 목표 상태가 보이지 않는다는 사실만으로 재전송하지 않는다. 실제 미적용을 확인한 뒤 다음을 사용한다.

```sh
handrail card resolve OPERATION_ID --evidence '이전 요청이 적용되지 않았음을 확인한 근거'
```

`resolve`는 외부 쓰기를 하지 않는다. 다른 사용자가 카드를 다른 상태로 이동했다면 최초 상태와의 충돌을 보존하므로 기존 요청을 무조건 다시 적용하지 않는다. 해당 요청을 취소하고 재선택하려면 `card resume`을 사용한다.

사용자가 자동 동기화 재개를 요청하면:

```sh
handrail card resume CARD --reason '사용자가 자동 상태 동기화 재개를 요청함'
handrail sync --topic board
```

이전 대기 이벤트의 상태 변경을 억제하고 최신 개발 상태를 새 이벤트로 큐에 넣는다. 개발 작업과 연결되지 않은 외부 카드는 자동 동기화할 상태가 없으므로 보류 기록만 해제한다. 불명확한 이동은 먼저 재조정해야 한다.

## 보드와 개발 작업의 연결

```sh
handrail board assign PLAN_ID --board frontend
handrail board assign WORK_ID --board backend
handrail board history
```

Plan 지정은 처음 동기화할 Work의 기본 보드를 정한다. Work 지정이 우선하며 기존 카드 위치는 유지한다. 승인된 Work 준비에 배정이 없으면 서버·부모 보드별 공용 default를 재사용하거나 생성한다. 별도 사용자가 만든 동명 보드는 `board default BOARD --reason USER_SELECTION`으로 선택한다. init·기획 작성·승인 전 Work 초안은 기본 보드를 만들지 않는다. `board prepare-work WORK`로 준비를 재개하며 sync는 보드를 생성하지 않는다.

## 구현 경계

| 구성 | 책임 |
| --- | --- |
| `board/catalog.py` | 연결 범위·보드·카드·기존 매핑 조회 |
| `board/provisioning.py` | 외부 생성 의도·칸반 준비·생성 복구 |
| `board/service.py` | 하위 보드 추가·등록·작업 배치·관리 이력 |
| `board/cards.py` | 사용자 지정 카드 상태·동기화 보류·재개·복구 |
| `interfaces/vikunja/` | 외부 보드·뷰·열·카드 API |
| `hooks/routing.py`, `hooks/board.py` | 지정된 보드로 카드 투영, 사용자 상태 보류 존중 |

외부 쓰기와 로컬 상태 변경은 기존 비공개 저장 경로를 사용한다. 필요한 호스트 승인은 구체적인 보드·카드 명령 범위로 요청한다. 여러 보드 추가는 한 명령으로 묶는다. 기존 토큰·HTTP 허용 선택을 재사용하며 권한 설정을 자동으로 확대하지 않는다.

alpha.6 소스와 번들을 준비하고 후속 요청에 따라 호스트 재설치를 완료했다. 실제 서버 변경·기능 테스트는 수행하지 않았으며 기존 설정과 이력을 보존했다. [현재 상태](status.md)를 따른다.

## 기획 완료와 Summary

리뷰 후 최종 승인 요청은 `plan complete`로 처리한다. `card move --force`는 사용자가 카드 표시 상태만 변경하려는 경우다. Summary는 부모 보드에 `[Summary]` 카드로 게시되고 Agent Context의 `type: summary`로 식별한다. Work로 배정하지 않는다. 초안·이전 cycle은 Review, 수락 요약은 Done을 사용한다. [완료와 Summary 운영](summaries.md)을 참고한다.
