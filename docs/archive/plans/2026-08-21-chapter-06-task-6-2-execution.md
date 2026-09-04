# Chapter 6 / Task 6.2 Execution Plan

**Goal:** Add a self-contained `ai-flow` orchestration Skill that uses only the repository's executable CLI and keeps Policy decisions in core code.

**Route / verification:** REVIEW / V1.

**Allowed scope:** `.claude/skills/ai-flow/SKILL.md`, `tests/integration/test_ai_flow_skill.py`, and Chapter 6 / overall progress records.

**Forbidden actions:** no external action, Policy mutation, direct task-state edit, evidence fabrication, approval substitution, push, merge, deployment, credential access, or paid call.

## Steps

1. Define precise activation boundaries for mutating repository work and exempt purely read-only explanation.
2. Document the executable lifecycle, ASK/REVIEW material quality, explicit human decisions, escalation triggers, and stopping conditions.
3. Add a behavioral contract that enumerates the live CLI parser, validates repository links, and rejects copied Policy/state/verification matrices.
4. Run the focused skill validator and integration test, then repository-wide verification and record review evidence.

## Acceptance

- Every command named by the Skill exists in `build_parser()`.
- The Skill links to current templates and core documentation rather than copying their schemas or rules.
- Human direction/risk acceptance and action approvals remain distinct from code approval.
- Invalid state, stale artifacts, expanded scope, unavailable verification, and repeated failure lead to status/escalation/recovery commands, never direct state edits.
