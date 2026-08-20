# Task 3.2 执行计划

**目标：** 实现可验证的决策单元输入和无代码执行能力的受限谓词层。

**授权与绑定：** 用户要求持续推进直至完成本章，并按大块提交。本计划绑定基线提交 `545aedba2ef37d695db04c9ab82d62ee9bf4a889`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: 决策单元和谓词将成为后续 route 与验证等级的确定性事实层；使用受限语法、定向测试和全量回归，不引入额外审核流程。
- allowed scope: `src/aiflow/decision_units.py`、`src/aiflow/predicates.py`、`tests/unit/test_decision_units.py`、`tests/unit/test_predicates.py`、`.ai/templates/task.yaml`、本计划及 Chapter 3/总体状态。

## 完成边界

1. 从 task 文档解析、排序并校验决策单元，拒绝重复 ID、空影响、未知可逆性和未声明权限。
2. 仅实现规范列出的八种谓词与受限点号路径，不允许表达式、正则或任意函数执行。
3. 匹配结果稳定且解释不包含敏感值；缺字段遵守 Policy，硬风险缺失采取保守结论。
4. 覆盖全部成功、错误类型和注入场景；定向测试及全量质量门通过后提交并推进 Task 3.3。
