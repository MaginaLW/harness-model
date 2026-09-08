# 维护文档、效果观察与清理审计发布

## 范围与新授权

所有者在只读待办盘点后要求“按照建议完成这些待办事项”。本次按建议完成当前可落地的
文档同步、TASK-0047 已有事实观察和本地清理审计发布；不把缺失的人工分钟/对照/缺陷
观察期伪写成已验证，也不改变 TASK-0028 选项 C、不重开七项历史 BLOCKED、不启动阶段三。

四份文档是维护模式下的 task-free 变更，独立提交于 `9bec84e`。既有清理审计 `d501027`
此前仅获准本地保存，本次是新的外部发布请求；以两个独立 action 记录限定本次 push 与
merge，不复用任何旧动作、不改旧 action 内容。TASK-0047 已 MERGED，仅追加后续动作
审计，不改变其冻结实现、规格、批准绑定和历史证据，也不重新调用 close。

## 可核实的本地检查

- `test_agent_entry_files.py`、`test_approval_overhead.py`、`test_contracts.py` 共
  103 passed（2.57 秒）；未增加只复述文字修改的测试。
- 文档使用精确历史快照：TASK-0047 观察截止 PR #36 的实际合并，不把后续清理或
  本次发布计入该窗口；5 组决定请求与 12 条批准记录分开，累计 N=2 无同类修复前对照。
- 只改文档与 TASK-0047 后续审计，未改源码、测试、Policy、Schema、CI 或维护模式。
- 发布前保留独立复核和 whitespace/任务契约检查；远端 required CI 必须对最终精确
  head 成功后才可正常合并，本地检查不替代远端完整质量门。

独立文档复核已通过：四份文档的事实、相对链接、历史快照和非目标一致。文档提交后，
status 对旧 TASK-0047 的历史 approvals/evidence 显示 stale，因为新增 task-free 文档
不是旧 subject 的纯任务账本差异；任务仍 MERGED、分类 fresh，CLI action 追加与任务
契约验证均通过。该结果不被改写为 fresh，不复用历史 evidence 验收本次文档，也不为
终态历史提示重开任务或请求重复代码批准；本次按自身 required CI 验收。

## 外部交付边界

目标只为 `codex/maintenance-status-sync` 到 main 的一个 PR。CI 全套检查及 85% 总覆盖、
90% diff coverage 阈值、main 保护均不变。使用普通 merge 与精确 head 匹配，不管理员
绕过、不删除分支、不部署，不递归创建发布记录 PR。实际 PR/CI/merge 结果由平台事实
和交付回复证明，不在合并前预写成功，也不伪造通用 action 消费 receipt。
