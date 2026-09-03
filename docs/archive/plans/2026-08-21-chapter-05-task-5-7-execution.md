# Task 5.7 执行计划

**目标：** 实现只读、确定性的 `aiflow gate`，统一裁决 route、版本、规格、批准、evidence 与 Git attestation 是否满足合并门。

**授权与绑定：** 用户要求按章节持续推进并逐块提交。本计划绑定基线提交 `988f667096349fc8dca0a2cc81cf0fd549a29361`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: Gate 是最终只读裁决面，必须复用统一 freshness 与 Git 范围语义并提供稳定机器输出。
- allowed scope: `src/aiflow/gate.py`、`src/aiflow/cli.py`、必要的 freshness/status 邻接、`tests/unit/test_gate.py`、`tests/fixtures/gate/decision-table.json`、`tests/integration/test_gate_command.py`、本计划和 Chapter 5/总体状态。
- forbidden actions: 不修改任务/事件/批准/evidence，不执行动作、不自动批准、不改变 route/V、不推送/合并/部署。

## 完成边界

1. Gate 输入覆盖任务与 Git、classification、规格冻结、route/V、ASK、spec/code/action 独立批准、evidence、BLOCK/ESCALATE。
2. AUTO/ASK/REVIEW/BLOCK 与混合单元决策表返回稳定有序原因和恢复命令。
3. 本地 evidence 与显式 CI evidence 都校验 repo/subject/attestation；绝对 checkout 路径不参与裁决。
4. 默认文本和 JSON 输出稳定；通过、门禁拒绝、输入损坏使用可区分退出码。
5. Gate 重复执行严格只读，action approval 不替代代码门也不触发动作。
6. 定向/全量回归、help、ruff、format、mypy、diff check 和精简复核通过后提交。
