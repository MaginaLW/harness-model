# Task Specification

## 目标
Preserve canonical UTF-8 JSON plus one LF per newly appended task event on Windows and POSIX.

## 范围
Only src/aiflow/task_service.py and tests/unit/test_facts_recovery.py, plus this task's native governance records. Use the existing binary file-descriptor flag at the append boundary; retain the existing JSON serialization, fsync, partial-write failure and descriptor cleanup behavior.

## 非目标
Do not rewrite existing events, migrate old tasks, import the rest of PR149 or PR150, change Git helpers, dependencies, Policy, permissions, mutation protocols or verification thresholds. Stage B, old mutation work, real scoring, automatic review and host attachment remain stopped. The prior task-free clean-checkout/documentation commit is the baseline and is not part of this core implementation.

## 验收条件
The real risk-facts persistence regression test_risk_fact_events_preserve_canonical_utf8_bytes demonstrates CRLF versus expected LF before the fix on Windows, then passes with exact UTF-8 bytes and Unicode actor data after the fix. Run the existing facts recovery cohort to retain exact recovery and failure behavior. Complete the native V1 selected by current Policy, full coverage and required static checks, independent implementation review, local Gate and exact-head required CI. The Windows actual byte path is checked directly; formal full-suite verification may use the project's existing Alpine environment with an independent exact-candidate clone and its own locked environment. Core/analysis 85 percent total and 90 percent applicable diff coverage remain unchanged.

## 禁止动作
No production, deployment, deletion of existing work, credential export, paid calls, policy changes, old-round retries, force push or history rewriting. Do not clone the shared object database into full-suite fixtures: formal verification uses a normal transport clone containing only public-main plus this task's reachable history. No extra private refs, alternates or unrelated objects are admitted. Publish only task-owned reviewed changes under existing standing authorization after required checks.

## 错误行为
Existing append failures, fsync failures, partial writes and cleanup must retain their current errors and recovery behavior. Preserve failed reproduction and verification originals; do not re-label old failed tasks as passed or transfer evidence across candidates.

## 回滚
Revert the single append-flag change and its regression with a normal follow-up commit. Preserve task evidence, old WIP and failure records; no reset, clean, stash or rewritten public history.
