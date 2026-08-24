# Task Specification

## 目标

完成 Chapter 11.4：在 TASK-0013 已记录外部集成并关闭后，把现有固定五项隔离 mutation runner 的原始 probe facts 规范化为 `killed`、`survived` 或 `unverified`，连同 manifest/保障目标、当前版本绑定、受控结构化日志引用和明确未覆盖项，持久化为可校验、可重放的独立 mutation-evidence artifact。本任务不让 live V2、approval 或 Gate 消费该 artifact；11.5 完成前 `targeted_mutation` 继续保持 pending/unverified，真实 live V2 必须失败。

## 范围

1. 本规格只能在 TASK-0013 状态为 `MERGED` 后冻结。TASK-0013 的 implementation subject 固定为 `290254cc70791bcfa9895feab98154b411c2ef55`，`merge_recorded` 固定记录 integration commit `4680a377591627d4887185b244dcbd0d43156d25`；其后只含 TASK-0013 close receipt 的干净治理提交 `3c87fc931329c903e2d22feff88a4fd4966718b6` 同时作为 TASK-0014 的 `base_commit` 与初始 `subject_commit`。`.ai/tasks/TASK-0014/dependency-resolution.md` 保留这些不同 commit 的角色、精确路径和不可重用边界。TASK-0013 的 action approvals、use receipts、raw probes、logs 或剩余预算不能充当 TASK-0014 的 mutation evidence 或删除授权。
2. 新增 `.ai/schemas/mutation-evidence.schema.json`，采用 JSON Schema Draft 2020-12、`schema_version: "1.0"` 和 `additionalProperties: false`。在 `src/aiflow/contracts.py` 以固定名称 `mutation-evidence` 注册该 schema；调用方不能提供任意 schema 目录或路径。新增 `.ai/templates/mutation-evidence.json`，只作为通过 contract 的非权威示例，不能被读取为当前运行证据。
3. mutation-evidence 顶层字段精确为：`schema_version`、`record_id`、`task_id`、`repository_id`、`branch`、`base_commit`、`subject_commit`、`spec_sha256`、`policy_sha256`、`classification_input_sha256`、`manifest_id`、`manifest_ref`、`manifest_sha256`、`runner_source_sha256`、`generated_at`、`main_tree_unchanged`、`run_reason_code`、`results`、`uncovered_mutation_ids` 与 `mutation_evidence_sha256`。`record_id` 固定匹配 `MUTRUN-YYYYMMDDTHHMMSSZ-<16 lowercase hex>`；commit 使用 40 位小写 SHA-1，摘要使用 64 位小写 SHA-256；`manifest_ref` 固定为 `.ai/mutations/phase-02-critical-manifest.json`，`manifest_id` 固定为 `phase-02-critical`。不得加入自然语言 conclusion、passed、Gate-ready、绝对路径、自由命令/环境、凭据、stdout/stderr body 或 action approval 结论。
4. `results` 必须按权威 manifest 顺序精确包含五项且每项恰好一次。每项字段精确为：`mutation_id`、`safeguard_id`、`target`、`target_symbol`、`operator`、`expected_detector`、`expected_outcome`、`baseline_exit_code`、`mutant_exit_code`、`timed_out`、`duration_ms`、`reason_code`、`outcome`、`log_ref` 与 `log_sha256`。前七个声明字段必须与当前 `load_mutation_manifest(repository_root)` 结果逐字一致，`expected_outcome` 固定为 `killed`；原始 exit code 接受任意 JSON integer 或 null，从而如实保留 POSIX 负信号码、Windows/工具特定正整数和 pytest `0`–`5`，duration 非负，outcome 只接受 `killed | survived | unverified`。只有真值表中的精确 `0/1` 有成功语义，其他整数一律进入 `unverified`。
5. outcome 派生是封闭纯函数：仅当 run-level `reason_code is None`、`main_tree_unchanged is True`，且该 probe `baseline_exit_code == 0`、`mutant_exit_code == 1`、`timed_out is False`、`reason_code is None` 时为 `killed`；相同 run-level 前提下，baseline `0`、mutant `0`、无 timeout/reason 时为 `survived`；其他任何 raw fact（包括 baseline 非零、mutant 2–5、null、timeout、infra/operator/cleanup/main-tree reason 或 `MUTATION_NOT_EXECUTED`）只能为 `unverified`，不得猜测或折叠为 survived/killed。`uncovered_mutation_ids` 必须按 manifest 顺序精确等于所有 outcome 非 `killed` 的 mutation ID；全 killed 时为空数组，但这仍不是 live V2 passed。
6. 新增 `src/aiflow/mutation_evidence.py`，提供冻结 API：`record_targeted_mutation_evidence(repository_root: Path, task_id: str, subject_commit: str) -> MutationEvidenceArtifact` 与 `load_targeted_mutation_evidence(repository_root: Path, task_id: str, evidence_ref: str) -> Mapping[str, object]`。frozen `MutationEvidenceArtifact` 字段精确为 `record_id: str`、repository-relative `evidence_ref: str`、`mutation_evidence_sha256: str` 与 manifest 顺序的 `log_refs: tuple[str, ...]`。记录入口 subject 必须等于当前 task subject 并可解析为 commit，task 的 spec/Policy/classification 必须 current；它不接受时间、nonce、run directory、manifest、operator、detector、argv、环境、worktree、log 文件名、outcome 或结果数组输入。

   每次记录调用在 runner 启动前只调用一次 UTC clock并生成一次 8-byte cryptographic nonce，内部形成唯一 `record_id`，把 `generated_at` 固定为同一 UTC 秒，并以原子 `mkdir(exist_ok=False)` 在 `.ai/tasks/<task_id>/logs/<record_id>/` 预留非 symlink direct-child目录。碰撞时最多重新生成三次 nonce，仍冲突则以稳定错误失败且不运行 runner。evidence 固定写入 `<record_id>/targeted-mutation/evidence.json`，五份日志固定写入 `<record_id>/targeted-mutation/logs/<mutation_id>.json`。同一外层 V1 的两次 collection 必须获得不同 record ID，不能覆盖或复用第一份 artifact。
