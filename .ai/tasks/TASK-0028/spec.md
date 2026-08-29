# Task Specification

## 目标

完成 Chapter 13.3 的真实 `REVIEW + V2` CI/Gate 闭环。先修复已由独立设计审核
`REV-0053` 证明的缺口：V2 `verify --ci` 必须在不写 task 目录、不消费 action、
不重新执行 targeted mutation 的前提下，只读重放 current local-final V2 evidence 绑定的
immutable mutation artifact；V2 Gate 必须分别验证 current local-final 的审核/批准事实和
external CI evidence 的本次执行/attestation 事实。修复通过完整 H1 V2、独立实现审核、
code approval、隔离 CI simulation 与 Gate 后，才把 13.3 五步投影为完成；13.4–13.6、
四个 Chapter 13 exit checks、Chapter 13 和 Phase 02 均保持未完成。

## 范围

1. 允许修改的业务路径精确限定为七个：
   `src/aiflow/verification_service.py`、`src/aiflow/gate.py`、
   `tests/integration/test_verify_command.py`、`tests/integration/test_gate_command.py`、
   `docs/implementation/chapter-13-review-self-hosting.md`、
   `docs/superpowers/state/chapters/chapter-13.yaml` 和
   `docs/superpowers/state/overall.yaml`。TASK-0028 的 task-local specification、review、
   approval、action、mutation、CI simulation receipt、evidence、snapshot 与日志按追加式规则
   维护；其他 task 目录只读。
2. `REV-0053 / RF-001` 是本任务初版文档-only 规格的阻断发现：当前 CI V2 固定产生
   `MUTATION_EVIDENCE_MISSING`，且 external pre-review evidence 不能独自满足 Gate 的
   local-final implementation-review 约束。该 finding 必须通过本版范围、测试与新设计审核
   显式处置，不能删除、改写或以自然语言声称已解决。
3. V2 local verification 的现有语义保持：完整 local V2 仍须取得 current subject 的
   single-use targeted-mutation action approval，record/runner/consumer 只运行一次；partial
   local check 不得借用旧 artifact 伪装完整通过。V0/V1 local/CI 行为保持兼容。
4. V2 `verify --ci` 在执行任何 check 前必须只读加载当前 task 的 `evidence.json`，并只接受
   `schema_version=2.0`、`verification_level=V2`、`mode=local`、`phase=final`、
   `conclusion=passed`、current task/base/subject/spec/Policy/classification、有效 snapshot、
   current design/implementation review、独立 Verifier 与 current context 的 source evidence。
   source 缺失、陈旧、篡改、非 final 或非 local 必须 fail closed。
5. V2 CI 的 Verifier actor 从通过上述校验的 local-final evidence 派生；workflow 不需要伪造
   新 actor。若调用者显式给出 `--actor`，只能与 source evidence 的规范化 actor 完全一致，
   否则在 runner 前拒绝。CI 输出继续记录可审计 actor/context，但不形成新 implementation review。
6. CI targeted-mutation check 必须把 current local-final evidence 交给既有 public
   `consume_targeted_mutation_evidence`，由 loader 重新校验 task/subject/spec/Policy/
   classification、canonical digest、manifest、runner source、五项结果和日志摘要。CI 不得调用
   `record_targeted_mutation_evidence`、action consume/complete、mutation runner 或任何新
   worktree collection；task 目录、ledger、approval、receipt 与 artifact 字节必须保持不变。
7. External CI evidence 仍是本次 attestation 的 `pre_implementation_review` execution artifact：
   它重新运行当前 Policy 的十四项 checks，并包含 CI snapshot、attestation head、governance-only
   结论、current design review、独立 actor/context 与只读 mutation replay；不得伪装为对新
   CI snapshot 做过 implementation review，也不得替代 local evidence 或 code approval。
8. `gate --evidence <ci-evidence>` 对 V2 必须分层计算：task-local current local-final evidence
   提供 final phase、local snapshot、design/implementation review 和 code-approval source；
   external CI evidence 提供本次 attestation、重新执行的 required checks、CI snapshot、
   verifier/context、current design review 与 mutation replay。除 `v2_final_evidence` 只来自
   local-final 外，其余 V2 checks/context/role/mutation/review 事实必须按各自适用阶段校验，
   local 和 CI 任一不当前即拒绝。External pre evidence 只需 current design review；local final
   仍必须 current design + implementation review。V1 Gate 结果不得改变。
