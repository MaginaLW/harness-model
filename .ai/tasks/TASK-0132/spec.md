# Task Specification

## 目标

Accept the target's existing content-identical pretest rebuild without accepting output drift, and keep native verification subprocess temporary material in the caller-selected project directory so full verification can run under the workspace boundary.

## 范围

Only src/aiflow/node_execution.py and src/aiflow/process_runner.py. The two prerequisites share one source-only verification candidate; companion regressions and documentation are already separate task-free baseline commits. Preserve existing checks, commands, timeouts, process guards, coverage thresholds and original native five mutations.

For Node, bind the exact rebuild rule in SEMANTIC_CONTRACT. Retain the first independently built full dist inventory as outputs.build_dist and the final inventory as outputs.dist. Immediately after successful fixed node_check and the successful primary V1 coverage-suite execution, enumerate safe dist and require equal complete canonical content (all paths, kinds, sizes, SHA-256) against the original build_dist before rebinding identity. Identify these two roles only by the exact primary argv of the fixed plan checks; ts_coverage check_ids alone are insufficient because its mapping-helper execution shares that check ID. The coverage mapping helper and all other phases retain full identity checks before execution and at final output validation. Read-only replay requires both inventories, their same content, and current final inventory identity; old semantic/material evidence is stale.

For native subprocesses, keep Policy's environment allow-list unchanged. Validate the first explicit parent TMPDIR, TEMP or TMP root before any directory creation or process launch: absolute, existing ordinary directory, no symlink/reparse ancestors. Invalid explicit roots reject without fallback or tempfile probing. With no explicit variable, preserve system-default root selection. Each execution exclusively creates one aiflow-check-* child of the validated root and supplies only the three fixed TMPDIR/TEMP/TMP roles in addition to existing roles. Never copy arbitrary caller environment, modify caller variables or add a new CLI/configuration surface. Retain these owned directories for inspection rather than deleting unknown work.

## 非目标

No installed V2 or Node CI activation, real target writes or target Policy, source-native mutation redesign, authorization-file/Policy-threshold changes, remote settings, model/WeChat execution, credentials, private material transfer, new sandbox or temporary-directory CLI. The actual acceptance Git clone and its sibling temporary root both stay within the selected project workspace; no outside temporary-directory exception is used.

## 验收条件

The existing ordinary-wheel pretest V0 red is independently confirmed from originals: build and check exited zero with confirmed cleanup, followed by failed verification before whitespace execution. After repair, both genuine pretest V0/V1 and original no-pretest lifecycles pass. Changed or additional dist is rejected after successful scripts. Rehashed evidence with missing build inventory, changed initial content, changed final identity or changed final content fails the read-only consumer.

Existing native temporary-root regressions fail before any OS tempfile write on the original runner. After repair, actual child tempfile.gettempdir and mkstemp stay under the explicitly selected root, two executions have distinct owned roots, parent environment remains identical, injected unrelated variables are absent, and relative/missing/file/symlink roots for each standard variable reject before mkdir/Popen. Policy cannot inject any of the temporary roles.

Run focused source tests, Ruff, format, strict mypy and whitespace, then current native V2 verification with complete pytest, both production coverage domains at 85% total and 90% diff, all required checks, five authorized native mutations, independent implementation review, same-verifier finalize and Gate. Keep original failures and actual support limits. Required remote CI remains separate from local verification and must pass before merge.

## 禁止动作

Do not modify original checkout WIP, agent-bridge, authorization files, remote settings, or global environment/ACLs. No deployment, deletion of existing work, paid calls, credentials export, force push or history rewrite. Source delivery is limited to the reviewed current candidate and standing authorization; no other refs or tags.

## 错误行为

Unknown or non-identical Node output, changed source/dependencies, missing/tampered originals or stale semantic inputs fail closed. Invalid explicit temporary roots must not fall back or create logs. Directory creation or process failure must not become PASS. Do not weaken or downgrade V2; unsupported capabilities remain blocked.

## 回滚

Normal scoped revert if needed; preserve task ledger, reviews, failed evidence and owned test materials. No target resources or unrelated work need removal.
