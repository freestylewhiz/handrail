# Cursor CLI / Grok 4.7 검토 원문

사용자 요청에 따른 실제 Cursor CLI 호출 결과다. 아래 의견은 검토 모델의 판단이며, 사실 확인과 채택 여부는 [주 검토자의 검토 결과](../CURSOR_REVIEW.md)를 따른다. 본문 앞의 진행 안내 문장만 생략했다.

- 호출 모델: `grok-4.7-high` (Grok 4.7 High).
- CLI: `2026.09.28-64d2043`, `--mode ask --sandbox enabled --print --output-format json`.
- 결과: exit 0, `subtype=success`, `is_error=false`.
- 실제 모델 식별자: 응답에 별도 필드 없음. 요청한 모델과 서버가 확인한 모델을 구분한다.
- 검토 입력: 설계 9개와 관련 소스 5개의 읽기용 복사본. 이후 주 검토자의 추가·수정 전 스냅샷이다.
- 공식 문서는 주 검토자가 조사해 출처와 요점을 전달했다. 리뷰 모델은 재조회하지 않았다고 밝혔다.
- 구현·Vikunja 변경·플러그인 설치·애플리케이션 테스트는 수행하지 않았다.

---

# Handrail Cursor CLI 오케스트레이션 설계 검토

검토일: 2026-09-30. 대상은 제공된 `spec/*.md`와 `source/*.py` 스냅샷이다. 홈 설정, 자격 증명, 원 저장소, Handrail 매니저 명령, 테스트, 플러그인 설치는 보지 않았다. 공식 문서 동작은 주 검토자가 확인했다고 한 출처에 기대며, 이번 세션에서 다시 열어 재현하지 않았다.

판정은 세 가지로 나눈다. **사실**은 스냅샷이나 이번 작업에서 확인된 로컬 CLI 표면이다. **설계 권고**는 그 사실에서 나온 변경안이다. **미검증 가정**은 런타임에서 아직 보지 못한 동작이다.

## 결론

공통 Python 코어를 유지하고, v0 사용자 배포물은 Codex 플러그인으로 두는 결정은 유지할 수 있다. Cursor CLI를 그 코어의 오케스트레이터로 쓰는 일은 같은 결론으로 따라오지 않는다. MCP 없는 오케스트레이션은 Cursor에서 **가능한 설계**이지 **확인된 능력**이 아니다. 별도의 에이전트 패키지(코어 복제)는 만들 필요가 없다. 하나의 Codex ZIP을 Cursor 설치물로 인증하는 것도 성립하지 않는다. 권장 포장은 공통 소스, 공통 스테이징 산출물, 호스트별 설치 메타데이터, 호스트별 지원 인증이다.

## 1. Cursor CLI가 MCP 없이 이 코어를 오케스트레이션할 수 있는가

**사실.** 설계의 호출 경로는 스킬이 `python3 -I <plugin-root>/scripts/handrail.py`를 인자 배열로 실행하는 것이다 (`PROJECT_STRUCTURE.md` §5, `MASTER_SPEC.md` §3). MCP는 v0 필수에서 빠져 있고, 빈 `mcp.json`을 넣지 않는다고 적혀 있다 (`PROJECT_STRUCTURE.md` §8, `BACKLOG.md` HR-NEXT-002). 이 “스킬만으로 배포 가능” 근거는 OpenAI 플러그인 문서와 Codex shell 모델에 있다 (`README.md` 외부 문서 전제, `COMPARISON.md` §4 대안 B).

**사실.** 이번 작업에서 본 Cursor CLI `2026.09.28-64d2043`의 `agent --help`에는 `--plugin-dir`, `--workspace`, `--mode ask/plan`, `--model`, `--print`, `--sandbox`가 있다. `agent plugin --help`는 marketplace 하위 명령을 보여 준다. `agent --list-models`에 `grok-4.7-high`가 있다. 플러그인 설치와 제품 흐름은 시험하지 않았다.

**미검증 가정.** Cursor 문서의 루트 `plugin.json`은 portable skills/MCP를, `.cursor-plugin/plugin.json`은 rules/agents/commands/hooks/variables를 다룬다고 주 검토자가 확인했다. 그 소개는 IDE를 다루므로, CLI가 같은 형식의 스킬을 읽고 스킬 지시대로 로컬 Python을 실행하는지는 별도 사실이다. `--plugin-dir`가 그 루트 형식을 로드하는지도 마찬가지다. marketplace 하위 명령만 보였으므로 Codex식 `plugin add`가 있다고 보면 안 된다.

