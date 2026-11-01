# Installed-engine governance mutations — design candidate

This is an implementation contract candidate, not an installed Policy or passing evidence. The owner has explicitly reopened complete agent-bridge integration, including installed V2 and Node CI. Real target application waits until the active target session finishes and its baseline and write ownership can be checked again. Existing local Node V0/V1 remains the delivered capability; see [Node verification](../../operations/node-verification.md).

## Outcome and boundaries

Verify the five existing AI Flow safeguards against the bytes of the ordinary installed engine actually used for a target task. A target commit identifies application code; it is not an engine source commit. Bind both facts explicitly. Do not substitute application mutations, historical native PASS, version strings, or hashes without their originals for installed-engine tests.

The first governed slice adds a closed execution primitive and read-only replay. It does **not** enable Node V2, finalize, CI, or a successful Node V2 Gate. Native Python checks, all five existing safeguards, coverage thresholds, existing evidence and approvals remain unchanged. Later slices connect the new evidence to every lifecycle consumer before removing capability rejection.

## Fixed probes and operators

Ship five package-owned probes, their fixtures and their exact declarations with the engine. No caller-supplied probe, module, command, operator or test selection is accepted. The first slice tests the installed engine's existing native V2 guards; it proves no Node V2 support. The lifecycle slice must extend these same five probes to the actual Node V2 consumer paths before enabling that capability.

| Probe / safeguard | Actual consumer | Fixed operator | Baseline expectation and mutant assertion |
|---|---|---|---|
| `MUT-V2-001` / complete required checks | `policy._validate_cross_file` | `drop_targeted_mutation_required_check` | The complete fixture Policy loads; a fixture with the required targeted-mutation protection removed is rejected. The mutation must make that rejection assertion fail. |
| `MUT-V2-002` / verifier independence | `verifier_service.validate_verifier_actor` | `allow_same_verifier_actor` | Blank and same-as-implementer verifier labels are rejected; a distinct label is accepted. Only the designated same-actor rejection assertion may fail under mutation. |
| `MUT-V2-003` / passing evidence before code approval | `approval._v2_evidence_current`, reached by code approval | `allow_nonpassing_required_check` | With other fixed context facts satisfied, a failed required check prevents approval before downstream mutation consumption. Mutation must fail that exact rejection assertion. |
| `MUT-V2-004` / killed mutations before Gate | `gate._v2_gate_facts`, reached by Gate | `accept_non_killed_mutation` | With other fixed facts satisfied, a non-killed mutation keeps the Gate mutation predicate false. Mutation must fail that exact predicate assertion. |
| `MUT-V2-005` / bound verification snapshot | `evidence.validate_v2_snapshot`, reached by finalize/approval/Gate | `ignore_snapshot_mismatch` | Changing a required-check result or mutation projection after snapshot creation is rejected. Mutation must fail the corresponding expected-error assertion. |

Fixtures may isolate unrelated context with fixed package-owned stubs, as the existing native detector tests do. They must call the real installed guard and verify that the exercised consumer retains that guard. Public approval/Gate/finalize integration tests separately prove reachability; a stubbed unit probe alone does not prove a whole lifecycle. Actor labels enforce role separation, not authenticated human or model identity.

`MUT-V2-001` needs an installed-only AST variant; preserve the native operator unchanged. The native operator deletes `targeted_mutation` from the expected `extras` tuple, which also rejects a complete valid Policy. That cannot satisfy a probe whose positive control must still pass. The installed variant keeps the complete `extras` declaration and changes only the unique actual-extras comparison from `actual_ids != extras` to `actual_ids not in (extras, ("acceptance", "integration", "independent_verifier"))`, where `actual_ids` denotes the existing inline tuple expression, not a new source variable. Bind this distinct operator implementation in the installed declarations. Both complete-Policy acceptance and missing-targeted-check rejection are fixed cases; only the latter assertion may fail in the mutant. Reject any other AST shape or additional match.

