# Review Package · TASK-0199

## 审核目标

对 `TASK-0199`（分支 `codex/cli-json-ascii-pipes`，基线 `189a5e8dc350c4af32ee10707a26ad82d0093d75`，实现提交 `a3b516bc0ba07af919df1cec897701395d508795`）进行独立实现审核（`REV-0002` / `--stage implementation`）：裁决受影响 CLI 命令的 stdout JSON ASCII 转义修改、回归测试与文档更新是否严格满足冻结规格、保持规范哈希/磁盘写入/`aiflow observe` 契约零变更，并满足仓库 V1 质量门禁。

## 背景

在 Windows 非 UTF-8（如 `cp1252` 或 `gbk`）子进程管道下，向 stdout 打印未转义的非 ASCII JSON 字符（如中文任务目标或 emoji）可能触发 `UnicodeEncodeError` 或下游编码损坏。继 `TaskListReport.to_json()` 已采用 `ensure_ascii=True` 后，本任务依据冻结规格与设计审核 `REV-0001` 将剩余受影响 CLI stdout JSON 展示输出（`StatusSummary.to_json`、`GateDecision.to_json`、`review context` stdout、`review show --format json` 与 `advise --format json`）统一改为 `ensure_ascii=True`，同时严格保留规范哈希摘要、磁盘原子写及 `aiflow observe` 紧凑输出契约。

## 代码地图

仅修改以下 5 个非账本文件（`git diff 189a5e8dc350c4af32ee10707a26ad82d0093d75..a3b516bc0ba07af919df1cec897701395d508795`）：
- `src/aiflow/status_service.py`：仅修改 `StatusSummary.to_json()`（第 83 行），将 `ensure_ascii=False` 改为 `ensure_ascii=True`；未触碰 `_artifact_digest`（第 267 行）。
- `src/aiflow/gate.py`：仅修改 `GateDecision.to_json()`（第 118 行），将 `ensure_ascii=False` 改为 `ensure_ascii=True`；未触碰 `_digest`（第 238 行）。
- `src/aiflow/cli.py`：仅修改 `review context` 未指定 `--output` 的 stdout 输出（第 520 行）、`review show --format json`（第 553 行）与 `advise --format json`（第 576 行），将 `ensure_ascii=False` 改为 `ensure_ascii=True`；未触碰 `review context --output` 的 `atomic_write_json`（第 517 行）及 `aiflow observe` stdout 输出（第 596 行）。
- `tests/unit/test_cli_error_output.py`：新增 `test_stdout_json_commands_escape_non_ascii_and_round_trip` 单元测试与 `test_cli_json_stdout_survives_non_utf8_pipe_encoding` 真实子进程回归测试（覆盖 `PYTHONIOENCODING=cp1252` 与 `gbk`），验证 `status --format json`、`advise --format json`、`gate --format json`、`review show --format json` 与 `review context` stdout 对 `"中文目标 🎯"` 等非 ASCII 载荷输出 `.isascii()` JSON、无 `UnicodeEncodeError` 堆栈且可经 `json.loads(...)` 无损还原。
- `docs/operations/quickstart.md`：在第 289 行补充一句简明说明，指出 `list`、`status`、`advise`、`gate`、`review show` 与 stdout `review context` 的 JSON 输出采用 ASCII 转义以兼容 Windows 非 UTF-8 管道，同时完整保留解码后文本。

## 语义变更

- **stdout JSON 展示层 ASCII 转义**：5 处面向 stdout 的 JSON 展示序列化统一启用 `ensure_ascii=True`，将非 ASCII 字符转义为 `\uXXXX`，在 `json.loads(...)` 解码后语义完全等价，同时避免非 UTF-8 标准输出编码下的字符编码失败。
- **不变量保持不变**：`_artifact_digest`（`status_service.py:267`）、`_digest`（`gate.py:238`）、`atomic_write_json`（`cli.py:517`）、`aiflow observe` stdout 紧凑 JSON（`cli.py:596`）与 `--format json` stderr 错误契约均保持零修改。

