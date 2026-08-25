# TASK-0014 focused integration action request 001

- Action file: `action-focused-integration-001.json`
- Canonical action SHA-256: `997bdb20ca1ca1a9e374df0f6797484a20b209455ed850cf21cbd90578538c43`
- Base commit: `3c87fc931329c903e2d22feff88a4fd4966718b6`
- Subject commit: `62df888baf2afa858ef096949ab1ade861cef7ea`
- Exact outer argv: `D:\Repos\harness-model\.venv\Scripts\python.exe -m pytest -q tests/integration/test_mutation_runner_contract.py`
- Working directory: `D:\Repos\harness-model`
- Shell: `false`
- Expiry: `2026-08-26T00:00:00Z`
- Outer-command budget: `1`
- Mutation-runner budget: `1`
- System temporary mutation-scratch-root budget: `1`
- Detached-worktree budget: `5`, serially beneath the one scratch root
- Retained task-local mutation-evidence record-root budget: `1`
- Frozen pre-existing TASK-0014 record IDs: `[]`
- Frozen pre-existing system-temp `aiflow-mutation-*` direct children: `[]`

The implementation subject is locally committed and synchronized. Safe checks
completed without invoking the production integration branch: 579 unit tests
passed with three platform symlink skips; the new module reached 92% branch-aware
coverage; Ruff, format, Mypy, contract validation, scope validation, CLI smoke,
and diff checks passed. Independent review confirmed that current historical
tasks on older subjects do not suppress TASK-0014 production mode, while another
head-bound active task still does.

The action binds the current frozen spec, Policy, classification input, subject,
mutation-evidence source, fixed runner, integration test, manifest, and evidence
schema hashes. It permits one production-record collection that retains one
ignored task-local evidence record while the fixed runner creates and removes
only its one contained system-temp scratch root and five serial worktrees.

This request is not an approval and authorizes no execution. Before the command
starts, the exact canonical SHA above requires explicit user approval and a
task-local `status: started` use record. Full V1, any retry, push, merge, deploy,
task close, or deletion of the retained task-local record remains unauthorized.
