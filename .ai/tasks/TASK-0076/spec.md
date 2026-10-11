# Task Specification

## 目标

在不改变其余 CLI、Policy、证据或 Gate 行为的前提下，下线项目所有者 2026-10-10 决定退役的外部审核导入（`aiflow external-review`）与 `aiflow verify --pytest-temp-root` 选项，合并完全相同的时间戳辅助函数，并让治理文档与 Policy 2.5.0 一致。

## 范围

- 外部审核导入：删除 `src/aiflow/external_review.py`、`aiflow external-review` 子命令及其专用错误输出、`contracts.py` 中的三个 external-review 契约及 `.ai/schemas/external-review*.schema.json`、对应契约夹具与测试；`docs/operations/external-review-import.md` 改为简短的“已移除”说明与恢复方法。
- pytest 临时根：删除 `--pytest-temp-root` 选项、`src/aiflow/verification_temporary.py`、`verification.py`/`verification_service.py`/`process_runner.py` 中只为它存在的分支与字段，以及对应测试；`docs/operations/pytest-temporary-roots.md` 改为“已移除”说明。
- 时间戳：`approval`、`ask_service`、`classification_service`、`process_runner`、`review_service`、`state`、`task_service`、`verification_service` 中 8 个实现完全相同的 `_now`/`_utc_now` 合并为一个公共函数（放在既有模块中，不新建模块）；`mutation_evidence._utc_now`（返回 datetime 且被测试替换）不动。
- 文档：`AGENTS.md` 升级清单补齐 Policy 2.5.0 治理面中缺少的路径（`.ai/**` 整体、`tools/ci/**`、`AGENTS.md`、`CLAUDE.md`、`pyproject.toml`、`uv.lock`），只增不减，不改“常设授权”一节；`docs/operations/maintenance-status.md` 当前 Policy 改为 2.5.0；README、quickstart、recovery、hooks 等仍介绍已删除功能的段落同步删改；`CHANGELOG.md` 记一行。
- `.ai/tasks/<本任务>/**`。

## 非目标

- 不删除 `aiflow observe`、observation 模块或 `tools/hooks`（阶段二验收矩阵 P2-ESC-01/P2-HOOK-01 与历史账本回放依赖它们）。
- 不改 Policy、`.ai/schemas` 中其他契约、mutation manifest 及其目标符号；不改历史任务记录。
- 不执行 deploy、delete 外部数据等动作。

## 验收条件

- `python -m aiflow --help` 不再列出 `external-review`，其余子命令不变；`python -m aiflow verify --help` 不再有 `--pytest-temp-root`。
- `git grep -n "external_review\|pytest_temp_root\|verification_temporary" -- src tests tools` 无结果；8 个时间戳副本只剩一个定义。
- `aiflow status` 对 TASK-0054～0062 等历史任务仍可读（不因删除契约失败）。
- 阶段二追溯与自举测试（`tests/integration/test_acceptance_traceability.py`、`tests/acceptance`、`tests/e2e`）通过。
- 完整质量检查通过：全量 pytest 带 `--cov-fail-under=85`、diff coverage ≥90%、ruff、mypy、`git diff --check`；AI Flow `verify` 与 `gate` 通过。

## 禁止动作

push、merge、deploy、delete、secret_export、paid_external_call；不修改其他任务目录。

## 错误行为

- 若发现被删代码在其余生产路径或历史任务读取路径中仍被调用，停止并升级，而不是保留兼容分支。
- 删除后旧参数 `--pytest-temp-root` 与旧子命令应由 argparse 报错拒绝，不静默忽略。

## 回滚

`git revert` 本任务实现提交即可恢复。
