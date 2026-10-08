# Cursor CLI / Grok 4.7 검토 결과와 반영 판단

검토일: 2026-09-30. 사용자의 요청에 따라 실제 Cursor CLI로 Grok 4.7 검토를 받았다.

## 1. 실행 기록

| 항목 | 관측 결과 |
| --- | --- |
| Cursor CLI | `2026.09.28-64d2043` |
| 요청 모델 | `grok-4.7-high` — `agent --list-models`에서 확인 |
| 모드 | `--print --mode ask --sandbox enabled --trust --output-format json` |
| 입력 | 설계 문서 9개와 Python 소스 5개의 임시 복사본 |
| 소요·반환 | 약 337초, exit 0, `subtype=success`, `is_error=false` |
| 확인한 응답 필드 | `result`, `session_id`, `request_id`, `duration_ms`, `usage` 등 |
| 실제 모델 필드 | 없음. 별도 확인된 실제 모델은 null |

읽기 전용 검토를 요청했고 입력 파일의 hash가 유지되는 것을 확인했다. 프록시는 조사·검토 subprocess에서 해제했다. 토큰 파일·사용자 보드를 입력으로 전달하지 않았다. 이 호출은 제품 구현이나 Handrail 플러그인 로딩 시험이 아니다.

[검토 원문](reviews/CURSOR_GROK_4_7.md)과 [입력 hash·실행 메타데이터](reviews/CURSOR_GROK_4_7_METADATA.json)를 보존한다. 원문은 반영 전 스냅샷을 대상으로 하므로 아래 판단과 최종 설계가 우선한다.

## 2. 최종 패키징 판단

**공통 코어와 portable 배포물 하나를 기본으로 하고, Codex와 Cursor의 설치·연동·지원 검증을 별도로 관리한다.** agent별 코어 패키지나 모델별 패키지는 필요하지 않다. 전용 기능이나 CLI 호환성 때문에 필요한 차이가 확인되면 같은 소스에서 배포 변형을 생성한다.

Grok도 코어 복제가 불필요하며 공통 소스·스테이징·호스트별 설치 메타데이터를 유지하는 데 동의했다. 공통 ZIP의 실제 양쪽 로딩이 아직 검증되지 않았다는 지적은 채택한다. 다만 미검증 상태만으로 지금 별도 ZIP 두 개를 만들 필요는 없다. v0는 Codex 지원을 선언하고 Cursor 지원은 수용 검증 뒤 추가한다.

OpenAI는 portable root manifest를, Cursor는 같은 형식과 CLI에서의 플러그인 사용을 공식 문서로 안내한다. 이는 공통 배포 설계의 근거이며 특정 버전에서의 Handrail 실행 성공을 보증하지는 않는다. [OpenAI](https://developers.openai.com/plugins/build/plugins), [Cursor 형식](https://cursor.com/docs/reference/plugins), [Cursor 플랫폼 안내](https://cursor.com/help/customization/plugins)

세부 구조와 분리 조건은 [PACKAGING_DECISION.md](PACKAGING_DECISION.md)를 따른다.

## 3. 지적사항 처리

| 검토 의견 | 판단과 반영 |
| --- | --- |
| Cursor CLI의 스킬 발견·번들 스크립트 호출 확인 | 채택. HR-NEXT-001의 첫 단계 C0 |
| 공통 코드와 호스트별 설치·지원 구분 | 채택. PACKAGING_DECISION과 PROJECT_STRUCTURE |
| 검증 전에는 반드시 Codex/Cursor ZIP을 따로 생성 | 보류. 실제 규격 충돌이 있으면 공통 소스의 빌드 변형으로 처리 |
| manager와 worker 권한·환경 구분 | 채택. MASTER_SPEC에 보강. 같은 사용자 sandbox의 실제 경계는 별도 확인 |
| worktree를 새 Handrail 프로젝트로 오인하지 않아야 함 | 채택. Git common directory와 workspace ID로 원 프로젝트 해석 |
| 두 호스트의 잠금·run schema·runtime 버전 호환 | 채택. 공통 코어의 조건으로 보강 |
| 구 CLI도 새 잠금을 읽어야 함 | 조건부. 구 CLI에 소급 적용할 수 없어 이관 때 동시 사용 금지와 전환 조건 명시 |
| `--trust`와 `--output-format` 미확인 | 정정. 주 검토자가 로컬 help에서 확인했고 이번 성공한 호출에도 사용 |
| JSON의 session/result/model 관측 | 일부 확인. session/result는 존재, model은 없음. 한 응답으로 전체 schema를 고정하지 않음 |
| Python 3.12.3을 현재 환경 지원표에 넣기 | 미채택. 리뷰가 제시한 버전에 대한 관측 근거 없음. 릴리스 시 실제 경로·버전을 기록 |
| root의 `extensions.com.openai` 금지 | 현 v0의 overlay 중복 방지 정책으로 유지. 표준 자체의 금지 사항은 아님 |
| MCP는 C0 실패 때만 도입 가능 | 수정. C0 실패 외에도 MCP 전용 클라이언트·공통 도구 규격 요구가 판단 근거가 될 수 있음 |
| 원격 Git·보드 일괄 생성·환경 denylist 수정 | 기존 이관 항목 유지. 이번에 제품 코드 수정 완료로 처리하지 않음 |
| Gemini가 코드에 남아 있음 | v0 지원·신규 등록 provider는 Codex/Cursor로 제한. 구형 데이터 자동 삭제 없음 |

원문의 “차단”에는 아직 구현하지 않은 목표 계약도 포함돼 있다. 해당 기능의 구현·릴리스 수용 조건으로 관리한다.

## 4. 후속 검증 단계

| 단계 | 확인할 내용 | 이번 결과 |
| --- | --- | --- |
| C0 | MCP 없는 최소 플러그인 발견 → 번들 스크립트 호출 → cache 비쓰기 | 미실행. Cursor 연동 구현의 첫 단계 |
| C1 | 모델 지정과 CLI JSON 결과 구조 | 리뷰 1건 확인. 제품 parser의 전체 계약 검증은 남음 |
| C2 | 두 호스트에서 같은 repo 쓰기 점유 충돌 | 미실행. 공통 잠금 구현 후 확인 |
| C3 | 실제 Cursor 세션의 설정·부모 보드·두 provider 위임·리뷰·복구 | 미실행. Cursor 지원 선언의 필수 조건 |

C0에서 두 호스트의 스킬 발견 개수·설치 경로·읽기 전용 cache를 확인한다. 실패 원인을 조사한 뒤 호스트 안내 수정, manifest 변형, MCP 중 필요한 것을 선택한다. 설치 설정 오류만으로 MCP가 필수라고 결론내리지 않는다.

## 5. 공동 개발

Codex가 코어와 CLI 계약을 정리하고 Cursor CLI가 읽기 검토와 Cursor 호스트 연동 구현을 맡는다. 같은 저장소 쓰기는 순차 위임하고 Codex가 검토·통합한다. 최종 수용은 실제 Cursor 오케스트레이터 세션에서 수행한다. 이번 Grok 호출은 첫 읽기 검토이며 구현은 아직 시작하지 않았다.
