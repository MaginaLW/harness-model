# ZCode 准备报告回收与独立核定：2026-10-03

四个指定会话已完成回收核查。ZN-01/03/04 有完整终稿，主体接受并附勘误；ZN-02
消息实际取消、无最终报告。独立审查补齐条件门评估，不冒充 ZN-02 交付。F 仍需新目标
及其后取得的匹配真实报告。本仓核查基线为 `ed4b3e7a57d785b57670eed47170944e3532a832`。
3 名原生 sub-agent 分别只读审核 F、两个外仓、条件门；主 agent 独占取证、记录和提交。

## 来源与回收

仅查询[任务安排](zcode-next-stage-assignments-2026-10-02.md)中的四个 ID。索引 DB/WAL
复制前后源与副本哈希相同。会话 DB 的前两次全窗口检查因并发 WAL 更新拒绝，未查询，
失败原件保留；第三次分开取证：数据库在 WAL 取得前后完整哈希相同，WAL 自己的
before/copy/after 哈希相同。SQLite 仅以只读连接查询副本的指定 session/message/part。
不声明整个源库停止活动或复制绝对原子性，未连接、修复或改写源 SQLite。

回收时刻 `2026-10-03T00:27:53.767471+08:00`。私有材料位于
`<RUNTIME_ROOT>/harness-model-followup-20261003-001/`：失败/成功副本、来源哈希、四份
持久化行、终稿提取、清单和 GET 回执，不入库。没有查询账户配置、凭据或费用表。
UTF-8 提取绑定数据库保存文本，不认证 provider 传输原始字节或真实身份。
`assistant.txt` 是过程及终稿的聚合；正式终稿按最后 `finish=stop` 消息定位。

| 工作包 | 既有会话 ID | 终态 / Singapore 完成时刻 | 终稿字节数及 SHA256 |
| --- | --- | --- | --- |
| ZN-01 | `sess_a4f8e128-e510-4a96-94f9-2ededcc717d7` | stop / 10-02 16:21:48.009 | 15316 / `949567c532501f984dc7dfa58d223afdaee24ab9dc3c00e2efba66cf7cd7d84d` |
| ZN-02 | `sess_2db709cb-d466-4881-b09e-33beaf1bf9ea` | cancelled / 10-02 16:23:03.279 | 无终稿，不把空文件当报告 |
| ZN-03 | `sess_6a7aad63-be2c-4aa2-8004-fd8b69836c70` | stop / 10-02 16:37:29.139 | 10249 / `966e1ca2e45df2460d226bb47a59f3f717507ad50f1aade7f9008cb48c3890f0` |
| ZN-04 | `sess_bff4e119-950a-4508-9138-05479d3a6f4e` | stop / 10-02 16:44:23.555 | 10507 / `166e821578778b313776b5edb8119a40bf29f31462a18afaa3236aa9cf066922` |

ZN-02 只有 user 1/assistant 1；assistant 无 text/tool，错误为 model_request_cancelled、
turnResult=cancelled、retryable=false。取消者和根因 UNKNOWN；索引仍 completed，不能推导
报告完成，reasoning 不作报告。其他三份保存的工具均为 Read（13/18/23 次），分别有
2/1/1 次错路径或读取上限错误，随后更正或分段。未见保存的 shell/edit/write/API/worker
调用；这只证明记录范围内的工具边界。03/04 的第二条 user 是 synthetic Todo 提醒，
timeline 为系统 model_change，不能算第二次人工提示词或新批次。应用元数据记载
GLM-5.3、GLM-5.3-Flash、GLM-5.3-Flash；真实 provider/model 身份未认证。

## ZN-01 勘误与 F

11 次成功 Read 的完整内容与 `cfec0779f52a267f6bfe0fdfee71344ab7d68aa4` 对应文件
规范化文本逐一相等，证明内容版本对应，不证明当时 HEAD。8 份源码/契约/接口仍与本轮
基线相等，3 份状态/安排文档已有追加。Read 保存时段为 10-02 08:19:39.776–08:20:08.033 UTC。
报告列 AGENTS.md 为来源但清单无该 Read；可能来自已加载上下文，证据不足，保持 UNKNOWN。

