# Task Specification

## 目标

让新贡献者在 Windows、macOS 或 Linux 上能够从干净克隆建立与 `uv.lock` 一致的项目
虚拟环境，并始终通过项目解释器运行 AI Flow；当 `uv` 不可用时，仍提供清晰的标准
`venv` + `pip` 回退路径和可执行的环境自检。同时确保 AI Flow 历史 snapshot 中由 manifest
按字节 SHA-256 绑定的文本文件在任何平台都以 Git blob 的 LF 字节检出，不受
`core.autocrlf` 改写。

## 范围

1. 业务修改文件精确限定为 `docs/operations/quickstart.md` 与根 `.gitattributes`。
2. 增加推荐的 `uv sync --locked --all-extras` 安装路径，且不得修改 `uv.lock`。
3. 保留 PowerShell 与 POSIX 的标准 `venv` + editable `pip` 安装路径。
4. 说明激活环境与直接调用 `.venv` 项目解释器两种可靠入口，避免把系统 Python
   的 `No module named aiflow` 误判为项目缺依赖。
5. 增加 `uv lock --check`、`uv sync --locked --all-extras --dry-run`、`pip check`、
   `aiflow --help` 等本地自检及最小故障定位说明。
6. `.gitattributes` 只为 `.ai/tasks/*/historical-snapshots/**` 声明 `text eol=lf`；不得扩大到
   普通源码、当前 task 记录或其他仓库路径。
7. TASK-0025 snapshot 的 manifest 与其 20 个哈希绑定文件保持字节不变；只修复 Git checkout
   属性，不重算、不替换、不弱化任何摘要。

## 非目标

1. 不升级 Python、pip、uv 或任何项目依赖，不修改 `pyproject.toml`、`uv.lock` 或 CI。
2. 不执行全局安装，不改变用户 PATH、PowerShell execution policy 或系统 Python。
3. 不修改 README 的阶段状态；该更新仍按 Chapter 13.6 推进。
4. 不修改、删除或取消跟踪 `.reasonix/` 内容，也不处理历史 AI Flow 任务状态。
5. 不实现 bootstrap 脚本、包发布、Hook 安装或远程环境配置。
6. 不修改 TASK-0025 的 manifest、historical snapshot 内容、测试断言或 evidence；不得通过
   文本归一化后再比较、跳过 E2E 或更新期望哈希来掩盖 checkout 字节漂移。

## 验收条件

1. `uv lock --check` 返回 0，证明锁文件与 `pyproject.toml` 一致。
2. `uv sync --locked --all-extras --dry-run` 返回 0 且报告无需变更。
3. `.venv` 项目解释器运行 `python -m pip check`、`python -m aiflow --help` 均返回 0。
4. Quickstart 同时包含推荐的锁定安装路径和无 `uv` 回退路径，Windows/POSIX 命令可区分。
5. `python -m pytest tests/integration/test_acceptance_traceability.py -q` 与 Policy 选定的
   V1 验证通过；`git diff --check` 无错误。
6. `git check-attr text eol -- .ai/tasks/TASK-0025/historical-snapshots/h1-fe30565/files/01-task.yaml`
   返回 `text: set` 与 `eol: lf`。
7. 在 `core.autocrlf=true` 的 Windows 工作树中，snapshot 的 20 个文件 SHA-256 全部等于
   manifest；`tests/e2e/test_phase_02_self_hosting_scenario.py` 与完整 V1 均通过。
8. AI Flow contract 与 scope 校验通过，业务 diff 仅含本规格允许的 Quickstart 与
   `.gitattributes`；历史 bundle 文件没有 Git diff。

## 禁止动作

禁止 push、merge、deploy、delete、secret export、package publish、付费或外部模型调用；
禁止修改依赖、锁文件、CI、系统环境、`.reasonix/`、历史 snapshot、manifest 或测试断言。

## 错误行为

若锁文件已过期、同步需要更改依赖、项目虚拟环境损坏、文档命令会修改系统环境，或实现
需要超出两个业务文件，必须停止并重新分类，不得静默升级包、重写锁文件或把系统 Python
当作权威项目入口。文档不得暗示 `uv` 是唯一可用安装器，也不得把 pip 的可用更新提示描述
为项目缺陷。若 `text eol=lf` 不能使工作树字节与现有 manifest 一致，必须失败并保留原始
摘要，不能修改历史 artifact、测试或 expected hash。

## 回滚

通过后续受治理提交还原 `docs/operations/quickstart.md` 与 `.gitattributes` 的本任务差异；
TASK-0026 的任务、分类、规格、事件和验证证据保持追加式，不删除或重写。历史 snapshot
从始至终保持相同 Git blob 与 manifest 摘要。
