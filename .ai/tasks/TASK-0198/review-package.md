# Review Package · TASK-0198

## 审核目标

对 `TASK-0198`（分支 `codex/task-0198-aiflow-list`，基线 `ea614587afdbe1a09f910eef837dd30ceb0ad8da`，实现提交 `a93c1d4443aecb1f69032659594c4c03fb795a7e`）进行独立实现审核（`REV-0002` / `--stage implementation`）：裁决 `aiflow list` 命令、`status_service.list_tasks`、单元与集成测试及文档更新是否严格满足冻结规格、`test_import_boundaries.py`、`test_ai_flow_skill.py` 与仓库质量门禁。

## 背景

用户与自动化流程需要一个严格只读的任务列表命令，在不触发逐任务 Git ancestry 检查、状态修复或任何 `.ai/` 写入的前提下，总览当前工作树 `.ai/tasks/` 下的受治理任务与状态分布，并兼容仓库中历史仅含 `logs/` 的目录（如 `TASK-0165/logs/`）及中断创建留下的 `creation_failed.json`。本任务依据冻结规格与设计审核 `REV-0001` 在 `src/aiflow/status_service.py` 新增 `TaskListEntry`、`TaskListReport` 与 `list_tasks`，并在 `src/aiflow/cli.py` 注册 `aiflow list` 子命令。

## 代码地图

仅修改/新增以下 6 个非账本文件（`git diff ea614587afdbe1a09f910eef837dd30ceb0ad8da..a93c1d4443aecb1f69032659594c4c03fb795a7e`）：
- `src/aiflow/status_service.py`：新增 `TaskListEntry`、`TaskListReport`（固定 `schema_version="1.0"`、`kind="aiflow-task-list"`、`to_dict()`、`to_json()` 使用 `ensure_ascii=True` 兼容 Windows GBK 管道编码、`to_text()`）、无标志位内部辅助 `_is_reparse_or_symlink` / `_require_plain_dir` / `_validate_list_filters`，以及 `list_tasks(repository_root, *, states=None, include_merged=False)`；仅导入公开符号 `collect_git_context`、`ALL_STATES`、`TASK_ID_PATTERN`、`task_root`、`read_task_json` 与 `read_task_record_strict`。
- `src/aiflow/cli.py`：在 `build_parser()` 新增 `list` 子命令（`--all` 与可重复 `--state` 互斥，`--state` `choices=sorted(ALL_STATES)`，`--format {text,json}` 默认 `text`），并在 `_dispatch()` 分派至 `list_tasks`。
- `tests/unit/test_task_list.py`：24 项单元测试覆盖空 `.ai/tasks/`、全部 14 个规范状态过滤、默认排除 `MERGED`、`--all`、重复 `--state` 去重、非 ASCII 目标 `to_json()` 转义、`incomplete_tasks`、`logs_only_tasks`、无效过滤拒绝（`TASK_LIST_FILTER_INVALID`）、非普通目录/重解析点/意外文件/`creation_failed.json` 非法 JSON/待物化 `task.yaml.next` fail-closed 拒绝，以及 CLI `--help`/exit 2/`--format json` stderr 错误契约。
- `tests/integration/test_list_command.py`：3 项集成测试在临时 Git 仓库覆盖默认过滤/`--all`/`--state`/子目录/外部 worktree `.ai/` 字节级零写入、待物化 `task.yaml.next` fail-closed 零写入，以及对当前仓库运行 `aiflow list --all --format json` 真实冒烟。
- `docs/operations/quickstart.md` 与 `.agents/skills/ai-flow/SKILL.md`：简要补充 `aiflow list` 只读查询说明。

## 语义变更

- **严格只读与目录分类边界**：`list_tasks` 仅调用一次 `collect_git_context(repository_root).repository_id` 并顺序扫描 `.ai/tasks/` 下匹配 `TASK_ID_PATTERN` 的条目；对符号链接/重解析点/非普通目录 fail closed；存在 `task.yaml`/`events.jsonl`/`task.yaml.next` 时交由 `read_task_record_strict` 严格校验并计入 `counts_by_state`（含 `MERGED`）；仅存在普通文件 `creation_failed.json` 且为合法 JSON object 时计入 `incomplete_tasks`；空目录或仅含普通 `logs/` 子目录时计入 `logs_only_tasks`；其余情形以 `StorageError(..., code="STORAGE_READ_FAILED")` 拒绝。
- **过滤与编码稳健性**：`states` 依据 `ALL_STATES`（覆盖 `TRANSITIONS` 全状态）校验且禁止与 `include_merged=True` 同时传入（`ContractError(..., code="TASK_LIST_FILTER_INVALID")`）；默认排除 `MERGED`，`--all` 包含全部状态。首轮 V1 验证中 `test_list_command_real_repository_smoke` 在 `process_runner` 无 `PYTHONUTF8` 的 Windows GBK 子进程管道下暴露了 `to_json()` 非 ASCII 输出导致 UTF-8 解码失败（同时首轮 `pytest` 于宿主并发重负载下触及 `3000s` `RUNNER_TIMEOUT`）；`a93c1d44` 将 `TaskListReport.to_json()` 修正为 `ensure_ascii=True` 并补充单测后，通过 `aiflow begin`（REC-04）重跑并全量通过。
- **跨模块边界**：零新增跨模块 `_private` 导入，`test_import_boundaries.py` 与 `test_ai_flow_skill.py` 均通过。

