# Review Package · TASK-0192

## 审核目标

对 `TASK-0192`（分支 `codex/d21-cross-repo-python-verify`，基线 `f9420c095fd9648d878717bdf7e1f12a4f65a688`，实现提交 `83359313df1e84c8174087672d6dde1ae9901477`）进行独立实现审核（`REV-0002` / `--stage implementation`）：确认改动严格限定于批准的 6 个 D2.1 文件与 `.ai/tasks/TASK-0192/**`（不含 `logs/`），`.ai/policy/*` 与 `.ai/schemas/*` 零改动，原 `tools/ci/check_coverage.py` 兼容包装与 `>= 85%` 总分支覆盖率 / `>= 90%` 差异覆盖率门禁保持不变，且本机 V1 全套 10 项验证全部通过。

## 背景

在跨仓消费场景中，目标 Python Git 仓库通过安装 `aiflow` 包运行验证，不包含 `harness-model` 自身的 `tools/ci/check_coverage.py` 脚本或 `src/aiflow` 目录。为此本任务将可复用的分支与差异覆盖率检查内核抽离至 `src/aiflow/coverage_check.py`，保留 `tools/ci/check_coverage.py` 作为向后兼容的薄包装，并扩展 `src/aiflow/verification.py` 对 `PYTEST_CHECK_IDS`（`--cov=<pkg_or_path>`）与 `diff_coverage`（`-m aiflow.coverage_check --source ...`）的可移植解析与安全校验契约。首轮本地 V1 发现 `verification.py` 导入私有符号 `_validate_source_domain` 触发 `test_shared_imports_use_public_symbols` 失败，已按 REC-04 在 `83359313` 将其提升为公共符号 `validate_source_domain` 并重跑完整 V1 验证通过。

## 代码地图

仅修改/新增以下 6 个非账本文件（`git diff f9420c095fd9648d878717bdf7e1f12a4f65a688..83359313df1e84c8174087672d6dde1ae9901477`）：
- `src/aiflow/coverage_check.py`（新增）：`DEFAULT_DOMAINS = (("core", "src/aiflow"),)`、`validate_source_domain`、`check_coverage`（函数体内延迟导入 `Coverage`）与 CLI `main`（支持 `--run-dir`、`--base`、可选 `--source`，硬编码 `>= 85%` 总分支覆盖率与 `>= 90%` 差异覆盖率）。
- `tools/ci/check_coverage.py`（修改）：保留为薄包装，导出并兼容原 `DOMAINS`、`check_coverage(repository, run_dir, base)` 与 `main(argv)` 契约。
- `src/aiflow/verification.py`（修改）：`PYTEST_CHECK_IDS` 校验 `--cov=<target>` 匹配安全包名/相对路径模式并要求同级所有 pytest 检查共享同一 `--cov=` 目标；`diff_coverage` 同时支持历史 `tools/ci/check_coverage.py` 与可移植 `-m aiflow.coverage_check`（及成对 `--source` 参数，调用 `validate_source_domain` 校验）。
- `tests/unit/test_coverage_check.py`（新增）：覆盖 `validate_source_domain` 合法/非法路径、延迟导入、`--source` 去重/域校验、缺失 `.coverage`、无分支数据及通过/失败分支。
- `tests/unit/test_verification_plan.py`（修改）：补充可移植 `--cov=` 目标校验与跨检查一致性校验、可移植 `-m aiflow.coverage_check --source ...` 正反向测试及历史命令回归测试。
- `tests/integration/test_external_python_verify.py`（新增）：构建自包含外部 Python Git 临时仓库（无 `tools/ci/` 与 `aiflow` 源码），运行完整 `start -> facts -> classify -> freeze -> begin -> verify`（V0/V1）-> `gate` 端到端验证通过。

## 语义变更

- **可移植覆盖率执行入口**：`python -m aiflow.coverage_check` 成为可安装运行入口，默认检查 `("core", "src/aiflow")`，指定 `--source <rel_dir>` 时映射为受校验的仓内相对路径域；两项阈值（总分支 `>= 85%`、diff `>= 90%`）保持硬编码不可配置，且仅在执行 `check_coverage()` 时延迟导入 `coverage` 避免污染 `aiflow` 普通导入边界。
- **跨仓验证计划契约**：`verification.py` 允许任意符合安全标识模式的 `--cov=<target>`（仍强制同级全部 `PYTEST_CHECK_IDS` 使用完全一致的 `--cov=<target>` 以保证单次共享 pytest 去重执行），同时保持 `smoke`（`-m aiflow --help`）、`ENVIRONMENT`（`COVERAGE_FILE`）、超时（`3000s`/`120s`）与既有 `tools/ci/check_coverage.py` 精确命令兼容性不变。
- **边界防护**：`validate_source_domain` 拒绝空串、绝对路径、前后 `/`、`.`/`..`、反斜杠、冒号、空白/控制字符，并在执行期再次确认解析路径严格位于 `repository` 内，防止路径逃逸。

