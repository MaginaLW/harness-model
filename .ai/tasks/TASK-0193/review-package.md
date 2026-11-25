# Review Package · TASK-0193

## 审核目标

对 `TASK-0193`（分支 `codex/d22-posix-init`，基线 `2eb2d8a6328ccd5d0bb11903d099f5cfb0c021b7`，实现提交 `67690043a86840047b27fc81be81f52c7cd523f8`）进行独立实现审核（`REV-0002` / `--stage implementation`）：确认改动严格限定于批准的 5 个 D2.2 文件与 `.ai/tasks/TASK-0193/**`（不含 `logs/`），`initialization_windows.py`、`test_initialization_windows.py`、`cli.py`、`verification.py`、`.ai/policy/*` 与 `.ai/schemas/*` 零改动，保留 `WindowsFilesystem` monkeypatch 接缝与原子 `O_NOFOLLOW` / `link` 非覆盖语义，且本机 V1 全套 10 项验证全部通过。

## 背景

此前 `aiflow init apply` 仅支持 Windows NTFS 句柄后端；在 POSIX / Linux 环境下无法运行真实落盘初始化。本任务在保持原有 Windows 行为及测试接缝完全不变的前提下，新增 `PosixFilesystem` 后端、统一平台分派与卷校验，并更新跨平台单元测试与文档；同时按决策调整 `tests/unit/test_initialization.py` 中的 `test_unsupported_platform_application_does_not_write`，改为 monkeypatch `initialization._platform_name` 避免在 Ubuntu CI 触发真实 POSIX 落盘并保持双端无跳过测试覆盖。

## 代码地图

仅修改/新增以下 5 个非账本文件（`git diff 2eb2d8a6328ccd5d0bb11903d099f5cfb0c021b7..67690043a86840047b27fc81be81f52c7cd523f8`）：
- `src/aiflow/initialization_posix.py`（新增）：实现 `PosixFilesystem(api=None)`（`_pin_ancestor`、`open_directory`、`open_file`、`create_directory`、`create_file`、`read`、`write`、`flush`、`identity`、`volume`、`rename_no_replace`、`close`），全程使用 `O_NOFOLLOW | O_CLOEXEC`，通过 `link` + `unlink` + `fsync` 与发布后 `volume`/`file_id`/`links == 1` 核验实现原子非覆盖发布，并支持注入 `api` 以在 Windows 上覆盖全部分支。
- `src/aiflow/initialization.py`（修改）：保留 `_DEFAULT_WINDOWS_FILESYSTEM = WindowsFilesystem` 接缝，新增 `_platform_name()` 与 `_open_filesystem()`（在 monkeypatch 替换 `WindowsFilesystem` 或 `_platform_name() == "nt"` 时返回 `WindowsFilesystem()`，`_platform_name() == "posix"` 时返回 `PosixFilesystem()`，其余抛出 `INITIALIZATION_UNSUPPORTED`），并将卷校验扩展为按后端接受 `"NTFS"` 或 `"POSIX"`。
- `tests/unit/test_initialization_posix.py`（新增）：使用伪造 POSIX `api` 覆盖全部分支与故障路径（符号链接、`st_nlink != 1`、`FileExistsError`、短写、读溢出、非法句柄/名称、关闭失败、不支持平台），并包含在 `os.name == "posix"` 上运行的真实文件系统集成测试。
- `tests/unit/test_initialization.py`（修改）：更新 `test_unsupported_platform_application_does_not_write` 使用 `monkeypatch.setattr(initialization, "_platform_name", ...)` 验证未支持平台拒绝写入（不篡改全局 `os.name`）。
- `docs/operations/initialization.md`（修改）：记录 POSIX/Linux `init apply` 支持范围与机制，无本机绝对路径或用户名。

## 语义变更

- **POSIX 原子非覆盖初始化后端**：`PosixFilesystem` 使用目录句柄 (`dir_fd`) 与 `O_NOFOLLOW | O_CLOEXEC` 固定父目录并拒绝符号链接；`create_file` 以 `O_CREAT | O_EXCL | O_RDWR` 创建临时文件，`rename_no_replace` 使用 `link` + `unlink` + `fsync` 完成原子非覆盖发布（目标已存在时精确抛出 `FileExistsError`）并校验 `volume`/`file_id`/`links == 1`。
- **平台分派与兼容性保持**：`initialization._open_filesystem()` 优先检测 `WindowsFilesystem is not _DEFAULT_WINDOWS_FILESYSTEM` 接缝以确保原有测试夹具零回归；`initialization_windows.py` 与既有 Windows NTFS 语义未作任何变更。
- **跨平台类型与边界校验**：所有 `os` POSIX 常量/原语通过安全动态查找与可注入 `api` 访问，保证 Windows 与 Linux 下 `mypy` 严格模式均零报错通过。