7. 记录入口在任何真实 worktree 创建前加载当前 task/Policy/classification/spec、权威 manifest、manifest bytes SHA、`src/aiflow/mutation_runner.py` SHA，并验证 run directory containment；随后只调用一次现有 `run_targeted_mutations(repository_root, subject_commit)`。它不得修改 TASK-0013 runner 的公开输入、五 operator、detector argv、最小环境、timeout、worktree/cleanup 或主树快照语义。runner preflight 抛错时原样失败且不伪造 artifact；runner 返回后必须验证 manifest ID、subject、五项顺序/数量与 probe 类型，再派生结果。
8. “日志”固定为有界、结构化 JSON execution summary：每个 log 只包含该项声明身份、raw integer/null exit、timeout/duration/reason、派生 outcome、run-level reason 与 `main_tree_unchanged`，字段集合由 mutation-evidence schema `$defs` 与 Python exact-key validator 共同封闭，不得尝试恢复 runner 已送往 `DEVNULL` 的原始 detector stdout/stderr。每个 log 原子写入后计算 SHA-256；evidence 的 repository-relative `log_ref` 与 `log_sha256` 必须逐项匹配。log ref 禁止绝对路径、反斜杠、dot segment、repository/task/record-root 逃逸与 symlink 逃逸。
9. `mutation_evidence_sha256` 是对完整 evidence 排除该摘要字段后的 canonical JSON（UTF-8、key sort、紧凑 separators）计算的 SHA-256。写入顺序固定为五份结构化 logs 成功后再以 create-new 语义原子写 evidence；record function 从不打开已有 record ID 重新运行。只读 loader 对同一 immutable record 的 byte-identical读取是 replay，任何内容冲突、目标预存在或 record ID 复用均拒绝且不覆盖历史。任一日志或 evidence 写入失败不得返回 artifact；已写的受控日志可以作为未引用的失败残留保留，不得用广泛删除、reset 或 clean 掩盖失败。
10. loader/validator 必须同时验证 JSON contract、record ID与路径一致性、canonical digest、当前 task/repository/branch/base/subject/spec/Policy/classification 绑定、当前 manifest/runner hashes、精确五项声明和顺序、outcome 派生、uncovered 集合、log containment/存在性/哈希与结构化 log 内容。缺失、重复、未知 mutation、跨 subject/manifest、陈旧 Policy/spec/classification、篡改 digest/log 或伪造 killed 都必须 fail closed。TASK-0014 的 artifact仅是当前本地 action transaction 的运行产物；11.5 不得跨任务复用它，必须在自己的 current subject/spec/Policy/classification 与新 action approval 下重新采集并只消费当次显式 artifact。
11. 更新 `tests/unit/test_contracts.py`，新增 `tests/unit/test_mutation_evidence.py` 和四份 valid/invalid contract fixtures，覆盖闭合 schema、缺失/额外/非法字段、任意整数/null raw exits、精确五项、canonical digest、三类 outcome、run-level failure precedence、uncovered 集合、版本陈旧、record ID/UTC/nonce与三次碰撞、路径/symlink 逃逸、log 缺失/篡改、write conflict/partial failure、不可变返回、集成测试模式选择和 runner 调用预算。unit tests 必须通过 private clock/nonce/runner/write seams，不创建真实 Git worktree，不需要 delete action approval。
12. 更新 `tests/integration/test_mutation_runner_contract.py`，冻结两种互斥模式。仅当 TASK-0014 是仓库唯一未终止 active task、其 current spec/Policy/classification 均有效且 `subject_commit` 等于 observed HEAD 时，测试必须调用一次 public `record_targeted_mutation_evidence(repository_root, "TASK-0014", subject_commit)`；该 public entry 自己调用 runner，写入 task-local unique record root，再由 public loader重新加载，并把 `MutationEvidenceArtifact` 暴露给外层 receipt 收集。不得先直接调用 runner，也不得为持久化再调用第二次。focused 与 TASK-0014 的两次完整 V1 collection 必须走此 production-record 模式，每次 collection 恰好一次真实 runner 调用。

    在 TASK-0014 已终止、不是唯一 active task、binding 不满足或普通后续仓库回归中，永久 integration test 不得调用已陈旧的 TASK-0014 production entry，也不得调用真实 runner或创建/删除任何 Git worktree；它只把冻结的 mocked `MutationRun` 经 private mapper/writer seam 写入 pytest 提供的唯一系统临时 record root后重载，校验五项模拟 raw facts、派生 outcome、uncovered、五份结构化 log 与摘要契约，不把该模式表述为真实 detector/runner 证明。TASK-0014 production 模式另须证明真实五项 baseline 均为 `0`、mutant 均为 `1`、全部 `killed`、uncovered 为空，同时保持 runner 返回前后的主工作树受控文件、预存 dirty status 与 Git worktree registry 不变。模式选择、production task/current/HEAD binding、unique task-log root、返回 artifact、active 模式恰好一次和 inactive 模式零 runner 调用由 mocked-runner tests封闭；非 production seam不能满足 TASK-0014 focused/V1 receipt。未来任务若要重跑真实 runner，必须按自己的 current subject/spec/Policy/classification 冻结显式调用图与预算并取得新的 single-use action approval，不能隐式借用本测试的 inactive 模式。
