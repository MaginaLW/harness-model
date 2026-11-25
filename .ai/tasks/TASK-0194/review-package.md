# Review Package · TASK-0194

## 审核目标

对 `TASK-0194`（分支 `codex/d4-aiflow-advise`，基线 `cc414e3a1dfe95bd3a8bd817bd7fa153880e2f63`，实现提交 `019b426f8733aeabaa1fd35832b681cc5f06c6ed`）进行独立实现审核（`REV-0002` / `--stage implementation`）：确认改动严格限定于批准的 4 个 D4 文件与 `.ai/tasks/TASK-0194/**`（不含 `logs/`），`.ai/policy/*`、`.ai/schemas/*`、`status_service.py`、`gate.py` 与 `freshness.py` 零改动，`aiflow advise` 严格保持只读、零写入与非授权契约（`probability_status="unestimated"`、`execution_allowed=False`），且本机 V1 全套 10 项验证全部通过。

## 背景

用户与维护者需要一种离线只读命令，在不触发任何状态变更、批准或外部动作的前提下，将现有 `status`、`gate`、`review` 与作用域诊断结果合并解释为确定性的下一步建议清单。本任务依据设计稿实现 `src/aiflow/advisory_service.py` 并在 `src/aiflow/cli.py` 暴露 `aiflow advise <TASK-ID> [--format {text,json}]` 子命令，同时以单元测试与全生命周期字节级零写入集成测试验证。

## 代码地图

仅修改/新增以下 4 个非账本文件（`git diff cc414e3a1dfe95bd3a8bd817bd7fa153880e2f63..019b426f8733aeabaa1fd35832b681cc5f06c6ed`）：
- `src/aiflow/advisory_service.py`（新增）：实现 `advise_task(repository_root, task_id)` 与 `format_advisory_text(report)`，仅组合调用 `summarize_task`、`evaluate_gate`、`list_review_records`、`load_task_record` 与纯函数 `assess_scope`；输出固定非授权字段及 6 类保守映射建议列表。
- `src/aiflow/cli.py`（修改）：注册 `advise` 子命令（`<TASK-ID>`、`--format {text,json}` 默认 `text`），复用 `resolve_repository_root(Path.cwd())` 解析仓库根并输出报告。
- `tests/unit/test_advisory_service.py`（新增）：单元测试覆盖全部 6 类建议、固定非授权不变量、Status/Gate 不一致保留、过期批准/证据、文本格式化与错误传播。
- `tests/integration/test_advise_command.py`（新增）：在真实临时 Git 仓库覆盖 10 种任务生命周期状态与子目录调用，验证执行 `aiflow advise` 前后 `.ai/` 目录字节级零变更与 JSON/text 输出契约。

## 语义变更

- **只读组合与非授权不变量**：`advise_task` 仅读取既有原生服务的计算结果，不重写任何状态、不执行命令、不授予或代行权限；响应体始终固定 `schema_version="1.0"`、`design_version="advisory-status-explanation-v0"`、`mode="offline_advisory"`、`purpose="offline_status_explanation"`、`probability_status="unestimated"`、`execution_allowed=False`、`permission_effect="none"`、`ledger_effect="none"`。
- **不覆盖原生 Gate 与保守映射**：若 `status` 就绪态与 `evaluate_gate` 结论不一致或存在未解释失败，报告同时保留 `native_constraints` 双方原始字段，并映射至 `complete_machine_evidence`、`retain_unknown` 或 `stop_out_of_scope`；需人工裁决的 `ask_answer` / `spec_approval` / `code_approval` / `action_approval` 映射为 `residual_human_decision`（`requires_human=True`）。
- **边界保持**：未复制或修改 `status_service.py`、`gate.py`、`freshness.py` 与 Policy/Schema 规则表；`cli.py` 既有命令与错误输出格式保持不变。

## 风险

