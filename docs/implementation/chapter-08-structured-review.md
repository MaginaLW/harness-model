# Chapter 8：结构化设计审核与实现审核

状态：planned
阶段二目标仓库：`harness-model`

## 本章结果边界

本章将现有自包含审核包扩展为可执行的 design/implementation 双阶段审核契约，增加结构化发现、最小审核上下文和 freshness/approval 前置关系。

本章不实现 V2 evidence、独立 Verifier、定向变异、Gate 新规则或完整 Hooks；这些能力按阶段二实施目录在后续章节交付。

## 当前进度

| 任务 | 状态 | 证据 |
|---|---|---|
| 8.1 审核记录与发现契约 | pending | 等待 design/spec approval |
| 8.2 最小审核上下文 | pending | — |
| 8.3 发现处置与 freshness | pending | — |
| 8.4 `aiflow review` 命令 | pending | — |
| 8.5 集成与文档 | pending | — |

## 兼容性护栏

- 现有 `review.py` 的 8 节包作为输入兼容基线。
- 现有 approval 的 `spec`、`code`、`action` 类型不合并。
- Chapter 8 不修改 evidence schema、verification Policy 或 Gate。
- 新审核记录使用独立版本化 contract，拒绝未知字段。

## 下一授权点

规划提交后，为 Task 8.1 创建独立 REVIEW 任务，冻结行为规格并生成 design review package。只有取得绑定当前 spec、Policy 与 base commit 的 spec approval 后才开始修改运行时代码。
