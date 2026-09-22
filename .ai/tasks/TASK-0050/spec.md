# TASK-0050: governed publication of the local-tool delivery

## 目标

Complete the remaining publication of reviewed evidence-handoff and controlled-discovery tools,
pilot diagnosis and bounded maintenance records through PR #42. The owner explicitly instructed
continued completion with full authorization in the current conversation. That standing authority
covers this bounded work; record current spec/code/action bindings only at their allowed CLI states.
Independent technical review is not a substitute for the owner decision or a trusted executor.

## Existing facts and process deviation

The tool implementation was legitimately task-free under maintenance mode. Source subject is
`5ecde7164af91f166c13ce1953e3878961a45bff`; source files are not changed by this publication task.
The first PR #42 head `20a948ce7a65f23a8616349b3d09368c00bd91cc` was pushed and the PR created
under the owner's explicit authorization, with a tree-external authorization receipt, but before
creating the AI Flow task required for external actions by AGENTS.md. That procedural omission
is preserved as a deviation. This task is prospective for the next push and merge; it cannot
retroactively turn the prior push into a task-governed or pre-approved event. Prior CI run
`35697012985` passed only that old head and does not cover the later output-boundary fix.
PR #41's earlier closeout publication used the same receipt-only handling and is already merged;
its actual order is retained, not relabeled as a TASK-0050 operation. No old task is reopened.

## 范围

Task base is the actual creation HEAD `5ecde7164af91f166c13ce1953e3878961a45bff`.
Task changes are limited to `.ai/tasks/TASK-0050/**` and explicitly listed maintenance documents:
`docs/operations/local-tools-closeout-2026-09-22.md`, `docs/operations/maintenance-status.md`,
`docs/operations/follow-up-backlog-2026-09-22.md`. Safe document updates remain separate commits;
their explicit inclusion supports cumulative scope checking, not a new business implementation DU.

The actual remote publication is separately compared from
`aeaed58272f90f1505fce3841d302f5be6317119` to the final PR head. That cumulative scope contains
11 pre-existing files: tools/evidence/bundle.py; tools/diagnostics/tool_discovery.py;
tools/diagnostics/probe_versions.ps1; tests/unit/test_evidence_bundle.py;
tests/unit/test_tool_discovery.py; and the six documents controlled-tool-discovery.md,
evidence-handoff.md, follow-up-backlog-2026-09-22.md, local-tools-closeout-2026-09-22.md,
maintenance-status.md, pilot-evidence-review-2026-09-22.md under docs/operations/.
Only this task's new governance records and bounded updates to those documents may be added.
A task-local scope pass does not replace that wider remote diff audit.

## 验收条件

The CLI chooses route and verification from truthful external-action facts. Do not lower it.
Complete design review, current specification approval and begin before implementing publication
records. Freeze a real committed subject before formal verification; complete every required check,
implementation review and code approval. Existing source validation remains separately bound to
its source subject; do not forge a formal result from an ad hoc test log.

Retain the full test suite, 85% total and 90% diff coverage, whitespace, Ruff, format and mypy.
The new tools' Python coverage is explicitly included in the separate full-quality source check;
PowerShell's actual Windows tests remain distinct from Linux CI. After local Gate passes, record
current action approval and the precise publication head/base before the authorized push/update.
Record push, PR update and merge action approvals with exact targets, parameters, subject, expiry
and single-use intent; append actual execution receipts. Gate does not enforce generic action
approval or consumption and the wrapper only refuses commands, so the operator checks each binding.
Require successful ai-quality-gate from app 15368 on the exact final head, unchanged protections,
and a clean mergeable base before ordinary merge with matching head. Verify actual remote merge
state, commit parents, tree equality and implementation ancestry, then close once through the CLI.
Closeout-only records after actual merge remain local unless separately selected; do not recurse.

## 错误行为

Any scope mismatch, changed source, stale binding, failed check or required-check mismatch blocks
publication. Preserve failure records and diagnose; no bypass, fabricated approval or stale CI reuse.

## 禁止动作

Do not change production source, tests, Policy, Schema, workflows or ignore rules in this task.
No force push, branch deletion, deployment, credential export, paid provider calls, external-repository
writes or service actions. Do not rewrite prior ledger entries or move the three user drafts.
TASK-0028 option C, seven historical BLOCKED tasks, E3 and later phase conditions stay unchanged.

## 回滚

Before merge, retain commits and exact candidate records; correct with forward commits and fresh
required checks. After merge, any business rollback is a separately scoped forward revert and
validation, never history rewriting. No automatic deletion or reversal of unrelated changes.

## Parallel responsibilities

Two independent sub-agents may review design/publication scope and verification evidence read-only.
The main agent alone writes the task ledger, serializes CLI transitions and approvals, fixes the
committed subject and performs authorized external actions only after their prerequisites pass.
