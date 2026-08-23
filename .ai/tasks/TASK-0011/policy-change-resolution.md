# TASK-0011 Policy change resolution

## Trigger

The approved `2.0.0` Policy bundle had SHA-256 `81699424c71ecf0af58936e449e1683b03e632bac50cb7007a430dea5aa85e60`. Replacing the V2 acceptance and integration help placeholders with deterministic pytest commands changed the active bundle digest to the intermediate value `9dd10d4839c77ef624856ea593683a28a607980673d3fbacd76e759e9fdbaca4` and invalidated the original classification, design review, and specification approval as expected.

## Resolution boundary

Chapter 1 requires every semantic Policy change to increment `policy_version`. The task scope and specification therefore now name all four Policy documents and `tests/unit/test_policy.py`: the four documents must move together from `2.0.0` to `2.1.0`, while hard rules, routing, and permissions may change only their version field. Historical `2.0.0` tasks, evidence, fixtures, and Chapter 9/10 records remain immutable historical bindings.

The currently implemented acceptance/integration command and runner changes are preserved as unapproved in-scope work. Focused development checks reported `69 passed, 1 skipped`, but this is not final evidence and does not authorize continuation past the refreshed specification gate.

## Required continuation

Reclassify and refreeze the expanded specification against the intermediate Policy, obtain a new independent design review and explicit specification approval, then update all four Policy versions. That update will create the final `2.1.0` digest and must trigger another `policy_changed` freshness cycle before final verification. No push, merge, deploy, publish, deletion, live V2 passed claim, or task close is authorized.
