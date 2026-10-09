# Review Package

## 审核目标

裁决 TASK-0074 实现提交 `867569c2584c07c2a15d6e63d4fb52230b5fd196` 是否满足冻结规格 `77f08fc66627be4c68315ac5d8e853f335bd6776488cb9e4f948736f16b402f5`：新任务 ID 高于本地与所有本地分支、远程跟踪分支 `.ai/tasks/` 中的编号。

## 背景

`reserve_task_id` 只取本地目录最大编号加一；2026-10-09 在 `claude/simplify-architecture` 上分配出的 TASK-0063 与未合并 `codex/*` 分支上的 TASK-0063～0071 冲突。设计审核 REV-0001 为 APPROVE_WITH_CONDITIONS（条件：`ls-tree --full-tree` 加末尾斜杠；明确失败码并测试失败时不建目录）。

## 代码地图

- `src/aiflow/git_context.py`：新增 `task_numbers_in_refs`，`git for-each-ref --format=%(objectname) refs/heads refs/remotes` 去重后对每个提交运行 `git ls-tree --full-tree --name-only <commit> .ai/tasks/`，取路径末段按 `TASK_ID_PATTERN` 精确匹配；失败码 `GIT_TASK_REFS_UNAVAILABLE`。
- `src/aiflow/storage.py`：`reserve_task_id(..., reserved_numbers=())` 以本地与额外编号的最大值加一，原子创建与重试不变。
- `src/aiflow/task_service.py`：`start_task` 在 `reserve_task_id` 之前收集编号（失败时不创建目录）。
- 测试：`tests/unit/test_storage.py`、`tests/unit/test_git_context.py`、`tests/integration/test_start_command.py`。
- 文档：`docs/operations/recovery.md` REC-01 增加一行说明。

## 语义变更

- `start` 额外运行 1 + N 次只读 git 命令（N 为去重后的分支提交数）；本仓库 72 个编号、0.66 秒。
- 编号可能出现空洞（其他分支或远程跟踪分支已用的编号被跳过），格式不变。
- git 不可用时 `start` 失败，不再只按本地目录分配；`start --recover` 不受影响。

## 风险

- 未 fetch 的远程分支无法看到（文档已提示先 fetch）。
- treeless partial clone 中 `ls-tree` 可能触发懒加载网络访问（REV-0001 RF-004，未处理，记为限制）。
- 分支很多时 `start` 变慢，每条 git 命令仍受 10 秒超时约束。

## 证据

- 已验证：AI Flow V1 evidence `.ai/tasks/TASK-0074/evidence.json`，subject `867569c2584c07c2a15d6e63d4fb52230b5fd196`，run `run-20261009T224509075725Z`，全部检查 passed；共享 pytest 执行 `2290 passed, 1 skipped in 628.14s`，verify 总耗时 631 秒。
- 已验证：总覆盖率 TOTAL 89%（`coverage report --fail-under=85` 通过）；diff coverage 100%。
- 已验证：新增测试覆盖其他分支有 TASK-0009 时分配 TASK-0010、只读取分支树而非工作区、非 TASK 名称被忽略、子目录调用、git 外部目录以 `GIT_TASK_REFS_UNAVAILABLE` 失败、收集失败时不创建 `.ai/tasks`。
- 已验证：mypy、ruff check/format、`git diff --check` 通过。
- 未验证：partial clone 与远程分支极多的仓库；Linux CI 上的运行（随 PR #46 执行）。

## 审核问题

1. `ls-tree` 用法与编号匹配是否能避免误读（如嵌套路径、非 TASK 条目）？
2. 失败时是否确实在创建任何任务目录之前退出？
3. 对既有测试与 `start --recover` 是否无副作用？
4. 剩余限制（未 fetch 分支、partial clone）是否可接受？

## 推荐结论

APPROVE：实现符合规格与设计审核条件，完整验证通过，剩余限制已在文档与本包中声明。
