# S1 合同适用关系、审核预算与残余问题补充候选

日期：2026-10-09。版本：`s1-compatibility-review-budget-v0`。状态：可评审普通文档准备；不是新 Task 规格、生产协议修订、执行许可或 3-A/3-B 正式采纳。

本稿补齐[统一合同提案](2026-10-08-review-confidence-contract-proposal.md)与[非评分状态解释设计](2026-10-08-advisory-status-explanation-design.md)之间的适用关系、审核停止后的交付格式，以及原生验收与独立诊断动作的区别。原[分阶段计划](../plans/2026-10-08-confidence-driven-approval-roadmap.md)、进入门、冻结源码/测试/合同原件、FAILED/SPENT 和质量门保持；本稿不修改它们。

## 1. 输入版本与事实边界

| 输入 | 固定 pin 与本次核对范围 | 可支持与不可支持的结论 |
| --- | --- | --- |
| 分阶段计划 | 文档 SHA256 `d2c84e0823705e4a61d8170676568a86bbe3a8085929dc2deaa431f5faf3e26e`，20911 bytes | S0–S5 依赖、现行门及非评分设计的排序；旧“尚未实施”只属其写作窗口。 |
| 统一合同提案 v0 | 文档 SHA256 `d9f6c1cd4828b9381b95d310bfaccc13a1b32a9d4da3912cdcf468b612a97ff1`，21960 bytes | 四类设计输入、CreateNew/shadow 候选、集中待定参数；不是当前实际接口或授权。 |
| 非评分设计 v0 | 文档 SHA256 `c6476576c50ecafa9bc4326691b30ff8643b7204e7d3a24387225b97a4a9862a`，21953 bytes | 固定记录解释、六类建议、22 synthetic 设计例子及 CreateNew 后移；候选文字不替代冻结技术合同。 |
| TASK-0071 实际 owner 规格 | 逻辑路径 `${TASK71_OWNER}/.ai/tasks/TASK-0071/spec.md`，working raw SHA256 `0f519ee5d853e3dc1268386081129d4610a16f837675483320d04b0ca183673e`，12297 bytes；本次全文只读 | 选中003合同、唯一 source DU、14 required、85/native B90/累计 F90、非目标及准入边界；两路非作者静态核对所见，本例 raw SHA256 与实际 native task.yaml 的 frozen_spec_sha256、approvals.json 相应 spec 字段同值。读件 pin 只固定本次读取输入，本身不认证或替代原生冻结/批准，不据此判失效或重复请求。 |
| TASK-0071 实际 owner 源码 | 逻辑路径 `${TASK71_OWNER}/src/aiflow/advisory_status.py`，working raw SHA256 `da181a0772f546a71ac6d9373d58f3af791baf6b172744bb15961f22bc501a1e`，89122 bytes；只读协议字段、常量和 public API 局部 | 所选模块的实际字段/API及固定无效果输出；没有 import、调用 API、执行测试或审查全部调用路径。 |
| 执行记录 | [执行页](../../operations/next-plan-execution-2026-10-08.md)的前45行固定窗口；按LF连接并保留末尾换行的选中内容 SHA256 `2df2a7982100ee1953a9ce41da33c82f696391ac00c18d80f6088ff174671e9b` | 记录一次实际 V2 的12/14、格式/集成失败、累计比较未运行、诊断尚待单独决定；不是本稿重新核定原生终态。 |

本次主 agent 另提供原生只读窗口 `a58bb0`：owner HEAD `a2237c2a78acb08144810e65f32a65e9b6eeec4f`，subject `589843a8beab11616c1dc3027cb64f6fa3d20388`，FAILED/REVIEW/V2、classification fresh、既有批准 current、evidence stale、Missing `retry_reason_or_escalation`，dirty 限定 private evidence/context。该信息来自主 agent 的实际读取，不是本作者新执行的 CLI，也不保证以后仍然当前。本稿不拿主检出缺席的源码替代实际 owner，不将安全 Doc foundation 的 clean 当作 owner clean。

原提案中 Task69 的 `c9e0132933f894ed5c684af08952fd535e863fc5`、“当前等待 spec”属于批准前设计例子；后继 approve/begin 及失败窗口按各自原件保留。不回写旧文字，也不将该例子作为现在重复请求规格批准的理由。

## 2. 三层合同的适用与兼容映射

