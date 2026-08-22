# Chapter 8：结构化设计审核与实现审核

状态：completed
阶段二目标仓库：`harness-model`

## 本章结果边界

本章已将现有自包含审核包扩展为可执行的 design/implementation 双阶段审核契约，增加结构化发现、最小审核上下文和 freshness/approval 前置关系。

本章不实现 V2 evidence、独立 Verifier、定向变异、Gate 新规则或完整 Hooks；这些能力按阶段二实施目录在后续章节交付。

## 当前进度

| 任务 | 状态 | 证据 |
|---|---|---|
| 8.1 审核记录与发现契约 | completed | `review-context` / `review-record` schema 与不可变 revision |
| 8.2 最小审核上下文 | completed | design/implementation 分阶段 context、canonical SHA-256、diff/evidence 摘要 |
| 8.3 发现处置与 freshness | completed | high/critical 阻断、追加式 resolve、当前事实失效判断 |
| 8.4 `aiflow review` 命令 | completed | `context`、`record`、`resolve`、`show` |
| 8.5 集成与文档 | completed | approval/validate 集成、旧 fixture 迁移、操作说明与累计回归 |

## 兼容性护栏

- 现有 `review.py` 的 8 节包作为输入兼容基线。
- 现有 approval 的 `spec`、`code`、`action` 类型不合并。
- Chapter 8 不修改 evidence schema、verification Policy 或 Gate。
- 新审核记录使用独立版本化 contract，拒绝未知字段。

## 验证证据

- design review `REV-0001` 绑定 TASK-0005 当前冻结规格，结论 `APPROVE`；唯一 high finding 已在规格中关闭。
- 核心实现提交：`8305ed6`。
- 累计回归：`600 passed, 3 skipped`；跳过项均为 Windows symlink 能力条件。
- Ruff、format check 与 mypy 全部通过。
- Chapter 8 不改变 evidence schema、verification Policy、Gate 判定或 V0/V1。
