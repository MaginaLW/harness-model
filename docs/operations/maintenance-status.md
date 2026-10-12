# 维护收尾与待办

## 当前状态

更新于 2026-10-12。本节是当前状态的唯一摘要；逐窗口的历史记录见文末指针，旧窗口文字不作为当前指令。

**治理模式**：仓库维护模式，task-free 例外已启用；规则以 [AGENTS.md](../../AGENTS.md) 为唯一权威。CI 质量门禁与 `main` 分支保护不放松。

- 常设授权（2026-10-10）按 [AGENTS.md「常设授权」](../../AGENTS.md#常设授权) 执行：限定条件下 Agent 自主推送、开 PR、合并并代为记录批准，其余高风险动作仍逐次决定。

**已完成**

- 阶段一 MVP（`0.1.0`）与阶段二 Chapters 8–13 已于 2026-08-30 完成；源码包收口版本 `0.2.0`，active Policy `2.5.0`（V1/V2 的 pytest 检查共享一次完整覆盖率执行；`impact_scope` 触及治理面的决策单元至少走 REVIEW）。`docs/superpowers/state/*.yaml` 是当时冻结的历史投影，不再更新。
- 已交付工作及其限制分别见[本地辅助工具](local-tools-closeout-2026-09-22.md)、[自托管执行基础设施](self-hosted-runners.md)（历史试点；runner、诊断与证据移交工具已于 2026-10-10 删除）、[E4 启动前收尾](e4-preflight-closeout-2026-09-23.md)；外仓试点按[按需反馈与回灌](feedback-loop.md)处理，无实质问题即 no-op。
- 2026-10-10 架构精简（PR #46）已合并并关闭 TASK-0072/0073/0074：V1/V2 只运行一次完整覆盖率 pytest、`src/aiflow` 净减约 1040 行、删除未接入的工具试点、任务 ID 分配跳过其他分支已用编号。PR #46 以 squash 合并为 `0f5aa4c`，任务证据绑定的原始提交由标签 `archive/claude-simplify-architecture` 保留。未完成的 TASK-0063～0071 所在分支已归档为本地 `archive/codex-*` 标签，未合并。
- TASK-0075 的治理面 REVIEW 下限已由 PR #51 合并，账本已关闭：Policy 2.5.0 覆盖 `.github/**`、`.ai/**`、`src/aiflow/**`、`tools/ci/**` 及 Agent 入口、依赖与 Git 配置文件；准入以当前 Policy 和 CLI 结论为准。
- TASK-0076 已由 PR #52 合并，账本已关闭：退役外部审核导入与 `verify --pytest-temp-root`，合并八处相同的 UTC 时间戳辅助函数，同步退役说明与治理清单。原生 V1 完整验证、两份独立实现审核、Gate 与远端 required CI 均通过；历史任务、失败记录和恢复来源保留。
- TASK-0078 已由 PR #55 合并并关闭：完整克隆内的 CLI 根目录、子目录与 worktree 定位，以及默认 Schema 资源作用域已交付。它是 TASK-0077 的后继，原阻断记录保留；这不提供完整引擎的外仓初始化或资源分发。

## 剩余建设主线

后续按有效能力推进，顺序以 [S0–S5 路线](../superpowers/plans/2026-10-08-confidence-driven-approval-roadmap.md)为设计输入。项目所有者已选择 **B：3-A 低风险建议与校准、3-B 高风险 V3 独立准入和验收**，首场景为本仓自然治理任务的只读建议，首用途已选**追加机器审核，并基于审核结果积累认识**，范围见[置信度反馈设计](../superpowers/specs/confidence-feedback.md)。当前范围的准备与常规实施按 [AGENTS.md](../../AGENTS.md) 准入；样本充分性、统计接受标准、隐私、保留期和风险用途参数尚未全部冻结，路线和用途选择不批准新私密采集、provider 或执行动作。

已具备[固定 HEAD 的账本事实快照](effect-observations.md#固定提交的事实快照)，以及复用当前原生 status 与适用状态 Gate 的[非评分只读建议](review-advisory.md)。
快照保守核对同 task 审核 context 与 review/event 引用，关联状态和子记录计数不提供新验收或独立样本；原失败及历史完整性等 `unknown` 保留。
同一工具的[四目标证据可用性](effect-observations.md#四目标证据可用性)模式复用该快照，区分已投影、白名单中至少一件所需原件缺失、未投影字段和关系未知；已有原值与冲突保留，任务事实覆盖计数不是估计分母或独立样本。
矩阵保持 `method_status=design_pending`、`probability_status=unestimated`、`execution_allowed=false`；[方法候选](../superpowers/specs/readonly-confidence-method.md)不代表 S1 全部冻结或生产评分准入。
建议的 `native_status` 提供 `base_commit`、`subject_commit`、`observed_head` 和受限 `missing_conditions`；`advice_basis` 通过 `advice`、`source` 及 `missing_condition` 或 `state` 记录已有建议的具体依据。
建议固定 `probability_status=unestimated`、`execution_allowed=false`；概率未估计，不给执行权限。
`SOURCE_READ_ATOMICITY_NOT_ESTABLISHED` 明确多次原生读取尚未证明原子一致性，版本投影不代表固定的原子观察窗口。
这些能力属于 S0/S1 准备，不证明生产评分、真实 shadow、模型身份认证、独立样本充分或阶段退出。
数据与方法合同、可靠身份、人时、独立缺陷真值、统一 telemetry、评分/校准、真实 shadow 与宿主接入仍需各自证据和准入。

项目所有者已允许最初评分参考公开排名网站；[初始外部参考工具](benchmark-reference.md)已提供离线配置相对评分、完整原指标/来源/日期、缺失处理、可复算输入 hash，以及 SWE-bench、Aider 和 Arena 的少量示例。多源比较只针对同一声明配置集合；相对分不是本仓成功或检错概率，不认证实际运行身份，也不接入审核路由。真实本仓反馈沿用既有审核与 PR 收尾；不以外部分数替代方法、样本、真值与质量条件。

[审核结果回读](review-feedback.md)已将固定 tracked `HEAD` 的正式账本审核修订、Finding 状态和已有验证原值汇总，并提供 commit/path/blob/locator 原件引用。它复用快照白名单，默认 snapshot/availability 保持不变。[公开 PR 回读](pr-feedback.md)另接受显式选定的 task-free 来源，保留当前描述中的各轮协调者摘要、原生集合数量及所见 workflow 原值；v2 将处置、修复候选和复核引用声明精确关联原 Finding，平铺保留，并对缺来源、候选冲突或角色声明问题提出非评分核对。v1 原报告形状与全部原失败保留，来源包仍为 1.0。两者可并列外部参考；声明关联不认证作者实际采纳、独立复核、actual diff、实际模型配置或 required check 完整性。当前补齐声明处理链与来源核对，模型评分更新及自动审核安排仍未实现，尚未完整评分闭环；原失败与未知继续保留。

[来源与尝试链合同候选](../superpowers/specs/readonly-confidence-data-contract.md)将固定原件、关系依据、缺失和 task-free 标识分别定义；[方法协议候选](../superpowers/specs/readonly-confidence-method.md)与[效果口径候选](effect-observations.md)明确目标单位与估计条件。[追加机器专项审核与反馈候选](../superpowers/specs/supplemental-machine-review.md)承接已选用途，具体化“专项审核→处理→复核→结果反馈”的来源和停止边界。首目标协议按 `review_detection` [具体化](../superpowers/specs/review-detection-protocol.md)：针对本仓自然契约专项审核，预声明候选、契约对象与缺陷类别机会，再核独立正真值及报告匹配。项目所有者已采用粗略研究精度：95% 覆盖，等尾双侧 `alpha=0.05`（每尾 `0.025`），区间总宽 `U-L<=0.20`（20 个百分点）；不是 ±20 个百分点、模型 95% 可靠或能力阈值。有限研究总体、公开来源/职责、相关组选择、30 日窗口、原预算及风险回退已整体采用；实际原件、独立真值/裁定、提示、预算端点及组间条件仍待核定；条件性样本规划只是设计需求，不是实际合格 N、充分性或新预算。已采用规则不新增私密来源或采集，也不构成 3-A/S3 真实准入；原件、实际身份及真值无法证明时保留未知，Phase 3 仍为 `not_started`。

项目所有者已采用[有限研究范围](../superpowers/specs/review-detection-admission.md)，不重复请求同一范围、用途或精度决定。[首个离线数学工具](review-detection.md)按独立合同接受 synthetic 计数，提供已选区间、空样本未知和数值域拒绝；它不把账本条数变成样本，不接入真实原件、模型评分或审核安排。真实数据/质量事实与 `T0/T1` 尚待核定，30 日窗口未启动。

| 能力 | 已有基础 | 剩余建设与验收 |
|---|---|---|
| 数据与效果基线（S0/S1） | task、review、verification、失败 receipts、受限账本/公开 PR 回读与合同提案；首场景已选本仓自然治理任务的只读建议 | 在自然真实边界形成请求→决定→执行→结果来源链；统一费用、返工、缺陷、工具失败和人工介入口径，明确独立样本、身份、缺失、隐私与偏差规则。现有记录数量不证明样本充分或效果提升。 |
| 任务分层置信度（S1–S3） | 能力/概率语义及样本合同提案 | 按模型、任务类型、角色和工具条件估计作者成功与审核检错能力；补样本不足、校准、留出和漂移处理。生产评分与反馈路由尚未交付。 |
| 反馈驱动的多层审核（S1–S4） | 结构化双阶段审核、独立 verifier 与 Review–Fix–Verify | 用实际结果支持追加专项审核、修复和人工升级，定义预算与停止条件；现行 route/V、REVIEW 批准和硬风险规则保持，置信度不产生执行权限。 |
| 最小宿主接入与真实试点（S1–S4） | 受限 observation、拒绝型 wrapper 和 advisory 合同提案 | 选择一个宿主正式支持的接入点，验证动作与授权映射；先影子建议，再对一个已授权低风险场景验证有限处理、停止恢复及可比效果。真实审批接管与人工时间下降尚未证明。 |

依赖顺序为 **S0/S1 基线与合同准备 → S2 离线实现及独立反例验证 → S3 真实影子评估 → S4 单场景试点 → S5 按效果扩展**。准备材料可以继续；共享合同、路线准入、候选整合、正式验证与真实动作依次串行。

[阶段三进入输入](../implementation/phase-03-entry-inputs.md)保留原三门基线：样本门为 `partial`，真实 V3 用例与统一版本化度量均为 `not_met`。B 已采用；3-A 非评分准备可先推进，生产估计与真实 shadow 仍须满足自身样本、数据隐私、方法用途和治理准入，3-B 真实 V3 独立准入。两包尚未完成实际实现准入，Phase 3 仍为 `not_started`；整体完成须两包各自退出并完成共同验收映射。

## 条件性能力

以下能力按真实目标与依赖分别立项，不作为所有低风险准备的前置条件，也不因旧蓝图存在而自动启动。

| 能力 | 启动条件与实际缺口 |
|---|---|
| 完整引擎跨仓产品化（E5） | 完整克隆内的根目录/子目录/worktree 定位与 Schema 作用域已具备；仍须选择确需完整引擎的目标，补非覆盖初始化、新仓库身份、Policy/Schema/模板资源分发、显式风险事实录入及目标 CI 适配。wheel 不提供外仓一键安装，详见[接入指南](adoption.md#完整引擎的跨仓库边界)。 |
| Provider 接入（E5） | 选择确有需要的接口，冻结输入、身份来源、数据、费用、取消与结果生命周期；真实调用另核具体授权。缺可靠来源的模型身份、费用和结果保持 `unknown`。 |
| 固定动作可信执行（E5） | 选择服务动作、资产与身份根；补精确参数/版本绑定、撤回/过期、原子一次消费、结果回执及结果未知时的恢复。现有 wrapper 和本地批准文本不提供此执行能力；本路线可独立于 provider。 |
| V3 高风险验证（3-B） | 选择真实用例，明确安全检查、沙箱、故障注入、dry-run、损失边界及回滚演练；V2、定向变异或低风险影子评估不替代这些证据。 |
| Phase 4 独立编排器 | 依赖整体 Phase 3（3-A 与 3-B）真实退出、稳定接口和实测协调需求；再建设持久队列、锁/租约、资源调度、暂停恢复及跨主机协调。3-A 单独退出不打开此门，当前会话并发上限不等于这些能力。 |

E5、样本、V3 与 Phase 4 的历史设计输入见[合同提案](phase-entry-proposals-2026-10-04.md)；其中历史现场状态、编号和批准仅适用于各自窗口。

## 旧工作线与证据边界

- [七项后续待办](follow-up-backlog-2026-09-22.md)的历史退出条件未全部验收，整体目标未完成；它们不再是默认执行队列。原范围与证据核对见[完整范围核对](follow-up-completion-audit-2026-10-09.md)。
- TASK-0063～0071 未完成，其工作线已归档为本地 `archive/codex-*` 标签，不再推进。若新的真实需求需要其中能力，应先确定当前范围、恢复来源与准入，不能直接续用历史动作。
- `external-review`、`verify --pytest-temp-root` 及 runner/诊断/证据移交工具已退役。F 的旧导入验收及 A/B 选择不作为默认待执行方向；新的报告获取或宿主接入需求须按现有能力重新定义。
- 原失败、SPENT、partial、unknown 结论、用户草稿、既有批准和历史治理编号保持；后继成功或新方案不改写原件。当前批准覆盖以实际 CLI `status` / `gate` 为准，已消费或过期动作不因继续建设而恢复。

**指针**：[执行记录](next-plan-execution-2026-10-08.md) · [完整范围核对](follow-up-completion-audit-2026-10-09.md) · [低干预工作方式](low-intervention.md) · [文档归档](../archive/README.md)

## 历史记录

2026-09 至 2026-10-09 的逐窗口记录已原样移至[维护状态历史记录](../archive/operations/maintenance-status-history.md)。
