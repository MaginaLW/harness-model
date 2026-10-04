# 后继阶段需求与合同提案：2026-10-04

状态：`proposal / not_frozen / implementation_not_started`。

本文件承接[当前待办第 5、6 项](follow-up-backlog-2026-09-22.md#2026-10-04-收尾核定与下次待办)，
给出 I1/I2、E5、I5 / Phase 3 和 Phase 4 的具体可审查材料。它是准备提案，不是治理
Task、冻结规格、Policy、采集许可或执行计划。数值阈值、观察窗口、保留期、预算与具体
执行资产仍待决定；不以提案完成宣布进入门已经满足。

权威入口为[独立启动条件](next-stage-start-conditions-2026-10-02.md)、
[阶段三进入输入](../implementation/phase-03-entry-inputs.md)、
[原实施目录的阶段三/四](../superpowers/plans/2026-08-01-ai-code-collaboration-mvp-implementation-directory.md)
与当前原生 Policy。既有任务、批准、取消、失败原件和已消费动作保持追加式保留。

## 1. 当前需求与证据矩阵

| 单元 | 已有事实或真实需求 | 尚未选择或满足的条件 | 本提案可交付范围 |
| --- | --- | --- | --- |
| I1 生命周期复用 | 同仓双平台 CI、guest 重启业务、恢复及原生收尾已完成；Linux runner 22 离线符合既有停用约定，POSIX queued 构成受控恢复接单的候选需求 | 尚未决定是否恢复接单，也未冻结当前 guest 冷启动身份、串行交接、权限、幂等、业务验证和可执行回退 | 保留既有已交付范围；准备固定实例的受控交接，不将离线直接判故障，不执行停启、注册、更新或重新运行 CI |
| I2 扩仓/平台 | 两个既有试点分别有真实证据；r3s 当前 POSIX 尚无执行步骤 | 未选新的可信目标及其独立准入、等价检查、准确候选完整 CI 和恢复方案 | 整理目标选择所需字段；既有 POSIX 恢复不记为扩仓完成 |
| E5 完整引擎采用 | 已有 wheel、治理引擎和 guided 交接基础 | 尚未选定确需全引擎的新目标；资源分发、非覆盖初始化、身份、存储和目标 CI 适配需独立设计 | 一目标需求与兼容矩阵 |
| E5 provider | 真实报告获取、来源核对、取消与导入已有经历 | 尚无选定接口/adapter，身份、数据、费用、超时/取消/分页/编辑/重复边界未冻结 | 一种接口的只读调用合同与离线反例提案 |
| E5 可信执行 | 当前没有通用 push/merge 强制授权消费者；本地 actor 与 approval 文本不能补足该能力 | 未选固定服务动作、资产、身份根、服务授权、原子消费、凭据托管或恢复范围 | 一种固定动作的授权消费合同提案 |
| I5 / Phase 3 | 原 task、review、verification、失败 receipts 可作输入，样本门 `partial` | 样本充分性与隐私偏差未冻结，真实 V3 用例门和统一 telemetry 门均 `not_met` | 样本/隐私、度量和 V3 候选提案；实施保持 `not_started` |
| Phase 4 | 已有资源感知设计和非执行蓝图 | 缺 Phase 3 真实退出、稳定接口、量化人工协调成本及真实暂停恢复/集中审批需求 | 缺证据矩阵；实施保持 `not_started` |

runner 现场事实只绑定本轮只读窗口：2026-10-04T04:39:51.7525165Z–
04:39:53.1184530Z，Linux runner 22 为 `offline / busy=false`，Windows runner 21 为
`online / busy=true`。r3s 候选 SHA 为 `9e1b538c6acdcb8fde410172ebf1dff4485e6ffb`，
run `37177002687` attempt 1 的 POSIX 为 `queued`、0 steps。
来源与本轮完整检查关联见[外仓现场证据](external-follow-up-evidence-2026-10-04.md)。
该快照不推定当前在线状态，也不能据 Windows busy 状态恢复或中断任何实例。

后续 13:29–13:35 UTC 只读窗口中 Windows job 已 success、runner 21 online idle，
Linux 仍 offline/POSIX 0 steps。既有最终约定主动停用 Linux 服务，当前 guest 进程也未
发现。后继不是直接 systemctl start：需新冷启动/身份绑定、停止 21、22 接单及完整
验证、停止 22/残留核对、恢复 21 的受控串行交接；旧动作授权均不能复用。
精确资产与待决动作以外仓证据文件的新窗口为准，不将历史 busy 写成当前事实。

I1 恢复提案至少要补齐：目标实例/运行时的实际身份与版本、所有权及保护对象、当前状态
和故障证据、允许生命周期动作、依赖和凭据边界、幂等与不重复注册、ACL 不扩张、恢复
目标及原业务完整验证。I2 则另选一个可信目标，不从 runner 22 恢复推出新增接入许可。

## 2. E5 三条独立最小需求

### 2.1 完整引擎采用

最小交付物为一个真实目标的需求和兼容表，回答“该目标为什么需要完整引擎，现有
guided 方式缺哪项能力”。未选目标时保留需求待决，不制造业务改动。

| 拟需求字段 | 必须形成的可审查内容 | 当前缺项 |
| --- | --- | --- |
| `target` / `need` | 可信目标、所有权、现有流程及实际能力缺口 | 目标与需求未选 |
| `existing_state` | 既有规则、配置、身份、存储与未提交文件清单 | 待目标选择后只读核对 |
| `resource_version` | 包/Schema/Policy 资源版本与兼容边界 | 待目标适配设计 |
| `initialization` | 只读预览、非覆盖合并、新 repository identity、幂等重入 | 未冻结 |
| `location` | 根目录、子目录和 worktree 的定位及同一身份规则 | 未冻结 |
| `verification` | 目标自己的完整检查及映射；不能用本仓检查替代 | 未冻结 |
| `recovery` | 中断/升级失败的可执行恢复和归属 | 未冻结 |

候选验收应证明既有文件与未提交修改保留、重复执行不覆盖、不扩大权限、身份重新生成、
版本不兼容零写拒绝、失败可恢复。不得复制本仓历史 task、身份、批准、evidence、维护
模式标记或模型账号配置。依据为[外仓产品化最小要求](../superpowers/plans/2026-09-12-harness-model_cross-agent_review-fix_plan_2026-09-12.md#83-外仓产品化的最小要求)。

### 2.2 provider

最小交付物为一次只选择一种接口的只读调用合同。手工获取原件的实际困难可以作为
需求输入，但不能据此默认选择无头 API、付费渠道或自动重试。

| 拟合同字段 | 草案语义 | 待决事实 |
| --- | --- | --- |
| `business_need` / `interface` | 明确要替代的手工步骤、接口与官方版本依据 | 实际接口与必要性 |
| `input_binding` | repository、stage、base、subject 的适用规则及冻结 context 引用 | 目标和受控输入 |
| `source_identity` | 产品/接口版本、session/ref、报告原件及实际身份依据；不明为 unknown | 可核实 provider/model/backend 事实 |
| `data_boundary` | 允许发送的文件/片段、脱敏与禁止发送的数据 | 具体数据范围及授权 |
| `cost_boundary` | 订阅/credits、API 与 CI 分开；金额来源、币种、实际/估计及上限分开 | 费用来源、预算和动作授权 |
| `lifecycle` | 超时、取消、partial、未回结果、分页、来源编辑和重复结果 | 接口真实可强制能力 |
| `failure_preservation` | 失败/取消原件、有限重试原因及状态保存；无结果不等于零 Finding | 重试规则和恢复归属 |

准备阶段只列接口验证问题和离线反例；真实发送、身份/费用采集及付费调用均留给实际
候选准入。一次 UI 发送不直接等于一次 inference，也不能证明费用封顶。静态工具选择
不建立模型排名、自动竞价或信任评分。

### 2.3 可信执行

最小交付物为一种固定动作的服务授权消费合同，而非自由 shell 或通用远端执行器。
实际动作与资产尚未选择。

| 拟合同字段 | 草案语义 | 当前缺项 |
| --- | --- | --- |
| `principal` / `identity_root` | 可认证执行者与批准者、身份根及认证事实 | 未建立 |
| `authorization` | 服务端决定、允许动作、目标资产、固定参数、期限、撤销与版本绑定 | 未冻结 |
| `consumption` | 原子一次消费、重复/重放/过期拒绝，消费后崩溃的状态规则 | 未建立 |
| `credential_custody` | 凭据托管、最小权限、禁止导出和调用方不可见边界 | 未选择 |
| `audit` | 不可变输入/决定/消费/结果链及原件定位 | 未建立 |
| `recovery` | 已消费但结果未知、部分完成、重入和恢复责任；不自动重新消费 | 未冻结 |

候选验收应覆盖错误目标/版本、过期/撤销、参数漂移、重复消费、授权后版本变化及消费
窗口崩溃；当前[Hook 边界](hooks.md)和本地 actor/approval 不证明上述能力已存在。
可信执行不依赖 provider 必然先落地，也不因 runner 已接入而自动完成。

## 3. Phase 3 样本、隐私与偏差合同草案

草案版本标识拟为 `phase3-sample-proposal-v0`，仅作审阅材料。没有已冻结的 Phase 3
样本阈值；现有任务数量不能单独证明对任务类型和角色的区分充分。

| 拟字段 | 草案内容 | 冻结前待决事项 |
| --- | --- | --- |
| `contract_version` / `dataset_id` | 合同版本、数据集标识、生成时间和来源快照 | 版本维护与责任人 |
| `source_refs` / `source_hashes` | 原 task/review/evidence/ref，公开摘要与私有原件各自绑定 | 授权输入范围与可读性 |
| `observation_window` | 开始、结束、纳入的 Policy/工具/契约版本 | 窗口长度和版本漂移处理 |
| `sample_unit` / `attempt_links` | 建议以任务阶段及固定受审版本为主单位，关联其检查/修复尝试 | 独立性规则；不能把重试、多个 Finding 或文档提交直接算为独立样本 |
| `inclusion` / `exclusion` | 纳入/排除原因逐条保留，失败、取消和未运行不消失 | 代表性总体及排除标准 |
| `strata` | 任务类型、route、V 等级、阶段/角色、平台、工具环境、证据等级 | 每层应覆盖的类型与充分性 |
| `identity_evidence` | task-local 标签、独立会话、实际身份依据分开 | 可认证范围；未知身份不默认等同 |
| `sufficiency_rule` | 数量规则或可判定充分性规则及每层检查方法 | 阈值、统计精度或判定规则均待决 |
| `missingness` | 每字段显式 unknown/null、缺失原因、每层缺失分布 | 是否允许进入后续分析的边界 |
| `bias_checks` | 幸存者/选择偏差、重复相关、版本漂移、平台 skip、角色与模型相关错误、取消/未运行 | 检查责任、接受标准及不充分时处置 |
| `privacy` / `access` | 可公开字段、脱敏方法、保管者、访问角色与控制证据 | 实际控制机制及授权 |
| `retention` / `disposal` | 新 telemetry 副本的保留与处置、源证据的追加式保全 | 保留期和副本处置待决；不删除既有 task/失败原件 |

候选偏差报告先给原始任务数、各层覆盖/缺失和证据状态，不计算成功率、效果百分比或
因果结论。多个名字不证明独立执行者，同一模型换角色也不证明错误不相关。历史/current、
local/CI、pass/fail/skip/未执行分别保留。

隐私草案沿用[现有边界](effect-observations.md#保存与隐私边界)：tracked 文档只放方法、
可公开脱敏摘要和提交/PR 引用；原始聊天、身份、凭据、逐次会话和运行日志留受控材料，
不提交机器名、用户名或本机绝对路径。该草案不新增私密采集、身份采集或费用采集。

## 4. 版本化 telemetry 实际字段草案

草案版本标识拟为 `phase3-telemetry-proposal-v0`。它引用现有原件，既不向旧 Schema
追加字段，也不建立第二套权威 task 账本。正式合同的治理影响、兼容性与实现路径待
准入时评估。

| 字段组 | 现有可复用事实 | 拟新增统一字段与语义 | 当前实际缺项 |
| --- | --- | --- | --- |
| 记录来源与版本 | task/review/evidence 原件及其 hash/ref | `observation_id`、`contract_version`、`recorded_at`、`source_refs`、`evidence_status`、`previous_observation_id` | 没有统一观察合同与修订关系 |
| 对象绑定 | task_id、repository_id、stage、base/subject、spec/Policy/context、review revision | `sample_unit_ref`、`attempt_id`、`parent_attempt_id`；分别引用实际验证和交付版本 | 尝试/任务阶段的统一关联未冻结 |
| 角色与身份 | task-local actor/reviewer；外部产品/报告版本/raw hash | `role_label`、`session_ref`、`product`、`reported_model`、`verified_model`、`reasoning_effort`、`backend`、`identity_evidence_refs`、`identity_evidence_level` | 标签不是认证；真实模型/backend/档位可能 unknown |
| 费用与调用 | 尚无统一计费来源 | `charge_kind`、`billing_ref`、`amount`、`currency`、`measurement_kind`、`call_count`、`token_counts`、`cost_evidence_refs` | 订阅/credits/API/CI 归属、实际金额与调用事实缺失；估计不得冒充账单 |
| 时间 | verification check 的 duration_ms、exit、timeout | `check_duration_ms`、`wall_clock_wait_ms`、`human_work_minutes`、`time_source_refs` | 人类工作分钟和等待归因 unknown；预算不是实际消耗 |
| 返工 | Finding、失败、修订及后续验证原件 | `rework_trigger_refs`、`before_commit`、`after_commit`、`attempt_count`、`work_minutes`、`attribution`、`attribution_evidence_refs` | 实际工作量和归因未统一；失败/重试次数不等于返工次数 |
| 审核缺陷 | 原生 severity、原外部 source_priority、Finding 状态/ref | `original_severity`、`normalized_severity`、`mapping_version`、`mapping_reason`、`duplicate_of`、`observation_window`、`escape_source_refs` | 严重度映射、重复口径和交付后观察未冻结；resolved 不转换原 review outcome |
| 工具失败 | check status、reason、exit_code、timed_out、日志、失败 receipts | `original_status`、`failure_class`、`failure_evidence_refs`、`retry_reason`、`retry_of`、`completion_scope` | 统一分类和跨工具映射未冻结；cancelled、partial、未启动和 unknown 均保留 |
| 缺失与隐私 | 现有 unknown 与脱敏原则 | `missing_reason`、`redaction_rule_version`、`access_policy_ref`、`retention_rule_ref`、`custodian` | 缺失值、访问机制、保留期尚未冻结 |

拟用的证据状态为“可复核 / 仅项目记载 / 缺失 / 不适用”，不得把无原件的完成声明标为
可复核。拟缺失原因包括未记录、不可访问、已脱敏、不适用及未知；每个原因都需要明确
字段适用性，unknown 不填默认分数、0 或模型排名。

工具失败的候选类别为代码/断言、环境/工具、契约不一致、权限或 Policy 拒绝、真实
timeout、取消、partial、未启动和 unknown。分类保留原 status/原因与证据，不用后来
成功覆盖原失败；真实超时必须同时核对值、单位和当时阈值。

依据包括[现有观察模板](effect-observations.md#下一批真实工作如何观察)、
[review Schema](../../.ai/schemas/review-record.schema.json)、
[evidence Schema](../../.ai/schemas/evidence.schema.json)及
[外部报告 Schema](../../.ai/schemas/external-review.schema.json)。现有 Schema 严格拒绝
未声明字段，本草案不改变其含义。费用、模型身份、真实返工、人类工时缺证据时保持
unknown；不通过读取旧私密聊天或重新调用模型补齐。

## 5. 真实 V3 用例、损失与恢复选项

现行[verification Policy](../../.ai/policy/verification-levels.yaml)与
[evidence Schema](../../.ai/schemas/evidence.schema.json)只提供 V0/V1/V2，当前不存在
可直接运行的原生 V3 检查链。候选用例必须在进入设计时评估 Policy、Schema、原生
验证/批准与兼容性；V2、定向变异、Hook、元数据和私有 qualification 不称为 V3。

| 选项 | 真实需求与用例候选 | 拟资产/故障边界 | 拟 dry-run 与可执行恢复 | 实际缺项与损失决定 |
| --- | --- | --- | --- | --- |
| A：Windows 清理生产化候选 | 当前 ProcessRunner/helper 生产化待办存在真实风险，可作为优先讨论的 V3 候选；[私有资格结果](windows-private-timeout-repair-2026-10-04.md)仅是输入 | 专用一次性 VM 内明确所有权的进程树、Job 和测试盘；故障必须证明 OS 条件及来源，mock 不替代真实异常 | 先核固定安全基线与 VM 边界；恢复方案为已核验 snapshot/重建及明确残留资源核对；UNKNOWN、保留资源与原回执不被抹去 | VM/运行时、实际故障、资产清单、备份可读性、恢复目标/时限、停止触发、证据矩阵、逐动作批准均未冻结；可损失进程/测试盘和损失上限待决 |
| B：隔离 runner 生命周期 | runner 22 offline 提供可选真实恢复需求；只有选择生命周期/升级风险后才成为 V3 候选 | 隔离 VM 内的一个固定 runner/runtime 副本；禁止触碰繁忙 Windows runner 21、生产服务及原凭据 | 对停止/更新/启动的固定动作先 dry-run；恢复旧固定运行时与实例配置，再完成原业务完整检查 | 是否选择恢复、故障原因、隔离方式、服务身份、版本与业务验证未决定；允许暂时不可用范围、恢复目标/时限和损失上限待决 |
| C：暂不选 V3 执行对象 | 当资产与恢复证据不足时，完成合同和候选清单，等待自然高风险任务 | 不执行故障或真实恢复 | 无 V3 执行，不补造退出证据 | 真实用例门保持 not_met；不能因此宣布 Phase 3 准入 |

任何选择都须形成一个固定用例包：任务与风险理由、资产/保护对象、实际故障模型、
沙箱隔离与其限制、dry-run、备份与可执行恢复目标、损失边界、停止触发、逐动作批准点、
独立验证与退出条件、原始流和摘要定位。恢复时限、预算和损失上限全部待决。

用例与边界先冻结，真实 V3/回滚执行证据在合法实施后形成，并用作 Phase 3 退出；
不能先运行未准入 Phase 3 再声称补齐进入门。Worktree 不充当 OS 安全沙箱。

## 6. Phase 4 证据仍未满足

| 进入事实 | 本轮结论 | 现有材料的实际限制 |
| --- | --- | --- |
| Phase 3 完整真实退出 | `MISSING` | Phase 3 not_started，未有真实 V3/回滚、可审计模型选择与退出记录 |
| Phase 1–3 接口稳定 | `PARTIAL / NOT_MET` | 当前阶段二接口可作基础；未来 Phase 3 尚未设计/发布，不能证明整体稳定 |
| 量化人工协调成本 | `MISSING` | [效果观察](effect-observations.md#尚不能得出的结论)明确人类打断、工作分钟、真实返工与缺陷率 unknown；账本数字不是人工协调成本 |
| 真实暂停/恢复和集中审批需求 | `PARTIAL / NOT_MET` | 有历史恢复与当前离线事实；尚无按统一窗口归因的需求记录与充分性证明 |
| 单机控制面/真实 adapter 强制能力 | `MISSING` | 已有设计蓝图不是执行结果，也不证明队列、锁、租约、调度或配额继承 |
| 独立规格与 scope decision | `MISSING` | 当前只整理准备提案，不创建阶段四治理 Task |

[本机防护蓝图](../superpowers/specs/2026-08-13-local-agent-overload-protection-blueprint.md#2-不可越过的进入门)
保留既有初始标准：连续 30 天或 30 个受治理任务的协调记录，并满足过载事件、协调
时间比例或资源争用比例之一；至少三个真实暂停恢复/集中审批需求，以及两个兼容发布
候选等。当前未找到其满足证据。本提案不改变这些既有数值，也不把它们挪用为 Phase 3
的已冻结样本阈值。进一步的窗口、度量和接受口径需要明确当前适用决定；Agent 不自行
降低旧标准或以样本计数替代实际协调成本。

[自适应蓝图](../superpowers/specs/2026-08-13-adaptive-agent-orchestration-blueprint.md)
还有控制面试点、真实 adapter、held-out 资源样本和身份/费用注册表等额外门，均不能
提前实施。旧固定主/子型号及档位的处理依[当前型号规则](model-selection.md#历史记录)，
不为解除历史漂移恢复旧型号，也不因此把阶段三/四门判为通过。

## 7. 待决项与下一顺序

| 决定 | 当前候选 | 尚需具体化的内容 |
| --- | --- | --- |
| I1 | runner 22 恢复或保留离线 | 实际所有权/状态、生命周期动作、保护对象、幂等、业务完整验证、回退和授权 |
| I2 | 新可信目标尚未选择 | 一目标需求、平台/权限、等价检查、准确候选、独立准入与回退 |
| E5 | 三线需求分别选择 | 引擎目标/provider 接口/固定服务动作、身份/数据/凭据、费用与预算 |
| 样本 | 数量规则或可判定充分性规则 | 观察窗口、各层覆盖、独立性和接受标准；阈值待决 |
| 隐私 | 沿用原件私有、公开脱敏摘要 | 实际访问控制、保管者、新副本保留期；保留期待决 |
| telemetry | 采用本草案字段组后再正式设计 | 权威字段映射、缺失语义、严重度与失败分类、实际来源、兼容与治理影响 |
| V3 | A、B 或 C | 固定资产/故障、沙箱、备份、恢复目标/时限、损失上限、预算与逐动作批准 |
| Phase 4 | 保持证据准备 | Phase 3 退出、稳定接口、当前协调成本证据和真实需求，不启动控制面 |

准备阶段的 E5 三线、样本/隐私、V3、telemetry 和 Phase 4 证据矩阵是 7 条可独立
研究的工作流；如另行采用该准备分工，计划使用 7 名 sub-agent，各自产出独立材料，
不同时修改共同权威入口。本轮本文件由一个写入者负责，不代表已经启用该分工。

需求方向选择 → 合同/边界冻结 → 设计与 Policy 影响评估 → 独立 task 准入和实际
Missing 所需决定 → 实施 → 具体动作 → 验证/退出依次串行。E5/I5 准备不依赖 F
验收完成；正式执行不能借 F、旧任务或已消费 action 的批准越过各自门。

本文件完成的仅为可审查需求与合同草案。没有冻结阈值、保留期、预算或损失数值，
没有新增采集、provider、训练、模型排名/路由、可信执行、V3、调度或跨主机服务。