9. Integration tests 必须覆盖：V2 CI positive、无 actor workflow、匹配/不匹配 actor、task
   零写、recorder/action/runner 零调用、existing artifact 五项 killed replay；source evidence
   missing/pre/non-local/non-passed/stale/snapshot tamper；artifact/projection/log/manifest tamper
   与 survived；Gate 的 local-final + valid CI positive，以及 local final、CI check、snapshot、
   context、design/implementation review、mutation 或 attestation 任一失效的拒绝。现有 V0/V1、
   local V2、workflow 与 Gate decision-table 回归必须继续通过。
10. H1 只修改两个 runtime 文件、两个 integration test 文件和 Chapter 13 实施说明，不修改
    两份 state 文件。形成 H1 subject 后，必须生成精确的 V2 targeted-mutation action file，
    取得用户单独的 single-use action approval，由不同于 Implementer 的 Verifier 执行完整
    14/14 V2；五项 mutant 必须全部 killed、`unverified_scenarios: []`。随后完成独立
    implementation review、finalize、code approval 与 local Gate，并保存 immutable H1 evidence。
11. H1 code-approval attestation 形成后，必须生成第二个精确 action file，单独批准一个
    OS-temp 本地 worktree 和一个 OS-temp CI run directory 的创建与清理。该 action 只允许把
    worktree 固定到 H1 attestation、使用该 checkout 的 `src/` 运行 `verify TASK-0028 --ci`、
    使用输出运行只读 Gate、生成脱敏 task-local receipt，再清理两个已解析且确认属于 OS temp
    的精确目标；不接受自由 argv、ref、environment、目录或网络。
12. H1 CI simulation 必须返回十四项 checks 全 passed、五项 mutant 按 manifest 顺序 killed、
    external CI evidence current、Gate `passed: true` 且无 reason code；源工作树、task 目录和
    Git refs 不变。Receipt 只记录 task/subject/attestation、命令 schema、稳定摘要、Gate JSON、
    零写/清理结论和限制，不写机器名、本机用户名、绝对路径、完整日志或凭据。
13. 只有 H1 final V2、独立实现审核、code approval/local Gate 和 CI simulation/Gate 均通过后，
    H2 才修改两份 state：13.3 `completed`、`completed_steps: [1,2,3,4,5]`，13.4 仍 pending；
    增加绑定 TASK-0028 H1 closure 的 chapter evidence；四个 exits、Chapter 13 与 Phase 02 保持
    未完成。Overall totals 保持 13 chapters、77 tasks、408 steps、24 exits；completed 更新为
    12/74/393/20，evidence items 更新为 18，current task 指向 `13.4`，只追加一条 13.3 完成事件。
14. H2 state 投影改变 subject 后，H1 action/evidence/review/CI receipt 只作为投影时序前提，
    不能充当 H2 merge readiness。H2 必须生成第三个、绑定新 subject 的 single-use V2 action，
    重新完成完整 V2、独立 implementation review、finalize、code approval 与只读 local Gate；
    不要求再次执行 CI simulation，也不自动 close/merge/push。

## 非目标

1. 不修改 evidence schema、`src/aiflow/evidence.py`、mutation consumer/runner、Policy、manifest、
   templates、workflow、Hooks、README、CHANGELOG、operations 文档、Chapter 12 或 TASK-0025。
   若证明最小修复必须触及这些路径，先停止、升级、重新分类/冻结/审核/批准。
2. 不实现 13.4 的 same/empty actor、survived mutant、scope overrun、stale review 专项 E2E；
   不建立 13.5 验收矩阵；不执行 13.6 发布文档和阶段三输入；不完成任一 Chapter 13 exit。
3. 不让 CI 重新采集 mutation，不把 CI evidence 用于 code approval，不把 external pre evidence
   强制标为 final，不为 CI snapshot 伪造 implementation review，不复用其他 task/version action。