## 风险

- **跨平台 CI 差异（待远端 CI 交叉验证）**：本机 V1 运行于 Windows，`tests/unit/test_initialization_posix.py:827` 的真实 POSIX 落盘测试按条件跳过（已由伪造 POSIX `api` 实现 `100%` 语句与分支覆盖）；PR 合入前的 Ubuntu `ai-quality-gate` 将直接运行真实 POSIX 落盘用例验证端到端行为。

## 证据

1. **已验证结果（正式 V1 全量通过）**：`uv run --locked python -m aiflow verify TASK-0193 --actor verifier-v1`（记录于 `.ai/tasks/TASK-0193/evidence.json`，绑定 `subject_commit: 67690043a86840047b27fc81be81f52c7cd523f8`）：
   - 全部 10/10 项 V1 检查 `passed`（`contract`、`scope`、`ruff_check`、`ruff_format_check`、`smoke`、`unit_tests`、`regression_tests`、`mypy`、`coverage_xml`、`diff_coverage`）。
   - `pytest --cov=aiflow --cov-branch`：`5313 passed, 9 skipped in 1445.92s`（`core` 总分支覆盖率 `90%` >= `85%`；`src/aiflow/initialization_posix.py` `100%`（268 语句、68 分支全覆盖）；`src/aiflow/initialization.py` `89%`）。
   - `diff_coverage`：Diff coverage **100%** >= `90%`（`281` 行、`0` 行未覆盖；`initialization.py` `100%`、`initialization_posix.py` `100%`）。
   - `mypy`、`ruff check .`、`ruff format --check .`：全部通过。
2. **未验证场景**：远端 GitHub Actions Ubuntu `ai-quality-gate` 工作流（含 `os.name == "posix"` 真实文件系统初始化集成测试，将在开 PR 后执行）。

## 审核问题

请独立审核者明确裁决以下问题：
1. `git diff 2eb2d8a6328ccd5d0bb11903d099f5cfb0c021b7..67690043a86840047b27fc81be81f52c7cd523f8` 是否严格仅触及批准的 5 个文件，且 `initialization_windows.py`、`test_initialization_windows.py`、`cli.py`、`verification.py`、`.ai/policy/*`、`.ai/schemas/*` 均未改动？
2. `PosixFilesystem` 是否严格强制 `O_NOFOLLOW | O_CLOEXEC`、原子 `link`/`unlink`/`fsync` 非覆盖语义、发布后 `links == 1` 与严格子名称校验，且 `_DEFAULT_WINDOWS_FILESYSTEM` 接缝保持完整？
3. `evidence.json`（10/10 `passed`，`5313 passed, 9 skipped`，`90%` core、`100%` diff coverage）与 `.ai/tasks/TASK-0193/` 账本记录是否一致且不含本机绝对路径、用户名或 `logs/` 目录？

### 交付边界五项自检

1. **目标与关键假设是否清楚**：是。目标明确为实现安全原子非覆盖的 POSIX/Linux `init apply` 后端及跨平台测试/文档；关键假设为目标 POSIX 文件系统支持 `O_NOFOLLOW`/`O_DIRECTORY`/`dir_fd` 与硬链接原子发布语义。
2. **是否已核实语言标准库与代码库既有复用机会**：是。直接复用 Python 标准库 `os` / `stat` POSIX 原语及 `initialization.py` 现有句柄规划/续跑/幂等框架，未引入外部依赖。
3. **各修改模块是否存在更简单的直接实现**：无。对称于 `WindowsFilesystem` 的单一 `PosixFilesystem` 类 + `_open_filesystem()` 平台分派是最简直接结构。
4. **新增抽象、分支或配置项是否均有当前明确依据**：是。可注入 `api` 句柄表与 `_platform_name()` 仅用于支持跨平台确定性单元测试，未新增业务配置开关或备用路径。
5. **是否只触及了任务范围边界内的文件**：是。业务变更严格限定于 5 个批准文件，账本变更仅位于 `.ai/tasks/TASK-0193/**` 且排除 `logs/`。

## 推荐结论

**APPROVE** — 5 个文件实现、测试与文档严格对齐冻结规格与安全边界，本地 V1 全套 10 项检查一次通过（`5313 passed, 9 skipped`、core `90%`、`initialization_posix.py` `100%`、diff coverage `100%`），满足独立实现审核通过条件。