状态、design 无 subject、implementation fresh passed evidence、context 匹配、expected-hash
消费及“不将准备报告当 F 原件”与源码一致。执行方案采用以下勘误，原件不改：

- Git 关系为 **base→subject→HEAD**，不是只分别检查两者为 HEAD 祖先。
- source_key 仅含 product/location/resolved repository/stage；report_version 派生 version_key，
  acquisition_method 不进入 source_key。
- 工具使用严格 JSON 且不执行内容；绝对路径及认证样式拒绝施于规定引用/路径字段，
  不声明扫描所有自由文本或拒绝一切“反序列化”。

最小单元是新 design-stage 目标：冻结[真实导入验收规格](f-real-import-acceptance-2026-10-03.md)，
经实际 CLI 准入及当前 context 后再取得匹配审查。不能向已 MERGED 或失败历史任务导入。

## 外仓证据与报告勘误

本地 Git 在 10-03 00:27:06 +08 核定两仓 main、净树和 cached upstream 相等。
主 agent 于 00:30:04–00:30:30 +08 仅 GET main/ref、准确 head runs/checks、attempt 1 jobs；
8 份 JSON 实际 exit 0/stderr 空，独立 reviewer 重算字节和 SHA256 与回执一致。
以下依据 API 结果及 step 状态，未复读 job 原始日志，未重跑 workflow。

