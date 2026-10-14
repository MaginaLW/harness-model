# Task Specification

## 目标

Preserve the original failed verification evidence and the bytes needed to recover every cleanup target while reclaiming ignored local artifact storage in the owner-approved order.

DRAFT: the exact candidate inventory and all three stream-verified archives are now available. The complete recovery rehearsal and delete preflight remain pending. verified_backup remains false. No deletion is permitted by this draft, and no final classification or specification is frozen yet.

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

- Before cleanup, create and verify a conservative failure-and-provenance package sufficient to inspect the original failed verification and its known failure inputs. minimum-failure.tar.xz retains its preparation filename, includes some provenance-unknown material, and does not claim a minimal reproduction set. Unknown random fixture state is not assumed reproducible.
- Before deleting any target, complete full-recovery.tar.xz for all 18 full_recovery_roots, including nested checkout .git data and unique files. The sole excluded ruff.exe must match its independently retained .venv/Scripts/ruff.exe source hash immediately before deletion. Verify all archive entry names, types, sizes, file hashes and recorded link targets; rehearse restoration into an empty local directory and compare bytes, directory structure and link descriptions without following links or executing any historical material. Absolute junction targets require the original location for functional reconstruction; ACL equivalence and historical replay remain uncertified.
- Resolve each source root inside the repository, require the exact reviewed relative-path allowlist, check ignored status, reject reparse roots and any scope drift, and recheck inventory before deletion.
- Delete only approved redundant fixture/cache/copy roots after independent review and a version-bound delete action approval. Keep the complete recovery archive and minimal failure package locally ignored.
- Compress old ignored inventory metadata only after a lossless verification; preserve original failure evidence in its original .ai task/log location.
- Compare protected entries, existing Git refs and tracked non-task files before and after. Preserve unknowns and failures. Run native verification without changing selected checks or thresholds, independent implementation review and gate.

The current preparation evidence is local and ignored under .reasonix/repository-hygiene-20261014:

- archive-receipts.json (SHA-256 60818de8b7cd554272e3d97232dba3e19fc8df6803ca571ab8d3901245472466) binds the archive and final inventory hashes after per-entry stream readback.
- full-recovery.tar.xz: 84458884 compressed bytes, 914402345 logical file bytes, 174179 files; SHA-256 06ae3bd211fd4dc641e074ae9992003a75db02720f82210ad4dfff50f9ac60e9. Its inventory is full-recovery-inventory.json.gz, SHA-256 6365cd5edff5a0072c1f39a1fb6fdab4d832ae823c225a666d0ccbcda081e0cd.
- minimum-failure.tar.xz: 10142136 compressed bytes, 5755 files; SHA-256 0c818820ee748ef0adebf767c75200684d10dd46bc281f43ed6810b8e177ad4b. Its inventory is minimum-final-inventory.json.gz, SHA-256 2d79b86663ab1c534dc2f7e51c5dc6b5e1195e7f2ba9fec5e246205b6e5ed48f.
- old-metadata.tar.gz: 1572698 compressed bytes, 16 files; SHA-256 926d144c96b04c333dfaf8fb595fa01e745163a4a2c0336c55a9f5f028a82f4a. Its inventory is old-metadata-final-inventory.json.gz, SHA-256 fb9e2da318ef03e9d0d075e3f6a3c30c6a800b7235ab3d46ab7fa20991d2373c.
- restore-receipts.json records completed 6959-entry conservative-package and 17-entry metadata restorations with independent no-follow topology comparisons. Neither certifies ACL, directory-time equivalence or historical replay.
- original-location-mode-probe.json records a successful four-entry original-location restore when the absolute target was initially absent. The bounded recovery mode rejects existing roots, path escape and reparse ancestors, and restores directories/files before links. Final helper review and the complete recovery rehearsal remain required.
- archive-preparation-adjustment.json preserves the stopped random-seek archive verification attempt, the stream-order replacement and the fact that original sources were not deleted. It is preparation evidence, not cleanup completion.

Later preparation failure and replacement plan (appended after the preceding preparation snapshot):

- The first complete full-recovery.tar.xz restore did not pass. restore-failure-diagnostic.json records 42917 files created, one mismatching Git pack and 131262 files still missing. restore-failure-preserved.json identifies failed-pack-copy.bin and records that the source, archive reread and a fresh copy match the expected hash. The failed restored copy remains preserved; the cause is unknown.
- pack-readback-diagnostic.json records the matching expected/source/archive-stream/fresh-copy hashes and differing failed-copy hash. This diagnostic does not repair or complete the failed full restoration.
- A resumed attempt then failed during pure xz archive verification at a different Markdown member. xz-second-read-failure.json records that the original source still matches the expected first-manifest hash, the assertion failed, raw console was not preserved, and the receipt was reconstructed from tool output. The cause remains unknown. No original sources were deleted.
- The replacement full-recovery-v2.tar.gz is being prepared from a separately computed complete source inventory. The new archive must pass source hash comparison during writing, full sequential archive readback, a complete independent restoration and no-follow content/topology comparison, and delete preflight. The original xz package, failed restore, failed-copy bytes and diagnostic receipts remain preserved. Compression format changes do not relax any check or scope.
- No usable full-backup conclusion follows from the earlier successful readback receipt. verified_backup remains false, the task remains NEW, and classification, freezing, approvals and deletion remain unperformed. Only a successful, independently reviewed replacement evidence chain may support a final specification.

The diagnostic receipt hashes are:

- restore-failure-diagnostic.json: SHA-256 bbac6fc0bdde68cac0e263e74729574878c7836821052cca5dfcb2faea722c98.
- restore-failure-preserved.json: SHA-256 df8badaaf6c63b9d193387b16ed32b7c31e77ce978d2139bff11bfaf98d5ae90.
- pack-readback-diagnostic.json: SHA-256 618f39017812465de7beb704d7fa5b556805f9c79c188a64e35015ab012a1282.
- xz-second-read-failure.json: SHA-256 4522db4f218b7069c716a55c8845354ca9db5eb5eab53bdc52a591df98525873.

## 非目标

No application implementation, Policy or authorization revision, public publication of local machine data, provider call, deployment or historical task cleanup. Publication of the new ledger is a separate final phase under the existing standing authorization.

## 禁止动作

Do not delete before backup, restoration and action approval pass. Do not modify primary-checkout existing .ai tasks or logs, private evidence, owner drafts or primary .venv. Do not change any pre-existing ref or archive tag other than the newly created task branch. Do not deploy, export secrets, pay for calls, weaken gates, change authorization, force push or rewrite published history.

## 错误行为

A missing or changed candidate, incomplete archive, hash or restoration mismatch, unsupported reparse point, scope escape, tracked deletion, protected inventory drift or changed pre-existing ref fails closed. Preserve the failed receipt and stop dependent deletion; do not silently omit entries, weaken verification or broaden paths.

## 回滚

Before deletion a verified complete recovery archive must restore every selected entry, including nested Git metadata and unique originals. Rehearse into an empty local root and verify hashes/topology. For actual original-location recovery, the bounded original_roots mode accepts only the exact absent roots inside the repository, rejects reparse ancestors or existing roots, restores directories/files before links, and never executes historical code. This preserves absolute junction targets; old ruff is copied back only from its hash-matched retained primary source. Retain the archive and manifest after cleanup; any ledger correction is appended through native CLI events without rewriting earlier records.
