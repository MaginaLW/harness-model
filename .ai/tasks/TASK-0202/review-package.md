# Review Package · TASK-0202

## 审核目标

对 `TASK-0202`（分支 `codex/portable-closeout-check`，基线 `d991674c81b6e874007e11515336780800384cee`，实现提交 `f44a2727e41aff3871b3040881546c4499680eab`）进行独立实现审核（`REV-0002` / `--stage implementation`）：裁决将收尾与保留账本校验能力抽离至可安装模块 `src/aiflow/closeout_check.py`、在 `src/aiflow/task_service.py` 公开兼容符号、将 `tools/ci/verify_closeout.py` 收敛为兼容薄包装及补充便携性测试的实现是否严格符合冻结规格与仓库 V1 质量门禁。

## 背景

既有 `tools/ci/verify_closeout.py` 依赖仓库内 `tools.ci.resolve_task.git_bytes` 与 `aiflow.task_service` 的私有符号（`_is_subject_sync_staged_patch`、`_require_merge_commit`），且未对 `require_valid_contract` 显式绑定目标仓库 `.ai/schemas` 上下文，因此无法在仅安装 `aiflow` wheel 且无源码树/`tools/` 的外部仓库中独立执行。继 `TASK-0192` 抽离 `aiflow.coverage_check` 后，本任务按相同模式提供可安装的 `aiflow.closeout_check` 与兼容的 `tools/ci/verify_closeout.py` 薄包装。

## 代码地图

仅修改以下 4 个非账本文件（`git diff d991674c81b6e874007e11515336780800384cee..f44a2727e41aff3871b3040881546c4499680eab`）：
- `src/aiflow/task_service.py`：
  - 将 `_is_subject_sync_staged_patch` 与 `_require_merge_commit` 公开为 `is_subject_sync_staged_patch`（第 483-509 行）与 `require_merge_commit`（第 1216-1260 行），并在模块内保留 `_is_subject_sync_staged_patch = is_subject_sync_staged_patch`（第 512 行）与 `_require_merge_commit = require_merge_commit`（第 1263 行）向后兼容别名，原有签名与校验逻辑保持不变。
- `src/aiflow/closeout_check.py`（新增，252 行）：
  - 迁入 `verify_closeout(root, base, head, task_id)`、`verify_retained(root, base, head, task_id)` 与 `main(argv=None)`（含 `if __name__ == "__main__": raise SystemExit(main())`）；
  - 实现自包含只读 `_git_bytes(root, *args)`（`GIT_OPTIONAL_LOCKS="0"`、`timeout=20`、`check=False`，非零退出抛出 `ValueError`），不导入 `tools.*`；
  - 仅从 `aiflow.*` 导入公共符号（`SCHEMA_RELATIVE_DIRECTORY`、`require_valid_contract`、`schema_directory_context`、`apply_risk_facts`、`AiflowError`、`replay_events`、`is_subject_sync_staged_patch`、`require_merge_commit`），不导入 `aiflow.node_*` 或 `aiflow.installed_*`；
  - 在 `verify_closeout` 与 `verify_retained` 中通过 `with schema_directory_context(root / SCHEMA_RELATIVE_DIRECTORY):` 绑定目标仓库 Schema 目录，确保构建 wheel 在无源码检出仓库中从 `root/.ai/schemas` 加载 Schema。
- `tools/ci/verify_closeout.py`：
  - 替换为对齐 `tools/ci/check_coverage.py` 风格的兼容薄包装（40 行）：通过 `_ensure_src_on_path()` 按需注入仓库 `src/` 路径，转发 `verify_closeout`、`verify_retained` 与 `main` 至 `aiflow.closeout_check`。
- `tests/unit/test_verify_closeout.py`：
  - 保留全部 12 条既有 `tools.ci.verify_closeout` 用例不变，新增 3 条覆盖 `aiflow.closeout_check` 直接 API（工作目录无 `.ai/schemas` 且依赖 `root/.ai/schemas`）、`python -m aiflow.closeout_check` 子进程（valid closeout、valid `--retained`、tampered/invalid exit 1）、`tools.ci.verify_closeout.main` 包装器，以及 `subject_commit_synchronized` / `spec_frozen` / `repository_id` 边界用例。

## 语义变更

- **可移植 closeout/retained 校验内核**：`python -m aiflow.closeout_check` 与 `aiflow.closeout_check.{verify_closeout,verify_retained,main}` 可脱离源码树与 `tools/` 独立运行，并从目标仓库 `root/.ai/schemas` 加载契约 Schema。
- **公共辅助导出与向后兼容**：`aiflow.task_service` 导出 `is_subject_sync_staged_patch` 与 `require_merge_commit` 并保留原私有别名；`tools/ci/verify_closeout.py` 保持与现有 CI 工作流及调用方完全一致的导入和 CLI 行为。