**설계 권고. 심각도: 차단.** 문서: `MASTER_SPEC.md` §3·§10, `COMPARISON.md` §4, `BACKLOG.md` HR-NEXT-002, `MIGRATION_PLAN.md` P0. 이유: MCP가 불필요하다는 문장은 Codex가 번들 CLI를 실행할 수 있다는 전제에 묶여 있다. Cursor 오케스트레이터는 그 전제가 게이트를 통과하기 전에는 후속 가설이다. 게이트가 실패하면 그때 MCP 또는 호스트 네이티브 command를 평가한다. 실패 전에 MCP 서버를 만들지 않는다. Codex v0의 스킬+번들 도구 경로는 이 게이트와 따로 진행할 수 있다.

최소 게이트 C0: MCP 설정이 없는 fixture에 루트 `plugin.json`, `skills/handrail/SKILL.md`, nonce만 출력하는 `scripts/handrail.py`를 둔다. 사용자 저장소에는 스킬을 복사하지 않는다. `agent --plugin-dir <fixture> --workspace <repo> --print`로 그 스크립트 실행을 한 번 요청한다. 통과는 스킬이 한 번만 보이고, 스크립트 경로가 플러그인 루트 기준이며, nonce가 돌아오고, 플러그인 디렉터리에 파일이 생기지 않는 것이다. 실패·무시·sandbox에서의 홈 쓰기와 네트워크 거부는 결과로만 기록하고, 동작을 메워 넣지 않는다.

## 2. 호스트별 스킬·설치·발견·승인·세션

**사실.** 스냅샷 `projects.install_skill()`은 저장소 `.agents/skills/handrail`에 스킬을 쓰고 `AGENTS.md`에 마커를 붙인다. `PROJECT_STRUCTURE.md` §6은 플러그인 설치가 저장소 `AGENTS.md`를 수정하거나 매니저 스킬 전체를 복사하지 않는다고 한다. 현재 코드와 목표 계약이 다르다.

**사실.** `workers.command()`의 Cursor 인자는 `--workspace`, `--sandbox enabled`, `--trust`, 선택적 `--model`, 읽기 전용일 때 `--mode ask`, 비대화형일 때 `--print --output-format json`이다. 이번 help 요약에 확인된 것은 `--workspace`, `--sandbox`, `--mode`, `--model`, `--print`까지다. `--trust`와 `--output-format`은 이 작업에서 확인된 표면이 아니다.

**사실.** `workers.execute()`는 모델이 비어 있으면 `'CLI default'`라고 기록한다. `MASTER_SPEC.md` §10은 확인하지 못한 실제 모델을 null로 두고, CLI 기본값을 모델명으로 추측하지 않는다. `workers.env()`는 이름에 TOKEN·SECRET·HANDRAIL 등이 들어간 변수를 빼는 denylist다. 명세는 승인된 provider 인증만 남기는 allowlist다 (`MASTER_SPEC.md` §10).

**미검증 가정.** 스킬이 `SKILL.md` 위치에서 `../../scripts/handrail.py`를 찾는 계산(`PROJECT_STRUCTURE.md` §5)은 호스트가 플러그인 트리를 그대로 둘 때 맞다. Cursor가 스킬만 다른 캐시로 복사하면 그 상대 경로는 깨진다. C0가 이 경로를 관측해야 한다. Cursor `--print` JSON에 `session_id`, `result`, 실제 모델이 있는지도 한 건의 stdout으로만 확인한다. 파서 필드를 그 전에 고정하지 않는다.

**설계 권고. 심각도: 차단.** 문서: `SETUP_AND_CONFIGURATION.md` §1·§4, `MASTER_SPEC.md` §10, `source/workers.py`. 이유: 오케스트레이터는 Vikunja로 나가고, XDG 설정·잠금·저장소 밖 worktree를 쓴다. worker는 sandbox와 비밀 경로 차단이 필요하다. 둘을 같은 `--sandbox enabled`와 `--trust`로 두면 매니저 쓰기가 막히거나, 반대로 worker가 자격 증명 파일을 같은 사용자 홈에서 읽을 수 있다. 0600은 같은 OS 사용자 격리가 아니라는 문장은 이미 있다. 여기에 호스트 프로파일을 둘로 적는다. 오케스트레이터는 네트워크와 XDG 쓰기, worker는 worktree 안 쓰기와 provider 로그인 파일만. 토큰은 사용자 TTY의 `getpass`만 사용하고, `--print` 세션은 `INTERACTIVE_SECRET_INPUT_REQUIRED`로 멈춘다. 설치된 help에 없는 플래그는 capability probe 실패로 두고 호출하지 않는다.

