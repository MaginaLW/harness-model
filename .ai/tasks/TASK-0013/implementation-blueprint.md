# TASK-0013 implementation blueprint

Status: draft implementation aid only. This document does not freeze the spec,
authorize implementation, create a worktree, consume an action approval, or
change TASK-0013 out of its current `ESCALATED` reassessment state.

Dependency merge inspected: `e5b00f4502354ef9d18ad7d1f9f1c52e27aac604`.
Execution baseline after the TASK-0012 close-receipt governance commit:
`dc49293936ae8f705b7a474dc5c7b0ac0c981865`.

Read-only reconnaissance at the dependency merge baseline ran the five exact manifest node IDs in
the main worktree with pytest plugin autoload disabled and `PYTHONPATH=src`; pytest
reported `6 passed in 2.83s` because one selected node is parametrized. This only
confirms the current detectors' baseline behavior. It is not isolated mutation
evidence, a V1 result, or authorization to run a mutant.

## Public contract

`src/aiflow/mutation_runner.py` exposes only:

```python
@dataclass(frozen=True)
class MutationProbe:
    mutation_id: str
    baseline_exit_code: int | None
    mutant_exit_code: int | None
    timed_out: bool
    duration_ms: int
    reason_code: str | None


@dataclass(frozen=True)
class MutationRun:
    manifest_id: str
    subject_commit: str
    probes: tuple[MutationProbe, ...]
    main_tree_unchanged: bool
    reason_code: str | None


def run_targeted_mutations(repository_root: Path, subject_commit: str) -> MutationRun: ...
```

No public input accepts a manifest path, transform, pytest node ID, argv,
environment, timeout, action approval, task ID, or scratch path.

## Exact operator bindings

The operator table is closed over the manifest's five exact
`operator + target + target_symbol` combinations.

1. `drop_targeted_mutation_required_check`
   - `src/aiflow/policy.py::_validate_cross_file`
   - Require exactly one assignment to `extras` whose tuple is exactly
     `acceptance`, `integration`, `targeted_mutation`, `independent_verifier`.
   - Remove only the unique `targeted_mutation` constant.
2. `allow_same_verifier_actor`
   - `src/aiflow/verifier_service.py::validate_verifier_actor`
   - Require exactly one `if implementer == verifier` whose body is the expected
     `ContractError` raise.
   - Replace only that guard test with `False`.
3. `allow_nonpassing_required_check`
   - `src/aiflow/approval.py::_v2_evidence_current`
   - Require exactly one `any(status != "passed" ...)` guard followed by
     `return False`.
   - Replace only that guard test with `False`.
4. `accept_non_killed_mutation`
   - `src/aiflow/gate.py::_v2_gate_facts`
   - Require exactly one `all(isinstance(item, Mapping) and
     item.get("outcome") == "killed" ...)` predicate.
   - Preserve list/nonempty checks and reduce only the generator predicate to
     `isinstance(item, Mapping)`.
5. `ignore_snapshot_mismatch`
   - `src/aiflow/evidence.py::validate_v2_snapshot`
   - Require exactly one snapshot type/hash mismatch guard with the expected
     stale-snapshot raise.
   - Replace only that guard test with `False`.

Every transform parses the complete module, requires exactly one top-level target
function and one structural anchor, applies one replacement, runs
`ast.fix_missing_locations`, compiles the result, and compares the before/after AST
outside the target function. Zero or multiple anchors, crossed bindings, parse or
compile failure fail closed. `ast.unparse` may reformat the disposable scratch
file, but no non-target AST may change.

## Internal boundaries

Suggested private seams:

- preflight: `_validate_subject`, `_controlled_paths`,
  `_assert_controlled_paths_at_subject`, `_assert_no_checkout_filters`;
- snapshots: `_snapshot_main_tree`, `_worktree_registry_bytes`,
  `_compare_main_tree_snapshot`;