## 风险

- **跨平台 CI 交叉验证待运行**：本机 V1 在 Windows 原生环境完成（9 项既定平台/外置 Node 用例跳过），远端 Ubuntu `ai-quality-gate` 将在推送 PR 后执行。

## 证据

- **已验证结果**：正式本地原生 V1 验证（`python -m aiflow verify TASK-0202 --actor closeout-author`，记录于 `.ai/tasks/TASK-0202/evidence.json`，绑定 `subject_commit: f44a2727e41aff3871b3040881546c4499680eab`）10/10 项全部 `passed`（`contract`、`scope`、`ruff_check`、`ruff_format_check`、`smoke`、`unit_tests`、`regression_tests`、`mypy`、`coverage_xml`、`diff_coverage`）。
- **测试与覆盖率实测**：`5402 passed, 9 skipped in 1395.69s (0:23:15)`；核心分支覆盖率 `91%`（门槛 >= `85%`；`closeout_check.py` `88%`，`task_service.py` `85%`）；diff coverage `92%`（`132` 行、`10` 行未覆盖；`closeout_check.py` `92.2%`、`task_service.py` `100%`；门槛 >= `90%`）。
- **静态检查与专项回归**：`ruff check .`、`ruff format --check .`（874 文件）、`mypy`（65 个源文件零错误）、目标 4 个测试文件（`104 passed in 45.10s`）与 `git diff --check` 全部通过。
- **复现命令**：`python -m aiflow verify TASK-0202 --actor closeout-author`。
- **仍未验证的场景**：GitHub Actions Ubuntu `ai-quality-gate` 远端 CI（将在推送 PR 后运行）。

## 审核问题

请独立审核者明确裁决以下问题：
1. `git diff d991674c81b6e874007e11515336780800384cee..f44a2727e41aff3871b3040881546c4499680eab` 是否严格限定在规格批准的 4 个文件，且 `src/aiflow/closeout_check.py` 仅导入 `aiflow.*` 公共符号、不导入 `tools.*` / `aiflow.node_*` / `aiflow.installed_*`，并使用 `GIT_OPTIONAL_LOCKS="0"` 只读 Git 查询与 `schema_directory_context(root / SCHEMA_RELATIVE_DIRECTORY)`？
2. `src/aiflow/task_service.py` 公开符号与私有别名及 `tools/ci/verify_closeout.py` 兼容薄包装是否完全保持现有 `tools.ci.verify_closeout` 与 `tests/integration/test_github_workflow.py` 契约？
3. `tests/unit/test_verify_closeout.py` 与 `evidence.json`（10/10 `passed`，`5402 passed, 9 skipped`，core `91%`，diff `92%`）是否有效绑定当前 `subject_commit` `f44a2727e41aff3871b3040881546c4499680eab` 并满足冻结规格验收条件？

交付边界五项自检结论：
1. **目标与关键假设是否清楚**：是；目标是将收尾与保留账本校验抽离至可安装 `aiflow.closeout_check`，关键假设是便携包通过 `schema_directory_context(root / SCHEMA_RELATIVE_DIRECTORY)` 从目标仓库读取 Schema 且不依赖源码树或 `tools/`。
2. **是否已核实语言标准库与代码库既有复用机会**：是；直接复用 `aiflow.contracts.schema_directory_context`、`aiflow.task_service` 校验函数、`aiflow.state.replay_events` 与 `aiflow.decision_units.apply_risk_facts`，兼容薄包装对齐 `tools/ci/check_coverage.py`。
3. **各修改模块是否存在更简单的直接实现**：无；单一模块 `closeout_check.py` 加薄包装 `tools/ci/verify_closeout.py` 已是最简可移植拆法。
4. **新增抽象、分支或配置项是否均有当前明确依据**：是；未引入新配置开关或额外抽象，仅保留既有校验逻辑与向后兼容别名。
5. **是否只触及了任务范围边界内的文件**：是；业务与测试变更严格限于 4 个批准文件，账本记录仅位于 `.ai/tasks/TASK-0202/**`（不含 `logs/`）。

## 推荐结论

`APPROVE` — 实现严格符合冻结规格与范围边界，V1 全部 10/10 项检查一次通过（`5402 passed, 9 skipped`，core `91%`，diff coverage `92%`），无未解决 critical/high 风险。
