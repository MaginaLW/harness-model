# Chapter 7 / Task 7.1 Execution Plan

**Goal:** Add an isolated, replayable scenario runner that exercises real AI Flow services without modifying the source checkout.

**Route / verification:** REVIEW / V1.

**Allowed scope:** `src/aiflow/scenarios.py`, `tests/integration/test_scenario_runner.py`, `examples/scenarios/README.md`, and Chapter 7 / overall progress records.

**Forbidden actions:** no source-checkout task creation, network, external action, push, merge, deployment, credential access, paid call, hard-coded runtime SHA/timestamp/path, or mutation of golden inputs.

## Design boundary

- A scenario definition supplies ordered CLI operations, actor, permitted file mutations, expected terminal state, and expected Gate reasons.
- The runner creates a fresh temporary Git repository, copies only `.ai` Policy/templates/contracts and the scenario inputs, establishes one initial commit, then calls real package/CLI services.
- Results include task snapshot, command exit codes, event state sequence, classification/approval/evidence summaries, Gate JSON, and a replayed terminal state.
- Deterministic comparison removes only timestamps, temporary absolute paths, and runtime commit identifiers; it preserves all semantic decisions and reason ordering.
- Source checkout Git status and `.ai/tasks` digest are captured before and after two runs and must remain identical.

## Steps

1. Define immutable scenario operation and result contracts plus isolated repository setup.
2. Execute declared operations through real services while enforcing the mutation allowlist.
3. Capture governed artifacts and replay events to prove the materialized terminal state.
4. Run the same scenario twice and prove normalized results and source-checkout digests match.
5. Run focused and repository-wide verification before recording completion evidence.
