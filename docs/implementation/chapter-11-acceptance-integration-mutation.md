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

## 11.3 已完成：隔离 mutant runner 实现投影

- 已纳入 11.3 的实现范围是：只从固定五项 manifest 读取声明，在逐项 detached 临时 worktree 中应用封闭 AST operator，并以 shell-free、固定 argv 的 subprocess 运行唯一 detector；runner 只返回不可变的内存原始执行事实。
- 主工作树保护、受控临时根/路径 containment、worktree 注册表快照、稳定错误码与 cleanup 失败语义均属于 11.3；不会在主工作树应用 mutant，也不会自动 stash、reset、checkout 或宽泛删除。
- 本投影不等同于完整 V1 已通过。首个精确绑定的 focused integration 事务在 `MUT-V2-002` 的 Windows 只读 scratch cleanup 失败；该失败回执已封存，残留根随后由独立 single-use action 精确清理。修复后的第二个精确事务已通过：五项 baseline detector 退出码均为 `0`，对应 mutant detector 退出码均为 `1`，无 timeout/reason，主工作树状态、受控文件哈希与 Git worktree 注册表不变，事务根和五个串行 worktree 全部清理；完整回执为 `.ai/tasks/TASK-0013/action-use-659ed5eed4b25a1daf73aa636219da690fcc5cbddf1c416a9ad2aa5dc4a2ab40.md`。首次完整 V1 的两次 full pytest 均为 `786 passed, 3 skipped`，两次 runner/十个 worktree 完全清理，但 Ruff format 与 `87%` diff coverage 令结论 failed；随后仅以 mocked unit 修复格式和缺口，52 个定向 unit 与 `90.6%` unit-only diff coverage 已通过，完整 V1 rerun 仍须新的 subject-bound action approval。
- mutant 的 `0`/`1` 在 11.3 仅为原始 probe fact；不命名或持久化为 killed/survived，不写 task evidence/log ref，也不改变 live V2、approval 或 Gate 结论。

## 仍待完成：11.4–11.5 targeted mutation

| 任务 | 状态 | 边界 |
|---|---|---|
| 11.2 mutant manifest | completed | 五项关键保障、封闭 schema、只读 loader 和 detector 绑定已建立；尚未执行 mutant |
| 11.3 隔离 mutant runner | completed | 实现投影和 focused integration 已通过；首次完整 V1 因 format/diff coverage 失败，remediation 已定向通过，完整 V1 rerun 待新 action approval |
| 11.4 killed/survived evidence | pending | 尚无 mutation 结果、日志或覆盖结论 |
| 11.5 replay/Gate failure | pending | 尚未实现 survived/missing mutant 的重放失败路径 |

`targeted_mutation` 在当前 live V2 中仍保持 `unverified`，reason code 为 `VERIFICATION_CHAPTER11_NOT_IMPLEMENTED`，并写入 `chapter-11-pending` manifest 与 `CHAPTER11-PENDING` 结果。因此 live V2 conclusion 必须为 failed；它不能 finalize，不能支持 code approval，也不能走向 Gate passed。11.3 的隔离 runner 实现不改变这一结论。

## 后续验证边界

Chapter 11.1 与 11.2 均按 `REVIEW + V1` 完成各自增量实现验证。11.3 已完成隔离 runner 的实现投影和一次修复后的 focused integration pass；首次完整 V1 失败证据已保留，format 与 changed-line coverage remediation 只通过定向 unit/static 检查，尚不能替代新的完整 V1。focused/V1 中的 mutation 退出码仍只是 task-local 原始执行事实，也未新增持久 killed/survived evidence。V2 的 acceptance/integration 运行结果是独立的 pre-evidence facts，11.2 manifest 也只是后续 runner 的受控输入。11.4–11.5 尚未完成，故 `targeted_mutation` 继续 unverified 并阻止任何 live V2 passed 宣称。完成 11.4–11.5 并取得所需验证证据后，才可新增持久 mutation 结果和重放验证；其范围、Policy、规格或验证要求变化仍须走 AI Flow 的升级、冻结、审核和批准流程。
