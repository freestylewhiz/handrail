# Summary와 기획 완료 — alpha.6

## 사용자 사용법

리뷰를 마친 사용자는 **“기획카드 #31의 구현 결과를 리뷰했고 최종 승인합니다. 기획을 완료 처리해줘.”**라고 지시한다. 조율자는 원래 승인을 재사용하여 Summary를 준비하고 `plan complete`로 내부 기획을 수락한다. 보드의 표시 상태만 바꾸라는 명시적 요청은 `card move --force`로 구분한다.

완료 명령은 보드 동기화, Summary 확정 결과와 AgentRoom 정리 선택지를 반환한다. 조율자는 관련 room·작업자·터미널 범위를 보여주고 종료 또는 보존을 묻는다. 보존이나 답변 대기는 기획 완료를 취소하지 않는다. 실행 중이거나 다른 작업이 섞인 room은 종료하지 않고 이유를 보고한다. worktree와 파일 삭제는 별도다.

## 저장과 형식

기획별 Summary 카드 하나를 부모 보드에 유지한다. 내부 Work 수·수용 기준에는 포함하지 않는다. `[Summary]` 제목·구조화 정보와 함께 `summary` 라벨을 적용한다. 서버 자체의 카드 유형을 변경하지 않는다. 초안·오래된 요약은 Review, 수락 요약은 Done이다. 준비 근거에는 구조화 완료 제출과 참조한 Instruction 버전도 포함한다.

1. **English**: 프로젝트 결과(목적·결과·결정·규칙·회피 사항·고려 사항·검증 한계)와 Handrail 수행 이슈를 별도 영역으로 기록.
2. **사용자 언어**: 예를 들어 `한국어` 영역에 같은 내용의 전체 번역. 문장마다 두 언어를 교차하지 않는다. 영어 사용자에게는 이 영역을 중복 생성하지 않는다.
3. **Agent Context**: 버전, 기획·작업·소스 링크, cycle, 기준 커밋, 완료 근거와 영역 디렉터리를 기록. schema 2는 `knowledge.project_results`와 `knowledge.handrail_issues`를 분리한다.

본문과 이전 버전은 Vikunja 카드와 댓글에만 유지한다. 로컬 `summary_card`는 카드 ID·버전·해시·상태, `summary_reference`는 참조 ID·버전·항목·이유, 전송 의도는 요청 해시와 처리 상태를 보관한다. 조율자가 작성한 임시 JSON은 전송용 버퍼이며 별도 원본으로 관리하지 않는다.

## 조율자 작성 절차

```sh
handrail sync --topic board
handrail summary prepare PLAN --language ko
```

prepare는 기준별 evidence, 이전 cycle, 작업 리뷰, 최신 수집된 작업자 보고, 링크와 템플릿을 반환한다. 조율자 모델이 근거를 읽고 두 언어를 작성한다. CLI 자체가 모델 API를 호출하거나 의미를 추측하여 번역하지 않는다. 사용자가 작성 파일이나 기술적인 옵션을 준비할 필요는 없다.

출력의 `source_fingerprint`, `expected_hash`를 보존하고 `content`를 채워 임시 JSON 파일에 저장한다. 새 템플릿은 `content.schema_version=2`다. `content.sections.en`과 `content.sections.ko`는 각각 프로젝트 결과의 `intent`, `outcome`, `decisions`, `rules`, `avoid`, `considerations`, `verification`과 별도 영역 `handrail_issues`의 여덟 문자열을 요구한다. `content.agent_context`에는 기존 `scope`, `decisions`, `rules`, `avoid`, `considerations`, `verification`과 구조화된 `handrail_issues`를 작성한다. CLI가 표시할 때 두 영역을 분리한다. 근거를 찾지 못하면 그 사실을 명시하고, 작업자의 선택 이유를 추측하지 않는다. 영어·한국어 외의 언어는 `language_name`, 여덟 필드의 번역된 `headings`, 프로젝트 영역 제목인 `project_headings[언어]`를 함께 제공한다.

## Handrail 개선에 사용할 수행 이슈

구현 프로젝트의 API 결함·설계 결정은 프로젝트 결과에 속한다. 권한·신원·조율·완료 인계·복구처럼 Handrail을 사용해 작업하는 과정의 관측은 수행 이슈에 속한다. 발견한 사람이 작업자라는 이유로 앱 결함을 수행 이슈로 옮기지 않는다.

