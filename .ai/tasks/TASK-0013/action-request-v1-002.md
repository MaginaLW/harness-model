# TASK-0013 full V1 rerun action request 002

- Action file: `action-v1-verification-002.json`
- Canonical action SHA-256: `b9e57469cab7769667138fa3d46b383b446e03b099cd7c149c158b8113aad43a`
- Subject commit: `290254cc70791bcfa9895feab98154b411c2ef55`
- Exact outer argv: `D:\Repos\harness-model\.venv\Scripts\python.exe -m aiflow verify TASK-0013 --actor task0013-independent-verifier`
- Expiry: `2026-08-25T02:00:00Z`
- Outer-command budget: `1`
- Mutation-runner budget: `2`
- Temporary-root budget: `2`
- Detached-worktree budget: `10` total, five serial worktrees per root

The previous full-V1 action is failed, consumed, and non-reusable. Its two
full-pytest checks passed and cleaned both mutation roots, but Ruff format and
`87%` changed-line coverage failed the gate. The remediation subject bound here
contains the formatting correction and five additional mocked tests; focused
verification passed 52 unit tests, Ruff format/check, mypy, and a unit-only
`90.6%` changed-line coverage probe. An independent read-only remediation review
approved the change.

This new action binds the remediated unit test in addition to the runner,
integration test, manifest, frozen spec, Policy, classification input, base,
and final subject hashes. It authorizes no execution until the exact canonical
SHA above receives a new explicit user approval.
