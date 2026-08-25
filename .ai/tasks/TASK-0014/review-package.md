# Review Package

## 审核目标

确认 TASK-0014 在 subject `e9bb833481659ec2ed9139dbb05539e8a822314d`
上完成的 Chapter 11.4 变更满足冻结规格：把固定五项 mutation runner 的原始
probe facts 封闭地记录为绑定当前 task、base/subject、spec、Policy、classification、
manifest 与 runner 的 killed/survived/unverified evidence、受控结构化日志和明确
未覆盖项，同时不接入 live V2、approval 或 Gate。

## 背景

TASK-0013 已完成 Chapter 11.3 runner，并以
`4680a377591627d4887185b244dcbd0d43156d25` 记录 integration merge；其 close
治理后继 `3c87fc931329c903e2d22feff88a4fd4966718b6` 是本任务 base。TASK-0014
绑定 `REVIEW + V1`、Policy
`f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`、
classification input
`cebbc4df4fe06a50521d0f3246d968dcc1660343d041570d09fa4f289a38e6d0` 与冻结规格
`a38fe5af6458a3c7f495616f96243d52347a08027bf0d8acde6c668893c0e9d9`。

H1 `62df888baf2afa858ef096949ab1ade861cef7ea` 包含实现、测试及一次 focused/一次
完整 V1 的真实 production records。H2 提交了经审计的 Chapter 11.4 文档/状态
投影并同步 task subject，使 H1 evidence 与 `REV-0002` 正确成为历史。Action 002
在启动前因 selector 时序条件不可满足而被拒绝，没有记录批准或执行；修正后的
action 003 单次执行完整 H2 V1 并通过。独立 H2 implementation review `REV-0003`
绑定 context `53926676c95f5858ec2928eee3caae32afbd33780a6bfea7d63727a89828b47a`
并给出 `APPROVE`。一个 medium 投影时点歧义已由严格追加的 task-local
currentness clarification 关闭，不改变 H2 subject 或已提交历史投影。

## 代码地图

- `.ai/schemas/mutation-evidence.schema.json` 与
  `.ai/templates/mutation-evidence.json`：封闭、版本化的五项 evidence contract 与模板。
- `src/aiflow/contracts.py`、`src/aiflow/mutation_evidence.py`：contract 注册、当前绑定
  校验、不可变 record-root 预留、outcome 派生、canonical digest、日志写入及
  fail-closed public loader。
- contract fixtures、`tests/unit/test_contracts.py`、
  `tests/unit/test_mutation_evidence.py`：覆盖精确五项、有序性、killed/survived/
  unverified、日志哈希、stale binding、路径/symlink containment 与错误语义。
- `tests/integration/test_mutation_runner_contract.py`：普通运行使用 synthetic seam；仅在
  当前唯一 TASK-0014 为 `IMPLEMENTING/VERIFYING` 时选择 production，调用 public
  recorder 并证明主树、受控 hashes 和 worktree registry 不变。
- Chapter 11 implementation/state/overall：把 11.4 标为 completed、指针移到 11.5，
  同时保持 11.5、两个 exit checks 和真实 live V2 pending/failed。
- `.ai/tasks/TASK-0014/`：规格、分类、action/use receipts、current H2 V1 evidence、
  review contexts/records、投影时点澄清与本审核包；这些是 task-local 治理事实。

## 语义变更

仓库现在可以在固定 runner 成功返回后，为精确五项 Phase 02 mutation 声明建立新的
不可变 task-local record。每个结果保存 manifest 声明、baseline/mutant exit code、
timeout/duration/reason、派生 outcome 与独立 log hash；顶层 evidence 保存完整绑定、
uncovered 集合、runner/manifest hashes 和 canonical evidence hash。public loader 只
接受当前 task 下格式受控的 evidence ref，并重新校验 contract、canonical digest、
result/log 一致性、manifest 顺序、当前绑定和路径 containment。

本变更没有让 V1 强制 mutation，也没有让 live V2、approval 或 Gate 消费新 record。
ignored task-local record/log bodies 不跨 checkout 或机器承诺持久；可提交 use receipt
只是当次本地 artifact 的哈希索引。Chapter 11.5 才负责 consumer、survived/missing
replay failure 与 Gate 接线。

## 风险

- AI Flow 仍无 action-consume CLI/schema；single-use worktree delete authority 依赖
  启动前先写 use receipt 的人工审计 fallback。Action 003 已消费且不可复用。
