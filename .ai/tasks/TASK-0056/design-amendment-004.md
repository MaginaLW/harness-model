# TASK-0056 fourth design amendment

The complete fourth V2 remains FAILED: 13/14 checks passed; integration timed
out at 600140 ms with no terminal exit code. Action004 is consumed. The preserved
failure report and original logs remain authoritative; no implementation review,
finalization, code approval or Gate pass is asserted.

The complete private integration profile finished 801 tests and skipped the one
original FIFO case in 851.34 seconds, actual exit 0. Its profiler and diagnostic
outer deadline prevent treating this as the original 600-second check. The report
SHA256 is 48a9775847fd4f592c7204a9e1a6217bcdc4b47a758c56026ff57ee93520ade2.

A separate original-environment benchmark completed with actual exit 0 and no
timeout. Twenty original initial repositories averaged 0.36051 seconds each;
twenty complete physical copies plus current source fingerprints averaged
0.05784 seconds. All copies matched the pristine seed bytes and independent
working-tree, index and commit mutations did not affect another copy or seed.
The result SHA256 is
9903815f99214a68b5ecc538359d259f1d70b8cabc0a5fe9002a31c1a3995add;
the completed-run SHA256 is
8f89855fa5bb8dc3f1ffbf0460543023fad36eae27a5666b8018bc4935625c90.
This isolates copying feasibility, not complete qualification cost, timeout
causality, platform-wide compatibility or a full V2 pass.

The amendment adds three explicit integration utility/test paths and a thin
entry at the existing shared repository builder. Only a pristine initial
repository built successfully at its original target may seed a session-private
snapshot. Current source/config/template eligibility, physical Git isolation,
original errors/partial state and subsequent real governance remain mandatory.
All original assertions, command deadlines, selectors, MINENV and gates remain.
Unknown config material stays in memory and is never printed or persisted.

The old frozen specification is preserved byte-for-byte as spec-design-004.md
(e3fcf4e6c3f13aef834d71be2e10b4947098311e383b5bb100bdf74d183ddd85).
The amended design requires native reclassification, freezing, independent
design review, current owner spec approval and begin before implementation.
