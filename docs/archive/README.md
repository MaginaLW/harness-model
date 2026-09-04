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
