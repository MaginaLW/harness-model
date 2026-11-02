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


## Isolated runtime recovery preparation

The old source virtual environment and failed cycle remain retained. Runtime preparation used a separately authenticated UV0.12.5 Windows artifact, the signed PSF CPython3.11.9 executable/DLL, the unchanged lock,35 locked registry wheels, explicit authenticated PSF/PyPI pip24 bootstrap, and offline current-source editable build with already locked setuptools/PyYAML. No old environment/cache was an installation source, no managed Python was downloaded, and no lock/Policy/runner or tracked source changed.

The exact47 untracked shared CP311 bytecode caches were preserved, independently reviewed and reversibly isolated before editable backend loading; no directory or unknown file was removed. The default bad mypy DB/WAL/SHM originals are retained with those caches in a50-record recovery manifest, raw SHAa565d1d0bc0d783b44ae4bb5c041c794c8aad20b45d887d9fe17db58667b0e47. Independent read-only before/after comparison found all4545 old-environment files unchanged.

The new runtime is the workspace-relative build/lf/source-recovery-env. Final static audit covers35 locked registry distributions plus pip24 and editable source, all37 distribution RECORDs, locked/official original archives and exact installed members, with narrowly reviewed authenticated-installer metadata and generated launchers. Generated PE wrappers remain prohibited as verification executables; original wheel-owned executables remain exact archive members. The actual14-check/8-execution native plan resolves every command through the new absolute interpreter without blocking or unverified checks.44 top-level ownership projections and5 actual imports satisfy boundaries. Optional SDK/CLI modules were only statically inspected or resolved by spec, never called.

Eight light origin/help/version commands passed with empty stderr and an unchanged environment snapshot. The original default strict mypy invocation and a preceding no-incremental rebuild each passed62 source files using the new environment, while the raw bad-cache backups stayed unchanged. The rebuilt default DB SHA is846e32cf1768ba2572dba2f09c9c466305dddf03014472bb6e9707fb4bfdfc56. Independent lf_review approved preparation after actually rechecking all50 backup hashes and all3601 current new-environment file identities/hashes. Retained preparation hashes: final static report2629c2fb43f2909b0e25a06f690cfbd94170a67192a832afadeec1cc728f13a4; light summary97f9bf52c7ba73ca339867c36fde85a7d9158bff8c884df74fa507f7eeba1f1e; cache diagnostic summary07232a119ad943825428634770115bd299dcab8610e120829c7bae9bf5fe2a84.

These are preparation and diagnostic facts only. No new full suite, native mutation run, action approval, finalization or Gate was executed. TASK-0139 remains FAILED until supported recovery and a newly reviewed single-use full action complete under the original14/3000/85/90/five-pair requirements. Neither the prior timeout cause nor the underlying input-corruption cause is claimed resolved. Root integration separately owns the exclusive resource window and later exact-head Linux CI/publication/target acceptance.


## Third invocation interrupted and legally abandoned: current HOLD

Current source subject remains 72c2ca5ab479fe1987bde62a6c29156a6b160677. The one authorized third invocation started under action46c0e7caa797ae658ae24da4d0031b83f8e6a92b46de080369885844b153ab21 and retained run-20261102T201444424784Z. Execution stopped after the protected SDK CLI member changed at physical offset62255516 from0x00 to0x66 while its size and recorded identity/timestamps stayed unchanged. The other3600 original protected files,76 source inputs, authenticated base executable/DLL and UV were unchanged in the retained diagnosis. The original wheel member remained intact. No cause or writer was established; repository/helper static review found no matching real-tool write path. The finite supplied twelve-file-offset pattern, each offset modulo64 equal28, is arithmetic only and excludes the logical typing.data.ff row offset. No hardware, SDK or self-update attribution follows.

No complete pytest output, coverage result, native result or third-round mutation consumption was produced. Fixture remnants and cached-collection/source-AST reasoning only locate an inferred test function, not a captured runtime trace. The main native PID exited1. The original termination helper did not retain taskkill return code/output or terminated child PIDs, so whole-tree termination is not proved; the later bounded process-metadata query found no matching known PID or executable-prefix processes. These limitations are preserved in ignored build/lf/native-v2-round3-hold-summary.json, raw SHA2561ca08de53fdec84219b3df965b613b809e3830b59f1e6cdce0da0978892fd411. Independent lf_review and lf_verify approved that passive summary. Its VERIFYING value is a historical observation before abandonment and is not the current task state.

Root subsequently used a separately authenticated ordinary control runtime and the supported verify --abandon --actor root-integrator --reason entry point, without running either suspect environment or any verification check. The retained control receipt is build/agent-bridge-adoption/a1-input-audit/abandon-control/receipt.json in the root integration workspace, raw SHA256486d7abe572425b9d0e612358ab1e5bfd06b756413ed4bb08e6be8eeedd0de09. It records exit0 and the genuine abandoned:true verification_failed event at sequence42, following sequence41 verification_started. Current task state is FAILED. The CLI abandon branch routes to the existing append/materialize transition, without writing verification evidence or mutation consumption.

The receipt's old-event-prefix and unchanged-evidence assertions were made against bytes retained in the controller process memory; no separate pre-abandon event snapshot was saved. Independently, the current task's old evidence is byte-identical to the committed failed evidence, SHA2568b4d04c8d77f4a7343a046698d004f9b2c2390a7e52a9c08014341f7ee3124c5. The first40 committed event contents are unchanged after accounting only for existing CRLF versus LF representation; current worktree bytes contain14 CRLFs while Git's committed blob is LF. Raw HEAD-prefix equality is therefore not asserted. Exactly the start and abandoned events are new. No historical worktree prefix was rewritten to make this comparison pass, and no missing pre-abandon snapshot was invented.

Recommendation remains HOLD. The third invocation authorization is closed even though mutation execution never began and no consumption receipt exists. Neither old environment nor source-recovery-env may execute. No fourth run, repair/reinstall, new environment, target acceptance, finalization, code approval, successful Gate, publication or merge is authorized by this record. The source72 candidate still requires a stable validation environment and a separately authorized complete native cycle, then exact-head required Linux CI and root-owned source/target integration acceptance. All prior failed/interrupted originals and the existing14-check/3000-second/85-percent-total/90-percent-diff/five-original-pair requirements remain intact.
