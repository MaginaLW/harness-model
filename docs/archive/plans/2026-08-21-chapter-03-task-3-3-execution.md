# Task 3.3 执行计划

**目标：** 实现表驱动硬规则、稳定 route 决定和仅汇总未完成决策单元的任务级路由。

**授权与绑定：** 用户要求持续推进直至完成本章，并按大块提交。本计划绑定基线提交 `fb6c83092687f6567c34247390215c660ad15ee9`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: route 引擎决定后续治理门，必须保留所有命中、拒绝不完整安全配置并确保默认 REVIEW；使用表驱动测试和全量回归。
- allowed scope: `src/aiflow/routing.py`、`tests/unit/test_routing.py`、`tests/fixtures/routing/decision-table.json`、本计划及 Chapter 3/总体状态。

## 完成边界

1. 合并硬规则与 routing 规则，按 Policy 优先级稳定评估并保留全部命中。
2. 有效 route 仅按 `BLOCK > REVIEW > ASK > AUTO` 安全序决定；无命中使用具名 `ROUTE-DEFAULT-REVIEW`。
3. 同优先级冲突、BLOCK 缺恢复条件或 AUTO 护栏不完整时返回可解释 BLOCK，不依赖文件顺序。
4. 任务级只汇总未完成单元，全部完成返回 `completed`，不覆盖单元 route。
5. 决策表、定向测试和全量质量门通过后提交并推进 Task 3.4。
