# 구현·이관 계획

## 1. 진행 원칙

새 구현의 출발점은 현재 Python 저장소다. 현재 작업 트리의 변경과 사용자가 운영 중인 설정을 먼저 확인한다. 이 설계 문서 작성으로 제품 구현·Vikunja 변경·플러그인 설치가 승인됐다고 간주하지 않는다.

구현을 요청받은 뒤에는 해당 요청에 이미 포함된 범위와 권한으로 진행한다. 이 문서를 이유로 매 단계 같은 승인을 다시 요구하지 않는다. 외부 데이터 삭제나 범위 밖 서비스 변경은 별도 행위다.

## 2. 단계별 산출물

| 단계 | 작업 | 완료 조건 |
| --- | --- | --- |
| P0: 계약 확인 | Codex plugin loading, Python, Cursor help, 대상 Vikunja OpenAPI·권한 조사 | `IMPLEMENTATION_PLAN.md`에 확인/미확인·fixture·지원표 기록 |
| P1: 플러그인 골격 | manifest·스킬·launcher·번들 빌드 | 별도 Handrail 설치 없는 깨끗한 환경에서 status 호출 |
| P2: 설정과 v2 | config/TokenStore, 숨김 입력, 프로젝트·뷰·열 선택, v2 adapter | 온보딩은 읽기 전용, token 비노출, 설정 재개·교체 가능 |
| P3: 기존 데이터 이관 | preview/apply, workspace·보드·명세 ID 보존, 서비스 운영 분리 | 백업·충돌·재실행·rollback 시나리오 통과 |
| P4: 작업 계약 보강 | Context·첨부, structured RESULT, 승인 검증 계획 | 승인과 현재 산출물에 맞는 필수 검사만 수용 근거로 사용 |
| P5: 실행·복구 | repo 잠금, 감독 프로세스, run 상태·게시 기록 | 중복 실행 차단, cancel/crash/외부 장애에서 결과 보존 |
| P6: 제품 수용 | Codex→Codex 먼저, Codex→Cursor 이어서 검증·리뷰·로컬 통합 | 두 경로의 모델 선택·전체 사이클·실패 경로 기록 |
| P7: 릴리스 | 배포 파일 검증, 새 설치·업데이트·구스킬 충돌 안내 | 문서와 artifact 버전 일치, 재현 가능한 plugin 설치 |

P1은 패키징 실험이지 릴리스 완료가 아니다. P2–P6의 필수 조건을 갖춘 뒤 새 사용자 배포를 선언한다. Cursor 오케스트레이터·MCP 평가·하위 보드 생성은 [BACKLOG](BACKLOG.md)의 후속 항목이다.

## 3. 제거·축소·유지 대상

| 현재 요소 | v0 처리 |
| --- | --- |
| `board.up/stop/launch`, 사용자·manager 계정 생성 | 새 배포의 실행 기능에서 제외 |
| `project init --kanban-dir` | 기존 repo 연결 중심으로 변경, data path 질문 제거 |
| `board.init/ensure_view`의 원격 생성·재배치 | 연결 경로에서 제거, 기존 선택·매핑으로 대체 |
| `setup --git-provider/--forgejo-base`, `project remote`, Forgejo 안내 | 제품 명령·설정·스킬에서 제외 |
| git remote·push·PR 상태 | 새 스키마에 넣지 않음, 기존 `.git/config` 보존 |
| 전역 스킬 설치·`install.sh` | 기존 사용자 이관·개발용 호환 경로로 한정 |
| 승인 명세·fingerprint·verify·review·로컬 integrate | 서비스로 재사용·필요 조건 보강 |
| Codex/Cursor worker adapter | 유지, capability와 환경 전달 검증 |
| 기타 구형 worker provider | v0 지원·신규 등록 범위에서 제외, 구형 설정은 이관 기록에 보존 |
| 개발 Docker·관리형 API fixture | 개발 전용으로 유지 가능, 배포 제외 |

구형 관리 명령을 새 런타임에 남겨야 하는 과도기라면 실제 서비스 조작 대신 이관 안내로 종료시킨다. 새 버전 설치만으로 기존 Docker 컨테이너를 멈추거나 삭제하지 않는다.

## 4. 기존 사용자 이관

### 4.1 Preview

새 `migrate --dry-run`은 구형 `HANDRAIL_HOME`/registry, repo `.handrail`, profile·run·worktree의 구조만 조사한다. 비밀값은 출력하지 않는다. 출력에는 변경 파일·schema, 충돌, 미지원 API, 진행 중 run, 사용자 수정 스킬이 포함된다.

