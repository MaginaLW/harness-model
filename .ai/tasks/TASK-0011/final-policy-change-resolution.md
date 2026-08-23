# TASK-0011 final Policy change resolution

- Condition: `policy_changed`
- Subject commit: `de0e2603b6e89928597df8479d41c5f1fa13b06f`
- Previous approved Policy digest: `9dd10d4839c77ef624856ea593683a28a607980673d3fbacd76e759e9fdbaca4`
- Final active Policy version: `2.1.0`
- Final active Policy digest: `f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`
- Four-file consistency: `hard-rules.yaml`, `routing.yaml`, `verification-levels.yaml`, and `permissions.yaml` all declare `policy_version: "2.1.0"`.
- Semantic boundary: the executable offline V2 `acceptance` and `integration` definitions are the only Policy behavior change; the other three Policy documents changed only their version fields.
- Historical boundary: prior tasks, classifications, approvals, evidence, state records, and fixtures retain their original Policy `2.0.0` bindings. The Chapter 9 implementation record now explicitly describes `2.0.0` as its historical active baseline.
- Verification boundary: `tests/unit/test_policy.py` passed (`15 passed`), but governed final V1 verification, remaining Chapter 11.1 documentation/state projection, and implementation review are deferred until a fresh specification approval is bound to the final Policy digest.

Resolution: reclassify and refreeze against the final Policy `2.1.0` digest, record an independent design review, and require one final fresh specification approval before continuing implementation and final verification.
