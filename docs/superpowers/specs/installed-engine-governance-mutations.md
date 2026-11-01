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

Each operator accepts one reviewed AST shape in one declared symbol, records original and mutated SHA-256, and verifies the exact expected change. Unknown shapes, no match, multiple matches, wrong target or unrelated changes reject. During Node V2 implementation, explicitly review the selected-profile AST transformation and detector: the current native Policy branch cannot establish enforcement in the early Node branch. A new engine/probe declaration digest invalidates prior results.

## Installed materials and execution

Reuse the ordinary-install inventory, file-type/path checks, combined budgets, copying and process receipts in `node_execution` and `process_runner`. Bind actual wheel/distribution metadata, complete engine modules and resources, required Python dependencies, interpreter, startup facts, fixed probes/fixtures/protocol/operator code and applicable host tools. Reuse target material binding for repository, task, decision units, base/subject/tree, spec, Policy and classification. Reject editable/source-path substitution, unknown startup hooks and missing or extra executable materials.

Copy the verified installed closure into fresh, exclusively owned baseline and mutant directories without links to the original. Verify content before launch and after completion; only the declared mutation may differ. Keep original RECORD bytes plus an explicit mutation overlay: do not rewrite RECORD to disguise a mutated copy as a valid ordinary installation. The original installation, target tree and Git management state must remain unchanged outside the exact permitted ledger/run writes.

Use the bound interpreter with isolated startup (`-I -S -B`), an explicit copied-site import root, disabled bytecode and no inherited Python/pytest injection. Confirm `__debug__` and the fixed interpreter contract. Recheck loaded `aiflow` module origins and bytes, and the actual guard function references, in each subprocess. Loading the unmodified parent installation instead of the mutated copy is unverified. This is controlled test execution on a trusted host, not a sandbox for hostile same-user code.

Use the existing Windows suspended-process/Job contract: no execution before Job assignment; require parent exit, empty Job, stdout/stderr EOF and confirmed cleanup. Fixed deadlines and bounded raw streams cover the complete process tree. Timeout, output overflow, launch failure, descendants still running or unknown cleanup cannot yield killed or passed. Unsupported hosts fail closed; no silent subprocess fallback.

## Failure attribution

A small stdlib probe harness suffices; this does not require a new general test runner or the source repository's pytest/conftest tree. Each probe emits one bounded canonical report with exact identity, selected case set, loaded-material facts, setup/call/teardown outcomes and terminal status. Reports and raw stdout/stderr have independent retained digests. Unexpected report fields, duplicate keys, missing/extra cases or incomplete reports reject.

- Baseline requires exit `0`, every declared case and all phases passed, and valid imports/materials/process receipts.
- Killed requires that baseline, mutant exit `1`, and exactly the predeclared call-phase `AssertionError` at the bound probe's assertion anchor, with its exact expected observation. Validate exception type, terminal traceback/code location and probe file digest; matching message text alone is insufficient. Other cases and setup/teardown must pass.
- Mutant all-pass/exit `0` is survived. Import, setup, collection, teardown or harness errors; unrelated assertion; wrong exit; missing report; or uncertain process/material facts are unverified. Never infer killed from exit `1` alone.

The trusted parent derives outcomes from retained reports, raw streams, receipts and material bindings. A subprocess's claimed outcome is not authority. Fixed failure injections must demonstrate every rejection category, including a right-looking report from the wrong loaded engine.

## Authority, storage and replay

The production recorder requires a newly reviewed, current task-bound single-use local action before any mutation launch. Bind action and launch to current engine/probe/material digests as well as task/version facts. Atomically claim consumption using the existing ledger/receipt transaction rules; one approval cannot start two concurrent runs. A spent or interrupted action is not retried implicitly. Do not reuse historical approvals or broaden this into external execution authority.

Retain an immutable run manifest, original inventories, operator diff facts, reports, receipts and raw streams under the task's ignored logs. Public evidence contains only bounded projections, digests and canonical relative references. Bind repository/task/base/subject, current inputs, verifier context, action consumption and engine/probe versions to the run; retain failure artifacts instead of rewriting history.

Provide one read-only consumer used by verification, freshness/status, review, approval and Gate. It derives all five outcomes again from originals and current bindings without subprocesses, recovery, directory creation or state writes. Missing, stale, malformed, incomplete or incompatible evidence rejects. Structure-only Schema validation never replaces replay. Existing native evidence keeps its original contract and consumer.

## Later lifecycle and CI slices

Use a separately reviewed Node profile revision and evidence version; the candidate is revision `2` / evidence `3.2`, retaining revision `1` / `3.1` behavior. Freeze the exact complete Policy before implementation. Node V2 contains full V1 plus fixed acceptance, integration, targeted-mutation and independent-verifier checks. Acceptance/integration must exercise the target's real fixed contract and cannot be relabeled Python checks.

Reuse verifier-context and review mechanics; extend the narrowly shared snapshot/finalization guards where both profiles need the same rule. Current native helpers and Gate assume evidence `2.0`, while Node `3.1` is local V0/V1 only. Update Schema, Policy, execution, snapshot/pre/final, review, approval and marker recovery, freshness/status and Gate together. Pre evidence cannot authorize V2 code approval; only the same independent verifier may finalize after current implementation review binds the unchanged snapshot. Snapshot includes the full Node material/run/coverage and mutation projection; finalize changes only phase and implementation-review reference. Missing capability continues to reject before recovery, writes or processes.

CI follows local V2, not the reverse. Define a fixed relative-path artifact inventory and stable execution-content digest distinct from local absolute paths, inode and host identities. Retain original local-final facts unchanged. A fresh CI installation/preparation must match the declared wheel/module/resource/probe/dependency content and bind its own host identities, preflights and receipts. Do not pretend a copied local inode/path is current on CI, or silently discard distribution/startup metadata differences.

CI checks the same target subject with complete checks and recomputes process, coverage and mutation originals. Its attestation must reference a current local-final snapshot and matching verifier/context/reviews; it does not create a second implementation approval. Gate validates both. Missing originals, content drift, wrong candidate or public-summary-only input rejects. Raw private-material transfer, target workflow and remote protection require their own authorized scope and verification.

## Acceptance before capability claims

1. Build direct wheel and sdist/rebuilt wheel; install an ordinary wheel outside the source checkout, with no parent harness-model resources or import path. Verify shipped probe/resource inventories and actual loaded origins.
2. Execute five real baseline/mutant pairs; independently replay all retained originals. Also prove survived, wrong assertion, import/setup/teardown errors, malformed/incomplete reports, timeout/overflow/cleanup failure, module substitution and changed original installation reject.
3. Exercise two simultaneous launch attempts and interrupted action consumption; at most one starts, with originals retained. Repeated consumer calls must be zero-write and zero-process.
4. After lifecycle implementation, use independent Git fixtures for pre-to-final-to-code-approval-to-Gate and each safeguard's public-consumer rejection; include every task/context/review/material/engine freshness boundary. Until then Node V2 remains unsupported.
5. After CI implementation, reproduce same-subject local/CI acceptance on the supported runner, and reject absent originals, changed content and wrong head. Only then prepare real target application after its active session finishes.

Each governed slice requires independent review and current native verification/CI. Preserve full tests, all required checks, 85% total and 90% diff coverage, whitespace, Ruff, format, mypy, five original mutations and existing branch protection. Probe success, document approval and disposable acceptance do not alone establish real agent-bridge adoption.
