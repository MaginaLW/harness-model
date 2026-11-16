# Task Specification

## 目标

按项目所有者在 `A02` 中明确批准的方案，退场外围未接入主引擎的 `tools/analysis/*` 离线参考/合成模拟脚本（`11` 个 Python 模块）及其 `18` 个专属测试文件，并将 `pyproject.toml`、GitHub Actions `ai-quality-gate`、`tools/ci/check_coverage.py`、`src/aiflow/verification.py`、`.ai/policy/verification-levels.yaml` 与 `docs/operations/quickstart.md` 的覆盖率及类型检查范围统一收敛到核心域 `core`（`src/aiflow`），完整保持 `>= 85%` 总分支覆盖率与 `>= 90%` diff coverage 门禁阈值不变。

## 范围

仅允许修改任务 `allowed_scope` 内的以下文件（外加本任务账本目录 `.ai/tasks/TASK-0156/**`）：

1. 删除 `tools/analysis/` 全部 `11` 个外围脚本模块：
   - `tools/analysis/approval_overhead.py`
   - `tools/analysis/benchmark_reference.py`
   - `tools/analysis/pr_feedback.py`
   - `tools/analysis/repository_readiness.py`
   - `tools/analysis/review_advisory.py`
   - `tools/analysis/review_detection.py`
   - `tools/analysis/review_detection_analysis.py`
   - `tools/analysis/review_detection_input.py`
   - `tools/analysis/review_detection_sources.py`
   - `tools/analysis/review_feedback.py`
   - `tools/analysis/review_feedback_simulation.py`

2. 删除仅验证已退场 `tools/analysis/*` 脚本的 `18` 个专属测试文件：
   - `tests/integration/test_approval_overhead.py`
   - `tests/integration/test_repository_readiness.py`
   - `tests/unit/test_benchmark_reference.py`
   - `tests/unit/test_confidence_availability.py`
   - `tests/unit/test_feedback_text.py`
   - `tests/unit/test_pr_feedback.py`
   - `tests/unit/test_pr_feedback_followups.py`
   - `tests/unit/test_review_advisory.py`
   - `tests/unit/test_review_detection.py`
   - `tests/unit/test_review_detection_analysis.py`
   - `tests/unit/test_review_detection_input.py`
   - `tests/unit/test_review_detection_sources.py`
   - `tests/unit/test_review_feedback.py`
   - `tests/unit/test_review_feedback_calibration.py`
   - `tests/unit/test_review_feedback_projection.py`
   - `tests/unit/test_review_feedback_score.py`
   - `tests/unit/test_snapshot_git_bounded.py`
   - `tests/unit/test_telemetry_snapshot.py`

