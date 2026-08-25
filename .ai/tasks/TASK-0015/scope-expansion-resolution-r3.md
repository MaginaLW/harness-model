# TASK-0015 scope declaration correction (r3)

## Trigger

Final diff review found that the implementation changed three directly relevant test files that were not listed in `allowed_scope`. It also found that DU-001's `impact_scope` did not fully mirror already-governed implementation and contract paths.

## Exact declaration changes

Added to `allowed_scope`:

- `tests/integration/test_approve_command.py`
- `tests/integration/test_mutation_manifest_contract.py`
- `tests/unit/test_review_package.py`

Added to DU-001 `impact_scope`:

- `src/aiflow/mutation_runner.py`
- `.ai/templates/evidence-v2.json`
- `tests/unit/test_mutation_runner.py`
- `tests/unit/test_review_package.py`
- `tests/integration/test_approve_command.py`
- `tests/integration/test_mutation_manifest_contract.py`

## Assessment

All additions are part of the existing Chapter 11.5 V2 mutation-evidence goal: runner authorization, the canonical V2 template, approval/review-package binding, mutation-manifest contracts, and their direct tests. The decision unit remains `REVIEW / V2`; permissions, external side effects, forbidden actions, and the requirement for a separate single-use action approval are unchanged.

Existing implementation is preserved for reassessment. No real targeted mutation has been executed.
