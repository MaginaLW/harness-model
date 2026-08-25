# TASK-0015 real targeted-mutation survivor resolution (r10)

- Subject: `c1a66567ba844f51d569aa3adb818febd1a0793e`
- Action SHA-256: `afeaeaf100365eddb7f5d6a9179f884fb3ee3b1da7d6a1c1b179c5c91c196dcf`
- Mutation record: `MUTRUN-20260825T162049Z-5c624fda2231c77f`
- Canonical mutation-evidence SHA-256: `7c23de237e65e28b94d082473d42a6d3e4003332968a4b4f99a218d8d8a6cd66`
- Verification conclusion: `failed`
- Public reason: `MUTATION_EVIDENCE_NOT_KILLED`

The user-approved action was correctly bound, consumed once in event 107, launched, and completed with an immutable loader-validated artifact. The receipt records the artifact and canonical digest. All ordinary V2 checks and the independent-verifier check passed, the main tree remained unchanged, and all disposable worktrees were cleaned.

The fixed five-mutation run produced four killed mutations and one survivor. `MUT-V2-001`, `MUT-V2-002`, `MUT-V2-004`, and `MUT-V2-005` were killed. `MUT-V2-003` (`allow_nonpassing_required_check` against `approval._v2_evidence_current`) survived because its declared detector did not isolate the required-check safeguard: after the mutant bypassed the nonpassing-check guard, the synthetic test evidence still referenced no loadable task-local mutation artifact, so the downstream loader returned a failing fact and the test's broad `assert not` continued to pass.

The production safeguard remains fail-closed; the defect is in the mutation detector's ability to distinguish that guard from an independent downstream rejection. The minimal remediation is to make the declared detector force a valid passing downstream mutation fact, so baseline code rejects solely because the required check is nonpassing while the mutant returns true and is killed by the assertion. The canonical manifest identity and operator remain unchanged, and the detector file is already in the approved task scope.

Action `afeaeaf1…` is consumed and must not be replayed. Any later real mutation run requires a new synchronized subject, a new action digest, and a new explicit user approval. No push, merge, deploy, repository-data deletion, credential use, paid external call, or network call occurred.

## Implemented outcome

The declared detector now replaces only its downstream mutation-evidence consumer with an explicitly passing `TargetedMutationFacts` and records calls. Baseline production code rejects the failed required check before the downstream seam and the detector asserts that no downstream call occurred. Under `MUT-V2-003`, the disabled guard reaches the passing seam and returns true, so the detector's rejection assertion fails and kills the mutant. Production approval code, the canonical manifest, operator identity, and detector reference are unchanged.

Focused approval/manifest/runner regression passed 92 tests. Final branch-coverage verification passed 948 tests with four Windows platform-condition skips; Ruff, formatting, mypy, AI Flow validation, diff-check, 87% total coverage, and 91% task-base diff coverage passed. Two independent reviewers agreed that the survivor was a detector false negative rather than a production approval bypass, that the isolated test correction is the minimal sufficient repair, and that it is safe to commit as a retry implementation checkpoint. This is not a final mutation-gate pass; a new governed action remains required.