4. 不调用远程 CI、网络、外部模型或付费服务；不 push、merge、deploy、publish、访问凭据、
   安装 Hook或执行 observation 所描述动作。
5. 不实现 V3、安全扫描、故障注入、真实模型路由、资源调度、自由 shell 解析、通用命令拦截
   或操作系统沙箱。

## 验收条件

1. `REV-0053 / RF-001` 有结构化处置；新 design review 对扩展后的七文件范围、local/CI 分层、
   actor derivation、zero-write 与三次 single-use action 时序给出可接受结论，之后才可 spec approve。
2. V2 CI 从 current local-final evidence 只读重放 artifact；十四项 required checks 全 passed、
   `MUT-V2-001`–`MUT-V2-005` 全 killed、Verifier 独立、context/design current、unverified 为空；
   recorder/action/runner 调用数为零，完整 task 目录逐字节不变。
3. V2 Gate 在 current local-final + valid external CI evidence 上 passed；external evidence 即使表面
   passed，也不能覆盖 missing/stale/non-final local evidence、stale code approval 或 implementation
   review。Local evidence 即使 passed，也不能覆盖 stale/tampered/failed CI execution 或 attestation。
4. External CI pre phase 不触发 `GATE_V2_EVIDENCE_NOT_FINAL`，因为 final readiness 来自 current
   local-final；但 CI 的 snapshot、checks、mutation、actor/context/design 或 attestation 任一无效，
   对应 V2/Gate 条件必须失败。Local-only Gate 语义和所有 V0/V1 路径保持不变。
5. 七个业务路径之外无业务变更；H1 不提前修改 state，H2 计数、任务状态、evidence ref、current
   pointer 与追加事件相互一致，13.4–13.6、四个 exits、Chapter/Phase 保持未完成。
6. H1/H2 各自完整 V2 均为 14/14 passed、五项 killed、独立 Verifier、`unverified_scenarios: []`，
   各自 implementation review/final evidence/code approval/Gate 均绑定对应 current subject；任何
   action 只消费一次且失败/中断后不自动重跑。
7. H1 隔离 CI simulation 的 external evidence 和 Gate 均通过；临时 worktree/run directory 仅按
   action 精确目标清理，源仓库和 refs 不变，receipt 脱敏且可由摘要复核。
8. Focused integration、Ruff、format、mypy、全量 pytest、coverage/diff-cover、AI Flow validate/
   scope、`git diff --check` 与独立审核全部通过；所有未验证项显式为空。
9. TASK-0028 最终只到本地 `APPROVED_FOR_MERGE`；不执行或暗示 external merge、push、deploy、
   remote CI 或其他外部动作。

## 禁止动作

禁止未经 current single-use action approval 的 targeted mutation 或临时 worktree/run-directory
创建与清理；禁止 action 目标以外的 delete；禁止 push、merge、deploy、package publish、
secret export、凭据访问、网络写入、付费调用或外部模型调用。Gate 始终只读。

## 错误行为

若 local-final evidence 缺失/陈旧/篡改/非 final，CI actor 不匹配，CI 调用 recorder/action/runner，
task 目录发生写入，artifact/projection/log/manifest 非 current，任一 mutant 非 killed，CI required
check、snapshot、context、review 或 attestation 无效，Gate 错误地让 external 覆盖 local 或反之，
业务范围越界，H1/H2 时序缺失，action 过期/已消费/目标变化，或状态/计数提前完成，必须 fail
closed、保留 13.3 pending 或重新治理；不得手写通过、复用旧批准或降低验证等级。

## 回滚

Runtime、tests、实施文档与 state 变更通过后续受治理提交反向修改；恢复旧 CI missing-sentinel/
Gate 单证据行为时必须同时恢复匹配测试和 13.3 pending 投影，不能只撤一侧造成宽松 Gate。临时
worktree/run directory 仅按获批 action 的精确目标清理。TASK-0028 的 task、spec、classification、
reviews、approvals、actions、receipts、mutation/evidence snapshots 与 events 保持追加式，不删除、
不重写；失败证据继续保留。
