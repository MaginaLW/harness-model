# Review Package · TASK-0190

## 审核目标

对 `TASK-0190`（分支 `codex/governance-surface-and-tools-mypy-v2`，基线 `ae5dc1aaaf80875efff96ee7610a1ca4c939bdd4`，实现提交 `bb21d3bc0344bf766d39be9597c8a9b8d898196d`）进行独立实现审核（`REV-0003` / `--stage implementation`）：确认改动严格限定于已批准的 7 个文件与 `.ai/tasks/TASK-0190/**`（不含 `logs/`）、4 份 Policy 文件保持 `policy_version: "2.6.0"` 不变、`tests/integration/test_acceptance_traceability.py` 未触及、`mypy` 覆盖 `src` 与 `tools` 全部 57 个源文件零报错，且 V1 全套 10 项验证原生通过。

## 背景

依据项目所有者于 2026-11-24 直接批准的 B1 与 B2 治理加固范围，本任务在 `BASE_B2`（`ae5dc1aaaf80875efff96ee7610a1ca4c939bdd4`）上完成以下工作：
1. **B1**：将 `tools/` 纳入严格 `mypy` 检查配置，并把 V1/V2 的 `mypy` 命令统一为直接读取 `pyproject.toml` 的 `["{python}", -m, mypy]`；
2. **B2**：将 `setup.py`、`MANIFEST.in`、`tools/hooks/**` 纳入 `HARD-REVIEW-GOVERNANCE-SURFACE` 规则及 `AGENTS.md` 升级清单，并补充单元测试与集成测试；
3. 按 `spec.md` 与 `docs/operations/low-intervention.md` 完成 `policy_changed` 自失效升级、解决、同步、重分类、冻结、`REV-0002`（`APPROVE`）及新 Policy 下的条件式预授权 `spec` 批准与正式 V1 `verify`。

## 代码地图

仅修改以下 7 个非账本文件（`git diff ae5dc1aaaf80875efff96ee7610a1ca4c939bdd4..bb21d3bc0344bf766d39be9597c8a9b8d898196d`）：
- `pyproject.toml`（`[tool.mypy]`）：`files = ["src", "tools"]`，新增 `explicit_package_bases = true` 与 `namespace_packages = true`。
- `.ai/policy/verification-levels.yaml`：V1 与 V2 的 `mypy` 检查 `command` 从 `["{python}", -m, mypy, src]` 更新为 `["{python}", -m, mypy]`；`policy_version: "2.6.0"` 保持不变。
- `.ai/policy/hard-rules.yaml`：`HARD-REVIEW-GOVERNANCE-SURFACE` 的 `conditions[0].value` 新增 `tools/hooks/**`、`setup.py`、`MANIFEST.in`；`policy_version: "2.6.0"` 保持不变。
- `AGENTS.md`：「当前治理模式」升级清单句补充 `tools/hooks/**`、`setup.py`、`MANIFEST.in`。
- `tests/unit/test_policy.py`：更新 V1/V2 `mypy` 命令断言，并新增 `test_governance_surface_includes_packaging_and_hook_paths`。
- `tests/integration/test_github_workflow.py`：新增参数化集成测试 `test_router_requires_task_for_packaging_and_hook_governance_paths`。
- `tests/integration/test_templates_and_policy.py`：新增参数化集成测试 `test_maintenance_route_requires_task_for_governance_surface_additions`。

治理账本文件位于 `.ai/tasks/TASK-0190/`（`task.yaml`、`spec.md`、`classification.json`、`approvals.json`、`events.jsonl`、`policy-changed-resolution.md`、`evidence.json`、`review-package.md`、`reviews/`、`review-contexts/`；`logs/` 不纳入版本库）。

## 语义变更

- **静态类型门禁范围扩展**：`mypy` 默认配置与 V1/V2 验证检查现同步覆盖 `src` 与 `tools`（共 57 个源文件），无新增配置开关或回退路径；`explicit_package_bases = true` 与 `namespace_packages = true` 仅用于消除无 `__init__.py` 工具子包的模块基路径歧义。
- **治理面路由加固**：在维护模式与常规 PR 路由检查下，修改 `setup.py`、`MANIFEST.in` 或 `tools/hooks/**` 均命中 `HARD-REVIEW-GOVERNANCE-SURFACE` 并要求对应实现 task，不再被 `bootstrap-mode.yaml` 的 task-free 例外放行。
- **既有契约保持**：4 个 `.ai/policy/*.yaml` 文件均维持 `policy_version: "2.6.0"`；`tests/integration/test_acceptance_traceability.py`（含第 289 行）未作任何修改；无业务源码改动与冗余抽象抽取。

## 风险

