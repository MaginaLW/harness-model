# TASK-0052: complete PR43 after Linux fixture repair

## 目标

Complete the existing PR43 with the reviewed test fixture correction and fresh publication
evidence. The owner explicitly approved and fully authorized continued completion, including
the current two-hour continuation. Preserve failed attempts; do not trade required checks for
the elapsed work window. This task governs subsequent push, PR update and ordinary merge.

## 范围

Fixed base `7b940bf67743673755ac872ed6ff32e9d1d87ca1`; only `.ai/tasks/TASK-0052/**` may change within this task.
The fixture-only correction was committed separately under maintenance mode. It replaces
host-dependent Join-Path inside one synthetic Windows disk-probe test with lexical fixture
joining and a throwing host-resolution sentinel. Existing assertions and cases remain;
no production module, Policy, Schema, workflow, ignore rule or quality threshold changed.

TASK-0051 remains BLOCKED as a preserved failed publication attempt: its Windows V1 passed,
but exact-head Linux CI run 35714491010 had 3 failed, 2233 passed, 2 skipped. Its two actual
actions and evidence remain historical, not approvals for this candidate. Never close that
task as merged or overwrite its frozen specification, reviews or raw evidence.

Production tool/core blobs still match `2393c672e72d7f27fbfd8042e3ca51a99affadc2`. Its complete source quality
record remains 2238 Windows tests, combined Python coverage 88.8607%, diff 99%; new fixture
tests and fresh full formal V1/CI separately establish the new test revision. No stale CI
or old test-file validation is claimed as current Linux acceptance.

The actual remote base is `ae0e3d3fb070d1fa00ff25b086d8a49e9d222db9`. Cumulative existing changed paths:

- `.ai/tasks/TASK-0050/approvals.json`
- `.ai/tasks/TASK-0050/events.jsonl`
- `.ai/tasks/TASK-0050/merge-authorization-001.json`
- `.ai/tasks/TASK-0050/pr-update-authorization-001.json`
- `.ai/tasks/TASK-0050/publication-closeout-001.md`
- `.ai/tasks/TASK-0050/push-authorization-001.json`
- `.ai/tasks/TASK-0050/task.yaml`
- `.ai/tasks/TASK-0051/approvals.json`
- `.ai/tasks/TASK-0051/classification.json`
- `.ai/tasks/TASK-0051/design-context-001.json`
- `.ai/tasks/TASK-0051/design-review-input-001.json`
- `.ai/tasks/TASK-0051/events.jsonl`
- `.ai/tasks/TASK-0051/implementation-context-001.json`
- `.ai/tasks/TASK-0051/implementation-review-input-001.json`
- `.ai/tasks/TASK-0051/pr-create-authorization-001.json`
- `.ai/tasks/TASK-0051/publication-failure-001.md`
- `.ai/tasks/TASK-0051/push-authorization-001.json`
- `.ai/tasks/TASK-0051/review-contexts/092b6ab3e133b7e939cbe54944b200b9e5ed7b26622418c8bf2aa932b98d8044.json`
- `.ai/tasks/TASK-0051/review-contexts/8e2218a624ae7028d92f3fb51878d3c5f6d96e096f450b930fea086ac9061f2d.json`
- `.ai/tasks/TASK-0051/review-package.md`
- `.ai/tasks/TASK-0051/reviews/REV-0001-r0001.json`
- `.ai/tasks/TASK-0051/reviews/REV-0002-r0001.json`
- `.ai/tasks/TASK-0051/spec.md`
- `.ai/tasks/TASK-0051/task.yaml`
- `docs/operations/evidence-handoff.md`
- `docs/operations/follow-up-backlog-2026-09-22.md`
- `docs/operations/local-tools-closeout-2026-09-22.md`
- `docs/operations/maintenance-status.md`
- `docs/operations/runner-health-checks.md`
- `tests/unit/test_evidence_selection_review.py`
- `tests/unit/test_runner_inspection.py`
- `tools/evidence/selection_review.py`
- `tools/runner/RunnerInspection.psm1`

## 验收条件

Current Policy determines REVIEW/V1 from truthful external actions. Independently review the
frozen design, record current owner spec approval and begin. Commit task records before formal
verification; run all required checks, independently review implementation/context/raw logs,
record code approval and require a passing local Gate. Keep 85% total and 90% diff coverage,
full tests, Ruff, format, mypy and whitespace. Task-local zero executable changes cannot
replace cumulative production coverage; PowerShell tests are not Python line coverage.

Each subsequent push, PR body update and merge needs a new exact-target/head/base/parameters,
unexpired single-use action record under this task. Check those facts just before the write.
Gate and wrapper do not provide trusted automatic consumption. Keep the existing PR43 and
normal branch; no second duplicate PR is needed. Require final-head ai-quality-gate from
app15368, unchanged strict protection, actual merged state, exact two parents, equal tree and
source ancestry before closing TASK-0052 once. Post-merge receipts remain local without
recursive publication. Preserve Windows and Linux test/skip/coverage counts separately.

## 禁止动作

No source/tests or prior-task edits within this task, forced push, branch deletion, protection
bypass, deployment, secret export, paid call, service mutation or external-repository write.
Preserve the three user drafts, TASK-0028 option C and seven earlier BLOCKED records. The new
TASK-0051 failure is additional history, not a revived feature queue. E3 still needs a natural
dual-product case; same-product sub-agents and this fixture fix do not satisfy it. All later
conditional stages and external writer handoffs retain their existing boundaries.

## 错误行为

Stop the affected action on changed bindings, failed checks, wrong app/head, expired approval
or protection drift. Preserve output, diagnose and create fresh evidence. Do not skip failing
cases, overwrite failure evidence, downgrade verification or use the former candidate's CI.

## 回滚

Keep pre-merge commits and correct forward with fresh evidence; any later business revert
requires its own bounded change and checks. Never rewrite or delete prior history.

## 并发与串行依赖

Two sub-agents independently review fixture/source, design and verification/archive evidence
with disjoint write scopes. The main agent serializes task state, fixed commits, formal checks,
approvals, external actions and closeout. Existing raw material is immutable.
