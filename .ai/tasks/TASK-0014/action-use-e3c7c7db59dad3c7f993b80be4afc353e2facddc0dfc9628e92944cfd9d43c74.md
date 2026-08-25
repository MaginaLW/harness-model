# TASK-0014 full local V1 rerun action use

- Transaction ID: `TASK-0014-V1-003`
- Task: `TASK-0014`
- Decision unit: `DU-001`
- Action type: `local_v1_verify`
- Retry instance: `full_v1_rerun`
- Action SHA-256: `e3c7c7db59dad3c7f993b80be4afc353e2facddc0dfc9628e92944cfd9d43c74`
- Status: `completed`
- Started at: `2026-08-25T10:32:18Z`
- Completed at: `2026-08-25T10:43:44Z`
- Expires at: `2026-08-26T12:00:00Z`
- Approval consumed on launch: `true`
- Reusable after launch or interruption: `false`

## Bound execution

- Working directory: `D:\Repos\harness-model`
- Shell: `false`
- Exact argv: `D:\Repos\harness-model\.venv\Scripts\python.exe -m aiflow verify TASK-0014 --actor task0014-independent-verifier`
- Outer-command budget: `1`
- Mutation-runner budget: `2`
- System temporary mutation-scratch-root budget: `2`
- Detached-worktree budget: `10` total, five serial worktrees per root
- Retained task-local record-root budget: `2`

## Frozen bindings

- Spec SHA-256: `a38fe5af6458a3c7f495616f96243d52347a08027bf0d8acde6c668893c0e9d9`
- Policy SHA-256: `f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`
- Classification input SHA-256: `cebbc4df4fe06a50521d0f3246d968dcc1660343d041570d09fa4f289a38e6d0`
- Base commit: `3c87fc931329c903e2d22feff88a4fd4966718b6`
- Subject commit: `e9bb833481659ec2ed9139dbb05539e8a822314d`
- Mutation-evidence source SHA-256: `364f158fe062e471cba7efedc3aa124459eca37362ed56f91d5349e200e87771`
- Runner source SHA-256: `4b227bf5785513cd757567b7b20d3d1e64680909340eec26a5817f80697372fd`
- Integration-test SHA-256: `9694c224f4c00c1996e8b89a315d47f6ed9f18dcc1edc10d78b3437af0b954e1`
- Mutation-evidence unit-test SHA-256: `604224c4ba1aa633991ef755bdc9f222867f2b3a2124fd39e130ed2cc01ce5a7`
- Contract unit-test SHA-256: `ff2f02b09016928cc50ec07ea02890384e38a697f4aa13da08475ba1ddc3bab6`
- Manifest SHA-256: `1dac9624e5a221784d56dc189e5bb225662334b550238b13ecf7587c96d277c0`
- Mutation-evidence schema SHA-256: `3cb47f1053ffb45902e74ec0a603d4b1569c8aeb8efe93cc3763b2b20c2c9a34`

## Preflight

- CLI-normalized canonical action SHA, expiry, bindings, source/test hashes, and recorded user approval are current.
- Recorded approval timestamp: `2026-08-25T10:31:55Z`.
- No previous use record existed for this action SHA-256.
- Action 002 (`1abc3543c48f28268aa6f7f1e3bb14a48e226799ab595a7c6fb3d626faa7417c`) was rejected before CLI approval recording, use-receipt creation, or launch and remains unexecuted.
- Repository `HEAD` and task subject both matched `e9bb833481659ec2ed9139dbb05539e8a822314d`.
- Task state was `WAITING_FOR_FINAL_REVIEW`; classification and approvals were fresh/current and H1 evidence was stale as expected after H2 synchronization.
- The exact outer command must record `verification_restarted -> VERIFYING` before any check execution; only then, before each integration collection, must the production selector equal H2 or fail closed without invoking the runner.
- Worktree changes were limited to TASK-0014 governance files.
- Frozen sorted pre-existing TASK-0014 task-local record IDs: `[MUTRUN-20260825T022439Z-d03f8977df9451a5, MUTRUN-20260825T042238Z-c9260f9dbec67a77, MUTRUN-20260825T042638Z-4d06bbcaca45787d]`.
- Frozen pre-existing system-temp `aiflow-mutation-*` direct children: `[]`.
- Pre-launch Git status blob SHA-1 before this use receipt: `996a51b6761b3b68cf5f531fbcbe3dce9be30120`.
- Pre-launch Git-worktree registry blob SHA-1: `ca1fe61df884557b4b8ac83aa34536d868b36c42`.
- The outer command had not started when this record was created.
- No retry, CI V1, focused integration, second outer invocation, push, merge, deploy, task close, code approval, further documentation/state projection, or deletion of retained task-local evidence is authorized.

