# TASK-0030 CI runner temporary-root resolution

## Observed failure

GitHub Actions run `33410732408` for PR `#2` checked out head
`afcb0055578bbab58959f6012201fd9a66e388bb`, attached the exact event SHA to
`codex/verification-timeout-hardening`, validated contracts, read repository identity, and resolved
`TASK-0030`. The formal `Verify and Gate` step then stopped before executing any Policy check with
`CI run directory is not an operating-system temporary directory`; Gate did not run and diagnostics
upload succeeded.

The workflow used `$RUNNER_TEMP/aiflow`, which resolves under the GitHub runner workspace. On the
Linux runner, Python's `tempfile.gettempdir()` remained `/tmp`, so the CLI's strict-descendant check
correctly rejected the different runner root. This is a workflow/runtime temporary-root mismatch,
not a branch attachment, task resolution, or Policy check failure.

## Bounded recovery

Only for the formal `Verify and Gate` step, bind `TMPDIR` through step `env` to
`${{ runner.temp }}` and derive `run_dir` as `$TMPDIR/aiflow`. Python then evaluates the documented
runner temporary directory as its operating-system temporary root, while the existing CLI still
requires an existing strict descendant and still requires external evidence to remain inside that
directory. Keep diagnostics upload on the same `${{ runner.temp }}/aiflow` path.

Do not change Python verifier code, accept arbitrary runner paths, remove strict-descendant or
output-containment validation, export the temporary-root override to bootstrap or unrelated steps,
or reuse historical evidence, review, or approvals for the expanded subject.

## Verification and audit

Add workflow contract assertions for the formal-only environment and consistent run/evidence/Gate/
artifact paths. Add a platform-independent verification-plan test that models distinct Python and
runner temporary roots: the configured strict descendant passes only when the Python temporary root
is bound to it, while an existing sibling root remains rejected. Rerun Policy V1, obtain new design
and implementation reviews and version-bound owner approvals, pass local Gate, update PR `#2`, and
require its final head to complete formal verification and Gate. Runs `33403951577` and `33410732408`
remain immutable failed platform evidence.
