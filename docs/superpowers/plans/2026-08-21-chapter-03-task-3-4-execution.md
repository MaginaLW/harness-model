# Task 3.4 执行计划

**目标：** 以独立、结构化事实实现 V0/V1 判定和仅汇总未完成决策单元的任务级验证等级。

**授权与绑定：** 用户要求持续推进直至完成本章，并按大块提交。本计划绑定基线提交 `e863a9c07253077b7fa46e6f1a9726f2ede22ec5`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: V 等级影响证据门，必须与 route 独立并从封闭事实确定；现有 Schema 缺少行为、代码、交互、回归和可检测性字段，因此做向后兼容的最小契约扩展。
- scope change: 实施目录原列出的引擎/测试范围扩展到决策单元 Schema、任务模板与四个冻结黄金输入；不修改 route Policy，不以路径或自然语言推断等级。
- allowed scope: `src/aiflow/verification_level.py`、`tests/unit/test_verification_level.py`、`tests/fixtures/verification/level-table.json`、`.ai/schemas/decision-unit.schema.json`、`.ai/templates/task.yaml`、`examples/scenarios/*/input.yaml`、直接相关契约测试、本计划及 Chapter 3/总体状态。

## 完成边界

1. 新增可选且封闭的 `change_characteristics`；旧记录仍满足 Schema，但缺字段保守判 V1。
2. V0 只允许显式机械、局部、非行为、非代码、无回归、高可检测性且 V0 Policy 检查完整的单元。
3. 行为/代码/跨文件或跨模块/回归风险/低可检测性任一成立即 V1；工具缺失保留等级并附 BLOCK 原因。
4. API 不接收 route；任务级只汇总未完成单元并保留逐单元规则与解释。
5. 覆盖 AUTO+V1、ASK+V0、REVIEW+V1、工具缺失和完成单元场景；定向及全量质量门通过后提交并推进 Task 3.5。
