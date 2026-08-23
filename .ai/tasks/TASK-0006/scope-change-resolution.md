# TASK-0006 fixture scope resolution

- Condition: `spec_changed`
- Frozen specification SHA-256: `cdfa3a3349e92c6596d78bc0aa6c0e6d9ba8dfcc12a686e36497e0266339a83d`
- Policy SHA-256: `81699424c71ecf0af58936e449e1683b03e632bac50cb7007a430dea5aa85e60`
- Subject commit: `e17a34dca5530dc71149004a5f5a5a6dad96ea70`

The committed V2 contract matrix contains two precise negative fixtures that
exercise rejection of unknown additional fields:

- `tests/fixtures/contracts/invalid/classification-v2.extra.json`
- `tests/fixtures/contracts/invalid/evidence-v2.extra.json`

Both paths are now listed in the task allowed scope and decision-unit impact
scope, and the specification names the extra-field rejection coverage. No other
scope is added. Reclassification and a fresh design/specification approval are
required before implementation resumes.
