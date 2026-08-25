# Task Specification

## 目标

在不改动运行时代码、Policy、mutation manifest 或 TASK-0015 历史的前提下，把已合并的
TASK-0015 权威事实投影为 Chapter 11.5 与 Chapter 11 完成状态，并按阶段二实施目录初始化
Chapter 12/12.1，使章节文件、总体计数、当前指针、README 和 Chapter 11 实施文档一致。

## 范围

1. 更新 `docs/superpowers/state/chapters/chapter-11.yaml`：11.5、两个退出检查、章节状态、
   证据与限制文字。
2. 新建 `docs/superpowers/state/chapters/chapter-12.yaml`：只登记阶段二实施目录中的六项任务、
   两个退出检查及 Chapter 11 完成依赖，全部保持 pending。
3. 更新 `docs/superpowers/state/overall.yaml`：Chapter 11 完成、Chapter 12 初始化、累计计数、
   当前指针、阶段二摘要及追加式历史事件。
4. 更新 `docs/implementation/chapter-11-acceptance-integration-mutation.md` 与 `README.md`，
   删除已被 TASK-0015 当前 V2/merge 事实取代的 pending 描述，同时保留本地 ignored artifact
   不跨 checkout/机器承诺持久的边界。
5. 投影只引用已提交的 TASK-0015 subject、final V2 evidence、REV-0016、code approval、
   action receipt、mutation digest、external merge commit 与 merge-record governance commit。

## 非目标

1. 不实现 Chapter 12 Hooks、观察事件或 escalation/refusal 映射；Chapter 12 仅初始化状态。
2. 不修改 `src/`、tests、active Policy、schemas、templates、mutation manifest、runner 或 Gate。
3. 不重跑 targeted mutation，不创建、清理或复用任何 mutation worktree、action 或 ignored record。
4. 不改写 TASK-0015 的 task/evidence/reviews/approvals/events/receipts 历史。
5. 不把 task-local ignored evidence/log 描述为跨 checkout、机器或未来 task 可重用。

## 验收条件

1. TASK-0015 必须仍为 `MERGED`；subject `9d48321d825a09a299bd7df0e70b716b2b598430`、
   integration commit `cc1e1bb55eabd44ef2b2e767e41637e7c36446e0` 与 merge-record governance
   commit `1342cd23302cdb918b19c2fc42aeaaaa3ee20639` 均存在且引用准确。
2. 投影核对 final V2 evidence 为 passed、14 项 required checks 全通过、unverified 为空，
   `MUT-V2-001` 至 `MUT-V2-005` 全部 killed，并记录当前 evidence/review/receipt 的文件哈希与
   canonical digest；任何引用或哈希不一致都不得标记完成。
3. Chapter 11 的 11.5 为 completed、五步完成、两个 exit checks 为 passed、blockers 为空，
   且新增一条只绑定 TASK-0015 当前事实的 chapter evidence。
4. Chapter 12 只按实施目录初始化 12.1–12.6 和两个 pending exit checks；不得提前声明 Hook 已实现。
5. overall 的章节、任务、步骤、退出检查、evidence 计数与 chapter 文件一致，并把当前指针移到
   Chapter 12.1；历史只追加、不删除。
6. README 与 Chapter 11 实施文档准确表述 Chapter 11 已完成和 live V2 当前通过，同时明确
   Phase 02 尚未完成、Chapter 12 待实施、V3/真实模型路由/资源调度仍不在当前范围。
7. `aiflow validate`、`aiflow scope`、Policy 选定的 V1 检查、YAML/引用一致性复核、
   `git diff --check`、设计审核和实现审核均通过。

## 禁止动作

禁止 push、merge、deploy、delete、secret export、package publish、付费外部调用、真实
mutation transaction，以及任何未经独立批准的范围或 Policy 变化。

## 错误行为

TASK-0015 未合并、evidence/review/approval/receipt/commit 不存在或哈希不一致、五项 mutation
非全 killed、unverified 非空、计数或指针不一致、Chapter 12 内容超出初始化范围时，必须保持
Chapter 11 pending 或升级处理；不得用自然语言“完成”掩盖缺失证据。

## 回滚

所有文档/状态修改通过后续受治理提交反向修改；TASK-0015 的追加式历史和本地 ignored artifact
保持不变。未通过最终验证或审核时保留本任务失败记录，并不得将 Chapter 11 投影为完成。
