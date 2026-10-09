# Task Specification

## 目标

`aiflow start` 分配的新任务 ID 大于本地任务目录与所有本地分支、远程跟踪分支中 `.ai/tasks/` 已出现的最大编号，避免并行分支各自分配同一 ID、合并时互相覆盖任务账本。

## 范围

- `src/aiflow/git_context.py`：新增只读函数，列出 `refs/heads` 与 `refs/remotes` 指向的提交，并用 `git ls-tree --name-only <commit> .ai/tasks/` 收集其中符合 `TASK-NNNN` 的编号；git 调用失败时以现有 git 错误码拒绝，不静默退回。
- `src/aiflow/storage.py`：`reserve_task_id` 接受额外的已占用编号，新编号取本地目录与额外编号中的最大值加一；原子创建与并发重试逻辑不变。
- `src/aiflow/task_service.py`：`start_task` 把上述编号传给 `reserve_task_id`。
- 测试（`tests/**`）：单元测试覆盖编号合并与 git 收集；集成测试在临时仓库中构造另一分支已有更高编号的任务，验证 `start` 跳过它。
- `docs/operations/recovery.md`：如有描述 ID 分配的段落则同步一句说明。
- `.ai/tasks/<本任务>/**`。

## 非目标

- 不改变任务 ID 格式、schema 或已有任务记录；不处理已经发生的撞号（TASK-0063～0071 在其他分支上，本仓库未复用）。
- 不扫描未 fetch 的远程状态，不访问网络；不执行 push、merge、deploy、delete 或任何外部动作。

## 验收条件

- 临时仓库中另一分支含 `.ai/tasks/TASK-0009/` 且本地目录最大为 `TASK-0002` 时，`aiflow start` 分配 `TASK-0010`。
- 没有其他分支或其他分支编号更低时，分配结果与现状一致。
- git 不可用或命令失败时 `start` 失败并给出 git 错误码，且不创建任务目录。
- 完整质量检查通过：全量 pytest 带 `--cov-fail-under=85`、diff coverage ≥90%、ruff check/format、mypy、`git diff --check`；AI Flow `verify` 与 `gate` 按 CLI 结论通过。

## 禁止动作

push、merge、deploy、delete、secret_export、paid_external_call；不修改其他任务目录。

## 错误行为

- git 输出无法解析或命令失败时拒绝分配，而不是只按本地目录分配。
- 引用中不符合 `TASK-NNNN` 的条目被忽略。

## 回滚

`git revert` 本任务实现提交即可恢复原分配方式；已分配的 ID 不受影响。