## Result

- Outer-command invocations: `1`.
- Mutation-runner invocations: `2`.
- System temporary mutation-scratch roots created and removed: `2`.
- Detached mutation worktrees created and removed serially: `10`, five per root.
- Newly retained task-local record roots: `2`.
- Command exit code: `0`.
- Verification conclusion and state: `passed`; `WAITING_FOR_FINAL_REVIEW`.
- Verification run directory: `.ai/tasks/TASK-0014/logs/run-20260825T103335143305Z/`.
- Task evidence ref: `.ai/tasks/TASK-0014/evidence.json`.
- Task evidence file SHA-256: `2fab98ec7a0f05e75b2873df592e7dfbd3ded8983ba51f5b8098aeb0a19933e1`.
- Canonical task evidence SHA-256: `d85f93d45a8453c01cd9e0b87158e38d28fa94249ecff29024fc6f947fdac240`.
- Evidence generated at: `2026-08-25T10:43:14Z`.
- Required checks: `10/10 passed` in Policy order.
- Unit tests: `579 passed, 3 skipped in 19.97s`.
- Regression tests: `871 passed, 4 skipped in 227.62s`.
- Coverage tests: `871 passed, 4 skipped in 328.21s`; line coverage `5511/6133` (`89.86%`), branch coverage `1631/2070` (`78.79%`).
- Coverage XML SHA-256: `9f5f434e12a5e767038aaf1867d4e54be473cb64e03037ded2f2870aba167ff4`.
- Python changed-line coverage: `92%` (`317/342` lines covered; threshold `90%`).
- New record-set difference: `[MUTRUN-20260825T103538Z-7e1b13c446467f3f, MUTRUN-20260825T103950Z-edac5c827d6b4b2f]`.

### Regression collection record

- Record ID: `MUTRUN-20260825T103538Z-7e1b13c446467f3f`.
- Evidence ref: `.ai/tasks/TASK-0014/logs/MUTRUN-20260825T103538Z-7e1b13c446467f3f/targeted-mutation/evidence.json`.
- Evidence file SHA-256: `a793af37249677ee1a12aa1b9b2ae5754e679e666a7dcc196c42817af7bd0907`.
- Canonical mutation-evidence SHA-256: `6d2816836c7cb100ea0c7bb2ce57b8b1fc70537403cfa03fa568d552a03d8228`.
- `MUT-V2-001` log ref/hash: `.ai/tasks/TASK-0014/logs/MUTRUN-20260825T103538Z-7e1b13c446467f3f/targeted-mutation/logs/MUT-V2-001.json` / `80611f900cd2efe3cda1a25cd5cb85bb0502e72c1b9a12bd486d097b083086a4`.
- `MUT-V2-002` log ref/hash: `.ai/tasks/TASK-0014/logs/MUTRUN-20260825T103538Z-7e1b13c446467f3f/targeted-mutation/logs/MUT-V2-002.json` / `d659b46176c709724cfd2571bab1acb20498dc4bd328c8df4290b14ed4eb31c7`.
- `MUT-V2-003` log ref/hash: `.ai/tasks/TASK-0014/logs/MUTRUN-20260825T103538Z-7e1b13c446467f3f/targeted-mutation/logs/MUT-V2-003.json` / `b7e607a501cbb1001282c4e532704e3ae492e9bdd66e206712411b727d6f38ec`.
- `MUT-V2-004` log ref/hash: `.ai/tasks/TASK-0014/logs/MUTRUN-20260825T103538Z-7e1b13c446467f3f/targeted-mutation/logs/MUT-V2-004.json` / `7bf4d68e6bb3fcd6dca8056ce3b844fcd0987cc1b1ae6bc782dcfa9ed1dadf63`.
- `MUT-V2-005` log ref/hash: `.ai/tasks/TASK-0014/logs/MUTRUN-20260825T103538Z-7e1b13c446467f3f/targeted-mutation/logs/MUT-V2-005.json` / `e981f54704302abf50448e4570a5a07382234b81cf6a55858aedd4f19ed0f4c1`.
- Raw/outcome summary: baseline `(0,0,0,0,0)`, mutant `(1,1,1,1,1)`, no timeout/reason, all `killed`, uncovered `[]`, main tree unchanged.