Each operator accepts one reviewed AST shape in one declared symbol, records original and mutated SHA-256, and verifies the exact expected change. Unknown shapes, no match, multiple matches, wrong target or unrelated changes reject. During Node V2 implementation, explicitly review the selected-profile AST transformation and detector: the current native Policy branch cannot establish enforcement in the early Node branch. A new engine/probe declaration digest invalidates prior results.

## Installed materials and execution

Reuse the ordinary-install inventory, file-type/path checks, combined budgets, copying and process receipts in `node_execution` and `process_runner`. Bind actual wheel/distribution metadata, complete engine modules and resources, required Python dependencies, interpreter, startup facts, fixed probes/fixtures/protocol/operator code and applicable host tools. Reuse target material binding for repository, task, decision units, base/subject/tree, spec, Policy and classification. Reject editable/source-path substitution, unknown startup hooks and missing or extra executable materials.

Copy the verified installed closure into fresh, exclusively owned baseline and mutant directories without links to the original. Verify content before launch and after completion; only the declared mutation may differ. Keep original RECORD bytes plus an explicit mutation overlay: do not rewrite RECORD to disguise a mutated copy as a valid ordinary installation. The original installation, target tree and Git management state must remain unchanged outside the exact permitted ledger/run writes.

The parent authority/recording process must start with bytecode writes disabled (`-B`, checked through `sys.dont_write_bytecode`) before importing this package. Ordinary-install inventory collection may cold-import dependencies such as `typing_extensions` or `_distutils_hack`; permitting those imports to write an unbound cache and only then rejecting that new file would already violate read-only preparation and preservation of the original installation. Parent `-I` is not an additional prerequisite. This requirement is distinct from, and does not weaken, the fixed child startup below.

Use the bound interpreter with isolated startup (`-I -S -B`), an explicit copied-site import root, disabled bytecode and no inherited Python/pytest injection. `-B` prevents cache writes but does not prevent reads: additionally select a fresh, exclusively owned empty cache directory with the fixed `-X pycache_prefix=<owned-cache>` role. Verify that prefix and its empty inventory before and after the subprocess; retain existing copied cache files as bound originals without allowing them to supply code. Never rely on source timestamps or sizes to invalidate a cached mutant. Confirm `__debug__` and the fixed interpreter contract. Recheck all loaded engine/dependency/probe module origins and bytes, and the actual guard function references, in each subprocess. Each reported module name must resolve to its legitimate copied-site module or package path: its dotted name maps to that module's `.py`, package `__init__.py`, or supported extension-module suffix under the bound interpreter contract. A hash matching some other file in the installed inventory is insufficient. In particular, a row named `aiflow.policy` cannot use the inventory path and digest of `aiflow/errors.py`. Reject mismatched name/path roles even when both files are otherwise bound. Loading the unmodified parent installation instead of the mutated copy is unverified. This is controlled test execution on a trusted host, not a sandbox for hostile same-user code. The first slice retains the existing Windows x64 / CPython 3.11 host boundary. Bind the selected executable, supported base-executable/runtime identity, actual implementation/version/cache-tag and isolated/debug flags; reject unsupported interpreter layouts rather than guessing them. The host interpreter's standard library, OS loader and OS remain trusted. Copied-site origin and byte checks establish which engine/dependency/probe code ran; they do not establish a hermetic interpreter, authenticated publisher or hostile-code isolation.

Use the existing Windows suspended-process/Job contract: no execution before Job assignment; require parent exit, empty Job, stdout/stderr EOF and confirmed cleanup. Fixed deadlines and bounded raw streams cover the complete process tree. Timeout, output overflow, launch failure, descendants still running or unknown cleanup cannot yield killed or passed. Unsupported hosts fail closed; no silent subprocess fallback.

## Failure attribution

