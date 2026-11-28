# Review Package · TASK-0201

## 审核目标

对 `TASK-0201`（分支 `codex/cli-text-pipe-encoding`，基线 `a81122e9a88d7e42c301fbda58b38c31735790ad`，实现提交 `fd95e533aec73afee35e10b4905d650183276a10`）进行独立实现审核（`REV-0002` / `--stage implementation`）：裁决 CLI 默认文本 stdout/stderr 输出的 `backslashreplace` 非 UTF-8 管道回退实现、回归测试与文档补充是否严格符合冻结规格，是否保持 UTF-8 字节一致、`aiflow observe` stdout、`atomic_write_json` 及规范摘要零变更，并满足仓库 V1 质量门禁。

## 背景

在 Windows 非 UTF-8（如 `cp1252` 或 `gbk`）子进程管道下，向 stdout 或 stderr 打印含中文或 emoji 等不可表示字符的默认文本输出（例如 `list`、`status`、`advise`、`gate`、`review show` 以及文本模式领域错误）会触发 `UnicodeEncodeError`。继 `TASK-0199` 完成 CLI JSON stdout 的 ASCII 转义后，本任务在 `src/aiflow/cli.py` 输出边界引入 `_write_line(...)`，仅在目标流编码无法表示某些字符时执行 `backslashreplace` 转义回退，同时保持 UTF-8 输出流与全部可编码字符 100% 原样不变。

## 代码地图

仅修改以下 3 个非账本文件（`git diff a81122e9a88d7e42c301fbda58b38c31735790ad..fd95e533aec73afee35e10b4905d650183276a10`）：
- `src/aiflow/cli.py`：
  - 从 `typing` 导入 `TextIO` 并新增 `_write_line(text: str, *, stream: TextIO | None = None) -> None`（第 52-61 行），在流具有非空字符串 `encoding` 且 `text.encode(encoding)` 抛出 `UnicodeEncodeError` 时才执行 `text.encode(encoding, errors="backslashreplace").decode(encoding)`，随后写入目标流；
  - 将 `cli.py` 中的 stdout 与 stderr `print(...)` 调用路由至 `_write_line(...)`（stderr 显式传 `stream=sys.stderr`）；
  - 严格保留 `aiflow observe` stdout 的 `print(json.dumps(serialize_observation_result(observe_result), ensure_ascii=False, sort_keys=True, separators=(",", ":")))`（第 607-614 行）原样不变。
- `tests/unit/test_cli_error_output.py`：
  - 新增 `test_default_text_output_escapes_unencodable_chars_and_preserves_utf8`（使用受限 `cp1252` / `gbk` / `utf-8` `io.TextIOWrapper` 流）与 `test_cli_text_stdout_and_stderr_survive_non_utf8_pipe_encoding`（使用 `PYTHONIOENCODING=cp1252` / `gbk` / `utf-8` 真实子进程），覆盖默认文本模式下的 `list`、`status`、`advise`、`gate`、`review show` 与文本领域错误 `stderr`，验证预期退出码（0 / 1 / 2）、零 `UnicodeEncodeError`、非 UTF-8 流的 `backslashreplace` 输出及 UTF-8 流字节一致保留。
- `docs/operations/quickstart.md`：
  - 在第 289 行补充一句简明说明，指出默认文本输出在 UTF-8 流下原样保留字符，仅对当前输出流编码无法表示的字符执行反斜杠转义（`backslashreplace`）。

## 语义变更

- **CLI 默认文本输出 I/O 边界容错**：当且仅当目标 stdout/stderr 流存在 `encoding` 且待写入文本包含该编码无法表示的字符时，通过 `encode(encoding, errors="backslashreplace").decode(encoding)` 将不可编码字符安全替换为 `\uXXXX` / `\UXXXXXXXX` 转义序列后再输出，防止 `UnicodeEncodeError`。
- **不变量保持不变**：UTF-8 流与所有可编码字符 100% 字节一致；`aiflow observe` 紧凑 stdout JSON、`atomic_write_json`、全部规范摘要哈希及 `--format json` 错误/正常输出契约均保持零变更。

