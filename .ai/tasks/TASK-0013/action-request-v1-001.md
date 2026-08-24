# TASK-0013 full V1 action request 001

- Action file: `action-v1-verification-001.json`
- Canonical action SHA-256: `f647e210f7442ae9bb8fea27b01fdfa34ace02c18a364f1f039140bc31cd8f85`
- Subject commit: `531d9bdf1c0daebbac547e05bfcbf941534b22e7`
- Exact outer argv: `D:\Repos\harness-model\.venv\Scripts\python.exe -m aiflow verify TASK-0013 --actor task0013-independent-verifier`
- Expiry: `2026-08-25T00:00:00Z`
- Outer-command budget: `1`
- Mutation-runner budget: `2`
- Temporary-root budget: `2`
- Detached-worktree budget: `10` total, five serial worktrees per root

The two mutation-runner invocations are the only expected consequences of the
V1 `regression_tests` and `coverage_xml` full-pytest checks. A passing run must
execute and fully clean both; any failure consumes the action and permits no
automatic retry. The action also binds the current runner source, integration
test, manifest, frozen spec, Policy, classification input, base commit, and
final subject hashes. There are currently zero pre-existing matching temporary
roots. This request record is not an approval and authorizes no execution.

## Outcome

The user approved this action and the one authorized outer command executed.
The action is consumed and non-reusable; its use record is
`action-use-f647e210f7442ae9bb8fea27b01fdfa34ace02c18a364f1f039140bc31cd8f85.md`.
V1 failed because Ruff format found one missing blank line and changed-line
coverage was `87%`. Both full-pytest checks nevertheless passed with
`786 passed, 3 skipped`, and both mutation roots cleaned completely.
Remediation subsequently passed 52 focused unit tests, Ruff format/check, mypy,
and a unit-only `90.6%` changed-line coverage probe. This request authorizes no
retry; a new subject-bound action approval is required.
