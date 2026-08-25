# TASK-0015 post-failure synchronized-subject resolution (r7)

- Condition: `spec_changed`
- Previous subject: `4f50383e9dcf95fc8b264858b8bd510d31f2101a`
- Current synchronized subject: `2599e878a37d8c970bd70c1257943381f08e4155`
- Required route and verification level: `REVIEW + V2`

The first user-approved full V2 attempt passed every ordinary check but failed before action consumption because mutation binding validation incorrectly rejected current-task governance attestation after the fixed subject. No mutation launched and the old action has no consumed event, receipt, launch claim, MUTRUN record, or mutation worktree.

The synchronized retry subject reuses the authoritative final Git assessment and additionally requires the fixed `base -> subject -> attestation HEAD` ancestry chain before action consumption. It permits only current-task governance attestation and rejects business subject synchronization, other-task governance, dirty business scope, repository/branch changes, and equivalent-tree non-ancestor histories.

Focused regression passed 141 tests with one platform-condition skip. Final full branch-coverage verification passed 946 tests with four platform-condition skips; Ruff, formatting, mypy, diff-check, AI Flow validation, 87% total coverage, and 91% task-base diff coverage passed. Independent review closed both P1 findings and marked the retry safe to checkpoint.

The specification, Policy, REVIEW/V2 route, permissions, and separate single-use action approval requirement are unchanged. The old action file and approval remain historical evidence bound to the old subject and cannot authorize the new subject. No real targeted mutation, push, merge, deploy, delete, credential use, or paid external call occurred.
