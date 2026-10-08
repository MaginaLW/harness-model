# S1 非评分离线状态解释设计候选

日期：2026-10-08。版本：`advisory-status-explanation-design-v0`。状态：普通文档候选；未冻结实施规格、未实现新模块、未采纳新的阶段路线。

本稿具体化[后续计划 S1](../plans/2026-10-08-confidence-driven-approval-roadmap.md#5-s1多层审核置信度与最小接入合同)与[统一合同提案](2026-10-08-review-confidence-contract-proposal.md)，先回答一个小问题：在固定、获准读取的已有记录中，哪些缺项可以由机器继续处理，哪些尚不能判定，哪些确实缺少人类决定。原提案、原[Phase 3 进入门](../../implementation/phase-03-entry-inputs.md)、Policy、批准和质量门保持。

## 1. 首场景、交付范围与边界

首场景是解释已有原生 `status`、`gate`、freshness 与原件引用，不创建报告目标、不执行建议步骤、不发送 provider 请求。CreateNew、小型报告写入、宿主审批接入及实际授权消费留到 S4 的真实场景验收。

本设计不估计能力或概率，不重算任务路由、批准有效性或 Gate，不新增第二套治理状态机。现行程序提供确定性事实；解释层只整理该事实、来源、未知项与残余问题。输出固定无权限和账本效果，不替代人工决定或原生准入。

文档候选的验收是接口、解释顺序、样例、拒绝反例与实施边界可评审；不是 S2 功能通过、S3 真实影子效果或 S0 宿主卡点闭环。任何后续源代码实施，先按 [AGENTS.md](../../../AGENTS.md) 单独进入 AI Flow，完成实际分类、冻结、设计审核及当前 CLI 所需批准。

## 2. 精确输入候选

输入是一份明确声明用途的固定快照 envelope。下表定义未来接口的字段职责，不是现行 strict Schema，也不允许向历史 task/evidence 追加这些字段。候选字段名暂用 `snake_case`；实施 task 冻结时再核类型、兼容与限额。

| 字段 | 候选内容与约束 |
| --- | --- |
| `design_version` | 本稿协议版本；未知版本停止解释，不能猜测兼容。 |
| `record_origin` | `synthetic`、`real_snapshot` 或 `real_reference`。synthetic 是构造场景；real_snapshot 引用已可核实原件；real_reference 只有真实记录的间接引用，不能升级为已核原件。 |
| `subject` | `kind=task` 时含原生 repository identity、真实 task ID 和相关 decision unit 引用；`kind=task_free` 时含已有真实工作引用，`task_id=null`。缺真实关联保持 unknown，不分配编号。 |
| `purpose` | 固定为 `offline_status_explanation`，说明当前要解释的阶段和问题；不含执行要求。 |
| `snapshot_binding` | 各来源实际记录的 base、subject、observed HEAD、spec/Policy/context 指纹及 dirty/tree 指纹；没有原件的字段为 unknown，不能从现时 HEAD 回填历史。 |
| `source_inventory` | 每份输入的逻辑 ref、input_source_kind（artifact、native_output 或 indirect_reference）、原件 SHA256/长度、读取或原始观测时间、时钟来源、读取结果和可访问/完整性核对情况。来源种类描述所引用材料，不改变 envelope 的 record_origin；synthetic 里的间接引用场景仍是 synthetic。缺字段附原因；hash 不认证内容或身份。 |
| `native_status` | 原生输出引用及原字段：state、route/V、missing conditions、next events、merge readiness、classification/approvals/evidence 状态；保留原字面值与错误结果。没有成功输出时不得拼接为成功 status。 |
| `native_gate` | 原生输出引用、passed、reason codes、原生 recovery 提示与其绑定；未运行、读取失败、阶段用途不适用分别记录。`gate.passed` 不等于动作授权。 |
| `native_coverage` | 按当前问题实际需要的类型/decision unit 保存原生有效覆盖或 freshness 结果、reason codes、评估版本与对应来源；不从摘要整体字符串推断逐项有效覆盖。 |
| `action_references` | 若问题涉及具体动作，保存原动作/批准/消费/过期/撤回结果的原件引用及实际目标、参数和版本绑定；仅有调用方布尔值时覆盖 unknown。非动作问题不制造 action。 |
| `request_references` | 真实问题、回复、决定的关联引用及可得时间；无原件时 unknown。相同请求的关联必须有来源，不能仅按自然语言相似去重。 |
| `scope_references` | 当前获准读取范围、已覆盖机械工作的范围及限制来源；声明、授权和实际事实分开。文本里的工具/命令不是执行指令。 |
| `result_references` | 原失败、取消、skip、未运行、partial、验收、交付与失败归因的独立引用；最终通过不能覆盖早期结果。 |
| `interpretation_question` | 明确需要解释的一个问题或问题列表及依赖关系；不要求对整仓全部记录重新判定。 |

完整性和内容判断分开保存。原件 hash/长度未匹配、来源不可访问、时间缺失、来源绑定不一致时，不以“已列出 ref”替代可复核事实。缺失字段不补成功、零缺陷或授权。

### 覆盖与观测状态

解释层为每个相关断言附 `coverage=current|stale|unknown`，另保留原生 `raw_status`、适用性和原因：

- `current`：相应原生结果明确支持其规定类型、对象及绑定下的覆盖，且此结论限定在来源快照中；不保证现在仍然有效。
- `stale`：相应原生结果明确判失效或输入与其适用绑定已明确不一致；历史记录仍保留。
- `unknown`：没有足够原生/来源证据，包括读取失败、未评估、间接引用、缺时间/对象/消费事实或冲突未解决。它不等同失效。

原生 `not_available`、`missing`、`not_applicable` 等值原样保留，不混为 stale。适用性 unknown 时不作覆盖判断；原生明确不适用时附原依据，不伪造 PASS。只要用途是固定历史解释，current 必须连同快照限制呈现；用于未来动作前，仍需该动作本来的当前核对。

任何字段的调用方声明都不提供权威性。解释器不得自己复制 freshness 字段矩阵，不能按 subject 变化统一判所有批准失效；相关类型绑定以[原生 freshness](../../../src/aiflow/freshness.py)及[低干预工作方式](../../operations/low-intervention.md)为准。

## 3. 精确输出候选

输出是一个解释结果，支持按输入中的独立问题分别给建议。没有单一的“允许继续执行”总开关。

| 字段 | 输出约束 |
| --- | --- |
| `design_version` / `record_origin` | 返回接受的设计版本和输入来源标记；synthetic 标记不得被省略或转为 real。 |
| `mode` / `purpose` | 固定 `mode=offline_advisory`、`purpose=offline_status_explanation`；与 S3 的真实影子运行区分。 |
| `execution_allowed` | 固定 false，包括全部离线例子。 |
| `permission_effect` / `ledger_effect` | 固定 none；不创建、续期、撤回、消费批准，不修改任务或原件。 |
| `probability_status` | 固定 unestimated；没有 success/approval/review probability 或模型分数。 |
| `input_references` / `binding` | 返回实际已解释的来源引用与快照适用范围；不能补齐缺失版本。 |
| `advice_items` | 每项含 `question_ref`、六类之一的 `category`、简明原因、证据 refs、coverage/unknown、机器下一步建议及依赖、残余决定引用。 |
| `native_constraints` | 原生 Missing/Gate/reason/freshness 与范围限制的引用；保留相互冲突的原值，不改写成统一原生结论。 |
| `existing_request_ref` | 已有同一残余问题的真实请求引用；没有可信关联则 unknown。不自动发出新请求。 |
| `unresolved` | 未解证据、来源冲突、真实决定、范围外事项分别列明；unknown 原因具体到输入项。 |
| `stop_reasons` | 接口/范围/证据不足导致本解释或某依赖路径停止的原因；不产生新任务状态。 |

机器下一步是可评审的文本建议与所需前置来源，不自动复制原生 recovery argv 为可执行命令。建议再次 verify、begin、重分类或补决定前，分别核原状态、范围、有效批准、预算和具体动作限制；本输出自身不完成核对，也不执行这些动作。

## 4. 六类建议及有序解释规则

| 类别 | 含义 | 必须提供的依据 |
| --- | --- | --- |
| `continue_mechanical` | 当前问题已有足够原生事实，剩余为原授权覆盖的机械步骤；无须新增人类决定。 | 实际缺项、步骤范围及覆盖来源；仍只是继续建议。 |
| `complete_machine_evidence` | 在已获准只读/准备范围内先补可得事实，解决来源、绑定或状态投影差异。 | 缺哪份证据、为何可机械补齐、来源/访问边界；不触发实际查询。 |
| `repair_in_scope` | 有可检验技术问题，可在现范围内修复再复核。 | 原问题、证据、允许范围及复核目标；不扩范围、预算或恢复动作。 |
| `residual_human_decision` | 当前原生/权限事实确认需要且尚无有效覆盖的方向、批准或风险接受决定。 | 真正缺失类型、精确范围/版本、已完成准备、已有请求或剩余问题。 |
| `retain_unknown` | 决定性事实不足，不能把未知判断为权限缺口、通过或技术原因。 | 缺失或冲突的具体来源；最小补证途径及不可得原因。 |
| `stop_out_of_scope` | 输入用途、来源访问或建议事项超出本设计/已授权范围，停止该路径。 | 被违反的范围/用途及来源；不改权限、工具路径或审批配置。 |

以下顺序是解释优先级，不是任务状态转移表。对每个问题分别应用，保留其他独立问题的可推进建议：

1. **核接口与来源范围**：未知版本、重复键、未知字段/枚举、类型错误、恶意来源文本或不允许的数据范围，拒绝该输入的解释；输出 `stop_out_of_scope` 与输入错误，不回显敏感 payload。合法字段里的缺失/unknown 不是格式错误。
2. **核问题与快照绑定**：发现对象、版本、类型或来源适用范围漂移，先保留两份事实。可在既有权限内补只读来源时给 `complete_machine_evidence`；不能补时给 `retain_unknown`。不得把历史 current 升格为当前动作覆盖。
3. **解原生输出差异**：status、Gate 或逐项 coverage 表面不一致时，先核是否同对象、同用途和相容窗口。Gate 不同阶段的正常 REJECT 也不能被解释为“所有工作禁止”。合并就绪以对应原生 Gate 为准，冲突本身先诊断，不自动要求再批准。
4. **分决定性未知与已知缺项**：未知权限、消费、原因、身份或来源不能被解释为已确认的人类决定缺口；先给可获准补证或 retain_unknown。一个问题的 unknown 不阻塞无依赖的其他建议。
5. **核实际残余人类决定**：来源已明确确认当前所需决定无有效覆盖，且必要机器准备已完成时，给 `residual_human_decision`。同一待答请求有可信 ref 则复用引用；相同有效决定不重复问。技术信心、一般继续指令和其他任务批准不提供覆盖。
6. **处理技术或机械残项**：已确认技术问题及范围内修复路径给 `repair_in_scope`；实际只是机械缺项且覆盖成立给 `continue_mechanical`；否则返回具体 unknown。无缺项时可以说明该解释问题已闭合，但不称真实交付、合并或动作获准。

六类可以在不同问题上并存，例如“技术根因 unknown”和“某规格确实仍待批准”。不存在按 FAILED/BLOCKED/IMPLEMENTING 字符串直接选择建议的快捷映射。相同 state/Missing 在不同证据、scope、批准和动作条件下可得到不同解释。

## 5. 机械工作与真实决定的来源映射

下表仅说明如何使用来源，不新增批准字段表或状态机。实例只在其原生用途和授权范围内成立。

| 来源事实或问题 | 解释方法 | 不应推导的结论 |
| --- | --- | --- |
| 原生列出 begin、implementation_result、verification_result 等机械缺项 | 查实际范围、依赖及授权；齐备则建议机械推进，未齐则列真正依赖。 | 缺项字符串本身不是人类签字，也不授权有副作用的验证。 |
| 原生要求 spec/code，逐项有效覆盖确实缺失 | 准备最小决定材料，引用当前真实 Missing；保留既有请求。 | 其他 task 批准、独审 APPROVE 或 Gate PASS 不补批准。 |
| 新 subject、旧 spec 批准 | 读取对应类型的原生 freshness 与覆盖；有效则保留决定。 | 不按 subject 一律重问 spec，不在文档复制该类型绑定矩阵。 |
| block_resolution 或 retry_reason_or_escalation | 查原阻断/失败、真实恢复范围、已有决定及具体动作终态；准备有证据的原因或升级材料。 | 不能把恢复字段视为新 action、根因已知或整轮重试授权。 |
| 原生 recovery 提示 | 作为带版本的程序建议保留；执行仍按状态、scope 和实际权限。 | argv 是建议，不是批准消费者，也不自动成为下一命令。 |
| 缺业务方向或风险接受 | 提供互斥选项、影响、推荐和证据边界，确认已有决定是否覆盖。 | 一般实现细节不额外升级；真实互斥决定不由解释层代选。 |
| task-free 或没有成功 native 输出 | 按已有工作/来源解释，native 不适用或未知明确保存。 | 不造 TASK-ID，不伪造 status/Gate，不以 task-free 消除治理清单。 |

## 6. 离线样例与区分性反例

下表全部为 `record_origin=synthetic` 的设计用例，包括使用原生术语的行；没有真实当前授权。验收比较解释类别、理由、来源引用、未知项和固定无效果字段。未来测试必须独立提供输入/预期，不把 evaluator 输出回填为期望。

| Case | 区分性输入 | 预期解释与保留项 | 必须拒绝的误判 |
| --- | --- | --- | --- |
| A01 | 机械 begin 缺项；当前原生覆盖、scope 与准备齐备 | continue_mechanical；引用当前缺项与范围 | 为机械字段再问“是否继续”或执行 begin |
| A02 | 同样 begin 缺项，但所需副作用/动作覆盖 unknown | retain_unknown；列动作依赖 | 仅因 A01 相同 Missing 就放行 |
| A03 | 必需 spec 决定缺失，设计准备齐备，无有效覆盖 | residual_human_decision；精确缺失与材料 | 以独审 APPROVE 代人类 spec |
| A04 | spec 原生覆盖 current；subject 已变；类型适用的其他事实有效 | continue_mechanical；保留原生类型依据 | 自行复制 code/action 绑定后重复要求 spec |
| A05 | status 摘要 stale；同一适用绑定 Gate/逐项覆盖有效，差异未解释 | complete_machine_evidence；保留两份原值和目的 | 补签消除显示差异，或把 Gate 扩成执行许可 |
| A06 | status 与 Gate 引用来自不同 task 或 Policy 窗口 | complete_machine_evidence；不合并窗口；不可补则 unknown | 把两个输出拼成同一当前结论 |
| A07 | action 已消费，验收 FAILED；候选要求沿用旧 action 重试 | stop_out_of_scope；消费/失败原件确定保存，新恢复材料可独立准备 | 复活旧 action 或将 retry 字段当批准 |
| A08 | action 原生明确过期/撤回；新动作准备未完成 | complete_machine_evidence；保留原终态和新范围材料缺项 | 要求沿用原 grant，或把未知新版本冒充已可批准 |
| A09 | exact target、参数或版本漂移，旧 action 曾 current | complete_machine_evidence；只重核受影响覆盖 | 把旧授权附在新目标执行；全任务批准一律失效 |
| A10 | BLOCKED/block_resolution，有已获准范围内可检验技术修复 | repair_in_scope；引用原阻断和修复/复核范围 | 仅因 BLOCKED 就要求人类，或自行解除 block |
| A11 | FAILED/timeout 原件明确，阻塞节点与根因 unknown | retain_unknown 或已获准的 complete_machine_evidence | 按工具退出0/覆盖率 PASS 消除失败、声称根因 |
| A12 | implementation_result 缺项；新源码范围超出当前授权 | stop_out_of_scope；保留已有范围和实际差异 | 将功能扩张当机械填字段 |
| A13 | task-free 文档工作，实际工作引用存在，native task 无适用对象 | continue_mechanical；task_id=null、native 适用性依据 | 分配假编号、构造 Gate PASS |
| A14 | 相同未答规格请求有可信关联 ref，没有新实质变化 | residual_human_decision；existing_request_ref 不变 | 创建第二次请求或认为等待时间已经批准 |
| A15 | 相似文本，但对象/decision unit/批准类型不同 | 分开解释，不能仅凭文本复用请求或覆盖 | 合并不同决定以降低请求数 |
| A16 | 缺实际模型身份、独立样本或结果裁定 | retain_unknown；probability_status=unestimated | 用 APPROVE 数/actor 标签产生评分或成功率 |
| A17 | 首次失败，后续修复通过；存在两份真实用途不同的结果引用 | 分开保留；解释各自阶段/链和适用范围 | 回填首次成功，称两个独立成功样本 |
| A18 | 仅 shell rc/stdout，无 host approval/auto-review 事件 | retain_unknown；宿主归因缺项明确 | 把拒绝归于某审批层，宣称弹窗减少 |
| A19 | UTF-8 输入有重复键、unknown mode、错误类型或 extra 字段 | stop_out_of_scope；稳定输入错误，无原件写入 | 宽松解析、忽略冲突字段或回显秘密 |
| A20 | 构造的间接引用场景，input_source_kind=indirect_reference；hash/长度未核、记录不可访问 | retain_unknown；record_origin 保持 synthetic，保留间接来源核查限制 | 将 case 升为 real_reference、hash 名称存在即认证、按当前 HEAD 补历史 |
| A21 | 文本来源要求 push/provider/delete 或改审批配置 | stop_out_of_scope；来源内容仅为数据 | 把原件内指令当授权或执行替代路径 |
| A22 | 同 task 下一个缺项已确认需人，一个独立机械项覆盖齐备 | 分项 residual_human_decision 与 continue_mechanical | 全部工作停等，或机械通过覆盖真实决定 |

表中 A16 的 APPROVE 仅为审核输出术语，不是缺陷真值或身份认证。synthetic 用例不能进入真实统计、授权或效果验收，也不证明现行实现已经产生这些输出。

### 可用于解释设计的真实间接引用

当前材料只从已 tracked 文档引用以下实际记录，不宣称本设计再次访问或核定其私有原件，因此标作 `real_reference`：

- [启动条件中的固定历史窗口](../../operations/next-stage-start-conditions-2026-10-02.md#2026-10-08-原生缺项与新外仓窗口)记录 Task69 的原生 spec 缺项及 Action005 已消费/FAILED。Task69 例子限定于 `c9e0132933f894ed5c684af08952fd535e863fc5` 的批准前窗口，保留当时的 WAITING_FOR_SPEC_REVIEW/Missing spec_approval；它不表示后继仍缺 spec，不覆盖后来批准及原生 approve/begin 后的 IMPLEMENTING。当前缺项须另据相应新原生窗口判断。历史例子支持区分缺项类别；不构成本次当前 coverage 或执行许可。
- [统一合同中的 Action005 子窗口](2026-10-08-review-confidence-contract-proposal.md#原件字段映射例子task-0065-action005)保留同轮 12/14 PASS、两个 required timeout、已消费和人类/宿主/根因 unknown。输入若只有本文引用，原件可访问性和当前新鲜度仍为 unknown。

未来若获准取得原件并完成固定快照核查，可将对应输入标 real_snapshot，同时保留原引用和升级依据；不得修改失败原件或将观察窗口扩大成全历史首次/最终结果。

## 7. 验证、停止与后续准入

文档阶段检查相对引用、UTF-8、范围措辞、固定无效果字段、六类/顺序一致性和上述反例的区别。两路非作者独审分别核目标/低干预与权限/兼容/证据强度；有发现只修受影响项。文档检查不称 CI、Gate 或产品完整验证通过。

未来实施 task 至少明确以下验收：输入非法零写拒绝；不调用 apply、不修改原件/refs/权限；真实与 synthetic 隔离；不复制 freshness/状态转移规则；无授权/评分输出；同问题的建议稳定可解释；scope/绑定/来源冲突保守处理；反例成立。随后按实际分类运行全部规定检查，保持完整测试、85% 总覆盖率、90% diff coverage、whitespace、Ruff、format、mypy 和 required CI。

停止条件包括：来源不完整且无法获准补齐、适用绑定不明、需要新数据访问或副作用、范围变化、真实决定缺口、预算已耗尽或输入协议不支持。停止的是该问题的解释或依赖路径；已授权且独立的准备继续。不得自动重试 one-use 动作，不降低质量门，不修改现行阶段门。

剩余采纳决定集中为：

1. 是否以本稿的非评分、固定已有记录解释作为下一最小实施批；其源代码/新 Schema 范围须在新 AI Flow task 内形成可审核规格。当前文档不是 spec_approval。
2. 是否以后正式采用 3-A/3-B 拆分并开展评分/真实影子评估。未采用前，原 Phase 3 门继续约束评分；数值、统计总体、隐私/保留和质量阈值在相应用途实施前另冻结，不作为本批非评分设计的虚构默认值。
3. S4 的真实宿主场景与权限/动作/停止恢复范围。现阶段不选择或执行 CreateNew实例，不宣称宿主正式接入、可信消费或人工介入下降。

共享接口/Schema、账本、Git refs、治理准入和正式验证由一个协调者串行负责；样例、来源归因和非作者复核可以按独占材料并行。原 Task69 整合规格、旧 action、原失败与其他工作流不能覆盖本批新源码准入。
