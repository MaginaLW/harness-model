# Third complete native V2 result

Independent actor `e4-temp-independent-verifier` executed the complete default
V2 plan on subject `4f0288b4afb608412f984fa9078b7b0692fa0e6f`, branch
`codex/e4-verification-control`, base
`ef92b795da729566870ff4878f100a4ffe319db5`.
Run `run-20260930T084210033275Z` started at
`2026-09-30T08:42:09.050776Z` and ended at
`2026-09-30T09:27:22.386925Z`. Native CLI exit 0 recorded FAILED;
that handled exit does not mean verification passed. Independent audit
exit was 0. Native Gate returned 1, REJECT. No implementation Review
export, finalization or code approval followed.

| Check | Status | Exit | Timeout | Duration, ms |
| --- | --- | --- | --- | --- |
| contract | passed | 0 | false | 531 |
| scope | passed | 0 | false | 797 |
| ruff_check | passed | 0 | false | 516 |
| ruff_format_check | passed | 0 | false | 140 |
| smoke | passed | 0 | false | 266 |
| unit_tests | passed | 0 | false | 167015 |
| regression_tests | failed | null | true | 900125 |
| mypy | passed | 0 | false | 344 |
| coverage_xml | passed | 0 | false | 1016843 |
| diff_coverage | passed | 0 | false | 766 |
| acceptance | passed | 0 | false | 813 |
| integration | failed | null | true | 600171 |
| targeted_mutation | passed | 0 | false | 0 |
| independent_verifier | passed | 0 | false | 0 |

Unit completed with 1838 passed in 166.60 seconds; acceptance completed
with 9 passed in 0.55 seconds. The complete default coverage execution
actually collected 2677 items and completed 2676 passed, one existing
POSIX FIFO skip, in 1016.10 seconds. Coverage XML contains 7402/8108
covered lines and 2298/2812 covered branches: combined coverage is
88.8278 percent. Diff coverage printed 95 percent, with 211/220 covered
lines. Both thresholds passed. Regression and integration each timed out
with partial output around 80 percent and no terminal pytest summary.
Their partial output contains no F; that is not complete success evidence.
Per-test duration distribution and the remaining timeout causes are unknown.

All five fixed mutations actually ran: baseline exit 0, mutant exit 1,
outcome killed, no timeout, with durations 891, 7813, 937, 875 and
734 ms. Public consumer passed and confirmed `main_tree_unchanged: true`.
The last two zero check durations are native evidence projections.

Task evidence and run archive are byte-identical, SHA-256
`b8ac267190373e0e6459fa1ed5e05de19040b7974763956adddffb44b8018ecf`.
Schema and snapshot validate; snapshot SHA-256 is
`61d2f0011dd7425af75c007015812db7055f412b43522901ee79edb181249485`.
Verifier context SHA-256 is
`7551afe52c8eacc5f41582969e538678f90a1b41f7ecb2ec06e4440d816d5fb6`,
matching current context at independent audit before freeze release.
All 24 non-null task-relative log references and four native null references
were checked. Audit SHA-256 is
`e3d7b6e94c13f7f15f21c2a0f815bfe641951f2dcaf1148d94fcea2c1d907310`;
handback SHA-256 is
`38b8be1abea8ebac3ed16fdcb960c3db84c43c930263d267978d5cdc643d17dc`.
Coverage XML SHA-256 is
`5c1176398fcf20023e8609a5a282941e77c525026c833d6007dd02128c566ada`.
Mutation canonical SHA-256 is
`b5c9786508c14ecac7e3c3b704f99e1451bc630f5c7fecccd67463c67fb1c512`.

Action003 canonical SHA-256 is
`72cd2c312ce3a3d1b2939fd9cf3d50f9c0d3dec933c5e716433c6da09abc07e8`.
Sequence 40 consumed it at `2026-09-30T09:27:00Z`; it cannot be reused.
Receipt SHA-256 is
`78514620f3b15e5a9cc0575a6b166f89e5eede8a66686b3ce83ad71ef7aaa24c`;
physical identity matches its native event. Original action001 and action002
receipt hashes were independently checked unchanged. Raw logs, evidence,
archive and runtime observations remain private and preserved.

At `2026-09-30T09:30:02.7040613Z`, an exact owned-PID query confirmed
both driver and native parent absent using explicit missing-process results.
Source/ref freeze was released. No selector, assertion, command deadline,
production environment, Policy threshold or budget was changed. A retry
requires diagnosed progress, fresh current preflight, a new single-use
action and the complete independent native V2 plan. Coverage success does
not waive the two failed required checks or authorize publication.
