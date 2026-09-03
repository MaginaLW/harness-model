# Task 4.5 执行计划

**目标：** 实现结构化 `escalate` 与版本绑定的解除条件记录，保证 route 只能升级，命名失效原因只能触发同级重新评估，BLOCK 恢复必须有完整证据。

**授权与绑定：** 用户要求按章节持续推进并逐章完成。本计划绑定基线提交 `d041c8496accdacb711e987ef37eba3e99dd3a53`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: 升级会改变治理路径并可能阻止继续实施，必须记录稳定原因、影响、下一步和当前版本身份；解除记录必须可审计且不能被旧证据重用。
- allowed scope: `src/aiflow/escalation.py`、`src/aiflow/cli.py`、`src/aiflow/state.py`、必要的 classification/task service 邻接修正、`tests/integration/test_escalate_command.py`、直接相关 fixture、本计划和 Chapter 4/总体状态。
- forbidden actions: 不推送、不合并、不部署；不得降低 route、用自定义原因同级重评或无证据解除 BLOCK。

## 完成边界

1. 固定原因码覆盖范围扩大、连续失败、依赖/权限/网络凭据、方向发现、不可验证、备份失效、任务变化、Policy 与规格摘要变化；影响和下一步均必填。
2. `escalate` 保存原/新 route、触发信号、影响、下一步和已有成果处理，BLOCK 进入 BLOCKED，其余进入 ESCALATED。
3. 所有降级拒绝；只有 `policy_changed`、`spec_changed` 可在相同 route 下进入 ESCALATED 重新分类。
4. 解除记录逐项保存非空证据引用并绑定前一分类和本轮预期 input/Policy，重新分类只接受相邻且匹配的记录。
5. 全部原因、升级组合、同级命名失效、非法同级/降级/缺字段以及 BLOCK 有无完整证据恢复测试通过。
6. 定向测试、CLI help、累计回归、Ruff、Mypy 与 diff 检查通过后完成 Task 4.5 并本地提交。
