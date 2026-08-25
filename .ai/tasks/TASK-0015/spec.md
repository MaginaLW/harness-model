# Task Specification

## 目标

完成 Chapter 11.5：让真实 V2 验证在当前 TASK-0015 的版本边界内采集并消费 targeted-mutation evidence；只有权威 manifest 的五项 mutant 均为 `killed`、记录完整且可重放时该检查才通过。任一 `survived`、`unverified`、missing、重复、未知、陈旧绑定、日志/摘要篡改或执行失败都必须令 V2 evidence 失败，并由 Gate 保持拒绝。

## 范围

1. 复用 `record_targeted_mutation_evidence` 与 `load_targeted_mutation_evidence`，但必须在 TASK-0015 当前 `subject_commit`、冻结规格、Policy 和 classification 下生成新记录；不得读取或复制 TASK-0014 的 ignored logs/evidence 充当当前证据。
2. 将 V2 `targeted_mutation` 检查从固定 `VERIFICATION_CHAPTER11_NOT_IMPLEMENTED` 占位改为受控 consumer；V0/V1 的检查集合、结论和命令保持不变。
3. consumer 只接受 loader 完整验证后的 artifact，并将 manifest 顺序的结果投影进 V2 evidence；只有五项全部 `killed` 且 `uncovered_mutation_ids` 为空时检查为 `passed`。
4. V2 evidence 的 `targeted_mutation` 摘要必须与同次检查事实一致，final evidence、approval 与 Gate 继续消费统一 evidence，不增加旁路判断或第二份 Policy 表。
   `targeted_mutation` 必须新增并要求 repository-relative `evidence_ref` 与 64 位小写 `mutation_evidence_sha256`，同时保留权威 `manifest_ref` 和 manifest 顺序的精确五项 projection。schema 继续 `additionalProperties: false`，`.ai/templates/evidence-v2.json` 必须同步为通过当前 contract 的非权威示例；pre/final snapshot 摘要必须绑定 artifact identity 与 projection。approval 和 Gate 必须调用同一个 loader-backed currentness/complete-killed consumer，不能只检查内嵌 outcome。
5. 覆盖 production collection、纯 fixture replay、missing/survived/unverified/stale/tampered/duplicate/unknown，以及 V1 不运行 mutation 的回归测试。
6. 完成 Chapter 11.5 与两个 Chapter 11 exit checks 的状态投影，只能在当前任务验证和所需审核通过后标记完成。

## 非目标

1. 不实现 Chapter 12 Hooks、Chapter 13 自举试点、V3、模型路由或资源调度。
2. 不改变固定五项 manifest、mutation operator、detector、runner worktree/cleanup 语义或既有 mutation-evidence schema；允许且必须按本规格扩展 V2 evidence schema，以绑定 immutable mutation artifact identity 与精确 projection。
3. 不把 task-local ignored evidence 描述为可跨 checkout 或机器保存；可提交 receipt 仍只是哈希索引。
4. 不自动批准、合并、推送、部署、删除临时或历史文件，也不执行付费外部调用。

## 验收条件

1. 单元与集成测试证明全 killed 时 targeted mutation 通过，任一 survived/unverified/missing/陈旧/篡改记录均以稳定 reason code 失败。
2. replay 测试证明同一 immutable artifact 得到确定性相同结论，TASK-0014 artifact 或其他 task/subject/spec/Policy/classification 绑定不能复用。
3. V1 验证不调用 mutation runner、不要求 mutation artifact，既有 V0/V1 evidence 与 Gate 行为不回归。
4. V2 evidence 中检查状态、`unverified_scenarios`、结论和 targeted-mutation results 一致；非全 killed 时 implementation review、code approval 与 Gate 不能通过。
5. focused tests、全量 pytest、Ruff、format check、mypy、覆盖率和 Git scope 检查通过。真实 runner 只允许在一次显式 production collection 事务中执行：调用图固定为 V2 verify service -> `record_targeted_mutation_evidence(repository_root, "TASK-0015", current_subject)` -> existing runner 一次 -> public loader 一次 -> V2 consumer；固定 manifest 五项，每项一次 baseline detector 与一次 mutant detector，最多创建五个 task-owned 临时 worktree，沿用 runner 既有每 probe timeout 和 cleanup，不接受自由 argv、环境、manifest、operator 或结果输入。事务开始前必须取得绑定当前 spec/Policy/base/subject/classification 和精确 action file 的 single-use action approval；批准不得授权 delete，失败残留不得自动清理或重跑，任何第二次真实 collection 需要新的 action approval。
6. Chapter 11 两个退出条件具有可重放测试和证据引用，状态汇总与章节文件一致。

## 禁止动作

禁止 push、merge、deploy、delete、secret export、package publish、付费外部调用及任何未经批准的真实 mutation worktree 执行。不得覆盖或清理既有 task-local mutation records。

## 错误行为

所有缺失、非全 killed、数量/顺序/身份不匹配、路径逃逸、摘要或日志不一致、陈旧版本绑定、runner/cleanup/main-tree 失败都必须 fail closed，保留明确 reason code 和未覆盖项；不得降级为 V1、不得以自然语言“通过”掩盖，也不得用 TASK-0014 receipt 或本地残留补齐。

## 回滚

代码和文档变更均通过后续受治理提交反向修改；历史任务记录、evidence、review 和 receipt 保持追加式审计，不删除、不重写。未完成或失败时保留 Chapter 11.5 pending 和 live V2 failed。
