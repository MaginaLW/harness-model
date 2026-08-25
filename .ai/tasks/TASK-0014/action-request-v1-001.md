# TASK-0014 full local V1 action request 001

- Action file: `action-v1-verification-001.json`
- Canonical action SHA-256: `5aacdcd307e58560328646d34d272e176d4d076c8f66229084e2afb2cbaf11a4`
- Base commit: `3c87fc931329c903e2d22feff88a4fd4966718b6`
- Subject commit: `62df888baf2afa858ef096949ab1ade861cef7ea`
- Exact outer argv: `D:\Repos\harness-model\.venv\Scripts\python.exe -m aiflow verify TASK-0014 --actor task0014-independent-verifier`
- Working directory: `D:\Repos\harness-model`
- Shell: `false`
- Expiry: `2026-08-26T00:00:00Z`
- Outer-command budget: `1`
- Mutation-runner budget: `2`
- System temporary mutation-scratch-root budget: `2`
- Detached-worktree budget: `10` total, five serial worktrees per root
- Retained task-local mutation-evidence record-root budget: `2`
- Frozen pre-existing TASK-0014 record IDs: `[MUTRUN-20260825T022439Z-d03f8977df9451a5]`
- Frozen pre-existing system-temp `aiflow-mutation-*` direct children: `[]`

The separately approved focused transaction completed successfully and consumed
its action. Its one public recorder invocation produced the frozen pre-existing
record above; all five baseline/mutant exit pairs were `0/1`, all outcomes were
`killed`, uncovered was empty, and the mutation scratch root and five worktrees
were removed. Independent read-only receipt review approved those facts.

This action authorizes one complete local V1 verification. Under the frozen V1
plan, only `regression_tests` and `coverage_xml` may collect the permanent
integration test. Each must select production mode once, yielding exactly two
new task-local records, two runner invocations, two contained temporary roots,
and ten serial worktrees total. Passing receipt collection must public-load both
new records and reject any synthetic seam result.

This request is not an approval and authorizes no execution. Before the command
starts, the exact canonical SHA above requires a new explicit user approval and
a separate task-local `status: started` use record. The consumed focused action
cannot be reused. CI V1, retries, push, merge, deploy, task close, code approval,
documentation completion projection, and deletion of retained records remain
unauthorized.
