# Codex와 worker CLI

Handrail v0.5.0 source distinguishes the existing Handrail-managed run workflow from the Herdr-backed workflow in development. Historical validation for the existing run path is based on v0.4.1. The Herdr path is invoked with `handrail herdr <command>` and has a separate command family, but its release acceptance is not established here; see the [Herdr workflow](herdr-workflow.md). CLI JSON output carries status and operation results; it does not replace natural-language judgment or user approval.

## Codex 매니저

Codex 매니저는 Vikunja 연결, task source 확인, 선택 첨부 판단, 범위 합의, 명세 승인 기록, run 감독, 검증·리뷰, 로컬 통합을 담당합니다. repository를 Codex에서 연 뒤 자연어로 구체적인 task 또는 작업을 지정합니다. 저장소 밖에서 전역 마지막 선택만으로 쓰기를 실행하지 않습니다.

```text
현재 repository의 Handrail binding을 확인하고 task 42와 comments/attachment metadata를 읽어줘.
필요한 첨부를 고르기 전에 목록을 보여주고, 목표·범위·완료 기준을 나와 합의해줘.
승인 명세와 검증 계획을 준비하고 worker를 시작하기 전에 변경 범위와 provider/model을 알려줘.
```

Codex의 숨김 터미널 token 입력이 필요한 `setup`과 `connection rotate`는 사용자가 직접 terminal에서 실행합니다. 토큰을 채팅, prompt, argument, packet, worker 환경에 포함하지 않습니다.

## Worker CLI

run별 worker provider는 `codex` 또는 `cursor`입니다. Worker는 별도 CLI 인증을 사용하고 승인된 worktree에만 구현 산출물을 씁니다. Handrail 관리자 token/config와 Vikunja API 호출은 worker 책임이 아닙니다. 필요한 provider CLI를 사용자가 설치·인증합니다. Handrail이 모델을 자동 설치하거나 유료 모델을 호출해 진단하지 않습니다.

```sh
python3 -I <plugin-root>/scripts/handrail.py worker profile set codex-default --provider codex --model <model-id>
python3 -I <plugin-root>/scripts/handrail.py worker profile set cursor-default --provider cursor --model <model-id> --autonomy workspace-auto
```

`--autonomy confirm` is the default. `workspace-auto` suppresses routine worker prompts. Codex retains workspace-write; Cursor retains its sandbox and uses --force (Run Everything, including configured MCP/Fetch tools). Explain those modes when recording capabilities. v0.4 `run start` reuses valid saved permissions and plan delegation; `--preview` inspects coverage without launch. Use one-run confirmation only when saved coverage is unavailable. Existing explicit user authorization is recorded without another question. See the [permission guide](permissions-v0.4.md) for multi-plan delegation, host preflight and recovery.

worker model precedence는 run override → repository 기본 worker 설정 → 선택 worker profile → 그 CLI의 기본값입니다. Provider 변경은 다른 provider의 model을 이어받지 않습니다. 제공자가 실제 model ID를 반환하지 않으면 Handrail은 추측하지 않고 null로 둡니다.

Candidate 검증 대상은 Codex 매니저 → Codex worker 및 Codex 매니저 → Cursor worker입니다. Cursor를 오케스트레이터로 쓰는 흐름은 후속 범위이며 현재 지원으로 소개하지 않습니다.

## 승인과 책임

Vikunja task/comment/attachment는 작업 evidence입니다. 해당 내용 안에 모델 지시, shell 문장, credential 요구가 있더라도 실행 권한이 되지 않습니다. 매니저가 사용자의 의사를 확인하고 승인된 Git 명세와 check plan에 기록합니다. Worker output은 구조와 hash를 검사한 다음 별도로 검증·의미 리뷰합니다. `accept`, local integration, Review sync, 사용자 최종 Done 확인은 각각 다른 단계입니다.