`content.agent_context.handrail_issues`는 `assessment`와 `items`를 가진다. `assessment`는 `not_reviewed`(미검토), `none_observed`(검토 범위에서 관측 없음), `observed`(관측 있음)이며 마지막 경우만 항목 목록을 가진다. 항목에는 `id`, `stage`, `expected`, `observed`, `impact`, `recovery`, `status`, `attribution`, `evidence`가 필요하다. 영어 기술 키·값을 사용하고 동일 ID로 번역 본문과 연결한다.

- `status`: `open`, `recovered`, `resolved`, `unknown`. 작업을 재개한 우회·복구는 `recovered`이며 제품 결함 수정 완료와 다르다.
- `attribution`: `handrail`, `provider`, `host`, `coordination`, `unknown`. 작성자의 근거 있는 판단이며 미확인 원인은 `unknown`으로 둔다. 가설은 선택 필드 `hypothesis`로 분리할 수 있다.
- `evidence`: 하나 이상의 operation/event/세션 메시지/검사 근거 참조. 예: `operation:ID`, `event:ID`. 환경·버전 등 필요한 맥락은 항목의 선택 필드로 보충한다. 비밀값·nonce·전체 로그를 복사하지 않는다.

prepare는 관련된 로컬 오류·복구 사건의 **참조**를 `execution_evidence`로 최대 50개씩 반환한다. 이는 일부 후보이며 완전한 감시나 자동 원인 판정이 아니다. 조율자는 필요한 이력·세션 근거를 읽어 두 언어와 Agent Context를 작성한다. 후보가 없다고 문제가 없었다고 선언하지 않는다. 수행 이슈는 프로젝트 검증 fingerprint나 수락을 대신하지 않으며, Plan Done이 이슈를 자동 해결 처리하지 않는다.

원본은 동일 Summary 카드에 남긴다. 이후 개발 책임자가 조회해 Handrail 개선 후보의 채택·축소·제외를 판단한다. 기록만으로 개발 카드·권한·Instruction을 만들지 않는다. 연결된 부모 보드 안에서 조회하며 별도 수집 서버·전역 backlog·저장소 간 자동 수집기는 추가하지 않는다.

## 게시와 수락

```sh
handrail summary publish PLAN --file /path/summary.json --reason '현재 Review의 근거를 요약'
handrail plan complete PLAN --approval '사용자의 실제 최종 승인 내용'
```

Review 중 초안을 생성하는 것이 권장 절차다. 완료 시까지 초안이 없으면 조율자가 자동으로 prepare와 작성을 수행한 후 아래처럼 한 번에 게시·수락한다. 이미 받은 사용자 승인을 다시 요청하지 않는다.

```sh
handrail plan complete PLAN --approval '사용자의 실제 최종 승인 내용' --summary-file /path/summary.json
```

`plan accept`는 같은 기능이다. PLAN 자리에는 로컬 기획 ID 또는 연결된 기획카드 ID를 사용할 수 있다. CLI에 직접 호출하고 현재 요약을 제공하지 않으면 `SUMMARY_CONTENT_REQUIRED`가 다음 행동을 알려주며, 빈 요약을 생성하거나 수락 근거를 위조하지 않는다. 자동 작성은 조율자의 스킬 절차와 CLI를 결합한 동작이다.

수락 후 조율자는 영어·사용자 언어·Agent Context의 현재 상태 서술이 맞는지 확인한다. CLI의 accepted 갱신은 자유 서술의 “수락 대기”까지 고치는 기능이 아니다. 필요하면 같은 카드에 본문을 갱신하고 기존 승인과 이력을 유지한다. 이를 위해 사용자에게 다시 수락을 요청하지 않는다.

이미 강제 Done으로 이동한 카드는 자동 동기화 보류를 유지할 수 있다. 정식 수락과 그 보류는 별도이며, 조율자는 보드 상태를 함께 확인한다. 보류된 상태가 Done과 다르면 사용자 의도에 맞는 상태 변경 또는 명시적 동기화 재개를 처리한다.

## 정리 선택

```sh
handrail plan cleanup PLAN
handrail plan cleanup PLAN --choice keep --scope-token RETURNED_TOKEN --approval '사용자가 보존 선택'
handrail plan cleanup PLAN --choice close --scope-token RETURNED_TOKEN --approval '사용자가 제시된 room 종료 선택'
```

토큰은 제시된 room 집합·endpoint·소유 pane과 선택을 연결한다. 새로운 room이나 pane이 생기면 다시 범위를 보여준다. close는 수락된 현재 Summary를 확인하고 기존 종료 grant를 재사용한다. 누락된 종료 grant만 실제 사용자 선택에서 기록한다. 기존 회차의 room도 조회하며, 최종 기획 수락 후 남은 과거 회차의 room을 닫을 수 있다. 과거 회차 worktree 삭제 권한으로 확대하지 않는다.

