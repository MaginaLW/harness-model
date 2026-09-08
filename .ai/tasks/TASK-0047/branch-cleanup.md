# 合并后分支清理

## 本次授权与边界

所有者在实现 PR #35 和关闭记录 PR #36 均合并后，另行明确要求“分支也清理一下”。
本记录对应独立的分支引用删除动作，不复用之前明确不含删除的交付批准。
通过现有 CLI 追加 action 批准，不重新打开已 MERGED 的 TASK-0047，不改实现范围、
冻结规格、代码接受或历史证据，也不把本地 actor 或 action 记录说成可信执行器。

核查基线 main 与 origin/main 均为 `65589dae574d7f33b448f78193697ff4524b0da1`。
根 Agent 与独立只读审计分别确认下列 tip 全部是该提交的祖先，且未被工作区占用；
GitHub 无开放 PR。清理只移除引用，不移除提交、文件或工作区。

## 精确清单及恢复映射

| 分支 | 本地 | origin | 保留在 main 历史中的 tip |
|---|---|---|---|
| `codex/ask-obligation-closeout` | 删除 | 删除 | `e10c8a37499c1bf504485478219975c0106e21a6` |
| `codex/ask-obligation-repair` | 删除 | 删除 | `deb05ade0ce29a3a85b6624c35578b5404c445e1` |
| `codex/reduce-human-intervention` | 删除 | 不存在，不执行远端删除 | `c9343c2b948b2373ff34892e79fb85e0dc547a66` |
| `codex/risk-input-closeout` | 删除 | 删除 | `e8944602a2da6d253a1851a81701910d79cdadbb` |
| `codex/risk-input-followups` | 删除 | 删除 | `a98a9249a267156a06d64c7ca1267a6c36ed115e` |

远端以一次 atomic push 和逐 ref 的精确 expected-SHA lease 删除；lease 仅作比较后删除，
没有非空 source refspec、历史替换或无条件强推。远端已变化则整批拒绝；本地随后仅用
`git branch -d`。恢复本地名称可用 `git branch <上表分支> <对应 tip>`；如需恢复远端，
应先重新核对目标不存在及权限，再在获得对应授权后推送恢复，不自动执行回滚推送。

## 明确保留

- `main` 与远端默认分支及其全部保护。
- `codex/maintenance-closeout` 已合并，但仍被独立工作区使用；本地和远端均保留。
- `claude/unruffled-gates-41d3ec` 有未合并提交，同 tip 还被 detached 工作区使用。
- `backup/task-0033-work` 与四个 `pilot/*` 分支均有 main 尚未包含的提交，保留备份与试点。
- 所有注册工作区、工作区内容及既有任务证据均不删除。

本次只在本地提交清理审计，不新增清理分支、PR 或额外推送/合并；不得为发布该记录
循环创建待清理分支。删除结果仅在执行后追加。

## 实际执行与复核

2026-09-08 已完成本次单次动作：四个远端 ref 在同一次带精确 lease 的 atomic push 中
删除成功；随后五个本地分支均以 `git branch -d` 删除成功。没有失败重试或删除其他引用。
该动作不再复用；这是 Agent 核对后的实际执行记录，不是通用批准消费者的自动 receipt。

删除后重新枚举确认：本地剩 8 个分支、origin 剩 7 个分支，恰为上述保留项；
远端 main 仍为 `65589dae574d7f33b448f78193697ff4524b0da1`。三个注册工作区路径与
删除前一致，两个附加工作区的 HEAD 不变。main 的 strict required `ai-quality-gate`、
管理员保护、禁止强推和禁止删除设置均未改变。

`aiflow validate TASK-0047` 通过，任务仍为 MERGED；契约测试 89 passed（7.86 秒）。
只提交本次 action、恢复映射及 CLI 追加的批准/事件/更新时间，不修改代码、配置或旧证据。
此审计提交仅保留在本地 main，远端 main 不推送；最终交付须明确本地领先的审计提交，
不将它说成已发布的实现或 CI 结果。现有实现与已合并任务无需重新关闭。
