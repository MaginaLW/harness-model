# Review Package

## 审核目标

确认 TASK-0020 在 current subject `794e4fc5831a7221e2b1d3c8f0ef7b53a428df0d` 上完成
Chapter 12.4 的结构化 pre-command refusal/audit adapter：只对 active Policy 禁止自动执行的
规范 action 构造当前 task/base/subject/Policy 绑定的 `hook_pre_command` /
`high_risk_command` immutable observation，并恰一次委派 Chapter 12.2 的公开
`apply_observation` service。确认 Hook 不执行命令、不消费 approval、不直接写 ledger/state、
不复制 Policy/decision 表，自动允许路径无 observation 副作用；同时确认状态投影只完成 12.4，
并且手动 push 事件的恢复时序未被追溯改写。

## 背景

任务 base 为 `addaa8d8f46b5dc41593b1f3ad1ea15211fb38b2`，恢复后的确定性分类为
`REVIEW / V1`。current classification input SHA-256 为
`b09c5b50bbd0020636ecc833ada5e17aaa3e0cb1018c01bb60017535483fffe0`，冻结规格
SHA-256 为 `a50f387c9ada201e791f7506cd780ccdf9ad229dd25a0cd3bc2bcfdc16037315`，active
Policy SHA-256 为
`f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`。

初始设计审核 `REV-0028` 通过后，实现形成 H1
`3c05534c5ec23c4bbabf1ef5534a91f3014351b4`。H1 正式 V1 与独立 `REV-0029`
均通过后才投影 12.4，形成 H2/current subject。H2 随后被用户手动 push 到 `origin/main`，
发生时间早于 H2 最终实现审查、code approval 与 Gate；事件 18–28 和
`unapproved-origin-push-incident.md` 保留了这一真实顺序，没有把该 push 写成先验 readiness
或追溯性批准。

用户确认历史 push actor 后，仅本地记录 resolution，重新分类仍为 `REVIEW / V1`，规格未变；
恢复设计审核 `REV-0030` / context
`3a5fc56bbb939cdb8f967c352fc494f107bf06bb36bb7edd16043893cee0f9bb` 为 APPROVE、
findings 为空，用户随后按 current classification/Policy/spec/context 重新批准。恢复后的 H2
重新取得正式 V1 和独立 `REV-0031`。该恢复不授权任何新增远程动作。

## 代码地图

- `tools/hooks/pre_command.py`：保留结构化 action/target 与共享 Policy permission seam；只在
  Policy-denied path 解析显式或唯一 active task，并提交 high-risk observation。
- `tests/integration/test_tool_wrappers.py`：验证空 target 优先失败、allowed path 无 task/service
  副作用、精确 payload/actor/exactly-once、resolver 和 service failure 的 fail-closed。
- `tests/integration/test_observation_escalation.py`：在真实临时 Git/task ledger 中验证六 action、
  AUTO/ASK/REVIEW/BLOCK 全部 canonical refusal、state 不变、无 escalation、replay 幂等和
  service/audit/stale Git/binding/target failure。
- Chapter 12 实施文档、chapter state 与 overall state：只把 12.4 五步和一项 evidence 投影为
  completed；指针移至 12.5，计数更新为 69 tasks、368 steps、13 evidence items。
- `.ai/tasks/TASK-0020/`：分类、冻结规格、设计/实现审核、H1/H2 evidence、手动 push 事件、
  block resolution、重新批准和追加式 task-local 治理记录。

## 语义变更

任意 action 的空白 target 在加载 Policy 前以 `HOOK_TARGET_INVALID` fail closed。对 Policy
自动允许的 action，包括当前 Policy 未列出的非空 label，adapter 不读取 task、不解析
observation、不调用 persistence；即使提供无效或空的 `--task` 也不改变该结论，target 只作为
未解释、未执行的 opaque label。

仅对 Policy 禁止自动执行的六类规范 action，adapter 严格读取显式 task，或要求唯一未
`MERGED` task；再使用同一 Policy 返回的 normalized action 与未经修改的原始 target，构造
schema `1.0`、当前 task/base/subject/Policy、`source=hook_pre_command`、
`kind=high_risk_command` 的最小 payload。payload 经 `parse_observation` 后只调用一次
`apply_observation(..., actor="hook_pre_command")`。共享 service 成功审计后，既有 workflow
仍返回 `ACTION_PERMISSION_DENIED` / exit 2；任一 contract、task、Git、Policy、classification、
state、audit 或 persistence failure 均走非敏感 exit 1，绝不放行或执行所描述动作。

