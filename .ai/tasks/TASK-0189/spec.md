# TASK-0189 · 在隔离验证执行器中补充 Windows `ssh-keygen` 所需目录与环境变量

## 目标

在隔离验证执行器 `process_runner._environment()` 中，(1) 构造最小 `PATH` 时将宿主机可定位到的 `ssh-keygen` 所在目录（紧随 `git` 之后）去重追加至 `PATH`，(2) 在 `os.name == "nt"` 时随 `SystemRoot` 一并转发非空的 `ProgramData`，使 Windows 原生 `aiflow verify` 中的集成测试可定位并正常初始化运行 OpenSSH `ssh-keygen.exe`。

## 范围

仅修改以下范围：

- `.ai/tasks/TASK-0189/**`
- `src/aiflow/process_runner.py`（仅 `_environment()` 内最小 `PATH` 工具目录解析与 `os.name == "nt"` 下的 `SystemRoot`/`ProgramData` 显式最小转发）
- `tests/unit/test_process_runner.py`（覆盖 `("git", "ssh-keygen")` PATH 分支、更新环境键允许集断言，并补充跨平台 `process_runner._environment()` 单元测试）

复用标准库 `shutil.which`、`pathlib.Path.resolve()` 与既有 `os.defpath` 去重追加及 `os.name == "nt"` 显式白名单转发模式；不将宿主机完整 `PATH` 或其他任意环境变量传入隔离进程。参数与边界校验仍仅留在既有的 `check.environment`、临时目录与运行目录验证边界，内部逻辑保持简洁。

## 非目标

- 不放宽 `process_runner._environment()` 对其他环境变量（如 `PYTHONPATH`、`NODE_OPTIONS`、用户配置或凭据变量）的隔离过滤策略。
- 不修改 `tests/integration/test_private_replay_receipt.py` 或任何收据验签逻辑。
- 不引入新配置项、环境变量开关、额外抽象层或顺手重构。
- 不修改 `codex/governance-surface-and-tools-mypy` 或其他并行任务分支与历史账本。

## 验收条件

1. `src/aiflow/process_runner.py` 中 `_environment()` 按 `("git", "ssh-keygen")` 顺序调用 `shutil.which(program)`，若非 `None`，取 `str(Path(located).resolve().parent)`，当不在 `path_entries` 中时追加至 `path_entries`。
2. `src/aiflow/process_runner.py` 中 `_environment()` 在 `os.name == "nt"` 时，遍历 `("SystemRoot", "ProgramData")`，当 `os.environ.get(key)` 非空时写入 `environment[key]`；在非 `nt` 平台不转发这两项。
3. `tests/unit/test_process_runner.py` 满足以下全部测试要求：
   - 新增单元测试覆盖 `("git", "ssh-keygen")` 三个分支：不同目录按序追加、同目录去重仅追加一次、`ssh-keygen` 为 `None` 时仅追加 `git` 不报错；
   - 既有测试 `test_runner_preserves_search_order_when_resolving_default_directories` 无需修改即可通过；
   - 更新环境允许集及转发断言以包含 `ProgramData`（`nt` 下存在时转发，否则不转发）；
   - 新增直接调用 `process_runner._environment(...)`（在 `monkeypatch.setattr(process_runner.os, "name", ...)` 时不启动子进程）的跨平台单元测试，覆盖：(1) `nt` 下 `SystemRoot` 与 `ProgramData` 均设置时两者均被转发；(2) `nt` 下 `ProgramData` 未设置时仅转发 `SystemRoot`；(3) `posix` 下两者在 `os.environ` 中存在时均不被转发。
4. 目标测试（`tests/unit/test_process_runner.py`、`tests/integration/test_private_replay_receipt.py`）、`ruff check .`、`ruff format --check .`、`mypy` 全部通过。
5. 在 Windows 原生环境下运行 `uv run --locked --extra dev python -m aiflow verify TASK-0189 --actor author-procfix` 全部 10/10 V1 检查通过（含 `test_private_replay_receipt.py` 全部 168 个用例无错误、core coverage >= 85%、diff coverage >= 90%）。

## 禁止动作

- 禁止修改本任务 `allowed_scope` 之外的任何源码、测试、CI 或政策文件。
- 禁止伪造、跳过或弱化测试、覆盖率门禁或审查/验证证据，禁止将 `logs/` 目录提交入库。
- 禁止自行审查本人变更；设计和实现独立审核均须由 `@reviewer-procfix` 完成。
- 禁止越过常设授权边界执行未授权的外部操作或触碰 `codex/governance-surface-and-tools-mypy`。

## 错误行为

- 若 `check.environment` 含除 `COVERAGE_FILE` 之外的键、`COVERAGE_FILE` 逃逸 `run_dir`、或临时目录根非法/不可创建，继续抛出既有 `ContractError`。
- 若 `shutil.which("git")` 或 `shutil.which("ssh-keygen")` 返回 `None`，静默跳过该缺失工具目录而不阻断不依赖该工具的检查运行；`SystemRoot` 或 `ProgramData` 为空或未设置时静默跳过。
- 若分类结果超出 `REVIEW / V1` 或验证出现超出范围的阻塞，立即停止并按规则上报。

## 回滚

所有变更位于基于 `1807c540f03be987df9115373036f72498553fc6` 创建的独立分支 `codex/fix-windows-runner-ssh-keygen-path`；如需回滚，放弃或回退该分支提交即可恢复至基线状态，无持久外部副作用。
