# Task Specification

## 目标

Preserve valid Unicode text when replaying task events and returning risk-facts JSON, so a successful facts write remains readable and reports success under Windows output encodings.

## 范围

Core changes are limited to `src/aiflow/task_service.py` and `src/aiflow/cli.py`. Read event records using standard text-stream line boundaries instead of Unicode-aware `str.splitlines()`. Keep UTF-8 event serialization unchanged, including unescaped U+0085, U+2028 and U+2029 inside JSON strings. Return facts results using ASCII-escaped JSON; decoded fields and values remain identical under ASCII, GBK and UTF-8 stdout.

The task ledger belongs to this task. Companion tests and long-lived usage/current-state documentation are separate task-free commits. `tools/analysis/approval_overhead.py` receives the same bounded event-reading correction in a separate task-free commit for legacy reports and fixed-HEAD snapshots. Cumulative allowed paths include these exact companions. Reuse standard `readlines()` and `io.StringIO`; introduce no parser framework or dependency.

## 非目标

No new Schema, Policy, routing, approval, state transition, recovery mechanism, retry, collector, SDK client or cross-repository initialization. Do not change output from unrelated commands. Real scoring, automatic review arrangement, host connections and the observation window remain paused with T0/T1 unset.

## 验收条件

- Reproduce the pre-fix failure for legal Unicode separators in event strings and facts output with emoji under a restricted stdout encoding.
- Exercise actual task loading and facts CLI apply, preview and no-op paths. Successful apply writes one unchanged Unicode event; subsequent task reads and a repeated apply succeed without extra events. Decoded JSON retains exact Unicode values.
- Cover LF/CRLF and terminal-newline compatibility. Empty, malformed and blank event records still follow existing rejection behavior; private fields are not newly projected, and read-only reports preserve source bytes.
- Exercise legacy statistics, fixed-HEAD snapshots and their existing consumers using the current fixtures. No unknown or historical failure is promoted to success.
- Obtain independent design and implementation reviews, native verification and Gate. Full pytest, separate core/analysis 85 percent total and 90 percent diff coverage, whitespace, Ruff, format, strict mypy and remote required CI remain mandatory. Publish only with a merge commit.

## 禁止动作

No deployment, data deletion, credential export, paid call, real scoring, automatic review arrangement or host connection. Source changes have no external side effects. Conditional push, PR and merge use existing standing authorization after applicable review, verification, Gate and required CI; do not change authority files or quality thresholds.

The task's forbidden-action list is exactly `deploy`, `delete`, `secret_export` and `paid_external_call`. The default `push` and `merge` prohibitions created by `start` are reconciled with the conditional publication scope above before implementation; this does not authorize unconditional publication or change repository permissions.

## 错误行为

Keep current input validation, task eligibility, event sequence checks and malformed-input domain errors. Do not suppress serialization or I/O failures generally. ASCII JSON escaping changes wire representation only, not event bytes, decoded fields, permission or task state. Retain actual failed runs and unknown outcomes.

## 回滚

Use a normal reviewed revert if required. Do not rewrite pushed history, delete task evidence or change existing event bytes. Disposable fixtures and local logs stay in ignored build/cache directories.
