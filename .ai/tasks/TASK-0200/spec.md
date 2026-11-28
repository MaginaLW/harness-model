# TASK-0200 · `0.3.2` 里程碑版本与发布前收口准备

## 目标

在基线 `fbf3f1a8437f2beff0d39e6bf6380313e504f6d1`（分支 `codex/release-032-prep`）上完成 `0.3.2` 里程碑版本与发布前收口准备：将源码包版本及锁定元数据由 `0.3.1` 提升至 `0.3.2`（仅变更 `aiflow` 自身版本，不升级任何第三方依赖；`POLICY_VERSION` 保持 `2.6.0`、`BUNDLE_VERSION` 保持 `1.0`），同步更新对应版本断言测试、`CHANGELOG.md`（将 `## Unreleased` 中的 PR #235、`TASK-0198`、Batch 1 PR #239、Batch 2 `TASK-0199` PR #240/#241 与本次 `0.3.2` 准备收口至 `## 0.3.2 - 2026-11-28`）、`README.md` 及 `docs/operations/maintenance-status.md`。本任务仅完成仓库内发布准备，**不创建 `v0.3.2` Git tag 或 GitHub Release**。

## 范围

仅允许修改以下 10 个路径（以及 `.ai/tasks/TASK-0200/**` 治理账本，不含 `logs/`）：
- `pyproject.toml`：`[project] version` 由 `"0.3.1"` 升至 `"0.3.2"`。
- `uv.lock`：通过 `uv lock` 仅更新 `aiflow` 包版本号由 `"0.3.1"` 至 `"0.3.2"`，不更新任何第三方依赖版本或解析哈希。
- `src/aiflow/__init__.py`：`__version__` 由 `"0.3.1"` 升至 `"0.3.2"`。
- `src/aiflow/resource_bundle.py`：`CLI_VERSION` 由 `"0.3.1"` 升至 `"0.3.2"`（保持 `POLICY_VERSION = "2.6.0"` 与 `BUNDLE_VERSION = "1.0"` 不变）。
- `tests/unit/test_cli.py`：将第 30、35 行的 `--version` 与 `importlib.metadata.version("aiflow")` 断言由 `"0.3.1"` 更新为 `"0.3.2"`。
- `tests/unit/test_resource_bundle.py`：将第 183、444、445 行的 `compatible_cli_versions` 及构造夹具版本断言由 `"0.3.1"` 更新为 `"0.3.2"`。
- `tests/integration/test_resource_bundle_distribution.py`：将第 1296、1320、1593、1879 行的构造包输出与暂存/元数据目录名断言（`aiflow-0.3.1*`）更新为 `aiflow-0.3.2*`。
- `CHANGELOG.md`：更新第 3 行基线说明纳入 `0.3.2`；保留空 `## Unreleased` 小节；新增 `## 0.3.2 - 2026-11-28`，将 PR #235、`TASK-0198`（PR #236 / #237）、Batch 1（PR #239）与 Batch 2 `TASK-0199`（PR #240 / #241）收口移入对应小节，并在 `### Changed` 中记录 `TASK-0200` 仓库内 `0.3.2` 发布准备（明确标注尚未创建 `v0.3.2` tag 或 GitHub Release）。
- `README.md`：更新第 14 行「当前状态」中的源码包版本由 `0.3.1` 更新为 `0.3.2`（保留历史 `[v0.3.1 Release]` 链接并注明已完成仓库内 `0.3.2` 准备、`v0.3.2` tag 与 GitHub Release 待收尾发布）。
- `docs/operations/maintenance-status.md`：将 `main` 基线指针更新至 `fbf3f1a8`（已合入 PR #204–PR #241），并补充 `PR #239` 与 `TASK-0200` `0.3.2` 仓库内发布准备状态（明确标注尚未创建 `v0.3.2` tag 或 GitHub Release），不含任何本机绝对路径或用户名。

已有能力复用与边界说明：
- 复用既有 `pyproject.toml`、`uv lock`、`resource_bundle.CLI_VERSION` 与打包分发测试，不新增额外版本读取脚本、配置项或发布工作流。

## 非目标

- **不在本任务 PR 中创建 `v0.3.2` tag，不创建或发布 GitHub Release，不向外部 package registry 发布包**。
- 不修改 `.ai/policy/*`、`.ai/schemas/*`、`.github/workflows/*`、除 `__init__.py` 与 `resource_bundle.py` 外的业务源码，不修改 `POLICY_VERSION`（`2.6.0`）或 `BUNDLE_VERSION`（`1.0`），不修改 `uv.lock` 中任何第三方包版本。

## 验收条件

1. `git diff origin/main..HEAD -- uv.lock` 仅反映 `aiflow` 自身版本 `0.3.1 -> 0.3.2` 变更（`+1/-1` 行），`uv lock --check` 退出 0。
2. `aiflow --version` 输出 `aiflow 0.3.2`，且 `tests/unit/test_resource_bundle.py`、`tests/integration/test_resource_bundle_distribution.py`、`tests/integration/test_external_python_verify.py`、`tests/unit/test_cli.py` 全部通过。
3. `ruff check .`、`ruff format --check .` 与 `mypy` 零报错通过。
4. 正式运行 `aiflow verify TASK-0200 --actor batch3-author`，V1 全部 10 项检查原生通过（`core` 总分支覆盖率 >= 85%、diff coverage >= 90%）。
5. 独立设计与实现审核均为 `APPROVE`，`aiflow gate TASK-0200 --format json` 返回 `"passed": true`，PR 合入 `main` 且 Ubuntu `ai-quality-gate` 全绿通过。

## 禁止动作

- **严禁在本任务实施过程中创建 `v0.3.2` tag 或 GitHub Release**，严禁外部发布或修改 `.ai/policy/*` / `.ai/schemas/*` / `.github/workflows/*`。
- 严禁升级或变更 `uv.lock` 中的第三方依赖，严禁提交 `.ai/tasks/TASK-0200/logs/`，严禁在受跟踪文件或提交中写入本机绝对路径、主机名或用户名。
- 禁止跳过独立审核、自审或强推。

## 错误行为

- 若 `uv lock` 意外改动第三方依赖、或分发打包测试/版本一致性测试失败、或分类超出预期 `REVIEW / V1`，立即停止并修正或按 `aiflow escalate` 规则处理。

## 回滚

所有改动均位于独立分支 `codex/release-032-prep`；合入 `main` 前可直接丢弃分支，合入后可通过标准反向 PR 回滚，无需删除或回滚远端 tag/Release。
