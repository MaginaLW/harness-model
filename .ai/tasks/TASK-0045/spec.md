# Task Specification

## 目标

通过仓库级忽略规则防止根目录 `.claude/worktrees/` 的检出副本在新克隆中被误纳入版本控制。

## 范围

- `.gitignore` 增加根目录锚定的 `/.claude/worktrees/`。
- `docs/operations/maintenance-status.md` 记录本配置修复的交付状态与验证入口。
- 当前 task 的追加式事实、规格与验证证据。

普通文档状态修正已在本 task 的 base 提交独立交付；这里的文档修改仅同步本配置的使用与验证。
改动是低影响、可由 Git 恢复的路径忽略配置，不改变 AI Flow 引擎、权限或 CI。
Git 未跟踪路径的可见性确实变化，因此声明 behavior_changed 与 regression_risk，
由当前 Policy 确定验证等级。

## 非目标

不删除、移动或整理任何工作区、分支或文件；不修改本机 exclude、Git hooks、Policy、
schema、CI 或源码；不合并 ASK 候选分支，不处置 TASK-0028，不改写其他任务记录。

## 验收条件

- `git check-ignore --no-index -v .claude/worktrees/probe/file.py` 的匹配来源
  必须是当前受跟踪的 `.gitignore`，而不是本机 exclude。
- `.claude/skills/ai-flow/SKILL.md`、`.claude/settings.json`、
  `docs/.claude/worktrees/probe/file.py` 不被本规则忽略。
- 原始工作区仍在，原工作区状态不改变；上轮记录分支的 TASK-0044 Gate 仍可复核。
- 完整 Policy 验证通过，总覆盖率至少 85%，适用的 diff coverage 至少 90%，
  whitespace、Ruff、format、mypy 和最终 Gate 均通过。

## 禁止动作

push、merge、deploy、delete、secret_export、paid_external_call。读取远端状态不是外部写入授权。

## 错误行为

若规则会隐藏根目录工作区副本以外的配置/源码，应修正规则后重新验证。
若需要删除、移动工作区或改变治理/权限，停止该动作并重新评估任务范围与所需授权。

## 回滚

以新的 Git 回退提交恢复新增忽略规则及关联说明；保留本任务的批准、证据和事件。
本任务不触碰工作区内容，无需从备份恢复源文件。
