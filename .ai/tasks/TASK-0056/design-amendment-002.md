# TASK-0056 design amendment 002

The previous frozen specification, digest
`ce99472dd171f31697288d2153e12865c5c1a111a033f5135d4333d0462adddf`,
is preserved verbatim in `spec-design-002.md`. Original design contexts,
Reviews, approvals, failures and receipts remain immutable.

Complete run002 remains FAILED. Original-case comparisons demonstrate
261-character ordinary-copy failure and 260-character atomic temporary
filename failure. Shortening a parent corrected the old e2e Review case
but not all historical attachment corruption writes. The narrow correction
uses a Windows physical-path representation only for test-owned filesystem
operations, retaining ordinary logical case roots and service arguments.

A separate original module run reached its diagnostic limit in fixture
Git timeout cleanup. Its actual Windows Python stack shows the existing
10-second `subprocess.run` timeout, direct `kill()` and unbounded subsequent
`communicate()` waiting for a pipe reader. Why Git exceeded that command
deadline and the exact pipe-holding descendant remain unknown. The added
test helper scope permits owned tree termination and bounded cleanup,
without changing Git command semantics or the 10-second execution limit.

The added files are `tests/integration/test_external_review_command.py`
and `tests/integration/test_begin_close_commands.py`. Production storage,
Policy, default argv, selectors, environment whitelist, verification
budgets and thresholds are unchanged. Test fixes are a separate stage
commit after native escalation, resolution, reclassification, freezing,
independent design Review and a current specification approval under the
owner's existing direct authorization. No new implementation has begun.
