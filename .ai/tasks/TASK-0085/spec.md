# Task Specification

## 目标

Record task closeout only when local Git can establish a merge commit that includes the task's reviewed candidate through an incoming parent, instead of treating any existing commit as a completed merge.

## 范围

Core implementation is limited to `src/aiflow/task_service.py`, extending the existing commit check used only by `close_task`. Preserve the current APPROVED_FOR_MERGE state, result, repository identity and complete SHA checks. Use Git plumbing to read parents, require at least two parents, and reuse `commits_are_ancestral` to prove `base_commit -> subject_commit -> incoming parent` for at least one parent after the first. Equality is allowed: a governance-only task can have subject equal to base, and a PR head may contain later governance commits after subject. Support ordinary two-parent and multi-parent merges without adding a new policy option.

The check uses the existing local Git view and timeout/error model. It is a necessary local consistency check, not trusted execution or remote provenance authentication. Do not add network access, fetch, merge, checkout or ref mutation. Keep the existing merge_recorded payload and state transition unchanged. Do not revalidate, migrate or rewrite historical MERGED tasks.

Companion tests in `tests/integration/test_begin_close_commands.py` and `tests/e2e/test_auto_scenario.py` and usage/current-state changes in `docs/operations/quickstart.md` and `docs/operations/maintenance-status.md` are separate task-free commits. The existing end-to-end close success fixture must use an actual merge. Their exact paths remain in cumulative allowed scope; this task's decision unit covers only core implementation. The task ledger belongs to this task.

## 非目标

No PR lookup, target-branch enforcement, required-CI authentication, Gate rerun, new approval, remote action, retry or historical adjudication. No new module, dependency, Schema, Policy, generic Git wrapper or execution permission. Real scoring, automatic review arrangement and host connections remain paused; observation-window T0/T1 remain unset. SDK and cross-repository initialization remain unstarted.

## 验收条件

- Reproduce that an existing root/ordinary commit is currently accepted as merged; add a failing regression before the source repair.
- On consistent approved disposable tasks, reject root/ordinary commits, unrelated merges, candidates present only through the first parent, invalid base-to-subject history, missing candidates, malformed parent metadata and Git errors/timeouts without changing task bytes or appending a merge_recorded event.
- Accept genuine merges containing subject through an incoming parent, including later governance commits, subject equal to base and a valid incoming parent after the second in a multi-parent merge. Do not require a PR head to equal subject or subject to be absent from the first parent.
- Success preserves the event payload, branch and HEAD; close performs no merge or network operation. Preserve old state/result/identity/SHA rejection and historical task reading.
- Pass focused real-Git regressions, native V1, independent design and implementation reviews, Gate and required CI. Complete pytest and separate core/analysis 85 percent total and 90 percent diff coverage, whitespace, Ruff, format and strict mypy remain mandatory. Publish with merge commits.

## 禁止动作

Forbidden actions are deploy, delete, secret_export and paid_external_call. Source implementation has no external side effects. Conditional branch push, PR and merge follow the existing standing authorization after applicable review, verification, Gate and required CI; no authority file or quality threshold changes.

## 错误行为

Return existing or bounded close-specific domain errors and nonzero exit when the local merge facts are false or unavailable. Do not echo raw Git output, paths or private metadata. Do not fetch missing objects or retry errors. On a consistent task, validation rejection does not write task artifacts. Existing loading/recovery behavior is unchanged; this task adds no repair path. A local pass does not prove that GitHub merged a particular PR, the target branch contains it or required CI passed; those publication facts remain separately checked.

## 回滚

Use a normal reviewed revert if required. Preserve original task history, approvals, evidence and failed receipts. Never rewrite pushed history or bulk-edit already closed task records. Keep disposable fixtures and local diagnostics in existing ignored locations.
