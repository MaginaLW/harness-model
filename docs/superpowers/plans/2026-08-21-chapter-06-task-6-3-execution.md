# Chapter 6 / Task 6.3 Execution Plan

**Goal:** Add thin local wrappers that delegate verification, scope/status, permission, and workflow decisions to the existing core.

**Route / verification:** REVIEW / V1.

**Allowed scope:** `tools/gauntlet.py`, `tools/hooks/pre_commit.py`, `tools/hooks/pre_command.py`, `src/aiflow/verification_service.py`, `src/aiflow/policy.py`, `tests/integration/test_tool_wrappers.py`, `docs/operations/hooks.md`, and Chapter 6 / overall progress records.

**Forbidden actions:** the wrappers must not execute commits, mutate the index, parse arbitrary shell syntax, perform external actions, auto-fix files, or copy Policy decision tables.

## Steps

1. Add the gauntlet argument adapter and a core provisional verification input.
2. Add a pre-commit adapter over strict task loading, status/workflow facts, changed-path collection, and core scope assessment.
3. Add a pre-command adapter over a core Policy permission decision and shared workflow evaluation.
4. Document explicit platform integration and enforcement limits.
5. Test delegation, matching conclusions/exit codes, missing/ambiguous tasks, out-of-scope paths, denied actions, help, and absence of external mutation.
6. Run focused and full verification and record completion evidence.
