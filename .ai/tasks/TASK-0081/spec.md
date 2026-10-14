# Task Specification

## 目标

Preserve the original failed verification evidence and the bytes needed to recover every cleanup target while reclaiming ignored local artifact storage in the owner-approved order.

DRAFT: the exact candidate inventory is now known, but complete recovery archive hashes, usable restore proof and protected inventory checks remain pending. verified_backup remains false. No deletion is permitted by this draft, and no final classification or specification is frozen yet.

## 范围

The exact inventory is .reasonix/repository-hygiene-20261014/plan.json (SHA-256 309123482f0c06dcd7f8d6fa94af16a0c85c15ad7d357e4312bc8971271b9eae). Its 19 deletion roots cover 255378 entries and 946719785 logical bytes: 12 pytest fixture/cache roots, five old mypy cache roots, one redundant publication checkout, and one duplicate ruff.exe. allowed_scope enumerates these roots and their descendants, only the 16 old metadata files named by old_metadata_delete_files, the new ignored work directory, and .ai/tasks/TASK-0081. The old hygiene directory itself is retained.

The exact roots are:

- .pytest_cache/confidence-contract-checks
- .pytest_cache/confidence-contract-r2
- .pytest_cache/construction
- .pytest_cache/construction-native-tmp
- .pytest_cache/ct1
- .pytest_cache/feedback-text-coverage
- .pytest_cache/task0076-contracts-failed-01
- .pytest_cache/task0076-full
- .pytest_cache/task0076-os-temp
- .pytest_cache/task0076-temp
- .pytest_cache/task0076-timeout-diagnose
- .pytest_cache/pr-feedback-independent.coverage
- .reasonix/execution-20261008/task0070-local-mypy-001/mypy-cache
- .reasonix/execution-20261008/task0070-local-mypy-002/mypy-cache
- .reasonix/execution-20261008/task0070-local-mypy-003/mypy-cache
- .reasonix/execution-20261008/task0070-local-mypy-005/mypy-cache
- .reasonix/execution-20261009/task0071-local-qa-001/mypy-cache
- .reasonix/execution-20261008/publication-a-status-002
- .reasonix/execution-20261008/task69-tools-001/venv/Scripts/ruff.exe

The exact old metadata files are:

- .reasonix/repository-hygiene-20261013/restore-refs.txt
- .reasonix/repository-hygiene-20261013/refs-cleanup.json
- .reasonix/repository-hygiene-20261013/recycled-ruff.json
- .reasonix/repository-hygiene-20261013/recycled-pytest-verified.json
- .reasonix/repository-hygiene-20261013/recycled-base-verified.json
- .reasonix/repository-hygiene-20261013/recycled-archive-verified.json
- .reasonix/repository-hygiene-20261013/recycle-probe.json
- .reasonix/repository-hygiene-20261013/pytest-cache-execution.jsonl
- .reasonix/repository-hygiene-20261013/completion-check.json
- .reasonix/repository-hygiene-20261013/closeout.json
- .reasonix/repository-hygiene-20261013/cache-targets-pytest.txt
- .reasonix/repository-hygiene-20261013/cache-plan-pytest.json
- .reasonix/repository-hygiene-20261013/cache-plan-base.json
- .reasonix/repository-hygiene-20261013/cache-execution.jsonl
- .reasonix/repository-hygiene-20261013/cache-archive-verified.json
- .reasonix/repository-hygiene-20261013/baseline.json

Preserve every pre-existing primary-checkout .ai task record and logs directory, private evidence, owner drafts, primary .venv, and pre-existing refs and archive tags. Preserve the nested publication checkout, including its complete .git, unique original files and TASK-0069 logs, in the complete recovery archive before removing its working copy. Creating this task branch and new commits is allowed; original main and all other pre-existing refs remain fixed. No source code, test code, dependency, Policy, authorization, CI, repository settings or runtime behavior change is planned.

## 验收条件

- Before cleanup, create and verify a compact package sufficient to inspect the original failed verification and its known failure inputs; do not claim that unknown random fixture state is reproducible.
- Before deleting any target, complete full-recovery.tar.xz for all 18 full_recovery_roots, including nested checkout .git data and unique files. The sole excluded ruff.exe must match its independently retained .venv/Scripts/ruff.exe source hash immediately before deletion. Verify all archive entry names, types, sizes, file hashes and recorded link targets; rehearse restoration into an empty local directory and compare bytes, directory structure and link descriptions without following links or executing any historical material. Absolute junction targets require the original location for functional reconstruction; ACL equivalence and historical replay remain uncertified.
- Resolve each source root inside the repository, require the exact reviewed relative-path allowlist, check ignored status, reject reparse roots and any scope drift, and recheck inventory before deletion.
- Delete only approved redundant fixture/cache/copy roots after independent review and a version-bound delete action approval. Keep the complete recovery archive and minimal failure package locally ignored.
- Compress old ignored inventory metadata only after a lossless verification; preserve original failure evidence in its original .ai task/log location.
- Compare protected entries, existing Git refs and tracked non-task files before and after. Preserve unknowns and failures. Run native verification without changing selected checks or thresholds, independent implementation review and gate.

## 非目标

No application implementation, Policy or authorization revision, public publication of local machine data, provider call, deployment or historical task cleanup. Publication of the new ledger is a separate final phase under the existing standing authorization.

## 禁止动作

Do not delete before backup, restoration and action approval pass. Do not modify primary-checkout existing .ai tasks or logs, private evidence, owner drafts or primary .venv. Do not change any pre-existing ref or archive tag other than the newly created task branch. Do not deploy, export secrets, pay for calls, weaken gates, change authorization, force push or rewrite published history.

## 错误行为

A missing or changed candidate, incomplete archive, hash or restoration mismatch, unsupported reparse point, scope escape, tracked deletion, protected inventory drift or changed pre-existing ref fails closed. Preserve the failed receipt and stop dependent deletion; do not silently omit entries, weaken verification or broaden paths.

## 回滚

Before deletion a verified complete recovery archive must restore every selected entry, including nested Git metadata and unique originals. Restore into an empty local root and verify hashes/topology before replacing a cleaned location. Retain the archive and manifest after cleanup; any ledger correction is appended through native CLI events without rewriting earlier records.
