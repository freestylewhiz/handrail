# 데이터와 경계

Handrail은 Codex 플러그인 안에 표준 라이브러리 Python runtime을 묶어 배포합니다. 사용자는 별도 Handrail pip package를 설치하지 않습니다. Python 3.9+와 Git은 host 요구사항입니다. Docker와 Node.js는 runtime 요구사항이 아닙니다.

## 원본 데이터

| 데이터 | 원본·저장 위치 |
| --- | --- |
| project, task, comments, attachment bytes, Kanban state | 사용자가 준비한 외부 Vikunja v2 |
| spec, check plan, source, summary snapshot | 각 로컬 Git repository |
| binding ID와 상태 mapping | repository의 `.handrail/project.json` |
| connection URL/profile 및 token | 사용자 XDG config/data의 private 파일 |
| worker profile, run state, logs, locks, attachment packet | 사용자 XDG data의 workspace별 디렉터리 |

한 Git repository는 하나의 기존 Vikunja parent project와 그 안의 manual Kanban view에 연결됩니다. 서로 다른 repository는 별도 parent binding, spec, run, lock을 갖습니다. binding은 원격 board를 수정하지 않습니다. Handrail은 Git remote URL, credential, push, pull request 상태를 읽거나 저장하지 않습니다.

## 권한과 secret

Manager만 Vikunja token을 사용합니다. Token input은 사용자의 terminal에서 숨김 처리합니다. Shared `.handrail/project.json`에는 host URL, token, 절대 경로를 저장하지 않습니다. Worker 환경에서 Vikunja token과 Handrail 관리자 설정 경로를 제외합니다.

Worker는 승인된 local Git worktree에서 실행됩니다. 같은 OS 계정에서 실행되는 CLI의 강한 격리를 보장하지 않습니다. `.env`, token file, SSH key는 자동 context로 수집하지 않습니다. Vikunja 원문과 첨부는 untrusted evidence로 표시하고 system instruction이나 권한으로 승격하지 않습니다.

Worker CLI 권한의 공통 계약은 [worker authorization policy](worker-authorization-policy.md)에 정의합니다. 명세 승인과 실행 권한 승인은 별개이며, provider별 자동화 모드는 같은 worktree 경계를 유지해야 합니다.

## 실행과 수명주기

Repository canonical Git common directory를 기준으로 write run을 하나만 허용합니다. Run은 spec hash, checks, binding revision, baseline SHA, worker provider/model 선택 출처를 고정합니다. 긴 작업은 supervisor가 관리하고 `run inspect`, `cancel`, `recover`, `resume`으로 상태를 확인하거나 복구합니다.

Worker result는 `RESULT.md`, `result.json`, `journal.md` 계약을 통과해야 합니다. 검증은 승인된 모든 check ID의 최신 fingerprint 통과와 수동 판정을 확인합니다. 의미 review, local integrate, Vikunja sync, 사용자의 Done 확인을 분리합니다. 외부 write 결과가 불확실하면 상태를 확인하기 전 자동 retry하지 않습니다.

## 작업 경로

```text
Codex manager
  ├─ bundled Handrail launcher → local config / workspace binding
  ├─ authenticated Vikunja v2 reads and reconciled writes
  └─ run supervisor → isolated Git worktree → Codex or Cursor worker CLI
```

Plugin cache는 배포 파일을 읽는 위치입니다. Token, project state, Python bytecode, run output은 cache에 쓰지 않습니다. Settings paths follow XDG: `${XDG_CONFIG_HOME:-~/.config}/handrail` and `${XDG_DATA_HOME:-~/.local/share}/handrail`.