preview는 외부 데이터를 바꾸지 않는다. 기존 미커밋 파일도 덮어쓰지 않는다. URL·project/view/bucket 정보를 확인할 네트워크 접근은 읽기만 수행한다.

### 4.2 Managed Vikunja에서 외부 연결로 전환

운영 중인 관리형 Vikunja를 외부 인스턴스처럼 연결할 수 있다. 서버 URL·project/view/bucket ID는 유지한다. 서비스의 수명·DB·files·container 설정은 이후 사용자가 관리한다.

사용자는 자신의 계정에서 발급한 토큰을 등록하는 방식을 기본으로 한다. 기존 manager 토큰을 계속 쓰려면 소유 계정·권한·대상 인스턴스에 대한 선택을 명시한다. 기존 토큰이 있다는 이유만으로 사람 계정의 권한이나 계정 소유권이 이전됐다고 해석하지 않는다.

이관은 manager 비밀번호·JWT secret을 새 config로 복사하지 않는다. 서버의 기존 계정·비밀번호·API 토큰을 삭제하거나 변경하지 않는다. 구형 credential 파일은 backup에 보존하고, 새 연결 검증 뒤 사용자에게 정리 대상을 알려준다.

### 4.3 설정·식별자 변환

1. 기존 workspace UUID와 `.handrail` 경로를 유지한다.
2. workspace별 root 및 추가 areas의 project/view/states ID를 공유 가능한 binding으로 옮긴다. root는 각 Handrail 프로젝트에 하나씩 유지하고 다른 workspace와 합치지 않는다. areas의 실제 부모 관계도 확인하며 불일치는 충돌로 보고한다.
3. URL·로컬 경로·선택한 profile은 사용자 config/registry로 분리한다.
4. `card-NNNN` 참조는 기존 project/instance 정보와 함께 복합 identity로 매핑한다. 기존 spec 문서 이름·원문을 불필요하게 바꾸지 않는다.
5. 명세 원문이 그대로면 내용 hash를 유지한다. 승인 manifest 구조 변환만으로 승인 원문을 새로 만들어 내지 않는다.
6. 기존 registry의 Git provider/base 데이터는 새 schema에서 사용하지 않는다. rollback용 backup에는 원문을 보존한다.

같은 URL에 여러 credential이 있을 때 자동 합치지 않는다. URL 정규화만으로 동일 계정·서버·권한을 증명할 수 없다. 프로젝트별 프로필로 보존하고 필요하면 사용자가 나중에 정리한다.

### 4.4 실행 기록과 진행 중 작업

실행 중인 run 또는 미통합 worktree가 있으면 해당 workspace의 이관 적용을 보류한다. 구버전에서 완료하거나 명시적으로 abandon한 뒤 전환한다. active 상태만 지워 새 run을 시작하지 않는다.

구 CLI는 새 durable 잠금·schema를 인식하지 못할 수 있으므로 이관 이후 같은 workspace를 구·신 런타임으로 동시에 관리하지 않는다. 지원하는 새 런타임들은 schema·build 호환 검사를 공유하고, 호환되지 않는 버전으로 기존 run을 재개하지 않는다.

과거 run은 `legacy` schema로 읽기 가능하게 보존한다. 과거 자유형 RESULT를 새 structured 결과로 위조하거나 기존 review에 새 validation ID를 만들어 붙이지 않는다. 새 조건에 따른 검증을 실제로 수행한 경우에만 새 evidence를 기록한다.

### 4.5 Apply와 rollback

명시적 이관 실행은 private backup → 새 schema 검증 → 새 credential/config 기록 → registry 전환 → repo binding 변경 순서로 수행한다. 다중 파일 변경 단계와 이전 revision을 migration journal에 기록한다.

실패하면 journal을 통해 완료한 단계만 판정하고 재실행한다. 비밀 파일을 일반 로그·Git patch에 저장하지 않는다. 로컬 backup은 0700/0600으로 제한한다.

rollback은 이관 후 새 run이나 새 설정 변경이 없는지 확인하고 이전 revision과 일치하는 파일만 복원한다. 이후 사용자 변경이 있으면 충돌을 보고한다. Vikunja 데이터·컨테이너·Git remote를 되돌리는 작업은 이관에 포함되지 않는다.

## 5. 검증 시나리오

아래는 후속 구현의 검증 계획이다. 이번 설계 문서 작업에서 실행한 테스트 결과가 아니다.

