# Review Package

## 审核目标
Decide whether the scoped event append fix preserves canonical bytes without changing error/recovery behavior.

## 背景
The user authorized the concrete maintenance follow-ups. The preceding task-free commit e3a41ee8 separately delivers clean-checkout isolation and the useful resource documentation from old drafts. This REVIEW/V1 task is limited to event persistence and its regression.

## 代码地图
src/aiflow/task_service.py:_append_event is the sole production boundary changed. tests/unit/test_facts_recovery.py:test_risk_fact_events_preserve_canonical_utf8_bytes reaches it through record_risk_facts and the existing persistence path.

## 语义变更
Add getattr(os, "O_BINARY", 0) to the existing append flags. Windows newly appended events keep UTF-8 JSON plus LF. POSIX flags are unchanged. Existing event history, JSON serialization, write checks, fsync, errors and descriptor cleanup are retained.

## 风险
No dependencies, Policy, permissions, Git helpers or runtime authority change. Existing failed repro and environment-preparation materials are retained. A transport clone and dedicated Windows environment were used for the full suite; the object store was positively checked against the candidate reachable graph plus the existing public v0.2.0 annotated tag, with no unrelated private graph or alternates. Selected-HEAD history is not a privacy-erasure mechanism or an OS sandbox.

## 证据
已验证：
The actual Windows red/green byte originals were inspected by the independent reviewer; red CRLF versus expected LF failed, green canonical bytes passed, including the Unicode actor. The affected facts recovery cohort passed 31 tests.
Current native evidence.json binds subject 97e9d334ccaa3cff943d522ea8ec2244a60b99ff, execution HEAD ccc9a208bca6500a863d6a0e1d8dcb869e4b6f87 and base e3a41ee842baab6afb713a521aef784851d0c52a. All 10 V1 checks passed without timeout. Full Windows suite: 6507 passed, 9 unchanged conditional skips in 43:02. Displayed core/analysis total coverage: 90%/98%; core one-line diff coverage: 100%; analysis has no changed executable lines. Evidence-referenced original logs remain in the actual local run directory.
未验证：The exact-head remote required CI is not yet run. Stage B, old mutation work, scoring, automatic review and host attachment remain stopped.

## 审核问题
1. Does the regression prove the real event-byte behavior? Yes: the independent reviewer inspected the raw originals and real facts path.
2. Are prior append error, recovery and cleanup semantics retained? Yes: only the binary flag changed, and the existing facts recovery cohort and full V1 passed.
3. Are scope and mandatory gates preserved? Yes: formal REV-0002 independently checked source and current V1 bindings; local Gate and exact-head required CI remain separate requirements before merge.

## 推荐结论
APPROVE, matching independent implementation REV-0002 with no findings. Continue to code approval, local Gate, publication and exact-head required CI; no paused work is activated.
