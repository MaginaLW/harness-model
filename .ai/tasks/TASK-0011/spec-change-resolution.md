# TASK-0011 spec change resolution

- Condition: `spec_changed`
- Subject commit: `1481a0123b8bc55371bdbca3aa5fac63f79e45c6`
- Existing implementation disposition: preserve the current Chapter 11.1 implementation and tests without executing final verification.
- Scope addition: `docs/implementation/chapter-09-v2-policy-contracts.md` may only clarify that Policy `2.0.0` was the Chapter 9 historical active baseline and direct readers to the active Policy bundle for the current version.
- Version boundary: historical tasks, classifications, evidence, state records, and fixtures remain bound to Policy `2.0.0`; only the four active Policy documents advance together to `2.1.0` after fresh approval.
- Review history: `design-review-context-v2.json` and `design-review-input-v2.json` were never recorded and are superseded by the post-expansion v3 design review.
- Newly added scope remains untouched until the expanded specification is reclassified, refrozen, independently reviewed, and explicitly approved.

Resolution: reclassify and refreeze the expanded specification, then require a fresh design approval before modifying the newly added scope.
