# AI 代码协同系统

一个面向人类、Codex 及其他编码助手的可执行协同治理系统。系统通过确定性分流（`AUTO` / `ASK` / `REVIEW` / `BLOCK`）、任务状态机、`V0` / `V1` / `V2` 分级验证、版本绑定证据与 CI 门禁，让低风险工作自动推进、高风险工作严格审阅并全程可追踪。

> 当前治理模式：仓库维护模式（`.ai/bootstrap-mode.yaml` 已激活），task-free 例外已启用。是否需要 task、升级清单及不放松要求均以 [AGENTS.md](AGENTS.md) 为唯一权威。

## 开始参与

1. 阅读 [AGENTS.md](AGENTS.md)（升级清单与常设授权）；Codex 可按任务需要使用 [AI Flow Skill](.agents/skills/ai-flow/SKILL.md)。
2. 非治理面日常维护按[低干预工作方式](docs/operations/low-intervention.md)推进；触及治理/核心代码时，运行 `python -m aiflow --help` 并按 CLI、active Policy 与当前 task ledger 的确定性结论推进。
3. 准备接入 ZCode、Codex 或其他项目时，从[接入指南](docs/operations/adoption.md)与 [Quickstart](docs/operations/quickstart.md) 开始：先合并轻量规则并沿用目标质量检查，再评估是否需要跨仓引擎；不要复制本仓 `.ai` 账本、身份或模型配置。

## 当前状态

- **已交付能力**：阶段一 MVP（`0.1.0`）与阶段二 Chapters 8–13 已完成，当前源码包版本 `0.2.0`，active Policy `2.6.0`；支持确定性分流、版本绑定证据、结构化审核、V2、独立 Verifier 与 required CI 门禁（`ai-quality-gate` + `main` 分支保护）。
- **明确边界**：Phase 3 仍为 `not_started` 且进入门未满足，Phase 4 依赖其整体退出；系统当前不提供 V3、真实自动评分/模型路由、通用命令拦截器或 OS 沙箱，`aiflow observe` 与 pre-command wrapper 只提供反馈和拒绝，不授予执行权（见 [Hooks](docs/operations/hooks.md)）。
- **暂停与退役项**：跨仓 `agent-bridge` Stage B 接入在探针失败后已停止，旧 mutation 加固与宿主接入继续暂停；`aiflow external-review` 与 `aiflow verify --pytest-temp-root` 已移除（见[外部审核导入](docs/operations/external-review-import.md)和[pytest 临时目录](docs/operations/pytest-temporary-roots.md)）。实时状态与待决定事项只在[维护收尾与待办](docs/operations/maintenance-status.md)维护，[overall state](docs/superpowers/state/overall.yaml) 仅作 2026-08-30 阶段二冻结投影，不再作为当前事实来源。

## 文档地图

| 文档 | 用途 |
|---|---|
| [Agent 规则](AGENTS.md) | 所有 Agent 的唯一共同权威与维护模式升级清单 |
| [AI Flow Skill](.agents/skills/ai-flow/SKILL.md) | Codex 可发现的通用 AI Flow 工作流 |
| [Quickstart](docs/operations/quickstart.md) | 从干净克隆安装、测试并运行无外部动作示例 |
| [接入现有 AI 工作流](docs/operations/adoption.md) | 只读盘点、可合并规则和分批推广；区分轻量接入与完整引擎 |
| [SDK 客户端与跨仓初始化方案](docs/operations/sdk-and-engine-plan.md) | SDK 使用、跨仓初始化边界与后续验收 |
| [低干预工作方式](docs/operations/low-intervention.md) | Agent 连续推进与必要人工决定的边界 |
| [Hooks](docs/operations/hooks.md) | 本地 wrapper、`aiflow observe` 协议与平台证据边界 |
| [故障恢复](docs/operations/recovery.md) | 半创建、损坏状态、FAILED/BLOCK、stale evidence 与精确清理边界 |
| [模型选择与代理职责](docs/operations/model-selection.md) | UI 与运行时决定型号，职责不绑定模型代际 |
| [按需反馈与回灌](docs/operations/feedback-loop.md) | 已登记试点仅在有实质问题或明确请求时执行 |
| [维护收尾与待办](docs/operations/maintenance-status.md) | 当前状态、未完成项与待决定事项 |
| [阶段一 MVP 设计](docs/superpowers/specs/2026-08-01-ai-code-collaboration-mvp-design.md) / [实施目录](docs/superpowers/plans/2026-08-01-ai-code-collaboration-mvp-implementation-directory.md) | 阶段一架构设计及 Chapters 1–7 实施记录 |
| [阶段二设计](docs/superpowers/specs/2026-08-22-phase-02-review-verification-design.md) / [实施目录](docs/superpowers/plans/2026-08-22-phase-02-review-verification-implementation-directory.md) | 阶段二审核与 V2 验证设计及 Chapters 8–13 实施记录 |
| [历史设计与验收](docs/archive/README.md) | 架构文档、验收报告、章节追踪、已归档运营日志与未授权蓝图索引 |

## 离线参考与回读工具（按需选用）

> 注意：下表工具仅用于离线只读回读或 Phase 3 预研 synthetic 演练，**不构成生产评分、独立真值或执行授权**；章节完成与测试通过也不自动等同于真实人时下降（口径见[效果观察口径](docs/operations/effect-observations.md)）。

| 需求 | 工具与用法 | 输入与结论边界 |
|---|---|---|
| 定位当前任务的准备缺项 | [只读任务建议](docs/operations/review-advisory.md) | 完整克隆及真实 `TASK-ID`；只给建议、不授执行权 |
| 查看正式账本 / 公开 PR 审核历史 | [审核结果回读](docs/operations/review-feedback.md) / [公开 PR 回读](docs/operations/pr-feedback.md) | 固定 `HEAD` 或公开 JSON；保留未知、不重算 Gate |
| 校验文档引用与本地 Git 行跨度 | [观察输入检查](docs/operations/review-detection-input.md)（含 [Git 原件核对](docs/operations/review-detection-input.md#本地-git-原件核对) 与 [行跨度定位](docs/operations/review-detection-input.md#精确行跨度定位)） | 标准输入声明包与本地 Git 根目录；不认证语义与准入 |
| 演练合成检出区间与校准反馈 | [离线区间计算](docs/operations/review-detection.md) / [记录级合成分析](docs/operations/review-detection-analysis.md) / [合成反馈演练](docs/operations/review-feedback-simulation.md) / [初始外部参考](docs/operations/benchmark-reference.md) | synthetic 计数或虚构快照；窗口准备见[观察流程](docs/operations/review-detection-preparation.md) |
| 显式执行单次 SDK 只读文档审核 | [单次只读审核](docs/superpowers/specs/sdk-readonly-review.md#使用) | 默认关闭；需可选 SDK 与明确任务输入范围 |

## 许可证

本项目采用 [MIT License](LICENSE)。