**설계 권고. 심각도: 높음.** 문서: `PROJECT_STRUCTURE.md` §6–§7, `BACKLOG.md` HR-NEXT-001. Cursor 설치 절차는 marketplace 도움말에 있는 하위 명령과 `--plugin-dir`만 후보로 적는다. Codex의 add/list/remove와 `source.path` marketplace 규칙을 Cursor 절에 복사하지 않는다. 캐시 경로가 호스트마다 달라도 사용자 데이터는 `XDG_*/handrail` 한곳이다. 플러그인 캐시에는 설정과 토큰을 쓰지 않는다는 기존 문장을 Cursor 캐시에도 적용한다.

**미검증 가정.** 오케스트레이터 `agent`가 worker `agent`를 띄울 때 플러그인, sandbox, 승인 프롬프트, 세션이 상속되는지는 모른다. `BACKLOG.md`의 “코어가 대화용 CLI를 중첩해 오케스트레이터를 만들지 않는다”와 “worker로 `agent`를 실행한다”는 서로 다른 동작이다. 후자만 구현 대상이고, 상속으로 승인 대화가 멈추는지는 C0 이후에 한 번 본다.

## 3. 패키지 하나인가, 설치 메타데이터인가

구분한다.

| 층 | 판정 |
| --- | --- |
| 공통 소스 | Python 코어, 스킬 본문, launcher, 템플릿은 하나 |
| 공통 산출물 | 루트 `plugin.json` + `skills/` + `scripts/` + `runtime/` 스테이징 |
| 설치 대상 | Codex 캐시/marketplace와 Cursor `--plugin-dir` 또는 marketplace는 별도 |
| 지원 인증 | 호스트×역할(오케스트레이터/worker)별로 따로 기록 |

**사실.** OpenAI 쪽은 루트 `plugin.json`이 portable 입구이고 `.codex-plugin/plugin.json`은 호환 fallback이다. 루트의 `extensions.com.openai`는 호환 overlay 전체와 합쳐지지 않고 교체한다. overlay는 표준 skills 발견을 바꾸지 못한다. Cursor는 MCP 설정에서 `PLUGIN_ROOT`/`PLUGIN_DATA` 대신 `CURSOR_PLUGIN_ROOT`를 쓴다고 주 검토자가 확인했다. 설계는 루트에 OpenAI 확장을 두지 않고 호환 manifest에 표시 정보를 두며, 스킬 이중 로드를 검사하라고 한다 (`PROJECT_STRUCTURE.md` §4).

**설계 권고. 심각도: 차단.** 문서: `PROJECT_STRUCTURE.md` §3–§4, `README.md` U4, `BACKLOG.md` HR-NEXT-001. 이유: U4의 최종 배포물은 Codex 플러그인이다. 그 문장이 Cursor 설치 인증까지 포함하지는 않는다. `.codex-plugin`이 들어 있는 ZIP을 Cursor에 그대로 주면, Cursor가 그 디렉터리를 무시하는지 스킬을 두 번 읽는지가 미검증이다. 빌드는 공통 스테이징을 만든 뒤 호스트 프로파일을 붙인다. Codex 프로파일만 `.codex-plugin/plugin.json`을 갖고, 루트 `extensions.com.openai`가 있으면 빌드가 실패한다. Cursor 프로파일에는 MCP 설정을 넣지 않는다. `.cursor-plugin/plugin.json`은 rules/hooks가 실제로 필요할 때만 추가한다. 런타임 트리는 복사하지 않는다. 이중 로드 게이트를 통과하기 전에는 “하나의 ZIP이 양쪽 설치물”이라고 적지 않는다. 통과 전에는 같은 스테이징에서 Codex용 아카이브와 Cursor용 아카이브를 따로 뽑는다.