A small stdlib probe harness suffices; this does not require a new general test runner or the source repository's pytest/conftest tree. Each probe emits one bounded canonical report with exact identity, selected case set, loaded-material facts, setup/call/teardown outcomes and terminal status. Reports and raw stdout/stderr have independent retained digests. The fixed harness captures terminal case exceptions in its one canonical stdout report, so raw stderr must be empty for both baseline and mutant; an added traceback, warning or other stderr output rejects even if the stdout report and exit code look correct. Unexpected report fields, duplicate keys, missing/extra cases or incomplete reports reject.

- Baseline requires exit `0`, every declared case and all phases passed, and valid imports/materials/process receipts.
- Killed requires that baseline, mutant exit `1`, and exactly the predeclared call-phase `AssertionError` at the bound probe's assertion anchor, with its exact expected observation. Validate exception type, terminal traceback/code location and probe file digest; matching message text alone is insufficient. Other cases and setup/teardown must pass.
- Mutant all-pass/exit `0` is survived. Import, setup, collection, teardown or harness errors; unrelated assertion; wrong exit; missing report; or uncertain process/material facts are unverified. Never infer killed from exit `1` alone.

The trusted parent derives outcomes from retained reports, raw streams, receipts and material bindings. A subprocess's claimed outcome is not authority. Fixed failure injections must demonstrate every rejection category, including a right-looking report from the wrong loaded engine.

## Authority, storage and replay

The production recorder accepts only an `IMPLEMENTING` governed native V2 task with current frozen-spec approval, current classification, distinct implementer/verifier labels and a current verifier context. It must not enter or resume verification, make a blocked Node task executable, or use the native recorder's `VERIFYING` prerequisite as a shortcut.

The production recorder requires a newly reviewed, current task-bound single-use local action before any mutation launch. Use action type `installed_engine_mutation_v1` and file prefix `action-installed-engine-mutation-`, separate from native `targeted_mutation_v2`. Keep the existing action-file shape: its `parameter_summary` is canonical JSON with exactly `kind` and `inputs_sha256`, where the digest covers the complete prepared task/material/probe/operator inputs below. The recorder must validate this exact summary and current classification before consumption; generic action approval alone does not interpret it. Old native actions, receipts and launch claims cannot authorize this primitive. Bind action and launch to current engine/probe/material digests as well as task/version facts. Atomically claim consumption using the existing ledger/receipt transaction rules; one approval cannot start two concurrent runs. A spent or interrupted action is not retried implicitly. Do not reuse historical approvals or broaden this into external execution authority.

Retain an immutable run manifest, original inventories, operator diff facts, reports, receipts and raw streams under the task's ignored logs. Public evidence contains only bounded projections, digests and canonical relative references. Bind repository/task/base/subject, current inputs, verifier context, action consumption and engine/probe versions to the run; retain failure artifacts instead of rewriting history.

Use four distinct steps: prepare stable inputs; record under a fresh single-use action; collect exact-reference current authority facts; then replay purely from files. The collector may perform the existing read-only Git operations. The pure reader performs no subprocess, recovery, directory creation or state writes. Later verification, freshness/status, review, approval and Gate adapters must preserve this boundary and recollect authority facts at their transaction boundary. Do not call `node_execution._binding`, `mutation_evidence._validate_bindings`, `_root_snapshot` or `_git_audit_delta` inside pure replay: they can launch Git. Reuse their existing validators/comparison rules on the appropriate side of the boundary; do not add a Git parser.

Historical `before == after` alone proves no completeness: deleting the same protected-file rows or metadata from both snapshots and rehashing the run/reference/completion must reject. The current collector supplies a complete authoritative root snapshot for the exact run reference. Pure replay must compare complete protected inventories and validate permitted evolution to those current facts, not merely loop over whatever historical rows remain. Missing, stale, malformed, incomplete or incompatible evidence rejects. Structure-only Schema validation never replaces replay. Existing native evidence keeps its original contract and consumer.

## Minimal production files and closed API

