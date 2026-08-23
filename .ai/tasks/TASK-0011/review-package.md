# Review Package

## 审核目标

确认 TASK-0011 在 subject `c5132446450aba9a8fe09ee839425c126bb134eb` 上完成的 Chapter 11.1 变更准确满足冻结规格：V2 `acceptance` 与 `integration` 由确定性、离线、无 Shell 的 pytest 检查真实执行并保留过程证据；定向运行保持 provisional；`targeted_mutation` 仍明确未实现并阻止真实 live V2 通过。

## 背景

Chapter 10 已建立独立 Verifier、V2 两阶段 evidence 与 Gate 契约，但当时 Chapter 11 的 acceptance、integration 与 targeted mutation 都不可执行。TASK-0011 只完成 Chapter 11.1，并将 active Policy 四文件一致升级到 `2.1.0`。任务因刻意不实现 mutation 而按 `REVIEW + V1` 自举验证；这不是验证降级，也不构成 live V2 passed。

首次实现审查 `REV-0004` 发现两个问题：定向 V2 evidence 被 mutation 占位错误强制为 failed，以及 Chapter 11 状态中的提交角色表述不清。两项 finding 已在 revisions 2/3 中关闭；修复后重新同步 subject、完整重跑 V1，并以新 context 记录 `REV-0005 APPROVE`。

## 代码地图

- `.ai/policy/*.yaml`：四份 active Policy 统一为 `2.1.0`；`verification-levels.yaml` 将 acceptance/integration 固定为对应离线 pytest argv，其余三份只改版本字段。
- `src/aiflow/verification.py`：对 acceptance/integration 的目标目录、argv 与 pytest parser 进行精确语义校验。
- `src/aiflow/verification_service.py`：默认 V2 在完整 V1 prefix 后执行 acceptance/integration；定向成功为 provisional，定向真实失败仍为 failed；mutation 保持不执行。
- `tests/acceptance/test_v2_acceptance.py`、`tests/unit/test_verification_plan.py`：锁定 Policy 计划、顺序、固定命令与拒绝路径。
- `tests/integration/test_verify_command.py`、`tests/integration/test_v2_acceptance_integration.py`、`tests/integration/test_templates_and_policy.py`：覆盖默认/定向编排、真实日志和版本、失败优先、pending mutation 及 Policy 契约。
- README、Quickstart、Chapter 9/11 实施记录和 chapter/overall 状态：记录 Policy 历史边界、11.1 完成、11.2–11.5 pending 及 live V2 失败边界。

## 语义变更

默认 live V2 现在按 Policy 顺序执行完整 V1 prefix、`pytest tests/acceptance -q` 与 `pytest tests/integration -q`，并从真实进程结果写入各自的状态、退出码、超时、时长、stdout/stderr log ref、命令摘要和 pytest 版本。`--check acceptance` 或 `--check integration` 只启动所选检查：所选检查和 Verifier 角色事实通过时 evidence 为 provisional 并返回 `IMPLEMENTING`；所选检查非零、超时、缺结果或工具不可用时仍为 failed。

`targeted_mutation` 不启动命令，继续写入 `unverified`、`VERIFICATION_CHAPTER11_NOT_IMPLEMENTED`、`chapter-11-pending` manifest 和 `CHAPTER11-PENDING` 结果。默认 live V2 因此始终 failed，不能 finalize、批准代码或通过 Gate。V0/V1 schema、计划、approval 与 Gate 语义保持不变。

## 风险

- 定向 evidence 若掩盖真实检查失败，会产生误导性 provisional；当前实现仅在全部所选检查和角色事实 passed 时返回 provisional，并有成功/失败端到端测试。
- V2 后处理若覆盖 acceptance/integration 真实结果，会破坏可审计性；升级逻辑只改写 pending mutation，真实 process fields 保持不动。
- Policy 语义变化若版本不同步会导致 bundle 漂移；四文件均为 `2.1.0`，cross-file loader 与精确断言已验证。
- 将 acceptance/integration passed 写成 live V2 passed 会越过 mutation 门；所有文档、状态和测试继续明确 mutation unverified、11.2–11.5 与两个 chapter exit checks pending。
- Chapter 状态不能自引用尚不存在的最终提交哈希；状态明确把 `de0e260` 标为投影前的 implementation snapshot，并以 task-local evidence 作为当前验证 subject 的权威来源。

## 证据

- 已验证：当前 subject 为 `c5132446450aba9a8fe09ee839425c126bb134eb`；base 为 `b6189010660e4e3adfd8f68309a95b7d81bdc419`。
- 冻结规格：`e0963471d8be49a33d6dc14c68561bc726c8ebebef8408d9d0f64b2fbaebb91f`；Policy `2.1.0`：`f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`。
- 当前 V1 evidence：`debf8c3764cb68d8e5c5ab7e30336e28c8ce22c11ce49a9d0e6d7a802d89de71`，10 个 required checks 全部 passed。
- unit：`407 passed, 2 skipped`；全量回归及 branch coverage：`693 passed, 3 skipped`；Python diff coverage：`100%`（10 行、0 missing）。
- contract、scope、Ruff、format、smoke、mypy、coverage XML 与 diff coverage 均 passed；定向修复测试另有 `43 passed`。
- 实现审查：`REV-0005 APPROVE`，绑定 context `f214ae52de08bf293dd6b453a0413f7b9d69cffdf71c9200201577c408fa1938`，无 findings。
- 未验证且未执行：targeted mutation、Chapter 11.2–11.5、两个 Chapter 11 exit checks，以及 push、merge、deploy、publish、delete、task close 等外部或高风险动作。

## 审核问题

- acceptance/integration 是否只使用固定 argv、离线依赖与现有无 Shell runner，并保留真实过程结果？
- 默认 V2 与定向 V2 是否分别满足 mutation-failed 和 provisional/failure-priority 边界？
- targeted mutation 是否始终保持未执行、unverified，且无法被 finalize、approval 或 Gate 包装为 passed？
- Policy `2.1.0`、历史 `2.0.0`、规格、subject、evidence、review 和状态计数是否互相一致？
- V0/V1、schema、Gate、approval、review 与历史 artifacts 是否无语义回归？
- 是否仍存在未关闭的 high 或 critical finding？

## 推荐结论

`REV-0004` 的 high/medium findings 已关闭，修复后的完整 V1 evidence 当前且通过，`REV-0005` 对新 subject/evidence 给出 `APPROVE` 且无 findings。建议批准 TASK-0011 当前代码与文档变更，使任务进入 `APPROVED_FOR_MERGE`；该批准不授权 push、merge、deploy、close，也不代表真实 live V2 passed。
