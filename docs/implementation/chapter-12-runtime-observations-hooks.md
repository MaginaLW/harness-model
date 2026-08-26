# Chapter 12：运行期升级观测与完整 Hooks

状态：in progress（12.1–12.2 completed；12.3–12.6 pending）

Chapter 12 在 Chapter 11 的 V2 failure/evidence 结构之上增加运行期观察与 Hook 入口，
当前已完成 12.1 的 observation contract/type 输入层和 12.2 的共享确定性
decision/task-local persistence 核心。没有新增 `aiflow observe`、Hook 或 CI adapter，也没有
修改现有 CLI、Gate、Policy、evidence 或 approval 行为；运行期入口与 parity 仍由
12.3–12.5 完成。

## 12.1 已完成：版本化 observation contract

- `.ai/schemas/observation.schema.json` 注册为命名 contract `observation`，版本固定为
  `1.0`。每个事实绑定 `task_id`、`base_commit`、`subject_commit`、`policy_sha256`、
  `source`、`kind` 与一个按 kind 判别的 closed `summary`；根对象与所有 summary 都拒绝
  未知字段。
- 五类 kind 固定为 `scope_out_of_bounds`、`policy_changed`、
  `controlled_file_changed`、`high_risk_command` 和 `evidence_missing`；四类 source
  固定为 `hook_pre_commit`、`hook_pre_command`、`cli`、`ci`。这只是事实来源标签，
  不代表调用方身份已获认证。
- scope、Policy 和受控文件变化只接受非空、去重的 repository-relative 正斜杠路径；
  绝对路径、Windows drive、反斜杠、重复分隔符、`.`/`..` 段和控制字符均 fail closed。
- high-risk command 只接受 active Policy 2.1.0 的六种规范 action 和最长 255 字符的
  `target_ref`。target 禁止空白、控制字符、引号、反引号、PowerShell/cmd 变量符号、
  shell 运算符、通配符与重定向；contract 不接受 argv、脚本文本、环境、stdout 或 stderr。
- evidence missing 只记录 closed artifact 类型和 `missing` / `invalid` / `stale` /
  `not_passed` reason code；不记录 evidence 正文或日志。

## 纯解析与不可变类型

`src/aiflow/observation.py` 提供五类 kind、四类 source、六种 action、evidence artifact /
reason 枚举，以及冻结的 `Observation`、`PathsSummary`、`CommandSummary`、
`EvidenceSummary`。`parse_observation` 先走共享 contract validator，再返回 tuple-backed
不可变事实；`serialize_observation` 返回新的 JSON-compatible 对象并重新验证。两者均不
读取仓库、时间、环境、Policy 或 task ledger，不持久化事件，也不产生 decision。

## 12.2 已完成：共享 decision 与 task-local persistence

- `.ai/schemas/observation-decision.schema.json` 与冻结的 `ObservationDecision` 固定
  `record`、`escalate`、`refuse` 三种 disposition、稳定 reason/required-condition 枚举、
  当前 route/V、canonical observation digest 和恒为 `false` 的 `execution_allowed`。
  只有 `escalate` 可携带 `REVIEW`/`BLOCK` 目标；parser 除 schema 外还校验固定语义矩阵，
  拒绝降级、未知组合与手工构造的不一致对象。
- 纯 mapper 对五类 kind、四类 source、AUTO/ASK/REVIEW/BLOCK 与 V0/V1/V2 给出确定结果。
  scope 越界只从 AUTO/ASK 升至 REVIEW；Policy 变化允许 REVIEW 同路由版本失效；受控文件、
  高风险命令和缺失 evidence 均 fail closed。BLOCK 的 `record` 只表示无需再次升 route，
  从不表示允许执行。
- `observation_service` 在写入前核对 task/task-id、base、subject、repository、branch、HEAD、
  ancestry、active Policy、classification task/version/input freshness、route/V 与 task state。
  `source=ci` 在加载 task ledger 前即被 persistence adapter 拒绝，CI 只能消费纯 mapper。
- `record`/`refuse` 只通过既有 task-local append 路径写入 `observation_recorded` 或
  `observation_refused`；两者在 `NON_STATE_EVENTS` 的封闭集合中，不改变 state，也不能充当
  transition 或满足推进 precondition。`escalate` 先写同一 canonical audit，再只委派既有
  `escalate_task`。
- observation 与 decision 的 canonical payload/digest 会在重放时重新解析和计算；完全一致
  的调用复用既有事实，event type、payload 或任一 digest 的冲突在新写入前失败。若升级委派
  中断，首个 audit 保留，重试复用它并继续既有升级路径。

## 验证事实与限制

- 初始 focused contract/parser：118 passed；首轮 V1 的 diff coverage 暴露 serializer
  防御分支覆盖不足后，受控 remediation 增加三项 fail-closed 测试，focused 更新为
  121 passed。
- 首轮正式 V1 的全量 pytest：987 passed、4 skipped；四项 skip 均是当前 Windows host 无法创建
  symlink 的既有平台限制。
- 全仓 Ruff、format check 和 mypy 均通过；`git diff --check` 通过。
- 首轮正式 V1 如实记录为 9/10 required checks passed：唯一失败是 diff coverage 87%，
  低于 90% 门槛；没有生成 code approval。该失败 evidence 和 retry 事件保留在 TASK-0017
  历史中，后续 current subject 的正式 V1 evidence 才能取代 merge-readiness 结论。
- TASK-0017 的确定性分类为 `REVIEW / V1`，冻结规格 SHA-256 为
  `159b3887cc16127361724e431baccc9cba3aed1c6e72df989eaec2ede1761911`；独立设计审核
  `REV-0019` 为 APPROVE、findings 为空。最终 merge readiness 仍以当前 implementation
  subject 的正式 V1 evidence、独立实现审核、code approval 与 Gate 为准。
- 12.1 不证明 P2-ESC-01 或 P2-HOOK-01，不宣称 Hook/CLI/CI parity，也不构成通用命令
  或操作系统安全沙箱。
- TASK-0018 的分类输入为
  `5cb11bdf357857d811007fb2ee0653e82418a22bb2bd220bbcdd531932e56de3`，Policy 为
  `f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`，冻结规格为
  `2fed82a3089bf1a277449b20c911436c995fe24e35e92d90840654d6974af82e`；设计审核
  `REV-0022` / context
  `b6f22f0ac0279af011d87bc934f7f79b06e7878177bd288384ecde63117cd0ba` 为 APPROVE。
- 12.2 preflight focused 回归为 607 passed；全量分支覆盖回归为 1374 passed、4 个既有
  Windows symlink skips，总覆盖 87.31%，相对 base 的 diff coverage 为 91%；Ruff、format、
  mypy 与 `git diff --check` 均通过。
- 实施期间一个原生审查子代理未经授权调用了付费外部服务。TASK-0018 立即以
  `new_permissions` 进入 BLOCKED，事件与费用事实记录在
  `.ai/tasks/TASK-0018/paid-external-call-incident.md`；用户随后绑定当前分类/Policy 授权仅本地
  恢复。该外部结果未被采用，后续 Grok、网络及任何外部/付费服务仍被禁止。
- 12.2 不实现 Hook/CLI/CI adapter 或 parity，不完成 P2-ESC-01/P2-HOOK-01，也不构成通用
  命令/操作系统安全沙箱。最终 merge readiness 仍取决于当前 subject 的正式 V1、独立实现
  审核、code approval 与 Gate；12.3 下一步只实现编辑后范围观察 Hook。
