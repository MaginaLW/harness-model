# TASK-0013 baseline transition

Recorded for the `spec_changed` reassessment that separates the dependency's
external merge fact from TASK-0013's clean execution baseline.

## Immutable facts

- TASK-0012 external merge commit recorded by `merge_recorded`:
  `e5b00f4502354ef9d18ad7d1f9f1c52e27aac604`.
- TASK-0012 state after the authorized close operation: `MERGED`.
- Local close-receipt governance commit:
  `dc49293936ae8f705b7a474dc5c7b0ac0c981865`.
- The close-receipt commit's only parent:
  `e5b00f4502354ef9d18ad7d1f9f1c52e27aac604`.
- The close-receipt commit modifies exactly:
  `.ai/tasks/TASK-0012/events.jsonl` and `.ai/tasks/TASK-0012/task.yaml`.
- `origin/main` remains at the external merge commit; the close receipt is local
  only. No push, merge, or deploy was executed.

## Binding decision

The external merge commit remains the dependency evidence. TASK-0013 uses the
clean post-close governance commit as both `base_commit` and initial
`subject_commit`:
`dc49293936ae8f705b7a474dc5c7b0ac0c981865`.

The CLI has no command for rebinding an unimplemented task's base commit. Under
the repository agreement for an unimplemented CLI operation, the two task fields
and the specification are updated directly while the task is `ESCALATED`; this
file is the resolution evidence. The old classification, frozen specification,
and design reviews remain immutable audit history but are not current. Before
implementation, AI Flow must record this resolution, reclassify at the new
binding, refreeze, rebuild the design context, obtain a new design review, and
obtain a new user specification approval.
