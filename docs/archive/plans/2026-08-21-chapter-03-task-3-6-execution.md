# Task 3.6 执行计划

**目标：** 用真实 Policy 和分类服务锁定四类黄金场景、变形关系和第三章退出证据。

**授权与绑定：** 用户要求持续推进直至完成本章，并按大块提交。本计划绑定基线提交 `5e8363c1c40af6a16c5d395af4075ad2b6f2ff92`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: 本任务是章节累计验收，使用真实服务、真实 Policy、黄金与变形测试、文档和双重复核，不增加额外审核层。
- scope refinement: Chapter 1 黄金 expected 的 route/V/state 保持不变；将人工预期 reasons 收敛为运行时可程序比较的 Policy 规范解释，并更新场景 README，不改变业务结论。
- allowed scope: `tests/integration/test_golden_classification.py`、`docs/implementation/chapter-03-routing-verification.md`、`examples/scenarios/*/expected.json`、`examples/scenarios/README.md`、必要的直接相关测试/实现修正、本计划及 Chapter 3/总体状态/README。

## 完成边界

1. 四类场景逐个通过真实 `classify_task`，比较 route、V、规则 ID、有序理由和最终状态，不 mock 路由。
2. AUTO 输入增加 CI、真实外部副作用、缺失验证工具时分别得到 REVIEW、REVIEW 或 BLOCK、BLOCK；恢复基线事实再次得到 AUTO，并沿用 3.5 的合法解除/降级保护证据。
3. 文档说明决策单元、硬规则、默认 REVIEW、任务汇总、V 等级独立、解释与 Policy 摘要，并给出四类 CLI 输出样例。
4. 运行实施目录列出的章节定向门、集成门、全量回归、Ruff、格式、mypy 与 diff 检查。
5. 完成需求复核和质量复核；Chapter 3/总体状态标记完成，当前指针推进 Chapter 4 / Task 4.1，并按大块提交。
