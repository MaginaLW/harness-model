# TASK-0016 classification baseline resolution

## Observed mismatch

- TASK-0016 was created with both `base_commit` and `subject_commit` bound to
  `1342cd23302cdb918b19c2fc42aeaaaa3ee20639`.
- The task-governance initialization was then recorded as
  `238a9b6682790c7c64f786cd3c2ce322d80ada98`, a direct descendant of that
  commit.
- Commit `238a9b6682790c7c64f786cd3c2ce322d80ada98` contains only TASK-0016 task-local
  governance artifacts under `.ai/tasks/TASK-0016/`; it contains no allowed-scope
  projection file, runtime code, Policy, schema, test, or dependency change.
- Classification recovery requires the observed repository `HEAD` to equal the
  task `subject_commit`, so the earlier subject binding cannot be reused after
  this governance-only attestation.
- The current `aiflow sync` path intentionally does not synthesize a subject-sync
  event when the intervening commit contains only current-task governance files.
  Therefore no existing CLI command can repair this specific recovery mismatch;
  this file and the associated resolution event record that implementation gap.

## Resolution

- Preserve the original `base_commit` at
  `1342cd23302cdb918b19c2fc42aeaaaa3ee20639`, retaining the full ancestry and
  scope chain from task creation.
- Synchronize only `subject_commit` to
  `238a9b6682790c7c64f786cd3c2ce322d80ada98` as the smallest baseline repair.
- Preserve the original creation binding and all previous attempts in
  `events.jsonl`; do not rewrite or reset Git history.
- Correct the current task-goal wording from the unsupported generic phrase
  `close receipt` to the precise fact `merge-record governance commit`. The
  immutable creation event remains unchanged as historical input.
- Keep TASK-0016 in `BLOCKED` state while computing the new deterministic
  classification input. This is an explicit recovery decision for a missing CLI
  path, not a claim that standard `aiflow sync` performed the synchronization.

## Authorization boundary

- The earlier manual authorization is bound to classification input
  `3d7b31192e98e8775facaaf94b6556225a4993e5dab7ac1fe26dae740739f446`
  and cannot authorize a digest produced from the rebound baseline and corrected
  goal.
- A new explicit authorization bound to the new full classification-input digest
  and Policy digest is required before `BLOCK` may become `REVIEW`; verification
  remains `V1`.
- This resolution does not authorize implementation, mutation execution, push,
  merge, deployment, deletion, or any other forbidden action.
