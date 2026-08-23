# TASK-0013 focused integration rerun action use

- Transaction ID: `TASK-0013-FOCUSED-002`
- Task: `TASK-0013`
- Decision unit: `DU-001`
- Action type: `focused_integration`
- Action SHA-256: `659ed5eed4b25a1daf73aa636219da690fcc5cbddf1c416a9ad2aa5dc4a2ab40`
- Status: `completed`
- Started at: `2026-08-23T23:52:13Z`
- Completed at: `2026-08-23T23:53:03Z`
- Expires at: `2026-08-25T00:00:00Z`
- Approval consumed: `true`
- Reusable: `false`

## Bound execution

- Working directory: `D:\Repos\harness-model`
- Shell: `false`
- Exact argv: `D:\Repos\harness-model\.venv\Scripts\python.exe -m pytest -q tests/integration/test_mutation_runner_contract.py`
- Runner invocation budget: `1`
- Temporary-root budget: `1`
- Detached-worktree budget: `5`

## Frozen bindings

- Spec SHA-256: `949aee0bca38d4dc5977d3a3a289b463b8f27fb666f6f67d416d1fb3f5a4a281`
- Policy SHA-256: `f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`
- Classification input SHA-256: `14b746b5cf4e5553e896c9863c7cb156133919dfbe818bb1eacd581d96b6f6bb`
- Base commit: `dc49293936ae8f705b7a474dc5c7b0ac0c981865`
- Subject commit: `dc49293936ae8f705b7a474dc5c7b0ac0c981865`
- Runner source SHA-256: `4b227bf5785513cd757567b7b20d3d1e64680909340eec26a5817f80697372fd`
- Integration test SHA-256: `2084d3f76007c7579f2b06d3ce2a62f16bfa3efa05dec78ec7c1d440c61883e1`
- Manifest SHA-256: `1dac9624e5a221784d56dc189e5bb225662334b550238b13ecf7587c96d277c0`

## Preflight

- Canonical action SHA-256, expiry, bindings, three file hashes, and recorded user approval were current.
- No previous use record existed for this action SHA-256.
- Repository `HEAD` matched the bound subject commit.
- The separately approved cleanup transaction completed successfully and its exact residual root was absent.
- No pre-existing `aiflow-mutation-*` directory existed directly under the system temporary directory.
- The command had not started when this record was written.
- No push, merge, deploy, full test suite, coverage run, or second runner invocation is authorized by this transaction.

## Result

- Outer-command invocations: `1`
- Runner invocations: `1`
- Temporary roots created: `1`
- Detached worktrees created and removed serially: `5`
- Command exit code: `0`
- Pytest result: `1 passed in 10.58s`
- Baseline detector exit codes: `(0, 0, 0, 0, 0)`.
- Mutant detector exit codes: `(1, 1, 1, 1, 1)`.
- Probe timeouts: none.
- Probe or aggregate reason codes: none.
- Main-tree controlled hashes and status: unchanged as asserted by the integration contract.
- Pre/post main-worktree status Git blob hash: `14b219fc870bf4293987ffb2bf1a531a616c3e7f`.
- Pre/post Git-worktree registry blob hash: `877a840b041e58fe1c3317ac0415b4804cc8a404`.
- Residual `aiflow-mutation-*` roots after command: `0`.
- Cleanup status: `completed`; all transaction-created scratch directories, detached worktrees, hooks directory, and the one temporary root were removed.
- This successful execution consumed the approval; it is not reusable.
- No push, merge, or deploy was executed.
