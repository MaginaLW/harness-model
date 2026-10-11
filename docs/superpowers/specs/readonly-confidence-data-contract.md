# 只读置信度数据与尝试链合同候选

状态：S0/S1 非评分准备，文档合同候选 `v0.1`。本稿固定现有来源的解释与缺口，承接[当前方向](confidence-feedback.md)、[四目标方法候选](readonly-confidence-method.md)和[效果观察口径](../../operations/effect-observations.md)。它没有实现运行时 Schema、sidecar、新存储或采集器，没有准入生产估计或真实 shadow；`method_status=design_pending`、`probability_status=unestimated`、`execution_allowed=false` 继续适用。

## 1. 固定输入与引用

当前自动投影复用 `tools/analysis/approval_overhead.py` 的 `--snapshot` / `--availability`，不增加另一个解析器。先固定 tracked `HEAD` 的提交，再读该提交的普通 Git blob；未提交材料不进入历史快照。live 当前建议仍依赖当时的原生读取，不能用快照替代原生状态、批准新鲜度或 Gate。

每个可复核声明定位到 `source_commit`、仓内 `path`、`git_blob` 与 semantic locator。前三项可由现有报告的 `source_commit`、`sources[].ref/git_blob` 对应；semantic locator 是本稿的文档定位约定，不是已实现的新输出字段：YAML/JSON 用字段名与已有对象 ID，JSONL 用 `task_id + sequence`，review 用 `review_id + revision`。行号可辅助阅读，不能单独标识修订。引用必须指向实际读取的原件，只有哈希而没有可读原件时不能补成证据。

`executed_tool_sha256` 标识实际执行工具的字节，不保证工具与来源提交同版，也不认证来源声明。复算应同时固定来源提交与工具版本，并保留各自标识；本稿不执行历史复算。

## 2. 现有 Git 白名单与字段映射

下表中 `P` 是 `.ai/tasks/TASK-<至少四位十进制数字>/`；路径必须完整匹配。review ID 与 revision 文件名各至少四位，context 文件名为 64 位小写十六进制 SHA-256。语法、类型、身份或 canonical hash 冲突沿用工具的拒绝行为，不能伪装成普通缺失。

| 原件路径 | 当前投影的字段或关系 | 保留的边界 |
|---|---|---|
| `P/task.yaml` | `task_id`；`schema_version`、`repository_id`、`current_state`、`frozen_spec_sha256`、`base_commit`、`subject_commit`。 | `task_id` 来自路径并核对原件；goal、inputs、actor、命令和正文不输出。当前版本绑定不是历史每次候选绑定。 |
| `P/classification.json` | `effective_route`、`effective_verification_level`、`classification_input_sha256`、`base_commit`、`subject_commit`、`spec_sha256`、`policy_sha256`。 | 记录的分类不等于过去每个时刻的路由，也不重新计算分类。原件缺席时保留 `unknown`。 |
| `P/events.jsonl` | `sequence`、`event_type`、`from_state`、`to_state`、`occurred_at`；payload 的 `effective_route`、`conclusion`；仅审核记录/解决事件另投影 `review_id`、`review_stage`、`context_sha256`、`revision`。 | 不输出 actor、自由文本、批准 payload、命令或 Finding 正文；时间顺序只定位已记录事件。 |
| `P/evidence.json` | `schema_version`、`phase`、`verification_level`、`mode`、`conclusion`、`generated_at`、`attestation_head`、`verification_snapshot_sha256` 及 base/subject/spec/Policy 绑定；`checks[]` 的 `check_id`、`category`、`status`、`required`、`exit_code`、`timed_out`、`duration_ms`。 | 原值为账本声明，未重新验证；检查耗时不提供人时或费用。当前 evidence 不自动属于旧验证尝试。 |
| `P/reviews/REV-<数字>-r<数字>.json` | `source_ref`、`review_id`、`revision`、`review_stage`、`outcome`、`context_sha256`、`recorded_at`；派生 `context_linkage` 与 `event_links`。 | 以 ID/revision 对应事件，保留原 outcome；不投影 Findings、作者身份或审核正文，不提供缺陷真值。 |
| `P/review-contexts/<64sha>.json` | 仅被同 task review 引用时解析：`source_ref`、`schema_version`、`review_stage`、`context_sha256`、base/spec/Policy/classification 绑定，及适用的 `subject_commit`、`evidence_sha256`、`verification_snapshot_sha256`。 | canonical hash 校验后只比较引用与 stage；不投影 content 正文或验证摘要。未被引用的 tracked context 仅列入 blob 来源。 |