| 层级/版本 | 场景与 mode | 输入/输出与效果 | 与其他层的关系 |
| --- | --- | --- | --- |
| 四类合同提案 `s1-contract-proposal-v0` | 审核升级、能力概率、样本效果、adapter授权四流；其中 CreateNew 是未来动作候选，建议输出拟用 shadow | 数据、方法、预算、隐私、动作实例尚待定；拟 execution_allowed=false、permission/ledger effect=none | 提供方向和问题清单；不把其 shadow 字样称为已经运行 S3，不将 CreateNew 视为已选执行目标。 |
| 非评分设计 `advisory-status-explanation-design-v0` | 固定已有记录解读，offline_advisory | 候选 envelope/来源关系、六类建议、保留 unknown；无分数、无执行效果 | 收窄一个准备单元；CreateNew 真场景后移 S4。没有因此采纳全部3-A、冻结统计参数或放宽旧门。 |
| TASK-0071 选中003技术合同与固定 source | 纯内存 `explain_status_snapshot(envelope_utf8: bytes, source_blobs: Mapping[str, bytes]) -> bytes`，offline_advisory | 实际14字段 envelope、17字段 output及闭合reader/ref/oracle；严格拒绝额外/错型字段。源码运行时要求实际 bytes 与普通 dict[str, bytes]，不因签名注解接受任意带行为 Mapping | 规格中的003正文、API/reader/cases/final-oracles及其 pins是此source的技术依据；不从本稿生成新的输入协议或扩大 DU。 |
| 后续 S3/S4 实际能力 | 自然真实影子观察或已核准宿主动作 | 需要对应数据/窗口/质量、正式接入、真实权限和结果；尚不能由上述无分数解释证明 | 独立准入与验收。当前没有自动mode转换、执行器、授权消费者或正式路线采纳。 |

### 2.1 设计文字到实际字段的区别

| 设计概念 | 当前 C71 选中接口的静态核对 | 兼容约束 |
| --- | --- | --- |
| purpose 与 mode | 输入 purpose 是含 mode=offline_advisory、name=offline_status_explanation、stage、scope_refs 的对象；输出 mode/purpose 是固定顶层值 | 不把旧提案的 mode=shadow 文本直接送入本协议；不自动把它转换成实际S3。 |
| 输出 binding / existing request | source 使用 input_binding、existing_request_refs；另有 source_assurance、input_errors，共17顶层字段 | 设计表的概念名不是可直接互换的JSON key；不能通过本稿给冻结API添加字段。 |
| 来源标记与覆盖 | record_origin 与 input_source_kind 分开；source_assurance 固定 supplied_bytes_and_declared_provenance | real_snapshot、current/stale及hash只描述供给字节和报告声明；模块不认证生产者、时钟、真实授权或live current。 |
| 原生状态与恢复 | 输入 native_status/native_gate 是有availability/source_ref/projection/error_ref等的选择结构；coverage按对象、类型、window与引用关联读取 | 不复制原生freshness矩阵、不计算新native Missing/Gate；保留字面值和用途限制，recovery原文不执行。 |
| 问题与建议 | interpretation_question是有类型、依赖和各类引用的列表；建议可分问题 | 本稿的说明case和审核包不是可直接调用的envelope；关系不支持就保留unknown，不能靠文字或布尔值提供覆盖。 |
| 动作 | action_references仅提供描述/批准/使用/终态等引用 | 外部诊断机制没有因为本稿而成为产品API、native execute/consumer或新action namespace。 |

14字段为 design_version、record_origin、subject、purpose、snapshot_binding、source_inventory、native_status、native_gate、native_coverage、action_references、request_references、scope_references、result_references、interpretation_question。17字段为 design_version、record_origin、mode、purpose、execution_allowed、permission_effect、ledger_effect、probability_status、source_assurance、input_references、input_binding、advice_items、native_constraints、existing_request_refs、unresolved、stop_reasons、input_errors。此列举只说明已读source的闭合形状，不是重新定义类型、reader关系或限额。

当前source的固定输出仍是 execution_allowed=false、permission_effect=none、ledger_effect=none、probability_status=unestimated。规格规定无文件/进程/网络/native/账本/权限效果；本次静态核对不替代完整隔离、必需检查或验收。

C71 显式源码范围仅为 `src/aiflow/advisory_status.py`。B中五件安全材料分别为三份unit/边界或integration测试、一份fixture及 `docs/operations/advisory-status.md`，均已在base，不是本source DU之后可改的路径。本稿不修改这些F5原件、003合同、源码、Policy/Schema或task。本次V2原14/85/native B90/原F90仍全须成立；已经完成的源码候选和失败验证不等同S2退出。

