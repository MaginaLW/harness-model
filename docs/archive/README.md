# 文档归档

本目录保存已被后续文档取代、但仍需可追溯的历史执行文档。归档只改变存放位置，不改变
任何文件内容，也不改变它们作为历史事实的效力。

## 归档原则

1. **只归档已完成且被取代的逐任务执行文档。** 章节 1–7 的每个 task 曾有一份独立执行
   文档；13/13 chapters 已完成后，这些文档不再是任何在途工作的入口。
2. **不归档被不可变证据引用的文档。** `docs/implementation/chapter-*.md` 被
   `.ai/tasks/**` 中已冻结、按 sha256 绑定的 spec 与 task.yaml 引用（例如
   `TASK-0025/historical-snapshots/`），移动会破坏不可变证据内部的链接，因此原地保留。
3. **不归档 `.ai/tasks/**`。** 任务账本按 `AGENTS.md` 为追加式记录，且 CLI 按
   `.ai/tasks/{task_id}/` 解析路径，移动会同时破坏 CLI 与按字节哈希绑定的证据检出。
4. **不归档仍未执行或仍在生效的计划。** 两份实施目录、Codex 模型路由配置决定和
   external worker routing 计划均留在 `docs/superpowers/plans/`。
5. **不归档验收报告、证据索引与进入输入。** 它们是当前结论的权威来源。

## 与历史状态记录的关系

`docs/superpowers/state/overall.yaml` 与 `docs/superpowers/state/chapters/*.yaml` 中仍
按**归档前的原路径**引用这些文档。这是有意保留的：

- 那些引用出现在绑定了 `base_commit` / `subject_commit` 的 `evidence:` 列表中；
- 部分引用是带 `raw_sha256` 的历史 `git status --porcelain` 快照记录。

改写它们会把「当时记录的路径」篡改成「今天的路径」，违反 `AGENTS.md` 中既有任务记录与
日志不得重写的要求。因此状态文件保持原样，请用下表把原路径解析到当前位置。

## 归档件中保留的本机路径

`2026-08-02-chapter-01-task-1-1-tdd-replay-remediation.md` 含当时运行环境的本机用户名
绝对路径。它没有被改成占位符，因为该文件的内容被
`docs/superpowers/state/chapters/chapter-01.yaml` 中的 `plan_sha256`（`5dd172aa…`）绑定，
任何改动都会使记录在案的哈希失配。同一份状态文件里的 `environment_result` 记录出于同样
理由保持原样。这是仓库卫生要求的一处**已登记例外**，仅限历史归档件与历史证据；活跃文档
一律使用占位符。

## 历史设计与验收索引

以下文档保持原位置（多数被 `.ai/tasks/**` 或测试按路径引用），只在此集中索引。它们记录已完成阶段的设计、计划、验收与证据，不是当前待办：

- 架构：[分流与模型路由设计 V0.1](../architecture/AI代码协同分流与模型路由设计_V0.1.md) · [实施总体规划 V0.2](../architecture/AI代码协同系统实施总体规划_V0.2.md)
- 阶段一：[MVP 设计](../superpowers/specs/2026-08-01-ai-code-collaboration-mvp-design.md) · [实施目录](../superpowers/plans/2026-08-01-ai-code-collaboration-mvp-implementation-directory.md) · [验收矩阵](../implementation/phase-01-acceptance-matrix.md) · [验收报告](../implementation/phase-01-acceptance-report.md)
- 阶段二：[进入输入](../implementation/phase-02-entry-inputs.md) · [设计](../superpowers/specs/2026-08-22-phase-02-review-verification-design.md) · [实施目录](../superpowers/plans/2026-08-22-phase-02-review-verification-implementation-directory.md) · [验收矩阵](../implementation/phase-02-acceptance-matrix.md) · [证据索引](../implementation/phase-02-evidence-index.md) · [验收报告](../implementation/phase-02-acceptance-report.md)
- 章节追踪：`docs/implementation/chapter-*.md`（Chapters 1–6、8–13）
- 历史状态投影：[overall state](../superpowers/state/overall.yaml) 与 `docs/superpowers/state/chapters/*.yaml`，阶段二于 2026-08-30 完成时冻结，不再作为当前事实来源
- 历史计划与诊断：[审批开销治理与未完成任务收敛](../superpowers/plans/2026-09-03-approval-overhead-and-open-task-consolidation-directory.md) · [ZCode 试点收尾执行目录](../superpowers/plans/2026-09-12-zcode-review-fix-execution.md) · [2026-09-12 计划收尾](../superpowers/plans/2026-09-12-plan-closeout-and-next-steps.md)

