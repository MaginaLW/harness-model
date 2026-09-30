# Second complete native V2 result

Independent actor `e4-temp-independent-verifier` executed the complete default
V2 plan on subject `b3c71296f0202a2e6a30ac2e65ca76d73225eab6`, branch
`codex/e4-verification-control`, base
`ef92b795da729566870ff4878f100a4ffe319db5`.
Run `run-20260930T061308181959Z` started at
`2026-09-30T06:13:06.738076Z` and ended at
`2026-09-30T07:03:29.064485Z`. The CLI exit was 0 after recording FAILED;
that handled exit does not mean verification passed. Native Gate returned
1, REJECT. No implementation Review export or finalization followed.

| Check | Status | Exit | Timeout | Duration, ms |
| --- | --- | --- | --- | --- |
| contract | passed | 0 | false | 438 |
| scope | passed | 0 | false | 797 |
| ruff_check | passed | 0 | false | 250 |
| ruff_format_check | passed | 0 | false | 141 |
| smoke | passed | 0 | false | 203 |
| unit_tests | passed | 0 | false | 235234 |
| regression_tests | failed | null | true | 900547 |
| mypy | passed | 0 | false | 5657 |
| coverage_xml | failed | null | true | 1200563 |
| diff_coverage | failed | 1 | false | 5109 |
| acceptance | passed | 0 | false | 1437 |
| integration | failed | null | true | 600328 |
| targeted_mutation | passed | 0 | false | 0 |
| independent_verifier | passed | 0 | false | 0 |

Unit completed with 1838 passed in 234.36 seconds; acceptance completed
with 9 passed in 0.68 seconds. Regression, coverage and integration have
no terminal pytest summary. Coverage XML is absent; total and diff coverage
remain unknown. The last two zero durations are native evidence projections.
All five fixed mutations actually ran: baseline exit 0, mutant exit 1,
outcome killed, no timeout, with durations 1296, 12062, 1204, 1281 and
1781 ms. The native consumer passed and confirmed `main_tree_unchanged: true`.

Task evidence and run archive are byte-identical, SHA-256
`cf9d00602efb28481b976c464806aead239587e7a73affd97c7a8c540af612d4`.
Schema and snapshot validate; snapshot SHA-256 is
`be6920f9461e531157969dcbcb18c176a85f25a10a3357c76a516377bb335ed8`.
Verifier context SHA-256 is
`479b8885afd1f57c42f1bb731d8bfe3addd963b86a714a9c0914c6c632bca25d`,
matching current context at handback. The independent audit checked all
24 non-null task-relative log references and four native null references;
its SHA-256 is
`f2bafb26d0032c82430d724781f41e6f44915bea75fd58ac0de85aea62387457`.

Action002 canonical SHA-256 is
`824d783a2bf0fce82b053e5ac330b9886f8d3924b5cdee3515c59586a1636019`.
Sequence 25 consumed it at `2026-09-30T07:02:20Z`; it cannot be reused.
Receipt SHA-256 is
`d32afeddeeb6b32521de0393e66e147cd001eb12f6394d7cf1dd4498675ae68b`;
physical identity matches the native event. Mutation canonical SHA-256 is
`29b71fc9b37d8065d4aba84fa34d1008fde55587a463151878e3a6d20061056b`.
The original run001 raw logs, archive, receipt and corrected auxiliary audit
were independently checked unchanged. All raw runtime facts remain private.

The regression progress stream contains failures and errors before its
timeout. A read-only collection mapped candidate node IDs; extra teardown
errors can shift later ordinals, so that mapping is diagnostic guidance,
not completed test evidence. Two independent bounded investigations now
target actual historical-import failures and the nested real-pytest cases.
Original assertions, Policy deadlines and minimal process environment stay
unchanged. A retry requires a diagnosed repair, a fresh exact-subject action
and a complete independent native V2 result.

Follow-up original-case diagnosis confirms a historical attachment's ordinary
copy access failed at 261 characters although extended-path reading succeeded.
A shorter ordinary parent reduced that attachment to 246 characters, but
its corruption write still failed on a 260-character atomic temporary name.
The original e2e review case changed from failed to passed with that shorter
parent. An external-review module run with `-x` completed 83 passed and
one failed; its remaining cases were not executed.

Both nested real-pytest parameter cases passed independently. A complete
verify-command module diagnostic instead reached its 220-second outer
limit while a fixture Git helper was blocked. The actual stack identifies
Windows `subprocess.run` timeout cleanup: after its original 10-second Git
deadline, `kill()` was followed by `communicate()` without another deadline,
waiting for a pipe-reader thread. The Git command was `git add .ai tracked.txt`;
all existing paths in that diagnostic were below 260 characters. Why that
Git command exceeded 10 seconds and which descendant held a pipe remain
unknown. Only the new owned diagnostic process tree was terminated. These
diagnostics do not supersede the failed complete native evidence.
