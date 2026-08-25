# Chapter 11：验收、集成与定向变异

状态：in progress

Chapter 11 分阶段补全 live V2 的执行证据。本章不把 Chapter 10 的 V1 基线或 acceptance/integration 的成功执行表述为 V2 passed，也不把它们视为 Gate ready。

## 11.1 已完成：离线 acceptance 与 integration 编排

- active Policy 四文件统一为 `2.1.0`。
- V2 `acceptance` 固定执行 `python -m pytest tests/acceptance -q`；`integration` 固定执行 `python -m pytest tests/integration -q`。两项均使用本地仓库和已安装依赖，不访问网络或外部服务。
- 默认 live V2 保留完整 V1 prefix，并按 Policy 顺序执行 acceptance 与 integration。每个检查的状态、退出码、时长、stdout/stderr task-local log ref、命令摘要与 pytest 工具版本来自真实进程结果。
- `--check acceptance` 或 `--check integration` 只运行所选进程且不调度 mutation；但 V2 的必需 mutation artifact 缺失时整体结论仍为 `failed`，不能用 partial/provisional 语义掩盖，也不能成为 Gate-eligible evidence。只有显式选择并通过 `targeted_mutation`、且所选检查与 verifier role fact 同时完整时，partial observation 才可为 provisional。
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

## 11.5 实现已落地，当前治理验证待完成：targeted mutation consumer 与 replay/Gate failure

- V2 evidence 的 `targeted_mutation` 现在必须绑定 repository-relative `evidence_ref`、canonical `mutation_evidence_sha256`、权威 manifest reference，以及严格按 `MUT-V2-001` 至 `MUT-V2-005` 排序的五项 projection；verification snapshot 同时绑定这些 artifact identity 与结果事实。
- `consume_targeted_mutation_evidence` 不信任内嵌 outcome。它通过 public loader 重放当前 task/subject/spec/Policy/classification/manifest/runner 绑定、canonical digest、结构化日志与 uncovered 集合，再把唯一的 current/all-killed fact 提供给 verification、code approval 和 Gate。missing、陈旧、篡改、顺序/身份不符、survived 或 unverified 均 fail closed。
- 完整 local V2 的生产调用图固定为 verification service 调用一次 recorder、既有 runner 一次、shared consumer 内的 public loader 一次，再投影到 V2 evidence。授权闸门位于 public recorder 本身：它只识别 task 目录直接子项 `action-v2-targeted-mutation-*.json`，要求 action type `targeted_mutation_v2`、target 为当前 task、决策单元声明 `action_approval`/targeted mutation、并把当前 classification input SHA-256、spec、Policy、base、subject 和精确 action canonical SHA 绑定到 current approval。
- recorder 在任何 runner 调用前先拒绝尚有 `approval_pending.json` 的未完成审批事务，再在 task-local 跨进程锁内以排他 create-new 方式写入并 fsync `action-use-<canonical-action-sha256>.md`，捕获 receipt 的 device/inode 后才把同一身份与精确 action digest 作为 `consumed` 事件原子追加到任务历史；事件持久化失败时 receipt 仍作为不可重用的消费标记保留。随后会重验同一 action 文件、approval、expiry、classification/spec/Policy/base/subject、HEAD、governance-only worktree、账本记录和 receipt 身份；runner 入口不能只凭合成 receipt/token 启动，它会独立重放这些权威绑定，并以排他 `action-launch-<digest>.json` claim 固化唯一一次 launch。结果只通过已校验身份的 append fd 写回，替换为普通文件或 symlink 均 fail closed。并发双消费和 token 重放都不能产生第二次 runner，旧 subject/旧 classification/已用批准不能复用；只有新的精确 action 文件和单独批准才能授权 retry。内部 token 仍只是 trusted-code 的防误用载体，不是抵御能够改写 Python 进程或本地任务历史的安全沙箱；真正的执行门来自当前 approval、append-only consumed event、receipt identity 和 single-use launch claim 的共同重验。本地事件日志仍依靠 AI Flow strict replay、Git 审计和禁止重写历史的工作约定。`--check acceptance`/`integration` 不隐式运行 mutation，CI 或未授权/缺失 artifact 保持失败。
- `MUT-V2-004` 保留原 manifest ID、保障目标、operator 名称和 detector；其封闭 AST 锚点迁移到 Gate 的共享 consumer `passed` 守卫，使“接受非 killed mutation”的 mutant 仍是非等价且必须被 detector 杀死。找不到唯一锚点或锚点歧义仍为 operator precondition failure。
- 离线 acceptance、integration、unit 与 E2E replay 覆盖 all-killed、survived、unverified、missing、projection/digest tamper、approval/Gate 同源拒绝、snapshot tamper，以及 V1 零 mutation 调用。当前实现全量测试已通过；真实 action-approved mutation collection、final V2 evidence 与 implementation review 仍是 TASK-0015 的治理完成门。

| 任务 | 状态 | 边界 |
|---|---|---|
| 11.2 mutant manifest | completed | 五项关键保障、封闭 schema、只读 loader 和 detector 绑定已建立；尚未执行 mutant |
| 11.3 隔离 mutant runner | completed | 最终 V1、独立 implementation review、code approval、integration merge 与 close facts 已记录；runner 原始 probe 不单独构成持久 evidence |
| 11.4 killed/survived evidence | completed | 投影前 subject 的 focused 与 local V1 production records 已由 receipt hash indexes 审计；三次均为五项 killed、无未覆盖项，local records/logs 不跨 checkout 保留 |
| 11.5 replay/Gate failure | in progress | consumer、schema、verify、approval/Gate、operator 与 synthetic replay 已实现；真实 current action-approved collection、V2 evidence 和 implementation review 待完成 |

完整 local V2 不再写入 `chapter-11-pending` 或 `CHAPTER11-PENDING` 占位；它只接受本任务当前版本中新采集并由 public loader 重验的 artifact。没有合规授权或 artifact、任一结果非 killed、任何 replay/binding 失败，或 selected run 缺少 mutation 时，targeted-mutation check 与 V2 conclusion 均为 failed，code approval 和 Gate 同步拒绝。当前 TASK-0015 尚未执行真实 action-approved collection，因此本文不宣称 live V2、code approval 或 Gate 已通过。

## 后续验证边界

Chapter 11.1、11.2 与 11.4 均按 `REVIEW + V1` 完成各自增量实现验证；11.3 的最终 V1、review、code approval、integration merge 与 close facts 也已审计记录。11.4 的 standalone mutation-evidence 仅证明当时 local action transactions 的受控结果，不能跨 task、subject、spec、Policy 或 checkout 复用。11.5 的行为实现已由 synthetic replay 和全量回归覆盖，但任务及 Chapter 11 状态继续保持 in progress；只有取得 TASK-0015 当前 subject 的独立 action approval、真实五项 evidence、passing V2、implementation review 和所需批准后，才能投影完成与两个 exit checks。