Keep the first implementation in `src/aiflow/installed_mutations.py` (preparation, namespace-specific action transaction, runner, report validation and pure replay) and `src/aiflow/installed_probe.py` (fixed stdlib harness, fixtures and declarations). Reuse `node_execution` file/inventory/budget/engine/copy/receipt helpers, `process_runner.run_node_process`, and the existing four compatible AST operators from `mutation_runner`. Implement only the installed `001` variant separately. Reuse generic action normalization/digests, approval matching and the existing task consumption lock; keep the new namespace's `IMPLEMENTING` checks, consumption events and exclusive launch claim explicit. Do not generalize or modify native mutation behavior merely to share it.

Python modules and Python fixture/declaration constants are already included by package discovery; prove their wheel and sdist inclusion without adding a new resource tree. Fixed Policy fixtures can use the native resource bundle. Keep companion tests and documentation separate; this slice does not change public profile/Policy/evidence versions or connect new artifacts to public Node V2/CI consumers.

The proposed internal API has no caller-selected probe, operator, command, environment or executable. Its immutable inputs are concrete current facts, not an authorization token:

```python
@dataclass(frozen=True)
class InstalledMutationInputs:
    repository_id: str
    task_id: str
    decision_unit_ids: tuple[str, ...]
    branch: str
    base_commit: str
    subject_commit: str
    subject_tree: str
    spec_sha256: str
    policy_sha256: str
    classification_input_sha256: str
    implementer_actor: str
    verifier_actor: str
    verifier_context_sha256: str
    materials: bytes

    @property
    def sha256(self) -> str: ...


@dataclass(frozen=True)
class InstalledMutationReference:
    ref: str
    size: int
    sha256: str


@dataclass(frozen=True)
class InstalledMutationCurrent:
    inputs: InstalledMutationInputs
    reference: InstalledMutationReference
    root_snapshot: bytes
    allowed_git_paths: tuple[str, ...]


@dataclass(frozen=True)
class InstalledMutationFacts:
    current: bool
    all_killed: bool
    results: tuple[tuple[str, str], ...]
    reason_codes: tuple[str, ...]


def prepare_installed_mutations(
    root: Path, task_id: str, *, verifier_actor: str
) -> InstalledMutationInputs: ...


def record_installed_mutations(
    root: Path, task_id: str, *, verifier_actor: str, expected_inputs_sha256: str
) -> InstalledMutationReference: ...


def collect_installed_mutation_current(
    root: Path, reference: InstalledMutationReference, *, verifier_actor: str
) -> InstalledMutationCurrent: ...


def replay_installed_mutations(
    root: Path, reference: InstalledMutationReference, *, current: InstalledMutationCurrent
) -> InstalledMutationFacts: ...
```

`prepare` is a read-only authority-side operation: validate current task/Git/context and ordinary installed materials, return their canonical inputs, and neither consume an action nor create a run. `materials` contains bounded canonical JSON with exactly `kind`, `version`, `engine`, `interpreter`, `host_tools`, `probes` and `operators`; these retain full inventories and metadata, not hashes without originals. Declaration/probe/protocol/operator bytes and original distribution/RECORD bytes are part of that bound closure.

`InstalledMutationInputs.sha256` hashes the canonical complete stable input representation, including the canonical material document. Keep these input fields and the action-summary digest unchanged: evolving events, approval ledgers, HEAD/index state and root metadata do not enter this digest. Drafting/approving/consuming the action or a later permitted governance commit must not invalidate its own action inputs. This separation does not remove subject/base/tree, spec, Policy, classification, actor/context or installed-material binding.

`InstalledMutationCurrent` is separate, immutable authority data for one exact `InstalledMutationReference`; it is not part of the prepared/action input hash. `root_snapshot` is bounded canonical JSON bytes for the complete existing root-snapshot shape (`identity`, `git`, `files`, `task`, `events`, `governance`, `metadata`, `git_audit`). `allowed_git_paths` is a sorted, unique tuple of exact absolute physical Git-management paths derived by the collector, never a caller-selected exemption or directory prefix. Validate exact dataclass/field types, canonical bytes, nested closed shapes, identities, digests and path roles before using either object. `InstalledMutationFacts` exposes `current`, `passed`, ordered fixed results and `reason_codes`; a current survived/unverified run is never passed.

