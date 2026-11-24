# TASK-0189 · `spec_changed` 升级解决说明

## 触发事实

1. 首轮实施提交 `3d5c243b4c92c01cf08b4645ee34df62430b94f2` 后，正式执行 `aiflow verify TASK-0189 --actor author-procfix`：
   - 7/10 项检查通过（`contract`、`scope`、`ruff_check`、`ruff_format_check`、`smoke`、`mypy`、`diff_coverage` 100%）。
   - `unit_tests` / `regression_tests` / `coverage_xml` 失败：`4774 passed, 9 skipped, 166 errors`。
2. 根因定位：
   - `C:\Windows\System32\OpenSSH\ssh-keygen.EXE` 已可通过新增的 `PATH` 项定位并启动（原 `FileNotFoundError` 已消除）。
   - 但在隔离环境 `process_runner._environment()` 剥离 `ProgramData` 后，Windows OpenSSH `ssh-keygen.exe` 在初始化阶段直接返回退出码 `255`（无输出）。
   - 在 `_environment()` 隔离环境中逐一二分验证 `os.environ` 后确认：仅补充转发 `ProgramData`（`C:\ProgramData`）即可使 `tests/integration/test_private_replay_receipt.py` 全部 `168 passed in 15.11s`。

## 解决措施

- 依据项目协同协调方批准（board `#87`），修订 `spec.md`，在 `os.name == "nt"` 条件下于 `process_runner._environment()` 中与 `SystemRoot` 并列显式转发非空 `ProgramData`，并在 `tests/unit/test_process_runner.py` 更新允许集断言及补充跨平台单元测试，以保证 Windows 与 Ubuntu CI 的 `diff_coverage >= 90%`。
- 任务允许修改文件范围保持不变（`.ai/tasks/TASK-0189/**`、`src/aiflow/process_runner.py`、`tests/unit/test_process_runner.py`），不降低路由或验证等级（保持 `REVIEW / V1`）。
