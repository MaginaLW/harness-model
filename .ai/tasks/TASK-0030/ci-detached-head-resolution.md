# TASK-0030 CI detached-HEAD resolution

## Observed failure

GitHub Actions run `33403951577` for PR `#2` resolved `TASK-0030` and checked out head
`dcca06fbbab73af2c047f2f0e9cb8bafbf5c7c75`. The checkout log explicitly entered detached
HEAD. `Verify and Gate` then stopped before planning or executing any required check with
`CI Git verification context is stale`; no CI evidence or Gate JSON was produced.

The task remains bound to branch `codex/verification-timeout-hardening`. The committed chain
is valid (`37dce2a` -> subject `26e57b8` -> attestation `dcca06f`), and every attestation path
is under `.ai/tasks/TASK-0030/**`. Evaluating the same commits on the attached local branch
passes committed, attestation and worktree scope. The rejected fact is therefore the runner's
branch value `DETACHED`, which correctly differs from the task binding.

## Bounded recovery

Keep checkout pinned to the immutable event head SHA with full history. Before any formal
verification, require a non-empty `github.head_ref`, confirm checkout HEAD equals the event
SHA, attach that same commit to the PR source branch with `git switch --force-create`, then
confirm both symbolic branch and HEAD SHA. Add an integration contract that fixes the step's
environment, commands and ordering, and document why the workflow binds both commit and branch.

Do not sync the governance-only attestation into the business subject, checkout only a moving
branch ref, fetch replacement content, weaken branch equality, alter task identity, or reuse the
historical V1 evidence, implementation review or code approval for the expanded subject.

## Verification and audit

After owner approval of the expanded frozen specification, implement only the already allowlisted
workflow, workflow integration test and corresponding current documentation. Create a new subject,
rerun the full Policy V1, obtain a new independent implementation review and code approval, pass the
local Gate, update PR `#2`, and require a new real `ai-quality-gate` run to complete formal resolve,
verify, Gate and diagnostics upload. Run `33403951577` remains immutable failed platform evidence.
