# GitHub branch protection checklist

Repository administrators must configure these settings in GitHub; the workflow cannot change its own protection rules.

- Require the `ai-quality-gate` check before merge.
- Require the pull-request branch to be current with its base branch.
- Disallow direct pushes and force pushes to protected branches.
- Limit bypass permission to named repository administrators or emergency roles.
- Require every bypass to carry a separate, retained audit record with actor, reason, affected commit, and follow-up verification.

For this repository, `main` protection was configured and read back on 2026-08-30 after
[PR #1](https://github.com/MaginaLW/harness-model/pull/1) passed the required
[`ai-quality-gate`](https://github.com/MaginaLW/harness-model/actions/runs/33299540705).
The rule requires an up-to-date PR and conversation resolution, applies to administrators, and
disallows force pushes and branch deletion. It requires zero GitHub reviewer approvals so the
single-maintainer repository is not deadlocked; AI Flow approvals and applicable external-action
authorization remain independent requirements.

The `pull_request` workflow grants `contents: read`, checks out the event head SHA and installs the locked environment. The job timeout is 90 minutes. `Resolve PR governance` uses the PR base and head to identify the implementation task, closeouts and retained records. Maintenance mode applies when the base commit's `.ai/bootstrap-mode.yaml` contains the exact lines `mode: bootstrap_auto` and `status: active`. A marker change takes effect for subsequent PRs after merge. [Workflow](../../.github/workflows/ai-quality-gate.yml) · [PR routing](../../tools/ci/resolve_task.py)

| PR contents | Checks to look for |
|---|---|
| Implementation task, including a governed change in maintenance mode | `Attach exact PR head branch` validates the branch name, creates the runner-local branch at the event SHA, and checks both name and SHA. `Validate contracts` and `Verify and Gate` run for the selected task. `Upload AI Flow diagnostics` collects its evidence and logs from the runner's temporary directory, with 14-day retention. |
| Changed `MERGED` records or retained `FAILED` / `BLOCKED` records | `Validate retained task records` validates each ledger and checks its base-to-head changes. In maintenance mode ordinary docs may accompany a closeout without a new implementation task. Retained failures require an implementation task. |
| Ordinary maintenance outside the governed paths, with no task changes | `Maintenance quality checks` runs without an implementation task. |

`Maintenance quality checks` applies to all three routes when maintenance mode is active. It reuses the full-suite coverage database from successful V1 or V2 verification. Otherwise it runs the full pytest suite with branch coverage. The coverage checker requires at least 85% total branch-enabled coverage for `src/aiflow` and 90% coverage of changed lines in that domain against the PR base. The step also runs `git diff --check` on the PR range, Ruff lint and format checks, and mypy. [Coverage checker](../../tools/ci/check_coverage.py)

To inspect a PR locally, run `uv run --locked python tools/ci/resolve_task.py --route --base <BASE-SHA> --head <HEAD-SHA>` from the repository root. For TASK-0162, the implementation returned `task_id=TASK-0162` and passed both verification and maintenance checks. The follow-up returned `closeouts=TASK-0162` with an empty `task_id` and passed both ledger validation and maintenance checks. [PR #175 implementation run](https://github.com/MaginaLW/harness-model/actions/runs/44344933819) · [PR #176 closeout run](https://github.com/MaginaLW/harness-model/actions/runs/44347779029)

The workflow file is not proof that enforcement is active. Before claiming the repository is protected, run it on a real pull request, configure `ai-quality-gate` as required, and retain platform evidence that the target branch rejects direct/force pushes and bypasses outside the named emergency roles.

Branch protection and the `ai-quality-gate` required check apply in both modes. The project owner defines the governed change classes, standing delivery authorization and actions requiring separate approval in [AGENTS.md](../../AGENTS.md).

## Formal-mode canary evidence

A formal-mode implementation canary requires a successful `ai-quality-gate` on the exact final PR head. In the current workflow, confirm that `Resolve PR governance`, `Verify and Gate` and `Upload AI Flow diagnostics` succeeded, and that `Maintenance quality checks` was skipped because the base had no active maintenance marker. Use the `ai-flow-<TASK-ID>` artifact during its retention window. The PR, merge commit, final-head check and Actions run metadata provide the durable record.

Do not commit the run URL back into the same governed pull request. That changes the final head,
invalidates the previous run's subject binding, and requires a new successful check. Record the
final task, head, and run in a later governed document or another immutable external audit record.
If the base or head changes before merge, accept only a new successful check for the resulting
exact head.

The first observed canary used the step names in effect at the time. [PR #2](https://github.com/MaginaLW/harness-model/pull/2)

| Fact | Retained value |
|---|---|
| Base | `main@37dce2a61a5dc484b077ba4463cede2be04dd746` |
| Final PR head | `9b3a58d63070eb8d221c7061fd383cb2ce7bcd3d` |
| Merge commit | `0989da65702a756c229b0dc7a1c14d56639ad384` |
| Required check | `ai-quality-gate` — `COMPLETED / SUCCESS` |
| Actions run | [33450685267](https://github.com/MaginaLW/harness-model/actions/runs/33450685267) |
| Job | [99679646219](https://github.com/MaginaLW/harness-model/actions/runs/33450685267/job/99679646219) |
| Formal steps | `Resolve task`, `Verify and Gate`, and `Upload AI Flow diagnostics`: `SUCCESS`; `Bootstrap quality checks`: `SKIPPED` |
| Diagnostics | `ai-flow-TASK-0030`, artifact `9779802345`, SHA-256 `9b8cfb915a79e6f3a5097739950dac42626ec50e7f6192e7b158b356dc04fe72` |
| Artifact retention | 14 days; expires `2026-09-14T23:33:23Z` |

PR #2's body still names an earlier subject, `26e57b82f6230ae3528583d7829a2270ad89acfd`,
from an intermediate review cycle. It is historical text, not the final-head binding. The PR and
Actions event metadata above are authoritative for the final head; the body is not edited
retroactively.

The predecessor TASK-0029 remains an immutable `BLOCKED` history on
`codex/formal-ci-canary@6d8184f`: its subject
`dabba1047156bf61b19fda33dca6902afd767f5b` retained two Policy 2.1.0 V1 failures at the
600-second coverage bound and a successful isolated 579.8-second diagnostic. TASK-0030's Policy
2.2.0 timeout remediation and the successful PR #2 run removed that runtime blocker; they do not
rewrite TASK-0029's failures or make its old evidence current.