- Windows 主机无法创建真实 symlink 的单元路径被 skip；词法/解析边界 mock tests
  保留对应逃逸覆盖。
- task-local mutation evidence/log bodies 被 `.gitignore` 排除；receipt 可审计本机
  哈希，但不能让另一个 checkout 或机器重放这些 ignored bodies。
- Windows 防病毒、索引器或外部 Git worktree 并发若破坏 cleanup/registry 不变量，
  runner 会 fail closed；任何后续残留清理仍需新的精确 action approval。
- 11.5 与 live V2 consumer 尚未实现，不能从 11.4 的 standalone records 推导真实
  live V2 passed。

## 证据

- 已验证：base `3c87fc931329c903e2d22feff88a4fd4966718b6`、subject
  `e9bb833481659ec2ed9139dbb05539e8a822314d`、冻结规格、Policy 与 classification
  input 均 current；AI Flow status 为 `WAITING_FOR_FINAL_REVIEW`，evidence 为 passed，
  scope-valid。
- 已验证：current V1 evidence 文件 SHA-256 为
  `2fab98ec7a0f05e75b2873df592e7dfbd3ded8983ba51f5b8098aeb0a19933e1`，canonical
  SHA-256 为 `d85f93d45a8453c01cd9e0b87158e38d28fa94249ecff29024fc6f947fdac240`；
  10/10 required checks 均 passed。
- 已验证：unit 为 `579 passed, 3 skipped`；regression 与 coverage collection 均为
  `871 passed, 4 skipped`；changed-line coverage 为 `92%`（`317/342`），超过 90%
  门槛；branch-aware coverage XML 已生成并通过 Policy check。
- 已验证：action 003 use receipt 文件 SHA-256 为
  `cbde31ef090966cc854b400c75434ad91b6f80173e57c6604e48e76652e927f1`；唯一外层命令
  产生两个 H2 records，canonical hashes 分别为
  `6d2816836c7cb100ea0c7bb2ce57b8b1fc70537403cfa03fa568d552a03d8228` 与
  `42d565697b6c0a91902382e743c6d87aa9d376011eeb09e739377e8799e6876a`。public loader
  复核两者均为五项 baseline `0` / mutant `1` / killed、无 reason/timeout、uncovered
  为空、main tree unchanged；2 个临时根和 10 个 worktrees 已清理，残留为 0，
  registry 前后 blob SHA-1 均为 `ca1fe61df884557b4b8ac83aa34536d868b36c42`。
- 已验证：独立 `REV-0003` 文件 SHA-256 为
  `ddce5d5c0b044e977d3d84362d6e6a018bee9827d0eae60638a79fcdd028ec72`，outcome 为
  `APPROVE`；唯一 medium finding 已由 SHA-256
  `48c504d543be914ac205ecdf0d357404f93a7ad5e3694e030f7ea61c186ab363` 的 task-local
  clarification 标记 resolved。工作树只有 `.ai/tasks/TASK-0014/` 治理变化。
- 未验证且未实现：Chapter 11.5 consumer/replay enforcement、两个 Chapter 11 exit
  checks、真实 live V2 passed，以及 push、merge、deploy、task close、凭据/付费调用、
  package publish 和任何新的 delete/runner transaction。

## 审核问题

- evidence contract、recorder 与 public loader 是否始终锁定精确五项、当前绑定、
  canonical digest、日志哈希、顺序与路径 containment？
- killed/survived/unverified 与 uncovered 语义是否只从受控 raw probe facts 派生，
  并在任何不完整、stale、越界或 hash mismatch 时 fail closed？
- production/synthetic split 是否保证普通测试不会创建 worktree，而精确批准的 H2
  V1 两轮 collection 各只产生一个真实 record？
- Chapter 11 投影与 currentness clarification 是否准确区分 H1 历史投影、H2 当前
  verification/review 以及仍 pending 的 11.5/live V2？
- current evidence、`REV-0003` 与 governance-only worktree 是否足以进入用户
  code/document approval 门？

## 推荐结论

`APPROVE`。H2 subject 的完整 V1 evidence 与独立 structured implementation review
均 current 且通过，唯一 medium 文档时点歧义已关闭，未发现阻止当前代码/文档批准
的遗留问题。本结论不授权 push、merge、deploy、task close、任何新 runner/delete
action 或 live V2。