**설계 권고. 심각도: 중간.** MCP를 나중에 넣을 때 Cursor 설정은 `CURSOR_PLUGIN_ROOT`만 쓴다. 이 문장을 `PROJECT_STRUCTURE.md` §8에 지금 적어 둔다. MCP 구현 자체는 게이트 C0가 실패한 뒤에만 착수한다.

## 4. 다중 워크스페이스, worktree, 동시 매니저, 버전

**사실.** 요구는 호스트 공통 부모 보드가 없고, 워크스페이스마다 부모 프로젝트·Kanban 하나다 (`README.md` U6, `PROJECT_HIERARCHY.md` §1, `SETUP_AND_CONFIGURATION.md` §8). 잠금 키는 Git common directory다 (`MASTER_SPEC.md` §11). `enter`/`leave`는 실행 대상의 유일한 근거가 아니다 (`MASTER_SPEC.md` §6).

**사실.** `core.project()`는 인자, cwd가 등록 경로에 포함되는 경우, 그다음 전역 `active` 순이다. `projects.init()`은 `kanban_dir`를 필수로 하고 `reg['active']`를 덮어쓴다. `board.init()`은 root 아래 inbox와 children을 만들고 `ensure_view()`가 열 이름·순서·기본 열 삭제를 할 수 있다. `edit_registry()`의 flock은 registry 갱신 동안만 유지된다. `workflow.delegate()`에는 저장소 쓰기 잠금이 없다. worktree는 `HANDRAIL_HOME/projects/<id>/worktrees/<run>`에 생긴다. 실행 기록에 플러그인 빌드 리비전은 없다.

**설계 권고. 심각도: 차단.** 문서: `MASTER_SPEC.md` §6·§11, `SETUP_AND_CONFIGURATION.md` §7–§8, `MIGRATION_PLAN.md` §4.4. 변경:

- 쓰기 대상은 명시적 workspace 또는 현재 Git common directory에 연결된 `project.json` id만 사용한다. 전역 `active`로 다른 저장소에 쓰지 않는다.
- 등록 키는 경로 문자열이 아니라 common directory와 workspace id다. Cursor `--workspace` 경로, symlink, 마운트는 표시용이다.
- worktree 경로는 Handrail 워크스페이스로 등록하지 않는다. worker의 `--workspace`는 worktree이고, 오케스트레이터의 `--workspace`는 사용자 저장소다. 용어를 명령 도움말에 고정한다.
- 잠금은 common directory 기준 durable 레코드다. Codex 오케스트레이터와 Cursor 오케스트레이터, 그리고 이관 중의 구 CLI가 같은 레코드를 본다. PID 부재만으로 지우지 않는다는 기존 문장을 유지한다.
- run은 `runtime_version`에 빌드 리비전과 호스트 id를 남긴다. 다른 플러그인 캐시의 다른 버전은 그 run을 재개하지 않는다. registry schema가 다르면 상대 버전은 쓰지 않고 이관 안내로 끝낸다.

**미검증 가정.** 같은 사용자의 두 CLI가 동시에 XDG를 쓸 수 있다는 것은 파일 잠금 설계로 다룰 수 있다. Cursor sandbox가 `~/.local/share/handrail/locks` 생성을 막는지는 C0의 sandbox 관찰에 포함한다. Vikunja 없이 할 수 있는 게이트 C2: 두 프로세스가 같은 common directory에 쓰기 run을 시작하면 하나만 점유한다.

**설계 권고. 심각도: 중간.** 부모 프로젝트 점유 충돌 진단은 그 호스트 registry 안에서만 가능하다 (`PROJECT_HIERARCHY.md` §5). 다른 사용자·다른 호스트가 같은 Vikunja 프로젝트를 묶는 것까지 막지는 못한다. 진단 문구에 그 범위를 적는다.

## 5. 범위 갭과 모순

**사실.** v0 수용은 Codex 오케스트레이터에서 Codex worker를 먼저 보고, 같은 릴리스에서 Cursor worker를 본다. Cursor 오케스트레이터는 HR-NEXT-001이다 (`README.md` 후속 논의, `BACKLOG.md` §1, `MASTER_SPEC.md` §10). 이 구분은 U7과 맞다. Codex 플러그인 설치만으로 Cursor 오케스트레이터 지원을 표시하지 않는다는 문장도 맞다.

