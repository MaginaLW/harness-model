# Bounded ordered warm-snapshot copy admission

Preserve the previous frozen B589 specification byte-for-byte as
spec-design-007.md, SHA256 b589852985fea26583efe09009aefe710465625ffac14609213c5d1caf3c1d70.
All native/original600 failures, consumed receipts, reviews and diagnostics stay.
Private comparison016 motivates this design, not a runtime or V2 PASS. The
success-only e518 prototype is neither admitted nor reused as implementation.

Only the current qualified owner snapshot warm copy may select bounded parallel
file batches; first publication remains serial. Preserve all original
populate_or_copy guards and caller mkdir, actual copy2/DirEntry, independent
physical files, original DFS error aggregation and postorder metadata. Drain a
consecutive-file batch before recursion, coordinator failures and copystat.
All submitted work reaches terminal state on every return/raise; four workers
and256 total submissions are separate bounds. Preserve actual abort identity
and logical priority, partial and no retry/cleanup. Explicit same-batch partial
and audit-thread/event-order differences are detailed in the new full spec.

Before selected copying, additional actual eligibility reads may choose original
serial on ineligible/unknown/recoverable checks; BaseException is not silently
converted. Known binding checks cannot prove absence of registered audit hooks.
Actual copying and hook failures never become a fallback probe. No source bytes,
IO, Git, Schema, Policy or governance result is cached or skipped. Postproof is
part of validation, not an added per-warm full-tree runtime scan.

Only _copy_snapshot/new private helpers/imports/constants and appended tests
change in the safe unit; every other old fixture function body, all65 current
cases and consumer/assertion ASTs remain. Documentation follows as a separate
safe commit. Cumulative scope remains24 paths; rule8 separation is preserved.

Implementation advice and readonly independent design review run in parallel
with two sub-agents. Native admission, source integration/commit, fixed-candidate
fullwarm and complete prerequisites, fresh action/native V2, independent
implementation Review/finalize/code approval/Gate are serial. Exact locked
3.13.15/full core MINENV remains conditional on actual original integration600
PASS. All14/5 mutations/85%/90%, CI3.11 and branch protection remain.
Task55, publication and real matching-report acceptance entry stay unchanged.
