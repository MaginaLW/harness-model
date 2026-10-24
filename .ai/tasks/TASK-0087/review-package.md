# Optional SDK supplement after implementation context

## 审核目标

Review the default-off implementation-context supplement against the frozen TASK-0087 specification. This phase is local preparation and simulation only; it does not authorize a real model turn or publication.

## 背景

The owner selected the next bounded step after the completed single-review pilot: one explicitly enabled supplement at one existing workflow node. Reuse the delivered SDK runner and feedback path; do not repeat TASK-0086 or build a scheduler, exporter or platform.

## 代码地图

`src/aiflow/cli.py` adds the explicit options and native readiness/context binding checks. `src/aiflow/sdk_review.py` shares the existing execution block through `execute_review`; the actual SDK transport, permissions and lifecycle worker are unchanged. Companion tests cover the original standalone behavior and the real Git/context node using fake runtimes. The SDK contract and operations plan document the inactive node and future activation inputs.

## 语义变更

Without the enable-once flag, context generation retains its original output and does not import the runner. An enabled request requires the implementation stage, explicit material, current WAITING_FOR_FINAL_REVIEW status and fresh native evidence/classification. Native context validation and recomputation bind the original subject/base and run before preparation and dispatch. Explicit candidate documents must be changed docs paths. One call uses the shared runner and a small application-owned trigger marker; failures/unknowns are retained without replay. The native context output stays compatible; supplemental status uses stderr. No formal review record, approval, finding resolution or state transition is made by the supplement.

## 风险

The checks are prelaunch snapshots, not an atomic repository lock. Context hashes and trigger markers are supplied application bindings, not authenticated model identity, complete context or human authorization. A completed REQUEST_CHANGES report is not success of the candidate or code approval. Separate explicit invocations are not claimed globally exactly-once. Existing SDK read-only limitations, unknown cost/context/identity, output reservation and bounded cancellation/close behavior remain. Real activation, external reports, publication and research admission are outside this local task.

## 证据

已验证：independent design review approved the frozen context. The 147 affected tests pass under the native process runner's reduced environment in 158.25 seconds: 112 SDK regressions (including the original 101) and 35 real Git/context integration cases using fake SDK execution. All 74 changed executable lines are covered. Whole-repository Ruff, format and strict mypy pass. Initial red regressions for the absent helper and missing CLI options are retained under the ignored local build directory. The authoritative final fixed-subject validation and its original logs will be recorded by native V1.

未验证：complete native V1, final context-bound independent implementation review and local Gate remain pending. No real SDK call, remote CI, push, PR, merge, deployment, statistical window or Desktop connection has been performed in this phase.

## 审核问题

- Does the default and rejected-input path avoid importing or starting the runner?
- Do the node and dispatch checks preserve current native bindings while using subject/base instead of HEAD?
- Does shared execution preserve standalone receipts, lifecycle and negative review conclusions, without modifying formal task/review authority?

## 推荐结论

APPROVE only if fixed-subject tests, complete native V1 and independent implementation review confirm the bounded behavior. A local Gate or explicit flag does not authorize the presently forbidden external actions or a real activation.