- workspace/Git: `_create_workspace_root`, `_validated_child`, `_git`,
  `_create_detached_worktree`, `_remove_worktree_with_retry`;
- mutation/detector: `_apply_mutation`, `_minimal_environment`,
  `_run_detector`, `_terminate_process_tree`;
- result assembly: `_not_executed_probes`, `_run_failure`.

The entrypoint performs:

1. fixed manifest load and preflight before any worktree creation;
2. main status/file/worktree-registry snapshot;
3. one validated system-temp direct-child root and empty hooks directory;
4. one detached child worktree per manifest declaration, in order;
5. isolated manifest identity reload, baseline detector, one AST mutation, mutant
   detector, then per-item `finally` cleanup;
6. fail-stop on any safety/infrastructure error and ordered
   `MUTATION_NOT_EXECUTED` placeholders;
7. outer-finally main-tree and registry comparison, with
   `MUTATION_MAIN_TREE_CHANGED` taking precedence over cleanup and normal probe
   facts.

All runner Git calls use `shell=False` and
`git -c core.hooksPath=<validated-empty-hooks-dir> ...`. Checkout filters are
rejected before worktree creation. Every removal attempt re-resolves and proves
strict containment under the one task-created temporary root.

## Detector process

The only argv is:

```python
(sys.executable, "-m", "pytest", "-q", declaration.expected_detector)
```

The environment contains only controlled `PATH`, Windows `SystemRoot` when
required, item-local `TMP`/`TEMP`, `PYTHONPATH=<worktree>/src`,
`PYTHONDONTWRITEBYTECODE=1`, `PYTHONNOUSERSITE=1`, and
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. Output goes to `DEVNULL`.

Windows uses `CREATE_NEW_PROCESS_GROUP`; timeout termination invokes the fixed
`%SystemRoot%/System32/taskkill.exe /PID <pid> /T /F`, falls back to
`process.kill()`, and reaps the process. POSIX uses a new session, kills the
process group, falls back to `process.kill()`, and reaps it.

## Test matrix

Unit tests use private seams and never create a real worktree:

- all five exact transforms plus zero/multiple anchor, crossed binding,
  parse/compile/write failures, and non-target AST invariance;
- invalid/nonexistent/non-HEAD subject, controlled-path drift, checkout filters,
  path escape, isolated-manifest drift, create/cleanup/registry failure;
- exact minimal environment and argv, raw exits 0/1, exits 2-5, launch failure,
  timeout, child-process-tree termination, and Windows retry bound;
- main-tree change precedence, five-probe ordering/fill, frozen results, and no
  scratch/log/environment fields.

The real integration test is not run until a current single-use action approval
for the exact outer transaction has been manually claimed as required by the
frozen spec. A focused transaction invokes the runner once at current HEAD and
requires, in manifest order, baseline exits
`(0, 0, 0, 0, 0)`, mutant exits `(1, 1, 1, 1, 1)`, no timeout/reason, and an
unchanged main status, controlled byte set, and raw worktree registry.

The frozen V1 plan collects that integration test twice: once in
`regression_tests` and once in `coverage_xml`. Its separately approved outer
`aiflow verify TASK-0013` transaction therefore has a maximum budget of two runner
invocations (two roots, ten item worktrees total); a passing transaction observes
exactly two. Focused, local V1, CI V1, and every retry have distinct action files,
approvals, and started use records. An unused allowance after early failure is
consumed with the outer transaction and cannot be carried forward.

## Known implementation risks

- `ast.unparse` reformats the disposable target; AST comparison, not textual
  equality, must prove non-target semantics unchanged.
- Git attributes can invoke checkout processes; preflight accepts only
  `unspecified`/`unset` filter results.
- Windows antivirus/indexer handles can delay cleanup; retries remain bounded to
  the frozen three-attempt/one-second limit and never broaden deletion.
- A cleanup or registry mismatch can coexist with valid detector exits; it still
  invalidates the run, and a main-tree change remains the highest-priority
  run-level failure.
