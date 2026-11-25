# TASK-0195 · `0.3.0` 里程碑版本与发布收口准备（D3.2）

## 目标

在基线 `559a066352305e4e2baebc2104e530c9957e07a7`（分支 `codex/d32-release-030-prep`）上完成 `0.3.0` 里程碑版本与发布前收口准备（D3.2）：将源码包版本及锁定元数据由 `0.2.0` 提升至 `0.3.0`（仅变更 `aiflow` 自身版本，不升级第三方依赖），同步更新对应版本断言测试、`CHANGELOG.md`（归集 `Unreleased` 与 D2.1 / D2.2 / D4 / D3.2 交付至 `0.3.0`）、`README.md` 及 `docs/operations/maintenance-status.md`。本任务仅完成仓库内发布准备，**不创建 `v0.3.0` Git tag 或 GitHub Release**。

## 范围

仅允许修改以下 10 个路径（以及 `.ai/tasks/TASK-0195/**` 治理账本，不含 `logs/`）：
- `pyproject.toml`：`[project] version` 由 `"0.2.0"` 升至 `"0.3.0"`。
- `uv.lock`：通过 `uv lock` 仅更新 `aiflow` 包版本号由 `0.2.0` 至 `0.3.0`，不更新任何第三方依赖版本。
- `src/aiflow/__init__.py`：`__version__` 由 `"0.2.0"` 升至 `"0.3.0"`。
- `src/aiflow/resource_bundle.py`：`CLI_VERSION` 由 `"0.2.0"` 升至 `"0.3.0"`。
- `tests/unit/test_cli.py`：将 `--version` 与 `importlib.metadata.version("aiflow")` 断言由 `"0.2.0"` 更新为 `"0.3.0"`。
- `tests/unit/test_resource_bundle.py`：将 `compatible_cli_versions` 及构造夹具版本断言由 `"0.2.0"` 更新为 `"0.3.0"`。
- `tests/integration/test_resource_bundle_distribution.py`：将构造包输出与暂存/元数据目录名断言（`aiflow-0.2.0*`）更新为 `aiflow-0.3.0*`。
- `CHANGELOG.md`：更新版本说明并将 `## Unreleased` 下的近期交付（含 D2.1 PR #216/#217、D2.2 PR #218/#219、D4 PR #220/#221 与 D3.2 `0.3.0` 里程碑准备）整洁发布至 `## 0.3.0 - 2026-11-26`，保留空 `## Unreleased` 小节。
- `README.md`：将「当前状态」中的源码包版本由 `0.2.0` 更新为 `0.3.0`，并准确补充已交付的跨仓 Python 验证、`init apply` POSIX 支持与只读 `aiflow advise` 能力边界。
- `docs/operations/maintenance-status.md`：将 `main` 基线指针更新至 `559a0663`（已合入 `PR #204`–`PR #221`），补齐 Wave 1–3（`TASK-0192` / `TASK-0193` / `TASK-0194`）实测交付记录与 Wave 4（`TASK-0195`）`0.3.0` 里程碑准备状态（明确标注尚未创建 `v0.3.0` tag 或 GitHub Release），不含任何本机绝对路径或用户名。

已有能力复用与边界说明：
- 复用既有 `pyproject.toml`、`uv lock`、`resource_bundle.CLI_VERSION` 与打包分发测试，不新增额外版本读取脚本或发布工作流。

## 非目标

- **不创建 `v0.3.0` tag，不创建或发布 GitHub Release，不向外部 package registry 发布包**。
- 不修改 `.ai/policy/*`、`.ai/schemas/*`、`.github/workflows/*`、除 `__init__.py` 与 `resource_bundle.py` 外的业务源码，不修改 `uv.lock` 中任何第三方包版本。

## 验收条件

1. `git diff main..HEAD -- uv.lock` 仅反映 `aiflow` 自身版本 `0.2.0 -> 0.3.0` 变更。
2. `aiflow --version` 输出 `aiflow 0.3.0`，`tests/unit/test_cli.py`、`tests/unit/test_resource_bundle.py`、`tests/integration/test_resource_bundle_distribution.py`、`tests/integration/test_agent_entry_files.py` 与 `tests/integration/test_repository_hygiene.py` 全部通过。
3. `ruff check .`、`ruff format --check .` 与 `mypy` 零报错通过。
4. 正式运行 `aiflow verify TASK-0195 --actor verifier-v1`，V1 全部 10 项检查原生通过（`core` 总分支覆盖率 >= 85%、diff coverage >= 90%）。
5. 独立设计与实现审核均为 `APPROVE`，`aiflow gate TASK-0195` 通过，PR 及 closeout PR 合入 `main` 且 Ubuntu `ai-quality-gate` 全绿通过。

## 禁止动作

- **严禁创建 `v0.3.0` tag 或 GitHub Release**，严禁外部发布或修改 `.ai/policy/*` / `.ai/schemas/*`。
- 严禁升级或变更 `uv.lock` 中的第三方依赖，严禁提交 `.ai/tasks/TASK-0195/logs/`。
- 禁止跳过独立审核、自审或强推。

## 错误行为

- 若 `uv lock` 意外改动第三方依赖、或分发打包测试/版本一致性测试失败、或分类超出预期 `REVIEW / V1`，立即停止并修正或按 `aiflow escalate` 规则处理。

## 回滚

所有改动均位于独立分支 `codex/d32-release-030-prep`；合入 `main` 前可直接丢弃分支，合入后可通过标准反向 PR 回滚，无需删除或回滚远端 tag/Release。
