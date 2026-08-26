# Chapter 12：运行期升级观测与完整 Hooks

状态：in progress（12.1 completed；12.2–12.6 pending）

Chapter 12 在 Chapter 11 的 V2 failure/evidence 结构之上增加运行期观察与 Hook 入口，
但决定仍必须由后续共享核心和 active Policy 产生。当前只完成 12.1 的 observation
contract 与纯类型层；没有新增命令、写入 observation ledger、改变 task state、执行升级或
拒绝，也没有修改现有 Hook、CLI、CI、Gate、Policy、evidence 或 approval 行为。

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
  或操作系统安全沙箱。12.2 的下一步是让共享核心在不复制 Policy 表、不降低 route/V 的
  前提下，把这些事实确定性映射为 record/escalate/refuse 并定义持久化边界。
