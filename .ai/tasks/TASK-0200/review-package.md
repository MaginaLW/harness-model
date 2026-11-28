# Review Package · TASK-0200

## 审核目标

对 `TASK-0200`（分支 `codex/release-032-prep`，基线 `fbf3f1a8437f2beff0d39e6bf6380313e504f6d1`，实现提交 `4100bcb6f46d34bc4ab5e15ee4bd259cf166ac72`）进行独立实现审核（`REV-0002` / `--stage implementation`）：确认改动严格限定于批准的 10 个文件与 `.ai/tasks/TASK-0200/**`（不含 `logs/`），`uv.lock` 仅将 `aiflow` 版本由 `0.3.1` 升至 `0.3.2`（无任何第三方依赖变化），`POLICY_VERSION` 保持 `2.6.0`、`BUNDLE_VERSION` 保持 `1.0`，未在本 PR 中创建 `v0.3.2` tag 或 GitHub Release，`.ai/policy/*`、`.ai/schemas/*` 与 `.github/workflows/*` 零改动，且本机 V1 全套 10 项验证全部通过。

## 背景

继 `v0.3.1` Release 发布后，主线陆续合入内置资源包 wheel 外仓端到端验证与 CI 示例工作流（[PR #235](https://github.com/MaginaLW/harness-model/pull/235)）、严格只读任务列表 `aiflow list`（`TASK-0198`，[PR #236](https://github.com/MaginaLW/harness-model/pull/236)/[#237](https://github.com/MaginaLW/harness-model/pull/237)）、Plan A 收尾文档同步（[PR #238](https://github.com/MaginaLW/harness-model/pull/238)）、便携 CI/任务列表回归测试与接入文档加固（Batch 1，[PR #239](https://github.com/MaginaLW/harness-model/pull/239)）以及 CLI stdout JSON 跨平台 ASCII 转义修复（Batch 2 `TASK-0199`，[PR #240](https://github.com/MaginaLW/harness-model/pull/240)/[#241](https://github.com/MaginaLW/harness-model/pull/241)）。本任务在最新 `main` 基线 `fbf3f1a8` 上完成 `0.3.2` 里程碑仓库内发布准备：统一更新源码包元数据、锁文件、资源包兼容 CLI 版本、对应版本测试断言、`CHANGELOG.md`（收口 `## Unreleased` 与 PR #239 / `0.3.2` 准备至 `## 0.3.2 - 2026-11-28`）、`README.md` 与 `docs/operations/maintenance-status.md`。

## 代码地图

仅修改以下 10 个非账本文件（`git diff fbf3f1a8437f2beff0d39e6bf6380313e504f6d1..4100bcb6f46d34bc4ab5e15ee4bd259cf166ac72`，合计 `+26/-18`）：
- `pyproject.toml`：`[project] version` 由 `"0.3.1"` 更新为 `"0.3.2"`（`+1/-1`）。
- `uv.lock`：通过 `uv lock --offline` 仅更新 `aiflow` 包 `version = "0.3.1" -> "0.3.2"`（`+1/-1`），零第三方依赖变动。
- `src/aiflow/__init__.py`：`__version__ = "0.3.2"`（`+1/-1`）。
- `src/aiflow/resource_bundle.py`：`CLI_VERSION = "0.3.2"`（`+1/-1`；保持 `POLICY_VERSION = "2.6.0"` 与 `BUNDLE_VERSION = "1.0"` 不变）。
- `tests/unit/test_cli.py`：第 30、35 行 `--version` 与 `importlib.metadata.version("aiflow")` 断言更新为 `"0.3.2"`（`+2/-2`）。
- `tests/unit/test_resource_bundle.py`：第 183、444、445 行 `compatible_cli_versions` 与夹具版本断言更新为 `"0.3.2"`（`+3/-3`）。
- `tests/integration/test_resource_bundle_distribution.py`：第 1296、1320、1593、1879 行 wheel/sdist 输出文件名与暂存/dist-info 路径断言更新为 `aiflow-0.3.2*`（`+4/-4`）。
- `CHANGELOG.md`：第 3 行基线版本说明纳入 `0.3.2`，保留空 `## Unreleased` 小节，新增 `## 0.3.2 - 2026-11-28` 收口 `TASK-0200` 与 PR #239（`### Changed`）、PR #235 与 `TASK-0198` PR #236/#237（`### Added`）及 `TASK-0199` PR #240/#241（`### Fixed`），注明尚未创建 `v0.3.2` tag 或 GitHub Release（`+9/-2`）。
- `README.md`：第 14 行更新当前源码包版本为 `0.3.2`（保留历史 `[v0.3.1 Release]` 链接并注明 `v0.3.2` tag/Release 待项目所有者决定，`+1/-1`）。
- `docs/operations/maintenance-status.md`：第 17 行更新 `main` 基线指针至 `fbf3f1a8`（PR #204–PR #241），第 51–52 行补充 PR #241 收尾引用、PR #239 与 `TASK-0200` `0.3.2` 仓库内发布准备状态（明确未打 `v0.3.2` tag / GitHub Release，`+3/-2`）。

## 语义变更

- **统一版本基准 `0.3.2`**：源码 `__version__`、构建元数据 `pyproject.toml`、`uv.lock` 及资源包 `CLI_VERSION` 保持单一一致的 `0.3.2`；`aiflow --version` 输出 `aiflow 0.3.2`，`POLICY_VERSION`（`2.6.0`）与 `BUNDLE_VERSION`（`1.0`）保持不变。
- **锁文件零第三方漂移**：`uv lock --offline` 仅更改 `aiflow` 自身条目 1 行版本号，未修改任何第三方包版本或解析哈希。
- **发布边界守卫**：本 PR 仅限仓库内发布准备，不创建 `v0.3.2` Git tag、不创建 GitHub Release、不向外部包仓库发布。

## 风险

- **跨平台 CI 差异（低风险）**：本地 V1 在 Windows 原生环境运行，9 项既有平台/外置 Node 条件测试按既定条件跳过；`test_cli.py`、`test_resource_bundle.py`、`test_resource_bundle_distribution.py` 与 `test_external_python_verify.py` 均通过。远端 Ubuntu `ai-quality-gate` 将在审核与 Gate 通过、推送 PR 后执行交叉验证。

## 证据

1. **已验证结果（正式 V1 全量通过）**：`python -m aiflow verify TASK-0200 --actor batch3-author`（记录于 `.ai/tasks/TASK-0200/evidence.json`，绑定 `subject_commit: 4100bcb6f46d34bc4ab5e15ee4bd259cf166ac72`）：
   - 全部 10/10 项 V1 检查 `passed`（`contract`、`scope`、`ruff_check`、`ruff_format_check`、`smoke`、`unit_tests`、`regression_tests`、`mypy`、`coverage_xml`、`diff_coverage`）。
   - `pytest --cov=aiflow --cov-branch`：`5393 passed, 9 skipped in 1676.67s`（`core` 总分支覆盖率 `91%` >= `85%`）。
   - `diff_coverage`：Diff coverage **100%** >= `90%`（`2/2` 行，`src/aiflow/__init__.py` `100%`、`src/aiflow/resource_bundle.py` `100%`）。
   - 定向验证（`tests/unit/test_resource_bundle.py`、`tests/integration/test_resource_bundle_distribution.py`、`tests/integration/test_external_python_verify.py`、`tests/unit/test_cli.py`）：`147 passed in 132.99s`；`uv lock --check`、`ruff check .`、`ruff format --check .`、`mypy`（64 个源文件零错误）与 `git diff --check` 全部通过。
2. **未验证场景**：远端 GitHub Actions Ubuntu `ai-quality-gate` 工作流（待审核批准与 Gate 通过后在 PR 阶段执行）。

## 审核问题

请独立审核者明确裁决以下问题：
1. `git diff fbf3f1a8437f2beff0d39e6bf6380313e504f6d1..4100bcb6f46d34bc4ab5e15ee4bd259cf166ac72` 是否严格仅触及批准的 10 个文件，且 `uv.lock` 仅更改 `aiflow` 版本 `0.3.1 -> 0.3.2`（无任何第三方依赖变化）？
2. 变更是否严格停留在仓库内 `0.3.2` 里程碑准备，保持 `POLICY_VERSION="2.6.0"` 与 `BUNDLE_VERSION="1.0"` 不变，未创建 `v0.3.2` tag 或 GitHub Release，且 `.ai/policy/*`、`.ai/schemas/*`、`.github/workflows/*` 均未改动？
3. `evidence.json`（10/10 `passed`，`5393 passed, 9 skipped`，`91%` core、`100%` diff coverage）与 `.ai/tasks/TASK-0200/` 账本记录是否一致且不含本机绝对路径、用户名或 `logs/` 目录？

### 交付边界五项自检

1. **目标与关键假设是否清楚**：是。目标明确为完成 `0.3.2` 仓库内里程碑版本、锁文件、测试与文档收口；关键假设为本任务不触发外部 tag/Release 发布。
2. **是否已核实语言标准库与代码库既有复用机会**：是。直接复用 `pyproject.toml`、`uv lock`、`resource_bundle.CLI_VERSION` 与既有分发测试。
3. **各修改模块是否存在更简单的直接实现**：无。仅精确更新版本号、1 行锁文件版本、对应断言与里程碑文档（`+26/-18`）。
4. **新增抽象、分支或配置项是否均有当前明确依据**：是。未新增任何抽象、分支或配置项。
5. **是否只触及了任务范围边界内的文件**：是。业务与文档变更严格限定于 10 个批准文件，账本变更仅位于 `.ai/tasks/TASK-0200/**` 且排除 `logs/`。

## 推荐结论

**APPROVE** — 10 个文件严格对齐 `0.3.2` 里程碑准备边界，`uv.lock` 仅变更 `aiflow` 版本且无外部 tag/Release 操作，本地 V1 全套 10 项检查一次通过（`5393 passed, 9 skipped`、core `91%`、diff coverage `100%`），满足独立实现审核通过条件。
