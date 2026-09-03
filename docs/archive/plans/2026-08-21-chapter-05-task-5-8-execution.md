# Task 5.8 执行计划

**目标：** 用章节级端到端回归和操作说明闭合 Verification as Code、证据失效与只读 Gate 链路，完成第五章退出检查。

**授权与绑定：** 用户要求按章节持续推进并逐块提交。本计划绑定基线提交 `911b5e9`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: 本任务是章节退出面，需要用真实工作流复核第五章已有单一来源，而不是增加新的判定规则。
- allowed scope: `tests/integration/test_verification_evidence_flow.py`、`docs/implementation/chapter-05-verification-evidence.md`、必要的 Chapter 5 测试邻接修正、本计划和 Chapter 5/总体状态。
- forbidden actions: 不新增规则副本、不降低 V0/V1 或 route、不伪造 evidence、不执行 action、不推送/合并/部署。

## 完成边界

1. 通过链覆盖 V0/V1、可复现检查、evidence、状态与 Gate。
2. 失败/恢复链保留旧日志并用新运行证据恢复，不让旧失败证据放行。
3. current-task governance attestation、外部提交、规格和 Policy 变化按统一 freshness 语义失效。
4. CI 临时目录证据与 Gate 只读消费闭合，仓库根无覆盖产物。
5. 文档说明计划、final/provisional、日志脱敏、版本绑定、Gate 退出码与排障。
6. 第五章指定退出命令、覆盖率、全量回归和精简双重复核通过后提交并进入第六章。
