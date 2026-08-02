# AI 代码协同系统

一个面向人类、Codex、Claude Code 及其他模型的可执行协同治理系统。项目通过确定性分流、任务状态机、版本绑定证据和 CI 门禁，让低风险工作可自动推进、高风险工作可审阅且可追踪。

> 当前状态：架构、阶段一 MVP 设计及实施目录已完成；工程代码尚未开始实现。

## 阶段一目标

- 支持 `AUTO`、`ASK`、`REVIEW`、`BLOCK` 与动态升级。
- 分别计算决策权分流和 `V0`/`V1` 验证强度。
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
| [Agent 规则](AGENTS.md) | 所有 Agent 的简短常驻约束 |
| [Claude Code 规则](CLAUDE.md) | Claude Code 的同源入口 |

## 实施路线

1. 工程基线与可执行契约
2. 任务记录与状态核心
3. 分流与验证等级引擎
4. 治理交互流程
5. 验证与证据闭环
6. Agent、Hooks 与 CI 集成
7. 试点验收与阶段一基线

各章节必须按[实施目录](docs/superpowers/plans/2026-08-01-ai-code-collaboration-mvp-implementation-directory.md)的前置关系推进，并以其中的命令和通过条件作为完成判据。

## 开始参与

1. 先阅读 [AGENTS.md](AGENTS.md)；使用 Claude Code 时同时阅读 [CLAUDE.md](CLAUDE.md)。
2. 以阶段一 MVP 设计为需求基线，从实施目录的 Task 1.1 开始。
3. 在 CLI 与 Policy 落地前，不把计划中的命令或能力视为已经可用。
4. 保留任务范围、决定、批准和验证证据；出现变化时升级，不自行降级或跳过 Gate。