Chapter 12 当前只完成 12.1–12.4。12.5 Hook/CLI/CI parity、12.6
README/operations/recovery、`CH12-EXIT-01/02`、P2-ESC-01 与 P2-HOOK-01 仍 pending。

## 风险

- adapter 只有被调用时才生效；本任务未安装 Hook，也不宣称可拦截自由 shell、GUI、IDE、
  remote 或未集成本 wrapper 的调用，更不构成通用命令/操作系统安全沙箱。
- allowed unknown nonempty action 沿用当前 Policy seam；Hook 不增加第二份 allow/deny 表。若
  Policy 将来变化，现有 binding/evidence 必须失效并重新分类。
- 当前 Windows host 有四项既有 symlink 测试按平台条件 skip；未把真实 symlink 行为叙述为
  已覆盖。
- coverage 配置只采集 `src/aiflow`，生产 adapter 位于 `tools/`。diff-cover 的无 coverage
  information sentinel 是确定性 pass，但不代表 100% diff coverage。
- 用户手动 push 已在最终 readiness 之前发生；本地记录只能依据用户陈述归属 actor，不能独立
  证明远端操作者。该事实不能授权未来操作，也不能替代 current review、approval 或 Gate。

## 证据

- 已验证：恢复后的 H2 正式 V1 evidence 为 passed，10/10 required checks 全部通过，
  `unverified_scenarios: []`；evidence 文件字节 SHA-256 为
  `0a1b9e52ec412aa252e206d6f1b2a9d733d2da4e474a480d7e89dfde06b3b9e2`，canonical
  evidence SHA-256 为
  `acedab28d93d600252186c0f1b23cd4afda2f4ee3fc6442df1cd02f1085250f2`。
- 全量 pytest 为 1407 passed、4 skipped；四项均为既有 Windows symlink 限制。正式 coverage
  XML line rate 为 90.15%、branch rate 为 79.21%，branch-mode combined total 约 87%；
  Ruff、format、mypy、contract、scope、smoke 与 `git diff --check` 均通过。
- 相对 base 的 diff-cover 原文为 `No lines with coverage information in this diff.`；正式
  check exit 0，AI Flow 记录 deterministic pass，未将其写成 100%。
- focused Hook wrapper 为 24 passed，真实临时 ledger integration 为 28 passed，合计 52；
  扩大的 observation/decision/service/Policy/workflow/state focused 回归为 555 passed。
- implementation review context SHA-256 为
  `b2e697a4a2bb98a159056d6351367affb901ddb91aa2649617e99caf96e31549`，绑定 current
  subject、恢复 classification、evidence、spec、Policy 与完整 base-to-subject diff；独立
  `REV-0031` 为 APPROVE 且 findings 为空。reviewer 还单独核对了 context diff summary 未包含的
  task-local recovery sidecars 和事件 18–28。
- 当前 `aiflow validate TASK-0020` 通过；HEAD、subject 与本地 `origin/main` 均为 H2。未提交
  变化只位于 `.ai/tasks/TASK-0020/**` 的恢复、evidence、review/package 治理文件。
- 未验证：12.5–12.6、Hook/CLI/CI parity、真实 Hook 安装、自由 shell/GUI/IDE/remote 拦截、
  P2-ESC-01、P2-HOOK-01 和两个 Chapter 12 exit checks。
- 未执行且未授权：任何新增 push、force-push、revert、merge、deploy、delete、secret export、
  package publish、凭据访问、网络、付费或其他外部服务调用。

## 审核问题

- allowed path 是否完全不读取 task 或产生 observation，空 target 是否在 Policy 前稳定失败？
- 六类 denied action 是否只使用 Policy normalized value 和原始受限 target，精确绑定当前事实，
  并以固定 actor 恰一次委派共享 service 后仍始终拒绝？
- 实现是否没有命令执行、approval consumption、direct ledger/state、第二份 Policy/decision 表或
  frozen scope 外的业务行为？
- 六 action、四 route、replay identity 与全部 fail-closed 路径是否有 wrapper/真实 ledger 证据？
- H1 V1/REV-0029、12.4 投影、历史手动 push、BLOCK/resolution/reclassification/reapproval、恢复
  H2 V1/REV-0031 的顺序是否真实且绑定当前？
- Chapter 12 是否只完成 12.4，overall 计数/指针是否一致，并继续保留其余任务和退出检查 pending？

## 推荐结论

`APPROVE`（仅授权进入本地 code approval / Gate；不授权任何新增远程动作）