## 历史/未授权，不是当前待办

以下文档保持原位置，**不是当前待办，也不构成实施授权**：

- 阶段三/四预进入蓝图（未授权实施）：[资源感知多智能体调度设计](../superpowers/specs/2026-08-13-resource-aware-agent-scheduling-design.md) · [本机过载防护预进入蓝图](../superpowers/specs/2026-08-13-local-agent-overload-protection-blueprint.md) · [自适应多智能体编排预进入蓝图](../superpowers/specs/2026-08-13-adaptive-agent-orchestration-blueprint.md)
- [阶段三进入输入](../implementation/phase-03-entry-inputs.md)：只整理进入事实，进入门未满足
- [多层审核与置信度反馈分阶段计划](../superpowers/plans/2026-10-08-confidence-driven-approval-roadmap.md)：后续排序提案，不授权实施
- 按日期的运营记录（证据与追溯；当前状态只以[维护收尾与待办](../operations/maintenance-status.md)为准）：
  - [维护状态历史记录](operations/maintenance-status-history.md)（原 `maintenance-status.md` 的逐窗口日记）
  - [follow-up-preparation-2026-09-13.md](../operations/follow-up-preparation-2026-09-13.md)
  - [zcode-retrospective-2026-09-20.md](../operations/zcode-retrospective-2026-09-20.md)
  - [follow-up-backlog-2026-09-22.md](../operations/follow-up-backlog-2026-09-22.md)
  - [local-tools-closeout-2026-09-22.md](../operations/local-tools-closeout-2026-09-22.md)
  - [pilot-evidence-review-2026-09-22.md](../operations/pilot-evidence-review-2026-09-22.md)
  - [e4-gap-assessment-2026-09-23.md](../operations/e4-gap-assessment-2026-09-23.md)
  - [e4-preflight-closeout-2026-09-23.md](../operations/e4-preflight-closeout-2026-09-23.md)
  - [self-hosted-runner-inventory-2026-09-12.md](../operations/self-hosted-runner-inventory-2026-09-12.md)
  - [next-stage-start-conditions-2026-10-02.md](../operations/next-stage-start-conditions-2026-10-02.md)
  - [zcode-next-stage-assignments-2026-10-02.md](../operations/zcode-next-stage-assignments-2026-10-02.md)
  - [f-real-import-acceptance-2026-10-03.md](../operations/f-real-import-acceptance-2026-10-03.md)
  - [zcode-report-recovery-2026-10-03.md](../operations/zcode-report-recovery-2026-10-03.md)
  - [backlog-execution-2026-10-04.md](../operations/backlog-execution-2026-10-04.md)
  - [external-follow-up-evidence-2026-10-04.md](../operations/external-follow-up-evidence-2026-10-04.md)
  - [f-successor-decision-2026-10-04.md](../operations/f-successor-decision-2026-10-04.md)
  - [phase-entry-proposals-2026-10-04.md](../operations/phase-entry-proposals-2026-10-04.md)
  - [publication-package-2026-10-04.md](../operations/publication-package-2026-10-04.md)
  - [verification-budget-decision-2026-10-04.md](../operations/verification-budget-decision-2026-10-04.md)
  - [windows-private-timeout-repair-2026-10-04.md](../operations/windows-private-timeout-repair-2026-10-04.md)
  - [windows-production-design-2026-10-04.md](../operations/windows-production-design-2026-10-04.md)
  - [next-plan-execution-2026-10-08.md](../operations/next-plan-execution-2026-10-08.md)
  - [follow-up-completion-audit-2026-10-09.md](../operations/follow-up-completion-audit-2026-10-09.md)

