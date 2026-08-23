# AI 代码协同系统

一个面向人类、Codex、Claude Code 及其他模型的可执行协同治理系统。项目通过确定性分流、任务状态机、版本绑定证据和 CI 门禁，让低风险工作可自动推进、高风险工作可审阅且可追踪。

> 当前状态：阶段一 MVP `0.1.0` 已完成本地发布基线验收；阶段二 Chapters 8–9 已完成。Chapter 10 的 V2 独立 Verifier、两阶段 evidence 与 Gate 实现正在收尾验证（implemented / verification pending）。V2 live run 目前只执行既有 V1 前缀；Chapter 11 的 acceptance、integration、targeted mutation 尚未执行，因此 live V2 evidence 必然失败。V3、真实模型路由及资源调度不在阶段二范围内。

## 阶段一目标

- 支持 `AUTO`、`ASK`、`REVIEW`、`BLOCK` 与动态升级。
- 分别计算决策权分流和 `V0`/`V1`/`V2` 验证强度；V2 当前只完成 contract 与分类，不执行检查。
- 用 Python CLI 统一任务状态、批准、验证和 Gate。
- 将规格、Policy、批准和 evidence 绑定到明确版本。
- 通过本地验证与 GitHub Actions 阻止越权或证据不足的变更。

## 文档地图

| 文档 | 用途 |
|---|---|
| [分流与模型路由设计 V0.1](docs/architecture/AI代码协同分流与模型路由设计_V0.1.md) | 概念模型、分流原则和长期模型路由方向 |
| [实施总体规划 V0.2](docs/architecture/AI代码协同系统实施总体规划_V0.2.md) | 总体架构、阶段路线和验收原则 |
| [阶段一 MVP 设计](docs/superpowers/specs/2026-08-01-ai-code-collaboration-mvp-design.md) | 已确认的阶段一技术与治理设计 |
| [阶段一实施目录](docs/superpowers/plans/2026-08-01-ai-code-collaboration-mvp-implementation-directory.md) | 7 章、44 个任务及逐步验证清单 |
| [阶段二设计](docs/superpowers/specs/2026-08-22-phase-02-review-verification-design.md) | 双阶段审核、V2、独立验证、变异与 Hooks 的边界和兼容性设计 |
| [阶段二实施目录](docs/superpowers/plans/2026-08-22-phase-02-review-verification-implementation-directory.md) | Chapter 8–13 的进入条件、任务顺序、验证与退出条件 |
| [资源感知多智能体调度设计](docs/superpowers/specs/2026-08-13-resource-aware-agent-scheduling-design.md) | “编排顾问 + 确定性控制面”、整机资源租约、背压与恢复设计 |
| [本机过载防护预进入蓝图](docs/superpowers/specs/2026-08-13-local-agent-overload-protection-blueprint.md) | 阶段四进入门满足后编写单机控制面执行计划的设计输入，当前未授权实施 |
| [自适应多智能体编排预进入蓝图](docs/superpowers/specs/2026-08-13-adaptive-agent-orchestration-blueprint.md) | 安全控制面通过后编写编排顾问与真实 adapter 执行计划的设计输入，当前未授权实施 |
| [Agent 规则](AGENTS.md) | 所有 Agent 的简短常驻约束 |
| [Claude Code 规则](CLAUDE.md) | Claude Code 的同源入口 |
| [Quickstart](docs/operations/quickstart.md) | 从干净克隆安装、测试并运行无外部动作示例 |
| [故障恢复](docs/operations/recovery.md) | 半创建、损坏状态、FAILED/BLOCK、stale evidence 等恢复流程 |
| [阶段一验收报告](docs/implementation/phase-01-acceptance-report.md) | 十二项验收、四试点、覆盖率、限制和风险接受 |
| [Chapter 8 追踪](docs/implementation/chapter-08-structured-review.md) | 结构化设计/实现审核的任务状态和兼容性护栏 |
| [Chapter 9 追踪](docs/implementation/chapter-09-v2-policy-contracts.md) | V2 Policy、版本化 contracts、分类规则与兼容性边界 |
| [Chapter 10 追踪](docs/implementation/chapter-10-independent-verifier-v2-evidence-gate.md) | 独立 Verifier、两阶段 V2 evidence/Gate 的实现状态与未完成验证 |

## 实施路线

1. 工程基线与可执行契约
2. 任务记录与状态核心
3. 分流与验证等级引擎
4. 治理交互流程
5. 验证与证据闭环
6. Agent、Hooks 与 CI 集成
7. 试点验收与阶段一基线
8. 结构化设计审核与实现审核
9. V2 Policy、contracts 与分类
10. 独立 Verifier、两阶段 V2 evidence 与 Gate

各章节必须按[实施目录](docs/superpowers/plans/2026-08-01-ai-code-collaboration-mvp-implementation-directory.md)的前置关系推进，并以其中的命令和通过条件作为完成判据。

## 资源感知调度路线

子智能体并发会同时增加模型、工具进程、内存、CPU 和 I/O 消耗。项目采用两层方案：可选的“编排顾问”负责提出 DAG 和并行建议，确定性调度控制面独占资源准入、全树配额、租约、背压和恢复权。LLM 不能自行提高并发、预算或绕过 AI Flow。

实施顺序为：阶段二先建立非侵入式资源与事件契约，阶段三用真实记录校准容量画像和影子策略，阶段四先交付单机过载防护，再接入自适应编排。当前每会话静态并发上限只是纵深防御，不能视为跨会话、跨进程的整机安全保证。两份预进入蓝图不是执行计划；只有阶段二、阶段三和阶段四进入证据齐备后，才能据此另建正式执行计划。

## 开始参与

1. 先阅读 [AGENTS.md](AGENTS.md)；使用 Claude Code 时同时阅读 [CLAUDE.md](CLAUDE.md)。
2. 以阶段一 MVP 设计为需求基线，从实施目录的 Task 1.1 开始。
3. 在 CLI 与 Policy 落地前，不把计划中的命令或能力视为已经可用。
4. 保留任务范围、决定、批准和验证证据；出现变化时升级，不自行降级或跳过 Gate。
