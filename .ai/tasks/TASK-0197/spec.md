# TASK-0197 · `0.3.1` 里程碑版本与发布前收口准备

## 目标

在基线 `e8f79e176c36b6e4c040958c918ae8d655c6c045`（分支 `codex/release-031-prep`）上完成 `0.3.1` 里程碑版本与发布前收口准备：将源码包版本及锁定元数据由 `0.3.0` 提升至 `0.3.1`（仅变更 `aiflow` 自身版本，不升级第三方依赖），同步更新对应版本断言测试、`CHANGELOG.md`（将 `Unreleased` 中的 `TASK-0196` 交付与本次 `0.3.1` 准备收口至 `## 0.3.1 - 2026-11-27`）、`README.md` 及 `docs/operations/maintenance-status.md`。本任务仅完成仓库内发布准备，**不创建 `v0.3.1` Git tag 或 GitHub Release**。

## 范围

仅允许修改以下 10 个路径（以及 `.ai/tasks/TASK-0197/**` 治理账本，不含 `logs/`）：
- `pyproject.toml`：`[project] version` 由 `"0.3.0"` 升至 `"0.3.1"`。
- `uv.lock`：通过 `uv lock --offline` 仅更新 `aiflow` 包版本号由 `0.3.0` 至 `0.3.1`，不更新任何第三方依赖版本。
- `src/aiflow/__init__.py`：`__version__` 由 `"0.3.0"` 升至 `"0.3.1"`。
- `src/aiflow/resource_bundle.py`：`CLI_VERSION` 由 `"0.3.0"` 升至 `"0.3.1"`。
- `tests/unit/test_cli.py`：将 `--version` 与 `importlib.metadata.version("aiflow")` 断言由 `"0.3.0"` 更新为 `"0.3.1"`。
- `tests/unit/test_resource_bundle.py`：将 `compatible_cli_versions` 及构造夹具版本断言由 `"0.3.0"` 更新为 `"0.3.1"`。
- `tests/integration/test_resource_bundle_distribution.py`：将构造包输出与暂存/元数据目录名断言（`aiflow-0.3.0*`）更新为 `aiflow-0.3.1*`。
- `CHANGELOG.md`：更新基线说明中的 `0.3.1`；保留空 `## Unreleased` 小节；新增 `## 0.3.1 - 2026-11-27`，将 `TASK-0196`（PR #227 / #228）移入 `### Added`，并在 `### Changed` 中记录 `TASK-0197` 仓库内 `0.3.1` 发布准备（明确标注尚未创建 `v0.3.1` tag 或 GitHub Release）。
- `README.md`：将「当前状态」中的源码包版本由 `0.3.0` 更新为 `0.3.1`（保留历史 `[v0.3.0 Release]` 链接并注明已完成仓库内 `0.3.1` 准备、`v0.3.1` tag 与 GitHub Release 待项目所有者决定）。
- `docs/operations/maintenance-status.md`：将 `main` 基线指针更新至 `e8f79e17`（含 PR #231 文档基线同步），并补充 `TASK-0197` `0.3.1` 仓库内发布准备状态（明确标注尚未创建 `v0.3.1` tag 或 GitHub Release），不含任何本机绝对路径或用户名。

已有能力复用与边界说明：
- 复用既有 `pyproject.toml`、`uv lock --offline`、`resource_bundle.CLI_VERSION` 与打包分发测试，不新增额外版本读取脚本或发布工作流。

## 非目标

- **不创建 `v0.3.1` tag，不创建或发布 GitHub Release，不向外部 package registry 发布包**。
- 不修改 `.ai/policy/*`、`.ai/schemas/*`、`.github/workflows/*`、除 `__init__.py` 与 `resource_bundle.py` 外的业务源码，不修改 `uv.lock` 中任何第三方包版本。

## 验收条件

1. `git diff main..HEAD -- uv.lock` 仅反映 `aiflow` 自身版本 `0.3.0 -> 0.3.1` 变更。
2. `aiflow --version` 输出 `aiflow 0.3.1`，`tests/unit/test_cli.py`、`tests/unit/test_resource_bundle.py`、`tests/integration/test_resource_bundle_distribution.py`、`tests/integration/test_agent_entry_files.py` 与 `tests/integration/test_repository_hygiene.py` 全部通过。
3. `ruff check .`、`ruff format --check .` 与 `mypy` 零报错通过。
4. 正式运行 `aiflow verify TASK-0197 --actor verifier-v1`，V1 全部 10 项检查原生通过（`core` 总分支覆盖率 >= 85%、diff coverage >= 90%）。
5. 独立设计与实现审核均为 `APPROVE`，`aiflow gate TASK-0197` 通过，PR 合入 `main` 且 Ubuntu `ai-quality-gate` 全绿通过。

## 禁止动作

- **严禁创建 `v0.3.1` tag 或 GitHub Release**，严禁外部发布或修改 `.ai/policy/*` / `.ai/schemas/*` / `.github/workflows/*`。
- 严禁升级或变更 `uv.lock` 中的第三方依赖，严禁提交 `.ai/tasks/TASK-0197/logs/`，严禁在受跟踪文件或提交中写入本机绝对路径、主机名或用户名。
- 禁止跳过独立审核、自审或强推。

## 错误行为

- 若 `uv lock --offline` 意外改动第三方依赖、或分发打包测试/版本一致性测试失败、或分类超出预期 `REVIEW / V1`，立即停止并修正或按 `aiflow escalate` 规则处理。

## 回滚

所有改动均位于独立分支 `codex/release-031-prep`；合入 `main` 前可直接丢弃分支，合入后可通过标准反向 PR 回滚，无需删除或回滚远端 tag/Release。
