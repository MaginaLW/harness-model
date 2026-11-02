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
