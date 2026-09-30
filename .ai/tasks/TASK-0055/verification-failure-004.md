# Fourth complete V2 result and bounded follow-up

The fixed source is `835701786550eeea79c27b68337c7de0bd59b3a1`; admission
HEAD is `c1a07638a2bb5dc67413a86f2f4293dbf3ecab9b`. The independent native run
`run-20260929T225100776687Z` ended normally at `2026-09-29T23:39:26Z`.
The CLI and outer launcher returned 0, but the native conclusion is **failed**
and TASK-0055 is FAILED. A successful CLI exit is not a passing verification.

All 14 required checks have actual results. Ten passed, including 1738 unit
tests (160.94 seconds), 9 acceptance tests (3.26 seconds), Ruff, format, mypy,
contracts, scope and smoke. Regression timed out at 900140 ms, coverage at
1200297 ms and integration at 600359 ms; each has exit code null and
`timed_out: true`. Diff coverage exited 1 because coverage.xml was absent.
Coverage metrics and complete regression/integration totals remain unknown.
No original budget, test, skip, Policy or quality threshold changed.

All five canonical mutations were killed, with baseline exit 0, mutant exit 1
and no timeout. The runner confirmed `main_tree_unchanged: true`. Action004
was consumed once at `2026-09-29T23:38:53Z`; the immutable action-use receipt
records its native result. It cannot be reused for another invocation.

The original failed evidence was copied create-only into the ignored run
directory as `failed-evidence.raw.json`; byte SHA-256 is
`c40fa68c36cf26c67e0126219400782e91f4c743e3bbad850e54a05c0012d954`.
The validated native V2 snapshot is
`a22daebf40df38e4b044a0f27b636915bf9d7c3d6920a25645be8e736a4fb9cb`.
Original stdout/stderr, coverage diagnostics, mutation artifacts and
`verification-outer-004.log` remain private ignored records. No raw evidence
is sanitized, rewritten or represented by this portable note.

Integration partial stdout contained four failures at collected positions
94, 177, 294 and 299, without a completed failure summary. Current collection
mapped them to the existing close command, implementation preflight, archived
Finding context and first-version/replay tests. The exact four were then run
through the native process runner's unchanged minimal environment on unchanged
production source: all four passed in 25.07 seconds, exit 0, no timeout.
Preparation logs, JUnit and runner result remain under the ignored diagnostic
directory. This does not identify the earlier failure causes or replace V2.

Current resource observations found substantial system-disk queues while a
separate local disk was idle. These are current observations, not proof of a
past timeout cause. Native ordinary checks pass only PATH, SystemRoot and
COVERAGE_FILE; changing outer TMP or merely relocating a checkout does not
move their preferred Windows temporary directory. No user process, system
setting, runner environment, Policy or directory permission was altered.

Next preparation may eliminate repeated genuine first-record test setup while
keeping all cases, assertions, isolated Git copies and subsequent real
preflight/writer observations, and may relocate the sole source checkout to
the separate disk with a newly verified locked editable environment. Any new
candidate still requires the full original V2 plan and a new exact-subject,
single-use canonical action. Implementation Review, finalize, owner code
approval, passing Gate, push and merge are not complete.
