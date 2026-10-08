# Handrail

Handrail은 사용자, 조율자, 작업자가 합의한 개발 작업을 계획부터 검수까지 이어주는 로컬 도구입니다. Herdr에서 작업자를 실행하고, 기존 Vikunja 서버에는 카드와 진행 이력을 연결합니다.

현재 소스는 **1.0.0a6 개발 버전**입니다. Codex/Cursor 조율자와 작업자가 같은 Herdr 실행 경로를 사용하며, 설정·워크플로우·보드·실행·외부 연동을 독립 컴포넌트로 나눕니다. [체크리스트 구현 기록](docs/alpha6-implementation.md)에 반영 사항과 확인 제한을 정리했습니다. 2026-10-08 사용자 요청으로 호스트 재설치와 기존 체크리스트 전체 종료를 완료했습니다. 실제 workflow 실행 테스트·측정의 수행 여부는 구현 기록에 보존했습니다.

## 작업 흐름

1. 계획과 완료 기준을 작성하고 사용자의 기존 구현 승인을 기록합니다.
2. 부모 보드 Instruction과 작업보드를 확인합니다. 명시 모델, 저장된 선택, 관측한 조율자 모델 순서로 배정합니다.
3. 필요한 쓰기 경로로 작업자를 실행하고 작업자 자신의 sandbox 진단 뒤 구현을 지시합니다.
4. 조율자가 구조화 완료 보고를 수신·검수하고 검수한 커밋을 통합합니다.
5. 통합된 코드의 기준별 증거를 기록하고 작업을 완료합니다.
6. 계획 전체를 검증해 Review로 제출하고 영어·사용자 언어·Agent Context로 분리한 Summary를 준비합니다.
7. 사용자 최종 승인에 내부 기획을 수락하고 보드·Summary를 동기화합니다. 관련 AgentRoom의 종료 또는 보존을 선택받습니다.
8. 다음 기획은 관련 Summary를 조회하고, 선택한 항목과 근거를 작업자에게 전달합니다.

작업자의 `idle/done`은 입력 가능한 실행 상태입니다. 카드 완료에는 검수·통합·검증 근거가 따로 필요합니다.

## 구조

```text
handrail/
  setup/          설치·연결·진단·좁은 호스트 승인 규칙
  board/          하위/default 보드·카드·라벨·Instruction
  summary/        보드 원본의 요약과 버전·선택 조회
  workflow/       계획과 작업, 승인, 증거, 상태와 이력
  agentroom/      room·worker·readiness·완료 인계·감시·복구
  interfaces/
    agentroom/    Herdr 어댑터
    vikunja/      기존 Vikunja API 어댑터
    git/          worktree와 통합 어댑터
  authorization/  범위별 승인 재사용
  hooks/          보드 동기화와 정리 후처리
  shared/         오류와 영속 저장
  application.py  컴포넌트 연결
  cli.py          명령 인터페이스
```

## 시작

설치 후 저장소에서 `handrail init`을 실행하거나 새 Codex/Cursor 세션에서 설정을 요청하세요. 기존 연결을 재사용하고, 부모 보드를 선택하면 필요한 Kanban 열을 준비합니다. [간단한 연결 절차](docs/onboarding.md)를 참고하세요.

Linux, Python 3.9 이상, Git, 실행 중인 Herdr, 기존 Vikunja v2 서비스와 인증된 작업자 CLI가 필요합니다.

```sh
python3 -m handrail --help
python3 -m handrail doctor
python3 scripts/build_plugin.py --output dist/rebuild
```

설치 및 설정은 [설치 안내](docs/installation.md), 전체 명령 흐름은 [운영 안내](docs/manual.md)를 참고하세요. v0.5의 설정과 이력은 자동 변환하지 않으며 신규 상태는 별도 `handrail/v1` 경로에 저장됩니다.

## 문서

- [아키텍처와 구조도](docs/architecture.md)
- [상세 아키텍처와 워크플로우 시퀀스](docs/architecture-detailed.md)
- [설계 철학](docs/philosophy.md)
- [에이전트 역할과 스킬](docs/agent-integration.md)
- [이번 재구현 범위](docs/rebuild-scope.md)
- [구현 상태와 제한](docs/status.md)

2026-10-08 사용자 요청으로 현재 코드·규약·설계·검증 결과를 새 `main`의 최초 커밋 기준으로 삼았습니다. 이전 로컬 Git 이력과 브랜치는 제거했으며 이후 개선은 이 기준에서 진행합니다. 과거 분석 문서는 설계 근거로 보존하고 자동 개발 backlog로 취급하지 않습니다. DEV-11의 미구현 범위와 DEV-12의 호스트 수용 대기는 [체크리스트](docs/checklist-v1-host-test.md)에 그대로 남아 있습니다.

## 보드와 카드 관리

하위 보드 추가는 `handrail board add frontend backend`, 사용자 요청 카드 전환은 `handrail card move CARD --state done --force --reason "사용자의 변경 요청"`으로 처리합니다. 작업자 실행이나 Git 통합 없이 관리 이력을 남깁니다. [보드·카드 관리](docs/boards.md)를 참고하세요.

정식 리뷰 승인은 `plan complete`로 처리합니다. [Summary와 기획 완료](docs/summaries.md)에 작성·참조·정리 선택 절차를 정리했습니다.