**사실.** 스냅샷에는 `projects.remote()`, Forgejo 안내, 초기 비밀번호 문자열이 남아 있다 (`source/projects.py`). `board.ensure_project()`는 `PUT /projects`이고 v1 스타일이다. 계층 문서의 하위 생성은 공개 데모 OpenAPI의 `POST /api/v2/projects`다 (`PROJECT_HIERARCHY.md` §3, 데모 버전 `v2.6.0-538-g0a5ac04f`). 주 검토자 요약은 하위 생성이 기본 뷰를 만들 수 있다고 더  cautiously 말한다. 데모 명세의 자동 뷰는 그 빌드의 관찰이다.

**설계 권고. 심각도: 차단.** 문서: `IMPLEMENTATION_PROMPT.md` §2, `MIGRATION_PLAN.md` §3, `COMPARISON.md` §3. 플러그인 번들·스킬·launcher가 노출하는 명령에서 원격 Git, Forgejo 설치 안내, `board.up`, 연결 경로의 `ensure_view()` 열 수정을 뺀다. 구 명령이 남아 있으면 이관 안내로 종료한다. 새 버전 설치가 Docker나 원격 설정을 지우지 않는다. Cursor와 Codex가 같이 개발해도 이 코어를 먼저 공유한다.

**설계 권고. 심각도: 높음.** 문서: `SETUP_AND_CONFIGURATION.md` §1, `PROJECT_HIERARCHY.md` §3–§4. 설정 흐름 그림의 주어를 Codex에서 오케스트레이터 CLI로 바꾼다. 토큰 입력 계약은 그대로다. 하위 보드(HR-NEXT-003)는 v0 연결의 읽기 전용, 관리자 권한 불필요와 분리한다. 하위 프로젝트 생성 뒤의 기본 뷰는 대상 인스턴스에서 다시 읽고, manual Kanban과 네 bucket이 아니면 연결하지 않는다. 자동 생성된 뷰를 Handrail 매핑으로 채택하지 않는다. 부모 쓰기와 프로젝트 admin, 토큰 scope는 그 확장 기능에서만 요구한다.

**설계 권고. 심각도: 중간.** `workers.py`의 Gemini 등록은 v0 provider `codex|cursor` 밖에 있다. 번들 스킬과 worker 목록에서 뺀다. Python은 명세의 3.9 최소와, 이 사용자 환경의 3.12.3, README에 적힌 3.9.25를 한 지원표에 둔다. launcher가 부르는 `python3`의 실제 경로와 `-I` 동작은 호스트 인증 항목이다.

**사실.** 카드 식별 `card-NNNN`은 task 숫자만 쓴다 (`source/board.py` `code()`). 명세는 `instance_id + project_id + task_id`다 (`MASTER_SPEC.md` §6). 같은 인스턴스의 숫자 충돌은 이관 시나리오에 있다 (`MIGRATION_PLAN.md` §5). 구현 계약으로는 이미 방향이 맞으므로 차단으로 올리지는 않는다. 허용 목록은 부모와 등록된 area의 project id만이다.

## 6. Cursor 공동 개발 순서와 수용 시험

**설계 권고.** `BACKLOG.md`의 역할 분담은 유지한다. Codex가 공통 서비스와 CLI 계약, Cursor CLI가 호스트 조사와 연동 계층, 사용자 Cursor 세션이 오케스트레이터 수용 시험이다. 순서를 코드 작성보다 게이트 앞으로 당긴다.

1. C0 플러그인 로드·스크립트 경로·캐시 비쓰기. MCP 없음.
2. 이 CLI 버전의 help를 기록한다. `--trust`, `--output-format`, plugin 설치 하위 명령은 있는 것만 적는다.
3. `--print` stdout 한 건으로 session·result·model 필드만 확인한다 (게이트 C1).
4. sandbox를 켠 오케스트레이터와 worker가 XDG, 네트워크, 자격 증명 경로에 대해 서로 다른지 관찰한다.
5. 통과한 뒤에만 Cursor 설치 프로파일(manifest 조각, 스킬 경로 문장)을 스테이징에 추가한다.
6. v0 제품 범위에서는 Codex 오케스트레이터 → Cursor worker 어댑터를 그 help에 맞춰 고친다. 이 경로는 HR-NEXT-001이 아니다.
7. C0가 통과한 뒤에 Cursor 오케스트레이터 수용을 연다. 실패하면 MCP 평가 기록을 쓰고 코어를 복제하지 않는다.
8. 같은 저장소 쓰기 run은 순차다. Cursor worker에게 Vikunja 토큰이나 재위임을 주지 않는다.

