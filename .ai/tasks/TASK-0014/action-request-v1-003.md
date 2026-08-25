# TASK-0014 full local V1 rerun action request 003

- Action file: `action-v1-verification-003.json`
- Canonical action SHA-256: `e3c7c7db59dad3c7f993b80be4afc353e2facddc0dfc9628e92944cfd9d43c74`
- Supersedes unrecorded/unexecuted action: `1abc3543c48f28268aa6f7f1e3bb14a48e226799ab595a7c6fb3d626faa7417c`
- Base commit: `3c87fc931329c903e2d22feff88a4fd4966718b6`
- Subject commit: `e9bb833481659ec2ed9139dbb05539e8a822314d`
- Exact outer argv: `D:\Repos\harness-model\.venv\Scripts\python.exe -m aiflow verify TASK-0014 --actor task0014-independent-verifier`
- Working directory: `D:\Repos\harness-model`
- Shell: `false`
- Expiry: `2026-08-26T12:00:00Z`
- Outer-command budget: `1`
- Mutation-runner budget: `2`
- System temporary mutation-scratch-root budget: `2`
- Detached-worktree budget: `10` total, five serial worktrees per root
- Retained task-local mutation-evidence record-root budget: `2`
- Frozen pre-existing TASK-0014 record IDs: `[MUTRUN-20260825T022439Z-d03f8977df9451a5, MUTRUN-20260825T042238Z-c9260f9dbec67a77, MUTRUN-20260825T042638Z-4d06bbcaca45787d]`
- Frozen pre-existing system-temp `aiflow-mutation-*` direct children: `[]`

Action 002 was rejected during preflight before its approval was recorded and
before any use receipt or outer-command launch. It incorrectly required the
production selector to return H2 while the task was still
`WAITING_FOR_FINAL_REVIEW`; the selector deliberately enables production only in
`IMPLEMENTING` or `VERIFYING`.

This corrected action keeps the pre-launch state at
`WAITING_FOR_FINAL_REVIEW`. The one exact outer command must first record
`verification_restarted -> VERIFYING`; after that transition and before either
authorized integration collection, the production selector must return H2 or fail
closed without a mutation-runner invocation. All source/test hashes, budgets,
record-set constraints, containment rules, and external-action prohibitions remain
unchanged.

This request is not an approval and authorizes no execution. Before the command
starts, the exact canonical SHA above requires a new explicit user approval and a
separate task-local `status: started` use record. A passing rerun will still require
a new H2 implementation review and separate code/documentation approval. Focused
retry, CI V1, a second outer invocation, further documentation/state projection,
push, merge, deploy, task close, code approval, and deletion of retained records
remain unauthorized.
