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
single-maintainer repository is not deadlocked; AI Flow approvals and separate external-action
authorization remain independent requirements.

The workflow uses only `contents: read`, receives no secrets, and runs on `pull_request`, not `pull_request_target`. It verifies and gates the PR head, uploads runner-temp evidence and redacted logs, and performs no merge, push, deployment, approval, or branch-protection mutation.

For a formal `pull_request` run, checkout continues to use the event head SHA. After governance detection only, the formal path creates or overwrites a runner-local branch named from `github.head_ref`, with that same event SHA as its explicit start point; the bootstrap path is unchanged. The workflow validates the branch name with `git check-ref-format`, checks the SHA before binding, then checks both the symbolic branch and SHA afterward. It does not fetch or push, treats `github.head_ref` only as the local branch name rather than commit authority, and never substitutes it for the event SHA.

For that same formal path only, the `Verify` and `Gate` step explicitly set Python's `TMPDIR` to `${{ runner.temp }}`. This places the run directory, evidence, Gate output, and uploaded artifacts under one runner-managed temporary root, while retaining the CLI's existing strict-descendant and output-containment checks unchanged. Bootstrap and all other workflow steps keep their prior environment and behavior.

While the pull request's base commit contains `.ai/bootstrap-mode.yaml` with the exact canonical lines `mode: bootstrap_auto` and `status: active`, the same required `ai-quality-gate` job validates and consumes `uv.lock`, runs one full branch-coverage pytest pass with an 85 percent total threshold, enforces 90 percent diff coverage and `git diff --check` over the PR range, and then runs Ruff, format, and mypy. It deliberately skips task resolution and AI Flow `verify`/`gate`. The base commit is authoritative: the owner-authorized PR that removes or disables the marker still uses bootstrap checks, while a PR cannot activate bootstrap merely by adding the marker to its head. After the exit PR merges, subsequent PRs use the normal AI Flow path without changing the required check name or branch-protection rule. The job has a 90-minute bound because the active V2 fixed checks may consume 68.5 minutes at their declared serial limits; the remainder covers locked installation, Gate evaluation, diagnostics, and normal runner variance without weakening any check or threshold.

The workflow file is not proof that enforcement is active. Before claiming the repository is protected, run it on a real pull request, configure `ai-quality-gate` as required, and retain platform evidence that the target branch rejects direct/force pushes and bypasses outside the named emergency roles.

The historical bootstrap mode never granted push, merge, deployment, deletion, secret-export, or paid-call authority. The project owner has now ended bootstrap; future PRs use formal AI Flow task resolution, verification, and Gate while the same external-action and platform controls remain in force.

## Formal-mode canary evidence

A post-bootstrap pull request is accepted as a live formal-mode canary only when the required
`ai-quality-gate` succeeds for its exact final head. The matching run must show `Resolve task`,
`Verify and Gate`, and `Upload AI Flow diagnostics` succeeding on the formal path while
`Bootstrap quality checks` is skipped. Its diagnostics artifact must be named
`ai-flow-<TASK-ID>` and is retained for 14 days for investigation. The pull request, merge commit,
final-head check, and Actions run metadata are the durable platform record; the artifact is not.

Do not commit the run URL back into the same governed pull request. That changes the final head,
invalidates the previous run's subject binding, and requires a new successful check. Record the
final task, head, and run in a later governed document or another immutable external audit record.
If the base or head changes before merge, accept only a new successful check for the resulting
exact head.

The first observed canary was [PR #2](https://github.com/MaginaLW/harness-model/pull/2):

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
