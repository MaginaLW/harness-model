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

## 11.3 已完成：隔离 mutant runner

- 已纳入 11.3 的实现范围是：只从固定五项 manifest 读取声明，在逐项 detached 临时 worktree 中应用封闭 AST operator，并以 shell-free、固定 argv 的 subprocess 运行唯一 detector；runner 只返回不可变的内存原始执行事实。
- 主工作树保护、受控临时根/路径 containment、worktree 注册表快照、稳定错误码与 cleanup 失败语义均属于 11.3；不会在主工作树应用 mutant，也不会自动 stash、reset、checkout 或宽泛删除。
- 历史上首个 focused transaction 曾在 `MUT-V2-002` 的 Windows 只读 scratch cleanup 失败，相关回执和精确清理均已保留；后续完整 V1 的一次失败及 remediation 也保留为审计历史。最终的 TASK-0013 implementation subject 是 `290254cc70791bcfa9895feab98154b411c2ef55`：其 V1 evidence 为 passed（10/10 required checks；`.ai/tasks/TASK-0013/evidence.json`），独立 implementation review `REV-0004` 为 APPROVE，随后获得 code approval。`4680a377591627d4887185b244dcbd0d43156d25` 是记录的 integration merge commit，`3c87fc931329c903e2d22feff88a4fd4966718b6` 是仅含 TASK-0013 close receipt 的后继治理提交。最终事实取代“passing V1 rerun pending”的旧投影，但不把 11.3 的 raw probe 扩展为持久 mutation evidence 或 live V2 passed。
- mutant 的 `0`/`1` 在 11.3 仅为原始 probe fact；不命名或持久化为 killed/survived，不写 task evidence/log ref，也不改变 live V2、approval 或 Gate 结论。

## 11.4 已完成：killed/survived evidence

- `.ai/schemas/mutation-evidence.schema.json`、`src/aiflow/mutation_evidence.py` 和对应 contract/unit/integration tests 将固定五项 raw probe facts 封闭地记录为 immutable mutation-evidence artifact、五份有界结构化 log 与 manifest 顺序的 uncovered 集合；记录和 loader 绑定当前 task、base/subject、spec、Policy、classification、manifest 与 runner hashes。
- 在投影前实现 subject `62df888baf2afa858ef096949ab1ade861cef7ea` 上，approved focused transaction 产生一个 record；approved local V1 的 regression 与 coverage collection 分别产生两个不同 record。三次 production collection 均观察五项 baseline detector `(0, 0, 0, 0, 0)`、mutant detector `(1, 1, 1, 1, 1)`、无 timeout/reason、五项 `killed`、`uncovered_mutation_ids: []` 和 `main_tree_unchanged: true`；三个 scratch roots 与十五个串行 worktrees 均无残留。
- 可提交的审计索引是 focused receipt `.ai/tasks/TASK-0014/action-use-997bdb20ca1ca1a9e374df0f6797484a20b209455ed850cf21cbd90578538c43.md`（file SHA-256 `eea9969e6c3d1a0ea053a34f2075c603ed195b245e00e4452bb32928124721f2`；canonical mutation-evidence SHA-256 `0d1bb294c1c07531fe17ca26936214d47705b2fb3ed1f69eeee2445fcee4638a`）和 local V1 receipt `.ai/tasks/TASK-0014/action-use-5aacdcd307e58560328646d34d272e176d4d076c8f66229084e2afb2cbaf11a4.md`（file SHA-256 `bdb6ed9975223350fcc6dda9744c5ee030291ccd9a504114826176f55d878fb6`；two canonical mutation-evidence SHA-256 values `f2730e54e40f71efbe052796fd618f5105fa6dc5efa6d0f916a72e92b41eb00a` and `ee329846aedb75ea91de3ccd91ec407032a7b7a81e2f8cf5e02c27ca0c9de143`）。V1 evidence is passed with 10/10 required checks and has file SHA-256 `538dc3bfe0fabdfe863daaae0a193554a79857d7a252a388932f01f7d83c3a76`; independent implementation review `REV-0002` is APPROVE.
- Task-local record JSON and structured logs are deliberately excluded by `.gitignore`. The receipts are auditable hash indexes of their local existence, references, and cleanup facts; they do not claim that ignored log or evidence bodies survive another checkout or machine, and they cannot be reused by 11.5.

## 仍待完成：11.5 targeted mutation consumer 与 replay/Gate failure

| 任务 | 状态 | 边界 |
|---|---|---|
| 11.2 mutant manifest | completed | 五项关键保障、封闭 schema、只读 loader 和 detector 绑定已建立；尚未执行 mutant |
| 11.3 隔离 mutant runner | completed | 最终 V1、独立 implementation review、code approval、integration merge 与 close facts 已记录；runner 原始 probe 不单独构成持久 evidence |
| 11.4 killed/survived evidence | completed | 投影前 subject 的 focused 与 local V1 production records 已由 receipt hash indexes 审计；三次均为五项 killed、无未覆盖项，local records/logs 不跨 checkout 保留 |
| 11.5 replay/Gate failure | pending | 尚未实现 survived/missing mutant 的重放失败路径 |

`targeted_mutation` 在当前 live V2 中仍保持 `unverified`，reason code 为 `VERIFICATION_CHAPTER11_NOT_IMPLEMENTED`，并写入 `chapter-11-pending` manifest 与 `CHAPTER11-PENDING` 结果。因此 live V2 conclusion 必须为 failed；它不能 finalize，不能支持 code approval，也不能走向 Gate passed。11.3 的隔离 runner 实现不改变这一结论。

## 后续验证边界

Chapter 11.1、11.2 与 11.4 均按 `REVIEW + V1` 完成各自增量实现验证；11.3 的最终 V1、review、code approval、integration merge 与 close facts 也已审计记录。11.4 的 standalone mutation-evidence 仅证明当前 local action transactions 的受控结果，不被 live V2、approval 或 Gate 消费，也不能跨 task、subject、spec、Policy 或 checkout 复用。11.5 尚未完成，故 `targeted_mutation` 继续 unverified 并阻止任何 live V2 passed 宣称；完成其 consumer/replay enforcement 并取得新的 current evidence 后，才可改变该结论。
