# TASK-0013 action transaction-type clarification

This task-local governance note clarifies the descriptive transaction label used
by the already-consumed V1 rerun action. It does not amend, replace, reopen, or
make reusable either the immutable action file or its use record.

## Canonical classification

- Canonical frozen-spec transaction type: `v1_verify`.
- Retry instance ID: `TASK-0013-V1-002`.
- Descriptive instance label retained in the immutable artifacts:
  `full_v1_verification_rerun`.
- Prior consumed transaction/action SHA-256 (`rerun_of`):
  `f647e210f7442ae9bb8fea27b01fdfa34ace02c18a364f1f039140bc31cd8f85`.
- Current consumed transaction/action SHA-256:
  `b9e57469cab7769667138fa3d46b383b446e03b099cd7c149c158b8113aad43a`.

`full_v1_verification_rerun` names this particular retry instance; it is not a
third transaction type. The transaction is canonically a `v1_verify` because
its exact outer command is one complete local `aiflow verify TASK-0013`
invocation with no `--check` or `--finalize`, bound to the current ten-check V1
Policy plan and the frozen budget of at most two mutation-runner invocations,
two temporary roots, and ten serial detached worktrees. The successful run
observed exactly those two runner invocations and consumed the approval.

The original action and use record remain immutable historical facts. This
clarification grants no delete authority, retry, unused budget, push, merge,
deploy, task close, code approval, full V2, or other external action.
