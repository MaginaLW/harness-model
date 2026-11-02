# TASK-0139 review package

## 审核目标

Review the single encoded-event append flag change at subject b053c38f6f5fd82ddc821cac8d8943a6274ecce9 against base 1c23e3b12bf6431f7ad3853ef1332ab2913edd14. Structured implementation approval is REV-0002-r0001 with context25ae4a4b4a8489a68fbf9e6bf7ece57f748f3d986d7960769d0f8cdc28d85a72.

## 背景

Windows CRT text mode translated the already encoded event LF to CRLF. A target using LF Git attributes then produced a conversion warning and failed its strict Node whitespace check even though every check process exited zero.

## 代码地图

src/aiflow/task_service.py:_append_event adds only getattr(os, "O_BINARY", 0) to the existing append/write flags. The task-free byte regression in tests/unit/test_facts_recovery.py was independently committed before this governed task's base.

## 语义变更

New UTF-8 event bytes retain exactly one LF on Windows, while POSIX receives the zero fallback flag. Existing LF or CRLF prefixes are preserved byte-for-byte. Write-count validation, fsync, failure handling and descriptor closure are unchanged.

## 风险

The shared event sink affects audit records, so full V2 and all original gates remain required. No historical record is normalized or rewritten, and no Git setting, attribute, Policy, permission or coverage threshold changes. Exact source-outside fixture locations remain only in ignored preflight/original materials; public action conditions bind their retained digest and boundary.

## 证据

已验证: real Windows byte regression red2 then full facts-recovery green32; actual independent full native V2 passed all14 checks,6504 tests with9 existing conditional skips, core90percent and analysis98percent total coverage,100percent changed executable-line coverage, and all five original native mutations killed. Same actual verifier finalized without rerunning suites or pairs. Current final evidence raw SHA81be8f760ec0f5f29f3f22428c053026e04ab0c544b907bd24eec7f312eade12. Direct and sdist-rebuilt ordinary wheels have identical78 member bytes; both source-outside installations verified20 resources, preserved both historical prefixes, UTF-8/new LF and empty Git whitespace stdout/stderr.

未验证: exact-head remote required CI, source publication, real target application and complete Node CI adoption remain root integration responsibilities. No model, SDK, WeChat or private-material transfer acceptance was run here. The9 prior conditional skips were not added or broadened.

## 审核问题

- Does the flag preserve previous bytes and the existing failure/flush/close contract?
- Do current final evidence, independent context, structured reviews and all five original mutation results bind the same candidate without lowering a gate?
- Are source publication and actual-target acceptance kept separate from this local source repair?

## 推荐结论

APPROVE. Actual independent REV-0002 has no findings and current same-verifier final evidence passes. Record only the permitted local code approval and evaluate the actual Gate; no personal human review or external action is asserted.


## Required-CI follow-up: current failed native cycle

Current governed source subject is 72c2ca5ab479fe1987bde62a6c29156a6b160677. Retain the earlier result above as historical evidence for b053c38; it does not approve this new subject. Required PR149 run41480071597 job125395713349 exposed eight read-only index-snapshot failures. The two read-only Git helpers now explicitly pass --no-optional-locks, preserving environment, configuration, errors, timeouts and every complete snapshot assertion. Actual Windows stale-index tests were red before the fix. The four-file focused follow-up passed396 tests with one existing Windows filename skip; independent design REV-0003 and a separate source pre-review approved with no findings.

Ordinary direct and sdist-rebuilt candidate wheels have all78 member bytes equal. Both actual source-outside installations verified20 resources, UTF-8 and both historical newline prefixes, empty Git whitespace stdout/stderr, and both collectors preserving index bytes and identity even with inherited optional locks enabled. These candidate checks do not replace complete V2 or required Linux CI.

The fresh independent native cycle FAILED. Its shared full pytest exceeded the unchanged3000-second budget at3000093ms, with output ending at83percent and no complete test or coverage result. The five shared check categories failed; diff coverage also failed because its coverage database was absent. Mypy separately exited2 with an internal cache-read assertion. Five targeted native mutations were actually killed, but they do not make the complete run pass. Failed evidence raw SHA256 is 8b4d04c8d77f4a7343a046698d004f9b2c2390a7e52a9c08014341f7ee3124c5. The independently reviewed action bd2281b6631ee961ce401e2819a7a948ed60633a62eb90465d1e603ad617f5aa is consumed and cannot authorize another run.

Separate diagnostics found all1426 hashed installed-mypy files matching RECORD and the locked1.20.2 version. The same strict62-source-file mypy check passed using a new diagnostic cache. Read-only comparison found only typing.data.ff differing among285 common fixed-format cache entries: a single byte at offset116378, old204 versus new3. The old cache and failed originals remain retained. This diagnostic is not formal verification and does not explain the pytest timeout. Fixture creation-time comparisons locate most additional elapsed time in earlier installed-engine real-original replay sections; these are timing proxies, not proof of a specific regression or environmental cause.

Current recommendation is HOLD. No implementation approval, code approval, finalization, Gate success, publication or target acceptance is asserted for the current failed cycle. Preserve the failed originals and diagnose before any fresh bounded action; do not reuse prior passed evidence, the spent action, relax checks or extend the timeout.