## 路径映射

| 归档前路径（历史记录中引用的） | 当前位置 |
|---|---|
| `docs/superpowers/plans/2026-08-02-chapter-01-task-1-1-execution.md` | [2026-08-02-chapter-01-task-1-1-execution.md](plans/2026-08-02-chapter-01-task-1-1-execution.md) |
| `docs/superpowers/plans/2026-08-02-chapter-01-task-1-1-tdd-replay-remediation.md` | [2026-08-02-chapter-01-task-1-1-tdd-replay-remediation.md](plans/2026-08-02-chapter-01-task-1-1-tdd-replay-remediation.md) |
| `docs/superpowers/plans/2026-08-20-chapter-01-task-1-1-lean-revalidation.md` | [2026-08-20-chapter-01-task-1-1-lean-revalidation.md](plans/2026-08-20-chapter-01-task-1-1-lean-revalidation.md) |
| `docs/superpowers/plans/2026-08-20-chapter-01-task-1-2-execution.md` | [2026-08-20-chapter-01-task-1-2-execution.md](plans/2026-08-20-chapter-01-task-1-2-execution.md) |
| `docs/superpowers/plans/2026-08-20-chapter-01-task-1-3-execution.md` | [2026-08-20-chapter-01-task-1-3-execution.md](plans/2026-08-20-chapter-01-task-1-3-execution.md) |
| `docs/superpowers/plans/2026-08-20-chapter-01-task-1-4-execution.md` | [2026-08-20-chapter-01-task-1-4-execution.md](plans/2026-08-20-chapter-01-task-1-4-execution.md) |
| `docs/superpowers/plans/2026-08-20-chapter-01-task-1-5-execution.md` | [2026-08-20-chapter-01-task-1-5-execution.md](plans/2026-08-20-chapter-01-task-1-5-execution.md) |
| `docs/superpowers/plans/2026-08-20-chapter-02-task-2-1-execution.md` | [2026-08-20-chapter-02-task-2-1-execution.md](plans/2026-08-20-chapter-02-task-2-1-execution.md) |
| `docs/superpowers/plans/2026-08-20-chapter-02-task-2-2-execution.md` | [2026-08-20-chapter-02-task-2-2-execution.md](plans/2026-08-20-chapter-02-task-2-2-execution.md) |
| `docs/superpowers/plans/2026-08-20-chapter-02-task-2-3-execution.md` | [2026-08-20-chapter-02-task-2-3-execution.md](plans/2026-08-20-chapter-02-task-2-3-execution.md) |
| `docs/superpowers/plans/2026-08-20-chapter-02-task-2-4-execution.md` | [2026-08-20-chapter-02-task-2-4-execution.md](plans/2026-08-20-chapter-02-task-2-4-execution.md) |
| `docs/superpowers/plans/2026-08-20-chapter-02-task-2-5-execution.md` | [2026-08-20-chapter-02-task-2-5-execution.md](plans/2026-08-20-chapter-02-task-2-5-execution.md) |
| `docs/superpowers/plans/2026-08-20-chapter-02-task-2-6-execution.md` | [2026-08-20-chapter-02-task-2-6-execution.md](plans/2026-08-20-chapter-02-task-2-6-execution.md) |
| `docs/superpowers/plans/2026-08-20-chapter-03-task-3-1-execution.md` | [2026-08-20-chapter-03-task-3-1-execution.md](plans/2026-08-20-chapter-03-task-3-1-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-03-task-3-2-execution.md` | [2026-08-21-chapter-03-task-3-2-execution.md](plans/2026-08-21-chapter-03-task-3-2-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-03-task-3-3-execution.md` | [2026-08-21-chapter-03-task-3-3-execution.md](plans/2026-08-21-chapter-03-task-3-3-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-03-task-3-4-execution.md` | [2026-08-21-chapter-03-task-3-4-execution.md](plans/2026-08-21-chapter-03-task-3-4-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-03-task-3-5-execution.md` | [2026-08-21-chapter-03-task-3-5-execution.md](plans/2026-08-21-chapter-03-task-3-5-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-03-task-3-6-execution.md` | [2026-08-21-chapter-03-task-3-6-execution.md](plans/2026-08-21-chapter-03-task-3-6-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-04-task-4-1-execution.md` | [2026-08-21-chapter-04-task-4-1-execution.md](plans/2026-08-21-chapter-04-task-4-1-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-04-task-4-2-execution.md` | [2026-08-21-chapter-04-task-4-2-execution.md](plans/2026-08-21-chapter-04-task-4-2-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-04-task-4-3-execution.md` | [2026-08-21-chapter-04-task-4-3-execution.md](plans/2026-08-21-chapter-04-task-4-3-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-04-task-4-4-execution.md` | [2026-08-21-chapter-04-task-4-4-execution.md](plans/2026-08-21-chapter-04-task-4-4-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-04-task-4-5-execution.md` | [2026-08-21-chapter-04-task-4-5-execution.md](plans/2026-08-21-chapter-04-task-4-5-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-04-task-4-6-execution.md` | [2026-08-21-chapter-04-task-4-6-execution.md](plans/2026-08-21-chapter-04-task-4-6-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-05-task-5-1-execution.md` | [2026-08-21-chapter-05-task-5-1-execution.md](plans/2026-08-21-chapter-05-task-5-1-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-05-task-5-2-execution.md` | [2026-08-21-chapter-05-task-5-2-execution.md](plans/2026-08-21-chapter-05-task-5-2-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-05-task-5-3-execution.md` | [2026-08-21-chapter-05-task-5-3-execution.md](plans/2026-08-21-chapter-05-task-5-3-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-05-task-5-4-execution.md` | [2026-08-21-chapter-05-task-5-4-execution.md](plans/2026-08-21-chapter-05-task-5-4-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-05-task-5-5-execution.md` | [2026-08-21-chapter-05-task-5-5-execution.md](plans/2026-08-21-chapter-05-task-5-5-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-05-task-5-6-execution.md` | [2026-08-21-chapter-05-task-5-6-execution.md](plans/2026-08-21-chapter-05-task-5-6-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-05-task-5-7-execution.md` | [2026-08-21-chapter-05-task-5-7-execution.md](plans/2026-08-21-chapter-05-task-5-7-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-05-task-5-8-execution.md` | [2026-08-21-chapter-05-task-5-8-execution.md](plans/2026-08-21-chapter-05-task-5-8-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-06-task-6-1-execution.md` | [2026-08-21-chapter-06-task-6-1-execution.md](plans/2026-08-21-chapter-06-task-6-1-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-06-task-6-2-execution.md` | [2026-08-21-chapter-06-task-6-2-execution.md](plans/2026-08-21-chapter-06-task-6-2-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-06-task-6-3-execution.md` | [2026-08-21-chapter-06-task-6-3-execution.md](plans/2026-08-21-chapter-06-task-6-3-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-06-task-6-4-execution.md` | [2026-08-21-chapter-06-task-6-4-execution.md](plans/2026-08-21-chapter-06-task-6-4-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-06-task-6-5-execution.md` | [2026-08-21-chapter-06-task-6-5-execution.md](plans/2026-08-21-chapter-06-task-6-5-execution.md) |
| `docs/superpowers/plans/2026-08-21-chapter-07-task-7-1-execution.md` | [2026-08-21-chapter-07-task-7-1-execution.md](plans/2026-08-21-chapter-07-task-7-1-execution.md) |
