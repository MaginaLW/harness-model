# Task Specification

## 目标

Include tools/analysis in full branch coverage and strict typing. Require core and analysis code to independently meet total coverage of at least 85 percent and diff coverage of at least 90 percent, without one domain compensating for the other.

## 范围

Governed implementation is limited to .github/workflows/ai-quality-gate.yml, pyproject.toml, .ai/policy/verification-levels.yaml, src/aiflow/verification.py and tools/ci/check_coverage.py. The exact companion test and durable documentation paths in allowed_scope are separate task-free commits.

Preserve V0, existing V1/V2 check IDs and ordering, required status, one shared full pytest execution, its 1200-second budget, and other quality checks. Policy version remains 2.5.0; the content digest changes. No authorization file, Schema, routing, dependency or repository setting changes.

## 验收条件

- Shared pytest adds --cov=tools/analysis beside --cov=aiflow and retains branch coverage and its run-bound combined coverage.xml. Strict mypy checks src and tools/analysis.
- Both CI and native V1/V2 call the fixed entry: python tools/ci/check_coverage.py --run-dir <run_dir> --base <base_commit>. Domain selection, thresholds and filtering cannot be overridden by CLI arguments.
- Use Coverage(data_file=<run_dir>/.coverage, config_file=False) with canonical repository-root cwd. Require an existing database, nonempty measured files, branch data, nonempty inventories in both fixed domains, and at least one canonical measured file per domain.
- Explicitly pass every Python file under src/aiflow and tools/analysis as each domain's morfs, include=[], omit=[], ignore_errors=False. Unexecuted files remain in the denominator. Compare the raw report return value to 85; display rounding cannot admit a lower result.
- Generate coverage-core.xml and coverage-analysis.xml from that same database. Invoke diff_cover.diff_cover_tool through the same interpreter with fixed argv, shell=False, canonical root cwd, a finite timeout, exact base and fail-under 90. Preserve existing diff-cover comparison semantics; documentation-only or deletion-only diffs may have no measurable added lines, but missing data or domain mappings cannot masquerade as an empty diff.
- Native diff_coverage remains the same category with threshold 90. Its guard binds complete argv, run directory, base, empty environment, required=true, parser exit_zero and timeout 120. Other required checks and thresholds remain effective.
- Exercise each domain independently failing total/diff thresholds, raw 85-percent boundary, unexecuted files, nested/same-name paths, missing/invalid/statement-only data, missing domains, report/subprocess failures, empty diffs, and plan tampering. Complete native verification and required CI remain necessary; a standalone replay of old data is not fresh verification.

The owner explicitly requested this work. Independent frozen design approval precedes implementation. Because the intended Policy content change invalidates its own previous digest, use native escalation, documented same-spec resolution, reclassification with no route/level downgrade, new design context/review and renewal only of the now-stale spec approval before final verification. Keep every earlier event and review. Code approval and publication require independent APPROVE without unresolved critical/high findings, complete verification and the standing authorization.

## 错误行为

Missing/unreadable/invalid data, non-branch data, empty or completely unmeasured domains, report failure, any total below 85, missing diff tool, timeout or nonzero diff result fails the checker. No automatic retry, omitted domain or weaker threshold substitutes for a failed check. Invalid native command bindings are rejected before execution.

## 禁止动作

Do not weaken gates, omit files, reduce the full suite, change authorization files, permissions or protected-branch settings, collect data, call providers, start scoring or an observation window, deploy, delete data, export credentials, pay for calls or rewrite pushed history. Native evidence with machine paths stays local and untracked; publish digest-bound summaries and reviews only.

## 回滚

Use a subsequent revert of this implementation and configuration if needed. Preserve all task events, reviews, original verification runs and existing history; rollback does not erase failure evidence.