`record` recomputes the preparation and rejects a different expected digest before claiming the new action. Under the existing task lock it independently validates the current approval, atomically consumes it and exclusively creates a namespace-specific launch claim; interruption leaves that approval spent. It then creates fresh baseline/mutant copies and emits a separate versioned installed-mutation artifact. It does not replace native mutation evidence or publish a successful V2 evidence document.

`collect_installed_mutation_current` is the sole read-only authority collector for replay. Reuse the state-neutral binding checks from the existing validators to obtain live task/Git/material/context facts. The `IMPLEMENTING` execution gate belongs independently to `prepare` and `record`, not to this collector: legitimate later review, finalization and code-approval progression may be read without reopening execution, consuming an action, recovering state or writing files. Reject changed stable inputs or unsupported capability; never manufacture a lifecycle transition.

Before using historical data in any Git argument or exemption, validate the exact typed reference, canonical run bytes/size/hash, namespace/completion binding and complete closed historical snapshot shapes. Validate historical commit SHA syntax and all relative/absolute path roles, Git directories, branch ref and bounded reflog-prefix facts; malformed data must not reach a Git command. Confirm the original `before` and `after` are equal. Collect complete current facts through `node_execution._root_snapshot`, excluding only the exact owned run resolved from this reference. Verify old-HEAD ancestry, historical old-to-current diff and cached diff against only the exact registered governance paths, following existing Node root-protection rules. Then reuse `_git_audit_delta` to verify Git audit continuity and derive the exact physical Git allowance. `_git_audit_delta` alone does not establish ancestry or the full old-to-current/cached-diff restriction and cannot replace those checks. Return the collected current snapshot and sorted unique allowance bound to the same reference; there is no directory-wide `.git` or task exemption.

`replay` requires `InstalledMutationCurrent` whose embedded reference exactly equals the requested reference, including ref, size and SHA-256. Authority collected for run A cannot be reused for run B, even when their stable inputs match. Revalidate the canonical current representation, reread retained original inventories, action/approval/consumption/launch/completion originals, reports, streams and receipts, and derive the ordered five outcomes. Recheck original `before == after`, then compare the complete protected root identity, file inventory (including membership, bytes and identities) and immutable task facts against the authoritative current snapshot. Check existing review originals remain immutable, approvals and events retain exact prefixes, and all appended events belong to the existing Node governance whitelist, plus the explicitly required verification_started transition from IMPLEMENTING to VERIFYING by the same recorded verifier. Validate that transition against strict task event replay; state-neutral reading does not grant execution authority. Do not treat arbitrary ledger growth as permission.

For complete historical-to-current metadata comparison, reuse pure `node_execution._check_root_metadata` with only exact registered governance files, the collector-verified physical Git allowance and the exact reference-owned run. Preserve its ancestor identity and child-membership checks; do not exempt the whole logs, task or Git directory. Missing metadata rows, deleted file rows, extra paths or a rehashed shortened snapshot must reject against the complete current snapshot. No `passed` boolean, subprocess outcome claim or self-written pair of equal snapshots is authority. The replay result grants no execution permission. Dataclasses do not authenticate their constructor: internal callers must obtain `InstalledMutationCurrent` through the collector, not deserialize it from evidence JSON, and must not construct an allowance from untrusted run data. Later lifecycle adapters must preserve this precondition.

Test the pure reader after authority facts have been collected by rejecting every `subprocess.Popen`/`subprocess.run` and relevant process wrapper, and by checking zero filesystem writes. Existing native loader tests replace binding collection and count mutation-runner calls; existing Node consumer tests forbid `run_node_process`. Neither establishes absence of Git subprocesses in a live top-level consumer. Keep those contracts and tests unchanged rather than relabeling them.

## Later lifecycle and CI slices

