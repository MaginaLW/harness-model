# Task Specification

## 目标

Retire the unused repository Reasonix working directory and the three inventoried generated caches while retaining byte-recoverability of all 2171 original entries, including all 1939 files, in compact recovery material outside all deletion roots.

DRAFT: exact source inventory and dependency evidence exist, and the all-entry outer-XZ plus exact-gzip-recipe retention strategy is selected. Final retained bundle/helper hashes, complete outer-member/EOF verification, physical full restoration and exact protected execution preflight remain pending. verified_backup=false and dry_run=false reflect this state. Preparation-only ledger commits are allowed. Do not classify, freeze, approve, begin or delete until Root provides and admits the real evidence; a preparation commit does not constitute execution admission.

## 范围

Only these four exact original roots and their descendants are cleanup targets:

- .reasonix
- .pytest_cache
- .ruff_cache
- src/aiflow/__pycache__

The only additional task scope is .ai/tasks/TASK-0082/** for this new ledger and its locally ignored retention/verification logs. This worker edits only task governance files outside logs; Root and the independent workers own the runtime/helper/retention material inside logs. No nonexistent .mypy_cache or broad source, tests or tools cache globs are authorized.

The original material/protection baseline is 64cd6a3252c5d8fa23f92e32dc09e2ae24bc1376. Preparation-only ledger commits preserve this original baseline; the still-NEW classification base/subject will be aligned to the real preparation HEAD before first classification, without rewriting history or claiming later recovery proofs already exist.

The immutable source inventory is .ai/tasks/TASK-0082/logs/reasonix-retirement/inventory/exact-inventory.json.gz, SHA-256 6e9ac8108407726a46901fd54a6a0ce2ecfd78e714d47c510eb318e503d1defd: 2171 entries, 1939 files, 630175443 logical file bytes, all ignored, zero tracked candidates, zero observed reparse points and zero hardlink groups. An independent second complete source SHA scan passed with no missing, extra or changed entries. These are preparation observations; execution must recheck them.

Preserve every pre-existing primary-checkout AI Flow task, logs and private native evidence, owner drafts, active .venv and original Git refs/archive tags. Every original entry inside .reasonix and the three caches must be accounted for in the new byte-recoverable retained recovery set before deletion. All original files except one exactly reconstructible redundant gzip are stored directly; that gzip is recreated byte for byte from the retained compact XZ plus its pinned recipe. All directories are retained in the manifest and restored. The earlier 41-file minimal-retention option is not selected. Reasonix historical references are audit evidence and do not themselves constitute a runtime dependency.

Repository publication is permitted later under the existing standing authorization after native code approval/gate and all unchanged required CI checks. Bind separate finite-lived single-use push and merge actions to this task branch and its single protected merge-commit PR. Original main changes only through that normal protected PR flow; no direct main push or history rewrite is permitted. Existing TASK-0081 closure changes are already in the branch baseline and this worker must not rewrite them.

## 非目标

No tracked implementation, test behavior, CI, dependency, Policy, Schema, authorization, shared ignore rule or repository-setting change. No claim of uninstall completeness, historical execution replay, physical validation or repair of old unknown anomalies. Zero observed matching processes remains a point-in-time observation. No evidence, logs or owner draft outside the exact targets may be deleted or moved.

The new task does not revise TASK-0081 admission: its primary gzip archive, prior failed xz observations and later successful facts remain the original historical decisions. A compact retained representation needs a fresh successor proof chain; later payload equivalence does not retroactively erase failures or claim a known root cause.

## 验收条件

- Freeze the exact four-root inventory and an all-entry reconstruction mapping before implementation. Preserve all 2171 original paths/kinds and all 1939 file byte contents, including historical source, evidence, failed-copy bytes, diagnostics, caches, manifests and provenance. The single outer XZ bundle includes the 1938 directly stored files plus all directories; only the large redundant gzip is represented by an exact recipe. Do not use the 41-file minimal-retention option or drop other original entries.
- Store every retained payload, required original, mapping manifest, recovery helper and actual proof outside all four deletion roots, in locally ignored task logs. Ensure no retained artifact depends on the .reasonix path being kept during normal use or verification.
- The sole recipe-backed original is .reasonix/repository-hygiene-20261014/full-recovery-v2.tar.gz: exactly 424878535 bytes with SHA-256 a7c81e516aa2dbc89186722ec421b7a37a4a9aa670d6119c3f1cb4ba2b089658. gzip-reconstruction.json already records a successful actual hash-only reconstruction from the compact XZ tar stream. Preserve the original gzip header filename full-recovery-v2.tar, mtime 1791982733, compression level 6, 1048576-byte chunking and observed Python 3.11.9/zlib compile/runtime 1.3.1 dependency in the retained recovery instructions. Do not change the current environment or Policy. Restoration must check its required runtime and produce the bound original compressed-file SHA; payload equivalence alone is insufficient.
- Validate every outer archive member and complete EOF, then actually restore every original directory and stored file. Physically regenerate the omitted gzip, close it, independently reread its full SHA and compare all 2171 original paths/kinds and all 1939 file contents against the frozen original inventory with an independent no-follow scan. The already passing hash-only recipe probe does not substitute for this final full physical restoration. Preserve all prior TASK-0081 decisions and unknowns; no old admitted hash or task record is rewritten.
- Resolve each exact deletion root and its ancestors inside the repository, reject changed inventories, tracked/protected entries, reparse points, unexpected hardlinks or active dependencies, and recheck every current file SHA. The reviewed helper must remove children bottom-up with non-recursive unlink/rmdir and stop on an unexpected child or changed entry.
- Complete independent frozen-design APPROVE, native spec approval and a separately version-bound finite-lived single-use delete action based on the owner's current explicit cleanup request before begin/execution. Do not auto-retry an interrupted or failed deletion.
- Preserve actual execution-started/completed or failed receipts. Recheck original protected task/log/private material, owner drafts, .venv, original refs and retained package hashes after deletion. Report actual original logical/allocated savings separately from discarded copies created by this task and from retained recovery overhead. Cache absence is a cleanup-time observation; later normal tools may regenerate caches.
- Run native validation, scope and the complete unchanged Policy-selected verification level. An independent implementation APPROVE with no unresolved critical/high findings precedes code approval and gate. Required CI still runs the full suite, both coverage domains and thresholds, whitespace, Ruff, formatting and strict typing before protected merge-commit publication.

The already completed isolated gzip recipe proof is logs/reasonix-retirement/gzip-reconstruction.json, SHA-256 4bce6b7d7b7b1a1594fc46828dfc642c2afbcfba5aa622be53663a4d370f0614. It streamed 1355581440 tar bytes (SHA-256 4dbbf6167aa57785a206a5a7919977a18fd6b647b0c09df804b372556434d6d4), reconstructed the original 424878535 gzip bytes with the exact expected SHA, and wrote no new large gzip file. This proves the recipe only; outer-bundle creation, complete physical restoration and final execution preflight remain pending.

## 禁止动作

Do not delete, freeze, classify, approve or begin while the real recovery and final preflight evidence are missing. Do not change old task records, old failures or historical approvals; all 2171 original entries must first have admitted byte recovery through direct storage or the sole exact gzip reconstruction recipe. Do not weaken gates, change Policy/Schema/authorization or shared ignore rules, deploy, export secrets, pay for external calls, force push, rewrite published history or touch another ref/archive tag. Do not execute historical source, fixture tests or historical actions as part of recovery.

## 错误行为

Missing or changed source, any original entry not covered by the full recovery manifest, failed exact-gzip reconstruction or runtime pin, failed member/EOF/SHA/restoration, incomplete topology, path escape, unexpected link/hardlink, tracked/protected target, active dependency, changed helper/binding, expired action or repeated execution fails closed. Preserve the original failed receipt and unknown cause. Do not omit the problematic material, broaden deletion roots, switch to a weaker proof or claim completion from inventory alone.

## 回滚

Before deletion the final retained plan must give a verified usable route to restore every original entry byte for byte, including the generated caches and the recipe-backed original gzip. The gzip recipe depends on the recorded Python 3.11.9/zlib compile/runtime 1.3.1 behavior, original header filename/mtime and compression/chunk settings; the helper must reject an incompatible reconstruction runtime or output hash. This task does not change or install an environment. Verify retained package/helper/manifest hashes, restore into an absent empty bounded target, recreate files/directories before links when required and compare file bytes/topology without following or executing historical content. Original-location restoration must reject existing roots and reparse ancestors. Keep the recovery set, restoration instructions and all historical failures after cleanup; append corrections through native records rather than rewriting evidence.
