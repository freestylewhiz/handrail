<div align="center">

# Handrail

**Traceable development workflows for humans and coding agents.**

*Keep human-agent development on track.*

[Get started](docs/installation.md) · [Philosophy](docs/philosophy.md) · [Workflow guide](docs/manual.md) · [Documentation](docs/README.md)

</div>

---

An idea becomes a plan. A plan becomes work. Every result comes back with a record of what changed, how it was checked, and who decides what happens next.

Handrail connects your Git repository, Vikunja board, and coding agents through a shared development workflow. An orchestrator coordinates the work, workers implement it in isolated Git worktrees, and you review the integrated result.

## From intent to a result you can review

| What you need to know | What Handrail keeps connected |
| --- | --- |
| What did we agree to build? | A plan, its scope, and approved specifications |
| Which work belongs to that plan? | Work cards with actual parent–child task relationships |
| What did the agent deliver? | Worker runs, changes, review, and verification evidence |
| Is the whole result ready? | Local integration and checks against the combined result |
| Who acts next? | Work completion, user review, and final acceptance |

One repository starts with one parent project. Register child boards as the project grows, while keeping their work connected to the original plan.

## The workflow

1. **Agree on the plan.** Define the goal, scope, constraints, and completion criteria.
2. **Break it into work.** Connect each work card to the plan and choose its worker.
3. **Implement and inspect.** Run the worker, review its changes, integrate locally, and verify.
4. **Complete the work.** Mark verified work cards **Done** and check the combined result.
5. **Ask for user review.** Move the plan to **Review**, with results and evidence attached.
6. **Accept or improve.** You decide when the plan is **Done**. Corrections become new work cards, preserving the earlier history.

Handrail normally manages card state. When you change it directly, the orchestrator can inspect the difference and reconcile it with your intent.

## Delegate a batch, keep the history

v0.4 stores reusable project or global permissions and connects them to several plan cards in one delegation. Covered runs, retries, and verification reuse that authority. New capabilities remain explicit, and you still decide when a plan is complete.

Failed candidates can be restored before a replacement worker starts, with dependency preparation and execution evidence recorded alongside the run. [Permission and delegation guide →](docs/permissions-v0.4.md)

[Explore the workflow, its intent, and terminology →](docs/philosophy.md)

## Get started

Handrail is distributed as a **Codex plugin**, with its Python runtime included. The current implementation uses Codex as the orchestrator and supports Codex or Cursor CLI workers.

The last published candidate can be installed with:

```sh
codex plugin marketplace add freestylewhiz/handrail --ref plugin-v0.3.0-rc.4
codex plugin add handrail@handrail
```

Open your repository in Codex, connect to your existing Vikunja service, and bind its parent project using the [setup guide](docs/installation.md).

**Requirements:** Linux, Python 3.9+, Git, an existing Vikunja v2 service, and an authenticated worker CLI. See [implementation status](docs/status.md) for the environments checked so far.

This source tree builds **v0.5.0**. Build the self-contained plugin with `python3 scripts/build_plugin.py --output dist/v0.5.0` and validate it with `python3 scripts/validate_distribution.py dist/v0.5.0`. The only installation commands above still install the historical RC4 candidate; they do not install this source version. Herdr orchestration is an in-development workflow with separate lifecycle commands; see the [Herdr workflow](docs/herdr-workflow.md) and [acceptance design](docs/testing/herdr-acceptance.md). It is not represented as a published or acceptance-verified release. Historical v0.4 permissions and child-board validation remain documented in the [v0.4 validation record](docs/v0.4-validation.md).

## Built around your project

- **Local execution.** Specifications live in Git; workers run in isolated local worktrees.
- **Existing tools.** Connect to the Vikunja service and coding CLIs you already use.
- **Explicit scope.** Each repository manages its parent project and the child boards you register.
- **Human acceptance.** The orchestrator prepares the result for review; you decide when the plan is complete.

Vikunja is installed and operated separately. Remote Git actions such as pushes and pull requests remain with your orchestrator and existing tooling.

## Read more

| Guide | Start here when you want to… |
| --- | --- |
| [Philosophy](docs/philosophy.md) | Understand the principles, workflow, and vocabulary |
| [Installation](docs/installation.md) | Install the plugin and connect a repository |
| [Manual](docs/manual.md) | Manage cards, run workers, review results, and recover work |
| [Architecture](docs/architecture.md) | Understand components, storage, and execution boundaries |
| [Implementation status](docs/status.md) | Check what is implemented and what has been validated |

---

*Keep human-agent development on track.*
