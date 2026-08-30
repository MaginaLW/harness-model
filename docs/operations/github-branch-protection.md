# GitHub branch protection checklist

Repository administrators must configure these settings in GitHub; the workflow cannot change its own protection rules.

- Require the `ai-quality-gate` check before merge.
- Require the pull-request branch to be current with its base branch.
- Disallow direct pushes and force pushes to protected branches.
- Limit bypass permission to named repository administrators or emergency roles.
- Require every bypass to carry a separate, retained audit record with actor, reason, affected commit, and follow-up verification.

The workflow uses only `contents: read`, receives no secrets, and runs on `pull_request`, not `pull_request_target`. It verifies and gates the PR head, uploads runner-temp evidence and redacted logs, and performs no merge, push, deployment, approval, or branch-protection mutation.

While the pull request's base commit contains `.ai/bootstrap-mode.yaml` with the exact canonical lines `mode: bootstrap_auto` and `status: active`, the same required `ai-quality-gate` job runs the full pytest, Ruff, format, and mypy checks but deliberately skips task resolution and AI Flow `verify`/`gate`. The base commit is authoritative: the owner-authorized PR that removes or disables the marker still uses bootstrap checks, while a PR cannot activate bootstrap merely by adding the marker to its head. After the exit PR merges, subsequent PRs use the normal AI Flow path without changing the required check name or branch-protection rule.

Bootstrap mode never grants push, merge, deployment, deletion, secret-export, or paid-call authority. That retained boundary is enforced by explicit human authorization and available platform or branch-protection controls; bootstrap does not add a task-free command interceptor or treat the existing optional AI Flow wrapper as one.
