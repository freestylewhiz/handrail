# alpha.6 구현 기록과 사용 계약

기준: `1.0.0a6` / 플러그인 `1.0.0-alpha.6`. 2026-10-08 활성 체크리스트 DEV-01~10을 대상으로 소스·스킬·문서를 변경하고 후속 요청에 따라 호스트 재설치를 완료했다. 실행 테스트와 실제 네 조합의 승인 횟수 측정은 미실행이다. 따라서 아래의 소스·설치 반영과 체크리스트 수용 확인을 구분한다.

**체크리스트 종료:** 2026-10-08 사용자 요청으로 DEV-01~10과 모든 기존 체크 항목을 닫았다. 아래의 미실행·미확인은 실제 확인 근거의 한계이며 열린 작업 상태를 뜻하지 않는다.

**후속 수정:** 같은 날 `handrail_rc_02`에서 발견한 setup 함수 누락을 복구하고 `1.0.0-alpha.6+codex.20261008041952`를 호스트에 설치했다. 이름 지정 내부 import 정적 분석(60개 모듈), 설치 파일 76개 무결성, Codex 활성 상태와 Cursor 연결을 확인했다. 아래 최초 alpha.6 빌드 기록은 당시 근거로 보존한다. 최신 원인·조치·설치 근거는 [RC02 분석 보고서](reviews/handrail-rc-02-2026-10-08.md)를 따른다.

## 개발 단위별 반영

| 항목 | 구현 위치 | 달라진 동작 | 추가 비용·확인 필요 |
| --- | --- | --- | --- |
| DEV-01 | `setup/access.py`, `agentroom/providers.py`, `handoff.py`, `process.py` | 의도/호스트 정책/요청 설정/관측 결과, 제출/수신/처리 상태 분리 | 명시 관측만 집계; 실제 클릭 수를 추정하지 않음 |
| DEV-02 | `setup/access.py`, `installation.py`, 재설치 스크립트, 공통 스킬 | 고정 절대 런처, Codex 접두어·Cursor 인수 규칙, Cursor 스킬 연결 | CLI 적용 대상. IDE·관리 정책 및 실제 반복 승인 감소는 미확인 |
| DEV-03 | `agentroom/providers.py`, `service.py` | 명시 선택→저장 선택→관측 조율자 모델, 실행 전 모델/옵션 점검 | 모델 목록 조회 비용; 모르는 모델을 추정하지 않음 |
| DEV-04 | `worker_io.py`, `handoff.py`, Herdr 어댑터 | worktree/gitdir/commondir/보고 경로 전달, 작업자 쓰기 진단 뒤 구현 | 시작 진단 추가. 디렉터리 쓰기 성공은 훅·서명 포함 커밋 성공 보장이 아님 |
| DEV-05 | `board/service.py`, `hooks/routing.py` | 공용 default 준비·첫 투영 전 배정·Review 열, 원래 카드 위치 유지 | 보드 준비 실패 시 실행 준비가 대기함; 같은 호스트에서 잠금·등록 공유 |
| DEV-06 | `agentroom/handoff.py`, `application.py`, `workflow/reporting.py` | 구조화 보고, 지속 확인, Work Review, 검토 처리, 검증 후 Plan Review 및 사용자 보고 추적 | 한 번의 tick은 한 번의 확인. 대화 종료 뒤 자동 깨우기는 구성하지 않음 |
| DEV-07 | `agentroom/process.py`, `cleanup.py`, `shared/results.py` | 지연 신원 보강, Done 전용 inspect/reconcile/resume, 정리 실패 종료 코드 | Linux 프로세스 관측 불가 시 확인 불가로 차단. 실제 교체·공유·활동 중 자원 보호 |
| DEV-08 | 공통 스킬, docs, 빌드·설치 스크립트 | 새 버전 번들 생성과 두 제공자 공통 절차, 호스트 재설치 | 설치 완료; 실제 workflow 실행·개별 수용 근거 미확인 |
| DEV-09 | `shared/presentation.py`, `board/format.py`, 보드 훅 | 개요/상세/2열 기준표, HTML, 영어·사용자 언어 분리, 선택 조회 | 번역 의미는 조율자가 검토. 기존 카드 본문을 일괄 재작성하지 않음 |
| DEV-10 | `board/labels.py`, `instructions.py`, Application | 유형 라벨·부모 보드 지침·버전/해시 참조·변경 검토와 작업자 전달 | 라벨 API 범위 필요. 모든 활성 지침을 기본 포함해 누락 방지; 내용이 크면 조율자가 관련 상세를 선별 |

## 공통 실행 계약