## 风险

- **跨平台 CI 交叉验证待运行**：本机 V1 在 Windows 原生环境完成（9 项既定平台/外置 Node 用例跳过），远端 Ubuntu `ai-quality-gate` 将在推送 PR 后执行。

## 证据

- **已验证结果**：正式本地原生 V1 验证（`python -m aiflow verify TASK-0201 --actor cli-text-author`，记录于 `.ai/tasks/TASK-0201/evidence.json`，绑定 `subject_commit: fd95e533aec73afee35e10b4905d650183276a10`）10/10 项全部 `passed`（`contract`、`scope`、`ruff_check`、`ruff_format_check`、`smoke`、`unit_tests`、`regression_tests`、`mypy`、`coverage_xml`、`diff_coverage`）。
- **测试与覆盖率实测**：`5399 passed, 9 skipped in 1726.28s`；核心分支覆盖率 `91%`（门槛 >= `85%`；`cli.py` `95%`）；diff coverage `100%`（`40` 行、`0` 行未覆盖；`src/aiflow/cli.py` `100%`；门槛 >= `90%`）。
- **静态检查与专项回归**：`ruff check .`、`ruff format --check .`（871 文件）、`mypy`（64 个源文件零错误）、目标 7 个单测/集成测试文件（`151 passed in 48.06s`）与 `git diff --check` 全部通过。
- **复现命令**：`python -m aiflow verify TASK-0201 --actor cli-text-author`。
- **仍未验证的场景**：GitHub Actions Ubuntu `ai-quality-gate` 远端 CI（将在推送 PR 后运行）。

## 审核问题

请独立审核者明确裁决以下问题：
1. `git diff a81122e9a88d7e42c301fbda58b38c31735790ad..fd95e533aec73afee35e10b4905d650183276a10` 是否严格限定在规格批准的 3 个文件，且仅在 `src/aiflow/cli.py` 中增加 `_write_line` 路由而不触碰 `aiflow observe` stdout、`atomic_write_json` 或规范摘要？
2. `tests/unit/test_cli_error_output.py` 的 `io.TextIOWrapper` 单元测试与 `cp1252` / `gbk` / `utf-8` 真实子进程回归测试是否充分覆盖 `list`、`status`、`advise`、`gate`、`review show` 与文本领域错误 `stderr`，并验证 UTF-8 输出保持字节一致？
3. `evidence.json`（10/10 `passed`，`5399 passed, 9 skipped`，core `91%`，diff `100%`）是否有效绑定当前 `subject_commit` `fd95e533aec73afee35e10b4905d650183276a10` 且满足冻结规格验收条件？

交付边界五项自检结论：
1. **目标与关键假设是否清楚**：是；目标为消除 CLI 默认文本 stdout/stderr 在非 UTF-8 管道下的 `UnicodeEncodeError`，关键假设为仅在 I/O 边界对目标编码不可表示的字符执行 `backslashreplace`，UTF-8 及可编码字符完全不变。
2. **是否已核实语言标准库与代码库既有复用机会**：是；直接复用 Python 标准库 `str.encode(encoding, errors="backslashreplace").decode(encoding)` 与 `typing.TextIO`，不引入新依赖或冗余抽象。
3. **各修改模块是否存在更简单的直接实现**：无；单一模块内局部 helper `_write_line` 已是覆盖 20 余处 CLI print 调用而不重复样板代码的最简方案。
4. **新增抽象、分支或配置项是否均有当前明确依据**：是；`_write_line` 仅含单一必需的 `UnicodeEncodeError` 边界回退分支，无配置开关或跨模块抽象。
5. **是否只触及了任务范围边界内的文件**：是；业务与文档变更严格限于 3 个批准文件，账本记录仅位于 `.ai/tasks/TASK-0201/**`（不含 `logs/`）。

## 推荐结论

`APPROVE` — 实现严格符合冻结规格与范围边界，V1 全部 10/10 项检查一次通过（`5399 passed, 9 skipped`，core `91%`，diff coverage `100%`），无未解决 critical/high 风险。