### Coverage collection record

- Record ID: `MUTRUN-20260825T103950Z-edac5c827d6b4b2f`.
- Evidence ref: `.ai/tasks/TASK-0014/logs/MUTRUN-20260825T103950Z-edac5c827d6b4b2f/targeted-mutation/evidence.json`.
- Evidence file SHA-256: `5ab754dcc5cf445ad6f3d8f3f6fff3f8b5800c3fd796d5b156b6aa68335969a5`.
- Canonical mutation-evidence SHA-256: `42d565697b6c0a91902382e743c6d87aa9d376011eeb09e739377e8799e6876a`.
- `MUT-V2-001` log ref/hash: `.ai/tasks/TASK-0014/logs/MUTRUN-20260825T103950Z-edac5c827d6b4b2f/targeted-mutation/logs/MUT-V2-001.json` / `c5f3e7263b4fccb9c2cdde9bfe77959cee756c456a053dee9825e850232ee209`.
- `MUT-V2-002` log ref/hash: `.ai/tasks/TASK-0014/logs/MUTRUN-20260825T103950Z-edac5c827d6b4b2f/targeted-mutation/logs/MUT-V2-002.json` / `b4ba378f5abc161b8ed65e777cadd66f3dd0d7aef88674e744283eca0b6115a3`.
- `MUT-V2-003` log ref/hash: `.ai/tasks/TASK-0014/logs/MUTRUN-20260825T103950Z-edac5c827d6b4b2f/targeted-mutation/logs/MUT-V2-003.json` / `7a070436e280df5fc752c363c5c42fc539157c1113406eeb8e0b16eda2199658`.
- `MUT-V2-004` log ref/hash: `.ai/tasks/TASK-0014/logs/MUTRUN-20260825T103950Z-edac5c827d6b4b2f/targeted-mutation/logs/MUT-V2-004.json` / `98224d8c882743783f69e7c4ef6c8f07e7db961592febaea6cdf5769327684a2`.
- `MUT-V2-005` log ref/hash: `.ai/tasks/TASK-0014/logs/MUTRUN-20260825T103950Z-edac5c827d6b4b2f/targeted-mutation/logs/MUT-V2-005.json` / `06bf4b23c0f4fdefc0f9c754c5ff440b1072bdad743741431688b66951ab2ac2`.
- Raw/outcome summary: baseline `(0,0,0,0,0)`, mutant `(1,1,1,1,1)`, no timeout/reason, all `killed`, uncovered `[]`, main tree unchanged.

### Postflight

- Pre-launch Git status blob SHA-1 before this use receipt: `996a51b6761b3b68cf5f531fbcbe3dce9be30120`.
- Post-verification Git status blob SHA-1: `5156c0bb01e44a2667377138f7bdf3d0b0f40e9a`; the difference is the permitted V1 governance/evidence output and the pre-created use receipt.
- Pre/post Git-worktree registry blob SHA-1: `ca1fe61df884557b4b8ac83aa34536d868b36c42`.
- Both production records were public-loaded and independently reported `main_tree_unchanged: true`; bound source, test, manifest, and schema hashes remained unchanged.
- Residual system-temp `aiflow-mutation-*` roots: `0`.
- Residual mutation worktrees: `0`; the five pre-existing non-mutation worktrees were unchanged.
- Cleanup status: `completed` for both transaction-created roots and all ten worktrees.
- All five retained mutation-evidence records are intentionally excluded by `.gitignore`; this receipt is the auditable hash index for the two new H2 records and does not claim their ignored JSON bodies survive another checkout or machine.
- This successful execution consumed the approval and it is not reusable.
- Action 002 remains unapproved, unexecuted, and without a use receipt.
- No retry, CI V1, focused integration, second outer invocation, push, merge, deploy, task close, code approval, further documentation/state projection, or deletion of retained task-local evidence was executed.
