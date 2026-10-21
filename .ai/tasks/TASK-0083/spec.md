# Task Specification

## 目标

Deliver `aiflow facts TASK-ID --decision-unit DU-ID --input FILE --actor ACTOR [--dry-run]` for explicit pre-classification risk facts, without hand-editing task YAML or altering routing, approval or execution authority.

## 范围

Core implementation is limited to `src/aiflow/cli.py`, `decision_units.py`, `facts_service.py`, `task_service.py` and `state.py`. The task ledger belongs to this task. Companion tests in `tests/integration/test_facts_command.py`, `tests/unit/test_facts_recovery.py` and the existing exact event-vocabulary assertion in `tests/unit/test_state.py`, and usage/current-state changes in `docs/operations/quickstart.md`, `adoption.md` and `maintenance-status.md`, are separate task-free commits. The task's cumulative allowed scope includes their exact paths, while its governance decision unit covers only core implementation.

The repository has no DRAFT state: eligibility means `current_state=NEW`, no frozen-spec fields, no existing classification or classification-pending artifact, and the original repository/branch/base/subject matching the current Git baseline. Dirty draft files do not themselves authorize a new baseline. The command does not edit scope paths, task/DU identity, goals, Git bindings, state, classifications, approvals or evidence.

Input is one explicit nonempty local UTF-8 JSON object. Reject malformed JSON, duplicate keys at any depth, non-finite constants, unreadable input, unknown fields and invalid complete resulting contracts. The only writable top-level DU fields are `scope`, `impact`, `protections`, `verification`, `impact_categories`, `controlled_actions`, `business_direction_count`, `change_characteristics`, `verification_requirements`, `reversibility`, `external_side_effects` and `permission_requirements`. Each supplied top-level field replaces that whole field; nested objects must satisfy the existing complete Schema. Omitted fields retain their original presence and values, with no risk defaults or inferred facts. The input path remains relative to the invocation directory.

Validate all decision units and the complete resulting task using the existing contracts and semantic DU checks. Only one named existing DU changes; other units and non-risk metadata remain unchanged. Facts are declarations, not independent verification of their truth. The command never classifies, freezes, approves, dispatches a review or executes an external action.

Output is JSON with `task_id`, `decision_unit_id`, `dry_run`, `changed`, `applied`, `recovered`, `before` and `after`; before/after are the complete present risk-field projections of the selected DU. Preview validates the same operation but writes nothing. Identical ordinary apply returns no change without an event or timestamp change. A changed apply records one `risk_facts_recorded` event with the selected DU, actor and before/after projections, then materializes the validated task with the event timestamp.

Reuse the existing staged-task/event-append/replace primitives under the repository's single-writer convention; do not claim cross-process isolation or atomicity under every I/O failure. Strict readers reject pending `task.yaml.next`; strict and repairing readers also refuse unapplied recorded facts when no staged task exists, so classification cannot consume stale facts after uncertain append failure. After valid state replay, compare each DU's latest facts event with its materialized risk projection until a later legal `classification_recorded` transition from NEW to CLASSIFIED. That transition is the completion barrier because first classification itself reads strictly. NEW self-loop events, including freeze, do not release the check. After the barrier, existing escalation/resolution/reclassification rules govern later fact changes; the facts CLI remains NEW-only. Preserve compatibility with tasks containing no fact events.

Only repeating the same valid apply may finish a risk-facts replacement interrupted after a complete event append. Before one replace, validate raw and staged task contracts, replayed state, NEW/unfrozen/unclassified/Git eligibility, last event type/task/DU/actor, its exact before/after projections, and staged-task equality to the unique task obtained from the current raw task plus this input and the original event timestamp. No other field or DU may change. Recovery preserves the original event, actor and timestamp and appends no second event. Preview, mismatched input/actor/DU, unknown staged files, corrupt/partial logs and missing recovery material preserve the original files and fail. Generic task loading must not silently recover arbitrary fact replacements.

## 非目标

No new Schema, Policy, dependency, general patch engine, cross-process lock manager, arbitrary task editor, source collector, result store or automatic retries. Real scoring, automatic review arrangement, host connections and the observation window remain paused with T0/T1 unset. Application-managed SDK clients and full-engine cross-repository initialization are not started. New governance code is not automatically a natural pure-document research sample.

## 验收条件

- Exercise the real in-process CLI on disposable repositories: typed valid replacements, omitted/missing facts, multiple DUs, root/subdirectory invocation, valid read-only preview and no-op preservation.
- Prove every rejection and preview preserves task artifacts byte-for-byte: non-NEW/frozen/classified drafts, unknown/protected fields, invalid nested values/types, duplicate JSON keys, non-finite input, missing DU, bad actor, wrong repository/branch/baseline, corrupt events and staged materialization.
- Prove append failure, interrupted replacement, exact same-input recovery, recovery refusal on changed input/actor/DU or staged metadata, and classification refusal while recorded facts are not materialized. Do not infer full I/O atomicity from these bounded cases.
- Preserve existing classification requirements: omitted impact categories/actions still require explicit assessment; valid facts can lead to AUTO, ASK, REVIEW or BLOCK only through the unchanged classifier.
- Preserve the existing facts-to-classify-to-escalate-to-manual-reassessment-to-resolve-to-reclassify path; historical facts events must not permanently lock subsequent authorized reassessment.
- Run targeted tests, then current native verification and Gate. Full pytest, separate core/analysis 85 percent total and 90 percent diff coverage, whitespace, Ruff, format and strict mypy remain required. Obtain independent design and implementation reviews, required CI and merge-commit publication.

## 禁止动作

No deployment, data deletion, credential export, paid call, real model scoring, automatic review arrangement, host connection or activation of either deferred route. Core implementation has no external side effects. Conditional branch push, PR and merge use the existing standing authorization after applicable review, verification, Gate and required CI; no permission or quality rule is changed.

## 错误行为

Return a domain error and nonzero exit without a success report for invalid input, task eligibility, contract, baseline or pending-material mismatch. Do not expose parser payloads or traceback. Preview and rejected requests never repair materialization or change any task artifact. Preserve uncertain/partial append failures and staged recovery material; only the specifically proven complete-event replacement case can resume through the same apply invocation. Stop rather than lower a gate or fabricate a classification, approval, risk fact or research result.

## 回滚

Implementation changes are reversible by a normal follow-up revert with reviews and quality gates; do not rewrite published history or delete historical task evidence. For disposable validation fixtures, retain the assertion evidence in tests. A real interrupted facts update keeps its original event and staged bytes; repeat only the same exact valid apply for the documented replacement case, and preserve any unmatched or uncertain failure for explicit diagnosis.
