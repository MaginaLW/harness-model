# Review Package — TASK-0189

## 审核目标

对 `TASK-0189` 的最终实现与 V1 验证证据进行独立实现审核（`REV-0003`，`--stage implementation`），裁决是否满足 `spec.md`、`REVIEW / V1` 门禁及交付边界要求以签发 `code` 批准。

## 背景

Windows 原生运行 `aiflow verify` 时，`process_runner._environment()` 构造的隔离环境仅包含 `os.defpath` 与 `shutil.which("git")` 所在目录，且在 `os.name == "nt"` 下仅转发 `SystemRoot`：
1. 缺少 `C:\Windows\System32\OpenSSH` 目录导致 `tests/integration/test_private_replay_receipt.py` 调用 `ssh-keygen` 报 `FileNotFoundError`；
2. 补齐 `PATH` 后（初版提交 `3d5c243b`），首轮 V1 验证揭示 Windows OpenSSH `ssh-keygen.exe` 在缺少 `ProgramData` 时立即以退出码 `255` 退出（`166` 个用例 setup 报错）；经 `spec_changed` 升级与 `REV-0002` 设计批准，修订规范并在 `os.name == "nt"` 时随 `SystemRoot` 一并显式转发非空 `ProgramData`。

## 代码地图

- `src/aiflow/process_runner.py`（`_environment()` L135–145）：
  - 依次解析 `("git", "ssh-keygen")` 并去重追加其父目录至 `PATH`；
  - 在 `os.name == "nt"` 时遍历 `("SystemRoot", "ProgramData")`，非空即写入隔离 `environment`。
- `tests/unit/test_process_runner.py`：
  - L241、L313–326：更新最小环境键集合及 `SystemRoot`/`ProgramData` 转发断言；
  - L384–425（`test_runner_includes_git_and_ssh_keygen_directories_in_path`）：覆盖不同目录按序追加、同目录去重、`ssh-keygen` 不可用（`None`）三个分支；
  - L428–470（`test_environment_forwards_windows_system_variables_only_on_nt`）：不启动子进程直接测试 `process_runner._environment()`，覆盖 `nt` 均设置、`nt` 缺 `ProgramData`、`posix` 均不转发三场景；
  - L341–381（`test_runner_preserves_search_order_when_resolving_default_directories`）：未修改并保持通过。
- `.ai/tasks/TASK-0189/`：完整任务账本（含首轮失败证据记录、升级解决记录、`REV-0001`/`REV-0002`、最终 V1 通过 `evidence.json`）。

## 语义变更

- 仅在 `process_runner._environment()` 的隔离最小环境中增加：`ssh-keygen` 可执行文件所在目录（紧随 `git` 后、不重复追加）与 `os.name == "nt"` 下非空 `ProgramData` 的显式白名单转发。
- 未抽取多余共用函数或新增标志位/配置开关，直接复用 `shutil.which`、`Path.resolve().parent` 与既有白名单结构；不可信输入校验与 I/O 边界仍保留在既有 `check.environment`、临时目录根及运行目录检查。

## 风险

- **隔离环境最小化风险**：仅新增 `ssh-keygen` 所在目录与 `ProgramData`（`nt` 专用），不导入宿主 `PATH`、用户环境变量或凭据变量；风险低。
- **跨平台 diff coverage 风险**：Ubuntu CI 上 `os.name != "nt"`，新增 `test_environment_forwards_windows_system_variables_only_on_nt` 通过置换 `process_runner.os` 显式覆盖 `nt` 与 `posix` 分支，确保双平台 diff coverage 均达标。

## 证据

- **已验证**：全部 10/10 正式 V1 检查在 Windows 原生环境下通过（`uv run --locked --extra dev python -m aiflow verify TASK-0189 --actor author-procfix`，`subject_commit: f534d25b0f4ba57fc5d2871fb31c26face120fde`）：
  - `contract`、`scope`、`ruff_check`、`ruff_format_check`、`smoke`、`mypy`、`unit_tests`、`regression_tests`、`coverage_xml`、`diff_coverage` 全部 `passed`。
  - `pytest` 全量：`4943 passed, 9 skipped in 1501.01s`（含 `tests/integration/test_private_replay_receipt.py` 全部 `168` 个用例通过、`0` 错误）。
  - 覆盖率：`src/aiflow/process_runner.py` diff coverage `100%`（`11/11` lines，`0` missed）；core 总分支覆盖率 `90%`（`>= 85%`）。
- **未验证**：PR 创建后 GitHub Actions `ai-quality-gate`（含 Ubuntu 运行器）CI 实跑尚未执行，将在推送并开启 PR 后观测。

## 审核问题

1. `src/aiflow/process_runner.py` 与 `tests/unit/test_process_runner.py` 的改动是否完全符合已冻结修订版 `spec.md` 与 `TASK-0189` 允许范围？
2. 正式 V1 `evidence.json`（10/10 通过、0 错误、`process_runner.py` 100% diff coverage、90% core 覆盖率）及新增跨平台单元测试是否足以支撑签发 `APPROVE`？

### 交付边界五项自检结论

1. **目标与关键假设是否清楚**：是。目标明确为解决 Windows 原生 `aiflow verify` 中 `ssh-keygen` 不可见及无 `ProgramData` 退出 `255` 的阻塞，并已通过实证确认。
2. **是否已核实语言标准库与代码库既有复用机会**：是。直接复用标准库 `shutil.which`、`pathlib.Path.resolve()` 与既有 `os.defpath` 去重及 `os.name == "nt"` 显式转发路径，无重复造轮子。
3. **各修改模块是否存在更简单的直接实现**：是（已是最简）。`("git", "ssh-keygen")` 与 `("SystemRoot", "ProgramData")` 均为紧凑表驱动循环，无冗余分支。
4. **新增抽象、分支或配置项是否均有当前明确依据**：是。未新增抽象层或配置项；`ProgramData` 转发有 Windows OpenSSH 实测退出 `255` 及协调方批准（board `#87`）的直接依据。
5. **是否只触及了任务范围边界内的文件**：是。代码与测试变更严格限定于 `src/aiflow/process_runner.py` 与 `tests/unit/test_process_runner.py`（共 2 个非账本文件），账本仅限于 `.ai/tasks/TASK-0189/**` 且不含 `logs/`。

## 推荐结论

**APPROVE** — 全部 10/10 V1 门禁在 Windows 原生通过，跨平台测试充分，变更最小且严格在范围边界内。
