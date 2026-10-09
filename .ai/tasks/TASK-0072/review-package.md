# Review Package

## 审核目标

裁决 TASK-0072 实现提交 `3ff8f600775d329f09dc237418ddcd377d80d196` 与审核修正提交 `65512bee49f8b57f42b2b8eb1fce6f803a8a4eaf` 是否满足冻结规格 `b66b0eb12764dd6c6d1294f366338428322022feb80ccc0d85eb1291ac704ded`：V1/V2 的 pytest 检查共享一次完整覆盖率执行，且检查 ID、evidence、Gate 与门槛不变。

## 背景

Policy 2.3.0 下 V1 运行 3 次、V2 运行 5 次 pytest，记录中的 V2 因 900/600 秒超时反复失败。现有计划引擎会把命令、环境、cwd、日志敏感度完全相同的检查合并为一次执行，pytest parser 只看退出码。设计审核 REV-0001（REQUEST_CHANGES）→ REV-0002（APPROVE）→ Policy 2.4.0 重新分类后 REV-0003（APPROVE）。

## 代码地图

- `.ai/policy/*.yaml`：版本 2.4.0；`verification-levels.yaml` 中 `unit_tests`、`regression_tests`（V1/V2）与 `acceptance`、`integration`（V2）取 `coverage_xml` 的命令、环境与 1200 秒超时。
- `src/aiflow/verification.py`：`_require_output_semantics` 对五项 pytest 检查固定完整套件 argv（含 `{python}` 解释器）、`COVERAGE_FILE` 环境、1200 秒超时（`FULL_SUITE_TIMEOUT_SECONDS`）与 parser；逐项全部固定后不再需要单独的同一执行检查（REV-0004 修正）。
- `.github/workflows/ai-quality-gate.yml`：“Validate contracts” 仅在非 bootstrap 模式运行；预算注释更新。
- 测试：`tests/unit/test_policy.py`、`tests/unit/test_verification_plan.py`、`tests/integration/test_templates_and_policy.py`、`tests/acceptance/test_v2_acceptance.py`、`tests/integration/test_github_workflow.py`。
- 文档：quickstart、recovery、pytest-temporary-roots、README、maintenance-status。

## 语义变更

- 五项 pytest 检查在 evidence 中仍逐项出现，但共享同一进程结果与日志；任一测试失败或超时使全部关联检查失败，不再按子集归因。
- `--check acceptance` 等局部检查运行完整覆盖率套件。
- 任何子集选择器、额外参数、不同超时或环境均在计划解析时被拒绝。
- bootstrap 模式 CI 不再单独重跑契约测试；非 bootstrap 模式保留。

## 风险

- 单次完整执行 1200 秒预算：本次本机实测 1083 秒，余量约 10%；超时仍是失败，不放宽。
- Policy 变化使其他非终态任务的分类失效，需各自按 CLI 重新分类（规格非目标）。
- 本任务为 V1，真实运行只覆盖 V1 合并；V2 五项合并由计划解析与 acceptance 测试证明。
- 85% 总覆盖率不由 `aiflow verify` 强制（未改变现状），本次手动核对。

## 证据

- 已验证：最终 AI Flow V1 evidence：`.ai/tasks/TASK-0072/evidence.json`，subject `65512bee49f8b57f42b2b8eb1fce6f803a8a4eaf`，run `run-20261009T150800114580Z`，10 项检查全部 passed；`unit_tests`、`regression_tests`、`coverage_xml` 共用一次执行：`2835 passed, 1 skipped in 819.84s`；verify 总耗时 823 秒。
- 首次 V1 evidence（subject `3ff8f60`，run `run-20261009T143814004346Z`）同样 passed：`2834 passed, 1 skipped in 1083.47s`；两次差异来自本机负载波动。
- 总覆盖率：`COVERAGE_FILE=<run>/.coverage python -m coverage report --fail-under=85` → TOTAL 89%，通过。diff coverage（基于 `9215ae1`）100%。
- mypy、ruff check/format、`git diff --check` 通过；移除超时或解释器固定后，新增负向用例失败（已在临时副本中核对后恢复）。
- 计划模拟：V1 一个 pytest execution（3 个检查 ID），V2 一个 pytest execution（5 个检查 ID），超时 1200 秒。
- 实现审核 REV-0004（APPROVE_WITH_CONDITIONS）的 RF-001～RF-003 已在 `65512be` 修正；RF-004（范围外的 chapter-11 历史文档、CHANGELOG）与 RF-005（1200 秒余量、V2/Linux 耗时未测）保留为已声明限制。
- 未验证：真实 V2 运行；Linux CI 上的单次执行耗时。

## 审核问题

1. 固定命令形状与“同一执行”约束是否足以阻止 acceptance/integration 被静默缩减为子集？
2. evidence/Gate 是否在共享执行下仍正确反映每个检查 ID 的结果？
3. 文档是否准确描述共享执行、失败归因与 `--check` 语义？
4. REV-0004 的 RF-001～RF-003 修正是否充分？

## 推荐结论

APPROVE：实现与冻结规格一致，V1 实测只运行一次 pytest 且全部检查通过，门槛与检查 ID 未变；剩余风险已在规格与文档中声明。
