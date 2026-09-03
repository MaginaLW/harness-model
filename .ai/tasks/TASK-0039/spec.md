# Task Specification

## 目标

把 TASK-0031 失败轮的详细验证证据从一个游离的 git stash 正式落进任务账本，使其不再依赖本机 stash 存活；该任务的既有记录一字不改。

## 范围

- `.ai/tasks/TASK-0031/evidence-failed-20260901T001936Z.json`：新建，内容为 stash 中原件的**逐字节副本**，文件名取自其 `generated_at` 时刻 `2026-09-01T00:19:36Z`。
- `CHANGELOG.md`：在 Unreleased 记录该证据保全。

## 非目标

- 不修改 TASK-0031 的 `events.jsonl`、`evidence.json`、`approvals.json`、`task.yaml` 或其余任何既有文件。
- 不改写、不重排、不删除任何事件。
- 不改动 stash 本身；是否清理 stash 由项目所有者在本任务之外决定。
- 不改 `src/aiflow/**`、Policy、证据 schema、Gate 语义或 CI 配置。

## 背景

TASK-0031 在 2026-09-01T00:19:36Z 有一轮 V1 验证失败，`unit_tests`、`regression_tests` 与 `coverage_xml` 三项未通过。随后 01:03:10 的重跑通过，并**覆盖**了 `evidence.json`——因为该文件按运行重写，不是追加式的。

该任务的事件账本记录了失败这一事实，其重试事件的理由写着 `Retry after preserving the failed V1 evidence`，说明当时的意图是保留失败明细。但核查 `main` 上 TASK-0031 目录的全部 16 个文件后确认：只有 `events.jsonl` 记录了失败的*事实*，没有任何文件保留失败轮的*明细*。

那份明细仅存于一个 GitHub Desktop 创建的 stash 中，且该 stash 所依附的分支 `codex/formal-ci-canary-r2` 已在分支整理中删除（其提交已并入 main）。stash 不随仓库推送、不参与克隆，且易被误丢。

项目的 REC-04 要求保留失败证据以供审计，阶段三进入输入亦明确「失败不得被后续成功覆盖」。本任务把该明细转为受版本控制的账本文件，以符合上述约束。

## 验收条件

- 新文件的 SHA-256 与 stash 中 `.ai/tasks/TASK-0031/evidence.json` 原件逐位相同（`b35394881e976961…`）。
- 新文件内容自证其身份：`task_id` 为 `TASK-0031`、`conclusion` 为 `failed`、`generated_at` 为 `2026-09-01T00:19:36Z`、失败检查为 `unit_tests`、`regression_tests`、`coverage_xml`。
- TASK-0031 目录下所有既有文件的字节与本变更前完全一致。
- V1 完整回归、`ruff check`、`ruff format --check`、`mypy src` 通过，总覆盖率不低于 85%，diff coverage 不低于 90%。
- `aiflow scope TASK-0039` 通过。

## 禁止动作

push、merge、deploy、delete、secret_export、paid_external_call。本任务不执行外部动作、不访问网络、不使用凭据、不产生付费调用。

## 错误行为

- 若落盘文件与原件摘要不符，必须视为失败而非「近似保全」。
- 若改动触及 TASK-0031 的任何既有文件，`aiflow scope` 必须拒绝。

## 回滚

删除新增文件并还原 `CHANGELOG.md` 即恢复原状。本任务不修改既有账本，回滚不涉及历史记录。

## 为什么走 AI Flow

仓库处于维护模式，多数变更不需要 task。但 AGENTS.md 的升级清单把「任务账本本身」列为仍须走 AI Flow 的类别，本变更正属于此类——它向账本写入文件。这是该清单落地后的第一次适用。

需如实记录一点边界：维护模式下 CI 走 bootstrap 路径，不再执行任务解析、`verify --ci` 与 Gate，因此该升级清单是自律约束，而非由 CI 强制。本任务的 task、证据与 Gate 均在本地完成并随变更提交。
