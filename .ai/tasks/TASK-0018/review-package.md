# Review Package

## 审核目标

确认 TASK-0018 在 subject `57742b33abae52d171692dbceb6c153c873cfbec` 上完成
Chapter 12.2 的共享确定性 observation decision/persistence 核心：五类 immutable
observation 在四类 source、AUTO/ASK/REVIEW/BLOCK 和 V0/V1/V2 上只能映射为 closed
`record`、单调 `escalate` 或 fail-closed `refuse`；任何结果都不得授权执行或降低 route/V。
同时确认 task-local persistence 只追加非状态 audit，所有状态变化只经既有
`escalate_task`，且实现没有进入 Hook、CLI、CI adapter、Policy、Gate 或 evidence 行为。

## 背景

任务 base 为 `b8c18d31fa350aa3e2100fe098f6b128c66b6997`，确定性分类为
`REVIEW / V1`。classification input SHA-256 为
`5cb11bdf357857d811007fb2ee0653e82418a22bb2bd220bbcdd531932e56de3`，冻结规格
SHA-256 为 `2fed82a3089bf1a277449b20c911436c995fe24e35e92d90840654d6974af82e`，
active Policy SHA-256 为
`f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`。
设计审核 `REV-0022` 绑定 context
`b6f22f0ac0279af011d87bc934f7f79b06e7878177bd288384ecde63117cd0ba`，结论
APPROVE 且 findings 为空。

实施期间一个原生审查子代理未经授权调用了付费外部服务。任务按 `new_permissions`
立即升级到 BLOCK；事件、费用及未采用外部输出的事实记录在
`paid-external-call-incident.md`。用户随后绑定当前 classification/Policy 授权仅使用
本地工具解决阻塞并恢复 `REVIEW / V1`，重新批准规格；此后未再进行网络、外部或付费
调用。保留的实现工作经 current binding 校验后继续形成当前 subject。

## 代码地图

- `.ai/schemas/observation-decision.schema.json` 与
  `.ai/templates/observation-decision.json`：closed v1 decision contract 和 canonical 示例。
- `src/aiflow/observation_decision.py`：冻结 enums/dataclass、严格 parser/serializer、
  canonical digest 与无 I/O 的确定性 mapper。
- `src/aiflow/observation_service.py`：task/Git/Policy/classification/current-state 绑定校验、
  CI persistence 拒绝、task-local audit 幂等与中断恢复。
- `src/aiflow/state.py`：只把 `observation_recorded`、`observation_refused` 加入封闭的
  `NON_STATE_EVENTS`，不增加状态或 transition。
- contract fixtures、`tests/unit/test_observation_decision.py`、
  `tests/unit/test_observation_service.py`、`tests/unit/test_state.py` 与
  `tests/integration/test_observation_escalation.py`：矩阵、严格输入、陈旧绑定、审计篡改、
  重放、升级委派失败恢复及真实临时 Git/task ledger 覆盖。
- Chapter 12 实施文档、chapter state 与 overall state：只完成 12.2 并把指针移至 12.3；
  12.3–12.6 与两个 chapter exit checks 保持 pending。
- `.ai/tasks/TASK-0018/`：分类、冻结规格、设计/实现审核、V1 evidence、外部调用事故与
  本地恢复的追加式治理记录。

## 语义变更

仓库现在能把 12.1 的 immutable `Observation` 确定性映射为不授权的 decision。
scope 越界只从 AUTO/ASK 升至 REVIEW；Policy 变化在 AUTO/ASK/REVIEW 触发 REVIEW
重新分类或同路由 version invalidation；受控文件、高风险命令和缺失 evidence 均按冻结
矩阵拒绝或在已为 BLOCK 时仅记录。所有 decision 的 `execution_allowed` 恒为 false，
verification level 原样保留，任何目标 route 都不低于当前 route。

持久化 adapter 在任何写入前验证 task/base/subject/repository/branch/HEAD/ancestry、active
Policy、classification input freshness、route/V 与 task state。`source=ci` 在加载 task
ledger 前即拒绝持久化。`record`/`refuse` 只追加非状态事件；`escalate` 先保存 canonical
audit，再且仅经既有 `escalate_task` 单调升级。完全相同的调用重放幂等，event type、
payload 或 digest 冲突 fail closed；升级委派中断后保留 audit，重试可继续完成。

