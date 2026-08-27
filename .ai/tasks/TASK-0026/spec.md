# Task Specification

## 目标

让新贡献者在 Windows、macOS 或 Linux 上能够从干净克隆建立与 `uv.lock` 一致的项目
虚拟环境，并始终通过项目解释器运行 AI Flow；当 `uv` 不可用时，仍提供清晰的标准
`venv` + `pip` 回退路径和可执行的环境自检。

## 范围

1. 唯一业务修改文件为 `docs/operations/quickstart.md`。
2. 增加推荐的 `uv sync --locked --all-extras` 安装路径，且不得修改 `uv.lock`。
3. 保留 PowerShell 与 POSIX 的标准 `venv` + editable `pip` 安装路径。
4. 说明激活环境与直接调用 `.venv` 项目解释器两种可靠入口，避免把系统 Python
   的 `No module named aiflow` 误判为项目缺依赖。
5. 增加 `uv lock --check`、`uv sync --locked --all-extras --dry-run`、`pip check`、
   `aiflow --help` 等本地自检及最小故障定位说明。

## 非目标

1. 不升级 Python、pip、uv 或任何项目依赖，不修改 `pyproject.toml`、`uv.lock` 或 CI。
2. 不执行全局安装，不改变用户 PATH、PowerShell execution policy 或系统 Python。
3. 不修改 README 的阶段状态；该更新仍按 Chapter 13.6 推进。
4. 不修改、删除或取消跟踪 `.reasonix/` 内容，也不处理历史 AI Flow 任务状态。
5. 不实现 bootstrap 脚本、包发布、Hook 安装或远程环境配置。

## 验收条件

1. `uv lock --check` 返回 0，证明锁文件与 `pyproject.toml` 一致。
2. `uv sync --locked --all-extras --dry-run` 返回 0 且报告无需变更。
3. `.venv` 项目解释器运行 `python -m pip check`、`python -m aiflow --help` 均返回 0。
4. Quickstart 同时包含推荐的锁定安装路径和无 `uv` 回退路径，Windows/POSIX 命令可区分。
5. `python -m pytest tests/integration/test_acceptance_traceability.py -q` 与 Policy 选定的
   V1 验证通过；`git diff --check` 无错误。
6. AI Flow contract 与 scope 校验通过，业务 diff 仅含本规格允许的 Quickstart 文件。

## 禁止动作

禁止 push、merge、deploy、delete、secret export、package publish、付费或外部模型调用；
禁止修改依赖、锁文件、CI、系统环境和 `.reasonix/`。

## 错误行为

若锁文件已过期、同步需要更改依赖、项目虚拟环境损坏、文档命令会修改系统环境，或实现
需要超出 `docs/operations/quickstart.md`，必须停止并重新分类，不得静默升级包、重写锁文件
或把系统 Python 当作权威项目入口。文档不得暗示 `uv` 是唯一可用安装器，也不得把 pip 的
可用更新提示描述为项目缺陷。

## 回滚

通过后续受治理提交还原 `docs/operations/quickstart.md` 的本任务差异；TASK-0026 的任务、
分类、规格、事件和验证证据保持追加式，不删除或重写。