13. `.ai/tasks/*/logs/` 受 `.gitignore` 排除，因此 mutation evidence/logs 明确只是本地或 CI run artifact，不宣称单靠 Git checkout 可跨机器回放。`delete` 继续属于禁止自动执行动作。每个真实外层事务都必须在当前 spec/Policy/base/subject/classification 未变时生成独立、未过期、single-use 的 task-local action file并取得用户明确 action approval；runner 不读取批准，仍采用 TASK-0013 已披露的人工 consume fallback，在外层命令启动前先把排序后的现存 task-local record ID 集合写入可提交的 `action-use-<sha>.md`，令其 `status: started` 并保守消费。结束后的只读 receipt collector 只接受对应 record root direct-child 集合差：focused 精确一项，完整 V1 精确两项；它必须对每项调用 public loader，再补记 record ID、evidence/log refs、canonical evidence SHA、五个 log SHA、五项 outcome/raw exit摘要、实际 runner/mutation-scratch-root/worktree 数、结果、retention limitation与cleanup。若集合差数量错误、loader失败或预期 TASK-0014 production-record 模式未被选择，事务必须失败且不得用 private temp seam 结果填充 receipt。receipt 是跨提交审计索引，不伪称包含被忽略的log body。11.5必须重新采集，不得把本地文件缺失隐藏为可重放成功。
14. 允许的真实事务仅有三种互不替代的精确授权实例：`focused_integration` 的 argv 固定为 `(sys.executable, "-m", "pytest", "-q", "tests/integration/test_mutation_runner_contract.py")`，预算最多一次 runner、一个系统临时 mutation scratch direct-child root、五个串行worktree和一个保留的task-local record root；`local_v1_verify` 是一次完整 `(sys.executable, "-m", "aiflow", "verify", "TASK-0014", "--actor", <frozen-actor>)`，禁止 `--check/--finalize/--ci`；`ci_v1_verify` 另行冻结完整 `--ci --ci-run-dir <validated-system-temp-run-dir> --output <descendant>` argv、actor与外部输出root。两种V1各自的当前plan由`regression_tests`与`coverage_xml`各收集一次integration test，预算最多两次runner、两个mutation scratch root、十个串行worktree和两个保留的task-local record root，成功必须获得两个不同record ID并恰好观察两次。focused、local V1、CI V1及每次重跑必须使用不同action SHA/use receipt；提前失败未用预算作废。任何argv、actor、CI目录、测试收集、spec/Policy/classification/subject或调用图变化必须重新冻结预算。
15. TASK-0014 按 `REVIEW + V1` 自举，四项 `verification_requirements` 均保持 false。原因是 11.4 只建立记录/校验能力，`targeted_mutation` 的 live V2 consumer与 survived/missing/uncovered 强制失败属于 11.5；用 V1 验证增量实现并以单独 action-approved focused transaction 证明真实 mutation evidence，不是验证降级。active Policy `2.1.0`、`src/aiflow/verification_service.py` 的 `chapter-11-pending` 投影、V2 conclusion/finalize、approval 和 Gate 均不得改变。
16. 更新 Chapter 11 实施文档、chapter state 与 overall state时，只能在当前 subject 的完整 V1 evidence、真实 focused mutation-evidence receipt（含artifact/log hashes与本地retention限制）和独立 implementation review 均通过后，把11.4标为completed、指针移到11.5，累计计数更新为64/65 tasks、343/348 steps、16/18 exits。状态投影只引用可提交receipt及其哈希摘要，不把被忽略log路径冒充跨checkout artifact；同时把11.3的最终passed V1、review、code approval、integration/close facts更新为当前审计事实。11.5、两个Chapter 11 exit checks、live V2 targeted-mutation消费和真实V2 passed继续pending。