## 风险

- **无 `logs/`-only 目录在本工作树内直接存在**：本工作树 git 跟踪目录下无 `TASK-0165/logs/`，该分支逻辑由 `tests/unit/test_task_list.py` 与 `tests/integration/test_list_command.py` 构造真实 `TASK-0165/logs/` 目录充分覆盖。
- **跨平台 CI 交叉验证待运行**：本机 V1 在 Windows 原生环境完成（9 项既定平台/外置 Node 用例跳过），远端 Ubuntu `ai-quality-gate` 将在推送 PR 后执行。

## 证据

- **已验证结果**：唯一有效正式本地原生 V1 验证（`python -m aiflow verify TASK-0198 --actor implementer`，记录于 `.ai/tasks/TASK-0198/evidence.json`，绑定 `subject_commit: a93c1d4443aecb1f69032659594c4c03fb795a7e`）10/10 项全部 `passed`（`contract`、`scope`、`ruff_check`、`ruff_format_check`、`smoke`、`unit_tests`、`regression_tests`、`mypy`、`coverage_xml`、`diff_coverage`）。
- **测试与覆盖率实测**：`5389 passed, 9 skipped in 2887.26s`；核心分支覆盖率 `91%`（门槛 >= `85%`；`cli.py` `94%`、`status_service.py` `94%`）；diff coverage `93%`（`133` 行、`8` 行未覆盖；`cli.py` `100%`、`status_service.py` `93.5%`；门槛 >= `90%`）。
- **静态检查与专项回归**：`ruff check .`、`ruff format --check .`、`mypy`（64 个源文件零错误）、`test_import_boundaries.py`、`test_ai_flow_skill.py`、`test_cli.py`、`test_cli_error_output.py` 与 `git diff --check` 全部通过。
- **复现命令**：`python -m aiflow verify TASK-0198 --actor implementer`。
- **仍未验证的场景**：GitHub Actions Ubuntu `ai-quality-gate` 远端 CI（将在推送 PR 后运行）。

## 审核问题

请独立审核者明确裁决以下问题：
1. `git diff ea614587afdbe1a09f910eef837dd30ceb0ad8da..a93c1d4443aecb1f69032659594c4c03fb795a7e` 是否严格限定在规格批准的 6 个文件，且跨模块仅使用公开符号（`test_import_boundaries.py` 通过）？
2. `status_service.list_tasks` 与 `cli.py` `list` 子命令是否严格只读（零 `.ai/` 写入）、正确处理 `MERGED` 默认过滤/`--all`/`--state`/`creation_failed.json`/`logs`-only（如 `TASK-0165/logs/`），并对损坏任务、待物化替换、符号链接/重解析点与意外文件 fail closed？
3. `evidence.json`（10/10 `passed`，`5389 passed, 9 skipped`，core `91%`，diff `93%`）是否有效绑定当前 `subject_commit` `a93c1d4443aecb1f69032659594c4c03fb795a7e` 且满足冻结规格验收条件？

交付边界五项自检结论：
1. **目标与关键假设是否清楚**：是；目标为提供只读、不调用逐任务 Git 查询、零写入 `.ai/` 的 `aiflow list` 命令，关键假设为当前工作树 `.ai/tasks/` 为权威扫描范围。
2. **是否已核实语言标准库与代码库既有复用机会**：是；直接复用 `pathlib.Path`、`stat`、`os`、`json`、`collect_git_context`、`ALL_STATES`、`TASK_ID_PATTERN`、`task_root`、`read_task_json` 与 `read_task_record_strict`。
3. **各修改模块是否存在更简单的直接实现**：无；新增数据结构与 3 个局部无标志位辅助函数直接服务扫描与过滤契约，无冗余封装或配置项。
4. **新增抽象、分支或配置项是否均有当前明确依据**：是；每个状态分支与错误码均直接对应 `spec.md` 的目录处理、过滤校验与 fail-closed 要求。
5. **是否只触及了任务范围边界内的文件**：是；业务与文档变更严格限于 6 个批准文件，账本记录仅位于 `.ai/tasks/TASK-0198/**`（不含 `logs/`）。

## 推荐结论

`APPROVE` — 实现严格符合冻结规格与公开导入边界，V1 全部 10/10 项检查一次重跑通过（`5389 passed, 9 skipped`，core `91%`，diff coverage `93%`），无未解决 critical/high 风险。
