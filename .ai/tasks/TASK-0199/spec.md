# Task Specification

## 目标

将 `aiflow` 受影响命令（`status`、`gate`、`review context` 标准输出、`review show`、`advise`）的 JSON stdout 序列化统一改为 `ensure_ascii=True`（即对非 ASCII 字符输出 `\uXXXX` 转义），确保在 Windows 非 UTF-8（如 `cp1252`、`gbk`）子进程管道下稳定输出合法且可无损反序列化的 ASCII JSON，同时保持 `aiflow observe`、`task.yaml`/`evidence.json` 落盘以及全部规范摘要哈希逻辑零变更。

## 范围

仅允许修改以下 5 个文件（及 `.ai/tasks/TASK-0199/**` 任务账本，不含 `logs/`）：
- `src/aiflow/status_service.py`：仅修改 `TaskStatusSummary.to_json()`（第 83 行），将 `json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)` 改为 `ensure_ascii=True`；严禁改动 `_artifact_digest`（第 267 行）等规范哈希计算函数。
- `src/aiflow/gate.py`：仅修改 `GateDecision.to_json()`（第 118 行），将 `json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)` 改为 `ensure_ascii=True`；严禁改动 `_digest`（第 238 行）等规范哈希计算函数。
- `src/aiflow/cli.py`：仅修改以下 3 处 stdout JSON 展示输出，将 `ensure_ascii=False` 改为 `ensure_ascii=True`：
  1. `review context` 未指定 `--output` 时的 stdout 输出（第 520 行）；
  2. `review show --format json` 的 stdout 输出（第 553 行）；
  3. `advise --format json` 的 stdout 输出（第 576 行）。
  严禁改动 `review context --output <path>` 的文件写入路径（`atomic_write_json`）以及 `aiflow observe` 的 stdout 紧凑 JSON 契约（第 596 行）。
- `tests/unit/test_cli_error_output.py`：新增单元测试与真实子进程编码回归测试（覆盖 `PYTHONIOENCODING=cp1252` 与 `gbk`），验证 `status --format json`、`advise --format json`、`gate --format json`、`review show --format json` 与 `review context`（stdout）在包含中文及 emoji 载荷（如 `"中文目标 🎯"`）时输出全 ASCII（`.isascii()`）JSON、无 `UnicodeEncodeError` 堆栈，且经 `json.loads(...)` 无损还原原始字符串。
- `docs/operations/quickstart.md`（约第 285 行附近）：新增一句简明说明，指出 `list`、`status`、`advise`、`gate`、`review show` 与 stdout `review context` 的 JSON 输出采用 ASCII 转义以兼容 Windows 非 UTF-8 管道，同时完整保留解码后文本。

本变更仅涉及 CLI stdout JSON 的字符转义展示层，不修改任何参数校验逻辑、文件落盘格式、磁盘 JSON/YAML 编码、规范摘要计算或已有错误契约；不引入新依赖、新配置项或新抽象。

## 非目标

- 不修改 `src/aiflow/status_service.py` 第 267 行 `_artifact_digest`、不修改 `src/aiflow/gate.py` 第 238 行 `_digest`、不修改任何 canonical hash 或磁盘原子写（`atomic_write_json` / `atomic_write_yaml`）。
- 不修改 `src/aiflow/cli.py` 第 596 行 `aiflow observe` 的 stdout JSON 契约（保持现有紧凑序列化与 `ensure_ascii=False` 不变）。
- 不修改 `--format text` 文本输出、stderr 错误输出契约、`.ai/policy/*`、`.ai/schemas/*` 或其他未在范围列出的源码/测试/文档。
- 不在本实施 PR 修改 `CHANGELOG.md` 或 `docs/operations/maintenance-status.md`（留待合并后的收尾 PR）。

## 验收条件

1. 目标测试集合通过：
   `.\.venv\Scripts\python.exe -m pytest tests/unit/test_cli_error_output.py tests/unit/test_cli.py tests/unit/test_gate.py tests/unit/test_task_list.py tests/unit/test_observation_adapter.py tests/integration/test_status_command.py tests/integration/test_advise_command.py tests/integration/test_review_command.py -q` 全部通过（含 `cp1252` / `gbk` 真实子进程回归测试）。
2. 静态检查通过：
   `.\.venv\Scripts\python.exe -m ruff check .`、`.\.venv\Scripts\python.exe -m ruff format --check .`、`.\.venv\Scripts\python.exe -m mypy` 与 `git diff --check` 全部退出 0。
3. 规范哈希与 `observe` 契约零回归：
   `_artifact_digest`、`gate._digest`、磁盘 `atomic_write_json` 及 `aiflow observe` 输出保持原样，现有全部单测与集成测试无退化。
4. 本地原生完整 V1 验证 `.\.venv\Scripts\python.exe -m aiflow verify TASK-0199 --actor batch2-author` 10/10 项全通过，核心分支覆盖率 >= 85%，diff coverage >= 90%。
5. 独立设计审核（`REV-0001`）与实现审核（`REV-0002`）均为 `APPROVE` 且无未关闭 critical/high 发现，`aiflow gate TASK-0199 --format json` 返回 `"passed": true`（exit 0）。

## 禁止动作

- 禁止修改范围清单之外的源文件、Policy、Schema、workflow 或 `aiflow observe` / canonical hash / 磁盘写入实现。
- 禁止执行 `deploy`、`delete`、`secret_export`、`paid_external_call` 或绕过独立审核/Gate 直接合并。
- 禁止提交 `.ai/tasks/TASK-0199/logs/` 或在 tracked 文件及提交记录中写入本机绝对路径、用户名或机器名。

## 错误行为

- 保持现有 `--format json` 领域错误契约不变：参数解析成功后发生 `AiflowError` 时，向 stderr 输出仅含 `code` 和 `message` 的 JSON（其默认 `json.dumps` 已为 ASCII 安全）并以退出码 1 退出，stdout 为空。
- 非法 CLI 参数维持 `argparse` usage 与退出码 2；未通过 Gate 时维持 stdout 输出 JSON 并以退出码 2 退出。
- `review context`、`status`、`advise`、`gate` 与 `review show` 在 `PYTHONIOENCODING=cp1252` 或 `gbk` 等非 UTF-8 管道下遇到非 ASCII 载荷（如中文及 emoji）时不得抛出 `UnicodeEncodeError`，必须以退出码 0（或 Gate 未通过时退出码 2）输出合法 ASCII JSON。

## 回滚

- 合入 `main` 前可在工作分支 `codex/cli-json-ascii-pipes` 回退或丢弃提交并删除分支；合入 `main` 后可通过标准反向 PR（`git revert`）完整回滚全部 5 个文件的改动，无不可逆外部状态或数据格式迁移。
