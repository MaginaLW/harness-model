# ZCode 下阶段任务安排：2026-10-02

## 最新回读：四项已实际分配

桌面解锁后四项已通过 ZCode 官方界面各提交一次，独立项目/任务索引审计确认归属正确。
下表取证时刻为 **2026-10-02 16:33:04 Singapore（08:33:04 UTC）**；应用状态会变化，
completed 只表示索引状态，报告内容尚未作为正式验收。

| 工作包 | 项目 | 实际会话 ID | 索引状态 |
| --- | --- | --- | --- |
| ZN-01：F 准备 | harness-model | `sess_a4f8e128-e510-4a96-94f9-2ededcc717d7` | completed |
| ZN-02：E5/I5 进入门 | harness-model | `sess_2db709cb-d466-4881-b09e-33beaf1bf9ea` | completed |
| ZN-03：试点/I2 | ai-agent-dotfiles | `sess_6a7aad63-be2c-4aa2-8004-fd8b69836c70` | running |
| ZN-04：双通道/I2 | r3s-VPS | `sess_bff4e119-950a-4508-9138-05479d3a6f4e` | running |

本次新调用的原生批准、四次发送时间、真实 ID/项目、保全与边界见
[实际分配审计](../../.ai/tasks/TASK-0047/zcode-next-stage-dispatch-2026-10-02.md)。
三名原生 sub-agent 分别复核权限/历史保全、项目元数据、提示词/最终记录，主 agent 独占 UI/账本/文档写入。
F、扩仓及 Phase 3/4 实施仍按启动条件准入。以下锁屏时的未提交快照和全部原提示词保留，
不代表目前仍被锁屏阻塞；本轮记录只在本地，未新增远端发布。

所有者本次明确要求安排 ZCode 任务。下列四项是**只读准备工作**，归入实际对应项目；
[启动条件](next-stage-start-conditions-2026-10-02.md)单独记录。ZN-01–04 是工作包标识，不是 AI Flow ID。
实际会话 ID/提交状态按回读追加，不复用过期调用批准，不改账户、模型、订阅、权限或隐私设置。

| 工作包 | ZCode 项目 | 交付 |
| --- | --- | --- |
| ZN-01 | harness-model | F 新目标准入、真实原件交接和绑定缺项矩阵 |
| ZN-02 | harness-model | E5/I5/Phase 3/4 进入门证据、待决条件与分离的后续范围 |
| ZN-03 | ai-agent-dotfiles | 当前试点收尾、第六项方法适用性和 I2 条件核对 |
| ZN-04 | r3s-VPS | 当前双通道 CI/dirty 边界/试点证据和 I2 条件核对 |

四项可并行，只在各自会话输出；协调者复核后另行处理文件。外仓任务不放在 harness-model，
也不重启历史完成任务。当前服务可能消耗额度，本安排不改订阅，不是费用封顶或单次底层 inference 承诺。

## 共同执行边界（每次发送均包含）

只用原生文件读取和会话报告；不运行 terminal/shell/命令/脚本/测试，不改文件、不提交、不 clone/fetch，
不调用外部 API，不启动其他 worker/模型，不自动重试，不接入 provider。不读取账户、密钥、私密配置或原始旧聊天。
无需批准变更弹窗；需执行或写入的步骤停止，列缺项。不能只读确定的事实写 UNKNOWN。
区分源码事实、项目记载、当前/历史实测；任务标题、actor 或 SHA 不能证明模型身份。
报告提供来源相对路径、可确认版本与取证时间，不泄露机器用户名、私有绝对路径或凭据。

## ZN-01 提示词

任务：F 合法目标准备与真实报告交接（只读）。
在 harness-model 项目，读取 AGENTS.md、docs/operations/maintenance-status.md、
docs/operations/next-stage-start-conditions-2026-10-02.md、docs/operations/external-review-import.md，
必要时只读 src/aiflow/external_review.py 及当前 context 定义。E4 已交付，0054–0057/0062 MERGED，F 缺匹配原件。
输出：新 native 目标的准入/合法状态/冻结范围/字段清单；source→target→当前 context 逐字段绑定矩阵，
区分 design/implementation；真实来源/原始字节/受审版本交接清单；preflight→expected-hash record→
追加/no-op/恢复的验收及停止条件；已证实/缺失/UNKNOWN 结论。
不创建 task，不生成或重包装 envelope，不改旧 task/context/source subject，不导入、不产生正式 Review/批准。
本报告是准备提案，不是 F 的目标匹配原件。严格遵守共同执行边界。

## ZN-02 提示词

