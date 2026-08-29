# TASK-0026 scope expansion resolution

## Trigger

The first complete V1 run for subject `cfd447ef7c997bd2ad80d778d8229d1420ef0afb`
failed only in `regression_tests` and `coverage_xml`. Both failures came from
`tests/e2e/test_phase_02_self_hosting_scenario.py`: the TASK-0025 historical replay
bundle's worktree bytes did not match its immutable manifest.

## Reproduced facts

- Host Git configuration reports `core.autocrlf=true` from the system Git config.
- For `files/01-task.yaml`, the manifest and raw Git blob SHA-256 are both
  `74dc529bc0c803ea8a09dd0b31647294369dd6cea854fd17a7c84352d930f8ed`.
- The current Windows worktree file SHA-256 is
  `ec89eb07b9591da938b9a553b7134aeb5fb248b26f3a57ed5a9821486d3b2f10` and its
  bytes contain CRLF checkout conversion.
- The same mismatch affects all 20 manifest-bound files. No file has a Git diff;
  the mismatch is checkout conversion, not a changed blob or stale manifest.
- The failed run recorded `1 failed, 1517 passed, 4 skipped, 9 errors`; unit tests,
  contract, scope, Ruff, format, smoke, mypy and diff coverage passed.

## Bounded resolution

Expand business scope only to the repository root `.gitattributes` and declare
`.ai/tasks/*/historical-snapshots/** text eol=lf`. This keeps historical artifacts
as text while requiring LF checkout on every platform. Do not update the snapshot,
manifest, expected hashes, E2E assertions, Policy, source, dependency files or CI.

After a current design review and version-bound spec approval, implement the single
attribute rule, materialize the existing Git blobs under that rule, prove all 20
worktree SHA-256 values match the unchanged manifest, and rerun focused E2E plus the
full V1 plan. The scope expansion remains REVIEW; it is not an authorization to
lower verification or modify any historical evidence.
