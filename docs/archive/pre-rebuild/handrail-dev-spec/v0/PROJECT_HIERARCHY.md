# 프로젝트별 부모 보드와 하위 보드 확장

정책: 각 Handrail 프로젝트는 계획 카드를 관리하는 부모 보드 1개로 시작한다. 구현·조사·후속 보완은 계획에 연결된 새 작업 카드로 관리하며, 필요하면 하위 작업 보드를 추가한다.

## 1. 한 호스트에서 여러 프로젝트

```text
하나의 개발 호스트
├─ Handrail 프로젝트 A / 저장소 A
│  └─ Vikunja 부모 프로젝트 A · 기본 Kanban 보드 1개
│     ├─ backend · 별도 Kanban   ← 필요할 때 추가
│     └─ frontend · 별도 Kanban  ← 필요할 때 추가
└─ Handrail 프로젝트 B / 저장소 B
   └─ Vikunja 부모 프로젝트 B · 기본 Kanban 보드 1개
      └─ 현재 하위 프로젝트 없음
```

초기에는 각 프로젝트의 부모 보드에 모든 작업을 둔다. 호스트 공통 부모 보드나 초기 inbox·컴포넌트 보드를 만들지 않는다. A와 B는 같은 Vikunja 인스턴스·연결 프로필을 사용할 수도, 다른 연결을 사용할 수도 있다.

| 개념 | 단위와 책임 |
| --- | --- |
| 호스트 설치 | 플러그인·번들 runtime 설치 |
| 연결 프로필 | Vikunja URL·계정 토큰 참조, 여러 workspace에서 재사용 가능 |
| Handrail 프로젝트/workspace | Git 저장소·부모 binding·명세·run·worktree의 관리 단위 |
| 부모 binding | 해당 workspace가 처음 사용하는 Vikunja project + Kanban view + 상태 bucket 매핑 |
| area | 필요할 때 등록하는 그 부모 아래의 하위 프로젝트·보드 |

현재 디렉터리의 Git root 또는 명시적 workspace 지정으로 대상을 선택한다. 선택 결과는 대화·run에 고정하고, 다른 세션이 전역 선택을 바꿔도 따라가지 않는다. 같은 Git common directory에는 쓰기 run 하나를 허용하며 다른 저장소의 작업은 독립적으로 진행할 수 있다.

## 2. Vikunja에서 가능한가