任务：E5 / I5 / Phase 3 进入门缺口评估（只读）。
在 harness-model 项目，读取 AGENTS.md、docs/operations/maintenance-status.md、
docs/operations/next-stage-start-conditions-2026-10-02.md、docs/implementation/phase-03-entry-inputs.md、
docs/operations/follow-up-backlog-2026-09-22.md 及相关设计入口，按最新核定优先，保留历史。
输出 PROVEN/PARTIAL/MISSING/UNKNOWN 矩阵。E5 分开引擎采用/provider/可信执行；I5/Phase 3 分开
样本充分性/分层/隐私偏差、真实 V3 沙箱损失与回滚、版本化费用/返工/缺陷/工具失败/身份口径，未定阈值列待决。
Phase 4 另列真实 Phase 3 退出、稳定接口及量化协调/暂停恢复/集中审批需求。给最小后续规格、依赖与可并行准备，
不先运行未准入阶段补门。不宣布 Phase 3/4 启动、不评分/路由/采样、不改 Policy/账本/代码/文档、
不调用 provider、不产生正式 Review/批准。严格遵守共同执行边界。

## ZN-03 提示词

任务：当前试点收尾证据与 I2 接入条件核对（只读）。
仅在 ai-agent-dotfiles 项目，读取本项目 AGENTS.md、docs/ZCODE.md（若有）、STATUS.md 或实际权威状态入口，
及其明确关联 CI/验证/试点记录。不把 harness-model 历史版本当本项目当前 head；两个项目 Phase 编号分开。
核对当前可确认版本/状态与原试点问题，Schema/生产端/CI 消费一致性；局部/全量/完整 CI/发布各自版本证据；
两段独立评审方法对下一自然安全任务的适用性；I2 真实需求、目标、权限/平台、等价检查、完整 CI/回退缺项。
仅用已有文件，不 rerun CI、不拉取/修复/安装；实时 Git/API 事实不能只读核实则 UNKNOWN，不从记录推断远端成功。
无新增缺口可 no_op。输出逐项来源和 PROVEN/PARTIAL/MISSING/UNKNOWN、最小建议；
不宣称完整 AI Flow 接入或效率/可靠度改善，不改业务/入口/配置、不创建实施 task。严格遵守共同执行边界。

## ZN-04 提示词

任务：双通道 CI 与当前试点证据 / I2 条件核对（只读）。
仅在当前 r3s-VPS 项目，读取 AGENTS.md、README.md、PROJECT_STATUS.md 或实际权威入口及相关 manifest/试点/CI 记录。
不选历史迁移目录、不操作主机。核对双通道 CI 是否各有同一准确候选 SHA 的 job/step/原始结果；
Strict 全量、专项、本地/项目记载各自边界；既有 dirty/未发布工作；upstream/当前版本可读证据；
第六项独立两段评审适用性；I2 真实需求、权限/平台、等价检查/回退缺项。
历史成功不覆盖当前，零步骤失败不写完整通过；不能仅从文件确认的实时 head/CI/dirty 写 UNKNOWN。
输出 PROVEN/PARTIAL/MISSING/UNKNOWN 与最小建议。不 rerun workflow、SSH、部署、升级订阅、安装，
不改 manifest/业务/入口、不启动 grok/provider/worker。严格遵守共同执行边界。

## 实际提交回读

2026-10-02 本轮核对：ZCode 中已登记 harness-model；ai-agent-dotfiles 和当前 r3s-VPS 已有对应项目。
历史已完成会话未重启。四个提示词均已固定，共同只读边界随每次提示词一并发送。
实际准备发送时 Windows 锁屏，官方界面无法继续；四项均**未提交**，没有本轮 ZCode 会话 ID、
调用成功或验收结果。待桌面解锁后核对准确项目，再逐项发送并追加实际回读；不改本机任务数据库代替提交。

| 工作包 | 准备状态 | 实际 ZCode 会话 ID | 当前阻塞 |
| --- | --- | --- | --- |
| ZN-01 | 提示词就绪，未提交 | 尚无 | 桌面待解锁 |
| ZN-02 | 提示词就绪，未提交 | 尚无 | 桌面待解锁 |
| ZN-03 | 提示词就绪，未提交 | 尚无 | 桌面待解锁 |
| ZN-04 | 提示词就绪，未提交 | 尚无 | 桌面待解锁 |

两名原生 sub-agent 已分别核查进入门/提示词、官方入口及现有项目元数据；最终独立文档审查 PASS。
三份权威入口历史正文、三个用户原稿和两份本地配置保全，链接和 whitespace 检查通过。
本轮仅本地文档提交，不把“提示词就绪”写成 ZCode 任务已创建、阶段实施或远端发布。
