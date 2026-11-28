# Task Specification

## 目标

为 `aiflow` CLI 的默认文本 stdout 与 stderr 输出路径增加仅针对目标输出流不可编码字符的 `backslashreplace` 转义回退，使受影响命令（`list`、`status`、`advise`、`gate`、`review show`、其余文本 stdout 输出以及文本领域错误 stderr 输出）在 Windows 非 UTF-8（如 `cp1252`、`gbk`）管道下不抛出 `UnicodeEncodeError`，同时保持 UTF-8 输出流及所有可编码字符 100% 字节一致，且完全不触动 `aiflow observe` stdout、`atomic_write_json` 及任何规范摘要哈希逻辑。

## 范围

仅允许修改以下 3 个文件（及 `.ai/tasks/TASK-0201/**` 任务账本，不含 `logs/`）：
- `src/aiflow/cli.py`：
  - 从标准库 `typing` 导入 `TextIO`，新增局部输出辅助函数 `_write_line(text: str, *, stream: TextIO | None = None) -> None`：
    - 目标流默认为 `sys.stdout`（显式传入 `stream=sys.stderr` 时输出至标准错误）；
    - 若目标流存在非空字符串 `encoding` 属性，先尝试 `text.encode(encoding)`；仅在触发 `UnicodeEncodeError` 时执行 `text = text.encode(encoding, errors="backslashreplace").decode(encoding)`，随后调用 `print(text, file=target)`。因此 UTF-8 流及一切可在当前流编码表示的字符均 100% 保持原样，不产生额外转义或字符改动；
  - 将 `cli.py` 中的 stdout 与 stderr `print(...)` 调用路由至 `_write_line(...)`（其中 stderr 输出显式传入 `stream=sys.stderr`，非字符串路径如 `start_result.task_directory.resolve()` 先显式转为 `str(...)`）；
  - **严格保留例外**：保持 `aiflow observe` 的 stdout `print(json.dumps(serialize_observation_result(observe_result), ensure_ascii=False, sort_keys=True, separators=(",", ":")))`（约第 593 行附近）原样不变，确保其紧凑 UTF-8 JSON 契约与 `tests/unit/test_observation_adapter.py` 零变更。
- `tests/unit/test_cli_error_output.py`：
  - 新增使用受限 `cp1252` / `gbk` `io.TextIOWrapper` 流的单元测试，以及使用 `PYTHONIOENCODING=cp1252` 与 `gbk` 携带中文及 emoji 载荷（如 `"中文目标 🎯"`）的真实子进程回归测试；
  - 覆盖默认文本模式下的 `list`、`status`、`advise`、`gate`、`review show` 以及文本领域错误 `stderr` 输出，断言预期退出码（0 / 1 / 2）、零 `UnicodeEncodeError` 堆栈、不可编码字符按 `backslashreplace` 安全输出，且在 UTF-8 流下输出保持完全一致。
- `docs/operations/quickstart.md`（约第 285 行附近）：
  - 新增一句简明说明，记录默认文本输出在 UTF-8 流下原样保留字符，仅对当前输出流编码无法表示的字符执行反斜杠转义（`backslashreplace`）。

本变更仅作用于 CLI 终端输出 I/O 边界，不引入任何新依赖、新 CLI 参数、新环境变量开关或跨模块抽象，不修改文件落盘逻辑或领域服务返回值。

## 非目标

- 不修改 `aiflow observe` 的 stdout 紧凑 JSON 输出（`ensure_ascii=False`、`separators=(",", ":")`）。
- 不修改 `atomic_write_json`、`atomic_write_yaml`、`status_service._artifact_digest`、`gate._digest` 或任何规范哈希摘要与磁盘持久化格式。
- 不修改 `src/aiflow/status_service.py`、`src/aiflow/gate.py`、`src/aiflow/advisory_service.py` 等领域服务模块、`.ai/policy/*` 或 `.ai/schemas/*`。
- 不在本实施 PR 修改 `CHANGELOG.md` 或 `docs/operations/maintenance-status.md`（留待合并后的收尾 PR）。

## 验收条件

1. 目标测试集合全部通过：
   `.\.venv\Scripts\python.exe -m pytest tests/unit/test_cli_error_output.py tests/unit/test_cli.py tests/unit/test_task_list.py tests/unit/test_observation_adapter.py tests/integration/test_status_command.py tests/integration/test_advise_command.py tests/integration/test_review_command.py -q`（包含受限 `cp1252` / `gbk` `io.TextIOWrapper` 单测、真实子进程回归及 UTF-8 无变更断言）。
2. 静态检查全部退出 0：
   `.\.venv\Scripts\python.exe -m ruff check .`、`.\.venv\Scripts\python.exe -m ruff format --check .`、`.\.venv\Scripts\python.exe -m mypy` 与 `git diff --check`。
3. 契约与不变量保持：
   UTF-8 流与全部可编码字符输出 100% 字节一致；`aiflow observe` stdout、`atomic_write_json` 与所有规范摘要哈希未受任何影响。
4. 本地原生完整 V1 验证 `.\.venv\Scripts\python.exe -m aiflow verify TASK-0201 --actor cli-text-author` 10/10 项全通过（核心分支覆盖率 >= 85%，diff coverage >= 90%）。
5. 独立设计审核（`REV-0001`）与实现审核（`REV-0002`）结论均为 `APPROVE` 且无未关闭 critical/high 发现，`aiflow gate TASK-0201 --format json` 返回 `"passed": true`（exit 0）。

## 禁止动作

- 禁止修改 `src/aiflow/cli.py`、`tests/unit/test_cli_error_output.py`、`docs/operations/quickstart.md` 之外的业务/测试/文档/治理文件。
- 禁止改动 `aiflow observe` stdout、`atomic_write_json` 或任何规范摘要计算。
- 禁止执行 `deploy`、`delete`、`secret_export`、`paid_external_call` 或绕过独立审核/Gate 直接合并。
- 禁止提交 `.ai/tasks/TASK-0201/logs/` 或在 tracked 文件及提交记录中写入本机绝对路径、用户名或机器名。

## 错误行为

- `--format json` 领域错误仍向 stderr 输出仅含 `code` 和 `message` 的 ASCII 安全 JSON 并退出 1（stdout 为空）。
- 默认文本模式领域错误（`AiflowError`）在 `cp1252`、`gbk` 等非 UTF-8 stderr 流遇到不可编码字符时，不得二次抛出 `UnicodeEncodeError`，必须通过 `_write_line(..., stream=sys.stderr)` 以 `backslashreplace` 转义不可编码字符并保持退出码 1（stdout 为空）。
- 默认文本模式下的 `list`、`status`、`advise`、`gate`（未通过时仍退出 2）、`review show` 在非 UTF-8 stdout 流下遇到中文或 emoji 载荷时不得抛出 `UnicodeEncodeError`，必须安全输出经 `backslashreplace` 转义的文本并保持各自预期退出码。
- 非法 CLI 参数继续沿用 `argparse` usage 输出与退出码 2。

## 回滚

- 合入 `main` 前可在工作分支 `codex/cli-text-pipe-encoding` 回退或丢弃提交并删除分支；合入 `main` 后可通过标准反向 PR（`git revert`）完整回滚全部 3 个文件的改动，无不可逆外部状态或数据格式迁移。
