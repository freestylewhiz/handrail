# 에이전트 역할과 스킬

Handrail의 조율자는 사용자 의도와 작업 진행을 관리한다. 작업자는 배정된 worktree에서 명시한 범위를 구현한다. Herdr는 둘 사이의 실행과 통신을 제공한다.

## 조율자

- 사용자의 목표와 완료 기준을 계획과 작업에 연결한다.
- 기존 지시로 허용된 범위를 기록하고, 기존 grant와 겹치는 범위는 재사용한다.
- 명시 모델→저장된 선택→실제로 관측한 조율자 모델 순서로 배정한다. 조율자 직접 구현 요청도 같은 모델의 Herdr 작업자로 수행한다.
- 지시 전달과 응답 관찰을 업무 완료와 구분한다.
- 실제 변경을 검수하고 통합 revision의 기준별 근거를 기록한다.
- 누구의 무엇을 기다리는지, 현재 필요한 행동이 무엇인지 보고한다.
- 리뷰 수락을 `plan complete`로 처리하고, Summary를 작성·확정한 뒤 사용자의 close/keep 선택으로 관련 AgentRoom을 관리한다.
- Summary는 영어·사용자 언어·Agent Context로 나누고, 근거가 없는 작업자의 의도는 추측하지 않는다.
- 다음 기획에 참조한 Summary ID·버전·항목을 기록하고 작업자에게 필요한 영역만 전달한다.
- 활성 Instruction을 기획·배정·검토에서 확인하고 변경 영향·예외·참조 버전 및 작업자 전달 결과를 기록한다.
- worker start 뒤 readiness 확인, 활성 대화의 tick, 완료 수신·검토·통합·검증·Plan Review·사용자 보고까지 이어간다. 대화 종료 후 자동 감시를 가장하지 않는다.

## 작업자

- 할당한 작업, worktree, branch와 수정 범위를 유지한다.
- 요구 범위를 구현하고 변경을 커밋한다. 검증은 요청된 범위에 따라 수행한다.
- 결과, 변경 파일, 커밋, 검증 근거와 미확인 부분을 조율자에게 보고한다.
- 보드·grant·관리자 상태·다른 worker의 lifecycle을 직접 변경하지 않는다.
- 막힘이나 추가 권한 필요를 구체적으로 보고한다. 다른 실행 공간으로 임의 이동하지 않는다.
- 자기 sandbox에서 쓰기 probe를 실행하고 구현 지시를 기다린다. 완료는 실행별 채널의 구조화 submission으로 제출하고 수신·검토는 조율자가 처리한다.

## 스킬 구성

제품 스킬의 진입점은 `plugins/handrail/skills/handrail/SKILL.md`다. 설치 경로 추측 없이 locate로 고정 절대 런처와 버전을 확인한다. Codex 플러그인과 Cursor skill 연결은 같은 release 내용을 사용한다.

| 참조 | 역할 |
| --- | --- |
| `references/execution.md` | 모델 선택·좁은 호스트 규칙·readiness·감시·신원 계약 |
| `references/cards-and-instructions.md` | 채택 HTML 양식·언어 분리·유형 라벨·프로젝트 지침 |
| `references/setup.md` | 숨김 토큰 입력과 실제 자원 설정 |
| `references/summaries.md` | Summary 작성, 선택 조회, 버전·참조 관리 |
| `references/workflow.md` | 카드, 승인, 실행, 검수와 사용자 수락 |
| `references/authorization.md` | 승인 재사용과 host 경계 |
| `references/herdr.md` | 내부/외부 조율과 명시 신원, 관찰과 통신 |
| `references/recovery.md` | 중단, 불확실 전송과 자원 보존 |
| `templates/WORKER.md` | 작업자 배정에 포함할 계약 |

## 권한과 외부 조율

외부 조율자는 `HERDR_ENV=1`을 수동 설정하지 않는다. 명시 endpoint와 대상 ID를 통해 기존 Herdr에 연결한다. 연결 성공은 지시 전송, 키 입력, 종료의 모든 권한을 뜻하지 않는다. 기존 사용자 지시가 해당 동작까지 포함한다면 중복 확인하지 않는다.

승인·evidence 문자열은 조율자가 관찰한 사실의 기록이다. CLI는 사람의 신원을 암호학적으로 인증하지 않으며 같은 OS 계정의 악의적인 프로세스를 격리하는 보안 경계도 아니다. 실제 worker sandbox와 관리 파일 접근 정책은 실행 호스트가 제공한다.
