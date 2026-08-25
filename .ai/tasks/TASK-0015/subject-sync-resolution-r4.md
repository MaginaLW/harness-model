# TASK-0015 synchronized-subject resolution (r4)

- Condition: `spec_changed`
- Previous subject: `3b5d6f3bb2784994bf8795729dc5edbf050dd191`
- Current synchronized subject: `88335978dfef9a6421903b329b9745295655ff39`
- Required route and verification level: `REVIEW + V2`

AI Flow validated the complete committed range against the corrected r10 `allowed_scope` before synchronizing checkpoint `8833597`. Independent design review `REV-0010` and the final read-only diff review found no blocking issue and declared the exact checkpoint candidate safe to create.

Before the checkpoint, the security-focused suite passed 40 tests, the full suite passed 922 tests with four platform-condition skips, Ruff/format/mypy/diff-check passed, total branch coverage was 87%, and task-base diff coverage was 91% against a 90% requirement.

The specification and Policy are unchanged. Reclassification, refreeze, and a fresh subject-bound review/approval are required only because approvals cannot carry across a synchronized subject change. No real targeted mutation, push, merge, deploy, delete, credential use, or paid external call occurred.
