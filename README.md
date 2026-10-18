# AI 代码协同系统

一个面向人类、Codex、Claude Code 及其他模型的可执行协同治理系统。项目通过确定性分流、任务状态机、版本绑定证据和 CI 门禁，让低风险工作可自动推进、高风险工作可审阅且可追踪。

> 当前治理模式：仓库维护模式，task-free 例外已启用。是否需要 task、哪些要求不放松，均以 [AGENTS.md](AGENTS.md) 为唯一权威。

项目同时追求可靠交付和减少人工介入。章节完成、测试通过证明的是已实现能力及其检查结果，尚不能证明真实任务中的人工时间或缺陷率下降。日常使用从[低干预工作方式](docs/operations/low-intervention.md)开始。

准备应用到 ZCode、Codex 或其他项目时，从[接入指南](docs/operations/adoption.md)开始：先合并轻量规则、沿用目标质量检查，再决定是否需要完整引擎。当前不提供外仓一键安装，不要直接复制本仓 `.ai` 账本、身份、维护标记或模型配置。

## 当前状态

阶段一 MVP（`0.1.0`）与阶段二 Chapters 8–13 均已完成，当前源码包版本为 `0.2.0`，active Policy 为 `2.5.0`（V1/V2 只运行一次完整覆盖率 pytest；`impact_scope` 触及治理面的决策单元至少走 REVIEW）。阶段三保持 `not_started` 且进入门未满足；系统不提供 V3、真实模型路由、资源调度、通用命令拦截或操作系统安全沙箱。当前状态、未完成项与待决定事项只在[维护收尾与待办](docs/operations/maintenance-status.md)维护。`docs/superpowers/state/*.yaml` 是阶段二于 2026-08-30 完成时冻结的历史投影，不是当前事实来源。

## 按需求选工具

以下工具提供离线参考、事实回读或准备建议，具体命令与输入格式见各自用法。

