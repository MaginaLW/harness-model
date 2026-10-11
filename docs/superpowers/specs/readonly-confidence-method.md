# 非评分置信度证据可用性方法候选

状态：S1 方法候选。项目所有者已选择 B 与本仓自然治理任务的只读建议首场景；本稿具体化四类目标的证据需求，不重新提出方向选择。当前只验证已有事实的投影和来源关系，统计、样本、隐私与预算参数尚未冻结。

## 1. 适用范围

本稿承接[置信度反馈设计](confidence-feedback.md)、[四类合同提案](2026-10-08-review-confidence-contract-proposal.md#3-能力与概率合同)及[合同兼容与审核预算补充](2026-10-09-s1-contract-compatibility-and-review-budget.md)。旧提案中的固定窗口、接口和任务例子是历史设计输入，不作为当前执行指令，不恢复归档任务或模块。

当前输入限于[固定提交事实快照](../../operations/effect-observations.md#固定提交的事实快照)已获准的 tracked Git 原件白名单。报告只描述该提交中的原记录，不证明 live current、全历史完整性、模型身份或原结果已经重新验证。[只读准备建议](../../operations/review-advisory.md)继续使用原生状态；本方法不重算 route、Missing、批准新鲜度或 Gate，不执行建议、不写账本。

本稿与对应可用性映射均为非评分准备，固定 `method_status=design_pending`、`probability_status=unestimated`、`execution_allowed=false`。不输出估计、`estimable`、样本充分性、eligible N、分母数、区间或阈值，也不将缺失补零。3-A 生产估计与真实 shadow 仍须满足[对应准入](../../implementation/phase-03-entry-inputs.md#当前采用的-3-a--3-b-进入与退出关系)，本稿不启动 S2/S3 或改变 Phase 3 的 `not_started`。

## 2. 四目标的事件与分母

以下为可评审的目标语义。真正分母是符合该目标协议的单位集合，不是已有文件数、task 数、检查数或审核人数；当前报告不计算其数量。总体、单位粒度、纳入规则和观察边界须在相应用途估计前确定。

| target ID | 预测事件 | 真正分母与单位 | 所需来源关系 |
|---|---|---|---|
| `author_first_acceptance` | 预先指定的首个作者候选，在声明条件和有限预算内达到指定阶段验收。 | 符合纳入规则的作者尝试链，每条链对应明确的阶段和首候选；后续修复不是新的首次单位。 | 链起点及完整性依据、首候选版本、作者角色与适用身份来源、阶段协议、条件/预算和该候选的验收原件。 |
| `author_after_repair_acceptance` | 已进入修复的链，按声明策略、支持条件和预算达到指定验收。 | 实际进入修复的合格链，是修复群体的条件分母；不能用所有任务、所有首次失败或所有修复提交代替。 | 原候选与原失败、修复入口、父子候选关系、修复策略/支持/预算、验收协议及修复候选结果。 |
| `review_detection` | 在固定受审候选、可见信息和预算内，正确报告一个独立裁定存在的可处置缺陷。 | 独立裁定为正的审查机会或缺陷单位；先声明审查单位和缺陷粒度，重复报告不增加正真值单位。 | 受审版本与范围、独立正真值及裁定协议、可处置性/严重度口径、审核报告与真值的对应关系、信息与预算。 |
| `review_false_positive` | 在独立裁定不存在对应可处置缺陷的审查单位上，错误报告该缺陷。 | 独立裁定为负的预定审查机会；须有明确机会集，不能用全部报告或 Finding 数充当负真值分母。 | 受审版本与机会集、独立负真值及裁定协议、审核报告和被报告缺陷的对应关系、信息与预算。 |

审核机会可按预先声明的候选、可检查对象和缺陷类别定义；若采用缺陷级单位，其正负机会及匹配规则也须明确。检出与误报使用相容单位，不能在结果揭示后切换粒度或只挑已报告对象。首次与修复后目标适用于不同群体，二者差值不直接表示修复的因果效果。

取消、skip、未运行、partial、工具失败和结果未知均保留原值；它们如何进入分母或映射为目标事件，留给预先明确的协议。工具或权限失败可以证明当轮未验收，不能自动证明作者能力差。模型身份仅接受获准且可复核的实际运行元数据；actor、线程名、UI 选择和自述不构成身份依据，本阶段不采集或按模型归层。

## 3. 当前投影能支持什么

| 已有投影 | 可以说明 | 尚不能补出的目标事实 |
|---|---|---|
| task、分类及事件原状态；verification started/result 顺序和原结论 | 固定窗口内记录了哪些状态及验证尝试，后续通过不覆盖先前失败。 | 全历史链完整、真正首候选、作者/修复角色、验收协议、预算和真实交付；当前 evidence 不能自动绑定旧尝试。 |
| 指定 review ID/revision、原 outcome、同 task context 的 canonical hash 与适用版本绑定 | review 与 context 的引用对应，事件与具体修订的匹配、冲突或缺失。 | 审核正确性、当前新鲜度、独立模型身份、缺陷正负真值；`APPROVE`、零 Finding 和 `resolved` 均不能提供独立真值。 |
| evidence 的绑定、各检查原结果与来源引用 | 所保存 evidence 声明的候选和检查结果。 | 未重新验证的声明不能升级为目标验收；多个检查不是多个独立候选或样本。 |
| 每个 task 的保守依赖组及原件 blob 标识 | 同 task 的修订、重试和检查应保留关联，固定输入可复核。 | 不能认证统计独立性；共同输入、缺陷来源或跨 task 相关性仍待对应来源与规则。 |

`historical_first_result`、`history_completeness` 和 `evidence_attempt_linkage` 继续按当前快照保留 `unknown`。上下文的 `matched` 仅指声明引用、stage 或 canonical 内容对应，不提供目标真值或授权。设计 context 的 subject/evidence/snapshot 不适用性沿用原投影，不改称缺失。

报告的 `targets` 使用第 2 节的四个 target ID；各项的 `denominator_definition` 是分母候选文字，`required_facts` 引用下列闭合 fact ID，不产生纳入单位清单或分母计数：

| fact ID | 当前映射与限制 |
|---|---|
| `candidate_version_bindings`、`verification_evidence`、`recorded_verification_results` | 按固定候选绑定、evidence 和验证事件的原投影及所需来源是否存在判断；保留失败、partial、unknown 等原值，不推定作者验收。 |
| `review_results`、`review_context_bindings`、`review_event_references` | 按 review 修订原结果、同 task context 绑定及事件对应判断；匹配、冲突和缺失分别保留，不认证独立真值或当前有效性。 |
| `first_candidate_lineage`、`repair_candidate_lineage`、`evidence_attempt_linkage` | 当前 snapshot 尚不能闭合相应目标链，固定为 `linkage_unknown`；不从事件先后或末次成功补成首候选、修复链或旧结果关联。 |
| `actual_model_identity`、`task_conditions`、`acceptance_protocol`、`dependency_independence` | 当前为 `not_projected`；task 的保守 `dependence_group` 不提供统计独立组认证。 |
| `repair_strategy_and_budget`、`independent_positive_truth`、`independent_negative_truth_and_opportunities`、`defect_report_matching`、`review_information_and_budget` | 当前为 `not_projected`；不能用重试次数、审核 outcome、Finding 或 resolved 补成策略、预算或正负真值。 |

`observations` 完整保留相应原投影，包括已有 `unknown`、`not_applicable`、冲突与部分结果。fact 的 `projected` 只表示来源投影或所检查关系可得，不表示协议已冻结、真值成立、样本充分或任一 target 可估计。

当前报告只使用四类 availability，不把它们合并成一个“可评分”判断：

| availability | 含义 | 典型例子 |
|---|---|---|
| `projected` | 对应事实已由白名单原件投影；附实际引用，保留原值及关系限制。 | 已记录的验证失败，或受审 context 的版本绑定；不表示已验收。 |
| `source_missing` | 该 fact 所需的白名单原件在固定提交中至少有一件缺席，可以是部分缺失；其他原投影仍保留。 | review 引用的同 task context 文件不存在；不据此宣称所有来源或全仓均无该证据。 |
| `not_projected` | 当前白名单投影未收集或未输出该目标事实。 | 作者身份、修复策略和独立缺陷真值；不表示原仓库或其他来源不存在。 |
| `linkage_unknown` | 有记录但缺少支持该目标关系的依据，或存在已知冲突；保留冲突原值。 | 验证结果与候选关系未闭合，或 review/context stage 不对应；不推断成功或失败归因。 |

availability 只映射一个具体事实或关系。来源齐全不自动形成充分样本；关系 `matched` 也不解除其他未知项。缺失原因与设计未定分别表达，字段和原件仍按对应来源的适用性解释，不扩展旧严格 Schema 或归档候选 API。

## 4. 当前可验证的反例

- 首次记录失败、后续记录通过：原失败保持，不能回填首次成功或增加独立样本；窗口内首次观察不能补成全历史首次。
- 两份审核报告可能指向同一缺陷：保留两份 review 的原投影与来源；当前 snapshot 不投影 Finding 匹配，缺陷对应关系仍为 `not_projected`，不能认证缺陷或样本的独立性。
- `APPROVE`、零 Finding 或追加 `resolved`：仍缺独立真值，不补“无缺陷”、检出或误报结果。
- 有 Finding 而没有负真值机会集：只报告原记录与未投影的真值需求，不计算误报率。
- 当前 evidence 通过，但旧尝试绑定不明：保留通过原值和旧关联未知，不从当前 HEAD 补写旧候选。
- 同一 context hash 仅在另一 task 出现：不借用；同 task 来源缺席按 `source_missing` 说明。
- 原记录存在，但正文、身份或费用不在投影中：按 `not_projected` 说明，不读取私密材料补齐。

验收只证明这些固定输入下的纯映射、原值保留、来源引用与隐私边界正确；不验证统计精度、实际校准、人工成本下降或真实 shadow。

## 5. 3-A 后续集中决定

| 实质决定 | 需要形成的具体内容 | 当前可继续的准备 |
|---|---|---|
| 用途与容许误差 | 预测将服务研究、追加专项审核或人工升审中的哪一种；适用总体、错误后果与可接受误差。 | 保留四目标事件和分母候选，不据候选自动改变审核安排。 |
| 来源与数据责任 | 可使用的原件和身份依据、新副本的责任人、访问/脱敏/保留及处置边界。 | 继续已获准白名单的只读投影；不新增私密采集、模型或费用统计。 |
| 纳入、分层、独立组与窗口 | 纳入/排除、任务及角色必需层、链与相关组、观察端点、取消/缺失处理及偏差边界。 | 列出现有原值和关系缺口；不删空层、不扩大分母、不把 task 组认证为独立。 |
| 真值与质量 | 审查单位、独立裁定责任和协议、严重度与可处置性、报告匹配、漏检/误报及返工口径。 | 提供四目标的来源需求与反例；不拿审核结论代替裁定。 |
| 方法与精度 | 相应用途的估计方法、区间与整体精度规则、充分性及跨 cohort 更新条件。 | 维持 `design_pending`；不推荐默认数值、新算法或冷启动分数。 |

这些是未来用途准入的实质问题，不是每个字段的新增签字门。普通可恢复实现细节按现行授权推进；真正尚无决定的方向、授权范围或风险接受集中呈现。数据和方法条件未成立时继续非评分准备；相应条件成立后再按 3-A 准入推进估计或真实 shadow。整体 Phase 3 与 Phase 4 的依赖保持 B 设计中的两包退出关系。