| 项目 | 本地及远端 main | 本轮准确 SHA 的 CI |
| --- | --- | --- |
| ai-agent-dotfiles | `e93d5b65e9f8089337f0c146a724468870e40566` | [run 36944593176](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/36944593176) attempt 1 SUCCESS；repository gates + 3 shards 的 check/job 集合一致，全部实际 steps SUCCESS |
| r3s-VPS | `513a3d09afda748da053e5ddb7170dd6f33624a6` | [run 36748860600](https://github.com/MaginaLW/r3s-VPS/actions/runs/36748860600) attempt 1 CANCELLED；Windows job 110001982989/runner 21 的 7 步 SUCCESS；POSIX job 110001983313/runner 0/0 步/CANCELLED |

ZN-03 当前 head CI UNKNOWN 由本轮补证解决，不回写为原会话已验证。“实读三层一致”
证据过强：原工具没有读 schema/emitter/registry。独立 reviewer 另核当前 schema 3 的生产、
注册、正负 fixture 和 CI orchestrator 消费一致，历史漂移已修复。
c18-09 原始 completion/route/summary 绑定代码候选
`3897dc4fbe22487b80e30ed6212ffce4779368aa`，11 门/43 套件 PASS；full-validation
8445150 ms（8445.15 秒），8158 秒属于 c17。#181 红样本及 #182 后继收口保留，
不接受“#176–#184 全绿”概括。项目记载真实 Apply/部署尚未执行；S5 setup DryRun
三次 FAIL/零写的原记载保留，本轮未复验。

ZN-04 两笔历史双绿及 c35 Strict 只有项目记载，原会话未读树外原件，不能认证为原始结果
PROVEN。本轮重算四项入口/workflow manifest 哈希一致，它不替代 Strict。
现在 Windows 成功已实证，POSIX 缺执行；恢复 runner 后仍须准确 SHA 的实际完整结果。
本轮不改外仓业务、不操作主机或触发 CI。

第六项统一映射[接入方法](adoption.md#真实任务的执行与收尾)的实现前方案/实现后 diff 评审，
不是 R1-W06、终审或定向复审。I2 按[启动条件](next-stage-start-conditions-2026-10-02.md)
分别核需求、单一可信目标、权限/平台、等价检查、准确 CI、回退和准入。现有收尾不表示
扩仓完成；无新增实质方法缺口，回灌保持 no-op。

## 条件门的本轮独立核定

| 单元 | 结论及下一条件 |
| --- | --- |
| I1 | 已有同仓双 lane/main/guest 重启业务、恢复及原生收尾保留；其他生命周期无选定真实新需求 |
| I2 | 既有试点分别核定，新增可信目标/准入未选；POSIX 恢复不直接等于扩仓完成 |
| E5 引擎采用 | wheel 等基础存在；完整资源分发、非覆盖初始化、身份/Policy/存储/目标 CI 适配需实际目标及设计 |
| E5 provider | 缺实际 adapter、身份/费用/数据、超时/取消/分页/重复结果边界和授权 |
| E5 可信执行 | 缺身份根、服务授权、固定参数、过期/原子消费、凭据托管、不可变审计/恢复 |
| I5 / Phase 3 | 样本充分性/分层/隐私偏差、真实 V3 沙箱损失/回滚、版本化度量合同未冻结，仍 not_started |
| Phase 4 | 缺 Phase 3 退出、稳定接口、量化协调/暂停恢复/集中审批需求，仍 not_started |

来源：[task02 验收](../implementation/task02-runtime-integration.md)、[阶段三输入](../implementation/phase-03-entry-inputs.md)、
[启动条件](next-stage-start-conditions-2026-10-02.md)、[Hooks](hooks.md)。overall.yaml 的旧
Sol/max 与 Sol/high 漂移保留历史；[当前型号规则](model-selection.md#历史记录)明确不恢复
任一固定值，其余门不因此解除。可并行准备样本/V3/度量提案，方向决定、冻结和准入串行。
未定阈值、身份和费用保留未知，不补造充分性或改善结论。历史任务、失败、批准、配置及
三份用户草稿保留，本轮记录仅本地。

## 本地验证与新目标准备

文档候选 `3d6528284bc6e867def4fc8139ef67a41544ae48`、比较基线 `ed4b3e7`：
完整 pytest+branch coverage 在 2026-10-03 00:41:37–01:00:44 +08 实际 exit 0，
3008 passed、1 skipped（Windows 无 POSIX FIFO），89.05% 总覆盖率达到 85%。
`diff-cover --fail-under=90` exit 0、差异无可覆盖行；whitespace exit 0。
前置 contracts 185 passed，lock check、Ruff、format（615 files）、mypy（44 source files）通过。
私有 stdout/stderr、coverage XML、命令/真实退出/时间回执保存在同一运行材料目录，
测试未改本地已有 coverage 文件。本节及最新交接只是结果追加，不再变更执行代码。
这些是本地主检出验证，不替代新任务原生 V2 或远端 required CI。

新隔离分支 `codex/f-real-import-acceptance` 从该候选创建，native start 分配 TASK-0063。
准入先修正本任务自身记录范围，native classify 为 REVIEW/V2；独立技术设计审查 APPROVE，
当前 WAITING_FOR_SPEC_REVIEW，Missing 只有 spec_approval。复制规格的一个相对链接
修正后重新 freeze；先前冻结字节保存为 `preparation/spec-frozen-001.md`，旧 context/Review
保留，新 context 保存为 `preparation/design-context-002.json`。一次重新 classify 因
Git baseline 不同拒绝；decision unit 未改变，既有 classification 仍 fresh，freeze/status
成功，不改 baseline 或降低路由。当前 spec SHA256：
`070b364c23837dade0a91d7c8e6a7a10e2bc7bbcbfb298b296744ce59c35968d`；context：
`2bfa873bda2125336b48b7181ba2a7de1ca568aac435b21af0d1ec4a67fcd605`。

具体新 ZCode 提示词与独立付费获取方案的 revision 002 已保存为私有材料，绑定该目标，
只读、最多一次初始发送、无自动重试/其他 worker/账户模型权限变更；提示词 SHA256：
`c2f846d3913ce80fccb61801a5b160ff1a112ce10a0007a632025ac921fdf640`。
原生规格批准不是该外部动作批准，两项均尚未取得，未发送新会话或执行 F preflight/record。
原生 V2/Review/Gate 和真实发布/close 仍是后续步骤。

补充只读 runners GET 窗口 2026-10-03 00:50:53.235389–00:50:54.632693 +08：
r3s-VPS Linux runner 22 offline、Windows runner 21 online，两者 busy=false。
626 bytes、SHA256 `ec141fe40d976726083d5ce3c2e600018dc185ba083d898620f6fada34541a37`，
实际 exit 0，独立重算与回执一致。在线窗口不证明取消原因，也不替代准确 SHA 的完整 CI；
未恢复主机、重跑 CI 或新增远端发布。
