# Chapter 6 / Task 6.1 Execution Plan

**Goal:** Keep `AGENTS.md` and `CLAUDE.md` as short, consistent entry files for the executable AI Flow without copying Policy or state-machine rules.

**Route / verification:** REVIEW / V1.

**Allowed scope:** `AGENTS.md`, `CLAUDE.md`, `tests/integration/test_agent_entry_files.py`, and the Chapter 6 / overall progress records.

**Forbidden actions:** no push, merge, deployment, credential access, paid call, destructive operation, Policy change, or external side effect.

## Steps

1. Compare both entry files with the six stable principles in the MVP design and the current CLI/Policy locations.
2. Keep only stable principles, one startup command, and relative links; retain platform-specific wording without adding rule tables.
3. Add an integration contract that checks principle parity, link validity, command availability, brevity, and absence of copied rule/state/verification tables.
4. Run the focused test, full regression, ruff, formatting, mypy, and diff checks; record hashes and review evidence before completing Task 6.1.

## Acceptance

- Both entry files express the same six core principles.
- Every referenced repository path exists and the documented startup command is accepted by the CLI.
- Neither file contains Policy rule identifiers, transition tables, route precedence, or a V0/V1 command list.
- Focused and repository-wide verification pass.
