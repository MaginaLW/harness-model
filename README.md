# AI 代码协同系统

一个面向人类、Codex、Claude Code 及其他模型的可执行协同治理系统。项目通过确定性分流、任务状态机、版本绑定证据和 CI 门禁，让低风险工作可自动推进、高风险工作可审阅且可追踪。

> 当前自举模式：项目所有者已决定先完成 harness-model，再将其完整应用于自身开发流程。[bootstrap 标记](.ai/bootstrap-mode.yaml) 有效期间，本仓库的本地开发与 PR 使用普通自动开发和常规质量检查，不要求创建 AI Flow task 或取得 spec/code approval；这不改变产品内 Policy 的 `AUTO`/`REVIEW` 语义，也不授权任何外部或破坏性动作。项目完成后仅由所有者显式移除标记；退出 PR 仍按目标分支的自举状态检查，合并后才恢复完整 AI Flow 自用审批。

> 当前状态：阶段一 MVP `0.1.0` 已完成本地发布基线验收；阶段二 Chapters 8–12 已完成，其中 Chapter 12.1–12.6 与两个退出检查均已通过。Chapter 13 尚未初始化，阶段二仍未完成。active Policy 为 `2.1.0`。Chapter 11 的 acceptance、integration、action-approved targeted mutation 与独立 verifier 已实现；TASK-0015 的 V2 结论与 TASK-0022 的 observe/Hook parity、审核、批准和合并结论均严格绑定各自 task、subject、规格与 Policy，不能自动复用于未来 task 或 subject。Chapter 12 已提供受限的运行期 observation 与 Hook/CLI/CI 入口，但不提供 V3、真实模型路由、资源调度、通用命令拦截或操作系统安全沙箱。

## 阶段一目标

- 支持 `AUTO`、`ASK`、`REVIEW`、`BLOCK` 与动态升级。
- 分别计算决策权分流和 `V0`/`V1`/`V2` 验证强度；阶段一基线中的 V2 只完成 contract 与分类，阶段二按 Chapters 8–13 逐步补齐执行能力。
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
| [Chapter 10 追踪](docs/implementation/chapter-10-independent-verifier-v2-evidence-gate.md) | 独立 Verifier、两阶段 V2 evidence/Gate 的退出证据与 live V2 限制 |
| [Chapter 11 追踪](docs/implementation/chapter-11-acceptance-integration-mutation.md) | 已完成的 acceptance/integration、targeted mutation、live V2 与退出证据边界 |
| [Chapter 12 状态](docs/superpowers/state/chapters/chapter-12.yaml) | 运行期升级观测与 Hooks 已完成；Chapter 13 尚未初始化，Phase 02 仍 in progress |

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
11. acceptance、integration 与 targeted mutation
12. 运行期升级观测与完整 Hooks
13. 自举 REVIEW 试点与阶段二基线

Chapters 1–7 按[阶段一实施目录](docs/superpowers/plans/2026-08-01-ai-code-collaboration-mvp-implementation-directory.md)推进；Chapters 8–13 按[阶段二实施目录](docs/superpowers/plans/2026-08-22-phase-02-review-verification-implementation-directory.md)推进。当前事实以 [overall state](docs/superpowers/state/overall.yaml) 和对应 chapter state 为准，计划中的未来能力不能当作已经可用。

## 资源感知调度路线

子智能体并发会同时增加模型、工具进程、内存、CPU 和 I/O 消耗。项目采用两层方案：可选的“编排顾问”负责提出 DAG 和并行建议，确定性调度控制面独占资源准入、全树配额、租约、背压和恢复权。LLM 不能自行提高并发、预算或绕过 AI Flow。

实施顺序为：阶段二先建立非侵入式资源与事件契约，阶段三用真实记录校准容量画像和影子策略，阶段四先交付单机过载防护，再接入自适应编排。当前每会话静态并发上限只是纵深防御，不能视为跨会话、跨进程的整机安全保证。两份预进入蓝图不是执行计划；只有阶段二、阶段三和阶段四进入证据齐备后，才能据此另建正式执行计划。

## 开始参与

bootstrap 标记有效时，先遵循本文顶部的自举例外；以下 AI Flow 自用步骤仅在标记移除或禁用后生效，或用于显式测试 AI Flow 产品行为。

1. 先阅读 [AGENTS.md](AGENTS.md)；使用 Claude Code 时同时阅读 [CLAUDE.md](CLAUDE.md)。
2. 先核对 [overall state](docs/superpowers/state/overall.yaml) 与当前 chapter state，再按对应阶段的设计和实施目录选择下一项工作。
3. 以已安装 CLI、active Policy 与当前 task ledger 的确定性结论为准；计划中的未来能力不能当作已经可用。
4. 保留任务范围、决定、批准和验证证据；出现变化时升级，不自行降级或跳过 Gate。

## 运行期 observation 与 Hooks 的当前边界

`aiflow observe` 仅接收一个显式 task、一个本地 UTF-8 JSON object 输入和封闭的
`apply`、`dry-run` 或 `ci` mode。它输出的是受当前 task/base/subject/Policy/classification
绑定约束的 observation decision；所有有效 observation 的
`execution_allowed=false`，因此以 exit 2 返回非授权结论，绝不以 exit 0 允许所描述的动作。
`apply` 才可能追加 task-local audit 或单调 escalation；`dry-run` 与 `ci` 对完整 task
目录零写。完整协议与恢复步骤见 [Hooks](docs/operations/hooks.md) 和
[故障恢复](docs/operations/recovery.md)。

当前 E2E 证据只覆盖两类 Hook 事实：pre-commit 的 `scope_out_of_bounds`，以及 pre-command
对六种 Policy 禁止规范高风险 action 的拒绝/审计；在该支持范围内，Hook、CLI 与 CI 比较的是
decision semantic fields，而非 source-sensitive digest、mode、ledger effect、event metadata、
JSON 字节或文案。现有验证运行在 Windows，保留 4 项既有 symlink capability skips；这不证明
Linux/macOS 的 live Hook 安装或全部宿主行为。未安装 Hook 的客户端、IDE 保存、GUI/remote Git
和绕过 wrapper 的调用都不能被声明为已拦截；pre-command 也不解释自由 shell 或执行命令。
