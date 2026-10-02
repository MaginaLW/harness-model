# TASK-0056 complete passive integration timing

The fixed source subject remains e3790a43bf51b976816a8eaf8770789c7f90a1f2;
checked own-ledger head was 12d4af9dc158192eca290e6a1c99b66458443c30. Exact
locked Python 3.13.15 ran the original complete tests/integration -q selection
with original native MINENV and a fresh owned EXEC-012 leaf. The external wrapper
only observed collection IDs, report fields and session exit; no cProfile,
test/helper monkeypatch or extra pytest selection option was used.

Run run-20260930T164044761682Z started 2026-09-30T16:40:44.801048Z and ended
16:54:24.434888Z. Pytest actually reported 854 passed, one existing FIFO skipped,
818.91 seconds; wrapper elapsed 819.371 seconds, actual pytest/driver/launcher
exits zero, no outer timeout. The private diagnostic ceiling was 1000 seconds.
This does not pass or replace the original 600-second prerequisite, whose
600188ms timeout/unknown pytest exit remains preserved in failure-006.

Collection contained 855 unique IDs. Every ID's real setup/call/teardown outcomes
was audited, without inferring completion from reportCount/3. There were no gaps,
duplicates or audit issues. The sole skip was the original FIFO call in
test_external_review_command.py::test_nonregular_input_is_rejected_before_open[fifo].
All 53 test_repository_fixture cases passed every phase. Main actual return and
sessionfinish exitstatus were both zero; telemetry errors were empty. Observer
callbacks measured 0.0822303 seconds; total instrumentation overhead is unknown.

The disjoint phase-duration sum over all 36 modules was 818.163996 seconds.
Largest module totals include:

| Module | Phase seconds |
| --- | ---: |
| external_review_command | 217.340 |
| verify_command | 136.797 |
| observation_escalation | 56.102 |
| repository_fixture | 55.662 |
| gate_command | 53.027 |
| verification_evidence_flow | 51.893 |
| classify_command | 41.940 |
| begin_close_commands | 41.551 |

These locate aggregate module/phase cost, not internal Git, validation or fixture
eligibility cost. Different source/runtime/case-set/profiling conditions prevent
attributing changes against old measurements. Warm-use counts and the timeout
root cause are not established by this observer.

Private create-only materials remain in integration-passive-phases-001 under
the owned runtime root. Completed SHA256:
6de80a939f3cdbd4d15fa9f8cbeffe6cf117436c194f519068100f533b762c52.
Per-ID audit SHA256:
9527ef9a96bd41d897822a17c8aa5b10c88a5fed503026ddb4738df9fe1274c0.
Handback SHA256:
22bbe3fe186f88577a8f2e3456908067d24856804d2f588b993fa375d8287762.

All 24 source hashes, eight old failure/receipt hashes, clean head/status and
actual common refs were equal before/after. Bounded creation-aware process
audit succeeded; all 13 known owned/actual child PIDs were absent and direct
retained processes had actual exits zero. Source/ref/ledger/test resources were
released. No action005 or native V2 was started; 3.13 formal-selection conditions,
implementation Review/finalization/code approval/Gate and dependent Task55/57
entry conditions remain unmet. Matching real report F remains unknown.