| 需求 | 工具与用法 | 输入 | 结果边界 |
|---|---|---|---|
| 比较公开榜单中的候选配置 | [初始外部参考](docs/operations/benchmark-reference.md) | 显式整理的榜单 JSON 文件 | 声明集合内的相对参考分，不是本仓成功或检错概率。 |
| 查看正式账本中的审核与 Finding 历史 | [审核结果回读](docs/operations/review-feedback.md) | 完整克隆的固定 tracked `HEAD`；可按 task 过滤输出 | 保留原结果、来源与未知，不重算 Gate 或更新模型分数。 |
| 查看 task-free PR 的审核、处理与复核声明 | [公开 PR 回读](docs/operations/pr-feedback.md) | 经标准输入提供的公开 connector 来源包 | 汇总所供声明及待核对问题，不认证缺陷真值、独立复核或实际模型身份。 |
| 检查假设计数下的检出区间 | [离线区间计算](docs/operations/review-detection.md) | 标准输入中的 synthetic 整数计数 | 仅提供条件数学结果；真实来源与窗口准备见[观察流程](docs/operations/review-detection-preparation.md)。 |
| 核对观察声明的时间、引用和选择缺口 | [观察输入检查](docs/operations/review-detection-input.md) | 标准输入中的候选／机会声明与原件引用 | 保留未知和冲突；不认证来源、启动窗口或产生真实估计。 |
| 演练记录到条件计数与区间的处理 | [记录级合成分析](docs/operations/review-detection-analysis.md) | synthetic envelope、原声明结构及情景假设 | 关键未知整批阻断；只给合成条件结果，真实数据与评分未启用。 |
| 演练评分更新、校准与反馈路由 | [合成反馈演练](docs/operations/review-feedback-simulation.md) | 虚构快照、拟合／留出记录及显式情景阈值 | 重算完整快照、诊断留出预测并给模拟建议；不启用真实评分或自动审核。 |
| 核对文档引用是否对应本地 Git 原件 | [固定文档原件核对](docs/operations/review-detection-input.md#本地-git-原件核对) | 同一声明包及显式本地 Git 根目录 | 只核 commit/path/blob 和字节；语义定位、公开性与观察准入仍未知。 |
| 定位固定文档中的精确字节跨度 | [行跨度定位](docs/operations/review-detection-input.md#精确行跨度定位) | 上述入口显式 `--resolve-locators`；行跨度与预期 SHA-256 | 位置命中与 Git 对象匹配分开；语义适用、真实时序和准入另核。 |
| 定位当前任务的准备缺项 | [只读任务建议](docs/operations/review-advisory.md) | 完整克隆及真实 TASK-ID | 复用原生 status 与适用状态的 Gate，只给建议，不授予执行权限。 |

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
| [阶段一 MVP 设计](docs/superpowers/specs/2026-08-01-ai-code-collaboration-mvp-design.md) | 已确认的技术与治理基础设计 |
| [历史设计与验收](docs/archive/README.md) | 架构文档、阶段一/二设计、实施目录、验收报告、章节追踪、历史状态投影与未授权蓝图的索引 |

## 实施路线

Chapters 1–7（工程基线、任务状态、分流与验证、治理交互、证据闭环、Agent/Hooks/CI、试点验收）按[阶段一实施目录](docs/superpowers/plans/2026-08-01-ai-code-collaboration-mvp-implementation-directory.md)完成；Chapters 8–13（结构化审核、V2 contracts、独立 Verifier、acceptance/mutation、运行期观测与 Hooks、自举 REVIEW 试点）按[阶段二实施目录](docs/superpowers/plans/2026-08-22-phase-02-review-verification-implementation-directory.md)完成。计划中的未来能力不能当作已经可用。

剩余建设以数据与效果基线、任务分层置信度、反馈驱动审核和最小宿主接入为主线，按 **S0/S1 准备 → S2 离线验证 → S3 真实影子评估 → S4 单场景试点 → S5 按效果扩展** 推进。项目所有者已选择 **B：3-A 低风险建议与校准、3-B 高风险 V3 独立准入和验收**，首场景为本仓自然治理任务的只读建议，见[置信度反馈设计](docs/superpowers/specs/confidence-feedback.md)。有效能力清单和旧工作线边界见[维护收尾与待办](docs/operations/maintenance-status.md#剩余建设主线)，设计输入见[多层审核与置信度反馈分阶段计划](docs/superpowers/plans/2026-10-08-confidence-driven-approval-roadmap.md)。当前范围的准备与常规实施仍按 AGENTS.md 准入；数据、统计、隐私和风险用途参数尚未全部冻结。

阶段三仍为 `not_started`，实际实现准入尚未完成。[阶段三进入输入](docs/implementation/phase-03-entry-inputs.md)保留原三门，并明确两包关系：3-A 非评分准备可先做，生产估计与真实 shadow 先满足自身数据、方法和用途条件；3-B 独立验证真实 V3。整体 Phase 3 须两包各自退出；Phase 4 编排继续依赖整体退出、稳定接口与实测协调需求。完整引擎跨仓产品化、provider 和固定动作可信执行按真实需求分别准入。旧七项是历史未验收范围，TASK-0063～0071 已归档、不再默认续跑；未来能力与历史通过均不能当作当前可用能力。

现有 S0/S1 准备工具包括[固定 HEAD 事实快照](docs/operations/effect-observations.md#固定提交的事实快照)和[只读任务准备建议](docs/operations/review-advisory.md)。
建议复用当前原生 status 与适用状态的 Gate，固定 `probability_status=unestimated`、`execution_allowed=false`，不给执行权限。
这些能力不代表生产评分、真实 shadow、模型身份认证、独立样本充分或阶段退出。

## 开始参与

1. 先阅读 [AGENTS.md](AGENTS.md)；使用 Claude Code 时，再阅读其[平台适配入口](CLAUDE.md)。
2. 按 AGENTS.md 的升级清单判断是否需要 task；日常维护按[低干预工作方式](docs/operations/low-intervention.md)推进。
3. 使用 AI Flow 时，运行 `python -m aiflow --help`，以 CLI、active Policy 与当前 task ledger 的确定性结论为准。

## 运行期 observation 与 Hooks

`aiflow observe` 只接收显式 task、本地 JSON 输入和封闭 mode；所有有效 observation 都是 `execution_allowed=false` 的非授权结论（exit 2）。Hook 与 pre-command wrapper 只提供早期反馈和拒绝，不安装自身、不授权、不执行动作，也不是通用命令拦截器或沙箱。完整协议、E2E 证据范围与平台边界见 [Hooks](docs/operations/hooks.md)。

`aiflow external-review` 与 `aiflow verify --pytest-temp-root` 已移除；历史记录继续保留。退役范围与历史恢复来源见[外部审核导入](docs/operations/external-review-import.md)和[pytest 临时目录](docs/operations/pytest-temporary-roots.md)。

## 许可证

本项目采用 [MIT License](LICENSE)。
