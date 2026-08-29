# TASK-0028 specification-change resolution

## Trigger

Independent design review `REV-0053` (`REQUEST_CHANGES`) found that the initial
documentation-only specification was not executable. At the frozen source version,
V2 `verify --ci` always projected `MUTATION_EVIDENCE_MISSING` and external CI pre-review
evidence could not independently satisfy the Gate's local-final implementation-review
requirements.

## Preserved evidence

- Rejected design context:
  `5b77b4c2753cc4cc6d1bdfe888421add63e7e54f21e46f4b9d1bafe2b3559bf1`
- Rejected frozen specification:
  `24f7ef3edf2862d8899bf17d64873020b37d8a2f4a3cee3374d706c8f7ac4eb0`
- Review record: `reviews/REV-0053-r0001.json`
- Open finding: `RF-001`

## Bounded resolution

The task now includes only the two runtime seams and two matching integration test files
needed to implement and prove a fail-closed split between current local-final V2 facts and
external CI execution/attestation facts. The three Chapter 13 documentation/state paths
remain in scope. Evidence schema, evidence snapshot implementation, mutation consumer,
runner, Policy, manifest, workflow, Hooks and unrelated tests remain out of scope.

The updated decision unit explicitly requires `REVIEW / V2`, current-subject targeted
mutation and independent verification. It also preserves separate single-use approvals
for each local mutation transaction and for the exact isolated CI-simulation temporary
targets. No source, test, documentation, state, mutation, CI simulation, temporary
worktree, deletion, push, merge or other external action occurred before this resolution.

## Next binding

Reclassify the expanded decision unit under active Policy, freeze the new specification,
obtain a new independent design review, resolve or supersede `RF-001` with concrete
review evidence, and request version-bound user specification approval before any
implementation.
