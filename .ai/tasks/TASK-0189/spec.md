# TASK-0189 · 在隔离验证执行器 PATH 中补充 ssh-keygen 目录

## 目标

在隔离验证执行器 `process_runner._environment()` 构造最小 `PATH` 时，将宿主机可定位到的 `ssh-keygen` 所在目录（紧随 `git` 之后）去重追加至 `PATH`，使 Windows 原生 `aiflow verify` 中的集成测试可正常调用 `ssh-keygen`。

## 范围

仅修改以下范围：

- `.ai/tasks/TASK-0189/**`
- `src/aiflow/process_runner.py`（仅 `_environment()` 内最小 `PATH` 工具目录解析逻辑）
- `tests/unit/test_process_runner.py`（补充覆盖新分支的单元测试，并保持既有搜索顺序测试不回归）

复用标准库 `shutil.which`、`pathlib.Path.resolve()` 与既有 `os.defpath` 去重追加模式；不新增环境变量白名单放行，也不将宿主机完整 `PATH` 传入隔离进程。参数与边界校验仍仅留在既有的 `check.environment`、临时目录与运行目录验证边界，内部逻辑保持简洁。

## 非目标

- 不放宽 `process_runner._environment()` 的环境变量过滤策略或导入任意外部程序目录。
- 不修改 `tests/integration/test_private_replay_receipt.py` 或任何收据验签逻辑。
- 不引入新配置项、环境变量开关、额外抽象层或顺手重构。
- 不修改 `codex/governance-surface-and-tools-mypy` 或其他并行任务分支与历史账本。

## 验收条件

1. `src/aiflow/process_runner.py` 中 `_environment()` 按 `("git", "ssh-keygen")` 顺序调用 `shutil.which(program)`，若非 `None`，取 `str(Path(located).resolve().parent)`，当不在 `path_entries` 中时追加至 `path_entries`。
2. `tests/unit/test_process_runner.py` 新增单元测试完整覆盖三个分支：
   - `git` 与 `ssh-keygen` 位于 `os.defpath` 之外的不同目录时，按 `("git", "ssh-keygen")` 顺序均被追加到 `PATH`；
   - `git` 与 `ssh-keygen` 位于同一目录时，仅追加一次（去重）；
   - `ssh-keygen` 不可用（`shutil.which("ssh-keygen")` 返回 `None`）时，仅追加 `git` 目录且不报错。
3. 既有测试 `test_runner_preserves_search_order_when_resolving_default_directories` 无需修改即可通过。
4. 目标测试（`tests/unit/test_process_runner.py`、`tests/integration/test_private_replay_receipt.py`）、`ruff check .`、`ruff format --check .`、`mypy` 全部通过。
5. 在 Windows 原生环境下运行 `uv run --locked --extra dev python -m aiflow verify TASK-0189 --actor author-procfix` 全部 10/10 V1 检查通过（含 `test_private_replay_receipt.py` 全部用例、core coverage >= 85%、diff coverage >= 90%）。

## 禁止动作

- 禁止修改本任务 `allowed_scope` 之外的任何源码、测试、CI 或政策文件。
- 禁止伪造、跳过或弱化测试、覆盖率门禁或审查/验证证据，禁止将 `logs/` 目录提交入库。
- 禁止自行审查本人变更；设计和实现独立审核均须由 `@reviewer-procfix` 完成。
- 禁止越过常设授权边界执行未授权的外部操作或触碰 `codex/governance-surface-and-tools-mypy`。

## 错误行为

- 若 `check.environment` 含除 `COVERAGE_FILE` 之外的键、`COVERAGE_FILE` 逃逸 `run_dir`、或临时目录根非法/不可创建，继续抛出既有 `ContractError`。
- 若 `shutil.which("git")` 或 `shutil.which("ssh-keygen")` 返回 `None`，静默跳过该缺失工具目录而不阻断不依赖该工具的检查运行。
- 若分类结果超出 `REVIEW / V1` 或验证出现超出范围的阻塞，立即停止并按规则上报。

## 回滚

所有变更位于基于 `1807c540f03be987df9115373036f72498553fc6` 创建的独立分支 `codex/fix-windows-runner-ssh-keygen-path`；如需回滚，放弃或回退该分支提交即可恢复至基线状态，无持久外部副作用。
