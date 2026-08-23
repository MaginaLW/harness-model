# TASK-0013 classification fact completion

The initial `aiflow start` scaffold omitted Policy predicate fields and therefore
classified deterministically as `BLOCK / PREDICATE_FIELD_MISSING`.

The decision unit now records a clear bounded scope, medium CI impact, reversible
isolated execution, automatic local verification with available tools, verified
subject-commit recovery, dry-run-only mutation outside the main worktree, and
cross-module behavior/regression risk. The intended route is REVIEW and the
self-bootstrap verification level remains V1. Because the last persisted raw
route is BLOCK, a subsequent BLOCK -> REVIEW transition is a route downgrade even
though it only corrects incomplete scaffold facts. It must not be recorded without
explicit manual downgrade authorization bound to the then-current classification
input and Policy hash.

TASK-0012 external integration remains an explicit begin precondition for this
task and is not treated as resolved by these classification facts.

The runner creates and removes only task-owned detached worktrees under one
validated system temporary root. The decision unit therefore declares that local
side effect and a separate, current, single-use `delete` action approval for each
complete real five-probe execution. The default automatic `delete` prohibition
remains in force; no cleanup is authorized by this fact-completion record.

The draft scope was subsequently narrowed to the new mutation runner, its two
test modules, and the Chapter 11 documentation/state projection. The existing
general process runner is read-only and no longer belongs to the impact scope.