`task.yaml` 与 `events.jsonl` 是快照必需原件；缺失时拒绝输出，而不是生成空矩阵。可选原件缺席与部分字段未知按现有规则保留。design context 的 subject/evidence/snapshot 为 `not_applicable`；implementation context 的 `schema_version=1.0` 时 snapshot 不适用，`schema_version=2.0` 时 evidence 不适用。这是 context Schema 版本规则，与 verification level 不同；不适用性沿用原投影，不改写成缺失。

`approvals.json`、`spec.md`、`review-package.md`、logs/private、会话、外部服务和宿主事件不在此快照白名单。工具默认模式的批准记录统计是另一种已有报告，不能接入此快照后推定真实请求、答复或人工打断。本稿第 6 节手工核对 task 原件中的后继声明，明确标注它没有被当前自动投影输出；不扩大上述字段范围。

## 3. 变更标识与 request → decision → execution → result

使用 AI Flow 的变更以真实 `task_id` 和仓库身份定位。task-free 工作使用真实变更的 baseline/candidate commit 或 tree、仓内变更范围及已有 PR 引用，不创建虚构 TASK-ID；其 TASK-ID 是 `not_applicable`。未提交候选还需当时可复核的差异依据，收尾 commit 不能冒充被测版本。当前快照只有 task 原件，task-free 来源与链为 `not_projected`；不能因它未出现而删除这类工作、增加分母或断言没有任务。没有适合且获准的保存位置时保留 `unknown`，不新建存储。

| 链阶段 | 当前白名单能支持的事实 | 仍未知或未投影的关系 |
|---|---|---|
| request | 已记录 task 创建、要求审核、阻塞等事件的类型和时序。 | `task_created` 不是原始人类请求；请求组、原请求、请求到答复关联和实际等待不投影。不能把每条账本事件视为一次打断。 |
| decision | 分类原值、review 原 outcome，以及批准或升级事件发生的账本声明。 | 批准 event 的出现不认证一次独立人类决定；批准 payload、原答复、覆盖哪些请求/动作及当前有效性没有由此闭合。 |
| execution | implementation/verification 开始、重启等记录；有 evidence 时可得检查原结果与技术耗时。 | 开始事件不证明全部动作确已执行；实际宿主动作、执行者身份、费用、工作分钟，以及候选与逐次执行的关联仍缺依据。 |
| result | verification 结果事件、review 修订 outcome、evidence 原结论、原状态与 merge 事件类型。 | PASS、APPROVE、MERGED 不补目标验收协议、首候选、完整交付或结束的缺陷窗口；缺少链接时不归因给某模型或前一次决定。 |

一个答复可覆盖多个决定或动作。只有获准的请求/答复原件能证明这种覆盖；账本批准条数不能逆推出请求组或人类介入量。同样，流程状态、审核结果和执行结果分别保留，不能相互代替。

## 4. 尝试链与未知值

当前 `verification_attempts` 由 `verification_started` / `verification_restarted` 与后续 result 事件定位，保留 start/result sequence 和 `original_result`。它是已记录的验证尝试，不是作者候选链。`historical_first_result`、`history_completeness`、`evidence_attempt_linkage` 保持 `unknown`。

