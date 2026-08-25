# TASK-0015 final synchronized-subject resolution (r5)

- Condition: `spec_changed`
- Previous subject: `88335978dfef9a6421903b329b9745295655ff39`
- Current synchronized subject: `4f50383e9dcf95fc8b264858b8bd510d31f2101a`
- Required route and verification level: `REVIEW + V2`

AI Flow validated the committed range against the current `allowed_scope` before synchronizing the final security-hardening subject. This commit adds explicit receipt-ledger identity regression coverage, verifies every bound runner authorization field reaches authoritative replay exactly once, and closes the independently discovered Python `bool`-as-`int` receipt device/inode bypass by rejecting boolean identities.

Independent review confirmed the P1 was closed and declared the result safe to commit. The final security/integration set passed 191 tests with one platform-condition skip. The final full branch-coverage run passed 935 tests with four platform-condition skips; Ruff, formatting, mypy, diff-check, AI Flow validation, 87% total coverage, and 91% task-base diff coverage all passed.

The specification, Policy, REVIEW/V2 route, and separate single-use real-mutation action approval requirement are unchanged. No real targeted mutation, push, merge, deploy, delete, credential use, or paid external call occurred.