## 3. 有界审核预算与职责合同候选

本节补可评审的引用/停止/交付格式，不建立预算服务或新的Policy。没有默认时间、费用、样本量或额外执行次数。引用已有授权上限；源文件、范围或风险变化仍按实际原生准入，不借“复核”获得新动作或重试。

### 3.1 预算来源与独立职责

| 记录项 | 应保存的来源事实 | 缺证处理 |
| --- | --- | --- |
| 范围与阶段 | 当前问题、候选版本、spec/Policy及允许读取/修改范围的已有引用 | 只处理已明确范围；不把scope unknown扩成默认允许。 |
| budget_source_ref | 已有审核安排、具体动作批准或费用上限的分别引用；预算适用的是哪一种工作 | 未定值标design_pending，已有规则缺事实标unknown；不将动作预算当审核轮数。 |
| 角色与所有权 | 作者/专项非作者/残余复核/协调者，各自独占材料；独立性事实及unknown | 多线程/不同actor不自动证明错误独立；人数不是概率或票数。 |
| 已观察投入 | 实际审核轮、工具/时间/费用来源及观察窗口 | 未知不补0；机器耗时、审批条数不换算人的分钟。 |
| 当前剩余范围 | 哪些已解决，哪些发生了实质变化，哪些仍待复核；已知上限和已花事实分列 | 不根据unknown计算剩余数值或推定无限预算。 |
| 停止与恢复来源 | 本阶段停止条件、可以继续的独立工作，以及具体执行已有次数/时限限制 | 没有新grant不能开启受控动作；不恢复spent。 |

统一提案第2节的候选编排为一批初始专项审核加一次受影响残余复核。本稿保留该候选形状：首轮各审核流按明确问题和独占材料工作；作者修复；非作者针对修复实际影响及接口关联复核一次。它不是给任意既有动作追加一次重跑，也不覆盖原规格要求的正式Design/Implementation Review、独立Verifier和完整质量检查。

协调者统一共同术语/接口及残余包，作者不能把自查标独审；非作者不抢写源文件/账本/refs。不为完成记录新增每轮用户签字。若既有安排已经覆盖预算，直接在范围内处理；若原安排没有数值但普通可恢复文档工作已获准，不把本表制造为额外审批门。

### 3.2 停止与升级分类

- 无新实质问题，或只剩已明确的人类决定：停止重复扩大审核，提交残余包；已授权独立工作继续。
- 出现新范围、风险、Policy或无法验证的关键事实：停止依赖路径并列具体变化，不用原批准/高信心填补。
- 已有审核/工具/费用上限耗尽，或受控动作已过期/撤回/消费：保留原事实，不自动延期或重试。未定的未来预算先保留为候选参数，不推导新的支付/执行许可。
- 技术分歧先固定可检验预期、来源和影响；范围内专项审核/修复后仍残留的方向/权限/风险接受问题才集中交人。
- 机械缺项、可复核状态投影差异和普通实现细节由机器处理。真实spec/code/动作或互斥业务方向决定须有当前实际来源；native Missing字符串本身不是人工请求清单。
- 来源或模型身份/结果裁定unknown只是证据限制，不能自动变成新human Missing、能力失败或冷启动分数。

### 3.3 停止后残余问题包

这是普通说明格式，不是新Schema、第二账本或新门禁；不给旧原件回填字段。

| 项 | 最小具体内容 |
| --- | --- |
| 固定范围 | 受审版本/阶段、输入引用、scope及本次角色/预算来源；未得值附原因。 |
| 已解决项 | 原问题、修复/证据、实际复核覆盖与限制；不抹掉原失败或Finding。 |
| 残余技术项 | 精确争议、可检验预期、影响、预算/来源限制；区分已知失败与未知根因。 |
| 残余决定项 | 实际所需决定类型、对象/版本/范围、已有有效覆盖或缺口来源、推荐及影响。 |
| 未知项 | 缺何来源、为何不可得、是否有获准补证路径、受影响依赖；无新采集默认许可。 |
| 已有问题引用 | 同一真实请求/决定的关联和仍未答事实；没有可信关联不按文本相似去重。 |
| 依赖与独立下一步 | 哪条路径等决定/事实、哪些已有授权工作可并行；每项建议不等于执行。 |
| 停止/恢复边界 | 所用停止依据、未来具体动作/新范围准入需求；保留取消、partial、unknown、spent。 |

