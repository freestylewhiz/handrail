# Handrail 상세 아키텍처

> 기준: `1.0.0a6`, 2026-10-08. [아키텍처 요약](architecture.md)을 보완한다. 다이어그램은 코드의 호출·저장·외부 실행 경계를 설명하며, 실서비스 검증 완료를 의미하지 않는다. 새 계약과 제한은 [alpha.6 구현 기록](alpha6-implementation.md)을 함께 읽는다.

> alpha.5 변경: `summary/`가 카드 원본·버전·선택 조회를, `agentroom/cleanup.py`가 완료 후 close/keep 선택을 소유한다. 정식 수락은 보드와 Summary를 동기화한다. 상세 사용법은 [Summary](summaries.md)를 따른다.

> alpha.4 변경: `board/`가 하위 보드 구성·카드 강제 전환·동기화 보류와 재개를 담당한다. 외부 생성 의도는 `board/provisioning.py`로 이동했다. Work 카드의 보드는 명시적 배치 또는 기존 연결을 사용하며 sync에서 하위 보드를 생성하지 않는다. 아래 개발 워크플로우와 별도로 [보드·카드 관리](boards.md)를 제공한다.

## 읽는 순서

1. [시스템 경계와 컴포넌트](#1-시스템-경계와-컴포넌트)
2. [데이터와 상태의 관계](#2-데이터와-상태의-관계)
3. [설정·경로·권한](#3-설정경로권한)
4. [워크플로우 시퀀스](#4-워크플로우-시퀀스)
5. [실패·복구·동시성](#5-실패복구동시성)
6. [코드 탐색과 확장 경계](#6-코드-탐색과-확장-경계)

## 1. 시스템 경계와 컴포넌트

### 1.1 배치와 외부 제품의 관계

Handrail은 명령 실행 시 동작하는 로컬 Python CLI다. 현재 구현에는 상시 실행하는 Handrail 서버나 자체 웹 UI가 없다. 조율자는 CLI를 호출하는 에이전트 또는 사람이며, 작업자는 Herdr가 관리하는 Codex/Cursor 프로세스다.

```mermaid
flowchart TB
    U["사용자<br/>목표·실행 범위·결과 수락"] --> C["조율자<br/>계획·지시·검수·진척 보고"]
    C --> HR["Handrail CLI<br/>로컬 프로세스"]
    HR --> DB[("비공개 설정·SQLite·명령 로그")]
    HR -->|"명시한 session 또는 socket"| H["외부 제품: Herdr"]
    HR -->|"HTTP API"| V["외부 제품: Vikunja<br/>기존 프로젝트·Kanban view"]
    HR -->|"Git 명령"| G["Canonical checkout<br/>검수 결과 통합·최종 검증"]
    H --> W1["Codex 작업자"]
    H --> W2["Cursor 작업자"]
    W1 --> T1["독립 worktree A"]
    W2 --> T2["독립 worktree B"]
    T1 -.->|"공유 Git 메타데이터"| GD[("Git common directory")]
    T2 -.-> GD
    G -.-> GD
    V -.->|"진행 표시"| U
    C -->|"검수 결과와 미확인 사항 보고"| U
```

- **Handrail**은 업무 상태, 실행 대상, 승인 기록, 증거와 후처리 의도를 관리한다.
- **Herdr**는 workspace/pane/terminal과 작업자 프로세스에 대한 실행·통신 인터페이스를 제공한다.
- **Vikunja**는 Handrail 이벤트를 카드·관계·버킷·댓글로 표시한다. 보드에서 카드를 옮겼다는 사실만으로 Handrail의 검수나 완료가 성립하지 않는다.
- **Git**은 작업 격리와 통합 revision의 근거다. 작업 디렉터리가 분리되어도 common directory에 대한 쓰기 경계는 공유된다.

### 1.2 논리 컴포넌트와 호출 관계

실선은 호출 또는 저장 접근, 점선은 저장된 이벤트를 통한 후속 처리다. 화살표는 모든 import를 나열한 것이 아니라 주요 실행 의존성을 나타낸다.

```mermaid
flowchart TB
    CLI["cli.py<br/>인자·입력 파일·JSON 출력"]
    APP["application.py<br/>조립·Git 확인·도메인 전이 연결"]
    SET["setup/<br/>연결·바인딩·진단"]
    WF["workflow/<br/>Plan·Work·기준·증거·수락"]
    ROOM["agentroom/service.py<br/>Room·Attempt·통신·복구·통합"]
    CMD["agentroom/commands.py<br/>승인된 준비·검증 명령"]
    AUTH["authorization/<br/>plan/cycle·action·resource 대조"]
    HD["hooks/dispatcher.py<br/>Outbox 순차 전달"]
    BP["hooks/board.py<br/>카드 투영·마커·재조정"]
    HI["interfaces/agentroom/<br/>Herdr CLI 어댑터"]
    VI["interfaces/vikunja/<br/>HTTP client·보드 어댑터"]
    GI["interfaces/git/<br/>worktree·revision·merge"]
    ST[("shared/store.py<br/>documents·events·outbox·locks")]

    CLI --> APP
    CLI --> SET
    CLI --> CMD
    CLI --> AUTH
    APP --> WF
    APP --> ROOM
    APP --> GI
    APP --> HD
    APP --> SET
    ROOM --> WF
    ROOM --> AUTH
    ROOM --> HI
    ROOM --> GI
    CMD --> AUTH
    CMD --> GI
    SET --> VI
    SET --> GI
    HD --> BP
    HD --> CLEAN["agentroom/cleanup.py<br/>close 또는 keep 선택"]
    CLEAN --> ROOM
    APP --> SUMMARY["summary/<br/>카드 원본과 선택 조회"]
    HD --> SUMMARY
    SUMMARY --> VI
    SUMMARY --> ST
    BP --> VI
    WF --> ST
    ROOM --> ST
    CMD --> ST
    AUTH --> ST
    HD --> ST
    BP --> ST
    ST -.->|"board 이벤트"| HD
```

| 컴포넌트 | 책임·소유 정보 | 주요 협력 대상 | 경계 |
| --- | --- | --- | --- |
| CLI | 명령 파싱, JSON·지시 파일 입력, 결과·오류 출력 | Application, Setup, Authorization, Commands | 완료 판단이나 외부 프로토콜 세부 구현을 추가하지 않는다 |
| Application | 서비스 조립, 실제 Git 상태를 확인한 review/evidence/complete/verify/accept | Workflow, Agentroom, Git, Hooks | 코드 상태와 도메인 증거를 연결하는 경계 |
| Setup | 토큰, 연결 프로필, 저장소·보드·endpoint·worktree 설정, 진단 | Git, Vikunja, 로컬 설정 저장 | 기존 외부 서비스에 연결하며 프로젝트 서버를 생성하지 않는다 |
| Workflow | Plan/Work, cycle, 기준별 증거, 승인·검수·검증·제출·수락 | Store | Herdr/Vikunja/subprocess에 의존하지 않는다 |
| Summary | 본문 렌더링·영역 선택·버전·remote 원본, 로컬 hash-only intent와 참조 | Vikunja, Store | 별도 로컬 Summary 원본을 만들지 않는다 |
| Cleanup | 사용자의 room 선택과 고정 범위, 정리 재개 | Summary, Agentroom, Authorization | 기획 수락과 정리 선택을 분리한다 |
| Agentroom | Room, Attempt, 실행 신원, 관찰, 통신 intent, 복구·통합·정리 | Workflow, Authorization, Herdr, Git, Store | 작업자 활동과 업무 완료를 별도로 유지한다 |
| Commands | 정확한 argv/cwd/purpose의 명령 실행, 로그와 종료 결과 | Authorization, Git, Store | 명령 실행 완료 자체가 카드 완료는 아니다 |
| Authorization | 사용자 승인 참조, plan/cycle·행동·자원 범위, 만료·철회 | Store | OS나 에이전트 sandbox 권한을 변경하지 않는다 |
| Hooks | 후처리 순서, 보드 투영 intent, 실패·미확정 전달 기록 | Store, Vikunja, Agentroom | 등록한 Python handler만 실행한다 |
| Interfaces | 각 외부 제품의 호출, 응답 정규화, 오류 분류 | Herdr CLI, Vikunja HTTP, Git 프로세스 | Plan/Work 상태를 직접 결정하지 않는다 |
| Shared | JSON 문서 저장, 추가 전용 이력, Outbox, 잠금, 오류·ID | SQLite, 파일시스템 | 도메인별 승인·완료 규칙을 소유하지 않는다 |

현재 구조는 도메인과 외부 프로토콜을 폴더·서비스로 분리한 형태다. 모든 의존성이 추상 포트를 통해 주입되는 구조는 아니다. Application과 일부 실행 경계에서 구체 어댑터를 생성한다.

## 2. 데이터와 상태의 관계

### 2.1 논리 데이터 모델

아래 관계는 논리 모델이다. 실제 SQLite 테이블은 `documents`, `events`, `outbox`, `meta`이며, Plan·Work 등을 각각 SQL 테이블로 구현하지 않았다. `documents`는 `(kind, id)` 키로 JSON을 저장한다.

```mermaid
flowchart LR
    P["Plan<br/>현재 cycle·기준·work_ids"] -->|"현재·과거 회차"| CY["Cycle<br/>승인·제출·수락 스냅샷"]
    P -->|"1:N"| W["Work<br/>plan_id·cycle·attempt_id"]
    CY -->|"plan_id:cycle"| SC["Cycle scope<br/>repo·endpoint·worktree_root"]
    SC --> R["Room<br/>workspace·owned_panes"]
    R -->|"여러 실행 시도"| AT["Attempt<br/>worktree·branch·provider·model"]
    W -->|"현재 실행 + 과거 교체 이력"| AT
    AT --> ID["실행 신원<br/>pane·terminal·provider session"]
    AT --> OB["Observation<br/>관찰 시각·응답·화면 근거"]
    AT --> OP["Operation<br/>요청 hash·결과·불확실성"]
    CY --> GR["Grant<br/>actions·resources·승인 참조"]
    W --> EV["기준별 Evidence<br/>cycle·attempt·revision"]
    W --> RV["Review와 Integration<br/>후보 commit·통합 commit"]
    P --> PV["계획 Verification<br/>최종 revision·완료 Work 근거"]
    PV --> SU["Submission"]
    SU --> AC["Acceptance"]
    P -.-> J["Journal event<br/>당시 문서 스냅샷"]
    W -.-> J
    J -.-> O["Outbox<br/>고정 key·topic·payload"]
    O -.-> BC["Board mapping / intent<br/>entity_id → task_id"]
```

`Cycle`의 과거 도메인 상태는 Plan 문서의 `cycles` 배열에 보존한다. 자원 고정 정보는 별도의 `cycle_scope` 문서다. Review·Evidence·Integration은 Work/Plan 내부 데이터이며, 다이어그램의 모든 상자가 독립 document kind인 것은 아니다.

### 2.2 서로 다른 상태 축

| 상태 축 | 상태 또는 근거 | 변화의 의미 |
| --- | --- | --- |
| Plan 업무 | `todo → doing → review → done` | 실행 시작, 검증된 제출, 사용자 수락 |
| Work 업무 | `todo → doing → review → done` | Review는 조율자 검토 대기; revise/reject는 doing |
| Attempt 생명주기 | `preparing`, `active`, `replaced`, `closed` | 실행 준비·연결·교체·종료 |
| 작업자 활동 | Herdr가 보고한 `working`, `blocked`, `idle`, `done` 등 | 관찰 당시 프로세스 활동; 관찰하지 않은 최신 상태는 알 수 없다 |
| Room | `open`, `closed` | 보존 중인 작업 공간의 생명주기 |
| 외부 operation | `prepared`, `sending`, `complete`, `unknown`, `rejected` | 개별 요청의 적용 여부 |
| Outbox 전달 | `pending`, `sending`, `complete`, `failed`, `unknown` | 이벤트 후처리의 진행 상태 |

```mermaid
stateDiagram-v2
    state "Plan" as Plan {
        [*] --> PTodo
        PTodo: Todo
        PDoing: Doing
        PReview: Review
        PDone: Done
        PTodo --> PTodo: approve 현재 회차
        PTodo --> PDoing: 첫 Work start
        PDoing --> PReview: verify 후 submit-review
        PReview --> PDone: 사용자 accept
        PReview --> PDoing: reopen / cycle 증가
        PDone --> PDoing: reopen / cycle 증가
    }
    state "Work" as Work {
        [*] --> WTodo
        WTodo: Todo
        WDoing: Doing
        WReview: Coordinator Review
        WDone: Done
        WTodo --> WDoing: start / attempt 연결
        WDoing --> WReview: 현재 실행의 구조화 제출 수신
        WReview --> WDoing: revise 또는 reject
        WReview --> WReview: 검수·통합·기준별 증거
        WReview --> WDone: complete 관문 통과
    }
```

Reopen은 이전 결과를 보존하고 새 회차를 `doing`으로 연다. 새 회차의 approval·verification·submission·acceptance는 비워지므로 실행 전 다시 그 회차의 승인을 기록해야 한다. 이전 회차 Work는 수정하지 않고 새 Work를 생성한다.

### 2.3 완료 근거의 연결

```mermaid
flowchart LR
    S["작업자 clean commit S"] --> R["Review accept<br/>revision S 고정"]
    R --> M["Git integration<br/>후보가 여전히 S인지 확인"]
    M --> I["Canonical commit I"]
    I --> E["Work의 모든 기준<br/>I에 대한 passing evidence"]
    E --> W["Work Done<br/>완료 revision I 보존"]
    W --> F["최종 canonical commit F<br/>모든 완료 I를 포함"]
    F --> P["Plan 기준의 evidence at F"]
    P --> V["Plan verification"]
    V --> S2["Review submission at F"]
    S2 --> A["사용자 acceptance<br/>submission ID와 F 연결"]
```

작업자 커밋 검수, 통합 후 Work 증거, 최종 Plan 증거를 각각 기록한다. Work를 통합한 뒤 그 revision의 증거와 완료를 기록해야 다음 Work를 통합할 수 있다. 이 순서로 후속 merge가 직전 작업의 검증 대상을 바꾸는 것을 막는다.

## 3. 설정·경로·권한

### 3.1 설정과 실행 범위 고정

```mermaid
sequenceDiagram
    actor C as 조율자와 사용자
    participant S as Setup
    participant G as Git adapter
    participant V as Vikunja adapter
    participant F as 비공개 설정
    participant R as Agentroom
    participant D as Store
    C->>S: setup 연결 프로필과 URL
    Note over C,S: 토큰은 사용자 터미널에서 숨김 입력
    S->>V: 사용자 인증 정보 확인
    V-->>S: 인증 결과
    S->>F: 연결 정보 저장
    C->>S: bind 저장소, project/view, 버킷, endpoint, worktree root
    S->>G: canonical checkout과 common directory 확인
    S->>V: 기존 manual Kanban view와 상태 매핑 조회
    S->>F: 프로젝트 바인딩 저장
    C->>S: doctor / preflight
    S-->>C: 실제 경로·IPC·네트워크·기존 cycle 범위
    Note over S,C: os.access는 힌트이며 host 권한의 증명이 아님
    C->>R: 실행 범위가 필요한 최초 동작
    R->>D: cycle_scope에 repo/endpoint/worktree_root 고정
    Note over R,D: 이후 설정 변경이 기존 실행의 대상을 바꾸지 않음
```

| 저장 위치 | 내용 | 설정 원칙 |
| --- | --- | --- |
| `$XDG_DATA_HOME/handrail/v1` 또는 `~/.local/share/handrail/v1` | 연결·프로젝트 설정, SQLite, 로그 | `HANDRAIL_HOME`으로 변경 가능; 비공개 관리 데이터 |
| 명시한 외부 영속 worktree root | 작업자 소스·브랜치별 작업 디렉터리·의존성 | 대상 프로젝트의 실제 쓰기 허용 범위와 함께 선택 |
| 기본 XDG 기반 `handrail/worktrees/<workspace-id>` | root 미지정 시 작업자 소스 | 홈 아래라는 이유만으로 sandbox 쓰기를 가정하지 않는다 |
| Canonical checkout와 Git common directory | 통합 코드·Git 객체·worktree 메타데이터 | 두 경로를 모두 진단한다 |

저장소 내부 worktree는 명시적 예외 옵션으로 허용한다. `/tmp`는 영속 작업자 저장소로 사용하지 않는다. Room 종료와 worktree 삭제는 별도 수명주기다.

### 3.2 승인 재사용과 실제 접근 권한

```mermaid
flowchart TB
    REQ["실행 요청<br/>plan·cycle·action·resources"] --> LOOK["유효 Grant 조회<br/>만료·철회·회차 확인"]
    LOOK --> MATCH{"요청 범위가 일치하는가?"}
    MATCH -->|"예"| USE["기존 grant_id 재사용"]
    MATCH -->|"아니요"| MISS["preview.missing 표시<br/>승인된 사용자 의도 확인·기록"]
    MISS --> LOOK
    USE --> HOST["실제 파일·Git·소켓·네트워크 접근"]
    HOST --> OK{"Host 정책이 허용하는가?"}
    OK -->|"예"| RUN["실행 및 결과 기록"]
    OK -->|"아니요"| ERR["실패 주체·자원·경계 보고"]
    ENV["HERDR_ENV<br/>실행 문맥 힌트"] -.-> DIAG["진단 inside/external 표시"]
    EP["명시 endpoint와 실행 신원"] --> HOST
```

권한 관련 기록은 세 가지다.

1. **Plan approval**: 그 회차의 목표·기준에 대한 구현 승인이다.
2. **Grant**: `room.create`, `worker.start`, `worker.prompt`, `worker.keys`, `worker.recover`, `work.integrate`, `command.run`, `room.close`, `worktree.remove`의 자원 범위다.
3. **Host 권한**: 파일시스템·소켓·네트워크·에이전트 sandbox가 실제로 허용하는 접근이다.

같은 요청 범위에는 기존 grant를 재사용한다. `preview.missing`은 후보 grant에서 일치하지 않는 필드를 보여준다. 현재 구현은 여러 grant를 합성하지 않으며, 요청 자원 필드가 일치하는 하나의 유효 grant를 찾는다. 추가 grant를 기록할 때도 완전한 요청 범위를 구성해야 한다.

`HERDR_ENV=1`을 Handrail이 수동 주입하지 않는다. 상속된 값은 유지하지만 endpoint 선택이나 권한 증명으로 사용하지 않는다. 내부 pane 조율자와 외부 조율자 모두 명시한 연결과 실행 신원을 사용한다.

보드 동기화는 위 action grant 목록에 포함되지 않는다. 현재 구현은 저장된 Vikunja 연결 권한과 명시적인 `sync` 호출로 보드 쓰기를 수행한다. 토큰 권한과 Handrail의 실행 grant를 동일하게 해석하면 안 된다.

## 4. 워크플로우 시퀀스

아래 그림은 명령 하나마다 새 CLI 프로세스가 실행될 수 있는 논리 시퀀스다. `Store`는 각 프로세스가 공유하는 영속 저장소이며, 그림의 참여자가 계속 살아 있는 서비스라는 의미는 아니다.

### 4.1 계획 생성에서 작업자 최초 지시까지

```mermaid
sequenceDiagram
    actor C as 조율자
    participant W as Workflow
    participant R as Agentroom
    participant A as Authorization
    participant D as Store
    participant G as Git adapter
    participant H as Herdr adapter와 서비스
    C->>W: plan create / work create / plan approve
    W->>D: 각 전이의 문서 + journal + board outbox 저장
    C->>A: 기존 사용자 승인에 근거한 grant 기록
    A->>D: plan/cycle별 actions와 resources
    C->>R: worker start(work, provider, model, effort, instructions, operation ID)
    R->>D: cycle scope 확인 또는 최초 고정
    R->>A: worker.start 범위 확인
    opt 이번 cycle의 Room이 아직 없음
        R->>A: room.create 범위 확인
        R->>D: room 생성 intent와 sending 저장
        R->>H: 명시 endpoint에 workspace 생성
        H-->>R: workspace와 초기 pane 신원
        R->>H: 실제 pane/terminal 신원 대조
        R->>D: 생성 결과와 Room 소유 기록
    end
    R->>D: Attempt preparing 예약
    R->>G: 고정 경로·branch·base revision으로 worktree 생성
    R->>H: Room 안에 worktree를 cwd로 tab 생성
    R->>H: 명시 provider/model/effort로 작업자 시작
    R->>H: 실제 agent와 worktree 신원 조회
    R->>D: Attempt active 및 소유 신원 저장
    R->>W: start_work(work, attempt)
    W->>D: Work Doing, 필요 시 Plan Doing, 이력·Outbox
    R->>H: readiness 최초 지시 전송
    R->>D: 메시지 전달 결과 기록
    R-->>C: Attempt와 메시지 receipt
```

최초 readiness와 준비 완료 뒤의 구현 지시는 `worker.start` 범위에 포함된다. `worker continue`는 작업자 진단 보고를 확인한 뒤 구현을 전달한다. 일반 후속 지시는 `worker.prompt` 범위를 확인한다. Doing은 실행 기록이며 readiness가 실패한 작업을 실제 구현 중이라고 보고하지 않는다. 동일 ID는 기존 Attempt와 원래 요청을 재사용한다. 모델·카드 준비와 완료 인계는 아래 alpha.6 통합 시퀀스를 따른다.

### 4.2 관찰·후속 지시·작업자 교체

```mermaid
sequenceDiagram
    actor C as 조율자
    participant APP as Application
    participant R as Agentroom
    participant A as Authorization
    participant D as Store
    participant H as Herdr
    C->>APP: status / history
    APP->>D: 저장된 상태와 이력 읽기
    APP-->>C: 누구의 어떤 작업을 기다리는지, 관찰 시각, 다음 행동
    C->>R: worker observe(attempt)
    R->>H: 고정 대상의 신원·활동·응답 조회
    R-->>C: 실시간 관찰 결과
    Note over R,D: observe는 증명된 신원 보강을 저장할 수 있음
    C->>R: worker collect(attempt, recent)
    R->>H: 신원 확인과 응답 수집
    R->>D: Observation과 활동 상태 저장
    Note over R,D: collect는 구조화 제출 수신과 Work Review를 연결하며 Done은 만들지 않음
    alt 동일 실행에 추가 지시
        C->>R: worker prompt(attempt, message ID, instructions)
        R->>A: worker.prompt 범위 확인
        R->>H: 전송 전 신원 대조
        R->>D: 요청 intent와 sending 저장
        R->>H: 명시한 작업자에게 지시
        R->>H: 전송 후 신원 대조
        R->>D: 결과 또는 불확실성 기록
    else 실행 소실 또는 교체
        C->>R: worker recover(attempt, target, evidence)
        R->>A: worker.recover 범위 확인
        R->>H: 명시 대상의 Room·provider·worktree 대조
        R->>D: 새 Attempt와 기존 replaced 이력
        R-->>C: 새 실행 연결 결과
    end
```

`worker keys`는 이 시퀀스의 일반 지시 전송과 별도다. 저장된 observation·화면 hash·정확한 키 목록·행동 이유를 대조한다. Enter 입력이 추가 권한 승인인지, 단순 지시 전송인지 조율자가 판단해야 한다.

### 4.3 검수·통합·Work 완료

```mermaid
sequenceDiagram
    actor C as 조율자
    participant APP as Application
    participant R as Agentroom
    participant CMD as Commands
    participant A as Authorization
    participant G as Git adapter
    participant W as Workflow
    participant D as Store
    Note over C,G: 작업자가 커밋하고 조율자가 실제 diff와 결과를 검수
    C->>APP: work review(accept, notes)
    APP->>R: 현재 유효 Attempt 확인
    APP->>G: worker worktree clean 확인과 commit S 읽기
    APP->>W: review_work(revision S)
    W->>D: 검수 판단·후보 revision 저장
    C->>R: worker integrate(attempt)
    R->>A: work.integrate 범위 확인
    R->>G: canonical/worker clean, 검수한 S와 현재 후보 대조
    R->>D: 통합 intent와 기준 HEAD 저장
    R->>G: merge --no-ff --no-edit
    alt 통합 성공
        G-->>R: canonical revision I
        R->>W: mark_integrated(source S, revision I)
        W->>D: 통합 근거·이력·Outbox
    else 충돌 또는 결과 불명확
        R->>D: rejected 또는 unknown 기록
        R-->>C: 실제 Git 상태와 복구 필요 사항
        Note over R,G: 자동 reset이나 무조건 재시도 없음
    end
    opt 사용자가 요청한 검증 명령 실행
        C->>CMD: command(purpose verify, exact argv/cwd)
        CMD->>A: command.run 범위 확인
        CMD->>G: 실행 전 clean canonical과 revision 확인
        CMD->>CMD: 승인된 argv를 cwd에서 실행
        CMD->>G: 실행 후 revision과 clean 상태 확인
        CMD->>D: 명령 결과·로그 경로 저장
    end
    loop Work의 모든 완료 기준
        C->>APP: evidence(work, criterion, observation, optional command ID)
        APP->>G: 현재 clean canonical revision I 확인
        APP->>W: record_evidence(revision I)
        W->>D: 기준·cycle·attempt·revision에 묶인 증거
    end
    C->>APP: work complete
    APP->>G: clean canonical HEAD 확인
    APP->>W: complete_work(revision I)
    W->>D: 검수·통합·증거 확인 후 Work Done
```

Commands의 실제 함수는 `agentroom/commands.py`의 `run_command`다. 증거에 command ID를 연결하면 같은 plan/cycle·자원 범위의 성공한 canonical 검증인지, 실행 전후 revision과 clean 상태가 일치하는지 확인한다. 텍스트 증거는 조율자가 기록한 관찰 진술이며 자동 검증 실행을 뜻하지 않는다.

### 4.4 계획 검증·사용자 수락·Summary·자원 정리

```mermaid
sequenceDiagram
    actor U as 사용자
    actor C as 조율자
    participant APP as Application
    participant G as Git adapter
    participant W as Workflow
    participant S as SummaryService
    participant D as Store
    participant V as Vikunja
    participant R as Cleanup and Agentroom
    participant H as Herdr
    C->>APP: plan verify 후 submit-review
    APP->>G: 통합 revision과 clean 상태 확인
    APP->>W: 기준별 evidence로 Review 제출
    W->>D: Submission과 board outbox 저장
    C->>S: summary prepare
    S-->>C: 근거와 언어별 템플릿, expected hash
    C->>S: 모델이 작성한 영어·사용자 언어·Agent Context
    S->>D: 본문 대신 전송 해시·상태 기록
    S->>V: 부모 보드에 Summary 초안 생성 또는 갱신
    C-->>U: 구현 결과와 Summary 리뷰
    U->>C: 최종 승인
    C->>APP: plan complete와 원래 사용자 승인
    APP->>G: 제출 revision 대조
    APP->>W: accept_plan
    W->>D: 단일 transaction에 수락·Done·board 및 summary outbox
    APP->>V: board 동기화
    APP->>S: summary hook
    S->>V: 이전 버전 댓글 보존 후 Summary 확정
    APP-->>C: 완료·후처리 결과와 cleanup scope token
    C-->>U: 해당 room 종료 또는 보존 선택
    alt close 선택
        C->>R: plan cleanup close와 scope token
        R->>D: 실제 선택 기록과 종료 grant 재사용
        R->>V: 수락된 Summary 보존 확인
        R->>H: 명시 endpoint와 owned pane·신원·활동 확인
        R->>H: 안전한 room 종료와 부재 확인
        R->>D: 결과 기록, worktree 유지
    else keep 또는 답변 대기
        Note over R,H: room과 worktree 유지, Plan Done 유지
    end
```

`plan complete`와 `plan accept`는 같은 동작이다. 현재 근거로 작성된 Summary가 없으면 조율자에게 작성 정보를 반환한다. 조율자는 사용자에게 JSON을 요구하거나 수락을 다시 묻지 않고, `summary prepare/publish` 또는 `--summary-file`로 마친 뒤 기존 승인으로 재개한다. CLI 내부에서 별도 모델을 호출하지 않는다.

수락 transaction에 board·summary 후처리가 함께 기록된다. 보드·요약 쓰기가 실패해도 수락은 보존되며 개별 topic sync로 재시도한다. 정리는 cleanup 선택 이후에만 enqueue한다. 이전 버전에서 남은 cleanup outbox도 선택 없이 실행되지 않는다. 이미 종료된 room은 같은 endpoint의 명시적 not-found 근거로만 정리 기록을 조정한다. 다른 room·worktree 삭제로 범위를 넓히지 않는다.

### 4.4.1 후속 기획의 이력 참조

```mermaid
sequenceDiagram
    actor C as 조율자
    participant APP as Application
    participant S as SummaryService
    participant V as Vikunja
    participant D as Store
    participant R as Agentroom
    participant A as 작업자
    C->>APP: plan create
    APP->>S: 제목·scope 기준 후보 조회
    S->>V: 부모 보드 Summary 읽기
    S-->>C: 후보 ID·버전·scope
    C->>S: read CARD
    S-->>C: Agent Context만 반환
    C->>S: read CARD language en section rules
    S-->>C: 선택한 설명과 한계
    C->>S: use PLAN 또는 WORK, 적용 이유
    S->>D: ID·버전·해시·선택 항목 기록
    C->>APP: worker start
    APP->>S: 기록된 참조의 현재 버전 확인
    S->>V: 필요한 영역 조회
    alt 참조가 현재 유효함
        APP->>R: 원래 지시와 선택된 참조 내용
        R->>A: 권한을 확장하지 않는 근거 전달
    else 변경 또는 stale
        APP-->>C: 재조회·참조 갱신 요청, 작업자 시작 보류
    end
```

### 4.5 카드·이력의 외부 보드 반영

```mermaid
sequenceDiagram
    actor C as 조율자
    participant W as Workflow
    participant D as Store
    participant HD as HookDispatcher
    participant BP as BoardProjection
    participant V as Vikunja adapter와 기존 서버
    C->>W: 도메인 변경 명령
    W->>D: 한 transaction에서 document + event + board outbox
    W-->>C: 로컬 변경 완료
    Note over W,V: 이 시점에는 보드 HTTP 쓰기를 하지 않음
    C->>HD: sync --topic board
    HD->>D: 순서대로 미완료 이벤트 조회, delivery sending
    HD->>BP: frozen event payload 전달
    BP->>D: entity/task mapping과 기존 세부 intent 조회
    BP->>V: 마커·카드·관계·댓글의 적용 여부 조회
    opt 신규이며 전송 가능한 세부 동작
        BP->>D: 카드 생성 / 관계 / 이동 / 댓글별 intent 저장
        BP->>V: 필요한 변경만 실행
        V-->>BP: 적용 결과
        BP->>D: mapping과 세부 결과 저장
    end
    alt 적용 결과 확인됨
        BP-->>HD: task ID와 event ID
        HD->>D: delivery complete
    else 실패 또는 적용 여부 미확정
        BP-->>HD: 구조화 오류
        HD->>D: delivery failed 또는 unknown
        Note over HD,D: 현재 dispatch 중단, 다음 이벤트의 추월 방지
    end
```

Plan 카드는 부모 보드에 투영된다. Work 카드는 명시적 지정, 보존된 기존 연결, 부모 보드 순으로 결정하며 기존 카드 위치를 유지한다. 하위 보드는 `board add`로 생성한다. 과거 이벤트는 당시 문서 스냅샷을 사용하고 관찰마다 댓글을 쓰지 않는다. 보드 읽기는 중복·충돌 확인에 사용한다. 사용자 지정 카드 상태는 `card_override`로 별도 기록하며, 도메인 검증·통합·수락 상태를 변경하지 않는다. 활성 보류가 있는 카드는 자동 상태 투영을 억제한다.

## 5. 실패·복구·동시성

### 5.1 외부 호출의 트랜잭션 경계

```mermaid
sequenceDiagram
    participant S as 실행 서비스
    participant D as SQLite
    participant E as 외부 시스템
    S->>D: transaction A - 고정 operation ID와 request hash 확인
    S->>D: intent prepared → sending, commit
    S->>E: 외부 요청 - DB transaction 밖
    alt 응답으로 결과 확정
        E-->>S: 성공 결과
        S->>D: transaction B - complete와 결과 저장
    else 명확한 거절
        E-->>S: 적용되지 않은 것으로 분류 가능한 오류
        S->>D: transaction B - rejected
    else timeout·응답 유실·프로세스 중단
        Note over E,D: 외부 적용 여부와 로컬 기록이 다를 수 있음
        S->>D: 가능한 경우 unknown 저장
        Note over S,D: 프로세스가 종료되면 sending이 남을 수 있음
    end
```

SQLite와 Herdr/Vikunja/Git을 하나의 원자적 transaction으로 묶지 않는다. 재시작 시 `sending`을 미실행으로 가정하지 않고, 관찰·마커·Git revision 등 실제 근거로 조정한다. 로컬 ID와 외부 마커는 중복을 줄이지만 외부 시스템 전체의 정확히 한 번 실행을 보장하지 않는다.

### 5.2 실패별 복구 책임

| 상황 | 유지하는 사실 | 복구 경로 |
| --- | --- | --- |
| 지시 timeout/stall | 전달됐을 가능성, 원래 operation ID | 응답 관찰 후 `worker resolve-message`로 delivered/not_delivered와 근거 기록 |
| Room 생성 응답 유실 | 원래 생성 의도·label·cycle scope | `room adopt`에서 origin operation·workspace·소유 pane을 명시하고 대조 |
| 작업자 교체 | 이전 Attempt와 관찰·검수 이력 | 명시 target에 `worker recover`; 새 Attempt, 이전 것은 replaced |
| Git 충돌·통합 응답 유실 | 검수한 후보와 이전 HEAD, 현재 Git 상태 | 실제 충돌 해결·ancestry 확인 후 integrate 재조정; 자동 reset 없음 |
| 보드 쓰기 미확정 | 이벤트와 카드/관계/이동/댓글 intent | 먼저 외부 조회; 미적용 근거로 `sync --resolve` 기록 후 별도 sync |
| 명령 실행 중단 | argv/cwd·operation·로그·가능한 부수효과 | 실제 프로세스 확인 후 `resolve-command`; 성공 검증으로 바꾸지 않음 |
| 정리 실패 | 사용자 Acceptance와 Plan Done | 소유·활동·승인 확인 후 cleanup 재시도; worktree는 별도 보존 |
| 파일·소켓 권한 실패 | 오류의 주체·자원·host 경계 | 실제 실행 환경의 허용 경로/IPC 확인; HERDR_ENV나 앱 grant로 우회하지 않음 |

`sync --resolve` 자체는 외부 쓰기를 하지 않는다. 재조정 근거를 로컬에 기록하며, 다음 dispatch에서 허용된 재시도가 일어난다. 실패 종류마다 복구 방식이 다르므로 `unknown`을 공통 재시도 버튼처럼 처리하지 않는다.

### 5.3 잠금과 남는 경합

- **`agentroom-mutation`**: worker 실행·통신·복구·통합·정리와 review/evidence/complete/verify/submit/accept의 주요 변경을 직렬화한다.
- **`outbox-delivery`**: 후처리 전달을 직렬화한다. cleanup handler가 Agentroom에 진입하므로 잠금 순서는 `outbox-delivery → agentroom-mutation`이다.
- **SQLite `BEGIN IMMEDIATE`**: 짧은 로컬 변경 transaction 안에서 문서·이력·Outbox를 함께 쓴다. 외부 I/O 동안 DB transaction을 유지하지 않는다.
- 잠금이 이미 다른 조율자에게 있으면 `OPERATION_BUSY`를 반환한다. 백그라운드 작업 큐에서 무한 대기하는 구조가 아니다.

Herdr에는 현재 원자적인 compare-and-send/close가 없다. Handrail의 전후 신원 확인 사이에 다른 주체가 pane을 교체할 수 있는 경합이 남는다. Handrail의 로컬 잠금은 다른 도구가 직접 수행하는 Herdr/Git 조작까지 막지 못한다. protocol generation도 서버 실행 인스턴스의 고유 ID로 사용하지 않는다.

Room 종료에서는 알려진 pane의 소유 신원과 실제 pane 수·소속을 대조한다. 알 수 없는 pane이나 진행 중인 프로세스가 있으면 자원을 보존한다. 작업자가 없는 shell pane도 foreground가 shell임을 확인해야 한다.

## 6. 코드 탐색과 확장 경계

| 확인할 설계 | 구현 진입점 |
| --- | --- |
| CLI와 서비스 조립 | [cli.py](../handrail/cli.py), [application.py](../handrail/application.py) |
| 연결·바인딩·진단 | [settings.py](../handrail/setup/settings.py), [diagnostics.py](../handrail/setup/diagnostics.py) |
| 상태 전이·검수·증거·수락 | [workflow/service.py](../handrail/workflow/service.py), [validation.py](../handrail/workflow/validation.py) |
| 실행·통신·복구·통합·정리 | [agentroom/service.py](../handrail/agentroom/service.py), [identity.py](../handrail/agentroom/identity.py) |
| 준비·검증 명령 | [commands.py](../handrail/agentroom/commands.py) |
| 승인 범위 | [authorization/service.py](../handrail/authorization/service.py) |
| Herdr 어댑터 | [interfaces/agentroom/herdr.py](../handrail/interfaces/agentroom/herdr.py) |
| 기존 Vikunja 연동 | [client.py](../handrail/interfaces/vikunja/client.py), [board.py](../handrail/interfaces/vikunja/board.py) |
| Git 격리·통합 | [repository.py](../handrail/interfaces/git/repository.py) |
| 후처리·보드 투영 | [dispatcher.py](../handrail/hooks/dispatcher.py), [hooks/board.py](../handrail/hooks/board.py) |
| 영속성·오류 | [store.py](../handrail/shared/store.py), [errors.py](../handrail/shared/errors.py) |
| 조율자·작업자 행동 지침 | [스킬](../plugins/handrail/skills/handrail/SKILL.md), [에이전트 통합](agent-integration.md) |

새 외부 제품의 프로토콜은 `interfaces/`에, 새 완료 규칙은 `workflow/`에, 실행 대상·관찰·복구는 `agentroom/`에 추가한다. 이벤트 후처리는 `hooks/`에 등록한다. 신규 기능이 승인·검수·증거 관문을 우회하는 별도 실행 경로를 만들지 않도록 연결 지점을 검토한다.

구체적인 사용 명령은 [운영 안내](manual.md), 이번 포함 범위는 [재구현 범위](rebuild-scope.md), 현재 검증 수준은 [구현 상태](status.md)를 따른다. 이 상세 문서는 향후 backlog나 검증되지 않은 기능을 현재 구현으로 간주하지 않는다.

## alpha.6 준비·인계·지침의 관계

```mermaid
flowchart LR
    CLI[Codex 또는 Cursor 조율자] --> APP[Application]
    APP --> MODEL[Providers 실제 모델과 CLI 기능]
    APP --> POLICY[Setup access 좁은 호스트 규칙]
    APP --> INSTR[Board Instructions 및 유형 라벨]
    INSTR --> VK[Vikunja 부모 보드 원본]
    APP --> ROUTE[Board default 등록 및 Work 배정]
    ROUTE --> VK
    APP --> ROOM[Agentroom Service]
    ROOM --> HERDR[Herdr 어댑터]
    HERDR --> WORKER[Codex 또는 Cursor 작업자]
    WORKER --> CHANNEL[실행별 contract readiness submission]
    APP --> HANDOFF[Handoff 수신 및 tick]
    CHANNEL --> HANDOFF
    HANDOFF --> WF[Workflow Review 및 완료 관문]
    WF --> STORE[로컬 문서 이력 Outbox]
    HANDOFF --> STORE
    APP --> REPORT[사용자 Review 보고 기록]
    REPORT --> STORE
    STORE --> HOOK[보드 및 Summary 동기화]
    HOOK --> VK
```

### 준비부터 사용자 Review까지

```mermaid
sequenceDiagram
    actor U as 사용자
    participant C as 조율자
    participant A as Handrail Application
    participant B as Board와 Instruction
    participant R as Agentroom
    participant W as 작업자 sandbox
    participant S as 보고 채널
    participant D as Workflow와 Store
    U->>C: 구현 범위 승인
    C->>B: 활성 지침 및 관련 이력 조회
    C->>A: Plan 및 Work 생성
    A->>B: 배정 결정 및 필요한 default 준비
    C->>A: worker start
    A->>A: 실제 모델/옵션 확인, 지침 변경 확인
    A->>B: 첫 Work 카드와 라벨 동기화
    A->>R: 승인 범위 확인 후 worktree와 실행 준비
    R->>W: 명시 쓰기 경로, readiness 지시
    W->>S: 자신의 도구 경계에서 probe 결과 저장
    C->>A: coordinator tick
    A->>S: readiness 조회
    alt 준비 완료
        A->>W: 원래 start 범위의 구현 지시
    else 거부 또는 확인 불가
        A-->>C: 실제 경계와 자원, 재개 담당
    end
    W->>W: 구현과 허용된 확인, commit
    W->>S: 식별자와 commit 및 구조화 완료 보고
    loop 활성 대화에서만 다음 주기에 확인
        C->>A: coordinator tick
        A->>S: 미수신 보고 읽기
        A->>R: 현재 실행 신원, clean tree, HEAD 확인
    end
    A->>D: receipt 및 Work Review
    C->>A: 실제 변경·지침 준수 검토
    A->>D: 처리된 제출과 review 기록
    C->>R: 승인된 후보 통합
    C->>D: 실제 기준별 canonical 근거 및 Work 완료
    A->>D: 모든 근거 충족 후 Plan Review
    A->>B: Review 보드 동기화
    A-->>C: 내부 상태/보드 전송/사용자 보고 대기
    C-->>U: 결과·검증·미확인·Review 링크
    C->>A: 실제 사용자 보고 기록
```

프로세스의 idle/done은 조회 계기다. 제출에 적힌 확인 내용은 조율자의 검토 자료이며 canonical evidence를 대신하지 않는다. monitor는 owner/targets/last_check/next_check/backoff를 저장하고 tick이 끝나면 running=false다. 실제 호스트 wakeup을 등록하지 않았으므로 재접속 시 다시 tick한다.

### 완료 이후 정리 전용 복구

```mermaid
sequenceDiagram
    actor U as 사용자
    participant C as 조율자
    participant A as Cleanup
    participant I as 실행 신원 관측
    participant H as Herdr
    participant D as Store
    U->>C: 기획 수락 및 room close 선택
    C->>D: Done, Summary, close 자원 범위 기록
    C->>A: plan cleanup
    A->>I: terminal/provider/session/process 대조
    alt 같은 실행의 지연 session ID
        I->>D: 시작 근거 및 프로세스 연속성으로 신원 보강
    else 기존 기록에 근거 부족
        A-->>C: inspect 관측 토큰과 확인 불가 사유
        C->>A: reconcile 토큰과 관측 근거
        A->>I: 실제 변경은 거부, 같은 소유 범위만 재확인
        I->>D: 원래 기록과 보강 근거 보존
    end
    C->>A: resume 기존 close 선택
    A->>H: 공유/활동/신원 검사 후 명시 room 종료
    A->>D: 정리 결과 및 전송 receipt
    A-->>C: 실패는 nonzero, Done과 worktree는 보존
```

정리 scope token은 workspace, pane, terminal, provider, 등록 이름과 소유 출처를 포함한다. 세션 ID의 정상 보강·관측 시각은 동의 범위를 바꾸지 않는다. 실제 대상 변경, 알 수 없는 pane, 활동 중 worker는 계속 종료를 차단한다. 조회/종료 사이 외부 경합은 남는다.

## alpha.5에서 유지하는 데이터와 복구 경계

| 위치 | 데이터 |
| --- | --- |
| Vikunja Summary 본문 | 분리된 언어 설명, Agent Context, 현재 버전과 기준 근거 |
| 같은 카드 댓글 | 이전 본문 전체와 변경 이유 |
| `summary_card` | 카드 ID, 버전, hash, cycle, record status |
| `summary_reference` | 기획/작업의 참조 ID, 버전, hash, 선택 필드, 적용 이유 |
| `operation` | Summary 외부 쓰기의 요청 해시와 처리 상태; 본문 복제 없음 |
| `cleanup_choice` | 사용자가 선택한 room 집합·scope token·close/keep·승인 출처 |

`summary.write`와 `summary.effect`는 생성·본문·댓글·열 이동의 불명확한 결과를 같은 ID로 조회한다. 원본이 변하면 expected hash가 덮어쓰기를 중단한다. 마지막 GET과 PATCH 사이의 경합을 원자적으로 막지는 못한다. `summary resolve`는 외부 쓰기를 하지 않고 관찰 결과와 재시도 판단을 로컬에 기록한다. 자세한 계약은 [Summary 운영](summaries.md)을 따른다.
