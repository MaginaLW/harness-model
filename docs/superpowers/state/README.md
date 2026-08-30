# 实施状态追踪

本目录是实施目录的人工状态投影，用于辅助追踪章节、任务、步骤、退出检查和验证证据。实施目录仍是工作范围与完成判据的来源；状态文件不替代计划或 AI Flow 运行时任务记录。

## 文件关系

- `overall.yaml`：跨阶段总体状态、章节依赖、累计计数、全局决定和未来阶段入口条件。
- `chapters/chapter-01.yaml` 至当前阶段章节文件：每章的任务、步骤计数、证据、阻断项和退出检查。
- `docs/superpowers/plans/2026-08-01-ai-code-collaboration-mvp-implementation-directory.md`：阶段一原始实施计划。
- `docs/superpowers/plans/2026-08-22-phase-02-review-verification-implementation-directory.md`：阶段二审核与强化验证实施目录。

## 状态约定

- `not_started`：总体尚未开始。
- `pending`：已登记但尚未开始。
- `in_progress`：已开始，仍有未完成工作。
- `completed`：对应工作和验证判据全部满足。
- `blocked`：有可定位的阻断条件，必须记录解除条件；不得改写为较低风险状态。
- `needs_revalidation`：来源计划、规格或 Policy 摘要变化，原结论需要重新验证。

任务只有在步骤、定向验证、本章累计回归、`git diff --check`/工作树检查、需求复核和质量复核均有证据后才能标记为 `completed`。章节只有在所有任务完成并通过章节退出检查后才能标记为 `completed`。

## 更新规则

1. 先读取并核对 `overall.yaml` 中的来源摘要，再更新对应章节文件。
2. 局部状态变化先写入章节文件的 `history`、任务状态和证据引用，再汇总更新 `overall.yaml` 的计数与当前指针。
3. 每次变化记录 UTC 时间、操作者、依据、验证命令或文件路径；没有证据时保持 `pending` 或 `in_progress`。
4. 计划、MVP 设计或将来可执行 Policy 的摘要变化时，将受影响状态改为 `needs_revalidation`，不得自行降级或沿用旧批准/证据。
5. 状态文件的 `history` 只追加，不删除既有决定、阻断或失败记录。

## 当前治理边界

当前仓库已有 `src/`、`.ai/tasks/`、可执行 Policy 与 `aiflow` CLI。AI Flow CLI 的确定性状态、验证、范围和 Gate 结论是运行时权威；人工状态文件只保留对实施目录和已核对运行时事实的辅助投影，不能覆盖、替代或伪造任务账本、批准或证据。

项目所有者已明确结束自举，`.ai/bootstrap-mode.yaml` 有意不存在。后续代码、配置、CI 或
行为变更必须创建或恢复 AI Flow task，并通过适用的审批、验证与 Gate。历史 state/evidence
中的 `bootstrap_active` 只记录形成时事实，不是恢复 task-free 例外的开关。无论处于哪个历史
阶段，本目录更新都不构成运行时批准，也不能覆盖 CLI、task ledger 或 Gate 的确定性结论。

删除、推送、合并、部署、凭据、付费调用和其他高风险外部动作仍须单独批准；本状态初始化不授予任何此类权限。
