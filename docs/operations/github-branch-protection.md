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

While the pull request's base commit contains `.ai/bootstrap-mode.yaml` with the exact canonical lines `mode: bootstrap_auto` and `status: active`, the same required `ai-quality-gate` job validates and consumes `uv.lock`, runs one full branch-coverage pytest pass with an 85 percent total threshold, enforces 90 percent diff coverage and `git diff --check` over the PR range, and then runs Ruff, format, and mypy. It deliberately skips task resolution and AI Flow `verify`/`gate`. The base commit is authoritative: the owner-authorized PR that removes or disables the marker still uses bootstrap checks, while a PR cannot activate bootstrap merely by adding the marker to its head. After the exit PR merges, subsequent PRs use the normal AI Flow path without changing the required check name or branch-protection rule. The job has a 35-minute bound because retained V1/V2 evidence includes successful verification runs near 14.4 and 20.5 minutes, excluding checkout, locked installation, and Gate overhead.

The workflow file is not proof that enforcement is active. Before claiming the repository is protected, run it on a real pull request, configure `ai-quality-gate` as required, and retain platform evidence that the target branch rejects direct/force pushes and bypasses outside the named emergency roles.

The historical bootstrap mode never granted push, merge, deployment, deletion, secret-export, or paid-call authority. The project owner has now ended bootstrap; future PRs use formal AI Flow task resolution, verification, and Gate while the same external-action and platform controls remain in force.

## First formal-mode pull request evidence

The first pull request after bootstrap exit is accepted as a live formal-mode canary only when its
final head has a successful required `ai-quality-gate` check and the run shows `Resolve task`,
`Verify and Gate`, and `Upload AI Flow diagnostics` on the normal path while `Bootstrap quality
checks` is skipped. The diagnostics artifact must be named `ai-flow-<TASK-ID>`; it is retained for
14 days for investigation, whereas the pull request and required check remain the durable platform
record.

Record the task ID, final head SHA, and matching CI run URL in the pull request body. Do not commit
that run URL back into the governed file in the same pull request: doing so creates a new subject,
invalidates the old run's binding, and starts another run. Updating only the pull request body does
not change the governed head. If the base branch or final head changes, require a new successful
check for that exact head before treating the canary as passed.
