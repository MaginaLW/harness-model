# TASK-0048 阶段 61 正式收尾

2026-09-21 UTC，本阶段已完成正式 V2、独立实现审查和当前版本 code approval。
实际 CLI 状态为 `APPROVED_FOR_MERGE`；受审本机验证工作区的 Gate 为
`passed=true`、`reason_codes=[]`，保持 `REVIEW / V2`。
这是合并就绪结论，不代表已推送、已合并、I5 或生产阶段完成。

## 固定版本与审查

- Base：`44bda60199c4344220590aff30522022bf3c1064`。
- 业务 subject：`968cc3c354b87671b7c3f8d60a2784ba06c90261`。
- 独立实现审查：`REV-0004 r0001 / APPROVE`，无剩余 finding。
- Implementation context：`94184ac4756cd2ab688c598e79295ec673fc879aa0aed41c000adea3df475e47`。
- 验证 snapshot：`2f359e3b58e54a32ad4fcba79a377cfc2200f6a6a364ec30f595ce6342672889`。
- Final evidence 原始 SHA256：`3dfbf836e0d56c6c96ee2714d39581f3bf5958e4fcfafa6cff42e93918ce9dc5`。

八份既有 ZCode 文档增量已通过明确规格升级纳入补充集成审查，原十个提交的归属、
base 和历史均保留。实际修复一项 P2：门禁自身的 native exit 必须检查，输出文本
断言只作附加检查，不能覆盖非零退出。细节见归属、发现及复核原记录。
当前 code approval 按所有者已有明确委托记录，不冒称所有者亲自检查了新原件。

## 本轮验证结果

第二轮完整 V2 的 12 项常规检查、独立 verifier 检查与 targeted mutation 检查均通过。
unit 为 1320 passed，regression 和 coverage 各为 1945 passed，acceptance 为
9 passed，integration 为 588 passed；Ruff、format、mypy、contract、scope、smoke
通过。标准 coverage 工具及独立复核得到总覆盖率 88.12%，保留 85% 门槛。
diff coverage 保留 90% 门槛，但本次差异没有可统计覆盖行，不能称实测 90% 或 100%。

固定五项 mutation 的 baseline 均退出 0，mutant 均退出 1，全部 killed、无超时；
第二次单次 action 已 consumed 并 recorded。它们只证明 harness 治理防线，
不代替目标 runner 的业务或隔离验收。V2 finalize 保持原 snapshot，只附加当前
实现审查引用，没有重跑或替换检查结果。

## 首轮失败与环境修复

首轮真实 FAILED：unit、regression、coverage 各有相同的 76 个 PowerShell fixture
错误，受控最小搜索路径未包含主机原有的 PowerShell 安装目录。失败原始 evidence
SHA256 为 `f824a7fdc1456423d43356fe73c0fbfacc35d86ffa9dea9abfb3878186e47aa6`；
失败归档、immutable run、首个已消费 action 和五项 killed 结果均保留。
CLI 当时 native exit 为 0，但语义结论明确 FAILED，未被误当通过。

真实进程终止后，按已审查单次方案安装官方 PowerShell 7.6.6 完整运行时到现有默认
搜索目录。658 文件、256625143 字节全部匹配固定 manifest，签名、权限及无 reparse
读回通过。实际受控环境预检 76 passed、exit 0 后才开始第二轮完整 V2。
没有修改 source、Policy、测试、阈值、系统 PATH 或外部 runner 服务。
安装回执 SHA256 为 `5bba85bec3e66708e48ff63e496c827f74ed8dc3f2491e8b31dbc1edcfb9d397`。

## 证据与后续边界

此前 main 同源码双平台 CI、新 BOOT Linux 完整业务与 Windows/Linux 串行恢复的
运维闭环已独立核验；本次治理通过与那些真实运行原件分别成立，未重跑外部 CI。
运维状态仍以各回执记录的观察时间为准，不把历史状态当作实时查询。

部分归属和审查原件为 CRLF，Git 按规则将文本 blob 规范化为 LF。原始 hash 绑定
必须依靠保存的原始字节，Git 文本不能单独替代原件。完整运行证据、失败与成功
归档和日志保留在专用本机验证工作区及其树外证据目录；含本机路径的运行材料不入库。
因此本 Gate 结论针对受审工作区，不宣称干净 clone 自带完整可重放证据，也不豁免
原项目目录中三个用户未跟踪计划文件的 scope 约束。同步仅限本阶段已审查的文件。

CLI 的 spec approval freshness 与 begin 的 subject 比较不一致已记录在
`closeout-begin-binding-001.json`。本阶段按现有更严格检查允许的顺序完成流程，
没有修复该源码问题；后续若处理，应单独进入治理代码任务。I5、推广、推送、合并、
部署及新增外部动作不由本技术收尾结论自动启动。
