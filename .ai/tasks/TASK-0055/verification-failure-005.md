# Fifth complete V2 result and bounded follow-up

The fixed subject is `eb4c49a4ff77ca07f210fceae707495c8dece8be`; admission
HEAD is `12b8e76e195e6f13772d3d692b80fca06422d31f` on
`codex/e4-report-import`. Independent native run
`run-20260930T001625595307Z` began at `2026-09-30T00:16:16Z` and ended
normally at `2026-09-30T01:07:11Z`. The native CLI and outer launcher returned
0, but verification concluded **failed** and TASK-0055 is FAILED. This
portable note records the actual result, not a replacement passing evidence.

## Complete required-check results

All 14 required checks have native results: nine passed and five failed.
Timeout exit codes are null because the command did not complete normally.

| Check | Status | Exit code | Timed out | Duration, ms |
| --- | --- | --- | --- | --- |
| contract | passed | 0 | false | 2187 |
| scope | passed | 0 | false | 2109 |
| ruff_check | passed | 0 | false | 2282 |
| ruff_format_check | passed | 0 | false | 359 |
| smoke | passed | 0 | false | 328 |
| unit_tests | failed | null | true | 300406 |
| regression_tests | failed | null | true | 900203 |
| mypy | passed | 0 | false | 3000 |
| coverage_xml | failed | null | true | 1200328 |
| diff_coverage | failed | 1 | false | 1031 |
| acceptance | passed | 0 | false | 1390 |
| integration | failed | null | true | 600172 |
| targeted_mutation | passed | 0 | false | 0 |
| independent_verifier | passed | 0 | false | 0 |

Acceptance completed with 9 passed in 1.07 seconds; mypy checked 42 source
files. Unit, regression, coverage and integration have no completed pytest
summary. Diff coverage failed because coverage.xml was absent; total and diff
coverage percentages remain unknown. No original test, skip, deadline, Policy,
quality threshold or native execution environment was changed for this run.

The last two zero durations are native evidence projections, not measured
mutation runtimes or a completed implementation Review. All five canonical
mutations actually ran: baseline exit 0, mutant exit 1, killed, no timeout.
Their measured durations were 1313, 9625, 1422, 1156 and 1328 ms. The native
loader independently checked their evidence and `main_tree_unchanged: true`.

## Immutable evidence and action consumption

The task evidence, native run evidence and create-only
`logs/run-20260930T001625595307Z/failed-evidence.raw.json` are byte-identical.
The raw SHA-256 is
`59997434080ad6dc95d602a23043e184d765dc20ae221160419a7e6504971726`.
The validated V2 snapshot is
`9db5f520a169f48b5abc5aa8bf6e09676bdacaceddd729b8d5a0e9a347c9371c`.
The frozen verifier context is
`5fe7f31a6879f4de5bad8575e06cf3443f27dcfdc53ace906c0cf4b34bca2987`.

Mutation evidence remains at
`.ai/tasks/TASK-0055/logs/MUTRUN-20260930T010643Z-5e9ab675f549a320/targeted-mutation/evidence.json`;
its canonical SHA-256 is
`7b1c82f048ac9a2d2da8a904de849f0570db451cd511b168278628587b569cc1`.
Action005 SHA-256 is
`e1a64fc542d424fccca61d7c28135ce8d71c5dfd19e885106903c0b027614d6a`.
It was consumed once at `2026-09-30T01:06:42Z`, recorded at event sequence
44. Its new-worktree physical receipt identity was independently matched.
Sequence 43 started verification and sequence 45 recorded failure. Earlier
events, failures, archives and consumed receipts remain intact. The fifth
action cannot be reused.

Original stdout/stderr, JUnit if produced, archive audit, launcher start/exit
records and `logs/verification-outer-005.log` remain private ignored files.
They retain their original bytes and runtime provenance. This tracked note
does not sanitize or substitute for the raw evidence.

## Bounded unit diagnosis after the complete run

Unit partial stdout contained 1503 result markers, including failures at
collected ordinals 1344 and 1356, without completed failure tracebacks.
Fresh collection of all 1738 unit cases on the same source mapped them to:

- `tests/unit/test_runner_inspection.py::test_parent_failure_keeps_classification_and_never_reads_leaf[wrong_type]`
- `tests/unit/test_runner_inspection.py::test_native_job_deadline_stops_exact_descendants_and_preserves_unrelated_process[stdout_descendant]`

After all formal verification processes ended, these two unchanged cases
ran through the native process runner's unchanged minimal environment.
Both passed in 12.64 seconds, process exit 0, no timeout; native runner
duration was 13016 ms. The diagnostic retained both cases and their existing
deadlines. Its private collection, JUnit, stdout/stderr and result are under
`.venv/external-review-perfdiag/native-env-005/`. The diagnostic verified the
formal raw evidence SHA-256 was unchanged.

This did not reproduce or identify either earlier failure cause, establish
complete unit success, replace V2, or justify an increased verification
budget. The causes of the complete-run timeouts and partial failures remain
unknown. Observed system-disk queues and progress differences from the fourth
run do not establish causation or an optimization benefit. The relocated
source and locked editable environment still permit ordinary test temporary
files on the system disk. No unknown process or system setting was changed,
and no temporary-directory, home-directory or runner-environment workaround
was installed.

## Current gate and next dependency

Read-only native status reports FAILED, REVIEW/V2, fresh classification,
current approvals, stale failed evidence and
`Missing: retry_reason_or_escalation`. Native Gate is REJECT with
`GATE_STATE_INVALID`, `GATE_EVIDENCE_STALE`, `GATE_EVIDENCE_NOT_PASSED`,
`GATE_V2_EVIDENCE_NOT_FINAL`, `GATE_V2_REVIEW_STALE`,
`GATE_V2_CHECKS_INCOMPLETE` and `GATE_CODE_APPROVAL_STALE`.

No failed evidence is finalized and no implementation approval is requested
on it. Implementation Review, final verification, owner code decision,
passing source/publisher Gates, push and merge remain incomplete. The owner's
existing push/merge authorization is preserved; no remote write occurred.

A further complete attempt requires an adequate ordinary verification
environment, a recorded retry reason, and a new exact-subject single-use
canonical mutation action while preserving every original check and deadline.
An environment or runner change beyond the frozen specification must be
separately scoped and governed before use. E4.3/E4.4, external providers,
training, devices and later phases are not authorized by this result.