Use a separately reviewed Node profile revision and evidence version; the candidate is revision `2` / evidence `3.2`, retaining revision `1` / `3.1` behavior. Freeze the exact complete Policy before implementation. Node V2 contains full V1 plus fixed acceptance, integration, targeted-mutation and independent-verifier checks. Acceptance/integration must exercise the target's real fixed contract and cannot be relabeled Python checks.

Reuse verifier-context and review mechanics; extend the narrowly shared snapshot/finalization guards where both profiles need the same rule. Current native helpers and Gate assume evidence `2.0`, while Node `3.1` is local V0/V1 only. Update Schema, Policy, execution, snapshot/pre/final, review, approval and marker recovery, freshness/status and Gate together. Pre evidence cannot authorize V2 code approval; only the same independent verifier may finalize after current implementation review binds the unchanged snapshot. Snapshot includes the full Node material/run/coverage and mutation projection; finalize changes only phase and implementation-review reference. Missing capability continues to reject before recovery, writes or processes.

CI follows local V2, not the reverse. Define a fixed relative-path artifact inventory and stable execution-content digest distinct from local absolute paths, inode and host identities. Retain original local-final facts unchanged. A fresh CI installation/preparation must match the declared wheel/module/resource/probe/dependency content and bind its own host identities, preflights and receipts. Do not pretend a copied local inode/path is current on CI, or silently discard distribution/startup metadata differences.

CI checks the same target subject with complete checks and recomputes process, coverage and mutation originals. Its attestation must reference a current local-final snapshot and matching verifier/context/reviews; it does not create a second implementation approval. Gate validates both. Missing originals, content drift, wrong candidate or public-summary-only input rejects. Raw private-material transfer, target workflow and remote protection require their own authorized scope and verification.

## Acceptance before capability claims

1. Build direct wheel and sdist/rebuilt wheel; install an ordinary wheel outside the source checkout, with no parent harness-model resources or import path. Verify shipped probe/resource inventories and actual loaded origins.
2. Execute five real baseline/mutant pairs; independently collect current authority and replay all retained originals. Also prove survived, wrong assertion, import/setup/teardown errors, malformed/incomplete reports, timeout/overflow/cleanup failure, module substitution and changed original installation reject. Prove a cold dependency import under the required parent `-B` leaves the original installation unchanged; reject an unsupported parent before preparation enters inventory collection or cold-imports further dependencies. This guard cannot undo imports performed before the API was called, so callers must apply `-B` from interpreter startup. Fixed new negatives include the unsupported parent flag, a reported module name paired with a different bound inventory file, and nonempty stderr appended to an otherwise killed-looking report.
3. Rehash run/reference/completion after deleting the same protected-file rows or metadata from both original snapshots; reject, including after actually changing the omitted original. Exercise metadata/Git-audit tampering, cross-run A-to-B reuse of `InstalledMutationCurrent`, malformed historical SHA/path/ref data before Git invocation, and non-governance HEAD/index/cache changes. Legitimate registered governance-only advancement remains readable through the state-neutral collector while `prepare`/`record` still reject outside `IMPLEMENTING`.
4. Exercise two simultaneous launch attempts and interrupted action consumption; at most one starts, with originals retained. Repeated consumer calls must be zero-write and zero-process.
5. After lifecycle implementation, use independent Git fixtures for pre-to-final-to-code-approval-to-Gate and each safeguard's public-consumer rejection; include every task/context/review/material/engine freshness boundary. Until then Node V2 remains unsupported.
6. After CI implementation, reproduce same-subject local/CI acceptance on the supported runner, and reject absent originals, changed content and wrong head. Only then prepare real target application after its active session finishes.

Each governed slice requires independent review and current native verification/CI. Preserve full tests, all required checks, 85% total and 90% diff coverage, whitespace, Ruff, format, mypy, five original mutations and existing branch protection. Probe success, document approval and disposable acceptance do not alone establish real agent-bridge adoption.
