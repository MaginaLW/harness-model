# TASK-0194 · 只读非评分 `aiflow advise` 命令与建议服务（D4）

## 目标

在基线 `cc414e3a1dfe95bd3a8bd817bd7fa153880e2f63`（分支 `codex/d4-aiflow-advise`）上交付只读非评分的 `aiflow advise` 命令与 `advisory_service`（D4）：新增 `src/aiflow/advisory_service.py` 基于既有原生 `status`/`gate`/`review`/`task` 服务组合生成确定性状态解释报告（固定 `probability_status="unestimated"`、`execution_allowed=False`、`permission_effect="none"`、`ledger_effect="none"`），在 `src/aiflow/cli.py` 注册 `aiflow advise <TASK-ID> [--format {text,json}]` 子命令，并补充全生命周期只读零写入测试与单元测试。

## 范围

仅允许修改以下 4 个路径（以及 `.ai/tasks/TASK-0194/**` 治理账本，不含 `logs/`）：
- `src/aiflow/advisory_service.py`（新增）：导出 `advise_task(repository_root: Path, task_id: str) -> dict[str, Any]` 与 `format_advisory_text(report: Mapping[str, Any]) -> str`；严格只读组合调用既有 `summarize_task`、`evaluate_gate`、`list_review_records`、`load_task_record`（及纯函数 `assess_scope` 检查脏工作树路径）；输出固定非授权契约（`schema_version="1.0"`、`design_version="advisory-status-explanation-v0"`、`mode="offline_advisory"`、`purpose="offline_status_explanation"`、`probability_status="unestimated"`、`execution_allowed=False`、`permission_effect="none"`、`ledger_effect="none"`）与 6 类保守建议（`continue_mechanical`、`complete_machine_evidence`、`repair_in_scope`、`residual_human_decision`、`retain_unknown`、`stop_out_of_scope`）；不写 `.ai/tasks/`、不复制路由/新鲜度规则表、不执行外部命令或记录批准。
- `src/aiflow/cli.py`（修改）：新增 `advise` 子命令 `aiflow advise <TASK-ID> [--format {text,json}]`（默认 `text`），通过 `resolve_repository_root(Path.cwd())` 解析仓库根，零写入、零 `chdir`。
- `tests/unit/test_advisory_service.py`（新增）：覆盖全部 6 类建议、固定非授权不变量、Status/Gate 不一致保留、过期批准/证据场景、`format_advisory_text` 与无效任务错误传播（分支覆盖率 `>= 95%`）。
- `tests/integration/test_advise_command.py`（新增）：在真实临时 Git 仓库跨越 `NEW`、`WAITING_FOR_ASK`、`WAITING_FOR_SPEC_REVIEW`、`READY_TO_IMPLEMENT`、`IMPLEMENTING`、`FAILED`、`BLOCKED`、`APPROVED_FOR_MERGE`（新鲜与过期）及 `MERGED` 全状态执行 `aiflow advise`，断言 `.ai/` 目录在执行前后字节级零变化、`--format json/text` 与子目录调用正确。

已有能力复用与边界说明：
- 直接复用既有 `status_service`、`gate`、`review_service`、`task_service`、`scope` 与 `cli.resolve_repository_root`；仅在任务读取与输入边界拒绝未知任务或非法参数，不重算或覆盖 Gate/Policy 结论。

## 非目标

- 不修改 `.ai/policy/*`、`.ai/schemas/*`、`src/aiflow/status_service.py`、`src/aiflow/gate.py`、`src/aiflow/freshness.py`。
- 不实现自动执行、自动批准、评分校准、概率估计（保持 `"unestimated"`）或写入任何 `.ai/` 状态文件。

## 验收条件

1. `tests/unit/test_advisory_service.py`、`tests/integration/test_advise_command.py`、`tests/unit/test_cli.py`、`tests/integration/test_cli_repository_root.py`、`tests/unit/test_import_boundaries.py`、`tests/unit/test_cli_error_output.py` 全部通过，`advisory_service.py` 分支覆盖率 `>= 92%`。
2. `ruff check .`、`ruff format --check .` 与 `mypy` 零报错通过。
3. 正式运行 `aiflow verify TASK-0194 --actor verifier-v1`，V1 全部 10 项检查原生通过（`core` 总分支覆盖率 >= 85%、diff coverage >= 90%）。
4. 独立设计与实现审核均为 `APPROVE`，`aiflow gate TASK-0194` 通过，PR 及 closeout PR 合入 `main` 且 Ubuntu `ai-quality-gate` 全绿通过。

## 禁止动作

- 禁止修改 `.ai/policy/*`、`.ai/schemas/*`、`status_service.py`、`gate.py`、`freshness.py`。
- 禁止 `advise` 写入 `.ai/tasks/`、授予执行权限、绕过 Gate 或估算概率数值，禁止提交 `.ai/tasks/TASK-0194/logs/`。
- 禁止跳过独立审核、自审或强推。

## 错误行为

- 当任务不存在、合约损坏或 CLI 参数非法时，保持与既有 `cli.py` 一致的确定性错误输出与非零退出码；遇到越界变更、Status/Gate 冲突或缺失根因时如实保留双方原始结果并映射至 `stop_out_of_scope` / `complete_machine_evidence` / `retain_unknown`。

## 回滚

所有改动均位于独立分支 `codex/d4-aiflow-advise`；合入 `main` 前可直接丢弃分支，合入后可通过标准反向 PR 回滚，无需变更不可逆远端状态。
