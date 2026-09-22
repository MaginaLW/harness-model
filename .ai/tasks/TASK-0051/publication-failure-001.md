# TASK-0051 publication attempt: required CI failure

PR #43 was created at `587dcb05160578f7487d79e29f43fb24a9880081` after this task's
local V1, independent review and Gate passed. Push and PR creation were separately
recorded and executed within their authorization period. No merge was performed.

Required ai-quality-gate (app 15368), run `35714491010`, check/job `106702632642`,
failed on that exact head. Linux reported 3 failed, 2233 passed, 2 skipped; core
coverage reached 88.03%. Three present-root cases in the disk-probe test invoked
the host Join-Path against synthetic C-drive paths. Linux has no such drive, so
the fixture failed before its disk assertions. Contracts passed (105 tests);
later diff/Ruff/format/mypy commands in that shell step did not run after pytest
failed. Maintenance-mode Verify and Gate was skipped as configured.

Raw run JSON, complete log and an independent failure diagnosis are retained in
the private continuation materials. This failed CI does not invalidate the fact
of the earlier Windows checks; those checks cannot establish Linux acceptance.

The frozen task only permits its own governance files. It is now BLOCKED through
CLI scope_expanded escalation, preserving the specification, prior approvals,
reviews, evidence and execution history. A separate task-free test-only fix and
a new publication task will continue the same PR from a new committed base with
fresh review, formal verification, Gate, exact-head CI and action approvals.
No result from this attempt is relabeled as the later candidate's acceptance.
