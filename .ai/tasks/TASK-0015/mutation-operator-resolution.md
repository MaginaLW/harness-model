# TASK-0015 mutation-operator architecture resolution

- Condition: `spec_changed`
- Current subject: `5f5c731fd049d4dfa738c06aeadd054c5b9ad409`
- Required route and verification level: `REVIEW + V2`

Implementation analysis found that `MUT-V2-004` currently locates an exact legacy
`all(outcome == "killed")` AST expression inside `gate._v2_gate_facts`. The approved
Chapter 11.5 architecture replaces that duplicated decision with one loader-backed
`consume_targeted_mutation_evidence(...).passed` fact shared by verification, code
approval, and Gate.

Keeping the old operator implementation would either fail its precondition after the
legacy loop is removed or produce an equivalent mutant if the loop were retained
behind the authoritative consumer guard. Both outcomes would make the required
targeted-mutation evidence unverified and would undermine the manifest's stated Gate
safeguard.

The scope therefore adds only `src/aiflow/mutation_runner.py` and
`tests/unit/test_mutation_runner.py`. The existing `accept_non_killed_mutation`
implementation may be updated to locate exactly one authoritative consumer `passed`
guard in `_v2_gate_facts` and bypass it. The manifest ID, safeguard, target symbol,
operator name, detector path, expected outcome, five-item order, detector execution,
timeouts, temporary-worktree lifecycle, and cleanup behavior remain unchanged. A
missing or ambiguous AST anchor remains a closed operator-precondition failure.

This is required to preserve a non-equivalent killed mutant under the approved single
consumer architecture; it does not authorize a real mutation run, which still needs a
current single-use action approval.
