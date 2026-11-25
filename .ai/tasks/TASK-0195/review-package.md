# Review Package · TASK-0195

## 审核目标

对 `TASK-0195`（分支 `codex/d32-release-030-prep`，基线 `559a066352305e4e2baebc2104e530c9957e07a7`，实现提交 `9cd96b49c3be8f296788acc32e830501afc5ebb9`）进行独立实现审核（`REV-0002` / `--stage implementation`）：确认改动严格限定于批准的 10 个 D3.2 文件与 `.ai/tasks/TASK-0195/**`（不含 `logs/`），`uv.lock` 仅将 `aiflow` 版本由 `0.2.0` 升至 `0.3.0`（无任何第三方依赖变化），未创建 `v0.3.0` tag 或 GitHub Release，`.ai/policy/*`、`.ai/schemas/*` 与 `.github/workflows/*` 零改动，且本机 V1 全套 10 项验证全部通过。

## 背景

在完成 Batch 3 测试加速（PR #214）以及 D2.1（PR #216/#217）、D2.2（PR #218/#219）和 D4（PR #220/#221）交付后，本任务执行仓库内 `0.3.0` 里程碑收口准备：统一升级源码包元数据、锁文件、资源包兼容 CLI 版本及对应测试断言至 `0.3.0`，并将 `CHANGELOG.md` 的 `Unreleased` 项归集为 `0.3.0 - 2026-11-26`，同时同步 `README.md` 与 `docs/operations/maintenance-status.md` 至最新主线基线 `559a0663`。

## 代码地图

仅修改以下 10 个非账本文件（`git diff 559a066352305e4e2baebc2104e530c9957e07a7..9cd96b49c3be8f296788acc32e830501afc5ebb9`）：
- `pyproject.toml`：`[project] version` 由 `"0.2.0"` 更新为 `"0.3.0"`。
- `uv.lock`：通过 `uv lock --offline` 仅更新 `aiflow` 包 `version = "0.2.0" -> "0.3.0"`（`2 +-`）。
- `src/aiflow/__init__.py`：`__version__ = "0.3.0"`。
- `src/aiflow/resource_bundle.py`：`CLI_VERSION = "0.3.0"`。
- `tests/unit/test_cli.py`：`--version` 与 `importlib.metadata.version("aiflow")` 断言更新为 `"0.3.0"`。
- `tests/unit/test_resource_bundle.py`：`compatible_cli_versions` 与夹具版本断言更新为 `"0.3.0"`。
- `tests/integration/test_resource_bundle_distribution.py`：wheel/sdist 输出文件名与暂存/dist-info 路径断言更新为 `aiflow-0.3.0*`。
- `CHANGELOG.md`：更新版本说明，将 `## Unreleased` 归集并补充 D2.1 / D2.2 / D4 / D3.2 至 `## 0.3.0 - 2026-11-26`，保留空 `## Unreleased`。
- `README.md`：更新当前源码包版本为 `0.3.0` 并简要补充已交付的跨仓覆盖率、POSIX 初始化与只读 `aiflow advise` 能力。
- `docs/operations/maintenance-status.md`：更新 `main` 基线指针至 `559a0663`（`PR #204`–`PR #221`），记录 `TASK-0192`～`TASK-0194` 已合入指标及 `TASK-0195` 发布准备状态（明确未打 `v0.3.0` tag / GitHub Release）。

## 语义变更

- **统一版本基准 `0.3.0`**：源码 `__version__`、构建元数据 `pyproject.toml`、`uv.lock` 及资源包 `CLI_VERSION` 保持单一一致的 `0.3.0`；`aiflow --version` 输出 `aiflow 0.3.0`。
- **锁文件零第三方漂移**：`uv lock --offline` 仅更改 `aiflow` 自身条目 1 行版本号，未修改任何第三方包版本或解析哈希。
- **发布边界守卫**：本任务仅限仓库内发布准备，不创建 `v0.3.0` Git tag、不创建 GitHub Release、不向外部包仓库发布。