允许修改范围固定为：

- `.ai/schemas/mutation-evidence.schema.json`
- `.ai/templates/mutation-evidence.json`
- `src/aiflow/contracts.py`
- `src/aiflow/mutation_evidence.py`
- `tests/fixtures/contracts/valid/mutation-evidence.json`
- `tests/fixtures/contracts/invalid/mutation-evidence.missing.json`
- `tests/fixtures/contracts/invalid/mutation-evidence.invalid.json`
- `tests/fixtures/contracts/invalid/mutation-evidence.extra.json`
- `tests/unit/test_contracts.py`
- `tests/unit/test_mutation_evidence.py`
- `tests/integration/test_mutation_runner_contract.py`
- `docs/implementation/chapter-11-acceptance-integration-mutation.md`
- `docs/superpowers/state/chapters/chapter-11.yaml`
- `docs/superpowers/state/overall.yaml`

## 非目标

- 不修改 `.ai/policy/**`、现有 V0/V1/V2 evidence schema/template、`verification.py`、`verification_service.py`、`evidence.py`、approval、Gate、Verifier、review、freshness、status、CLI、Hooks 或 CI 配置。
- 不把 standalone mutation-evidence artifact 嵌入 live V2 `evidence.json`，不替换 `VERIFICATION_CHAPTER11_NOT_IMPLEMENTED`、`chapter-11-pending` 或 `CHAPTER11-PENDING`，不改变 targeted_mutation check status/conclusion，也不 finalize V2。
- 不实现 11.5 的 survived/missing/uncovered consumer、V2 verify/approval/Gate 拒绝接线、replay E2E 或两个 Chapter 11 exit checks。
- 不修改 TASK-0013 runner 的 frozen dataclass/API、五个 operator、detector、argv、环境、timeout、worktree lifecycle 或 cleanup reason precedence。
- 不记录、恢复或暴露 detector 原始 stdout/stderr，不建立通用 mutation framework、自由 log sink、自由 output path、任意 manifest/command/transform/target 或用户插件。
- 不自动读取或消费 action approval，不复用 TASK-0013 action/use receipt，不执行未经当前批准的真实 worktree create/delete；不把TASK-0014本地logs/artifact当成11.5的当前输入。
- 不实现 Chapter 12/13、V3、模型路由、资源调度或任何外部服务。

