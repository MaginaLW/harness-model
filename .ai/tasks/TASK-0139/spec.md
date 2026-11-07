# Task Specification

## 目标

Append the already encoded canonical UTF-8 task-event JSON plus exactly one LF on Windows and POSIX, and collect Git context/scope without optional index writes. Eliminate Windows CRT newline translation and the required Linux CI failure caused by Git refreshing the index during a supposedly read-only rejection.

## 范围

Retain the accepted src/aiflow/task_service.py O_BINARY-only repair. Extend only src/aiflow/git_context.py and src/aiflow/scope.py: their read-only Git subprocess argv must explicitly include Git's --no-optional-locks global option, so inherited GIT_OPTIONAL_LOCKS=1 cannot enable opportunistic index refreshes. Keep all command arguments, observed protocol, errors, timeouts and snapshot/index assertions otherwise intact; symbolic-ref reads need no additional write protection. No Git configuration or caller environment is changed. The task-free tests in tests/unit/test_facts_recovery.py and tests/unit/test_git_context.py are separately authored safe companions; the latter is allowed transport only and is not approved as governed implementation by this task.

Additional safe test transport: independently authored task-free commit b8cc97c55c872c3435b241f5f4f38f519392ed4e changes only tests/integration/test_resource_bundle_distribution.py. Its wheelhouse helper excludes only the exact distribution metadata entry <dist-info>/uv_cache.json from portable wheel payload; nested metadata and ordinary package files retain their existing validation and handling. The companion regressions are transported by this task but are not governed production implementation. DU-001 retains only the original three production paths; no production behavior or verification contract is broadened. This preparation does not authorize a new native invocation. Any later complete cycle still requires a newly authorized limit and action, all original 14 checks, the unchanged shared 3000-second budget, 85-percent total and 90-percent diff coverage, and five original baseline/mutant pairs with 60-second child limits. All existing prohibited actions and failed originals remain preserved.

Required-CI follow-up evidence: PR149 run41480071597 job125395713349 has eight installed-mutation transaction failures, all differing only in .git/index identity/stat cache after a rejected read-only query. Retain that failed job and its original log. Actual Windows forced-stale-index red tests independently reproduce both collectors changing index bytes/identity while reporting no content change. Local WSL is unavailable; Linux claims must come only from the actual exact-head required CI.

Serial dependencies: actual Windows red regressions, frozen facts/specification and independent design review, spec approval, minimal flag change and green regression, fixed candidate independent verifier/action, complete native V2, independent implementation review, same-verifier finalization, code approval and Gate, then ordinary direct and sdist-rebuilt wheel verification. Suggested concurrency is three: implementer plus independent reviewer and verifier; source writes remain single-owner.

## 非目标

No rewriting or normalizing existing event records, Policy, schema, Git configuration, Git attributes, approvals or evidence. No threshold reduction, relaxed stderr handling, new storage abstraction, model/SDK/WeChat calls, private transfer, source publication, remote changes or target installation.

## 验收条件

On the actual Windows host the new byte-level test must fail before the fix and pass after it for both existing LF and CRLF prefixes, with Unicode UTF-8 content and exactly one new LF. Existing prefixes must remain byte-for-byte unchanged. Run the entire event/facts recovery tests and Git context/scope tests, including both forced-stale-index cases with inherited optional locks enabled, exact argv assertions and the existing full snapshot rejection assertions. Preserve index bytes, device/inode, mtime and ctime and absence of index.lock without ignoring any Git administration path. The full eight-case required-CI failure cohort must be rechecked; use local Windows evidence honestly and require actual exact-head Linux CI before merge. Run full source pytest with both coverage domains, at least85percent total and90percent complete diff coverage, Ruff, format, strict mypy, whitespace and all unchanged native V2 checks and five original mutation operators under a fresh independently reviewed single-use action. The decision unit explicitly declares action_approval for this existing local targeted-mutation requirement; no external permission is requested. Record independent implementation review, same-verifier finalization, code approval and a passing local Gate. Build ordinary wheel and sdist-rebuilt wheel; verify their resource manifests and run the regression against ordinary installed bytes outside source imports. Root integration still separately owns exact-head required CI, publication and actual target acceptance.

## 禁止动作

Do not alter previous events, failed runs, reviews, approval history, spent actions, source maintenance mode, authorization files, unrelated worktrees or user WIP. Do not change Git/index protection, skip tests, weaken whitespace or coverage, copy credentials, run models, upload private material, push, merge or force-update refs.

## 错误行为

Preserve all failures and original bytes. A short write, fsync/open/close error, stale fact or missing approval remains rejected under existing behavior. Do not reinterpret or repair historical records or reuse spent authority. Diagnose new validation failures and fix only direct blockers, retaining every original gate.

## 回滚

Use an ordinary reviewed revert of only the relevant flag changes when necessary; retain the byte regression and append-only task/review/action/evidence records. Do not reset or delete historical task events or other work.
