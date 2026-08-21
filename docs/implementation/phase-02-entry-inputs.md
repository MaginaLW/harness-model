# 阶段二进入输入

本文档只从阶段一测试和真实试点提取有证据的缺口，不是阶段二执行计划，也不授权开始实现。除下列输入外，进入阶段二还需要一个明确的跨模块 REVIEW 目标仓库和独立执行计划。

| ID | 分类 | 证据支持的缺口 | 证据来源 | 进入阶段二的必要性 |
|---|---|---|---|---|
| P2-REV-01 | 审核增强 | REVIEW 试点能生成自包含审核包和版本绑定批准，但设计/实现审核的问题分类、发现定位和结构化处置仍依赖人工流程。 | `docs/pilots/results/PILOT-REVIEW/result.md`、`tests/unit/test_review_package.py` | 跨模块 REVIEW 需要可重放的设计审核与实现审核分层，否则审核质量仍无法作为 V2 证据。 |
| P2-V2-01 | V2 | 阶段一 Policy 和 verification engine 只实施 V0/V1，无验收测试编排、定向故障注入或更高强度 evidence 合约。 | `docs/implementation/chapter-03-routing-verification.md`、`docs/implementation/phase-01-acceptance-matrix.md` ACC-02 | 阶段二的核心退出条件要求跨模块 REVIEW 产生可复现 V2 证据，不能以 V1 替代。 |
| P2-VER-01 | 独立 Verifier | 当前 verify 可由实施 agent 触发，虽有独立 CI 重验和 REVIEW code approval，但没有强制不同验证主体、最小上下文包或 verifier 身份隔离。 | `docs/pilots/results/PILOT-REVIEW/result.md`、`docs/implementation/chapter-05-verification-evidence.md` | V2 要证明的是独立可反驳结论；仅分离进程而不分离主体/上下文不足以建立该信任边界。 |
| P2-MUT-01 | 变异测试 | 阶段一有行/分支/差异覆盖率和黄金场景，但没有验证测试能否杀死定向行为变异。 | `docs/implementation/phase-01-acceptance-report.md` 覆盖率章节、`tests/integration/test_scenario_runner.py` | 高于 V1 的置信需要“测试会在行为被破坏时失败”的证据，单独覆盖率无法提供。 |
| P2-ESC-01 | 动态升级 | 结构化 `escalate/resolve` 已覆盖范围、Policy、验证和权限原因，但初始分类事实目前需在 task record 写入，运行期变化主要由 agent 显式报告。 | `docs/operations/quickstart.md`、`tests/integration/test_escalate_command.py` | 跨模块实施更容易出现未预期范围/依赖；阶段二需要更完整的观测事件和自动升级触发，但仍不允许自动降级。 |
| P2-HOOK-01 | 完整 Hooks | 阶段一 Hook/Skill/GitHub Action 是调用共享核心的薄层，提供分支保护配置清单，但没有编辑期范围监控、高风险命令拦截或外部仓库保护实施证据。 | `docs/implementation/chapter-06-agent-ci.md`、`tests/integration/test_tool_wrappers.py` | 阶段二的审核强化需在执行时更早发现越界，而不是只在 final scope/Gate 阶段拒绝。 |

## 进入前必须确认

1. 选定一个有明确测试类型和业务风险的跨模块 REVIEW 目标仓库。
2. 为 V2、独立 Verifier、变异测试和 Hooks 建立独立规格、Policy 变更评估和实施计划。
3. 保持阶段一硬规则：新能力不得降低 route/V、绕过状态/批准/Gate，也不得把信任度用于覆盖硬风险。
