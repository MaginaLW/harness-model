# TASK-0015 second specification change resolution

- Condition: `spec_changed`
- Subject commit: `17ab98cf879cf913e91dfcdf69861b387eabf7ac`
- Required route and verification level: `REVIEW + V2`

During implementation preflight, the existing contract regression
`tests/unit/test_contracts.py::test_v2_evidence_template_satisfies_the_v2_contract`
was found to validate `.ai/templates/evidence-v2.json`. The approved design adds
required immutable mutation-artifact identity fields to the V2 evidence schema, so
the non-authoritative template is a direct, mechanically necessary contract surface.

The current task record adds only `.ai/templates/evidence-v2.json` to `allowed_scope`
and requires it to remain schema-valid. This does not expand runtime behavior, change
the mutation manifest/runner/evidence artifact contract, lower `REVIEW + V2`, or
authorize a real mutation run. In-scope TDD work is preserved; no out-of-scope file
was edited before this reassessment.

Reclassification, refreeze, a current design review, and a fresh specification
approval are required before implementation resumes.