## 验收条件

1. `mutation-evidence` contract、template 与四份 fixtures 可重放；未知/缺失/额外字段、非法record ID/hash/path/outcome/exit类型和空或非五项results在语义执行前拒绝；任意JSON integer/null raw exit合法但除精确0/1真值表外没有成功语义。
2. 当前固定 manifest 的五项声明、顺序、subject、spec/Policy/classification、manifest/runner hashes 与 canonical digest 全部绑定；任一漂移或篡改使 validator 失败，不回退到历史 TASK-0013 raw probe 或自然语言确认。
3. outcome 派生严格满足本规格真值表：0/1 且无任何 probe/run failure 才 killed，0/0 才 survived，其余均 unverified；run-level cleanup/main-tree failure 覆盖所有局部正常 exit facts。uncovered 列表与所有非 killed 项精确一致。
4. 每次生产记录内部生成唯一record ID和task-log direct-child目录；同一V1的两个invocation路径不同且不会覆盖。五份JSON logs位于对应record root后代，内容封闭、有界且hash匹配；绝对/逃逸/symlink/缺失/篡改log ref拒绝。runner原始stdout/stderr继续为DEVNULL，artifact不含敏感环境或绝对scratch path。
5. TASK-0014 的 focused integration transaction通过 public production entry只调用runner一次，观察五项baseline `(0,0,0,0,0)`、mutant `(1,1,1,1,1)`、全部killed、uncovered为空，并从task-local unique record root用public loader重载evidence/logs成功；runner临时root/五个worktree全部清理，主工作树受控bytes/status与registry在runner边界保持不变。TASK-0014终止或不满足唯一active/current/HEAD binding后的普通回归仅使用mocked `MutationRun`与private受控temp-root seam，真实runner/worktree调用数为零；模式选择、production binding/unique-path和两种模式的精确call count另以mocked runner验证。
6. 失败、timeout、survived、unverified、log/evidence write conflict或 partial failure均不返回成功 artifact，不被写成 passed/Gate-ready；已写失败日志不自动删除或覆盖。
7. 当前 live V2 回归继续证明 targeted_mutation为 `unverified`、reason `VERIFICATION_CHAPTER11_NOT_IMPLEMENTED`、manifest ref `chapter-11-pending`、结果 `CHAPTER11-PENDING`、conclusion failed；standalone artifact的存在不改变 finalize、code approval或Gate。
8. V0/V1、Policy 2.1.0、现有 V2 contracts/snapshot/review/approval/Gate、manifest/runner与Windows cleanup回归全部保持通过。
9. `uv run aiflow validate TASK-0014`、`uv run aiflow scope TASK-0014`、定向 tests、Ruff、format、mypy、全量 pytest、branch coverage、Python diff coverage不低于90%和`git diff --check`全部通过，并完成独立 implementation review。
10. 每个真实focused/local-V1/CI-V1 transaction均有当前且未使用的精确action approval/use receipt；TASK-0014 focused和完整V1必须选择production-record模式，focused成功实际为1 runner/1 root/5 worktrees并留下一个task-local record，完整V1成功实际为2 runner/2 roots/10 worktrees并留下两个不同task-local record ID，且零mutation worktree/root残留。receipt持久化artifact/log hashes、结果摘要和本地retention限制；预期production模式未被选择即失败，未获批准时仅运行mocked/seam tests。
11. Chapter/overall仅宣称11.4记录能力完成并修正11.3最终审计投影；11.5、两个 exit checks、live V2 mutation consumption与真实 V2 passed保持pending。

