# Task Specification

## 目标

让 AI Flow 自动生成的任务级原始验证日志不再污染 Git 工作区，并清理现有 TASK-0005、TASK-0006 原始日志。

## 范围

- 在 `.gitignore` 增加 `/.ai/tasks/*/logs/`。
- 删除 `.ai/tasks/TASK-0005/logs/` 与 `.ai/tasks/TASK-0006/logs/`。
- 记录 TASK-0007 的本地治理事实和验证结果。

## 非目标

- 不修改 AI Flow 日志生成逻辑。
- 不删除任务级已跟踪证据、批准、事件或规格文件。
- 不处理其他任务目录或仓库外文件。

## 验收条件

1. `git check-ignore` 能匹配 `.ai/tasks/<TASK-ID>/logs/` 下的文件。
2. TASK-0005、TASK-0006 的 `logs` 目录均不存在。
3. `git status --short --untracked-files=all` 不再列出原始日志。
4. `.gitignore` 之外没有产品代码变更。

## 禁止动作

- 禁止 push、merge、deploy、secret export 和 paid external call。
- 删除动作仅限用户已批准的两个精确日志目录，且只执行一次。

## 错误行为

- 任一删除目标解析到仓库外、目标不是预期目录或范围扩大时拒绝执行。
- 不得删除 `.ai/tasks/TASK-0005/` 或 `.ai/tasks/TASK-0006/` 的其他内容。

## 回滚

- `.gitignore` 规则可通过后续反向提交移除。
- 原始日志可由相应验证命令重新生成；已跟踪的任务级 `evidence.json` 不受影响。
