# TASK-0025 verification-unavailable resolution

## Bound blocker

- Blocking governance commit: `527961a194851a77033a1aa088749d83caeb7d3e`.
- Block condition: `verification_unavailable`.
- Previous frozen specification SHA-256:
  `625ac850cfbfedc05c5af636b4f274faacc8325aa806caee7f47f9ec16bb5a4c`.
- The first H1 mutation action
  `9740af8fafb53760e829f94fd3c34d252a742fd42f2928e16272f32ee91d2cfa`
  was consumed exactly once and is not reusable.

The frozen acceptance text required regression/E2E to consume the same current subject's real
mutation artifact and Gate-positive implementation review. Production V2 executes regression
before its first mutation collection, while `REV-0045 r0001` is `REQUEST_CHANGES`. The original
requirement was therefore cyclic and could not be satisfied without pre-executing/reusing a
single-use action, changing runtime verification order, or recursively changing the subject.

## Resolution evidence

- Revised specification proposal commit:
  `5f272b10996c551ca20a94c545b41af7a3f8dfcb`.
- Revised specification SHA-256:
  `04f951e922a1183b750111b101b9e47532c9bd9261225c289e6faa5237262318`.
- The revision keeps `REVIEW / V2`, independent verification, five fixed mutations, current
  outer V2 evidence, independent implementation review, code approval, and Gate as the only
  authoritative readiness path.
- Versioned E2E separates a real historical pre-evidence/mutation replay, the historical
  `REQUEST_CHANGES` fail-closed result, and an explicitly non-authoritative positive contract
  model. Neither historical nor modeled facts can become current evidence or readiness.
- An independent design-draft review approved these boundaries after the bundle provenance,
  complete inputs, per-file and bundle digests, and non-task input reuse rules were specified.
- A local feasibility experiment cloned the repository into an OS temporary directory, placed a
  local `main` branch at source governance commit
  `ef1f32d42b935ef2f7d8acfdc805a95399b33317`, restored the real ignored mutation artifact and
  five logs to their exact refs, and replayed them successfully through the public loader and
  consumer without monkeypatching production Git or loader behavior.

## Authorization and retained work

The user explicitly authorized resolving `verification_unavailable` from `BLOCK` to `REVIEW`
while retaining `V2`, bound to governance commit `527961a`, proposal commit `5f272b1`, and the
revised specification digest above. The authorization permits only local resolution,
reclassification, specification freeze, and independent design review. It does not authorize a
targeted mutation or any remote operation.

The five-file H1 implementation, the in-progress RF-001/RF-003 fixes, the consumed action receipt,
and all historical evidence remain preserved. No old action or evidence is authorized for reuse.
