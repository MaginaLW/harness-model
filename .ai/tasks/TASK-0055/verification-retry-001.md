# First V2 failure and fixed-candidate retry

The native V2 run at subject `8526db074b41071ebd03de4ca13ae25bf7316baa`
found a real legacy CLI regression: `test_cli_domain_error_does_not_emit_traceback`
raised `UnboundLocalError` because the new domain-error handler read `arguments`
before parser initialization had completed. Unit results were 1725 passed and
1 failed in 145.14 seconds. The independent verifier stopped its confirmed
process tree and recorded native `verify --abandon`; the run is failed, not passed.
The regression run was interrupted, and later checks and mutations were not run.
The original logs, `verification-outer-001.log` and `verification-stop-001.json`
remain under this task's ignored logs directory.

Fixed subject `59bba106ad56530d39cbce3885cb8206381b7ea8` establishes the invocation
kind before parser initialization. The existing legacy test is unchanged; four
pure-unit cases cover builder/parser domain errors, sensitive synthetic input
and closed stderr. The focused check passed 51 tests, and Ruff, format and mypy
passed. These checks are preparation for a complete new native V2 run.

The source fix remains within the unchanged approved frozen specification.
Native subject synchronization preserves its current design/spec approval and
classification. A new exact-subject, single-use mutation action is recorded;
the former action and all failure events remain unchanged. No threshold, timeout,
Policy, CI, source scope, external action or approval requirement changes.