## 风险

- **跨平台 CI 差异（低风险）**：本地 V1 在 Windows 原生环境运行，9 项既有平台条件测试按既定条件跳过；`test_cli.py`、`test_resource_bundle.py`、`test_resource_bundle_distribution.py`、`test_agent_entry_files.py` 与 `test_repository_hygiene.py` 均通过。远端 Ubuntu `ai-quality-gate` 将在开 PR 后执行交叉验证。

## 证据

1. **已验证结果（正式 V1 全量通过）**：`uv run --locked python -m aiflow verify TASK-0195 --actor verifier-v1`（记录于 `.ai/tasks/TASK-0195/evidence.json`，绑定 `subject_commit: 9cd96b49c3be8f296788acc32e830501afc5ebb9`）：
   - 全部 10/10 项 V1 检查 `passed`（`contract`、`scope`、`ruff_check`、`ruff_format_check`、`smoke`、`unit_tests`、`regression_tests`、`mypy`、`coverage_xml`、`diff_coverage`）。
   - `pytest --cov=aiflow --cov-branch`：`5322 passed, 9 skipped in 1574.98s`（`core` 总分支覆盖率 `91%` >= `85%`）。
   - `diff_coverage`：Diff coverage **100%** >= `90%`（`2/2` 行，`__init__.py` `100%`、`resource_bundle.py` `100%`）。
   - `mypy`、`ruff check .`、`ruff format --check .`：全部通过。
2. **未验证场景**：远端 GitHub Actions Ubuntu `ai-quality-gate` 工作流（待审核批准与 Gate 通过后在 PR 阶段执行）。

## 审核问题

请独立审核者明确裁决以下问题：
1. `git diff 559a066352305e4e2baebc2104e530c9957e07a7..9cd96b49c3be8f296788acc32e830501afc5ebb9` 是否严格仅触及批准的 10 个文件，且 `uv.lock` 仅更改 `aiflow` 版本 `0.2.0 -> 0.3.0`（无任何第三方依赖变化）？
2. 变更是否严格停留在仓库内 `0.3.0` 里程碑准备，未创建 `v0.3.0` tag 或 GitHub Release，且 `.ai/policy/*`、`.ai/schemas/*`、`.github/workflows/*` 均未改动？
3. `evidence.json`（10/10 `passed`，`5322 passed, 9 skipped`，`91%` core、`100%` diff coverage）与 `.ai/tasks/TASK-0195/` 账本记录是否一致且不含本机绝对路径、用户名或 `logs/` 目录？

### 交付边界五项自检

1. **目标与关键假设是否清楚**：是。目标明确为完成 `0.3.0` 仓库内里程碑版本、锁文件、测试与文档收口；关键假设为本任务不触发外部 tag/Release 发布。
2. **是否已核实语言标准库与代码库既有复用机会**：是。直接复用 `pyproject.toml`、`uv lock --offline`、`resource_bundle.CLI_VERSION` 与既有分发测试。
3. **各修改模块是否存在更简单的直接实现**：无。仅精确更新版本号、1 行锁文件版本、对应断言与里程碑文档（`+26/-16`）。
4. **新增抽象、分支或配置项是否均有当前明确依据**：是。未新增任何抽象、分支或配置项。
5. **是否只触及了任务范围边界内的文件**：是。业务与文档变更严格限定于 10 个批准文件，账本变更仅位于 `.ai/tasks/TASK-0195/**` 且排除 `logs/`。

## 推荐结论

**APPROVE** — 10 个文件严格对齐 `0.3.0` 里程碑准备边界，`uv.lock` 仅变更 `aiflow` 版本且无外部 tag/Release 操作，本地 V1 全套 10 项检查一次通过（`5322 passed, 9 skipped`、core `91%`、diff coverage `100%`），满足独立实现审核通过条件。