가능하다. Vikunja는 프로젝트의 하위에 프로젝트를 중첩할 수 있고, 각 프로젝트는 자체 Kanban 뷰를 가질 수 있다. UI에도 하위 프로젝트 생성 기능이 있다. 사용자가 말한 하위 보드는 **하위 프로젝트와 그 안의 Kanban 뷰**로 모델링한다. [공식 Projects](https://vikunja.io/help/projects/), [공식 Views](https://vikunja.io/help/views/)

현재 Handrail에도 기반이 있다. [board.py](https://github.com/freestylewhiz/handrail/blob/673c29a022e01dec1d4102f665aa0d0afdd1fd12/handrail/board.py)의 `init()`은 root를 만든 뒤 `ensure_project(..., parent=root['id'])`로 inbox와 children을 만들고 각 프로젝트에 `ensure_view()`를 적용한다. 기존 컴포넌트 구성은 이 계층을 이용한다. 코드 존재를 확인했으며 이번 조사에서 사용자 보드를 변경하지 않았다.

재사용할 것은 부모 ID와 area별 project/view/states 매핑이다. 신규 설정에서 inbox와 children을 일괄 생성하는 동작은 제거한다. 기존 `ensure_view()`는 열을 수정·삭제할 수 있으므로 기존 보드 연결 경로에 그대로 사용하지 않는다.

## 3. API와 권한

공식 공개 데모의 [v2 OpenAPI](https://try.vikunja.io/api/v2/openapi.json)를 읽어 아래 계약을 확인했다. 응답의 버전은 `v2.6.0-538-g0a5ac04f`였다. 공개 데모의 개발 버전 계약이며 사용자의 설치 버전을 보증하지 않는다. 구현 시 대상 인스턴스의 명세를 다시 확인한다.

| 작업 | 확인한 v2 경로 | 프로젝트 권한 |
| --- | --- | --- |
| 하위 프로젝트 생성 | `POST /api/v2/projects`, body의 `parent_project_id` 지정 | 부모 프로젝트 쓰기 + `projects-create` token permission |
| 프로젝트의 뷰 조회 | `GET /api/v2/projects/{project}/views` | 프로젝트 읽기 |
| 전용 Kanban 뷰 생성 | `POST /api/v2/projects/{project}/views` | 해당 프로젝트 admin + `project-views-create` token permission |
| 뷰 설정 변경 | `PUT/PATCH /api/v2/projects/{project}/views/{view}` | 해당 프로젝트 admin + view update token permission |
| Kanban bucket 생성 | `POST /api/v2/projects/{project}/views/{view}/buckets` | 해당 프로젝트 쓰기 + `buckets-create` token permission |

모든 작업에는 해당 경로를 허용하는 API 토큰 permission도 필요하다. 프로젝트 권한과 토큰 permission을 각각 확인하고, route별 이름은 대상 서버의 token permission 목록을 따른다. project/task 생성·읽기·수정, manual view와 bucket 관리, task bucket 이동 및 plan/work 연결용 task relation 생성 권한을 setup에서 안내한다. 설정 단계는 읽기만 검증할 수 있으므로 write 권한 성공을 보장하지 않는다. 프로젝트 생성에 서버 전체 관리자 권한은 필요하지 않다. 부모 쓰기 권한 확인은 [공식 권한 구현의 CanCreate](https://github.com/go-vikunja/vikunja/blob/main/pkg/models/project_permissions.go)에서도 확인된다.

확인한 명세에서 새 프로젝트의 소유자는 인증 사용자이며 기본 views와 backlog bucket이 자동 생성된다. 생성 후 응답과 views를 다시 읽는다. Handrail 전용 manual Kanban 뷰가 필요하면 새로 생성한 프로젝트 안에 만들고 Todo/Doing/Done 상태 열을 구성한다. Review 열은 하위 작업 보드에서 요구하거나 자동 생성하지 않으며, 카드 자체가 작업 이력이다. 부모 또는 기존 사용자 뷰의 열을 변경하지 않는다.

기존 프로젝트를 다른 부모로 이동시키는 행위는 별도 권한·영향을 갖는다. 하위 보드 추가 기능에 기존 프로젝트 이동·공유 설정 변경을 묶지 않는다. 하위 프로젝트가 별개의 권한 격리 공간이라고 가정하지 않고 대상 서버의 상속·공유 규칙을 확인한다.

## 4. 권장 대화 흐름

예: 사용자가 A 저장소에서 “backend 작업을 분리하자. 이 프로젝트 아래에 보드 하나 만들어줘”라고 요청한다.

1. A workspace와 부모 project ID를 확정한다. B 또는 호스트 공통 선택을 사용하지 않는다. 부모 프로젝트는 계획 카드를 두는 메인 보드이고, 하위 보드는 선택 기능이다.
2. 같은 부모 아래 기존 이름·등록 상태, 프로젝트 권한과 토큰 scope를 확인한다.
3. 요청 범위인 하위 프로젝트·전용 Kanban·기본 상태 열 구성을 기록한다. 이미 받은 생성 요청을 같은 범위에서 반복 승인받지 않는다.
4. operation ID와 부모·이름·현재 binding revision을 로컬에 기록한다.
5. `parent_project_id`를 지정해 하위 프로젝트를 생성한다.
6. 생성된 manual Kanban view를 재사용하고 Todo/Doing/Done을 준비·확인한다. Review는 요구하거나 자동 생성하지 않는다.
7. 서버에서 ID·소속·열을 다시 읽어 검증하고 A의 `areas.backend`에 등록한다.
8. 새 보드와 등록 결과를 보고한다. 이후 계획카드의 작업카드를 생성하고 원하는 하위 보드에 배치해 실제 task relation으로 연결한다. 작업카드는 상태와 실행 연결을 보존하는 작업 이력이다.

내부 명령은 `area create --parent root --name backend`, `area bind --project-id … --view-id …`, `area list`다. `--parent`에는 현재 workspace의 root 또는 이미 등록한 area만 허용한다. 사용자에게 이 명령을 외우게 하지 않고, 자연어 요청에 맞춰 조율자가 수행한다.

분리 요청만으로 기존 카드를 모두 이동하지 않는다. 카드 이동이 필요한 경우 대상·범위를 해당 작업으로 처리한다. 하위 보드가 없는 동안에도 부모 보드에서 명세·위임·검증 흐름이 모두 동작해야 한다.

## 5. 연결 범위와 복구

- 부모 binding은 하나이며 area는 같은 instance의 해당 부모 아래에 있어야 한다. 이름은 표시용이고 ID와 실제 조상 관계로 확인한다.
- 다른 Handrail 프로젝트가 사용하는 부모·하위 프로젝트와 범위가 겹치면 자동 등록하지 않는다. 같은 호스트의 registry에서 확인 가능한 충돌을 진단한다.
- 서버에서 보이는 모든 자손을 자동 등록하지 않는다. 명시적으로 연결한 project ID만 작업 허용 목록에 추가한다.
- 생성 중 잠정 허용 범위는 요청한 부모와 해당 operation에서 확인한 새 project ID로 제한한다. 연결 정보 갱신과 실행 시작은 같은 repository 잠금 규칙으로 직렬화한다.
- 활성 쓰기 run이 있으면 area 추가·binding 변경을 보류한다. 완료된 등록에서만 binding revision을 증가시킨다.
- 생성 성공 뒤 뷰 설정이나 로컬 저장에 실패하면 project ID와 완료 단계를 보존하고 이어서 구성한다. 자동 삭제로 되돌리지 않는다.
- 생성 요청의 응답이 유실되면 `unknown`으로 남기고 재조회한다. operation 표식·부모·생성 기록으로 유일하게 확인할 수 있을 때만 이어간다. 같은 이름만 보고 기존 프로젝트를 자신의 생성 결과로 채택하거나 POST를 반복하지 않는다.
- 계층이 외부에서 바뀌거나 접근이 철회되면 해당 area의 쓰기를 멈추고 재연결을 안내한다.

## 6. 전체 현황 보기

부모-자식 계층이 있다는 사실만으로 부모 Kanban에 자식 카드가 자동 통합된다고 가정하지 않는다. Handrail의 목록·요약은 현재 workspace의 부모와 등록된 areas를 명시적으로 읽어 집계하고 출처 area를 표시한다.

Vikunja의 saved filter는 여러 프로젝트의 카드를 모아 볼 수 있는 개인 기능이다. 현재 공식 안내상 다른 사용자·팀과 공유하는 보드로 사용할 수 없다. 필터의 Kanban bucket이 원본 보드의 상태와 자동 동기화된다고도 가정하지 않는다. 따라서 기본 통합 보드 의존성으로 삼지 않는다. [공식 Saved Filters](https://vikunja.io/help/saved-filters/)

## 7. 개발 순서

v0에서 프로젝트별 부모 보드 하나, 여러 workspace의 선택·기록 구분, 기존 areas 이관을 구현한다. 그 위에 요청에 따른 하위 생성·등록을 선택 기능으로 추가한다. [BACKLOG의 HR-NEXT-003](BACKLOG.md)에 범위와 완료 조건을 기록한다.

공식 기능·공개 명세·현재 코드만 조사했다. 사용자의 토큰 권한, 설치 버전의 생성 동작, 실제 다중 workspace 실행은 구현 수용 단계에서 확인할 항목이다.
