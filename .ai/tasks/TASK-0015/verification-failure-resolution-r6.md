# TASK-0015 first authorized V2 verification failure (r6)

## Result

The user-approved action `36fbb90847712e2cc701a97c1492607706b23cce3d12b22a94c650608c44ff6b` was presented to one full local V2 verification at `2026-08-25T14:43:16Z`. All twelve ordinary checks and the independent-verifier fact passed. The `targeted_mutation` check failed before collection and the task entered `FAILED` at `2026-08-25T14:55:30Z`.

No mutation process launched. There is no consumed-action event, action-use receipt, launch claim, MUTRUN record, or mutation worktree. The action remained unused.

## Root cause

The governed code subject is `4f50383e9dcf95fc8b264858b8bd510d31f2101a`; observed HEAD is the descendant governance attestation `c3402c76bd37a04f38ecd1555f445fa732193b71`. The committed `subject..HEAD` range contains only TASK-0015 governance files, which `evaluate_verification_git_context(..., mode="final")` accepts.

`mutation_evidence._validate_bindings` independently required `context.head == subject` before action discovery. It therefore raised `MUTATION_EVIDENCE_BINDING_STALE`, which the V2 projection reported as `MUTATION_EVIDENCE_INVALID`. This duplicated and contradicted the authoritative Git verification assessment.

## Resolution direction

Reuse the read-only final `evaluate_verification_git_context` assessment inside mutation binding validation. Require its original subject to remain unchanged and require gate-eligible committed, attestation, and worktree scope. This permits only current-task governance attestation while continuing to reject business HEAD synchronization, other-task governance, dirty business paths, repository/branch changes, and ancestry failures.

The existing Chapter 11.5 goal, allowed scope, REVIEW/V2 route, permissions, and verification level remain unchanged. A repaired code subject must be reclassified, refrozen, independently reviewed, and separately action-approved before any real mutation run.
