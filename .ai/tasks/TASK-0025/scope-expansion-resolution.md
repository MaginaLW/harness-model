# TASK-0025 Scope Expansion Resolution

## Condition

`spec_changed` / narrow scope expansion discovered during H1 focused verification.

## Reproduced evidence

The frozen specification requires both
`tests/acceptance/test_phase_02_self_hosting.py` and
`tests/integration/test_phase_02_self_hosting.py`. Each file passes independently:

- acceptance: `2 passed`;
- integration: `4 passed`;
- E2E: `9 passed`.

The Policy-required full regression uses the repository default pytest prepend import mode.
Collecting the two required same-basename files together exits 2 before tests run with an
`import file mismatch`: both are imported as top-level module `test_phase_02_self_hosting`.
Removing caches does not change that deterministic module identity collision.

## Narrow resolution

Add exactly one business path, `tests/acceptance/__init__.py`, to TASK-0025 `allowed_scope` and
DU-001 `impact_scope`. After renewed spec approval, the file must be empty. It makes only the
acceptance directory a Python package, so acceptance and integration receive distinct module
identities while preserving the two filenames frozen by Chapter 13.1.

Rejected alternatives are broader or less auditable: changing repository-wide pytest import mode,
renaming a frozen candidate file, adding package markers to the large integration suite, or
mutating `sys.modules` from test code. No runtime, Policy, schema, manifest, Hook, existing test,
dependency, or lock-file change is required.

## Existing work disposition

Preserve the four current in-scope H1 files and all immutable TASK-0025 governance history. No
targeted mutation launched, no action approval was consumed, no state file changed, and no commit,
push, merge, deploy, delete, credential, network, paid, or external-model action occurred.
