# TASK-0015 runner-preflight synchronized-subject resolution (r9)

- Condition: `spec_changed`
- Previous subject: `2599e878a37d8c970bd70c1257943381f08e4155`
- Current synchronized subject: `c1a66567ba844f51d569aa3adb818febd1a0793e`
- Required route and verification level: `REVIEW + V2`

The second user-approved action was correctly bound and irreversibly consumed, but the runner stopped before its first detached mutation worktree because an obsolete duplicate `HEAD == subject` preflight rejected the current-task governance attestation HEAD. Event 93, the action-use receipt, and the exclusive launch claim agree; the reserved MUTRUN directory is empty and no detector or mutant executed. The consumed action remains immutable, non-reusable history.

The synchronized subject preserves the authoritative final Git assessment and action/receipt/ledger replay, then requires the fixed subject to be an ancestor of the governed HEAD. Controlled mutation inputs must still match the subject, checkout filters remain forbidden, the main-tree snapshot must remain unchanged, and every disposable worktree still checks out the exact subject. Business tails, other-task governance, dirty scope, repository/branch changes, and equivalent-tree non-ancestor histories continue to fail before action consumption.

Focused regression passed 205 tests with one platform-condition skip. Final branch-coverage verification passed 948 tests with four Windows platform-condition skips; Ruff, formatting, mypy, diff-check, AI Flow validation, 87% total coverage, and 91% task-base diff coverage passed. Two independent reviewers found no P0-P2 issue and marked the checkpoint safe.

The specification, Policy, scope, REVIEW/V2 route, permissions, and separate single-use action approval requirement are unchanged. Action `36fbb908…` remains unused but stale on an older subject; action `165b0ba2…` is consumed and cannot be replayed. Any real targeted mutation against this subject requires a newly proposed digest and a new explicit user approval. No successful mutation execution, push, merge, deploy, repository-data deletion, credential use, paid external call, or network call occurred.