同一时间可决定的实质问题集中呈现，实际批准类型与绑定仍分别记录。不能提前批准尚未完成的代码，也不能把合并Gate、技术复核、历史成功或本稿候选当作新的动作授权。

## 4. 原生验收、独立动作与执行能力的正交例子

以下三条全部标记 `record_origin=synthetic`，只用于合同语义复核，不是C71实际fixture、完整public API输入、真实grant、动作消费者或已执行诊断。记录里出现原生术语不提供权限，解释结果始终保持offline_advisory/no effects/unestimated。例子不硬编码第二状态机，只保留假设已提供的不同层事实。

| Case | 设定的来源事实 | 可评审解释 | 不可推导的结论 |
| --- | --- | --- | --- |
| O1：只有诊断提案 | 原生报告FAILED、既有批准current、evidence stale、Gate拒绝、Missing=retry_reason_or_escalation；另有新诊断提案，matching grant不存在 | 原生各值保留。可以解释已有机器准备和精确动作决定仍未完成；必要材料齐备才呈现其真实独立决定。授权/能力未核时保留unknown | 不把native Missing改成action_approval；不重复要求有效spec；不启动诊断、consume旧action或称全V2已可重跑。 |
| O2：另有匹配决定 | 原生报告同O1；另假设存在当前精确诊断决定，范围/版本/时限覆盖仅该诊断 | 如来源/关系可支持，只描述该报告的窄覆盖；原FAILED/stale/Gate和Missing不变。实际资源/actor/正式executor/consumer/关闭能力若未核仍分别unknown | grant不令task自动离开FAILED，不证明executor存在或V2/累计diff通过；本产品仍execution_allowed=false，不伪造native consumed或新evidence。 |
| O3：旧action已消费 | 原生报告同O1；旧full-V2 action已spent，另提案要求沿用它 | 拒绝复用该动作路径，保留消费/失败；独立且已授权的文档/诊断材料准备可以继续 | 不因新审核、当前有效spec、subject不变或coverage达标复活spent；不沿用旧grant做新节点/stack采集。 |

每条至少分开四个问题：原生任务/验收状态；所需具体动作的人类决定覆盖；正式工具或外部机制的执行能力与资源资格；实际执行/消费/结果。不能由其中一个轴的通过自动补齐其余轴。

若只有人工声明、未知生产者/时钟或未支持的reader关联，产品只能描述所提供声明并保留unknown，不能认证O2的真实覆盖。不得向C71 envelope加入 `diagnostic_approved`、任意grant布尔值或新diagnostic consumer来实现这些例子；额外字段、外部机制格式与冻结reader的兼容性须遵守原合同，未支持的来源不被本稿新增为支持。

### 当前诊断提案的固定窗口引用

执行记录在固定窗口记载新diagnostic action canonical `4a6de2408f9f21d669a785113f6eb956066e128c351bcb6badb496deb114ee88`，human reply尚未收到，资源/claim未创建。其方案是一次600秒integration观察、540秒一次无locals父栈及既定自有清理边界；CLI没有该诊断的execute/consumer，外部单次记录不得伪造native consumed/evidence/V2。本稿仅引用上述窗口，未验证后来的期限/回复/状态，没有新grant或执行。

该机制是独立受控诊断方案，不是003产品协议中的新命名空间。它也不扩大71规格批准、原14/85/90/F90，或允许provider、push/merge、服务/设备及其他副作用。

## 5. 本次交付与后续检查

本稿交付三个实质候选：带版本/pins的合同兼容映射；不填造预算的职责/停止/残余包格式；三个synthetic正交语义例子。四类合同的统计充分性/精度、隐私保留、用途阈值和3-A/3-B路线仍在相应用途准入前决定，不作为本次无评分准备的虚构默认值。

本作者仅新建此普通文档并保留独占私有审计，未修改旧稿/F5/源码/Policy/Schema/task/refs，未运行CLI、API、测试、Job或网络。核对UTF-8、相对链接、whitespace与原source/spec pins。普通文档不新增逐行实现测试，也不将文档检查称完整质量门或S2–S5退出。

两名非作者可并行审：一名核适用关系/实际C71边界/来源强度，一名核低干预、预算停止和动作正交语义；共同发现由唯一作者定点修复。Root统一入口链接、scope和阶段提交。新源码、治理规格修订或实际动作须走对应真实准入；本稿独审或提交本身均不提供该权限。
