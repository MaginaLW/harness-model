# TASK-0072 Policy 2.4.0 resolution

- Implementation commit: `3ff8f600775d329f09dc237418ddcd377d80d196`.
- Change: all four Policy files move from `2.3.0` to `2.4.0`; in `verification-levels.yaml` the
  V1/V2 `unit_tests`, `regression_tests` and V2 `acceptance`, `integration` checks take the exact
  `coverage_xml` command, environment and 1200 s timeout. No other routing, hard-rule or
  permission content changed.
- This change was planned in frozen spec `b66b0eb12764dd6c6d1294f366338428322022feb80ccc0d85eb1291ac704ded`
  (验收条件, last item) and approved with design review REV-0002.
- Next: reclassify under Policy 2.4.0, record a fresh design review and spec re-approval, then
  sync, verify and gate.
