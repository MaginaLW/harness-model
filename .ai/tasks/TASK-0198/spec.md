# Task Specification

## 目标

新增严格只读的 `aiflow list` 命令与 `status_service.list_tasks` 服务，确定性列出当前仓库 `.ai/tasks/` 下的受治理任务摘要、按状态统计数量及合法的残缺/仅日志目录记录，对 `.ai/` 保持字节级零写入。

## 范围

仅允许修改与新增以下 6 个文件（及 `.ai/tasks/TASK-0198/**` 任务账本，不含 `logs/`）：
- `src/aiflow/status_service.py`：新增不可变数据类 `TaskListEntry` 与 `TaskListReport`（固定 `schema_version="1.0"`、`kind="aiflow-task-list"`），以及只读函数 `list_tasks(repository_root: Path, *, states: Sequence[str] | None = None, include_merged: bool = False) -> TaskListReport`。严格复用公开能力：`collect_git_context(repository_root).repository_id`、`ALL_STATES`（与 `TRANSITIONS` 全状态集合一致）、`TASK_ID_PATTERN`、`task_root`、`read_task_json` 与 `read_task_record_strict`，严禁跨模块导入 `_private` 符号。
  - 遍历 `.ai/tasks/` 下匹配 `TASK_ID_PATTERN` 的条目：拒绝符号链接、Windows 重解析点或非普通目录；若存在 `task.yaml`、`events.jsonl` 或 `task.yaml.next`，调用 `read_task_record_strict`（对损坏、状态重放不匹配、待物化替换或未物化风险事实 fail closed）；否则若存在非链接普通文件 `creation_failed.json`，校验其为可读 JSON object 并计入 `incomplete_tasks`；否则若目录为空或仅包含普通子目录 `logs`（如 `.ai/tasks/TASK-0165/logs/`），计入 `logs_only_tasks`；其余情形以 `StorageError(..., code="STORAGE_READ_FAILED")` 严格拒绝。
  - 校验 `states` 均属于 `ALL_STATES`（覆盖 `TRANSITIONS` 全部状态），且 `include_merged=True` 与非空 `states` 互斥（均抛出 `ContractError(..., code="TASK_LIST_FILTER_INVALID")`）。默认过滤掉 `MERGED` 状态任务；`include_merged=True`（`--all`）包含全部状态；`counts_by_state` 统计所有已扫描有效任务（含 `MERGED`）。
- `src/aiflow/cli.py`：在 `build_parser()` 新增 `list` 子命令（`--all` 与可重复 `--state` 互斥，其中 `--state` `choices=sorted(ALL_STATES)`；以及 `--format {text,json}` 默认 `text`），并在 `_dispatch()` 分派至 `list_tasks` 输出 `to_json()` 或 `to_text()`；复用既有 `cli.main()` 的 `--format json` stderr 错误契约。
- `tests/unit/test_task_list.py`：新增单元测试覆盖全部状态过滤、默认排除 `MERGED`、`--all`、重复 `--state` 去重与无效过滤、`incomplete_tasks`、`logs_only_tasks`、空 `.ai/tasks/`、符号链接/重解析点/非目录/损坏任务/待物化 `task.yaml.next`/意外文件 fail-closed 拒绝、文本与 JSON 序列化及 `--format json` stderr 错误契约。
- `tests/integration/test_list_command.py`：新增集成测试在临时 Git 仓库与子目录/worktree 调用下验证 `.ai/` 字节级零写入、各类目录边角路径及本仓真实 `aiflow list --all --format json` 冒烟（含对 `.ai/tasks/*/logs/` 的兼容）。
- `docs/operations/quickstart.md` 与 `.agents/skills/ai-flow/SKILL.md`：简要补充 `aiflow list` 只读查询用法，保持通过 `test_ai_flow_skill.py` 校验。

## 非目标

- 不修改 `.ai/policy/*`、`.ai/schemas/*`、`src/aiflow/state.py`、`src/aiflow/storage.py`、`src/aiflow/task_service.py`、`src/aiflow/gate.py`、`src/aiflow/advisory_service.py`。
- 不扫描跨分支 Git 历史（仅扫描当前工作树 `.ai/tasks/`），不调用昂贵的逐任务 `summarize_task` / Git ancestry 计算，不自动修复损坏任务或清理残缺目录。
- 不在本实施 PR 修改 `CHANGELOG.md` 或 `docs/operations/maintenance-status.md`（留待合并后的收尾 PR），不新增未请求的分页、排序开关或模糊匹配选项。

## 验收条件

1. `.\.venv\Scripts\python.exe -m pytest tests/unit/test_task_list.py tests/integration/test_list_command.py tests/unit/test_import_boundaries.py tests/integration/test_ai_flow_skill.py tests/unit/test_cli.py tests/unit/test_cli_error_output.py -q` 全部通过。
2. `.\.venv\Scripts\python.exe -m ruff check .`、`.\.venv\Scripts\python.exe -m ruff format --check .`、`.\.venv\Scripts\python.exe -m mypy` 与 `git diff --check` 全部退出 0。
3. 真实仓库冒烟 `.\.venv\Scripts\python.exe -m aiflow list --all --format json` 正常退出 0 且对 `.ai/` 零写入。
4. 唯一一次正式本地原生 V1 `.\.venv\Scripts\python.exe -m aiflow verify TASK-0198 --actor implementer` 10/10 全项通过，核心分支覆盖率 >= 85%，diff coverage >= 90%。
5. 独立设计审核（`REV-0001`）与实现审核（`REV-0002`）均为 `APPROVE` 且无未关闭 critical/high 发现，`aiflow gate TASK-0198 --format json` 返回 exit 0（`"passed": true`）。

## 禁止动作

- 禁止对 `.ai/` 写入任何文件、事件或修复动作；禁止跨模块导入 `_private` 符号。
- 禁止执行 `deploy`、`delete`、`secret_export`、`paid_external_call`，禁止绕过独立审核或 Gate 直接推送或合并。
- 禁止提交 `.ai/tasks/TASK-0198/logs/`、本机绝对路径、用户名或机器名；禁止触碰暂缓轨道及未在范围清单中的文件。

## 错误行为

- 当 `.ai/tasks` 或任一匹配 `TASK_ID_PATTERN` 的条目为符号链接/重解析点/非普通目录，或包含损坏的 `task.yaml`/`events.jsonl`、状态不匹配、待物化 `task.yaml.next`、不可读/非 JSON object 的 `creation_failed.json` 或意外文件时，fail closed 抛出对应 `StorageError` / `ContractError` / `StateTransitionError`（意外文件或非普通目录使用 `code="STORAGE_READ_FAILED"`），绝不静默跳过或修改任何文件。
- 当 `states` 含未知状态或 `include_merged=True` 与非空 `states` 同时传入时，抛出 `ContractError(..., code="TASK_LIST_FILTER_INVALID")`；CLI 中 `--all` 与 `--state` 互斥由 `argparse` 以退出码 2 拒绝。
- `--format json` 下遇到领域错误时沿用 `cli.py` 约定，向 stderr 输出仅含 `code` 和 `message` 的 JSON 并以退出码 1 退出，stdout 为空。

## 回滚

- 合入 `main` 前可在工作分支丢弃提交并删除分支 `codex/task-0198-aiflow-list`；合入后可通过标准反向 PR（`git revert`）完整回滚全部改动，不涉及不可逆外部状态变更。
