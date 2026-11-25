# TASK-0193 · 支持 POSIX/Linux 的安全非覆盖初始化（D2.2）

## 目标

在基线 `2eb2d8a6328ccd5d0bb11903d099f5cfb0c021b7`（分支 `codex/d22-posix-init`）上交付 POSIX/Linux `init apply` 支持（D2.2）：新增 `src/aiflow/initialization_posix.py`（`PosixFilesystem`）实现基于句柄、拒绝符号链接（`O_NOFOLLOW | O_CLOEXEC`）与原子 `link`/`unlink`/`fsync` 非覆盖发布的 POSIX 后端，在 `src/aiflow/initialization.py` 按平台分派并保留原有 `WindowsFilesystem` monkeypatch 接缝，同步更新 `tests/unit/test_initialization.py` 中平台不支持用例与 `docs/operations/initialization.md` 文档，并提供覆盖全部分支与实盘 POSIX 集成测试的 `tests/unit/test_initialization_posix.py`。

## 范围

仅允许修改以下 5 个路径（以及 `.ai/tasks/TASK-0193/**` 治理账本，不含 `logs/`）：
- `src/aiflow/initialization_posix.py`（新增）：实现 `PosixFilesystem(api=None)`，提供与 `initialization.py` 一致的句柄契约（`_pin_ancestor`、`open_directory`、`open_file`、`create_directory`、`create_file`、`read`、`write`、`flush`、`identity`、`volume`、`rename_no_replace`、`close`）；全部打开/创建使用 `O_NOFOLLOW | O_CLOEXEC`，`rename_no_replace` 使用 `link(..., src_dir_fd=parent_fd, dst_dir_fd=parent_fd)` + `unlink` + `fsync` 并核验发布后 `volume`/`file_id`/`links == 1`；严格校验子名称（拒绝空串、`.`、`..`、`/`、`\`、`\0`、控制字符、`>255` UTF-8 字节）与绝对路径；通过可注入 `api` 在 Windows 上实现 100% 确定性分支覆盖并通过跨平台 `mypy` 严格检查。
- `src/aiflow/initialization.py`（修改）：保留模块顶层 `from aiflow.initialization_windows import WindowsFilesystem` 及 `_DEFAULT_WINDOWS_FILESYSTEM = WindowsFilesystem` 接缝；新增 `_platform_name()` 与 `_open_filesystem()`（在 monkeypatch 替换 `WindowsFilesystem` 或 `_platform_name() == "nt"` 时返回 `WindowsFilesystem()`，`_platform_name() == "posix"` 时返回 `PosixFilesystem()`，其余抛出 `INITIALIZATION_UNSUPPORTED`）；更新卷类型校验以允许 `WindowsFilesystem`/`PortableFilesystem` 返回 `"NTFS"`、允许 `isinstance(fs, PosixFilesystem)` 返回 `"POSIX"`。
- `tests/unit/test_initialization_posix.py`（新增）：使用伪造 POSIX `api` 在 Windows 与 Linux 上确定性覆盖全部分支与错误路径（符号链接、`st_nlink != 1`、`FileExistsError`、短写、读溢出、非法句柄、关闭失败、不支持平台），并补充 `@pytest.mark.skipif(os.name != "posix", ...)` 实盘 POSIX `preview -> apply -> inspect -> resume -> duplicate -> existing target` 集成测试。
- `tests/unit/test_initialization.py`（修改）：仅更新 `test_unsupported_platform_application_does_not_write`，通过 `monkeypatch.setattr(initialization, "_platform_name", ...)` 模拟未支持平台验证 `AiflowError`（`INITIALIZATION_UNSUPPORTED`）且不修改只读仓库（不改动全局 `os.name`，保持 `require_windows_apply()` 与全部 Windows 测试原样）。
- `docs/operations/initialization.md`（修改）：准确记录 POSIX/Linux `init apply` 支持范围与实现机制，不含任何本机绝对路径或用户名。

已有能力复用与边界说明：
- 复用 `initialization.py` 现有句柄生命周期、内容哈希规划、部分续跑与幂等重放逻辑；仅在系统调用/句柄/子名称与平台能力边界执行防御性校验。

## 非目标

- 不修改 `src/aiflow/initialization_windows.py`、`tests/unit/test_initialization_windows.py`、`src/aiflow/cli.py`、`src/aiflow/verification.py`、`.ai/policy/*`、`.ai/schemas/*`。
- 不修改现有 Windows NTFS 语义、不放宽 `O_NOFOLLOW`/原子非覆盖约束、不增加未请求的配置开关或外部依赖。

## 验收条件

1. `tests/unit/test_initialization_posix.py`、`tests/unit/test_initialization.py`、`tests/unit/test_initialization_windows.py`、`tests/unit/test_node_v2_contract.py` 在 Windows 上全部按预期通过（实盘 POSIX 用例按平台条件跳过并在 Ubuntu CI 执行）。
2. `ruff check .`、`ruff format --check .` 与 `mypy` 零报错通过。
3. 正式运行 `aiflow verify TASK-0193 --actor verifier-v1`，V1 全部 10 项检查原生通过（`core` 总分支覆盖率 >= 85%、diff coverage >= 90%）。
4. 独立设计与实现审核均为 `APPROVE`，`aiflow gate TASK-0193` 通过，PR 及 closeout PR 合入 `main` 且 Ubuntu `ai-quality-gate`（含实盘 POSIX `init apply` 测试）全绿通过。

## 禁止动作

- 禁止修改 `initialization_windows.py`、`test_initialization_windows.py`、`cli.py`、`verification.py`、`.ai/policy/*`、`.ai/schemas/*`。
- 禁止测试中篡改全局 `os.name`，禁止允许覆盖已存在目标或跟随符号链接，禁止提交 `.ai/tasks/TASK-0193/logs/`。
- 禁止跳过独立审核、自审或强推。

## 错误行为

- 当运行环境非 CPython >= 3.11 或缺失必需 POSIX `os` 原语、或遇到符号链接、硬链接 `st_nlink != 1`、目标已存在（`FileExistsError`）、非法子名称/句柄时，必须以明确 `AiflowError` / `OSError` 安全失败且不污染目标目录。

## 回滚

所有改动均位于独立分支 `codex/d22-posix-init`；合入 `main` 前可直接丢弃分支，合入后可通过标准反向 PR 回滚，无需变更不可逆远端状态。