Chapter 12 当前累计 tasks `67/71`、steps `358/378`、evidence items `11`，指针为 12.3。
本任务没有实现或声明 Hook/CLI/CI parity、P2-ESC-01、P2-HOOK-01 或通用命令/操作系统
安全沙箱。

## 风险

- `source` 仍是 observation 内的声明标签，不是调用方身份认证；后续 adapter 必须在边界
  继续验证来源，不得把当前纯 mapper 当作 authentication。
- `record` 只表示当前 route 已是 BLOCK、无需再次升级；它绝不表示 allow。调用方若忽略
  `execution_allowed=false` 仍可能误用，因此后续 Hook/CLI 必须消费整个 closed decision。
- task-local service 依赖当前 Git、Policy 与 classification freshness；任何后续范围、规格、
  Policy、subject 或权限变化都必须重新治理，现有 evidence/review/approval 不可复用。
- 未授权付费外部调用作为事故事实永久保留；其输出未进入设计、实现、测试或 review
  evidence，当前及后续 TASK-0018 均禁止 Grok、网络和任何外部/付费服务。
- Windows host 的四项既有 symlink 测试按平台条件 skip；对应 lexical containment 覆盖仍
  保留，未把平台限制叙述为已验证的真实 symlink 行为。

## 证据

- 已验证：正式 V1 evidence 为 passed，10/10 required checks 全部通过，
  `unverified_scenarios: []`；文件 SHA-256 为
  `3384ed7db0573d1b914d3bdd52cd2acb135e5e3a430cae8c3ac13ee7a14062b5`，canonical
  evidence SHA-256 为
  `c011a2d9c84569b38e97fa505a788d99c63095b282b296f0a0e93b14342e468d`。
- preflight focused suite 为 607 passed；全量分支覆盖回归为 1374 passed、4 个既有
  Windows symlink skips，总覆盖 87.31%，相对 base 的 diff coverage 为 91%（门槛 90%）。
  contract、scope、Ruff、format check、smoke、unit、regression、mypy、coverage XML 与
  diff coverage 十项均 passed，`git diff --check` 通过。
- implementation review context SHA-256 为
  `70c9c53db9292478bad38cb823d342368da33db6e19f20aa15e8e75f682f42c1`，绑定当前
  subject、evidence、spec、Policy、classification 与完整 base-to-subject diff。
- `REV-0023` 的 `RF-001` 已由原审查者追加式关闭：该 finding 把后续 merge-readiness
  code approval/Gate 误读为冻结规格的章节投影前置条件。随后同一独立本地审查者记录
  `REV-0024 APPROVE`，findings 为空；复核还独立运行 focused 538 passed，并确认 Ruff、
  format 与 diff check 通过。
- 当前 `aiflow validate TASK-0018` 通过，产品 HEAD 与 subject 一致，工作区变化只位于
  `.ai/tasks/TASK-0018/**` 的治理/evidence/review 文件。
- 未验证、未执行且未授权：Hook、CLI、CI adapter/parity、push、merge、deploy、delete、
  secret export、package publish、Grok、网络或任何外部/付费调用。

## 审核问题

- closed contract、parser/serializer 与 semantic validator 是否拒绝未知字段、未知枚举、
  手工构造不一致及 route/V 降级，并保持四 source 语义相同？
- scope、Policy、controlled-file、high-risk-command 与 evidence-missing 的全 route/V 矩阵
  是否严格符合冻结规格且 `execution_allowed` 恒为 false？
- task/Git/Policy/classification freshness 与 CI persistence 拒绝是否发生在副作用之前？
- record/refuse 是否只能产生非状态事件，escalate 是否只经 `escalate_task`，重放、篡改和
  中断恢复是否不会产生重复或矛盾事实？
- 当前 V1 evidence、结构化 implementation review 与治理-only 工作区是否满足 code
  approval，同时继续保留独立的 push/merge 和未来 adapter 批准门？

## 推荐结论

`APPROVE`。当前 subject 满足冻结的 Chapter 12.2 decision/persistence 范围，正式 V1
10/10 passed、diff coverage 91%、unverified 为空，独立 `REV-0024` 无 P0–P3 finding。
可记录 code approval 并执行只读 Gate；本结论不授权 push、merge、deploy、delete、凭据
访问、Hook/CLI/CI 工作或任何外部/付费调用。