## 风险

- **延迟导入与测试隔离风险（已验证缓解）**：`test_coverage_check.py` 与 `test_import_boundaries.py` 实测确认普通导入 `aiflow.coverage_check` 不加载 `coverage`、不加载可选 `node_*`/`installed_*` 模块，且核心模块间无跨模块私有符号导入。
- **跨平台 CI 差异（低风险）**：本地 V1 在 Windows 原生环境运行，9 项既有条件跳过用例（6 项 `AIFLOW_NODE_TEST_MATERIALS` + 3 项 POSIX 专属用例）按既定规则跳过；远端 Ubuntu `ai-quality-gate` 将在开 PR 后交叉验证。

## 证据

1. **已验证结果（REC-04 重试后正式 V1 验证全量通过）**：`uv run --locked python -m aiflow verify TASK-0192 --actor verifier-v1`（已记录于 `.ai/tasks/TASK-0192/evidence.json`，绑定 `subject_commit: 83359313df1e84c8174087672d6dde1ae9901477`）：
   - 全部 10/10 项 V1 检查 `passed`（`contract`、`scope`、`ruff_check`、`ruff_format_check`、`smoke`、`unit_tests`、`regression_tests`、`mypy`、`coverage_xml`、`diff_coverage`）。
   - `pytest --cov=aiflow --cov-branch`：`5256 passed, 9 skipped in 1415.12s`（`core` 总分支覆盖率 `90%` >= `85%`；`src/aiflow/coverage_check.py` 分支覆盖率 `97%`；`src/aiflow/verification.py` 分支覆盖率 `92%`）。
   - `diff_coverage`：Diff coverage **98%** >= `90%`（`130` 行、`2` 行未覆盖；`coverage_check.py` `98.0%`、`verification.py` `100%`）。
   - `mypy`：通过；`ruff check .` 与 `ruff format --check .`：通过。
   - 历史失败运行 `logs/run-20261125T170801685052Z/`（首轮 `test_shared_imports_use_public_symbols`）按 REC-04 保留在账本事件与本机日志目录中未删改。
2. **未验证场景**：远端 GitHub Actions Ubuntu `ai-quality-gate` 工作流（待审核批准与 Gate 通过后在 PR 阶段执行）。

## 审核问题

请独立审核者明确裁决以下问题：
1. `git diff f9420c095fd9648d878717bdf7e1f12a4f65a688..83359313df1e84c8174087672d6dde1ae9901477` 是否严格仅修改/新增 spec 批准的 6 个 D2.1 文件，且 `.ai/policy/*`、`.ai/schemas/*`、`pyproject.toml`、`cli.py`、`initialization*.py` 均未触及？
2. `coverage_check.py` 与 `verification.py` 是否在边界处严格拒绝不安全 `--source` / `--cov=` / 跨检查目标不一致，并硬编码保持 `>= 85%` 总分支覆盖率与 `>= 90%` diff coverage 门槛？
3. `evidence.json`（10/10 `passed`，`5256 passed, 9 skipped`，`90%` core、`98%` diff coverage）与 `.ai/tasks/TASK-0192/` 账本记录是否一致且未含本机绝对路径、用户名或 `logs/` 目录入库？

### 交付边界五项自检

1. **目标与关键假设是否清楚**：是。目标明确为使外部 Python Git 仓库在不复制 `tools/ci/` 或 `aiflow` 源码的前提下执行 V0/V1 验证与 Gate；关键假设为 `aiflow.coverage_check` 可被已安装环境以 `-m` 调用且 `verification.py` 维持同级共享 pytest 去重。
2. **是否已核实语言标准库与代码库既有复用机会**：是。直接将 `tools/ci/check_coverage.py` 既有 `coverage` + `diff_cover` 检查逻辑抽离至 `src/aiflow/coverage_check.py` 并复用现有包装测试接口，未重复造轮子。
3. **各修改模块是否存在更简单的直接实现**：无。薄包装 + 单一公共校验函数 `validate_source_domain` + `verification.py` 列表校验已是最小直接实现。
4. **新增抽象、分支或配置项是否均有当前明确依据**：是。未新增降阈值开关、配置项或备用执行路径；新增 `--source` 与 `--cov=` 模式校验均直接对应外部仓包路径验证需求。
5. **是否只触及了任务范围边界内的文件**：是。业务变更严格限定于 6 个批准文件，账本变更仅位于 `.ai/tasks/TASK-0192/**` 且排除 `logs/`。

## 推荐结论

**APPROVE** — 6 个文件实现与测试严格对齐冻结规格与边界约束，`validate_source_domain` 已按 REC-04 修正并通过完整 V1 全套 10 项检查（`5256 passed, 9 skipped`、core `90%`、diff `98%`），满足独立实现审核通过条件。
