# Review Package

## 审核目标

Decide whether the explicit draft risk-facts CLI at subject `d917af097353dd592bf60696a9e4e8eb6f1bd680` satisfies its frozen specification and is ready for code approval and conditional publication.

## 背景

The owner selected this bounded CLI and requested implementation, verification and merge. Core governance changes use TASK-0083; companion tests and durable documentation are separately committed task-free. The revised frozen design has an independent APPROVE in `reviews/REV-0002-r0001.json`; the earlier design review and its exact historical context remain preserved.

## 代码地图

`src/aiflow/cli.py` exposes the command. `decision_units.py` owns the twelve-field projection and validated top-level replacement. `facts_service.py` handles strict local JSON, draft/Git eligibility, preview, no-op, audited apply and exact staged recovery. `task_service.py` guards materialized facts and preserves uncertain append material; `state.py` admits the non-state audit event. The exact companion paths are in `task.yaml` and the frozen specification.

## 语义变更

One existing NEW, unfrozen and unclassified DU can receive explicitly supplied risk fields under its original repository, branch, base and subject. Omitted facts and unrelated metadata retain their values. Preview and ordinary no-op do not write task artifacts. A changed apply appends one facts event and materializes its timestamp. A complete interrupted event can finish only when the same actor/DU and an equivalent valid update uniquely reproduce the entire staged task; recovery appends no event. Raw JSON formatting and redundant unchanged input keys are not identity bindings.

Strict readers reject pending replacements; both strict and repairing readers reject unapplied initial facts without staged material. Only a later legal `classification_recorded` NEW-to-CLASSIFIED transition releases that initial projection binding, preserving the existing escalation, manual reassessment, resolution and reclassification path. Generic subject-sync recovery also checks facts before replacement. Isolated Unicode surrogates are rejected before any task write, while valid Unicode remains accepted.

## 风险

The command records declarations and does not verify their truth or change classification, approval or execution authority. It retains the existing single-writer convention and does not promise cross-process isolation or atomicity under every I/O failure. Partial, uncertain or unmatched recovery material is preserved and refused. No Policy, Schema, dependency, trusted host connection or generic task editor is added. Real scoring, automatic-review arrangement, host connections and the observation window remain paused; both deferred new routes remain unstarted.

## 证据

- 已验证：Fresh complete native V1 passed all ten required checks and 3793 tests on the unchanged implementation subject. Core total coverage is 89 percent, analysis total coverage 97 percent and core diff coverage 97 percent. Whitespace, Ruff, formatting and strict mypy passed. The 116 new in-process CLI and recovery cases cover typed fields, omitted facts, multiple DUs, cwd-relative input, all routes, rejection/preview byte preservation, interrupted append/replace, equivalent recovery, stale materialization and legal reassessment.
- 原始 `evidence.json` contains local runtime paths, remains local and excluded from Git, and has canonical digest `be9d9cc090dd679bcf5df522f5290ed80fb5b61cff033e58f5018b06fbf1ea0c`. Published review contexts bind the digest without claiming public access to the local original. Reproduce the complete verification with the locked project environment and `python -m aiflow verify TASK-0083 --actor codex-main`.
- Earlier failure evidence remains in local run archives and append-only task events. The first full run had 3792 passes and one existing gate-parity fixture initial Git commit exceeding its unchanged 10-second timeout; the unchanged module then passed all nine cases under the same minimal runner environment. The fresh complete second run used its own coverage database and passed without modifying the implementation, test timeout or quality thresholds. The underlying transient Git latency is not attributed to an unverified system cause.
- 未验证：Required remote CI and merge are pending. Cross-process isolation, arbitrary I/O-failure recovery, declaration truth, real scoring and host integration are not established by these tests.

## 审核问题

Do the implementation and companion tests enforce the twelve-field boundary, complete contracts, no-write preview/no-op, original Git binding, exact equivalent-update recovery and classification completion barrier without breaking existing reassessment? Do the final native evidence and source subject remain correctly bound, with failures and paused boundaries preserved?

## 推荐结论

Independent implementation review `reviews/REV-0003-r0001.json` is APPROVE with no findings and binds the passed native evidence and unchanged subject. Code approval is recorded under standing authorization and Gate passed with no reason codes. Publication remains conditional on required remote CI.
