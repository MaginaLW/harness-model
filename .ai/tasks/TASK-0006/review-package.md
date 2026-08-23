# Review Package

## 审核目标

决定是否接受 TASK-0006 在 subject `a1de0800a640634db6cdce4e58b50358a4b7ebd0` 上完成的 Chapter 9 V2 Policy、版本化 contracts 与分类实现。

## 背景

Chapter 8 已提供结构化 design/implementation 双阶段审核。Chapter 9 将 active Policy 升级为 `2.0.0`，定义 contract-only V2，同时保持历史 V0/V1 classification、evidence 与 Gate 语义。

## 代码地图

- `.ai/policy/verification-levels.yaml`、`src/aiflow/policy.py`：1.x/2.x Policy 分支和严格 V2 prefix。
- `.ai/schemas/classification.schema.json`、`.ai/schemas/evidence.schema.json`：`1.0`/`2.0` 版本分支。
- `src/aiflow/verification_level.py`：route-independent V2 选择和任务聚合。
- `src/aiflow/verification.py`：V2 固定顺序计划解析。
- `src/aiflow/verification_service.py`：执行前 `VERIFY_V2_NOT_EXECUTABLE` 拒绝。
- `tests/`：Policy、contracts、classification、plan、status 与执行拒绝回归。

## 语义变更

Policy `2.x` 必须含恰好有序的 V0/V1/V2，V2 是完整 V1 定义前缀加四项固定 required checks。decision unit 可用封闭四布尔 facts 选择 V2；classification 仅在 effective V2 时写 `2.0`，V0/V1 继续写 `1.0`。本章不执行 V2，也不生成 V2 evidence 或改变 Gate。

## 风险

- 版本分支过宽可能让 V2 明细进入旧 `1.0` 记录。
- prefix 校验不足可能削弱 V0/V1 required checks。
- route 与 verification facts 耦合可能造成静默重分类。
- V2 fallback 或提前启动检查会伪造实现完成度。

## 证据

- 已验证：TASK-0006 V1 evidence 结论 `passed`，10 个 required checks 全部 passed。
- 累计回归 `639 passed, 3 skipped`；跳过项均为 Windows symlink 条件。
- Ruff、format、mypy、contract、scope 与 coverage 均 passed；80 行 Python diff coverage 为 `100%`。
- implementation context：`7a09fca6116902d104a8df70db9fc765bd120526ac0fd6801c8c83d61a984974`。
- evidence digest：`e56803ea46387219d7c7795591297e16611014d219bb6a650ec8597919ac7b3d`。
- 未验证：push、merge、deploy、V2 checks、独立 Verifier、mutation runner 与其他后续章节动作均未执行，且不属于本章范围。

## 审核问题

- 当前实现是否满足冻结规格的 V2 只增不减、版本绑定和 route-independent 选择？
- 旧 V0/V1 Policy、classification、evidence 和 Gate 是否保持原语义？
- V2 是否在解析或启动任何检查前稳定拒绝执行？
- 是否存在未关闭的 high/critical finding？

## 推荐结论

独立 implementation review `REV-0004` 已给出 `APPROVE` 且无 findings，建议批准当前实现。