3. 收敛治理、验证、CI 与工具配置中的 `tools/analysis` 域引用（`5` 个核心/治理文件 + `docs/operations/quickstart.md`）：
   - `pyproject.toml`：`[tool.coverage.run]` 的 `source = ["aiflow"]`；`[tool.mypy]` 的 `files = ["src"]`。
   - `.github/workflows/ai-quality-gate.yml`：`Bootstrap quality checks` 中 pytest 参数改为 `--cov=aiflow --cov-branch \`（移除 `--cov=tools/analysis`）。
   - `tools/ci/check_coverage.py`：`DOMAINS = (("core", "src/aiflow"),)`，同步更新文件顶部模块文档字符串；保持 `core` 域空文件集拒绝、未测量文件集拒绝、`< 85%` 总分支覆盖率拒绝、路径越界拒绝及 `diff-cover --fail-under=90` 逻辑不变。
   - `src/aiflow/verification.py`：`_require_output_semantics` 中 `PYTEST_CHECK_IDS` 的 `expected_argv` 移除 `"--cov=tools/analysis"`，保持运行目录绑定与超时/解析器语义校验不变。
   - `.ai/policy/verification-levels.yaml`：保持 `policy_version: "2.6.0"` 不变；从 `V1`（`unit_tests`、`regression_tests`、`coverage_xml`）与 `V2`（`unit_tests`、`regression_tests`、`coverage_xml`、`acceptance`、`integration`）移除 `--cov=tools/analysis`；将 `V1` 与 `V2` 的 `mypy` 命令改为 `["{python}", -m, mypy, src]`。
   - `docs/operations/quickstart.md`：同步将验证重放命令与覆盖率说明从双域（`src/aiflow` + `tools/analysis`、`coverage-analysis.xml`、`mypy src tools/analysis`）更新为单核心域 `core`（`--cov=aiflow --cov-branch`、`coverage-core.xml`、`mypy src`、总分支覆盖率 `>= 85%` 且 diff coverage `>= 90%`）。

4. 同步更新耦合契约与覆盖率门禁测试（`6` 个测试文件）：
   - `tests/unit/test_policy.py`：更新 `full_suite["command"]` 与 `mypy` 命令断言为单核心域命令。
   - `tests/unit/test_verification_plan.py`：移除预期命令中的 `"--cov=tools/analysis"`。
   - `tests/unit/test_check_coverage.py`：适配单域 `DOMAINS = (("core", "src/aiflow"),)`，完整保留 `< 85%`、`nan`/`inf`、嵌套未导入源码文件、`diff-cover` 失败码 `1`/`2`、路径越界及无 Python 变更 diff 的单测覆盖。
   - `tests/integration/test_coverage_gates.py`：适配 `DOMAINS = ("src/aiflow",)` 与 `coverage-core.xml`，完整保留 `>= 85%` 总分支覆盖率、`>= 90%` diff coverage、未导入/隐藏源码文件检出及纯文档变更通过行为的端到端门禁测试。
   - `tests/integration/test_github_workflow.py`：断言工作流包含 `"--cov=aiflow --cov-branch"` 且不再包含 `"--cov=tools/analysis"`。
   - `tests/integration/test_acceptance_traceability.py`：同步更新对 `docs/operations/quickstart.md` 核心域覆盖率重放说明的断言。

## 非目标

- 不降低任何 CI 或验证门禁阈值（`core` 总分支覆盖率继续 `>= 85%`，diff coverage 继续 `>= 90%`，`ruff`、`format`、`mypy`、`whitespace` 全部保持强制）。
- 不修改授权文件（`AGENTS.md`、`.ai/policy/hard-rules.yaml`、`.ai/policy/permissions.yaml`）、路由规则（`.ai/policy/routing.yaml`）、`.ai/bootstrap-mode.yaml` 或 `policy_version`（保持 `"2.6.0"`）。
- 不在本治理任务中混入独立的 `docs/operations/{benchmark-reference,pr-feedback,review-*}.md` 运营文档归档与历史任务关闭记录（按 `AGENTS.md` 规则 8 拆分至紧随其后的独立文档归档/收尾 PR，减小治理任务耦合）。

## 验收条件

1. 定向契约与门禁测试全部通过：
   `pytest tests/unit/test_policy.py tests/unit/test_verification_plan.py tests/unit/test_check_coverage.py tests/unit/test_contracts.py tests/integration/test_templates_and_policy.py tests/integration/test_coverage_gates.py tests/integration/test_github_workflow.py tests/integration/test_acceptance_traceability.py tests/integration/test_resource_bundle_distribution.py tests/e2e/test_clean_checkout.py -q`
2. 静态与格式检查全部通过：`ruff check .`、`ruff format --check .`、`mypy`、`git diff --check`，且代码库（除历史归档与待归档独立说明文档外）在活跃验证/CI 配置中无残留 `tools/analysis` 引用。
3. 提交实现后执行完整原生 V1 验证 `aiflow verify TASK-0156 --actor verifier`，10 项检查全绿，`core` 总分支覆盖率 `>= 85%` 且 diff coverage `>= 90%`。
4. 独立设计审核与独立实施审核结论均为 `APPROVE`（无未关闭 `critical`/`high` 发现），记录 `spec` 与 `code` 批准后，`aiflow status TASK-0156 --format json` 为 `APPROVED_FOR_MERGE` / `gate_required`，`aiflow gate TASK-0156 --format json` 返回 `passed == true`（退出码 `0`），且远端 `ai-quality-gate` 通过后以 merge commit 合入 `main`。

## 禁止动作

- 禁止执行 `deploy`、`delete`（外部生产数据删除）、`secret_export`、`paid_external_call`。
- 禁止修改 `allowed_scope` 之外的文件，禁止触碰根工作区或其他保留工作树，禁止强推、squash 或 rebase。
- 禁止在 tracked 文件或提交信息中写入本机用户名或本机绝对路径。

## 错误行为

- `tools/ci/check_coverage.py` 在 `src/aiflow` 源文件为空、无分支覆盖数据、无已测量核心文件、`total < 85`、`total` 非有限浮点数或 `diff-cover` 返回非零退出码时，必须继续显式报错或返回非零退出码，不得弱化任何失败关闭分支。
- `src/aiflow/verification.py::_require_output_semantics` 对偏离单核心域全量覆盖率套件参数（如篡改 `--cov` 目标、缺少 `--cov-branch`、输出路径偏离 `{run_dir}/coverage.xml`）的配置必须继续抛出 `VERIFICATION_COVERAGE_CONFIG_INVALID` / `VERIFICATION_COMMAND_INVALID`。

## 回滚

- 本任务所有变更均在独立分支 `codex/retire-analysis-extension` 提交并以 merge commit 合入；历史 `tools/analysis/*` 完整保存在 Git 历史与既有 `archive/*` 标签中，如需恢复可通过 `git revert -m 1 <merge_commit>` 完整无损回滚。
