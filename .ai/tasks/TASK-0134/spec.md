# Task Specification

## 目标

Add a closed installed-engine mutation primitive that executes and independently replays five fixed probes against the ordinary wheel bytes, without enabling public Node V2 or CI.

## 范围

Only src/aiflow/installed_mutations.py and src/aiflow/installed_probe.py implement behavior. The separately task-free companion tests and design precede this source candidate. Preserve subsequent TASK-0133 governance records by normal merge without rewriting their contents; these records are carried history, never authority for this new task.

Follow docs/superpowers/specs/installed-engine-governance-mutations.md at the frozen baseline. Reuse existing installed inventories, budgets, copies, generic action normalization/approval matching, task consumption lock, Windows Job process execution and four compatible native AST operators. Do not change native mutation behavior. The installed 001 operator retains the complete extras declaration and positive control, relaxing only the unique fixed comparison to admit exactly the missing-targeted alternative. Reject ambiguous, unsupported or unrelated AST shapes and preserve outside-target AST.

Expose only the declared immutable InstalledMutationInputs/InstalledMutationReference and prepare_installed_mutations(root, task_id, verifier_actor), record_installed_mutations(root, task_id, verifier_actor, expected_inputs_sha256), replay_installed_mutations(root, reference, current) boundaries. Preparation validates current IMPLEMENTING native V2 task, spec approval, classification, distinct actual actor labels, current verifier context and ordinary installed materials. Its canonical inputs bind all task/version facts, full installed distribution/dependency/startup/RECORD bytes, supported interpreter/host identity, fixed probe/protocol/operator bytes. Preparation consumes nothing and creates no run.

Recording revalidates the complete inputs before consuming a new current single-use action of type installed_engine_mutation_v1 with action-installed-engine-mutation- prefix and exact canonical parameter_summary containing only kind/inputs_sha256. Under the existing shared task lock, atomically consume and reserve an exclusive launch claim. Any interrupted or failed attempt remains spent. Require only IMPLEMENTING, never manufacture VERIFYING or reopen blocked Node capability. Retain originals and namespace-specific completion; do not issue native targeted-mutation evidence.

Each fixed pair runs fresh independent verified closure copies, retaining original RECORD and explicit mutation overlay. Execute the bound Windows x64 CPython 3.11 interpreter with -I -S -B and a fresh empty -X pycache_prefix, fixed copied-site root, fixed environment and bounded complete Job receipts. Confirm loaded engine/dependency/probe origins and bytes and actual guard references. Explicitly trust the supported interpreter standard library, loader and OS; do not claim hermetic or hostile-code isolation.

The stdlib run_probe(probe_id) accepts only five fixed IDs. Fixed case order includes complete positive controls and designated negative controls. Report setup/call/teardown, observations and terminal exception traceback independently for each case, with complete terminal marker. Baseline requires exit0/all phases passed. A killed mutant requires exit1 and exactly its predeclared call-phase AssertionError at its bound source anchor, exact observations, other phases/cases passed and fully validated process/material facts. Exit1 alone is never killed. Survived, unrelated errors, changed loaded bytes, missing/ambiguous report, timeout/overflow/uncertain cleanup reject as unverified.

Pure replay accepts caller-validated current immutable inputs, then rereads bound inventories, namespace action/approval/consumption/launch/completion originals, canonical reports, receipts and raw streams. It derives all five outcomes with no subprocess, recovery, mkdir or writes. Authority callers collect live Git facts outside the pure reader and must preserve that precondition; do not deserialize current authority from untrusted evidence. Dataclasses grant no authority. Missing, stale or malformed inputs reject with bounded reason codes.

## 非目标

No public Node V2/CI activation, Policy/profile/evidence version change, lifecycle adapters, target repository write, remote settings, authentication framework, arbitrary plugin/probe/operator/command/executable/environment API, native runner redesign, threshold reduction or authorization-file change. No source checkout or editable engine substitutes for ordinary wheel acceptance. Real target/model/WeChat/native engine acceptance is outside this slice.

## 验收条件

Run task-free test-baseline red/green regressions and focused source tests, Ruff, format, strict mypy and whitespace. Build direct wheel and sdist/rebuilt wheel, verify both package modules, and use a real ordinary installation outside the source import path for five actual baseline/mutant pairs. Independently replay original reports/receipts/materials. Demonstrate survived, unrelated assertions/import/setup/teardown failures, missing/duplicate/extra report fields, wrong engine, stale source/material/context/task/action, process failure, timeout/overflow/cleanup rejection, concurrency and interrupted single-use consumption. Pure reader tests forbid all subprocess APIs/process wrappers and detect filesystem writes. Record actual failures; no fabricated or mocked full PASS.

Then complete current native V2 verification with complete pytest, both production branch coverage domains at85percent total and90percent diff, every required check, the five unchanged native mutations under a separately current action, independent implementation review, same-verifier finalization and Gate. Required exact-head remote CI remains distinct and must pass before merge. This new task's mutation execution action is separate from the installed primitive's fixture actions and from spent TASK-0132/TASK-0133 actions.

## 禁止动作

Preserve original checkout WIP, prior failed evidence, ignored owned materials and target work. No deployment, deletion of existing work, credentials/private export, model calls, paid calls, threshold reduction, repository-setting change, authorization edits, force push or rewritten history. All generated material, caches and temporary roots remain project-owned and preflighted.

## 错误行为

Reject unsupported hosts/layouts, source/editable substitutions, unknown probe/operator/case, ambiguous AST, unbound imported modules or stale cached bytecode, incomplete task/context/action authority, reused/concurrent/interrupted action, missing originals, mutation drift and uncertain process cleanup before any successful outcome. Failed recording retains evidence and spent authority; replay never retries or repairs.

## 回滚

Use a normal scoped revert while retaining append-only task/review/action/evidence history and owned acceptance originals. No target resource or unrelated work needs removal.
