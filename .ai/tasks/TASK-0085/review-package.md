# Closeout consistency review

## 审核目标

Review fixed candidate `4b8fcfd4aab0fbc88d567df5204173e27e2f10ab` against the frozen TASK-0085 specification and current native evidence.

## 背景

The previous close check accepted any existing commit, including a zero-parent root, as a completed merge. That could record MERGED without the declared merge including the task candidate. Existing publication has required separate manual merge-parent and candidate-ancestry checks.

## 代码地图

`src/aiflow/task_service.py` extends the existing private close check; `commits_are_ancestral` is reused unchanged. Separate task-free tests in `tests/integration/test_begin_close_commands.py` cover real Git graphs and bounded errors; `tests/e2e/test_auto_scenario.py` now closes with an actual merge object. The quickstart describes the local check and its external limits.

## 语义变更

Use Git rev-list to read one commit and its parents. Require valid complete SHA metadata, at least two parents, a non-null subject, and base-to-subject-to-incoming-parent ancestry through at least one non-first parent. Preserve task state, result, repository identity, SHA checks, event payload and existing loading/recovery. Equality, later governance commits and multi-parent merges remain valid. No module, dependency, Schema, Policy or permission is added.

## 风险

This uses the existing local Git view; it does not authenticate a PR, target branch, remote completion, required CI or tamper resistance. Those facts remain separately checked. Historical MERGED records are not revalidated or rewritten. Rejection makes no closeout writes on a consistent task; existing loading/recovery behavior is unchanged. Real scoring, automatic review arrangement, host connections and observation-window activation remain paused.

## 证据

已验证：fixed-candidate native V1 passed all ten required checks, including 3858 tests in 899.73 seconds. Core/analysis total coverage is 89/97 percent; core diff coverage is 100 percent, with no analysis source changes. Full native Ruff, format and strict mypy passed. Before the repair, 16 new rejection regressions failed because close incorrectly returned success; a separate null-subject regression reproduced an uncaught TypeError during independent pre-review. Both original failure logs are retained locally. After the repair, all 57 tests in the affected integration file and AUTO end-to-end scenario passed in 69.60 seconds. Rejection tests compare complete task-directory bytes, while success checks preserve event payload, HEAD and branch. The authoritative current result is `evidence.json`; original run logs remain under its task-relative references.

未验证：final context-bound implementation review, Gate, required remote CI and merge-commit publication remain pending. Local verification does not establish production effectiveness or remote merge facts.

## 审核问题

- Does the local check reject ordinary or unrelated commits and unavailable candidate/parent facts before recording closeout?
- Are equality, later governance commits, multi-parent merges and candidates also on the first parent still accepted?
- Do the fixed native evidence and independent review cover the current subject without changing historical records or execution authority?

## 推荐结论

APPROVE for the bounded fixed candidate, subject to independent implementation review, current Gate and required remote CI before publication.
