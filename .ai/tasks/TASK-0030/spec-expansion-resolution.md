# TASK-0030 acceptance scope resolution

The first full V1 run under active Policy `2.2.0` is retained as failed evidence in
`run-20260831T132605537718Z`. Its regression check completed in 621.97 seconds and its coverage
check completed with XML in 735.31 seconds, so both exceeded or approached the former 600-second
runner limit without timing out under the new budgets.

Both checks reported the same two failures in
`tests/acceptance/test_phase_02_self_hosting.py`. The assertions treated TASK-0025's retained
Policy `2.1.0` classification as current after the active Policy changed to `2.2.0`; the verifier
service correctly rejected that classification as stale. The minimal correction adds only this
acceptance file to TASK-0030's business scope, asserts the historical/current digest difference
and fail-closed error code, and uses the retained immutable TASK-0025 verifier context only for a
negative reuse check.

No TASK-0025 artifact, evidence, approval, review, event, or Gate conclusion will be modified.
The failed TASK-0030 run remains append-only. Implementation of the acceptance correction must
wait for reclassification, a newly frozen specification, independent design review, and fresh
owner approval.
