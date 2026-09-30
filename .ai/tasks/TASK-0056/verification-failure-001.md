# First complete native V2: failed

Independent verifier `e4-temp-independent-verifier` ran all required checks on
subject `659f61cb4245112d75b119b103821bb06bae69ce`, branch
`codex/e4-verification-control`, base
`ef92b795da729566870ff4878f100a4ffe319db5`.
Run `run-20260930T043225674088Z` began at
`2026-09-30T04:32:24.827540Z` and ended at
`2026-09-30T05:24:13.275424Z`. The native CLI returned 0 after recording
FAILED; that exit is not a passing verification result. Native Gate returned
1, REJECT. No implementation Review, finalization or publication followed.

| Check | Status | Exit | Timeout | Duration, ms |
| --- | --- | --- | --- | --- |
| contract | passed | 0 | false | 390 |
| scope | passed | 0 | false | 547 |
| ruff_check | passed | 0 | false | 985 |
| ruff_format_check | passed | 0 | false | 296 |
| smoke | passed | 0 | false | 266 |
| unit_tests | failed | 1 | false | 264734 |
| regression_tests | failed | null | true | 902812 |
| mypy | passed | 0 | false | 1344 |
| coverage_xml | failed | null | true | 1210734 |
| diff_coverage | failed | 1 | false | 43547 |
| acceptance | passed | 0 | false | 4094 |
| integration | failed | null | true | 600813 |
| targeted_mutation | passed | 0 | false | 0 |
| independent_verifier | passed | 0 | false | 0 |

Unit completed with 40 failed and 1798 passed in 261.86 seconds. Acceptance
completed with 9 passed in 2.20 seconds; mypy checked 43 source files.
Regression, coverage and integration have no complete pytest summary.
Coverage XML was absent, so total and diff coverage remain unknown.
The last two zero durations are native evidence projections. The five fixed
mutations actually ran with baseline exit 0, mutant exit 1, no timeout and
outcome killed. Their measured durations were 2655, 20906, 1266, 1094 and
1766 ms; the native consumer confirmed `main_tree_unchanged: true`.

## Preserved bindings

Task evidence and native run archive are byte-identical, SHA-256
`d9b9c9ad5712af92437f49034b0d419a4879edd0b64612965db3a3c788769ee8`.
The schema and snapshot validate. Snapshot SHA-256 is
`e00765018d34bd9801d32d569e6c2a005bf8a669b3e05aa4fe5c67a562546a01`;
verifier context SHA-256 is
`8a4db7cd53daf142bd29592755639184b2aae4cdc80559bcba47a752fbb163c8`,
matching the current context at handback.
Mutation canonical SHA-256 is
`4cb5910a3b5b3e3b12326ff738e781248c15875277a69941345f411209e93759`.
Action001 canonical SHA-256 is
`7c185e24995f728cb55fd48ccee2d60757a6318f35730e19c589e56483d25f33`.
Its receipt SHA-256 is
`da1cef0032722e318f85b08840dc2aaa13091b452171ef7377cfd8f55fa65183`;
physical receipt identity matches the native consumption event.
Sequence 18 started verification, sequence 19 consumed the action at
`2026-09-30T05:23:12Z`, and sequence 20 recorded failure at
`2026-09-30T05:24:13Z`. The action cannot be reused.

Private original stdout/stderr, driver start/exit facts and native evidence
remain under `logs/`. The independent audit revision 1 incorrectly resolved
ordinary task-relative check log refs from the repository root. It remains
preserved; revision 2 explicitly corrects that auxiliary audit error and
checks all 24 non-null log refs and their actual SHA-256 values. Four refs
are natively null. No native evidence was edited to correct the audit.

## Bounded follow-up

Thirty-five mutation/context failures involved atomic-write destinations
of 272-275 characters. The UUID repository-copy failure reported 251 failed
destination paths of 260-289 characters. Four other failures were original
PowerShell subprocess deadlines of 15, 17 or 30 seconds. These are observed
clusters; their causes are not yet established.

Next, compare unchanged representative assertions through the original
native process environment using equally shaped run-owned leaves beneath
long and short ordinary external parents. Separately prepare an isolated
locked runtime and verify actual tool resolution, including diff-cover.
Runtime preparation is not a test or Gate pass. Any retry requires a fresh
exact-subject single-use action, preserves the full default V2 plan and all
deadlines, and uses an independent verifier. Later source integration and
publication remain dependent on actual passing verification and Gate.
