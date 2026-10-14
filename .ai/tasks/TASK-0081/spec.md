# Task Specification

## 目标

Preserve the original failed verification evidence and the bytes needed to recover every cleanup target while reclaiming ignored local artifact storage in the owner-approved order.

DRAFT: exact candidate paths, complete recovery archive hashes, usable restore proof and protected inventory checks are pending. No deletion is permitted by this draft, and no final classification or specification is frozen yet.

## 范围

Local ignored work artifacts listed in the final inventory under .reasonix/repository-hygiene-20261014/plan.json, this work directory, lossless compression of prior ignored hygiene metadata, and the new .ai/tasks/TASK-0081 ledger. The final inventory must name each deletion root exactly and must be copied as relative paths into allowed_scope before freezing.

Preserve every pre-existing .ai task record and logs directory, private evidence, owner drafts, .venv, existing refs and archive tags. No source code, test code, dependency, Policy, authorization, CI, repository settings or runtime behavior change is planned.

## 验收条件

- Before cleanup, create and verify a compact package sufficient to inspect the original failed verification and its known failure inputs; do not claim that unknown random fixture state is reproducible.
- Before deleting any target, complete a separate recovery archive containing every candidate entry, including nested checkout .git data and unique files. Verify all entry names, types, sizes and file hashes; rehearse restoration into an empty local directory and compare contents and topology.
- Resolve each source root inside the repository, require the exact reviewed relative-path allowlist, check ignored status, reject reparse roots and any scope drift, and recheck inventory before deletion.
- Delete only approved redundant fixture/cache/copy roots after independent review and a version-bound delete action approval. Keep the complete recovery archive and minimal failure package locally ignored.
- Compress old ignored inventory metadata only after a lossless verification; preserve original failure evidence in its original .ai task/log location.
- Compare protected entries, existing Git refs and tracked non-task files before and after. Preserve unknowns and failures. Run native verification without changing selected checks or thresholds, independent implementation review and gate.

## 非目标

No application implementation, Policy or authorization revision, public publication of local machine data, provider call, deployment or historical task cleanup. Publication of the new ledger is a separate final phase under the existing standing authorization.

## 禁止动作

Do not delete before backup, restoration and action approval pass. Do not modify existing .ai tasks or logs, private evidence, owner drafts, .venv, existing refs or archive tags. Do not deploy, export secrets, pay for calls, weaken gates, change authorization, force push or rewrite published history.

## 错误行为

A missing or changed candidate, incomplete archive, hash or restoration mismatch, unsupported reparse point, scope escape, tracked deletion, protected inventory drift or changed pre-existing ref fails closed. Preserve the failed receipt and stop dependent deletion; do not silently omit entries, weaken verification or broaden paths.

## 回滚

Before deletion a verified complete recovery archive must restore every selected entry, including nested Git metadata and unique originals. Restore into an empty local root and verify hashes/topology before replacing a cleaned location. Retain the archive and manifest after cleanup; any ledger correction is appended through native CLI events without rewriting earlier records.
