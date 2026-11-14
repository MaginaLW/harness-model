# 维护收尾与待办

## 当前状态

本页只回答当前能力、版本、阻塞和下一步边界；规则以 [AGENTS.md](../../AGENTS.md) 为唯一权威，操作流程见[低干预工作方式](low-intervention.md)。历史计划和 NEW/BLOCKED 任务不是执行队列。

**当前方向：仓库维护。** 入口治理和已授权的维护收口已完成，后续按具体需求或可复现问题推进；Stage B、旧 mutation 加固、真实评分、自动审核、Desktop 附着及 Phase 3/4 继续暂停。维护交付不自动恢复这些工作，Policy、授权和质量阈值保持不变。

**治理资料归属**：[治理建议](HARNESS_MODEL_GOVERNANCE_RECOMMENDATIONS.md)与[执行计划](HARNESS_MODEL_GOVERNANCE_EXECUTION_PLAN.md)已从 dotfiles 归入本仓，原文按规划时点保留；其中“待执行”“本次未执行”描述原文编写阶段。实际治理已由 [PR #154](https://github.com/MaginaLW/harness-model/pull/154) 合入：P0/P1/P2/P5 收口，P3/P4 按证据不实施；入口固定集合字符减少 53.62%，实际 token 与自然任务工时效果未测。Stage B 与旧加固仍停止。

### 版本与用途

| 对象 | 固定版本与用途 | 可用结论及限制 |
|---|---|---|
| 状态核对基线 | main `94fa84dce452a08e682a838ffd8b1a8d2b84e571`，已含 PR #157 的维护变更与 PR #158 的任务关闭记录。 | 已合并代码与下述候选分开；源码包与安装包不能只按相同版本号互相认证。 |
| 原主根与旧 WIP | `codex/agent-bridge-phased-adoption` / `4ab57ce5b0291ec2841c90782a751c920e284403`；仍属原任务，非本轮写入对象。 | 八个暂存 mutation/schema 文件、TASK-0094/0095/0124 及三份未跟踪建议稿保留。本轮已核对路径和内容校验值；不得整文件覆盖、stash、reset、clean 或当作重复删除。 |
| 已验收本地候选 | 普通安装候选 `c60b663427e73ca2d551d7a9aca2dc68b443c954`；Stage A 自有治理根。 | 原记录报告本地采用通过，不代表本维护基线含有全部候选代码，也不代表 Stage B 验收。 |
| source6 发布候选 | `5ce4cbd841a4656d346c9b17938a0b42d5f1d897`；[PR #150](https://github.com/MaginaLW/harness-model/pull/150)。 | 原记录报告 Native、7354 项测试/9 项跳过、变异及源 Gate/CI 通过；本轮未重验，不扩大为 main 或目标消费成功。 |
| 已停止消费候选 | agent-bridge TASK-0017 / REVIEW / V2；原独立目标根及原任务所有者保留现场。 | 原记录为 BLOCKED，Missing: block_resolution；历史干净封账 `d1fbd37a7df351610021b0a4a509073a573d8cab` 属较早窗口，不冒称 probe5 后新 HEAD。 |

### 已完成的维护收口

[PR #157](https://github.com/MaginaLW/harness-model/pull/157)已合并 Windows 新任务事件的规范 UTF-8/LF 字节修复、clean-checkout 的 Git/构建/安装/CLI 配置隔离及离线 wheel 验收，并保留资源包规范化与大小限制说明。TASK-0149 的独立设计与实现审核通过，原生 Windows V1 的十项检查通过（6507 passed、9 项条件跳过），本地 Gate 与当前候选 required CI 通过；[PR #158](https://github.com/MaginaLW/harness-model/pull/158)已合并任务关闭记录，账本状态为 MERGED。证据见[任务记录](../../.ai/tasks/TASK-0149/task.yaml)与[验收索引](../../.ai/tasks/TASK-0149/evidence.json)，原始日志仍在实际验收克隆中。

[草稿 #128](https://github.com/MaginaLW/harness-model/pull/128)和[草稿 #131](https://github.com/MaginaLW/harness-model/pull/131)已由上述交付替代并关闭，未合并旧候选，原分支和失败材料保留。配置隔离不提供 OS 沙箱，也不清除所选 HEAD 自身可达的历史；超时不证明全部后代已停止。

[PR #149](https://github.com/MaginaLW/harness-model/pull/149)已因后继替代而关闭，未合并：只读 Git 保护已由 [PR #151](https://github.com/MaginaLW/harness-model/pull/151)以子进程环境 `GIT_OPTIONAL_LOCKS=0` 交付，LF 修复由 PR #157 交付。旧分支、TASK-0139 的 FAILED 状态、失败原件和缺失验收继续保留；关闭不表示旧候选验收通过，后继证据不能移用于该候选。[PR #150](https://github.com/MaginaLW/harness-model/pull/150)仍打开且未合并，目标 LOCAL、私有 CI 与 combined 验收仍未完成。

### agent-bridge 阶段 B 当前收尾

**完整接入未完成，最新手动主探针5失败后已封账停止。** 最新失败为 L exit1、空 `AssertionError`，仅能定位至启动身份/绑定区域；具体断言和根因仍 UNKNOWN。临时 Process 策略已恢复；N 不存在、L 退出不能证明 carrier 独立性或 owned cleanup。

原件静态核对已确认，准备材料的前驱链声明与 supervisor、controller 两处检查引用的前驱层级不一致。在固定维护基线 `bdd4fef3e1ae4a331c738e07e932c4749cd05c0c` 的 `src`、`tools`、`tests` 中按精确名称核对，未发现这些私有 helper 的生产消费者，本轮 P3 生产代码修改不实施。私有修复留待原工作线恢复时核定。原执行缺少 traceback，历史实际首个异常断言仍为 UNKNOWN。静态诊断回执保留在原主根的 `build/co/campaign/stage-b/target-subject-recovery/diagnosis/static-binding-review.json`。

累计 probe5/5、policy7/8、Set14/16。LOCAL14、产品 record/verify、PR3 新同步、私有 CI 和 combined Gate 均未启动。源/目标的旧消耗、失败、UNKNOWN 与全部资源上界保留，剩余预算和未用槽位不恢复执行许可；不修复后重跑、不提出新恢复轮。PR150/PR3 在原停止记录中保持打开，本文不冒称已合并或实时远端状态。

本地失败原件：`build/co/campaign/stage-b/target-subject-recovery/probe-failure-closeout.json`（忽略目录，不能随公开文档发布）。旧根、空 worker 目录和全部原件不动。精确历史计数、额度、候选与 Windows 边界见[接入计划](../superpowers/plans/agent-bridge-integration.md)，两者均不批准恢复。

## 剩余建设主线

### 当前能力进度

| 能力 | 已有结果 | 尚缺或保持暂停 |
|---|---|---|
| Phase 1/2 治理基础 | 确定性分流、版本绑定、结构化审核、V2、独立 verifier、required CI；维护模式以 AGENTS 为准。 | 无 V3、通用命令拦截、OS 沙箱或可信动作执行；批准文字不是运行时强制。 |
| 非评分准备（S0/S1） | [事实快照](effect-observations.md#固定提交的事实快照)、[正式账本回读](review-feedback.md)、[PR 回读](pr-feedback.md)、[只读建议](review-advisory.md)。 | 来源认证、实际身份、人时/费用、独立真值和原子一致性仍有 unknown；记录数不是独立样本。 |
| 离线工具（S2 局部） | [公开外部参考](benchmark-reference.md)、[输入检查与原件定位](review-detection-input.md)、[区间计算](review-detection.md)、[合成分析](review-detection-analysis.md)、[合成反馈](review-feedback-simulation.md)。 | synthetic 结果不能改标为真实数据；尚无生产评分、校准或自动路由效果证明。 |
| SDK | [单次文档审核及可选上下文节点](../superpowers/specs/sdk-readonly-review.md#使用)已交付。 | 默认关闭；一次真实审核不证明长期效果，新实际调用需明确任务、输入与范围。 |
| 跨仓引擎 | main 已合并[资源包](resource-bundle.md)、[非覆盖初始化](initialization.md)、[Node 本地 V0/V1](node-verification.md)与 [installed 变异切片](https://github.com/MaginaLW/harness-model/pull/147)。 | 后续本地 V2/source6/Stage A 按上表独立候选读取；Node CI 与目标 combined 验收未闭合。 |

### 既定离线范围的收口

现有离线范围已交付；没有新增必做准备队列。具体新需求或可复现问题才触发受影响部分的修改和检查；复用现有接口，不为填队列增加采集器、Schema 或服务。

### 剩余缺口与推进条件

- **真实观察**：B（3-A 非评分准备、3-B 独立 V3）、首用途、`review_detection`、95% 等尾区间/总宽不超过20个百分点及有限研究范围已采用，不重复请求这些决定。真实自然任务的预声明候选、旧契约、实际输入/职责/原预算、完整报告、独立裁定与预算关闭原件仍缺；`T0/T1` 未设置，不制造样本、不启动30日窗口。见[观察准备](review-detection-preparation.md)、[准入](../superpowers/specs/review-detection-admission.md)。
- **宿主接入**：仍缺受支持的既有 Desktop 通道、实例绑定、实际 server/协议版本、全部返回面及接收前累计限制。既有[issue #55904](https://github.com/openai/codex/issues/55904)是回复入口，未在本轮重查回复；不重复提问、不重启已关闭读取。新材料按[核对步骤](../superpowers/specs/review-detection-host-evidence.md#维护方回复后的核对步骤)处理，齐备也不自动连接。
- **Phase 3/4**：Phase 3 仍 `not_started`；[进入输入](../implementation/phase-03-entry-inputs.md)的样本门 partial、真实 V3/统一度量 not_met 保留。3-A 单独完成不打开整体退出或 Phase 4。
- **旧 mutation 加固**：TASK-0094 范围扩大后 BLOCKED；TASK-0095 尚待规格审核，私有 CI 原件传递/重放、Ubuntu 进程树约束和旧账本隔离三个 medium 发现未关闭。旧核对仅证明 c60b663/a231941 未覆盖八文件 WIP；本轮未独立比较 source6，不能推断可丢弃；旧探针绑定有漂移，恢复前须重新核定规格、材料与消费者。TASK-0124 的资源包目标已有后继交付，旧 NEW 不倒填成功。
- **恢复决策**：本轮只完成治理；是否恢复 Stage B 或旧加固，由所有者另行决定具体目标、基线、风险和额度。治理过程中没有新授权缺口需要用旧预算填补。

## 条件性能力

完整引擎产品化、provider、固定动作可信执行及 V3 均按真实需求分别准入，详见[合同提案](phase-entry-proposals-2026-10-04.md)与[两条路线](sdk-and-engine-plan.md)。Phase 4 另依赖整体 Phase 3 退出、稳定接口及实测协调需求。旧蓝图与宿主并发额度不是实现或运行许可。

## 旧工作线与证据边界

TASK-0063～0071 已归档，历史七项未全部验收，均不默认续跑。四条 pilot 验收分支、全部 archive refs、用户草稿、原失败/SPENT/partial/unknown、既有批准及编号保留。`archive/local-task0079-private-evidence` 含私有失败材料，不直接合并或公开推送。历史工具退役不授权恢复或删除原件；见[范围核对](follow-up-completion-audit-2026-10-09.md)。

## 历史记录

不新建逐窗口台账。原账本、原件与固定 Git 版本保持可追溯：

- [本轮维护基线原状态全文](https://github.com/MaginaLW/harness-model/blob/5b82fc78987a63b686357c272f6dfdd4e0c6e96a/docs/operations/maintenance-status.md)：各 PR、离线合同及旧方向。
- 停止现场原状态仅在保留的原主根可读：`git show 4ab57ce5b0291ec2841c90782a751c920e284403:docs/operations/maintenance-status.md`。Stage A、A11–A50、失败/额度与 WIP 边界；正文中旧“先接入后瘦身”已由当前治理方向取代。
- [较早维护历史](../archive/operations/maintenance-status-history.md)与[归档索引](../archive/README.md)。main 原文也可用 `git show <固定提交>:docs/operations/maintenance-status.md` 读取。停止工作线提交尚未公开，远端不能检出；保留原本地分支和对象，不为导航公开其历史/私有原件。对象缺失时报精确缺口，不改写为成功。