| 기록 | 의미 |
| --- | --- |
| Plan/cycle/Work/Attempt | 기획 회차, 작업, 실제 실행의 식별자 |
| provider/model/effort/source | 사용자가 정했거나 실제 관측한 선택과 출처 |
| launch/requested_paths/policy_observation | 요청한 실행 인수와 쓰기 범위; 실효 권한과 별도 |
| readiness | 작업자 자신의 도구 경계에서 실행한 최소 쓰기 진단 보고 |
| worker_submission | 제출 ID, 후보 commit, 실제 확인/미확인/차단/지침 준수 보고 |
| delivery/received_at/processed_at | 수신과 조율자 검토 처리 상태 |
| monitor | 담당, 대상, 마지막/다음 확인, 주기·backoff, 감시 실행 여부 |
| review_notice | 내부 Review와 별개인 사용자 보고 내용·시각·당시 보드 전송 상태 |
| instruction_reference | 원본 카드 ID·버전·본문 해시·범위·참조 영역·적용 근거 |
| cleanup_choice | 실제 room/pane/terminal/소유 출처에 대한 close/keep 선택 |

Work Review는 조율자 검토 대기다. Plan Review는 모든 필수 작업의 검토·통합·기준별 근거 및 최종 canonical revision 확인을 통과한 사용자 검토 대기다. 최종 Done은 사용자 수락으로만 기록한다. 프로세스 idle/done이나 제출의 verification 텍스트로 검증을 통과시키지 않는다.

## 권한과 지원 범위

조율자/작업자 Codex→Codex, Codex→Cursor, Cursor→Codex, Cursor→Cursor는 같은 도메인 경로를 사용한다. 네 조합의 실제 호스트 수용 테스트는 모두 미실행이다. CLI 규칙과 IDE 정책을 동일한 것으로 보고하지 않는다.

`access plan`은 read, board-sync, summary-sync, labels-sync, monitor, cleanup, onboarding 중 필요한 그룹의 규칙을 제시한다. `access apply`는 해당 호스트 정책 변경을 승인받은 경우에만 실행한다. `access revoke`는 Handrail이 추가했다고 기록한 규칙만 제거한다. Codex는 저장소와 동작을 포함하는 argv 접두어, Cursor는 `Shell(command:args)` 규칙을 사용한다. 임의 Python·셸·전체 Handrail 허용은 생성하지 않는다. 기존 Cursor deny/설정과 Codex 규칙은 유지한다. 사용자 설정·관리 정책은 실제 집행자가 우선하며, 저장했다는 이유로 적용됐다고 보고하지 않는다.

`access record`의 kind와 category로 호스트 승인·사용자 선택·대기, 의도·보드·모델·호스트 실행·수락·정리를 구분하고 관측한 대기 시간을 기록한다. 미기록 승인이나 실제 사용자 클릭 수를 추정해 집계하지 않는다.

작업자에게 전달하는 네 경로는 할당 worktree, 실제 gitdir, 공유 commondir, 해당 실행의 보고 채널이다. 토큰·관리 DB·다른 worktree·Herdr 제어를 쓰기 경로에 추가하지 않는다. 공유 Git 메타데이터 쓰기는 저장소 수준의 영향이 있으므로 브랜치 격리라고 부르지 않는다. Codex는 현재 legacy workspace-write 경로를 사용하고 프로필 키와의 충돌 가능성을 진단에 표시한다. 관리 프로필이 이를 거부하면 실제 적용은 blocked/unknown으로 남는다. 전역 sandbox 해제나 자동 권한 확대를 하지 않는다.

작업자 진단은 커밋을 만들지 않는다. 진단 보고는 같은 OS 사용자와 악의적인 프로세스 사이의 보안 인증 수단이 아니다. nonce·fingerprint는 다른 실행의 보고 혼입을 막는 일관성 장치다. 실제 코드·검증·정책 판단은 조율자가 확인한다.

## 기본 작업보드와 원본 보존

init·기획 작성·조회에서는 default를 만들지 않는다. 실제 Work 생성/실행 준비가 기존 카드→Work 배정→Plan 배정→등록된 default 순서로 결정한다. 서버·부모 보드별 공유 setup registry로 같은 호스트의 다른 저장소에서도 재사용한다. Handrail 생성 마커나 사용자 등록 근거가 없는 동명 보드는 자동 인수하지 않는다. `board default BOARD --reason USER_SELECTION`으로 선택한다.

