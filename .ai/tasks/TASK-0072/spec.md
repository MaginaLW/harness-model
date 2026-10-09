# Task Specification

## 目标

V1/V2 验证不再重复执行同一套 pytest：`unit_tests`、`regression_tests`、`coverage_xml`（以及 V2 的 `acceptance`、`integration`）共享一次固定的完整覆盖率 pytest 执行；所有检查 ID、required 状态、evidence 结构与 90% diff coverage 门槛保持不变。PR CI 只在 bootstrap 模式下省去与随后完整覆盖率运行重复的契约测试步骤。

## 范围

- `.ai/policy/*.yaml`：Policy 版本升至 `2.4.0`；上述五项检查使用完全相同的命令 `{python} -m pytest --cov=aiflow --cov-branch --cov-report=xml:{run_dir}/coverage.xml`、环境 `COVERAGE_FILE={run_dir}/.coverage` 与 1200 秒超时，由现有计划引擎合并为一次执行。
- `src/aiflow/verification.py`：将上述五项检查的命令、环境、超时与 parser（`coverage_xml` 用 `coverage_xml`，其余用 `pytest`）固定为该完整套件形状；不接受任何额外参数（测试路径、`-k`、`--ignore`、`--deselect`、`-x` 等）。
- `.github/workflows/ai-quality-gate.yml`：“Validate contracts” 步骤仅在非 bootstrap 模式运行（bootstrap 模式由完整覆盖率运行覆盖）；更新过期的 68.5 分钟预算注释，`timeout-minutes` 不变。
- 测试（`tests/**`）：更新固定旧命令的断言；新增负向测试（五项同带子集选择器仍被拒绝、超时或环境不一致被拒绝）与 `pyproject.toml` `testpaths == ["tests"]` 固定测试；保留 MUT-V2-001 检测测试。
- 文档：`docs/operations/quickstart.md`（共享执行、失败归因与 `--check` 语义）、`docs/operations/recovery.md`（Policy 版本与超时）、`docs/operations/pytest-temporary-roots.md`（历史说明加注）、`README.md`、`docs/operations/maintenance-status.md`。
- `.ai/tasks/TASK-0072/**`。

## 非目标

- 不删除或重命名任何检查 ID，不改变 evidence/approval/gate 语义、mutation manifest、diff coverage 门槛或分支保护。
- 不在 `aiflow verify` 中新增 85% 总覆盖率强制（现状仅 CI bootstrap 强制）；本任务手动运行该检查。
- 不改写历史任务记录、证据或其绑定的 Policy 2.3.0；不处理其他未完成任务因 Policy 变化产生的重新分类。
- 不执行 push、merge、deploy、delete 或任何外部动作。

## 验收条件

- V1 计划中 `unit_tests`、`regression_tests`、`coverage_xml` 为同一 execution；V2 计划中再加上 `acceptance`、`integration`；V2 evidence 仍含全部 14 个检查 ID。
- 五项中任一命令带额外参数、或超时/环境/parser 不一致时，计划解析以 `VERIFICATION_COMMAND_INVALID`（或覆盖率配置错误码）拒绝。
- `python -m pytest tests/unit/test_policy.py tests/unit/test_verification_plan.py tests/integration/test_templates_and_policy.py tests/acceptance tests/integration/test_verify_command.py tests/integration/test_github_workflow.py -q` 通过。
- 完整质量检查通过：全量 pytest 带 `--cov-fail-under=85`、diff coverage ≥90%、ruff check/format、mypy、`git diff --check`。
- 实现提交后 Policy 变化使本任务分类失效：按 CLI 以 `policy_changed` 升级、resolve、重新分类，重新取得设计审核与规格批准，再运行 AI Flow `verify` 与 `gate`；记录本次 verify 的 pytest 执行次数与耗时。

## 禁止动作

push、merge、deploy、delete、secret_export、paid_external_call；不修改其他任务目录。

## 错误行为

- 五项 pytest 检查中任一命令、环境、超时或 parser 偏离固定完整套件形状时，计划解析必须拒绝。
- 共享执行的 pytest 失败或超时时，所有关联检查均为 failed；coverage.xml 缺失时 `coverage_xml` 仍报 `VERIFICATION_COVERAGE_XML_MISSING`。
- 已知代价：失败不再按子集归因，日志共用一个执行；`--check acceptance` 等会运行完整覆盖率套件。

## 回滚

`git revert` 本任务实现提交即可恢复 Policy 2.3.0、原命令约束与 CI 步骤；历史证据不受影响。