- **Policy 自失效风险（已缓解）**：修改 `.ai/policy/verification-levels.yaml` 与 `.ai/policy/hard-rules.yaml` 使 `policy_sha256` 从 `72baefa4710edfc7ba10dc3de6b751d93c69226bab86222985f7b5009f11a50e` 变为 `d664125e3ff172ab4e9ffb0b142eaa21f96953c6e067618dc4434f3ca4b039ff`。已通过 `escalate(policy_changed)` -> `sync` -> `resolve` -> `classify` -> `freeze` -> `REV-0002(APPROVE)` -> 条件式预授权重签 `spec` 批准完整闭环。
- **跨平台工具链差异（低风险）**：本地全量验证在 Windows 原生环境运行，9 个仅限 POSIX 或需外部 `AIFLOW_NODE_TEST_MATERIALS` 树的测试按既定条件跳过；Linux CI `ai-quality-gate` 将在开 PR 后执行交叉验证。

## 证据

1. **已验证结果（正式 V1 验证）**：`uv run --locked --extra dev python -m aiflow verify TASK-0190 --actor author-track-b2`（已记录于 `.ai/tasks/TASK-0190/evidence.json`，绑定 `subject_commit: bb21d3bc0344bf766d39be9597c8a9b8d898196d`、`policy_sha256: d664125e3ff172ab4e9ffb0b142eaa21f96953c6e067618dc4434f3ca4b039ff`）：
   - 全部 10/10 项 V1 检查 `passed`（`contract`、`scope`、`ruff_check`、`ruff_format_check`、`smoke`、`unit_tests`、`regression_tests`、`mypy`、`coverage_xml`、`diff_coverage`）。
   - `pytest --cov=aiflow --cov-branch`：`4950 passed, 9 skipped`（`core` 总覆盖率 `90%` >= `85%`；本任务无 `src/` Python 代码变更，diff coverage 检查通过）。
   - `mypy`：`Success: no issues found in 57 source files`（覆盖 `src` + `tools`）。
2. **局部快速复现命令**：
   - `uv run --locked --extra dev python -m mypy`
   - `uv run --locked --extra dev python -m ruff check .`
   - `uv run --locked --extra dev python -m ruff format --check .`
   - `uv run --locked --extra dev python -m pytest tests/unit/test_policy.py tests/integration/test_github_workflow.py tests/integration/test_templates_and_policy.py -q`（80 passed）
3. **未验证场景**：远端 GitHub Actions `ai-quality-gate` 工作流（将在提交审核并开 PR 后由 CI 执行）。

## 审核问题

请独立审核者明确裁决以下问题：
1. `git diff ae5dc1aaaf80875efff96ee7610a1ca4c939bdd4..bb21d3bc0344bf766d39be9597c8a9b8d898196d`（排除 `.ai/tasks/`）是否严格只包含上述 7 个已批准文件，且 `policy_version: "2.6.0"` 与 `test_acceptance_traceability.py:289` 均保持原样？
2. `evidence.json` 是否完整覆盖当前 `subject_commit` 与新 `policy_sha256`，10/10 V1 检查是否全部通过（含 `mypy` 检查 `src` + `tools` 57 个文件与 `core` 覆盖率 `90%` >= `85%`）？
3. 账本提交是否完整、追加式且不包含 `.ai/tasks/TASK-0190/logs/`？

### 交付边界五项自检

1. **目标与关键假设是否清楚**：是。任务目标明确为将 `tools/` 纳入严格 `mypy` 门禁并将 `setup.py`、`MANIFEST.in`、`tools/hooks/**` 纳入治理面；关键假设为 4 份 Policy 文件保持 `policy_version: "2.6.0"` 不变及新测试精确覆盖维护模式与 PR 路由行为，已全部核实。
2. **是否已核实语言标准库与代码库既有复用机会**：是。直接复用既有 `pyproject.toml` `[tool.mypy]` 配置、`.ai/policy/*.yaml` 规则集与 `tests/integration/test_github_workflow.py` 中的 `_repo`/`_active_base`/`_git`/`main` 测试辅助，未重复造轮子。
3. **各修改模块是否存在更简单的直接实现**：无。配置、规则与测试改动均为最小直接表达。
4. **新增抽象、分支或配置项是否均有当前明确依据**：是。未新增任何抽象或业务分支；`explicit_package_bases = true` 与 `namespace_packages = true` 为 `tools/` 纳入 `mypy` 所需的直接配置。
5. **是否只触及了任务范围边界内的文件**：是。非账本改动仅含 spec 批准的 7 个文件，账本改动仅在 `.ai/tasks/TASK-0190/**` 内且不提交 `logs/`（`S / Q / U / H` 核验：本次过程无人工打断，`S=0, Q=0, U=0, H=0`）。

## 推荐结论

**APPROVE** — 7 个文件实现与测试严格对齐所有者批准的 B1/B2 范围，`policy_changed` 二次治理闭环完整，V1 全部 10 项检查原生通过（`mypy` 57 个文件 0 错误、4950 测试通过、核心覆盖率 `90%`），满足 `REV-0003` 实现审核通过条件。
