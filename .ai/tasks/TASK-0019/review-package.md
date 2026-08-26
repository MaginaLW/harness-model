# Review Package

## 审核目标

确认 TASK-0019 在 subject `b8c25d0e9dec18baf9df5a03dcc390d28689c114` 上完成
Chapter 12.3 的 scope-only pre-commit observation adapter：只在共享 scope assessment
发现越界时，构造绑定当前 task/base/subject/Policy 的
`hook_pre_commit` / `scope_out_of_bounds` immutable observation，并恰一次委派 Chapter
12.2 的公开 `apply_observation` service。确认 Hook 不复制 Policy/route/V 表、不直接写
ledger/state、不放行任何 observation disposition；同时确认状态投影只完成 12.3。

## 背景

任务 base 为 `99c550e40448a214a98688bb3ad9615985a2838b`，确定性分类为
`REVIEW / V1`。classification input SHA-256 为
`dc0dc067c30ca339c6f7cb61d684c750c7ea02debef2eb0e151edc39893b0f47`，冻结规格
SHA-256 为 `6d402281787e3cd978e8b1480485f7e716fd1a3445f741880d14249b6f4d35cf`，
active Policy SHA-256 为
`f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`。
设计审核 `REV-0025` / context
`6856a4708ef33cb877af149b95125968c06ac1f5a47366196937be5bd41f78b4` 为
APPROVE、findings 为空，用户随后按上述精确绑定批准进入实现。

实现先形成 H1 `b98f16212550e9577222908421545dececb39cf8`。H1 正式 V1 与独立
`REV-0026` 均通过后，才按冻结规格投影 12.3，并形成当前 H2。H2 随后重新取得正式 V1
和独立 `REV-0027`，没有把 H1 evidence/review 冒充为 current merge readiness。整个任务
只使用本地工具；没有 Grok、网络、外部或付费调用，也没有 push、merge 或 deploy。

## 代码地图

- `tools/hooks/pre_commit.py`：保留显式/唯一 active task 解析、完整 changed-path collector 与
  共享 scope assessment；只在 `out_of_scope` 非空时构造并提交 observation。
- `tests/integration/test_tool_wrappers.py`：验证 in-scope 无 Policy/service 副作用、精确 payload、
  固定 actor、exactly-once 委派及 service failure 的 exit 1 fail-closed。
- `tests/integration/test_observation_escalation.py`：在真实临时 Git/task ledger 中验证 REVIEW
  refusal 与幂等重放、AUTO/ASK 单调升级、BLOCK record 仍拒绝，以及 service/audit/陈旧绑定
  失败绝不放行。
- Chapter 12 实施文档、chapter state 与 overall state：只把 12.3 五步及一项 evidence
  投影为 completed；指针移至 12.4，计数更新为 68 tasks、363 steps、12 evidence items。
- `.ai/tasks/TASK-0019/`：分类、冻结规格、设计/实现审核、H1/H2 V1 evidence 与追加式 task-local
  治理记录。

## 语义变更

pre-commit 仍由既有 resolver 确定 task，并由共享 collector 收集 base-to-subject、
subject-to-HEAD attestation 及 tracked/untracked/deleted/renamed worktree 路径。共享
`assess_scope` 产生 canonical、排序去重的越界路径；仅当该 tuple 非空时，adapter 加载 active
Policy，构造 schema `1.0`、当前 task/base/subject/Policy、`source=hook_pre_commit`、
`kind=scope_out_of_bounds` 和最小 `summary.paths`，经 `parse_observation` 后调用一次
`apply_observation(..., actor="hook_pre_commit")`。

in-scope 路径不加载 Policy、不构造或持久化 observation。out-of-scope 无论共享 service
返回 `record`、`refuse` 或 `escalate`，既有 workflow 都继续返回 `SCOPE_EXPANDED`，主入口
保持 denied / exit 2；service、audit、Policy、classification 或 binding 的 `AiflowError`
继续走非敏感 exit 1。Hook 没有直接 event/state/escalation seam，也没有新增 CLI 参数或
第二份决策表。

