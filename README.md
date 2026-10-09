# AI 代码协同系统

一个面向人类、Codex、Claude Code 及其他模型的可执行协同治理系统。项目通过确定性分流、任务状态机、版本绑定证据和 CI 门禁，让低风险工作可自动推进、高风险工作可审阅且可追踪。

> 当前治理模式：仓库维护模式，task-free 例外已启用。是否需要 task、哪些要求不放松，均以 [AGENTS.md](AGENTS.md) 为唯一权威。

项目同时追求可靠交付和减少人工介入。章节完成、测试通过证明的是已实现能力及其检查结果，尚不能证明真实任务中的人工时间或缺陷率下降。日常使用从[低干预工作方式](docs/operations/low-intervention.md)开始。

准备应用到 ZCode、Codex 或其他项目时，从[接入指南](docs/operations/adoption.md)开始：先合并轻量规则、沿用目标质量检查，再决定是否需要完整引擎。当前不提供外仓一键安装，不要直接复制本仓 `.ai` 账本、身份、维护标记或模型配置。

## 当前状态

阶段一 MVP（`0.1.0`）与阶段二 Chapters 8–13 均已完成，当前源码包版本为 `0.2.0`，active Policy 为 `2.4.0`（V1/V2 只运行一次完整覆盖率 pytest）。阶段三保持 `not_started` 且进入门未满足；系统不提供 V3、真实模型路由、资源调度、通用命令拦截或操作系统安全沙箱。当前状态、未完成项与待决定事项只在[维护收尾与待办](docs/operations/maintenance-status.md)维护。`docs/superpowers/state/*.yaml` 是阶段二于 2026-08-30 完成时冻结的历史投影，不是当前事实来源。

## 阶段一目标

- 支持 `AUTO`、`ASK`、`REVIEW`、`BLOCK` 与动态升级。
- 分别计算决策权分流和 `V0`/`V1`/`V2` 验证强度；阶段一基线中的 V2 只完成 contract 与分类，阶段二按 Chapters 8–13 逐步补齐执行能力。
- 用 Python CLI 统一任务状态、批准、验证和 Gate。
- 将规格、Policy、批准和 evidence 绑定到明确版本。
- 通过本地验证、required `ai-quality-gate` 和已配置的 `main` 分支保护提供门禁；真实 PR 已验证严格状态检查生效，workflow 本身仍不替代平台保护或单独的外部动作授权。

## 文档地图

| 文档 | 用途 |
|---|---|
| [Agent 规则](AGENTS.md) | 所有 Agent 的唯一共同权威与维护模式升级清单 |
| [Claude Code 规则](CLAUDE.md) | Claude Code 平台适配入口 |
| [Quickstart](docs/operations/quickstart.md) | 从干净克隆安装、测试并运行无外部动作示例 |
| [接入现有 AI 工作流](docs/operations/adoption.md) | 只读盘点、可合并规则和分批推广；区分轻量接入与完整引擎 |
| [低干预工作方式](docs/operations/low-intervention.md) | Agent 连续推进与必要人工决定的边界 |
| [Hooks](docs/operations/hooks.md) | 本地 wrapper、`aiflow observe` 协议与平台证据边界 |
| [故障恢复](docs/operations/recovery.md) | 半创建、损坏状态、FAILED/BLOCK、stale evidence 与精确清理边界 |
| [模型选择与代理职责](docs/operations/model-selection.md) | UI 与运行时决定型号，职责不绑定模型代际 |
| [按需反馈与回灌](docs/operations/feedback-loop.md) | 已登记试点仅在有实质问题或明确请求时执行 |
| [维护收尾与待办](docs/operations/maintenance-status.md) | 当前状态、未完成项与待决定事项 |
| [自托管执行基础设施](docs/operations/self-hosted-runners.md) | 私有 runner 接入、健康检查与回执契约 |
| [阶段一 MVP 设计](docs/superpowers/specs/2026-08-01-ai-code-collaboration-mvp-design.md) | 已确认的技术与治理基础设计 |
| [历史设计与验收](docs/archive/README.md) | 架构文档、阶段一/二设计、实施目录、验收报告、章节追踪、历史状态投影与未授权蓝图的索引 |

## 实施路线

Chapters 1–7（工程基线、任务状态、分流与验证、治理交互、证据闭环、Agent/Hooks/CI、试点验收）按[阶段一实施目录](docs/superpowers/plans/2026-08-01-ai-code-collaboration-mvp-implementation-directory.md)完成；Chapters 8–13（结构化审核、V2 contracts、独立 Verifier、acceptance/mutation、运行期观测与 Hooks、自举 REVIEW 试点）按[阶段二实施目录](docs/superpowers/plans/2026-08-22-phase-02-review-verification-implementation-directory.md)完成。计划中的未来能力不能当作已经可用。

后续排序提案见[多层审核与置信度反馈分阶段计划](docs/superpowers/plans/2026-10-08-confidence-driven-approval-roadmap.md)；它是后续排序提案，不改变现行准入与权限边界。资源感知调度与阶段三/四蓝图只有在[阶段三进入门](docs/implementation/phase-03-entry-inputs.md)满足并另建正式设计后才可推进；当前每会话静态并发上限只是纵深防御，不是整机安全保证，蓝图都不是执行授权。

## 开始参与

1. 先阅读 [AGENTS.md](AGENTS.md)；使用 Claude Code 时，再阅读其[平台适配入口](CLAUDE.md)。
2. 按 AGENTS.md 的升级清单判断是否需要 task；日常维护按[低干预工作方式](docs/operations/low-intervention.md)推进。
3. 使用 AI Flow 时，运行 `python -m aiflow --help`，以 CLI、active Policy 与当前 task ledger 的确定性结论为准。

## 运行期 observation 与 Hooks

`aiflow observe` 只接收显式 task、本地 JSON 输入和封闭 mode；所有有效 observation 都是 `execution_allowed=false` 的非授权结论（exit 2）。Hook 与 pre-command wrapper 只提供早期反馈和拒绝，不安装自身、不授权、不执行动作，也不是通用命令拦截器或沙箱。完整协议、E2E 证据范围与平台边界见 [Hooks](docs/operations/hooks.md)。

## 许可证

本项目采用 [MIT License](LICENSE)。
