# TASK-0018 implementation resume baseline

TASK-0018 entered implementation at event 13. The work listed below was produced in
that authorized implementation window and deliberately preserved when the task was
blocked at event 14. After the user-authorized incident resolution, reclassification,
spec refreeze, and spec re-approval, `aiflow begin` correctly refused to resume because
the original task baseline recorded a clean worktree.

The CLI currently has no command that re-baselines preserved in-scope work after a
BLOCKED recovery. To retain the work without stashing, deleting, committing it outside
the implementation state, or weakening scope, the materialized task baseline records
the exact current non-governance dirty paths:

- `.ai/schemas/observation-decision.schema.json`
- `.ai/templates/observation-decision.json`
- `src/aiflow/contracts.py`
- `src/aiflow/observation_decision.py`
- `src/aiflow/observation_service.py`
- `src/aiflow/state.py`
- `tests/fixtures/contracts/invalid/observation-decision.extra.json`
- `tests/fixtures/contracts/invalid/observation-decision.invalid.json`
- `tests/fixtures/contracts/invalid/observation-decision.missing.json`
- `tests/fixtures/contracts/valid/observation-decision.json`
- `tests/integration/test_observation_escalation.py`
- `tests/unit/test_contracts.py`
- `tests/unit/test_observation_decision.py`
- `tests/unit/test_observation_service.py`
- `tests/unit/test_state.py`

Every path was already in the frozen 18-path allowed scope. This baseline records only
the existence of preserved work; it does not accept its contents, expand scope, alter
the classification input, authorize an external action, or replace later V1 evidence
and implementation review.
