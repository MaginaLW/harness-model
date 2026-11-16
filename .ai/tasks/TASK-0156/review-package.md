# Review Package

## 审核目标

对 `TASK-0156`（分支 `codex/retire-analysis-extension`，基线 `a376ad4c94b6608e9a2a492f3f870e456be2618e`，待审实现提交 `e112514570fff25f45003ad628eb69a872b33b27`，Policy SHA 绑定升级提交 `1018532f`）进行 `implementation` 阶段独立审核，裁决实现是否完整满足 `.ai/tasks/TASK-0156/spec.md` 与 `V1` 验收条件，能否进入常设授权 `code` 批准及 `APPROVED_FOR_MERGE`。

## 背景

在项目瘦身排查及所有者明确批准 `A02` 选项后，确定退场从未被 `src/aiflow/` 主流程或 CLI 运行时导入的外围 `tools/analysis/*` 离线参考/合成模拟扩展（`11` 个 Python 模块、`18` 个专属测试文件），并将 CI、原生 `V1`/`V2` 验证策略、`pyproject.toml`、`tools/ci/check_coverage.py` 与 `docs/operations/quickstart.md` 的覆盖率及类型检查范围统一收敛到核心域 `core`（`src/aiflow`），同时严格保持 `>= 85%` 总分支覆盖率、`>= 90%` diff coverage 门槛以及 `policy_version: "2.6.0"` 与权限规则不变。

途中因 `.ai/policy/verification-levels.yaml` 变更导致基线 Policy SHA 变化，本任务已严格按 AI Flow 升级流程执行 `sync -> escalate(policy_changed) -> resolve -> classify -> freeze -> REV-0002(APPROVE) -> approve(spec) -> begin`，在新 Policy SHA（`72baefa4710edfc7ba10dc3de6b751d93c69226bab86222985f7b5009f11a50e`）下重分类、重审核并完成本地完整 `V1` 验证。

## 代码地图

| 文件 | 变更内容与职责 |
| :--- | :--- |
| `tools/analysis/*.py`（11 个文件） | 移除全部未接入主引擎的外围分析与合成模拟脚本 |
| `tests/{unit,integration}/test_*`（18 个文件） | 移除仅测试上述退场脚本的专属测试文件 |
| `pyproject.toml` | `[tool.coverage.run].source` 收敛为 `["aiflow"]`；`[tool.mypy].files` 收敛为 `["src"]` |
| `.github/workflows/ai-quality-gate.yml` | Bootstrap quality checks 去除 `--cov=tools/analysis`，保持 `--cov=aiflow --cov-branch` 与 `check_coverage.py`、`ruff`、`mypy`、`git diff --check` |
| `tools/ci/check_coverage.py` | `DOMAINS` 收敛为 `(("core", "src/aiflow"),)`，保留核心域非空目录、分支数据检查、`>= 85%` 总覆盖率与 `diff-cover --fail-under=90` 失败关闭门禁 |
| `src/aiflow/verification.py` | `_require_output_semantics` 中 `PYTEST_CHECK_IDS` 的 `expected_argv` 移除 `"--cov=tools/analysis"`，保持其余参数、运行目录与超时契约校验 |
| `.ai/policy/verification-levels.yaml` | 保持 `policy_version: "2.6.0"` 与全部阈值不变，移除 `V1`/`V2` 检查命令中的 `--cov=tools/analysis` 与 `mypy` 的 `tools/analysis` 参数 |
| `docs/operations/quickstart.md` | 更新验证重放命令与覆盖率说明至单核心域 `core`（`--cov=aiflow --cov-branch`、`coverage-core.xml`、`mypy src`） |
| `tests/unit/test_policy.py` | 同步 `V1`/`V2` `full_suite` 与 `mypy` 命令契约断言 |
| `tests/unit/test_verification_plan.py` | 同步 `parse_verification_plan` 预期命令行列表并保留缺少 `--cov=aiflow` / `--cov-branch` 拒绝断言 |
| `tests/unit/test_check_coverage.py` | 适配单域 `("core", "src/aiflow")` 并完整保留 `< 85%`、`84.9999999`、`nan`/`inf`、嵌套未导入源码、非法 SHA、路径越界与 `diff-cover` 非零退出码单测 |
| `tests/integration/test_coverage_gates.py` | 适配单域 `core` 真实 Git diff 与分支覆盖率门禁，保留未导入文件、隐藏文件 `.unexecuted.py` / `.hidden/unexecuted.py`、纯文档 diff 等集成测试 |
| `tests/integration/test_github_workflow.py` | 断言工作流使用 `--cov=aiflow --cov-branch` 且不包含 `--cov=tools/analysis` |
| `tests/integration/test_acceptance_traceability.py` | 同步 `quickstart.md` 重放命令与 `coverage-core.xml` 追踪断言 |

