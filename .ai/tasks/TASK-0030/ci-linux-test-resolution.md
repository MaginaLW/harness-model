# TASK-0030 Linux CI test resolution

## Observed failure

GitHub Actions run `33445448671` for PR `#2` evaluated attestation head
`7796d1a36aa81e0efdf321841556079eb740c5dd`. Exact event-SHA checkout, source-branch
attachment, contract validation, repository identity, task resolution, locked installation, and
the unified runner/Python temporary root all succeeded. Formal V1 unit tests passed, while both
regression and coverage reported the same two failures (`2 failed, 1600 passed`), so Gate correctly
returned `GATE_EVIDENCE_STALE` and `GATE_EVIDENCE_NOT_PASSED`.

`tests/e2e/test_clean_checkout.py` ran inside the verification runner's intentional minimal
environment (`PATH=/bin:/usr/bin`). The uv-created active Python had no `pip`, and the test's
fallback incorrectly required `uv` to remain discoverable through inherited PATH. The runner
is correct to hide that executable.

`tests/integration/test_verification_evidence_flow.py` performed its first V1 verification with
the real Policy plan, despite already defining a controlled full-category plan for this evidence
contract test. A nested environment-sensitive check failed and moved the fixture task to `FAILED`;
the later `Task is not ready for verification` message was only the correct state-machine rejection
of replay from that failed state.

## Bounded recovery

Keep the production Policy, process-runner environment, verification service, state machine,
workflow, thresholds, and required checks unchanged.

1. In the clean-checkout E2E helper, retain the current-interpreter `pip` path when available. If
   the active environment has no `pip`, use its validated base interpreter to run `-m pip` and
   install the clean clone into the same isolated target. Continue running the documented commands
   with the active interpreter and isolated `PYTHONPATH`; do not search inherited PATH for `uv`.
2. In the V0/V1 evidence reproduction test, bind `parse_verification_plan` to the existing
   `_full_category_plan()` fixture before verification. The test must still produce every required
   V0/V1 check identity, replay its recorded command, and pass Gate, but must not recursively test
   the host's real V1 toolchain.

No production fallback, platform exception, runner PATH widening, FAILED-to-VERIFYING transition,
automatic retry, reduced check, lowered threshold, or stale evidence reuse is allowed.

## Verification and audit

Add a focused assertion for the no-pip base-interpreter installer path, run the real clean-checkout
E2E, run both evidence-reproduction parameters with the controlled plan, then rerun locked local V1,
independent implementation review, fresh owner code approval, local Gate, and final PR CI. Preserve
run `33445448671` and artifact `ai-flow-TASK-0030` (`9778029326`) as immutable failed platform
evidence.
