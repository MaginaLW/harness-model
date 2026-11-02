# Task Specification

## 目标

Append the already encoded canonical UTF-8 task-event JSON plus exactly one LF on Windows and POSIX. Eliminate Windows CRT text-mode CRLF translation that makes the target's fixed Node whitespace check reject an otherwise passing run.

## 范围

Only src/aiflow/task_service.py, specifically _append_event's os.open flags. Add getattr(os, "O_BINARY", 0) to preserve the encoded wire bytes on Windows and remain portable on POSIX. Keep append, write-count, fsync, exception and close behavior unchanged. The separately authored task-free regression in tests/unit/test_facts_recovery.py is already the task's committed baseline and is not owned by this governed implementation.

Serial dependencies: actual Windows red regression, frozen facts/specification and independent design review, spec approval, minimal flag change and green regression, fixed candidate independent verifier/action, complete native V2, independent implementation review, same-verifier finalization, code approval and Gate, then ordinary direct and sdist-rebuilt wheel verification. Suggested concurrency is three: implementer plus independent reviewer and verifier; source writes remain single-owner.

## 非目标

No rewriting or normalizing existing event records, Policy, schema, Git configuration, Git attributes, approvals or evidence. No threshold reduction, relaxed stderr handling, new storage abstraction, model/SDK/WeChat calls, private transfer, source publication, remote changes or target installation.

## 验收条件

On the actual Windows host the new byte-level test must fail before the fix and pass after it for both existing LF and CRLF prefixes, with Unicode UTF-8 content and exactly one new LF. Existing prefixes must remain byte-for-byte unchanged. Run the entire event/facts recovery tests. Run full source pytest with both coverage domains, at least85percent total and90percent complete diff coverage, Ruff, format, strict mypy, whitespace and all unchanged native V2 checks and five original mutation operators under a fresh independently reviewed single-use action. The decision unit explicitly declares action_approval for this existing local targeted-mutation requirement; no external permission is requested. Record independent implementation review, same-verifier finalization, code approval and a passing local Gate. Build ordinary wheel and sdist-rebuilt wheel; verify their resource manifests and run the regression against ordinary installed bytes outside source imports. Root integration still separately owns exact-head required CI, publication and actual target acceptance.

## 禁止动作

Do not alter previous events, failed runs, reviews, approval history, spent actions, source maintenance mode, authorization files, unrelated worktrees or user WIP. Do not change Git/index protection, skip tests, weaken whitespace or coverage, copy credentials, run models, upload private material, push, merge or force-update refs.

## 错误行为

Preserve all failures and original bytes. A short write, fsync/open/close error, stale fact or missing approval remains rejected under existing behavior. Do not reinterpret or repair historical records or reuse spent authority. Diagnose new validation failures and fix only direct blockers, retaining every original gate.

## 回滚

Use an ordinary reviewed revert of only the flag change when necessary; retain the byte regression and append-only task/review/action/evidence records. Do not reset or delete historical task events or other work.
