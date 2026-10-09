# ZCode 下阶段准备任务：实际分配审计

所有者明确要求记录下一阶段启动条件、安排 ZCode 任务并放入对应项目，随后确认桌面已解锁。
本次为独立维护动作审计，不重开 TASK-0047，不复用 2026-09-08 的过期调用批准。
提示词及共同只读边界固定于 `cfec0779f52a267f6bfe0fdfee71344ab7d68aa4`，见
[任务安排](../../../docs/operations/zcode-next-stage-assignments-2026-10-02.md)。

## 原生批准与历史保全

- 原生 `approve TASK-0047 --type action` 仅执行一次，真实退出 0，stderr 为空；批准时刻
  `2026-10-02T08:16:55Z`，新动作 canonical SHA256
  `e700ae22360dce9cfa2cc77e0be4b9e179c3b216dbb57a108575f5bb949a93fb`。
  [动作参数](action-paid-zcode-next-stage-preparation-2026-10-02.json)固定四项、项目映射、原始提示词 SHA、
  一次初始发送、无重试和只读边界；到期 `2026-10-03T00:00:00Z`。
- 原 19 份批准完整保留，追加第 20 份；原 55 条事件原件字节前缀与对象前缀保留，
  追加 event 56 `approval_recorded`、`MERGED→MERGED`。spec/classification 字节不变；
  task 只有 `updated_at` 更新，subject/base/state 等原字段不变，无 pending marker。
- 审计提交 `8ba37b6037d4da5721cdc8e0d79589df24c7ac39` 仅含四个动作/账本文件。
  events 工作原件与 Git blob 仅 EOL 不同，各自字节域的 SHA 不混用。

## 四次实际 UI 发送与项目回读

| 工作包 | 项目 | 初始发送 UTC | 新 ZCode 会话 ID | 08:33:04 UTC 索引状态 |
| --- | --- | --- | --- | --- |
| ZN-01 | harness-model | 08:19:18.632 | `sess_a4f8e128-e510-4a96-94f9-2ededcc717d7` | completed |
| ZN-02 | harness-model | 08:23:03.185 | `sess_2db709cb-d466-4881-b09e-33beaf1bf9ea` | completed |
| ZN-03 | ai-agent-dotfiles | 08:26:25.642 | `sess_6a7aad63-be2c-4aa2-8004-fd8b69836c70` | running |
| ZN-04 | r3s-VPS | 08:30:15.102 | `sess_bff4e119-950a-4508-9138-05479d3a6f4e` | running |

发送日期均为 2026-10-02；Singapore 时间为 UTC+8。官方桌面逐项输入固定 UTF-8 文本，
UI 可访问值与源文本逐字符比对时仅忽略排版空白，四项均匹配。每项初始发送一次，无重发或后续提示词。
SHA 绑定协调者输入原件，不认证 provider 序列化后接收字节。发送时间与 metadata 的 created_at
分别保留，不互相替代；任务标题由应用生成，不能假称含有 ZN 编号。

独立只读审计于 `2026-10-02T08:33:04.975440Z` 核实基线 69 行到 73 行，准确新增上述四项，
全部 archived=0。ZN-04 属于当前项目而非历史迁移目录。源 DB/WAL before/copy/after SHA 一致，
只在副本以只读连接查询 ID/title/workspace/status/created/archived，不连接或改写源 SQLite。
原 literal ZN-token 匹配 false 保留；单独通过真实新 ID、业务标题和精确项目关联核定四项，
不覆盖原始结果或把标题匹配失败伪装为原脚本成功。

私有原件位于 `<RUNTIME_ROOT>/zcode-next-stage-dispatch-001/` 和
`<RUNTIME_ROOT>/zcode-next-phase-metadata-audit-001/{baseline-001,post-send-001}/`。
post-send 原 handback SHA256 `b4384feb583bdc4645988f9c4c3f9f141032312576e1b1e3ce11b4a72b06d73b`；
独立关联说明 SHA256 `05d12d027216fec3d98ce878e64ebfc6c5f954f350a3a170a6603ff5531bff36`。
原 prompt、metadata 副本和运行日志不入库。

## 结论与实际限制

四项已实际分配，项目归属和 ID 已核定。completed/running 是应用索引快照，不是报告内容、
实际执行合规或阶段验收 PASS；本次没有读取这些新报告作正式 Review，也未把准备报告作为 F 原件。
F 仍需合法新目标及匹配报告；E5/I5/Phase 3/4 仍按[进入门](../../../docs/operations/next-stage-start-conditions-2026-10-02.md)决定。
UI 只观察到 harness 两项 GLM-5.3、外仓两项 GLM-5.3-Flash 标签，真实身份/费用/底层 inference 次数 UNKNOWN。
协调者没有改变账户、模型、订阅、权限或隐私设置，没有批准权限弹窗，也未重启旧完成会话。
本 batch 已人工登记一次执行，不能再用它安排新任务；现有系统没有认证或原子消费通用 action 批准。
未通过 wrapper 授权执行，未重新 close、运行完整 CI、发布或降低任何门禁。
