# Review Package

## 审核目标

Decide whether independent core and analysis quality gates satisfy the frozen specification and are ready for code approval and conditional publication.

## 背景

The owner requested all five reviewed improvements. PR #70 delivered the CLI repair and task-free analysis tools and documentation. TASK-0080 governs the quality-gate successor; companion tests and durable documentation are separate task-free commits. The same frozen specification was independently renewed against the intended Policy content change without downgrading REVIEW/V1.

## 代码地图

`tools/ci/check_coverage.py` creates complete per-domain reports from one branch-coverage database and enforces independent 85 percent total and 90 percent diff coverage. `.ai/policy/verification-levels.yaml`, `.github/workflows/ai-quality-gate.yml` and `pyproject.toml` connect coverage and strict typing; `src/aiflow/verification.py` binds the native fixed command. Exact companion files are recorded in `task.yaml`.

## 语义变更

Core and analysis each meet both thresholds; neither can compensate for the other. Every Python source, including unexecuted and hidden paths, remains in its domain report. Strict typing includes analysis tools. V0, required categories, complete shared pytest execution and its 1200-second budget remain unchanged.

## 风险

The first candidate passed all native checks but independent review reproduced a hidden-path diff filtering bypass. The corrected implementation relies on isolated domain XML rather than a second glob; four real Git and coverage regressions cover hidden files and directories in both domains. Existing empty-diff behavior is preserved. No authorization files, repository settings or admission boundaries change.

## 证据

- 已验证：Complete locked native V1 verification of subject `39529ed512e4ddcd486f9c1ed0031bdbc185b9fd` passed 2887 tests in 563.49 seconds and all ten required checks. Core total coverage is 88.7212492 percent, analysis total is 93.7129841 percent; native core diff coverage is 100 percent and this task adds no measured analysis lines. Strict mypy passed for both source domains. Reproduce with `uv run --locked python -m aiflow verify TASK-0080 --actor codex-main`.
- Final evidence canonical digest is `446ea1aef3ae7b4095f83d55b5d2c3504ad66ac81d6b3f3d7970580ce6b3f0c0`, bound by context `d5a758a22fe5077be70f842f1405d3fc785c6240dd3a1984ec2ff2fd316a456f` and independent `reviews/REV-0004-r0001.json` / `reviews/REV-0005-r0001.json`. Raw native evidence includes runtime paths, remains local and untracked, and matches its preserved run original byte for byte.
- Original 2883-test verification, REV-0003 REQUEST_CHANGES and RF-001 remain preserved. `reviews/REV-0003-r0002.json` appends the confirmed resolution. The four hidden-path regressions were RED on the original implementation, then 34 locked unit tests and 15 locked integration tests passed after repair.
- Supplemental replay copied this same database into a separate local directory and compared the entire user batch since `1ab83a9821abbbe66dfd731e45b1927b83b4c5da`: core diff passed at 100 percent, analysis diff failed at 88 percent (30 missing of 271 changed lines). The gap is in prior PR #70 text-output tests executed as unmeasured subprocesses. This result is not native task evidence and does not replace it. A separate task-free test improvement will retain actual output assertions, cover the in-process path and recheck the whole batch before final user delivery; thresholds remain unchanged.
- 未验证：Required remote CI remains pending. The broader batch replay remains failed until that separate test follow-up passes. Real source authentication, observations, scoring and the observation window remain unstarted.

## 审核问题

Do complete source inventories prevent omitted-file passes, do domains independently enforce both thresholds, and do native plans bind the fixed checker without weakening other checks? Do the corrected candidate and final evidence satisfy both independent reviewers? Both independent reviewers confirmed the frozen candidate and native evidence with no findings.

## 推荐结论

APPROVE for code approval under the standing authorization after the final evidence and reviews are bound. Publication remains conditional on Gate and required CI. Real observation, scoring and the observation window remain unstarted.
