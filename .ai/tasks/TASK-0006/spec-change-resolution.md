# TASK-0006 specification change resolution

- Condition: `spec_changed`
- Frozen specification SHA-256: `5b411b5f64856c9867792a32303b9854699334cd007cdb94a6fd6a1f3a370cb0`
- Subject commit: `52b543e72435afef9e7e5c52c5c09fd1109bd435`

The initial independent design review found two implementation-boundary gaps. The
frozen specification and allowed scope now:

1. include `src/aiflow/verification_service.py` and
   `tests/integration/test_verify_command.py`, and require V2 execution to fail
   before parsing or starting checks with `VERIFY_V2_NOT_EXECUTABLE`; and
2. require the complete secondary `policy_changed` governance cycle after the
   active Policy is edited: escalation, task-local resolution evidence,
   reclassification, refreeze, fresh design review, and fresh specification
   approval.

No production implementation has started. The prior classification and design
review are treated as stale and will not be reused. Reclassification may proceed
against this newly frozen specification.
