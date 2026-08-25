# TASK-0015 consumed-action preflight failure resolution (r8)

- Subject: `2599e878a37d8c970bd70c1257943381f08e4155`
- Governance attestation HEAD: `b3aa524224fc5cce8b16b76b238bc49d24c0660c`
- Action SHA-256: `165b0ba22733e2c499613766b82cea5d1c00b93d07a3633dcfbb6be05441dd33`
- Reserved record: `MUTRUN-20260825T153831Z-835a581cb1cf88cc`
- Verification conclusion: `failed`

The user explicitly approved one targeted-mutation action for the current subject. AI Flow correctly recorded the exact action approval, consumed it once in event 93, created the immutable action-use receipt, and reserved the exclusive runner launch claim. The action is not reusable and must not be replayed.

All ordinary V2 checks and the independent-verifier check passed. Targeted mutation failed with the public fail-closed projection `MUTATION_EVIDENCE_INVALID`. The reserved MUTRUN directory is empty, no targeted-mutation artifact or probe log exists, no temporary mutation worktree remains registered, and the main worktree contains no mutation changes.

The exact internal failure occurred before the first detached mutation worktree or detector execution. `mutation_evidence._validate_bindings` correctly accepted the current-task-only governance attestation after the fixed subject, but `mutation_runner._validate_subject` still required `HEAD == subject_commit`. The attestation HEAD is a descendant of the fixed subject and changes only `.ai/tasks/TASK-0015/**`, so the runner raised `MUTATION_SUBJECT_INVALID` after launch claim creation. `verification_service` deliberately projected that non-action exception as the generic `MUTATION_EVIDENCE_INVALID` sentinel.

Remediation is to preserve the authoritative action replay and current-task governance-only assessment, require fixed `base -> subject -> attestation HEAD` ancestry at runner preflight, keep controlled mutation inputs identical to the subject, and continue checking out detached mutation worktrees at the exact subject. Regression coverage must prove governance attestation reaches preflight while business, other-task, dirty, and non-ancestor histories still fail before action consumption. The consumed action and its failed-run evidence remain immutable history; any later real mutation attempt requires a new synchronized subject and a separately explicit action approval.

No successful mutation execution, push, merge, deploy, repository-data deletion, credential use, paid external call, or network call occurred.

## Implemented outcome

`mutation_runner._validate_subject` now verifies the full subject object, a full governed HEAD, and `subject -> governed HEAD` ancestry instead of requiring equality. Production entry still performs the authoritative current-task governance-only Git assessment and full action/receipt/ledger replay before the exclusive launch claim. Controlled mutation inputs, checkout filters, main-tree snapshot comparison, and detached worktrees fixed at the exact subject are unchanged.

Unit regression covers governance-attestation descendants plus invalid, unresolved, malformed, and non-ancestor histories. A real-Git integration regression consumes a test-only action, passes the production runner subject preflight with a current-task governance descendant, and stops at the next controlled-path seam before any detector or mutation; the prior equality implementation fails that test. Existing integration cases continue to reject business, other-task, and equivalent-tree non-ancestor tails before action consumption.

Focused runner/evidence/verification regression passed 205 tests with one platform-condition skip. Final branch-coverage verification passed 948 tests with four Windows platform-condition skips; Ruff, formatting, mypy, AI Flow validation, diff-check, 87% total coverage, and 91% task-base diff coverage passed. Two independent reviewers found no P0-P2 issue and marked the repair safe to checkpoint.
