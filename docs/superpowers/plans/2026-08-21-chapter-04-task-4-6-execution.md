# Task 4.6 执行计划

**目标：** 用真实命令与持久记录串联 AUTO、ASK、REVIEW、BLOCK 和混合单元治理路径，补齐操作说明并完成 Chapter 4 退出检查与双重复核。

**授权与绑定：** 用户要求按章节持续推进并逐章完成。本计划绑定基线提交 `6614eb6417257fa48dfe4f0dd7893e46260c8afb`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: 章节退出会形成后续验证执行器的治理基线，需用端到端事件链证明不同 route 与批准类型不会互相吞并，并完成一次有界需求/质量复核。
- allowed scope: `tests/integration/test_governance_paths.py`、`docs/implementation/chapter-04-governance-workflows.md`、必要的直接缺陷修正与测试 fixture、本计划和 Chapter 4/总体状态。
- forbidden actions: 不推送、不合并、不部署、不执行真实外部动作；不得用文档断言替代运行时测试。

## 完成边界

1. AUTO 路径无需人工批准但完整通过冻结、范围、Policy、分类与 V 前置条件，范围扩大稳定拒绝并可升级。
2. ASK 缺答不能开始；回答后决定、规格摘要、事件和后续状态一致。
3. REVIEW 的 spec/code/action 批准独立，code 仍要求审核包和当前证据，action 不可替代 code。
4. BLOCK 未解除持续阻止；证据恢复后重分类保留历史；混合 ASK+REVIEW 严格先答再审。
5. 治理流程说明覆盖四条时序、三类批准、冻结、升级/恢复命令，并明确阶段一不执行真实动作。
6. 实施目录列出的定向退出检查、全量回归、Ruff、Mypy、format 与 diff 检查全部通过。
7. 需求复核与质量复核均无阻断项，Chapter 4 状态、计数、证据和总体指针原子推进到 Chapter 5。