## 风险

- **跨平台 CI 交叉验证待运行**：本机 V1 在 Windows 原生环境完成（9 项既定平台/外置 Node 用例跳过），远端 Ubuntu `ai-quality-gate` 将在推送 PR 后执行。

## 证据

- **已验证结果**：正式本地原生 V1 验证（`python -m aiflow verify TASK-0199 --actor batch2-author`，记录于 `.ai/tasks/TASK-0199/evidence.json`，绑定 `subject_commit: a3b516bc0ba07af919df1cec897701395d508795`）10/10 项全部 `passed`（`contract`、`scope`、`ruff_check`、`ruff_format_check`、`smoke`、`unit_tests`、`regression_tests`、`mypy`、`coverage_xml`、`diff_coverage`）。
- **测试与覆盖率实测**：`5393 passed, 9 skipped in 1965.79s`；核心分支覆盖率 `91%`（门槛 >= `85%`；`cli.py` `94%`、`gate.py` `91%`、`status_service.py` `94%`）；diff coverage `100%`（`3` 行、`0` 行未覆盖；`cli.py` `100%`、`gate.py` `100%`、`status_service.py` `100%`；门槛 >= `90%`）。
- **静态检查与专项回归**：`ruff check .`、`ruff format --check .`、`mypy`（64 个源文件零错误）、目标 8 个单测/集成测试文件（`165 passed`）与 `git diff --check` 全部通过。
- **复现命令**：`python -m aiflow verify TASK-0199 --actor batch2-author`。
- **仍未验证的场景**：GitHub Actions Ubuntu `ai-quality-gate` 远端 CI（将在推送 PR 后运行）。

## 审核问题

请独立审核者明确裁决以下问题：
1. `git diff 189a5e8dc350c4af32ee10707a26ad82d0093d75..a3b516bc0ba07af919df1cec897701395d508795` 是否严格限定在规格批准的 5 个文件，且仅修改指定 stdout JSON 展示路径而未触碰规范哈希、磁盘写入或 `aiflow observe`？
2. `tests/unit/test_cli_error_output.py` 的单元测试与 `cp1252`/`gbk` 真实子进程回归测试是否充分验证了 5 个受影响命令的 ASCII 输出、无 `UnicodeEncodeError` 及 `json.loads(...)` 无损往返？
3. `evidence.json`（10/10 `passed`，`5393 passed, 9 skipped`，core `91%`，diff `100%`）是否有效绑定当前 `subject_commit` `a3b516bc0ba07af919df1cec897701395d508795` 且满足冻结规格验收条件？

交付边界五项自检结论：
1. **目标与关键假设是否清楚**：是；目标为消除 CLI stdout JSON 输出在 Windows 非 UTF-8 管道下的编码错误，关键假设为仅调整展示层转义而不改变内部摘要与落盘格式。
2. **是否已核实语言标准库与代码库既有复用机会**：是；直接复用标准库 `json.dumps(..., ensure_ascii=True, sort_keys=True)` 与既有的 `TaskListReport.to_json()` 约定，未新增辅助函数或包装层。
3. **各修改模块是否存在更简单的直接实现**：无；每处仅改动单个 `ensure_ascii` 参数布尔值，已是最小实现。
4. **新增抽象、分支或配置项是否均有当前明确依据**：是；无新增抽象、分支或配置项，仅补充回归测试与文档说明。
5. **是否只触及了任务范围边界内的文件**：是；业务与文档变更严格限于 5 个批准文件，账本记录仅位于 `.ai/tasks/TASK-0199/**`（不含 `logs/`）。

## 推荐结论

`APPROVE` — 实现严格符合冻结规格与范围边界，V1 全部 10/10 项检查一次通过（`5393 passed, 9 skipped`，core `91%`，diff coverage `100%`），无未解决 critical/high 风险。
