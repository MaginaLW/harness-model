# Second V2 interruption and performance investigation

The second native V2 run used fixed source subject
`59bba106ad56530d39cbce3885cb8206381b7ea8` and committed admission HEAD
`00560ee7c78d3a41851fa9481eff5b49d5a8af7c`.
The full unit suite passed 1730 tests in 214.72 seconds; mypy reported no issues
in 42 source files. The legacy parser regression did not recur.

The regression subprocess began at 2026-09-29T21:39:57Z. Its partial stdout and
empty stderr were written at 21:54:57Z, matching the existing 900-second deadline.
Output contained 2104 passed progress markers and one skip marker, ending at
83 percent without a pytest completion summary. The runner's per-check return
fields were still in memory when stopped, so no final regression result or
overall passing evidence is claimed. The exact memory-held timeout flag and
individual slow-test or host cause were not independently recovered.

The independent verifier stopped only its confirmed process tree and recorded
native `verify --abandon`. Coverage was interrupted; acceptance, integration and
the five mutations were not reached. Original run logs, `verification-outer-002.log`
and `verification-stop-002.json` remain under this task's ignored logs directory.
The first failure, both verifier contexts and all native failure events remain.

A current diagnostic collection contains 2514 cases. The last reported case
was a runner-inspection domain-error parameter; its position does not identify
the performance cause. The new external-review integration cases occur earlier
in that collection and had already emitted their progress markers.
Representative profiling and bounded host observations are preparation only.
They do not replace native verification or justify any test removal, extra skip,
changed Policy, expanded timeout or lowered coverage threshold.
