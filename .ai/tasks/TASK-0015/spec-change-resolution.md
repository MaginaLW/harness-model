# TASK-0015 specification change resolution

- Condition: `spec_changed`
- Subject commit: `17ab98cf879cf913e91dfcdf69861b387eabf7ac`
- Required route and verification level: `REVIEW + V2`
- Approved design review: `reviews/REV-0003-r0001.json`

The first design review found that the initial allowed scope omitted the code-approval
consumer and V2 evidence contract surfaces, and that the real mutation transaction
budget was not sufficiently bounded. The second review found one contradictory
non-goal concerning the V2 evidence schema.

The current task record and specification now:

1. include `src/aiflow/approval.py`, `.ai/schemas/evidence.schema.json`, contract
   fixtures, and direct approval/Gate regression tests;
2. require one shared loader-backed currentness and complete-killed consumer for
   verification, code approval, and Gate;
3. bind V2 evidence and its pre/final snapshot to `evidence_ref`,
   `mutation_evidence_sha256`, the authoritative manifest reference, and the exact
   manifest-ordered result projection; and
4. freeze the production collection call graph, fixed five-mutant execution budget,
   maximum temporary-worktree count, existing timeouts and cleanup semantics, and a
   separate current single-use action approval requirement.

`REV-0001-r0004.json` resolves the first three findings. `REV-0002-r0002.json`
resolves the schema wording conflict. Independent `REV-0003-r0001.json` approves
the resulting design with no open findings. No runtime implementation or real
mutation execution has started, and the route/verification level is not downgraded.
The stale pre-change classification, frozen digest, and earlier review contexts remain
immutable audit history and must not be reused as current approval inputs.
