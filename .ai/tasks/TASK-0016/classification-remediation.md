# TASK-0016 classification remediation

The initial `aiflow start` scaffold intentionally contained only the minimum
decision-unit contract and therefore classified fail closed as
`BLOCK / PREDICATE_FIELD_MISSING`.

DU-001 now records the complete current facts:

- the scope is explicit and limited to five documentation/progress-state paths;
- the projection is reversible in Git, has no external side effects, and requires
  no action approval;
- all required local verification tools are available and automatic checks will run;
- this is non-mechanical cross-file documentation/state work with medium impact,
  regression risk, and low error detectability because an incorrect projection
  would alter chapter entry and cumulative progress facts;
- no runtime behavior, code, Policy, manifest, mutation execution, deletion,
  deployment, push, or merge is in scope;
- all V2-specific requirements are false, while the conservative verification
  result remains V1.

These facts deliberately produce the default `REVIEW` route rather than AUTO:
the authoritative human progress projection and Chapter 12 entry have medium
impact even though the files are documentation.  The intended post-remediation
classification is therefore `REVIEW / V1`.

Because the persisted incomplete classification is BLOCK, moving to REVIEW is a
route downgrade and must retain AI Flow's explicit manual downgrade-authorization
gate.  This remediation record supplies evidence for `block_resolution`; it does
not itself authorize the downgrade, implementation, merge, push, or any mutation.
