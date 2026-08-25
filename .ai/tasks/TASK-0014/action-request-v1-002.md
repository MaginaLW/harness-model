# TASK-0014 full local V1 rerun action request 002

- Action file: `action-v1-verification-002.json`
- Canonical action SHA-256: `1abc3543c48f28268aa6f7f1e3bb14a48e226799ab595a7c6fb3d626faa7417c`
- Base commit: `3c87fc931329c903e2d22feff88a4fd4966718b6`
- Subject commit: `e9bb833481659ec2ed9139dbb05539e8a822314d`
- Exact outer argv: `D:\Repos\harness-model\.venv\Scripts\python.exe -m aiflow verify TASK-0014 --actor task0014-independent-verifier`
- Working directory: `D:\Repos\harness-model`
- Shell: `false`
- Expiry: `2026-08-26T00:00:00Z`
- Outer-command budget: `1`
- Mutation-runner budget: `2`
- System temporary mutation-scratch-root budget: `2`
- Detached-worktree budget: `10` total, five serial worktrees per root
- Retained task-local mutation-evidence record-root budget: `2`
- Frozen pre-existing TASK-0014 record IDs: `[MUTRUN-20260825T022439Z-d03f8977df9451a5, MUTRUN-20260825T042238Z-c9260f9dbec67a77, MUTRUN-20260825T042638Z-4d06bbcaca45787d]`
- Frozen pre-existing system-temp `aiflow-mutation-*` direct children: `[]`

H2 `e9bb833481659ec2ed9139dbb05539e8a822314d` adds the audited Chapter 11.4
documentation/state projection and committed H1 governance records without
changing the bound source, tests, manifest, or schema. Synchronizing the task to
H2 correctly made the H1 V1 evidence and `REV-0002` historical. The prior focused
and local V1 actions are completed, consumed, and non-reusable.

This action authorizes one complete local V1 verification rerun. The exact outer
command restarts verification from `WAITING_FOR_FINAL_REVIEW`. Under the frozen V1
plan, only `regression_tests` and `coverage_xml` may collect the permanent
integration test. Each must select production mode once, yielding exactly two new
task-local records, two runner invocations, two contained temporary roots, and ten
serial worktrees total. Passing receipt collection must public-load both new
records and reject any synthetic seam result.

This request is not an approval and authorizes no execution. Before the command
starts, the exact canonical SHA above requires a new explicit user approval and a
separate task-local `status: started` use record. A passing rerun will still require
a new H2 implementation review and separate code/documentation approval. Focused
retry, CI V1, a second outer invocation, further documentation/state projection,
push, merge, deploy, task close, code approval, and deletion of retained records
remain unauthorized.

## Preflight outcome

Rejected before CLI approval recording, use-receipt creation, or outer-command
launch. The frozen condition requiring both pre-launch
`WAITING_FOR_FINAL_REVIEW` and a pre-launch H2 production-selector result is
unsatisfiable because the selector deliberately enables production only in
`IMPLEMENTING` or `VERIFYING`. Action 002 remains unexecuted and is superseded by
the corrected action 003, which moves the selector check after the exact outer
command records `verification_restarted -> VERIFYING` and before integration
collection.
