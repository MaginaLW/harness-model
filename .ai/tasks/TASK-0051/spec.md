# TASK-0051: governed publication of runner path and evidence preflight improvements

## 目标

Publish the reviewed follow-up implementation from `8bdbcc07052fe7210a9d8fe7b4f6a240ad7a66f6` through one protected pull request.
The current owner asked to continue the remaining work for two hours and previously explicitly
approved and fully authorized completion. Record spec, code and each external action separately
at their valid CLI state; this direction does not itself prove a technical check passed.

## 范围

The task starts at `8bdbcc07052fe7210a9d8fe7b4f6a240ad7a66f6` and may only append `.ai/tasks/TASK-0051/**`.
Source, tests and tool documentation were implemented task-free under maintenance mode before
this publication task. No source changes are permitted within this task. The actual remote base
is `ae0e3d3fb070d1fa00ff25b086d8a49e9d222db9`. The cumulative remote delivery consists of the following existing files, plus
this task's append-only governance records:

- `.ai/tasks/TASK-0050/approvals.json`
- `.ai/tasks/TASK-0050/events.jsonl`
- `.ai/tasks/TASK-0050/merge-authorization-001.json`
- `.ai/tasks/TASK-0050/pr-update-authorization-001.json`
- `.ai/tasks/TASK-0050/publication-closeout-001.md`
- `.ai/tasks/TASK-0050/push-authorization-001.json`
- `.ai/tasks/TASK-0050/task.yaml`
- `docs/operations/evidence-handoff.md`
- `docs/operations/follow-up-backlog-2026-09-22.md`
- `docs/operations/local-tools-closeout-2026-09-22.md`
- `docs/operations/maintenance-status.md`
- `docs/operations/runner-health-checks.md`
- `tests/unit/test_evidence_selection_review.py`
- `tests/unit/test_runner_inspection.py`
- `tools/evidence/selection_review.py`
- `tools/runner/RunnerInspection.psm1`

The complete source quality run binds `2393c672e72d7f27fbfd8042e3ca51a99affadc2`. The only difference from that subject
to this task base is the reviewed runner-health-checks wording that distinguishes an early
PSDrive Root binding query from a later Free-space read. Source and test blobs are unchanged;
the documentation clarification is separately whitespace-checked and is not a new test run.

Prior TASK-0050 closure and safe closeout documents are selected for this next real delivery;
their historical facts are not rewritten or retrospectively relabeled as this task's work.
A task-local scope pass does not replace the full remote diff audit.

## 验收条件

Let current Policy determine route and verification from truthful external-action facts.
Complete independent design review, fresh spec approval and begin before implementation records.
Commit the candidate before formal verification. Complete every required check, independent
implementation review, code approval and a passing local Gate on the fixed subject.

Retain full tests, 85% total and 90% diff coverage, whitespace, Ruff, format and mypy. Separate
source validation includes optional Python tools; PowerShell behavior is verified by real
PowerShell subprocess tests, not claimed as Python line coverage. Formal task-local coverage
may contain no executable changed lines and cannot replace source cumulative coverage.

Before each push, pull-request creation and merge, record a current action approval with exact
target, candidate head/base, parameters, expiry and single-use intent. The operator verifies
these fields and actual receipts; generic Gate and the pre-command wrapper do not enforce
trusted action consumption. No remote mutation occurs before this task and its prerequisites.
Require successful ai-quality-gate from app 15368 for the exact final head and unchanged main
protection. Merge normally with an exact matching head; verify remote state, both parents, tree
equality and source ancestry before closing once. Post-merge receipts remain local unless
separately selected, without recursive publication.

## 禁止动作

No production source, tests, Policy, schemas, workflows, ignore rules or prior task history changes
inside this publication task. No force push, branch deletion, protection bypass, deployment,
credential export, paid provider call, external-repository write or service mutation. Preserve
the three user drafts. TASK-0028 option C, seven historical BLOCKED tasks and conditional E3,
E4/E5/I2-I5/later-phase work remain unchanged. Same-product sub-agents are not a dual-product E3.

## 错误行为

Scope drift, changed source, stale binding, failed checks, changed remote head/base/protection,
or wrong/missing required-check identity blocks that action. Keep failures, diagnose and produce
new evidence where needed. Do not bypass, fabricate evidence or reuse superseded candidate CI.

## 回滚

Before merge, retain commits and correct forward with fresh evidence. Any post-merge business
rollback requires its own scoped forward revert and checks; never rewrite history or delete
unrelated material.

## 并发与串行依赖

Two sub-agents independently review source, design and evidence in disjoint/read-only scopes.
The main agent serializes ledger changes, committed subject binding, formal verification,
code/action approvals, external publication, merge checks and closeout.
