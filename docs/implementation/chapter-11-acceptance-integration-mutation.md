# Chapter 11：验收、集成与定向变异

状态：in progress

Chapter 11 分阶段补全 live V2 的执行证据。本章不把 Chapter 10 的 V1 基线或 acceptance/integration 的成功执行表述为 V2 passed，也不把它们视为 Gate ready。

## 11.1 已完成：离线 acceptance 与 integration 编排

- active Policy 四文件统一为 `2.1.0`。
- V2 `acceptance` 固定执行 `python -m pytest tests/acceptance -q`；`integration` 固定执行 `python -m pytest tests/integration -q`。两项均使用本地仓库和已安装依赖，不访问网络或外部服务。
- 默认 live V2 保留完整 V1 prefix，并按 Policy 顺序执行 acceptance 与 integration。每个检查的状态、退出码、时长、stdout/stderr task-local log ref、命令摘要与 pytest 工具版本来自真实进程结果。
- `--check acceptance` 或 `--check integration` 只运行所选检查，并保留 provisional 语义；未运行的必需检查不能被当作 final 或 Gate-eligible evidence。
- 计划解析继续拒绝错误 pytest 目录、错误 parser、`aiflow --help` 占位和 shell-like 命令形式。

## 11.2 已完成：受控 mutant manifest

- `.ai/mutations/phase-02-critical-manifest.json` 是仓库级、版本化权威清单，只声明五项阶段二关键保障：V2 固定必需检查、Verifier 独立性、code approval 的 passing evidence 前置、Gate 的 killed mutation 前置，以及 verification snapshot 绑定。
- `.ai/schemas/mutation-manifest.schema.json` 和 `src/aiflow/mutation_manifest.py` 提供封闭 operator、稳定 ID/path/nodeid 约束、固定仓库路径读取、重复项检查、仓库与 symlink 逃逸拒绝，以及 target/symbol/detector 的 AST 存在性检查。返回值是不可变声明；loader 不运行 mutant、不调度 pytest，也不写 evidence。
- manifest 中每项 detector 都指向普通、确定性的 pytest 测试。11.2 只证明声明和当前保障测试可定位；由 manifest 驱动的隔离变异及 detector 调度仍属于 11.3。
- `MUT-V2-003` 与 `MUT-V2-004` 的 detector 直接覆盖 `_v2_evidence_current` 对 non-passing required check 的拒绝，以及 `_v2_gate_facts` 对非 killed mutation 的拒绝，避免只存在但不触达保障的 nodeid。

## 仍待完成：11.3–11.5 targeted mutation

| 任务 | 状态 | 边界 |
|---|---|---|
| 11.2 mutant manifest | completed | 五项关键保障、封闭 schema、只读 loader 和 detector 绑定已建立；尚未执行 mutant |
| 11.3 隔离 mutant runner | pending | 尚不运行 mutation，且不得修改主工作树 |
| 11.4 killed/survived evidence | pending | 尚无 mutation 结果、日志或覆盖结论 |
| 11.5 replay/Gate failure | pending | 尚未实现 survived/missing mutant 的重放失败路径 |

`targeted_mutation` 在当前 live V2 中保持 `unverified`，reason code 为 `VERIFICATION_CHAPTER11_NOT_IMPLEMENTED`，并写入 `chapter-11-pending` manifest 与 `CHAPTER11-PENDING` 结果。因此 live V2 conclusion 必须为 failed；它不能 finalize，不能支持 code approval，也不能走向 Gate passed。

## 后续验证边界

Chapter 11.1 与 11.2 均按 `REVIEW + V1` 完成各自增量实现验证。V2 的 acceptance/integration 运行结果是独立的 pre-evidence facts，11.2 manifest 也只是后续 runner 的受控输入；11.3–11.5 尚未完成，因此 `targeted_mutation` 继续 unverified 并阻止任何 live V2 passed 宣称。完成 11.3–11.5 后，才可新增 mutation 运行、结果和重放验证；其范围、Policy、规格或验证要求变化仍须走 AI Flow 的升级、冻结、审核和批准流程。