## 禁止动作

- 禁止 push、merge、deploy、package publish、凭据导出、付费外部调用，以及未经单独授权的 task close。
- 禁止未经当前 single-use action approval 创建或删除真实 mutation worktree；禁止跨事务复用、超预算、删除 repository/workspace/user root或未验证路径。
- 禁止修改、stash、reset、checkout、clean、删除或自动恢复主工作树业务文件；禁止在主工作树应用 mutant。
- 禁止把 raw mutant exit `1` 在缺少完整绑定、log/digest验证或存在 run-level failure时表述为 killed；禁止把 survived/unverified/missing表述为通过。
- 禁止通过 standalone artifact改变 live V2、approval或Gate结论，或提前关闭11.5/Chapter exit checks。
- 禁止扩大 allowed scope、改变 active Policy/route/V或引入新权限而不升级、重新分类、冻结、独立设计审核和批准。

## 错误行为

1. task/spec/Policy/classification/base/subject陈旧或不匹配：`MUTATION_EVIDENCE_BINDING_STALE`；subject/Git解析失败：`MUTATION_EVIDENCE_SUBJECT_INVALID`。
2. run directory、evidence/log ref词法无效或解析逃逸：`MUTATION_EVIDENCE_PATH_INVALID` / `MUTATION_EVIDENCE_PATH_ESCAPE`。
3. manifest/runner identity、五项声明/顺序、probe数量/ID漂移：`MUTATION_EVIDENCE_INPUT_MISMATCH`；runner preflight错误在任何 artifact构造前原样透传。
4. record ID/UTC/nonce生成失败或三次目录碰撞：`MUTATION_EVIDENCE_ID_FAILED` / `MUTATION_EVIDENCE_IMMUTABLE_CONFLICT`；不得运行runner或复用已有record。
5. outcome、uncovered集合、canonical digest或结构化log内容不一致：`MUTATION_EVIDENCE_SEMANTICS_INVALID` / `MUTATION_EVIDENCE_DIGEST_INVALID` / `MUTATION_EVIDENCE_LOG_INVALID`。
6. log/evidence I/O失败或已有内容冲突：`MUTATION_EVIDENCE_WRITE_FAILED` / `MUTATION_EVIDENCE_IMMUTABLE_CONFLICT`；不得覆盖、伪造成功或广泛清理。
7. schema错误继续使用`CONTRACT_VALIDATION_FAILED`并保留稳定 JSON Pointer；同一输入按上述前置顺序只报告最先命中的语义类别。

## 回滚

所有持久业务变更仅为新 mutation-evidence schema/template/service、测试和 Chapter 11 文档/状态投影。回滚通过后续反向提交移除这些新文件与 contract 注册、恢复被扩展测试，并把11.4恢复pending、指针移回11.4、累计计数恢复63/65 tasks与338/348 steps；不得修改或回退 TASK-0013 runner/merge ledger、历史 evidence/approvals/actions。运行期日志作为 task-local受控输出保留或由另行批准的精确清理处理；回滚不授权 delete、push、merge、deploy或task close。
