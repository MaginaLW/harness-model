# Fourth complete native V2 result

Independent actor `e4-temp-independent-verifier` ran the complete default V2
on source subject `38648440f5a862edd5a7dccfb55a60aae4f6757e`, admission HEAD
`36efe4cc7cc85ccd368c2df065cd4e99f0963b9f`, branch
`codex/e4-verification-control`, base
`ef92b795da729566870ff4878f100a4ffe319db5`. Frozen specification is
`e3fcf4e6c3f13aef834d71be2e10b4947098311e383b5bb100bdf74d183ddd85`.

Run `run-20260930T112131331525Z` started at
`2026-09-30T11:21:30.498868Z` and ended at
`2026-09-30T12:04:40.479668Z`. Driver/native handled exit 0 recorded FAILED:
13 required checks passed and integration timed out. Native Gate returned
exit 1, REJECT. No implementation Review context, finalization or code
approval followed. Python 3.11.9, original MINENV, selectors, deadlines,
thresholds and five fixed mutations remained unchanged.

| Check | Status | Exit | Timeout | Duration, ms |
| --- | --- | --- | --- | --- |
| contract | passed | 0 | false | 375 |
| scope | passed | 0 | false | 765 |
| ruff_check | passed | 0 | false | 532 |
| ruff_format_check | passed | 0 | false | 93 |
| smoke | passed | 0 | false | 188 |
| unit_tests | passed | 0 | false | 131062 |
| regression_tests | passed | 0 | false | 857891 |
| mypy | passed | 0 | false | 313 |
| coverage_xml | passed | 0 | false | 973125 |
| diff_coverage | passed | 0 | false | 750 |
| acceptance | passed | 0 | false | 656 |
| integration | failed | null | true | 600140 |
| targeted_mutation | passed | 0 | false | 0 |
| independent_verifier | passed | 0 | false | 0 |

Unit tests completed 1869 passed in 130.82 seconds. Complete regression
completed 2707 passed and one existing POSIX FIFO skip in 857.61 seconds.
Complete coverage collected 2708 and completed 2707 passed/one skip in
972.57 seconds. Acceptance completed nine passed. Coverage XML contains
7483/8187 covered lines and 2321/2834 covered branches: combined coverage
is 88.9574 percent. Diff coverage printed 97 percent, 301 changed lines and
nine missing. Passing these checks does not waive integration.

Integration used the original complete `tests/integration -q` selector and
600-second deadline. Its partial stdout reached 89 percent followed by 25
dots, with no terminal collection/result summary; stderr was empty. Static
count found 744 dots and one original skip. This is neither a complete pass
nor evidence that the last printed module caused the aggregate timeout.
Per-test phase durations remain unknown and require complete diagnostic
measurement before choosing another correction.

All five mutations had actual baseline exit 0, mutant exit 1, killed outcome
and no timeout. Public consumption confirmed `main_tree_unchanged: true`.
The two zero-duration rows are native evidence projections, not substitute
tests or final independent implementation Review.

Current task evidence and archived evidence are byte-identical, SHA-256
`4d2c8f05e9fc4b73ea61a8836b11b8069cdd34a4b7acf573faf513a08d2848bc`.
Schema/snapshot validate; snapshot SHA-256 is
`551afcaef27f5a8a353f7b261b36b908a6a5e0c06a995bef8fc600c92ace2639`.
Verifier context SHA-256 is
`164aeaa4b0f901ee9f9e1aff1b2b4f95eb9c81a692f3a22fc2eb1b317f2dbc54`.
Independent audit checked every 24 non-null task-relative reference and
four native null references; audit SHA-256 is
`d2127599c7769043859de746ee2987e969a1ad783353b714d6c5d155bc699ca9`.
Coverage XML SHA-256 is
`a0ca9de68fcea1d8c710f939df6ef0ed5bc3a2efb2d0b57eb9ca17aaa097d7fe`.
Mutation canonical SHA-256 is
`ab8777894305fbb0ac9a5be88b5490bce1fcf2a69e69e72b5f10b22fa1217f6a`.

Action004 canonical SHA-256 is
`837674124a8da1874968998e295a201b321fbb47cee20356a24abc142ed9d4dd`.
Native event sequence 54 consumed it at `2026-09-30T12:04:18Z`; receipt
SHA-256 is
`eaf86032a29842eaad2c46e6207bb4077da747c6c921f70bcd4234a8d3c6a07a`.
It is not reusable. Prior failures, receipts and raw evidence remain intact.

At `2026-09-30T12:06:27.1122498Z`, exact owned driver/native PID queries
succeeded and confirmed both absent; no process was killed. The verifier
explicitly handed back the source/ref/ledger/test freeze after audit.
Next work measures the complete unchanged integration selector on a fixed
candidate using the original runtime/environment and fresh guarded leaves.
That diagnostic cannot replace the 600-second native check, authorize
Task55 dependency admission or publication, or justify budget/selector
changes. A later full V2 needs diagnosed progress and a fresh single-use
action.
