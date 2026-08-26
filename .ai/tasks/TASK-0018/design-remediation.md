# TASK-0018 design remediation

## Trigger

- Review: `REV-0021` revision 1
- Context: `7ac3c4c2b9f6f179f5381a13d6563763794208dee1efd39c9e913aed5be9a63a`
- Outcome: `REQUEST_CHANGES`
- Finding: `RF-001` (`high`)

The first frozen specification required `observation_recorded` and
`observation_refused`, but the allowed scope excluded `src/aiflow/state.py` even
though `record_task_event` accepts only names registered in the closed
`NON_STATE_EVENTS` set.

## Bounded correction

1. Add only `src/aiflow/state.py` and `tests/unit/test_state.py` to product/test
   scope.
2. Permit only registration and regression testing of the two new non-state
   event names. No state, transition, precondition, Policy, CLI, Hook, CI, Gate,
   evidence, approval, review, task schema, or event schema change is allowed.
3. Correct `policy_changed` at current route `BLOCK` to `record` with
   `execution_allowed=false` and reclassification required. It must not call
   `escalate_task` from a normally `BLOCKED` task.
4. Keep the deterministic classification facts at medium-impact, reversible,
   automatically verifiable, behavior-changing cross-file code with no external
   side effects. The active Policy must determine the refreshed route and V.

The first review and frozen-spec history remain immutable. A refreshed
classification, frozen specification, context, and independent design review are
required before implementation.