首次候选需预先指定链起点、阶段、候选版本、角色、验收协议与完整性依据；窗口内第一条记录、最小 sequence 或最早 tracked commit 都不能单独证明历史首次。修复链另需原候选及原失败、明确的修复入口、父子候选版本和修复策略/支持/预算；重试、重新审核、resolved 或 source-only successor 均不自动提供这些事实。每个失败、partial、取消、skip、未运行和 unknown 保留原值，后续成功不覆盖它们。四目标的事件与真正分母继续引用[方法候选](readonly-confidence-method.md#2-四目标的事件与分母)，本稿不计算分母或样本数。

`dependence_group=task_id` 只是保守的记录关联：同 task 的检查、Finding、修订和重试不能拆成独立样本。跨 task 的共同输入、相同规格、候选继承、共享缺陷或显式后继关系也可能相关；两个 TASK-ID、多名审核者或多线程都不证明独立。用途合同仍须确定相关组、纳入单位及留出规则，不能直接以现有 task 分组认证独立性。

以下区分字段原值与 fact 的 availability，二者不可混为一个枚举：

| 标签 | 含义 | 不能推导 |
|---|---|---|
| `unknown` | 字段值或结果/关系没有可支持的结论，例如快照的实际模型或全历史完整性。 | 不补零、失败、成功、没有缺陷或没有动作。 |
| `not_applicable` | 来源协议明确该字段不适用，例如 design context 的 subject。 | 不改称来源缺失；没有协议依据不能用它掩盖未知。 |
| `projected` | 对应 fact 已由原件投影或所检查的引用关系可得，仍保留原值与限制。 | 不表示独立核实、目标可估计、样本充分或授权有效。 |
| `source_missing` | 某 fact 所需白名单原件在固定提交至少缺一件，可能部分缺失。 | 不表示原仓、未提交或外部来源均不存在；引用只列实际存在且读取的原件。 |
| `not_projected` | 当前白名单投影没有收集/输出该事实，例如实际身份、策略预算或缺陷真值。 | 不证明原事实不存在，不允许为补齐而发现私密材料。 |
| `linkage_unknown` | 有记录但尚不能证明所需目标关系，或有明确引用冲突。 | 不从末次成功、相近时间、相同 SHA 或当前 HEAD 补成历史关系；冲突原值继续保留。 |

`design_pending` 则表示用途或方法规则尚未决定；它与来源缺失不同。规则已定但证据不足时的 `insufficient` 仅在对应方法准入后按协议判断，本稿不产生这一统计结论。

actual 模型身份只接受获准、可复核的运行元数据，requested/reported 与 actual 分开；actor、批准人名、线程名、UI 选择、自述不认证身份。当前实际身份、费用、人时、真实宿主事件与缺陷真值保持未投影/未知。Finding、零 Finding、APPROVE 和 resolved 不提供独立正负真值；工具耗时、配置预算和聊天等待不补费用或人时。本稿不新增这些数据的私密采集。

## 5. 后续用途、方法与隐私接口

这份数据候选只提供可读取来源、字段含义、引用和关系缺口。它向方法候选交付四目标所需事实的可用性，不交付模型层、合格单位、分母、区间或默认分数；向效果观察交付请求/决定/执行/结果的可复核原值及缺失，不交付改善百分比。

| 准入前仍需确定 | 本数据候选给出的输入 | 不满足时可继续的工作 |
|---|---|---|
| 已选用途与错误后果 | 首用途已选追加机器审核，并基于结果积累认识；[专项审核与反馈候选](supplemental-machine-review.md)明确候选/问题单位及需引用的结果。目标、触发和错误接受边界仍待冻结。 | 不重复请求用途选择；继续非评分建议和来源准备，不改变审核安排或执行权限。 |
| 目标、总体与观察协议 | 四目标的事实需求；候选/尝试/审核单位、角色、相关组、纳入排除与取消/缺失来源缺口。 | 保留原记录；不删空层或把来源计数当统计分母。 |
| 方法、精度与真值责任 | 明确哪些关系未闭合、哪些独立真值未投影。 | 方法候选继续设计，不从批准或 Finding 补真值，不推荐经验样本量或阈值。 |
| 获准数据与隐私责任 | 现有固定 Git 白名单；未来新增原件、实际身份依据、访问、脱敏、保留/处置和责任人尚需对应范围。 | 不新增副本、私密采集或后台监控，不删除既有追加原件。 |

普通可恢复准备仍按现有授权推进，上表不是逐字段签字门。真正的用途、来源授权或风险接受决定集中进入 3-A 对应准入；Phase 3/4 的独立进入与整体验收关系沿用[当前设计](confidence-feedback.md)。公开材料仅留方法、脱敏摘要及 Git/PR 引用，原始会话、身份、凭据、逐次记录和日志不入库，保存边界以[效果观察](../../operations/effect-observations.md#保存与隐私边界)为准。

## 6. 固定来源链例子：TASK-0077 → TASK-0078

本例固定来源提交 `75cb3198daf02ebd440097dc4b127460a314fd00`，只说明这一版本的台账声明与引用；不代表 live 当前状态、完整请求链或结果重新验证。下表每行的来源提交均为该 SHA，blob 是 Git 对象标识；locator 不依赖本地行号。

| 仓内 path | git blob | semantic locator 与可说明的原值 |
|---|---|---|
| `.ai/tasks/TASK-0077/task.yaml` | `a0374c2d07419a4c52e86ec90fcb194382e1fc01` | `task_id=TASK-0077; current_state=BLOCKED`；保留原任务，不能因后继合并关闭它。 |
| `.ai/tasks/TASK-0077/reviews/REV-0001-r0001.json` | `f8e3c2d5fea44e04e7425d919e215a37bde33d00` | `review_id=REV-0001; revision=1; outcome=REQUEST_CHANGES`。 |
| `.ai/tasks/TASK-0077/reviews/REV-0001-r0002.json` | `264ed83951514c691af1c43c5fa27d49b83da2e7` | `review_id=REV-0001; revision=2; outcome=REQUEST_CHANGES`；手工可核 Finding `RF-001.status=resolved`，但该字段不被快照投影，也不生成新验收或缺陷真值。 |
| `.ai/tasks/TASK-0078/task.yaml` | `359d178aed99763863c2fbc6f1536cad3a4b4d76` | `decision_units[decision_unit_id=DU-001].inputs` 声明 source-only successor 并保留 TASK-0077；这是手工引用的账本文字关系，当前自动投影不输出 inputs。`current_state=MERGED`、`subject_commit=acd05b14a09e16e87394f8920ef854170165a585` 分别是状态与候选绑定声明。 |
| `.ai/tasks/TASK-0078/events.jsonl` | `589729d99f6d3c30229de5bcf2d29212899490b9` | `task_id=TASK-0078; sequence=16/17` 分别记录 verification started/passed，17 的原 conclusion 为 `passed`；sequence 22 记录 merge。事件顺序不提供历史首候选或旧 evidence 关联。 |
| `.ai/tasks/TASK-0078/reviews/REV-0003-r0001.json` | `fdbb8de75b5ebf738e6159de9cf6cd1423d0fbbb` | `review_id=REV-0003; revision=1; review_stage=implementation; outcome=APPROVE`，引用同 task context `2d75e7892b9743d4865909d73f47041a7b7bdaba42f8d509eeb7a33d8422f4a6`。 |
| `.ai/tasks/TASK-0078/review-contexts/2d75e7892b9743d4865909d73f47041a7b7bdaba42f8d509eeb7a33d8422f4a6.json` | `76f3163509631d0f7f14289d0f31f9014438bb19` | `review_stage=implementation; subject_commit=acd05b14a09e16e87394f8920ef854170165a585; evidence_sha256=60035166f73b29b29cfbdc0ff9a8b9649e0f7e772298e8640d62f25cf6ca70ea`。引用声明不等于 evidence 原件。 |

该提交没有 tracked `.ai/tasks/TASK-0078/evidence.json`；对应 `verification_evidence=source_missing`，不能从 context 的 evidence hash 或正文摘要补成原件，也不访问未提交/私密材料补齐。记录的验证结果仍可保留，目标 `evidence_attempt_linkage` 仍未知。

由此可核的链仅是：原任务及 REQUEST_CHANGES 保留 → 台账声明一个 source-only successor → 后继记录验证通过、implementation APPROVE 和合并。它不是已认证的“首次失败 → 修复成功”样本，更不是两条独立首次样本。来源明确关联的两任务不得在后续数据划分中当作独立输入；真实请求/答复、候选父子链、实际模型、预算、独立缺陷真值与全历史完整性仍须各自来源，不由这组记录补造。