수용 시험은 역할을 나눈다. 정적 ZIP 검증, Codex 설치 후 스킬 실행, Cursor C0, 실제 Vikunja, worker 모델 호출은 서로 다른 통과다 (`MIGRATION_PLAN.md` §6에 이미 있는 구분에 Cursor C0를 추가한다).

Cursor 오케스트레이터 수용에 넣을 항목:

- 새 세션에서 스킬이 저장소 밖 플러그인에서 한 번만 보인다.
- A/B 저장소의 부모 binding, 명세, run이 섞이지 않고, 첫 보드가 둘째 프로젝트의 기본값이 되지 않는다.
- 전역 선택을 다른 터미널에서 바꿔도 진행 중 run의 대상이 바뀌지 않는다. 세션을 다시 열면 `status`로 workspace를 다시 고른다.
- 토큰 원문이 채팅, 도구 인자, stdout, worker 환경에 없다. TTY가 아니면 설정이 중단된다.
- Codex worker와 Cursor worker 모두 요청 모델, 선택 출처, 확인된 실제 모델(없으면 null)이 남고, 미지원 모델을 바꾸지 않는다.
- 두 호스트가 같은 repo 쓰기를 동시에 시작하면 하나만 점유한다 (C2).
- 취소·timeout·결과 파일 없음·게시 `unknown` 뒤에 worker를 자동으로 다시 실행하지 않는다.
- 사용자 최종 확인 없이 Done으로 옮기지 않는다.
- 플러그인 버전을 바꾼 뒤 진행 중 run을 다른 빌드로 재개하지 않는다.

## 패키징 결정

공통 소스는 하나다. 공통 스테이징 산출물(루트 `plugin.json`, `skills/`, `scripts/`, `runtime/`)도 하나다. 설치 메타데이터와 지원 인증은 호스트별로 둔다. v0에서 사용자에게 배포한다고 말하는 파일은 Codex 프로파일이다. Cursor 프로파일은 공동 개발 중인 설치 대상이며, C0 전에는 지원 환경표에 올리지 않는다. 코어를 Codex용·Cursor용 Python 패키지 둘로 나누지 않는다. MCP는 C0 실패라는 기록이 생기기 전에는 추가하지 않는다.

## 차단 변경

1. Cursor 오케스트레이션의 MCP 불필요 결론을 C0 통과 전으로 내리지 않는다. `MASTER_SPEC.md` §3, `COMPARISON.md` §4, `MIGRATION_PLAN.md` P0.
2. 공통 스테이징과 호스트별 manifest를 분리하고, 루트 `extensions.com.openai`를 금지한다. Codex ZIP을 Cursor 인증으로 세지 않는다. `PROJECT_STRUCTURE.md` §3–§4.
3. 오케스트레이터 권한과 worker sandbox·환경 allowlist·TTY 비밀 입력을 나눈다. help에 없는 플래그를 하드코드하지 않는다. `MASTER_SPEC.md` §10, `SETUP_AND_CONFIGURATION.md` §4, `source/workers.py`.
4. 확인된 모델만 기록하고, 없으면 null이다. `MASTER_SPEC.md` §10, `source/workers.py`.
5. Git common directory 잠금, workspace id 선택, worktree 비등록, 교차 버전 재개 금지를 계약에 고정한다. `MASTER_SPEC.md` §6·§11, `SETUP_AND_CONFIGURATION.md` §8.
6. 원격 Git·Forgejo 안내·연결 시 보드 생성/열 재배치를 양쪽 호스트 번들에서 제거한다. `MIGRATION_PLAN.md` §3, `source/projects.py`, `source/board.py`.

## 비차단 변경

- `PROJECT_STRUCTURE.md` §8에 향후 Cursor MCP는 `CURSOR_PLUGIN_ROOT`만 사용한다고 적는다.
- 하위 보드 자동 뷰는 대상 인스턴스 재조회로 두고 HR-NEXT-003에 남긴다.
- Handrail workspace와 Cursor `--workspace` 용어를 도움말에 구분한다.
- Gemini 등록을 v0 표면에서 뺀다.
- 단일 ZIP 통합은 이중 로드를 본 뒤에 결정한다.
- 지원표에 호스트별 `python3` 경로와 버전을 남긴다.
- 부모 보드 충돌 진단의 범위가 로컬 registry임을 문구에 남긴다.