| 영역 | 시나리오 | 기대 결과 |
| --- | --- | --- |
| 패키징 | 글로벌 Handrail 없는 환경, 공백 경로, read-only plugin cache | 번들 코드 호출, cache 쓰기 없음 |
| 발견 | root+호환 manifest, 새 채팅, 구형 스킬 잔존 | 스킬 중복/충돌 확인, 현재 버전 식별 |
| 설치 | Docker 미설치, Vikunja 미준비 | plugin 설치와 안내 가능 |
| 비밀 입력 | TTY 없음, echo 비활성화 실패, 사용자 취소 | 평문 입력 fallback 없이 중단·재개 |
| 비밀 저장 | 신규·교체 중 crash, symlink 대상, 권한 과다 | 기존 정상 credential 보존 또는 명확한 복구 |
| 정보 노출 | 임의 형식의 테스트 토큰을 오류·stdout·packet·worker env에서 검색 | 원문 없음 |
| API | v2 페이지 envelope, empty 204, 401/403/404/422, redirect | 올바른 파싱·원인별 오류, 다른 origin에 인증 전달 없음 |
| 보드 | 이름 중복, 다국어, read-only 권한, 필터 Kanban, 잘못된 done 매핑 | ID 선택과 검증, 무단 원격 변경 없음 |
| 다중 프로젝트 | 한 인스턴스의 여러 board, 여러 계정, 같은 numeric task ID | 연결 밖 task 차단, profile 혼용 없음 |
| 호스트 내 여러 workspace | A/B 각각 부모 하나, 같은 프로필 재사용, 다른 터미널의 선택 변경 | 각 binding·명세·run 유지, 신규 프로젝트에 이전 보드 자동 배정 없음 |
| Git 경계 | origin 있음/없음, 다른 provider, 연결 불가 remote | 원격 접근 없이 로컬 작업 가능, `.git/config` remote 보존 |
| Context | 경로 탈출 파일명, symlink, 대용량, 악성 지시문 첨부 | 안전 저장·범위 제한·명령 실행 없음 |
| 승인 | 승인 뒤 명세 수정, 다른 task의 승인, 필수 check 누락 | 실행/accept 거부 |
| 실행 | 두 manager·두 worktree에서 동시에 시작, crash 후 PID 재사용 | 동일 repo 쓰기 하나, 점유 임의 해제 없음 |
| worker | 미설치, 옵션 미지원, 인증 실패, timeout, cancel | 정확한 실패 상태와 산출물 보존 |
| 모델 | 두 provider, 실행/프로젝트/프로필 설정, 미지원 모델, 실제 모델 미제공 | 지정 우선순위·기록 일치, 자동 대체 없음, 미확인 실제 모델은 null |
| 결과 | result 없음/구조 오류/다른 round, exit 0+blocked | returned/accepted 오판 방지 |
| 검증 | 성공·실패 검사 혼합, 검사 후 소스 변경, 의미 검토 누락 | 최신 모든 필수 근거가 있어야 accept |
| 통합 | baseline 이동, dirty source, fingerprint 변경 | 자동 reset/stash 없이 중단 |
| 게시 | 응답 유실, 댓글 중복 위험, 사용자 상태 변경, 서버 장애 | unknown/conflict/pending 구분, worker 재실행 없음 |
| 이관 | multi-area, 기존 manager creds, 구형 run, 부분 실패 재실행 | 원문·서비스·remote 보존, 안전한 재개 |

외부 호출 없는 unit/contract 검증을 기본으로 하고 실제 Vikunja·Codex·Cursor 호출은 명시적인 통합 환경에서 한다. 실제 모델 호출 여부와 사용량 발생을 테스트 결과에 기록한다. 필요한 핵심 계약을 검사하며 구현 함수를 그대로 복제하는 테스트는 만들지 않는다.

## 6. 릴리스 판정

완료 보고는 구현된 것·검증한 것·미확인 범위를 구분한다. 특히 다음 세 항목은 서로 다르다.

- plugin ZIP 생성과 manifest 정적 검증.
- Codex에 설치한 후 실제 스킬·번들 코드 실행.
- 외부 Vikunja와 실제 worker를 사용하는 전체 개발 흐름.

릴리스에는 지원 환경표, fixture에 사용한 API schema hash, 검증 명령·결과, 실패 복구 사례, 사용자 설정 이관 방법을 남긴다. 원격 Git 운영은 지원 환경표나 설치 완료 조건에 포함하지 않는다.
