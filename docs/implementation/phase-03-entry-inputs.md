# 阶段三进入输入

本文档只整理阶段二结束后可审计的进入事实，不是阶段三设计或执行计划，也不授权实现
V3、模型调用/路由、信任评分、成本优化、资源调度、沙箱或任何外部动作。阶段三仍为
`not_started`；必须先满足下列进入门，再单独形成设计、Policy 影响评估和实施目录。

## 进入门现状

| 进入条件 | 当前结论 | 已有事实 | 仍缺少的证据 |
|---|---|---|---|
| 已积累足以区分任务类型和角色的内部记录 | `partial` | `.ai/tasks/` 已保留 AUTO、ASK、REVIEW、BLOCK、V0/V1/V2、审核、升级和失败重试记录；阶段二证据索引给出可重放入口。 | 尚未冻结“足够”的样本量、任务/角色分层、保留期、隐私边界和偏差检查；actor 仍只是 task-local 标签，不是身份或模型认证。 |
| 存在明确的真实 V3 用例 | `not_met` | 阶段二证明了 V2、定向变异和受限 Hook/CI fail-closed 语义。 | 尚未选择需要安全检查、故障注入、dry-run 与回滚演练的真实高风险任务，也没有批准的沙箱、回滚目标或损失边界。 |
| 费用、返工、审核缺陷和工具失败有统一采集口径 | `not_met` | task ledger、结构化 review findings、verification checks 和失败 receipts 已分别保留部分事实。 | 尚无统一版本化 telemetry contract；没有模型调用/费用来源、返工归因、缺陷严重度归一化、工具失败分类和脱敏/访问规则。 |

因此阶段二完成只解除“先完成可靠 V2 闭环”这一依赖，不自动打开阶段三实现门。

## 可作为后续设计输入的阶段二事实

| 输入 | 可复用事实 | 不可扩大解释的边界 |
|---|---|---|
| 结构化双阶段审核 | Chapter 8 的 hash-addressed context、append-only review/revision 和 freshness 可作为缺陷记录的基础。 | finding 不能直接推断模型能力、人员能力或因果归因。 |
| V2 与独立 Verifier | 已合并 TASK-0025 原 subject 的历史 final V2 evidence 包含 acceptance、integration、五项 killed mutation、独立 actor/context 和零 unverified；TASK-0028 保留 local/CI 分离及历史 CI/Gate receipt。 | task-local actor 不是外部身份认证；历史通过不能复用于新 subject，也不能冒充 V3。 |
| 失败与恢复记录 | TASK-0025 的一次 H2 verification failure、TASK-0028 的失败 CI attempts 与后续成功 receipt 都保持追加式，可用于定义工具失败和重试分类。 | 这些少量样本不能直接形成成功率、置信度或自动重试策略；失败不得被后续成功覆盖。 |
| observation 与 Hooks | Chapter 12 证明支持范围内的 observation-to-escalation/refusal 以及 Hook/CLI/CI decision semantic parity。 | 未证明跨平台 live Hook、全部客户端、自由 shell、通用命令拦截或 OS sandbox。 |
| 资源与并发设计输入 | 现有资源感知设计和两份预进入蓝图可提示需要采集的 CPU、内存、I/O、租约和协调成本事实。 | 它们不是阶段三/四执行授权；当前没有资源调度器、DAG、抢占或跨主机编排。 |

逐项实现、测试、历史/current 绑定和复现命令见
[阶段二验收矩阵](phase-02-acceptance-matrix.md)与
[阶段二证据索引](phase-02-evidence-index.md)。

## 满足进入门后才可创建的产物

1. 版本化 telemetry contract：定义任务/角色、模型与推理档位、费用、返工、review finding、
   tool failure、隐私和保留规则；缺失值必须显式，不得以默认分数代替。
2. 一个真实 V3 用例与沙箱/回滚边界：给出资产、故障模型、dry-run、备份、恢复目标和每个
   高风险动作的独立批准点。
3. 阶段三设计和实施目录：重新评估 Policy、Schema、兼容性、迁移、验证矩阵和非目标，
   并保持 route/V 与硬风险规则不可被信任度或成本评分覆盖。
4. 模型能力与选择方案：只能基于已定义的数据口径给出可审计理由；在真实 adapter、费用来源
   和身份绑定建立前，不得宣称自动模型路由已经可用。

## 当前禁止声明

- 不得把阶段二的 V2、targeted mutation 或 observation 称为 V3、安全沙箱或回滚演练。
- 不得把 Codex/Claude/其他模型的配置文件、线程名或 actor label 当作模型能力注册表或身份认证。
- 不得依据现有少量历史 task 自动计算信任度、成功率、预算或最优模型。
- 不得自动 push、merge、deploy、delete、导出凭据、发起付费调用或操作外部系统。
- 不得绕过当前生效的 AI Flow 自用治理。`.ai/bootstrap-mode.yaml` 的状态只由项目所有者
  决定：本文写作时 bootstrap 已结束，此后所有者又明确决定重建该标记并进入仓库维护模式
  （TASK-0038，见 `AGENTS.md` 与 `README.md`）。无论该标记处于何种状态，都不授权阶段三
  实现或任何外部动作；Agent 不得自行重建或移除它。