응답 유실은 기존 의도를 조회해 복구한다. unknown이란 이유만으로 같은 생성 POST를 다시 보내지 않는다. 다른 호스트의 전역 원자적 중복 방지는 보장하지 않는다. 기존 카드 위치, 사용자 상태 강제 전환·보류, 기존 열 매핑을 보존한다. 라벨 충돌도 사용자 라벨 삭제로 해결하지 않는다.

Instruction 원본·이전 본문은 부모 보드 카드와 댓글에 둔다. 처음 참조한 본문 해시마다 제목·원문을 해당 카드 댓글에 보존하고 동일 버전은 재사용한다. 따라서 댓글 작성 권한이 필요하다. 댓글·조회 시각 변경만으로 지침 변경을 감지하지 않는다. 로컬에는 참조와 진행 중 쓰기 의도/복구 정보가 남는다. 수동 instruction 카드도 발견하며, 조회 실패와 지침 없음은 구분한다. 변경을 감지하면 영향과 범위를 확인한 뒤 `instruction use`로 기록하고 `instruction deliver`로 해당 작업자에게 전달한다. 프로젝트 지침은 실행 권한이나 자원 삭제 동의가 아니다.

기존 관리 카드의 라벨은 `card types`로 적용한다. 로컬 Plan·Work·Summary 연결로 대상을 판별하며 제목 추측, 카드 본문·상태·위치 변경을 하지 않는다. 일부 카드 실패는 개별 결과와 종료 코드에 반영한다.

## 복구와 운영

- 완료 보고가 화면 알림에서 누락돼도 채널의 submission과 coordinator inbox로 복구한다. tick을 활성 대화에서 반복하고 재접속 시 즉시 다시 확인한다.
- 실제 백그라운드 스케줄러나 호스트 알림 등록은 없다. `running=false`, 마지막 관측과 다음 확인 시각을 표시하며 감시 중이라고 가장하지 않는다.
- Work 수신 뒤 조율자가 변경 검토·통합·허용된 검증을 이어간다. 모든 근거가 있으면 followthrough가 Plan Review까지 진행하고, 부족하면 구체적인 차단을 반환한다.
- 사용자에게 실제로 결과/Review 링크를 전한 뒤 `coordinator report --message`로 기록한다. 기록 명령은 채팅을 보내지 않는다.
- Done 후 정리는 `plan cleanup --inspect` → 필요시 `--reconcile TOKEN --evidence TEXT` → `--resume` → `sync --topic room.cleanup`이다. 정상적인 세션 ID 보강으로 기존 close 선택을 무효화하지 않는다. 신원 교체·관측 불가를 강제 종료로 우회하지 않는다.
- CLI는 중첩된 정리/보드/후처리 실패를 nonzero로 반환한다. Plan Done, 전송 대기, 방 정리 실패는 독립 상태다.

## 이번 확인의 범위

Python 파일 62개의 Python 3.9 구문 AST 및 내부 모듈 경로와 Markdown 문서 30개의 상대 링크를 정적 분석했고 오류가 없었다. 자동 테스트·실제 보드 쓰기·작업자 실행·승인 클릭 측정은 수행하지 않았다. 후속 요청에 따른 호스트 재설치와 설치 파일 75개의 무결성·버전·스킬 연결 확인을 완료했다. 사용자 요청에 따라 체크리스트를 모두 닫되, 이 종료로 실제 테스트·측정·수용 근거를 새로 만들지 않는다.

최종 번들: `dist/alpha6-checklist-final/handrail-1.0.0-alpha.6.zip`. 실행 지시 재개는 최초 전송 본문을 고정하며, 지연 신원 보강으로 기존 전송 의도의 해시를 바꾸지 않는다. 실제 적용 지침을 변경할 때는 별도 변경 전달을 기록한다.

번들 SHA-256: `7969676297b318003d30cfb28772bafe8c3cbfcd004988732492b69d63cdef27`.

호스트 설치 근거: [설치 보고서](../dist/alpha6-checklist-final/host-install-report.json). 고정 런처는 `~/.local/bin/handrail`, Cursor 스킬은 `~/.cursor/skills/handrail`이며 Codex 캐시 외부의 관리된 alpha.6 release를 사용한다. 기존 alpha.5 설치물은 제거하고 연결·바인딩·이력·worktree·외부 서비스 데이터는 보존했다. 새 세션에서 사용자 테스트를 진행한다.

프로토콜 참고: [Vikunja v2](https://vikunja.io/docs/api-v2/), [Vikunja API](https://try.vikunja.io/api/v2/docs), [Cursor CLI 권한](https://cursor.com/docs/cli/reference/permissions), [Cursor sandbox](https://cursor.com/docs/reference/sandbox), [Codex 권한](https://learn.chatgpt.com/docs/permissions).