## 语义变更

- **单核心域覆盖率与静态检查收敛**：`src/aiflow`（`core` 域）继续强制 `>= 85%` 全量分支覆盖率与 `>= 90%` diff coverage 及 strict `mypy src`；退场外围 `tools/analysis` 不影响任何 `src/aiflow` 运行时行为、Schema 或授权规则。
- **不降低门禁强度**：`V0 <= V1 <= V2` 前缀约束、`3000s` budget、`policy_version: "2.6.0"`、`.ai/policy/{hard-rules,permissions,routing}.yaml` 与 `AGENTS.md` 均完整保留。
- **拆包边界（`AGENTS.md` 规则 8）**：独立的退役运营说明归档（`docs/operations/*.md` -> `docs/archive/operations/`）与历史任务关闭记录拆入紧随其后的无代码归档/收尾 PR，确保本次治理变更范围清晰单一。

## 风险

| 风险 | 影响 | 缓解措施 |
| :--- | :--- | :--- |
| 删除 18 个分析测试后影响 `src/aiflow` 分支覆盖率 | 核心域总覆盖率低于 85% | 完整 V1 验证实测 `src/aiflow` 仍为 **`90%`**（`>= 85%` 门禁） |
| 历史文档中仍存在旧链接未在本 PR 一并移动 | 文档链接测试回归 | 活跃入口链接（`README.md` / `AGENTS.md` / `SKILL.md`）当前保持存在且全量通过，相关分析文档归档在紧随 PR 完成 |
| `verification.py` 或 `verification-levels.yaml` 契约漏改 | `verify` 或 `test_policy`/`test_templates_and_policy` 失败 | 定向契约测试、模板策略测试、工作流测试与完整原生 V1 验证全部一次通过 |

## 证据

在当前 `subject_commit`（`e112514570fff25f45003ad628eb69a872b33b27`）及新 `policy_sha256`（`72baefa4710edfc7ba10dc3de6b751d93c69226bab86222985f7b5009f11a50e`）绑定之后，完成一次完整原生 `V1` 验证：

- 复现命令：`python -m aiflow verify TASK-0156 --actor verifier`（日志目录 `.ai/tasks/TASK-0156/logs/run-20261116T145033747864Z`）
- 已验证结果：`conclusion: passed`（退出码 `0`），任务状态迁移至 `WAITING_FOR_FINAL_REVIEW`
- 10 项原生 V1 门禁结果：
  - `contract`、`scope`、`ruff_check`、`ruff_format_check`、`smoke`、`mypy`（`src` 51 文件 0 issues）：全部 `passed`
  - `unit_tests` / `regression_tests` / `coverage_xml`：**`4,742 passed, 9 skipped in 2483.12s`**（9 项 skip 为固定 Node/POSIX 环境测试）
  - `core` 总分支覆盖率：**`90%`**（`13,786` 语句未覆盖 `1,074`，`5,548` 分支部分 `764`，`>= 85%` 门禁）
  - `diff_coverage`（vs `a376ad4c94b6608e9a2a492f3f870e456be2618e`）：`core` 域新增可执行 diff 为 0 行（`verification.py` 仅移除列表元素，并由 `test_verification_plan.py` 与 `test_policy.py` 直接测试），退出码 `0`
- 未验证场景：当前分支尚未推送至远端 GitHub，未触发远端 Ubuntu `ai-quality-gate`（需在 `code` 批准及 `Gate` 通过后执行）。

## 审核问题

1. **核心与 CI 门禁收敛完整性**：`pyproject.toml`、`.github/workflows/ai-quality-gate.yml`、`tools/ci/check_coverage.py`、`src/aiflow/verification.py`、`.ai/policy/verification-levels.yaml` 与 `docs/operations/quickstart.md` 是否已完整移除 `tools/analysis` 依赖，且 `>= 85%` 总分支覆盖率与 `>= 90%` diff coverage 门禁未有任何弱化？
2. **耦合测试改编有效性**：更新后的 `test_check_coverage.py` 与 `test_coverage_gates.py` 是否仍在单核心域下真实验证了 `< 85%` 总覆盖率失败、`< 90%` diff coverage 失败、隐藏文件/未导入嵌套文件检出、无分支数据拒绝及防路径逃逸约束？
3. **范围与政策绑定合规性**：`allowed_scope`、`subject_commit`（`e112514570fff25f45003ad628eb69a872b33b27`）、`policy_sha256`（`72baefa4710edfc7ba10dc3de6b751d93c69226bab86222985f7b5009f11a50e`）及授权文件未改动是否均合规，且仓库内已无残留的活跃 `tools/analysis` 引用或本机绝对路径/敏感信息？

## 推荐结论

APPROVE