- **跨平台 CI 差异（低风险）**：本地 V1 在 Windows 原生环境运行，9 项既有平台条件测试按既定条件跳过；`advise` 全部新增单位测试与集成测试均无平台跳过且 100% 通过。远端 Ubuntu `ai-quality-gate` 将在开 PR 后执行交叉验证。

## 证据

1. **已验证结果（正式 V1 全量通过）**：`uv run --locked python -m aiflow verify TASK-0194 --actor verifier-v1`（记录于 `.ai/tasks/TASK-0194/evidence.json`，绑定 `subject_commit: 019b426f8733aeabaa1fd35832b681cc5f06c6ed`）：
   - 全部 10/10 项 V1 检查 `passed`（`contract`、`scope`、`ruff_check`、`ruff_format_check`、`smoke`、`unit_tests`、`regression_tests`、`mypy`、`coverage_xml`、`diff_coverage`）。
   - `pytest --cov=aiflow --cov-branch`：`5322 passed, 9 skipped in 1534.60s`（`core` 总分支覆盖率 `91%` >= `85%`；`src/aiflow/advisory_service.py` `100%`（275 语句、138 分支全覆盖）；`src/aiflow/cli.py` `91%`）。
   - `diff_coverage`：Diff coverage **100%** >= `90%`（`282` 行、`0` 行未覆盖；`advisory_service.py` `100%`、`cli.py` `100%`）。
   - `mypy`、`ruff check .`、`ruff format --check .`：全部通过。
2. **未验证场景**：远端 GitHub Actions Ubuntu `ai-quality-gate` 工作流（待审核批准与 Gate 通过后在 PR 阶段执行）。

## 审核问题

请独立审核者明确裁决以下问题：
1. `git diff cc414e3a1dfe95bd3a8bd817bd7fa153880e2f63..019b426f8733aeabaa1fd35832b681cc5f06c6ed` 是否严格仅触及批准的 4 个文件，且 `.ai/policy/*`、`.ai/schemas/*`、`status_service.py`、`gate.py`、`freshness.py` 均未改动？
2. `advisory_service.py` 与 `cli.py` 是否严格只读（零 `.ai/` 写入）、固定 `probability_status="unestimated"` 与 `execution_allowed=False`、且不覆盖或绕过原生 Gate 裁决？
3. `evidence.json`（10/10 `passed`，`5322 passed, 9 skipped`，`91%` core、`100%` diff coverage）与 `.ai/tasks/TASK-0194/` 账本记录是否一致且不含本机绝对路径、用户名或 `logs/` 目录？

### 交付边界五项自检

1. **目标与关键假设是否清楚**：是。目标明确为提供只读非评分的 `aiflow advise` 命令及状态解释服务；关键假设为所有状态/Gate/审核真源仍由既有原生服务计算。
2. **是否已核实语言标准库与代码库既有复用机会**：是。直接组合 `summarize_task`、`evaluate_gate`、`list_review_records`、`load_task_record`、`assess_scope` 与 `cli.resolve_repository_root`，未重复实现策略、路由或新鲜度计算。
3. **各修改模块是否存在更简单的直接实现**：无。单一 `advisory_service.py` 模块配合 `cli.py` 11 行子命令接入已是最小清晰结构。
4. **新增抽象、分支或配置项是否均有当前明确依据**：是。6 类建议映射与结构化报告字段均直接对应既有设计规范，无未请求配置开关或外部依赖。
5. **是否只触及了任务范围边界内的文件**：是。业务变更严格限定于 4 个批准文件，账本变更仅位于 `.ai/tasks/TASK-0194/**` 且排除 `logs/`。

## 推荐结论

**APPROVE** — 4 个文件实现与测试严格对齐冻结规格与只读非授权约束，本地 V1 全套 10 项检查一次通过（`5322 passed, 9 skipped`、core `91%`、`advisory_service.py` `100%`、diff coverage `100%`），满足独立实现审核通过条件。