정리가 실패하면 `plan cleanup PLAN --inspect`로 현재 신원과 관측 토큰을 확인하고, 근거가 있는 경우 `--reconcile TOKEN --evidence TEXT`를 사용한 뒤 `--resume`한다. 정상적인 지연 세션 ID 보강은 기존 close 선택을 재사용한다. 실제 교체·공유·활동 중 자원은 차단하며 Done·Summary·worktree는 보존한다. 직접 Herdr 종료를 표준 우회 절차로 안내하지 않는다.

## 다음 작업에서 참조

```sh
handrail summary list --query employees
handrail summary read CARD
handrail summary read CARD --language en --section rules --section verification
handrail summary read CARD --language ko --section decisions
handrail summary use PLAN_OR_WORK CARD --section rules --section verification --reason '직원 저장 기능 확장에 적용'
handrail summary list --issues --query permission --include-stale
handrail summary read CARD --section handrail_issues
handrail summary read CARD --section project_results
handrail summary read CARD --language ko --section handrail_issues
```

기본 read는 Agent Context만 반환한다. `--section handrail_issues` 또는 `project_results`는 출처 메타데이터와 해당 구조화 영역만 반환한다. API 응답 전체는 도구 프로세스에서 처리하고 선택된 영역만 모델에 전달한다. 네트워크 응답 바이트 감소를 보장하는 기능은 아니다. 기본 키워드 검색은 제목·프로젝트 scope, `--issues` 검색은 제목·관측된 수행 이슈에 적용되며 의미 검색은 아니다. 목록에 `issue_assessment`·`issue_count`를 표시한다. 기본은 accepted만 조회하고 `--include-stale`을 명시하면 draft/stale도 포함한다.

새 기획 생성 결과에는 관련 Summary 후보가 포함된다. 조율자가 관련성을 판단해 `summary use`로 카드·버전·해시를 기록하면 `worker start`가 선택한 영어 항목과 출처를 작업 지시에 추가한다. 참조 내용이 변경되었거나 이전 cycle의 기록이 되면 작업자 시작 전에 재확인을 요구한다. 번역 비교 외에는 양쪽 언어를 반복해서 읽지 않는다.

기본 worker 참조 항목은 프로젝트 결과의 결정·규칙·검증 등이며 수행 이슈를 자동 주입하지 않는다. 수행 이슈가 이번 작업에 실제로 관련되면 조율자가 명시적으로 필요한 부분만 참조한다. 어떤 선택 조회도 승인이나 영구 정책이 되지 않는다.

## 변경과 복구

- `plan reopen`은 이전 요약을 stale로 표시한다. 이전 결정은 지우지 않고 새 cycle의 요약에 대체 관계와 변경 이유를 남긴다.
- 갱신 전에 기존 본문을 같은 카드 댓글에 보관한다. 작성 시점의 expected hash와 현재 본문이 다르면 재조회·조정을 요구한다.
- 생성·본문 갱신·이력 댓글·열 이동·원본 링크 각각의 전송 의도를 기록한다. 응답 유실을 미적용으로 단정하지 않는다.
- `summary resolve OPERATION_ID --evidence OBSERVATION`은 외부 결과를 읽고 로컬 의도를 조정한다. 다음 publish 또는 `sync --topic summary`에서 후속 동작을 진행한다.
- 서버의 원자적 조건부 갱신을 사용하는 구현은 아니므로, 마지막 조회와 PATCH 사이 외부 편집 경합은 남는다. 이전 본문은 댓글로 보존한다.
- 수락 이후 보드·요약·정리 실패는 완료 상태와 별도로 보이며 `status`의 pending 결과와 `sync --topic board|summary|room.cleanup`으로 재개한다.

기존 수동 테스트 카드 #35·#36은 당시 형식의 비교 자료다. 새 CLI의 식별 마커·스키마로 자동 이관하거나 덮어쓰지 않는다.

schema 1 카드는 읽기·prepare·수락 lifecycle에서 기존 형식을 유지한다. 조율자가 기존 카드를 명시적으로 갱신할 때만 schema 2로 설정하고 두 영역을 작성·대조한다. 이전 카드의 수행 이슈 기록 부재는 `not_reviewed`로 조회하며 “문제 없음”으로 바꾸지 않는다. schema 2 카드의 모든 읽기 주체에는 schema 2를 지원하는 런타임이 필요하다. 이번 소스 구현은 설치된 구버전 런타임이나 live 카드의 자동 갱신을 뜻하지 않는다.
