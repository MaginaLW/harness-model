# 自适应多智能体编排预进入设计蓝图

> 日期：2026-08-13
> 状态：`pre-entry / not_authorized`
> 文档性质：阶段四后半段执行计划的设计输入，不是可执行计划，不授权接入编排模型或真实 worker

## 1. 蓝图目的

本蓝图定义：在[本机智能体过载防护蓝图](2026-08-13-local-agent-overload-protection-blueprint.md)已经通过正式实施和真实试点后，如何把“指挥官”以无授权的编排顾问接入确定性控制面。它保留任务理解、DAG 建议和关键路径优化的价值，同时保证 AI Flow 与 Scheduler 仍是唯一治理和资源裁决者。

本文不提前拆分阶段四代码任务。达到进入门后，必须依据届时运行时能力与代码结构新建独立执行计划；本蓝图的工作包只用于检查该计划是否覆盖关键风险。

## 2. 额外进入门

除本机防护蓝图第 2 节的全部阶段四进入条件外，还必须满足：

1. 单机控制面已经发布，并在至少 30 个受治理任务或连续 30 天内没有资源安全/Gate 逃逸；
2. GREEN/AMBER/RED/PROTECT、leader 重启、旧 worker、orphan、冲突锁和 callback 认证均有真实或受控试点证据；
3. 至少一个真实 adapter 已证明 `can_enforce_spawn`、可观察完整生命周期且所有后代继承 root 配额；若没有，编排只允许影子模式；
4. 每个拟优化的角色 × 模型 × 工具环境至少有 100 个独立 held-out 资源样本；样本不足的组合保持 conservative，只做影子评估；
5. 模型身份、推理档位、backend、费用和工具环境有版本化注册表，版本变化能自动使 capability 和评估失效；
6. 新建独立 `REVIEW` scope decision，列出真实模型/adapter、最大 Token/费用、只读与写入边界、试点仓库和禁止动作；
7. 任何真实模型、外部 worker 或付费调用另有绑定脚本、预算、Policy 和 `subject_commit` 的动作批准。

## 3. 候选交付序列

### A1：无授权的编排顾问契约

交付：只读、窄职责的顾问角色与 `untrusted_proposal` 契约。提案包含候选 DAG、依赖、资源等级、关键路径、假设和置信度，但只引用已存在的批准 ID。

必须拒绝：顾问自提优先级、扩大路径/预算、降低 route/V、声称未知 adapter 可终止、直接要求 spawn、把 Luna 标为 native，以及在资源压力下建议绕过控制面。

### A2：确定性 DAG 编译和并行资格证明

交付：把冻结规格、决策单元、允许范围、批准、能力注册表和不可信提案编译成版本化 ExecutionPlan。

每条并行边必须证明：无数据依赖、无 worktree/文件/端口/缓存/数据库冲突、上下文可分离、adapter 可观察、节点可独立验收且容量已知。缺少证明就拒绝或稳定串行化；顾问不存在时，人工 DAG 仍可工作。

### A3：版本化资源估计和离线回测

交付：可解释的分位数估计、分组回退、候选画像和 held-out 报告。自适应输出只能生成候选 Policy，不能在运行中改写硬阈值。

统计门：每个可提高并发的画像使用至少 100 个独立 held-out 样本；资源 reservation 的 held-out 低估事件要求为 0，使单侧 95% 二项置信上界低于约 3.7%。若出现低估、数据漂移或样本不足，继续使用旧 conservative profile。该门衡量观察窗口，不构成未来绝对保证。

### A4：关键路径、预算和公平性影子策略

交付：只读影子排序、父子预算 reservation/reconciliation、关键路径 tie-breaker 和与现行策略的 A/B 报告。

关键路径不能改变 Policy priority class。`safety_recovery` 保持严格优先；其余类别和 root/repository 使用主设计定义的加权 DRR 与 aging。用量或费用未知时停止下一付费 route，不能按 0 结算。

### A5：真实 adapter 能力验证

交付：针对 Codex native、外部 worker 和独立 Luna 的版本化 capability report。能力必须来自观察到的线程身份、后代事件、interrupt/resume、进程归属和回调测试，而不是提示词声明。

只有证据证明 direct spawn 可截获的 adapter 才能 `enforced`。否则调度器只能保证自己不再启动第二个受管 worker，任务 evidence 标记 `advisory_unenforceable`，并通过操作层禁用嵌套/自动 spawn；它不能满足全树强制计数的发布门。独立 Luna 始终为 `native_subagent=false`。

### A6：影子评估和逐级真实试点

交付：代表性 workload、至少 50 个真实 chronology 的影子对照、受控 adapter 试点和独立复核。

发布候选要求：安全和治理违规为 0；资源统计门通过；后台服务门不退化；p95 makespan 至少改善 10%，或相同 makespan 下 Token/费用至少降低 10%；每个决定可复放。没有效率收益时不发布，但绝不能为达到收益放松安全。

## 4. 正式执行计划必须冻结的内容

阶段门满足后，新计划至少列明：

- 顾问可读取的最小上下文、模型、推理档位、sandbox 和不可用工具；
- proposal 与 ExecutionPlan 的完整 Schema、对抗 fixture 和稳定错误码；
- 训练/校准/held-out 时间窗口、去重、漂移检测和隐私过滤；
- 现行与候选调度 Policy 的摘要、影子期和 REVIEW 激活流程；
- 每个 adapter 的运行时版本、强制能力、过期条件和逃逸测试；
- nested descendant、跨会话、迟到回调、身份不匹配和费用未知的测试；
- `aiflow start --objective`、逐项 `--allow`/`--forbid-action`、verify/Gate 和提交证明；
- 真实模型与费用预算的单独动作批准。

## 5. 候选退出标准

1. 顾问无 spawn、租约、Policy、批准、优先级或 Gate 权力；移除顾问不影响人工计划执行；
2. 相同冻结输入产生相同 DAG 和影子报告；提案顺序变化不改变结果；
3. 所有并行边具备可审计证明；未知项稳定串行化；
4. 自适应画像通过 held-out 统计门，未通过组合不提高并发；
5. 候选 Policy 先影子、再 REVIEW、再版本绑定，不在线自改；
6. 真实 adapter 的后代全部计入同一 root 配额；不能证明时明确降级且不夸大保证；
7. Luna 身份、外部 worker 顺序 fallback、quota 证据和 Sol 最终复核未被放宽；
8. 效率指标有改善且安全、公平、费用和审计指标无退化；
9. 多机调度、自动购买和未经批准的付费调用仍在范围外。

## 6. 当前禁止动作

本文当前不授权：创建顾问配置或代码、调用任何模型、接入 Codex/外部/Luna worker、修改 scheduler Policy、运行真实试点、消耗付费预算、读取凭据、修改阶段一状态、推送、合并、部署或删除。
