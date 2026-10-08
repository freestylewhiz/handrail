# 계층형 Kanban workflow 검증

검증일: 2026-10-01. 대상은 현재 개발 트리이며, 기존 배포본 `0.3.0-rc.3`의 기능을 소급하여 변경한 기록이 아니다.

## 실행 결과

- 전체 Python unittest: **108개 통과**, 생략 없음.
- 실제 Vikunja 2.6.0을 별도 임시 컨테이너로 실행하고 인수 테스트를 활성화했다.
- 작업자는 결정적인 테스트용 CLI를 사용했다. HTTP API, Git 저장소/worktree/통합, supervisor 프로세스, 카드 관계·상태는 실제 실행했다. 이 테스트가 Codex/Cursor 모델 자체의 구현 품질을 검증했다는 뜻은 아니다.
- 개발용 플러그인 bundle/ZIP/checksum 생성 및 distribution 검사 통과.
- 빌드 결과의 플러그인 manifest 검사, 스킬 검사, 격리된 Python launcher의 한국어 도움말 조회 통과.
- `git diff --check` 통과.

실행 명령:

```bash
HANDRAIL_TEST_VIKUNJA_URL=http://127.0.0.1:<테스트포트> python3 -m unittest discover -s tests
python3 scripts/build_plugin.py --output dist/workflow-development
python3 scripts/validate_distribution.py dist/workflow-development
python3 -I dist/workflow-development/handrail/scripts/handrail.py help workflow
```

`HANDRAIL_TEST_VIKUNJA_URL`은 폐기 가능한 테스트 서버에만 지정한다. 테스트는 새로운 계정·프로젝트를 생성하며 기존 사용자 연결정보를 사용하지 않는다.

## 실제 서버에서 확인한 흐름

1. 부모 보드 하나와 backend/frontend 하위 보드를 등록한다.
2. 계획 카드와 교차 프로젝트 하위 작업 카드 두 개를 실제 subtask 관계로 연결한다.
3. 같은 카드 생성 operation을 반복해도 카드가 중복되지 않는다.
4. 각각 작업자를 실행하고 검수·검증·Git 통합 후 작업 카드를 Done으로 처리한다.
5. 사람이 완료 작업을 Doing으로 바꾸면 충돌을 감지한다. preview는 관리 파일을 수정하지 않으며, 사용자 선택에 따른 apply는 보존된 완료 근거를 확인하고 Done을 복원한다.
6. 계획의 자동·수동 종합 검증을 수행한다. 검증 이후 코드가 달라지면 Review 제출을 차단한다.
7. 댓글 생성 및 상태 이동 직후 응답 유실을 주입한다. 재시도는 같은 제출을 이어가고 댓글을 중복 생성하지 않는다.
8. 계획은 Review 및 `done=false`, 작업은 Done으로 남는다. 같은 Review 제출과 이전 작업의 `run sync`를 반복해도 상태를 잘못 되돌리지 않는다.
9. 계획을 재개하고 종합 검증만 반복해도 신규 작업 카드가 없으면 재제출을 차단한다. 새 보완 작업을 완료한 뒤 새로운 Review 회차로 제출한다.
10. 사용자 UI Done을 명시적으로 adopt하는 경로와 `plan accept --approval` 경로를 확인한다.
11. 코드 변경이 없는 조사 작업은 불필요한 Git commit 없이 검수·검증 후 완료한다.

## 범위

- 기존 하위 보드 등록 및 순차 작업자 실행을 지원한다. 하위 프로젝트 자동 생성과 병렬 작업자 통합은 포함하지 않는다.
- Vikunja의 조건부 쓰기를 원자적 비교·교환으로 가정하지 않는다. 상태 재조회 및 operation 복구를 사용하지만, 원격의 동시 UI/API 변경 사이에는 서버 수준의 경합 여지가 있다.
- 개발 빌드의 버전 문자열은 기존 소스 버전을 유지한다. 공개 release, 원격 push, 호스트 설치본 교체는 이번 검증 기록에 포함하지 않는다.

이 기록은 배포 전 개발 검증을 보존한다. 후속 `0.3.0-rc.4` 배포의 최종 소스·배포 리비전, 테스트 결과, 설치·다운로드 검증은 [릴리스 검증 기록](release-validation.md)과 해당 GitHub release의 `handrail-release-evidence.json`에서 확인한다.
