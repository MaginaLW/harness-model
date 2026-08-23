# Review Package

## 审核目标

决定是否接受 TASK-0009 在 subject `8eee9c1bb3c7c4ac35aa7843a1a3ec85e0fb4326` 上完成的 Chapter 10 独立 Verifier、两阶段 V2 evidence/Gate，以及当前任务治理提交的 `begin` 基线兼容实现。

## 背景

Chapter 9 已定义 contract-only V2，但不允许执行。Chapter 10 在不改变 routing/verification Policy 与 V0/V1 语义的前提下，为 V2 增加可重放的角色独立性、最小不可变 Verifier context、pre/final 两阶段 evidence 和 Gate 判定。Chapter 11 拥有的 acceptance、integration 与 targeted mutation runner 仍不在本章范围内。

## 代码地图

- `.ai/schemas/`、`.ai/templates/`、`src/aiflow/contracts.py`：Verifier context、V2 evidence 与 review context 的版本化契约。
- `src/aiflow/verifier_service.py`：actor 解析、最小上下文生成、canonical SHA-256、不可变 task-local 存储与 freshness 校验。
- `src/aiflow/evidence.py`、`src/aiflow/review_service.py`：稳定 verification snapshot、pre/final evidence 与 implementation review 绑定。
- `src/aiflow/verification_service.py`、`src/aiflow/cli.py`：V2 actor 前置拒绝、V1 前缀执行、Chapter 11 检查显式 unverified，以及无 runner 的 `--finalize`。
- `src/aiflow/gate.py`、`src/aiflow/approval.py`：V2 final、snapshot、context、双 review、required checks、mutation 和 attestation 门禁。
- `src/aiflow/task_service.py`：只允许当前任务治理路径位于 `subject_commit..HEAD` 的 `begin` 兼容。
- `tests/` 与 `docs/`：契约、单元、集成、E2E 回放、运维边界和 Chapter 10 状态说明。

## 语义变更

V2 verify 在任何 runner 启动前要求 trim 后的 Implementer 与 Verifier actor 非空且不同，并生成绑定 task/repository/base/subject/spec/Policy/classification 的不可变 context。V2 pre evidence 固定验证事实与 snapshot，implementation review 绑定该 snapshot，随后 `--finalize` 只追加 current implementation review ref。V2 Gate 只接受 current final evidence；V0/V1 继续使用既有 `1.0` evidence、完整 evidence hash 和执行路径。真实 V2 live run 只执行既有 V1 前缀，其余 Chapter 11 检查写为 unverified，因此必然 failed。

## 风险

- snapshot 投影遗漏字段可能允许 review 与最终证据漂移；实现采用 canonical 投影并覆盖篡改拒绝测试。
- actor/context 校验晚于 runner 会破坏独立性边界；实现和测试均要求进程启动前拒绝。
- V2 规则倒灌可能破坏 V0/V1；旧 schema、完整 evidence hash、Gate 与 actor 回归均保留。
- 治理-only `begin` 兼容若过宽会越过业务变更；实现只接受当前任务 `.ai/tasks/TASK-0009/**`，并拒绝业务路径和其他任务路径。
- Chapter 11 checks 尚未实现；系统显式生成 failed pre evidence，不能伪装为可进入 final Gate 的 live V2。

## 证据

- TASK-0009 当前 V1 evidence 绑定 subject `8eee9c1bb3c7c4ac35aa7843a1a3ec85e0fb4326`，10 个 required checks 全部 passed。
- 全量回归与 branch coverage 各为 `680 passed, 3 skipped`；跳过项均为 Windows symlink 条件。
- Ruff、format、mypy、contract、scope、smoke、unit、regression 与 coverage 均 passed；468 行 Python diff coverage 为 `91%`，高于 90% 门槛。
- implementation review context：`a42bd4bd72e04cf16208d8f75b04091050f23a8c22c7e0d46e85650fcfe23ad6`；evidence digest：`0a7e93bc30cb7680b2e27eff75df01dd10e6c12b56ae7c70b2fd829a6c39d61c`。
- E2E 使用确定性完整 V2 fixture 回放 pre → implementation review → finalize → code approval → local Gate PASS，并验证 finalize 不启动 runner、snapshot 不变及 context 篡改拒绝。
- 未执行 push、merge、deploy 或真实 Chapter 11 runner；这些动作不在本章授权和范围内。

## 审核问题

- 当前实现是否严格满足冻结规格的 actor/context、两阶段 snapshot 和 finalization 边界？
- V2 Gate 与 code approval 是否拒绝 pre、陈旧/篡改 context、失配 review、未通过 required check 和非 killed mutation？
- V0/V1 的契约、完整 evidence hash、执行与 Gate 语义是否保持不变？
- `begin` 是否只接受当前任务治理提交，同时继续拒绝业务或其他任务路径？
- 是否存在未关闭的 high/critical finding？

## 推荐结论

独立 implementation review `REV-0002` 给出 `APPROVE` 且无 findings，建议批准当前实现。残余风险仅为规格明确延期到 Chapter 11 的真实 acceptance、integration 与 targeted-mutation 执行。