Chapter 12 当前只完成 12.1–12.3。12.4 `pre_command`、12.5 CLI/CI adapter/parity、12.6
README/operations/recovery、`CH12-EXIT-01/02`、P2-ESC-01 与 P2-HOOK-01 仍 pending。

## 风险

- Git Hook 只有在正确安装并由对应 Git 客户端调用时生效；本任务未安装 Hook，也不宣称可
  拦截 IDE 保存、GUI/remote Git 或提供通用操作系统安全沙箱。
- `record` 只表示共享 core 无需再升级 route，绝不表示 allow；本 adapter 通过独立 workflow
  deny 保持这一边界，后续 adapter 仍必须同样 fail closed。
- adapter 依赖当前 task/Git/Policy/classification freshness；任何 subject、范围、规格、Policy
  或权限变化都会使现有 evidence/review/approval 失效并要求重新治理。
- 当前 Windows host 有四项既有 symlink 测试按平台条件 skip；未把真实 symlink 行为叙述为
  已覆盖。
- coverage 配置只采集 `src/aiflow`，本次生产 adapter 位于 `tools/`。diff-cover 因此报告无
  coverage information；该 sentinel 由 AI Flow 确定性判为 pass，但不代表 100% diff coverage。

## 证据

- 已验证：H2 正式 V1 evidence 为 passed，10/10 required checks 全部通过，
  `unverified_scenarios: []`；evidence 文件 SHA-256 为
  `b18b24acd0a79b50b5dd4d6e4b63243e69b95ed60c706fc158f996096e53f93f`，canonical
  evidence SHA-256 为
  `817542389eb014c4dc303eaea62396a818cefd521ad9bf1080a2719c32733dad`。
- H2 全量 pytest 为 1383 passed、4 skipped；四项均为既有 Windows symlink 限制。正式
  coverage XML 的 line rate 为 90.12%、branch rate 为 79.12%，branch-mode combined total
  约 87%；Ruff、format、mypy、contract、scope、smoke 与 `git diff --check` 均通过。
- 相对 base 的 diff-cover 原文为 `No lines with coverage information in this diff.`；正式
  check exit 0，AI Flow 记录 deterministic pass，未将其写成 100%。
- focused Hook wrapper + real ledger 为 28 passed；扩大的 observation 相关 focused 回归为
  437 passed。第二路 H2 投影审计另行重跑 focused 28 passed，并核对事件 ID、计数增量和
  pending 边界。
- implementation review context SHA-256 为
  `75b3492cbe755b8c5f0e2cd3329dff01b1a66b9b65c887bfd762fb747e245296`，绑定 H2
  subject、evidence、spec、Policy、classification 与完整 base-to-subject diff；独立
  `REV-0027` 为 APPROVE 且 findings 为空。
- 当前 `aiflow validate TASK-0019` 通过；HEAD 与 subject 一致，未提交变化只位于
  `.ai/tasks/TASK-0019/**` 的 H2 evidence/review/package 治理文件。
- 未验证、未执行且未授权：12.4–12.6、pre-command、CLI/CI adapter/parity、真实 Hook 安装、
  push、merge、deploy、delete、secret export、package publish、Grok、网络或任何外部/付费调用。

## 审核问题

- Hook 是否只在 shared scope assessment 越界时构造精确 task/base/subject/Policy 绑定的
  immutable observation，并使用固定 actor 恰一次委派共享 service？
- in-scope 是否无 observation 副作用，所有 out-of-scope disposition 是否仍被拒绝，任一
  service/audit/binding failure 是否保持 exit 1 fail closed？
- 实现是否没有复制 Policy/route/V 表、直接写 ledger/state、增加新 CLI/CI/pre-command
  行为或扩大 frozen allowed scope？
- H1 V1/REV-0026、12.3 投影、H2 V1/REV-0027 的顺序与绑定是否当前且可审计？
- Chapter 12 是否只完成 12.3，overall 计数/指针是否一致，并继续保留 12.4–12.6 与两个 exit
  checks pending？

## 推荐结论

`APPROVE`
