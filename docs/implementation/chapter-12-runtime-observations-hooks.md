# Chapter 12：运行期升级观测与完整 Hooks

状态：completed（12.1–12.6 与 `CH12-EXIT-01/02` passed；Chapter 13 未初始化）

Chapter 12 在 Chapter 11 的 V2 failure/evidence 结构之上增加运行期观察与 Hook 入口，
当前已完成 12.1 的 observation contract/type 输入层、12.2 的共享确定性
decision/task-local persistence 核心、12.3 的 pre-commit scope observation adapter、12.4 的
结构化 pre-command 拒绝与审计 adapter，以及 12.5 的受限 `aiflow observe` CLI/CI adapter
和支持范围内的语义 parity。12.5 没有改变 Gate、Policy、evidence、approval 或 Hook 的既有
决策；12.6 已完成恢复、操作文档与 Chapter 12 退出投影。

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

## 12.3 已完成：编辑后范围观察 Hook

- `tools/hooks/pre_commit.py` 保留既有显式 task / 唯一 active task 解析、完整 changed-path
  collector 与共享 `assess_scope` 语义。仅当 `out_of_scope` 非空时，adapter 才加载 active
  Policy，构造 schema `1.0`、当前 task/base/subject/Policy 绑定、
  `source=hook_pre_commit`、`kind=scope_out_of_bounds` 和 canonical `summary.paths`，经
  `parse_observation` 后恰一次委派公开
  `apply_observation(..., actor="hook_pre_commit")`。
- Hook 不直接写 task event/state，不导入 escalation helper，也不复刻 decision、route/V 或
  Policy 表。in-scope 检查不加载 Policy、不构造或持久化 observation。
- out-of-scope 无论共享 decision 为 `record`、`refuse` 或 `escalate`，都继续由既有 workflow
  返回 `SCOPE_EXPANDED`，主入口保持 `pre-commit denied` / exit 2；`AiflowError` 继续走既有
  非敏感 fail-closed exit 1。共享 service 的 audit-first、幂等重放和单调升级语义未在 Hook
  中复制。

## 12.3 验证事实与边界

- focused wrapper 与真实临时 task-ledger integration 合计 28 passed；包含 in-scope 无副作用、
  精确 observation/actor/exactly-once、REVIEW refusal 与重放幂等、AUTO/ASK 单调升级、BLOCK
  record 仍拒绝，以及 service/audit/stale-binding fail-closed。扩大后的 observation 相关
  focused 回归为 437 passed。
- 投影前 H1 subject `b98f16212550e9577222908421545dececb39cf8` 的正式 V1 为 10/10
  required checks passed，full pytest 为 1383 passed、4 skipped；四项 skip 均为既有 Windows
  symlink 限制，总分支覆盖为 87%。Ruff、format、mypy 与 `git diff --check` 均通过。
- 相对 base 的 diff-cover 原始输出为 `No lines with coverage information in this diff.`：当前
  coverage source 只包含 `src/aiflow`，而本次生产 adapter 位于 `tools/`。AI Flow 将该 sentinel
  确定性判为 pass；它不表示也不被记录为 100% diff coverage。
- 独立 H1 implementation review `REV-0026` / context
  `cee1d6478dd098fb14f0f12dfe4e331320af270931e3a32cb9240d273e2761e9` 为 APPROVE、
  findings 为空；该事实与 H1 正式 V1 共同满足本次完成投影的时序前提。投影后的 current
  subject 仍须重新取得正式 V1、独立实现审核、code approval 与 Gate，方可形成 merge
  readiness。
- 本条只完成 12.3 的 pre-commit scope adapter，不包含下一节的 `pre_command`。12.5
  Hook/CLI/CI parity、12.6 README/operations/recovery、`CH12-EXIT-01/02`、P2-ESC-01 和
  P2-HOOK-01 均保持 pending；未安装 Hook、未修改 index，也不宣称可拦截所有 Git 客户端、
  IDE 保存或提供通用命令/操作系统安全沙箱。

## 12.4 已完成：pre-command 拒绝与审计记录

- `tools/hooks/pre_command.py` 保留必填 `--action` / `--target` 结构化接口和既有
  Policy permission seam，并增加只供高风险绑定使用的可选 `--task`。任意 action 的空白
  target 在加载 Policy、读取 task 或构造 observation 前先以 `HOOK_TARGET_INVALID` 失败。
- Policy 自动允许的 action 保持无 observation 副作用：即使调用方提供无效 `--task`，adapter
  也不读取 task、不解析 observation、不调用 persistence service。当前 Policy 未列出的非空
  action label 继续沿用既有 auto-allow 语义，其 target 只是未解释、未执行的 opaque label。
- 仅对 active Policy 禁止自动执行的六类规范 action，adapter 严格读取显式 task，或要求恰有
  一个未 `MERGED` task；再以 Policy normalized action 和未经修改的原始 target 构造 schema
  `1.0`、当前 task/base/subject/Policy 绑定、`source=hook_pre_command`、
  `kind=high_risk_command` 的最小 observation。
- payload 经 `parse_observation` 后恰一次委派
  `apply_observation(..., actor="hook_pre_command")`。Hook 不直接写 ledger/state、不消费 action
  approval、不复制 Policy/route/decision 表，也不执行命令；共享 service 成功审计后仍固定返回
  `ACTION_PERMISSION_DENIED` / exit 2。task ambiguity、显式空 task、target contract、绑定、审计
  或 service 失败均走既有 fail-closed error path。

## 12.4 验证事实与边界

- wrapper tests 为 24 passed，真实临时 task-ledger integration 为 28 passed，合计 52 passed；
  扩大的 observation/decision/service/Policy/workflow/state focused 回归为 555 passed。
- 投影前 H1 subject `3c05534c5ec23c4bbabf1ef5534a91f3014351b4` 的正式 V1 为 10/10
  required checks passed，`unverified_scenarios` 为空；全量 pytest 为 1407 passed、4 skipped，
  四项 skip 均为既有 Windows symlink 限制。coverage.py 分支模式总覆盖显示 87%；正式 XML 的
  line-rate 为 90.15%、branch-rate 为 79.21%。Ruff、format、mypy 与 `git diff --check` 均通过。
- 相对 base 的 diff-cover 原始输出为 `No lines with coverage information in this diff.`：配置的
  coverage source 只包含 `src/aiflow`，而本次生产 adapter 位于 `tools/`。AI Flow 将该 sentinel
  确定性判为 pass；它不表示也不被记录为 100% diff coverage。
- 独立 H1 implementation review `REV-0029` / context
  `c83dd12e20e147ee31cf4c6d501dec1af9c8741d0cd551df0ad8fdf4ace62f11` 为 APPROVE、
  findings 为空；该事实与 H1 正式 V1 共同满足本次完成投影的时序前提。投影后的 current
  subject 仍须重新取得正式 V1、独立实现审核、code approval 与 Gate，方可形成 merge
  readiness。
- 本条只完成结构化 pre-command adapter。12.5 Hook/CLI/CI parity、12.6
  README/operations/recovery、`CH12-EXIT-01/02`、P2-ESC-01 和 P2-HOOK-01 均保持 pending；
  未安装 Hook，不解析自由 shell，不保证拦截 GUI、IDE、remote 或未集成本 wrapper 的调用，
  也不构成通用命令/操作系统安全沙箱。

## 12.5 已完成：受限 CLI/CI adapter 与语义 parity

- 新命令契约固定为
  `aiflow observe TASK-ID --input FILE --mode {apply,dry-run,ci} [--actor ACTOR]`。
  `TASK-ID`、本地 UTF-8 JSON object 输入和 mode 都必须显式提供；adapter 不搜索 active task，
  不从 stdin、环境、自由 shell、argv 或网络接收事实。重复 key、未知字段、非 object、读取失败
  和 observation contract 错误均 fail closed。
- mode/source/actor 是封闭组合：`apply` 只接受 `source=cli` 且要求非空 actor；
  `dry-run` 只接受 `source=cli` 且禁止 actor；`ci` 只接受 `source=ci` 且禁止 actor。
  adapter 不伪装 `hook_pre_commit` 或 `hook_pre_command` source。
- `evaluate_observation` 公开复用 task identity/state、base/subject、repository/branch/HEAD/
  ancestry、active Policy、current classification input 和 route/V 的完整绑定校验，再委派既有
  deterministic mapper；该入口不写 task、event、state、approval 或 evidence。
  `apply_observation` 在任何 ledger 读取前继续拒绝 CI，随后复用同一 evaluator，并保留既有
  task-local audit、幂等重放和只经 `escalate_task` 的单调升级。
- `apply` 只委派 persistence service；`dry-run` 与 `ci` 只委派只读 evaluator。成功解析
  后 stdout 只含协议版本、task、mode、ledger effect、canonical decision 和 apply-only event
  reference，不回显 observation、summary、path、target 或 actor。所有有效 observation 因
  `execution_allowed=false` 固定 exit 2；无效输入或状态 exit 1，不存在 observation allow
  的 exit 0。
- parity 只比较 decision 的 schema/disposition/reason/current route/current V/
  `execution_allowed`/required conditions/target route。canonical observation digest 正确包含
  source，因此 Hook、CLI 与 CI digest 可以且应不同；mode、ledger effect、event metadata、
  JSON 字节和用户可见文案也不属于语义 parity。

## 12.5 验证事实与边界

- core/adapter matrix 覆盖五类 observation、AUTO/ASK/REVIEW/BLOCK 与 V0/V1/V2；真实临时仓
  parity 覆盖当前实际支持的 pre-commit `scope_out_of_bounds`、pre-command 六类 Policy
  禁止 action、CLI apply/dry-run 与 detached CI dry-run。其余三类 observation 只证明 core、
  CLI 和 CI 语义，不声称现有 Hook 能产生。
- dry-run/CI 的完整 task 目录逐字节 hash 保持不变；测试同时验证 mutation helper 未被调用。
  apply replay 复用 audit identity；in-scope edit 保持 allow 且无 observation。focused
  remediation suite 为 99 passed。
- 投影前 H1 subject `f977b977dd47482e77bbc2067c9e1a41de470f41` 的正式 V1 首次为
  10/10 required checks passed、全量 1507 passed/4 skipped、diff coverage 94%；独立审核
  `REV-0033` 唯一提出 CLI help 契约不精确。remediation subject
  `741790f14ccdc79748a1c83a83536c88fd6095bd` 修复 help 与精确断言后重新取得正式 V1：
  10/10 required checks passed、`unverified_scenarios` 为空、全量 1507 passed/4 skipped、
  diff coverage 94%（110 changed executable lines，6 missing；门槛 90%）。Ruff、format、
  mypy、validate、scope 与 smoke 均通过。
- `REV-0033-r0002` 如实保留 RF-001 的解决历史；独立投影前审核 `REV-0034` / context
  `f50ae437af089d6853974ad9d01ba4ddc9330013a00b4d4d37c09d012e6e088f` 对 remediation
  subject APPROVE、findings 为空。投影后的 final subject
  `893ce6bc7f31a20a964776bbbc2b7e5a2c280d90` 已重新取得正式 V1：10/10 required checks
  passed、`unverified_scenarios` 为空、全量 1507 passed/4 skipped、diff coverage 94%；独立
  `REV-0035` / context
  `f424e758b3519848b9d0ea68ddf07df81ad9c631bd20869d1aff7085d1538b0b` 批准该 current
  subject，随后生成绑定 evidence
  `9054a208781ba61ff65cd03b30fee6e58168a8865c49ee7ebc0e4dc4e723fd58` 的 code approval。
- TASK-0022 的 external merge 已由 event 25 记录，目标仍是上述 final subject；只追加
  merge-record 的治理提交为 `d51721b92694d6684e4d3fd14079a18b321a449c`。这组事实只证明
  TASK-0022 与 12.5 已完成，不能复用于其他 task、subject、spec、Policy 或 classification。
- 上述验证运行在当前 Windows host；4 项 skip 是既有 symlink 平台限制。临时仓和 wrapper
  entrypoint 测试不证明 Linux/macOS live Hook 安装或全部 host 行为。Git Hook 无法拦截未安装
  Hook 的客户端、IDE save、GUI/remote Git 或绕过 wrapper 的调用。
- pre-command 只接受结构化 canonical action/target，不能安全解释 PowerShell、cmd、bash、
  alias、pipe、redirection、quote、wildcard、variable/command expansion 或任意自由 shell。
  本系统不是通用命令执行拦截器或操作系统安全沙箱。
- 本条历史上只完成 12.5 的五步投影；12.6 的文档、P2 支持输入与 Chapter 12 退出证据见下节，
  不反向扩大 TASK-0022 的技术证明范围。

## 12.6 已完成：恢复、操作文档与章节退出

- 12.6 以 README、Hooks、Quickstart、Recovery 和本实施记录为正文范围，校正
  Chapter 11、12.1–12.5 与 `aiflow observe` 的当前事实，并提供不绕过 ledger、Policy、
  review、approval 或 Gate 的 fail-closed 恢复路径。
- 操作文档只描述当前支持的两个 Hook 事实与受限 CLI/CI adapter；decision semantic parity
  不扩展为 source-sensitive digest、mode、ledger effect、event metadata 或 JSON bytes 相同，
  也不把 Windows wrapper 测试和四个既有 symlink skips 扩展为 Linux/macOS live Hook 证据。
- 投影前 H1 subject `965e7e92eb8fa694659cf69d89b9325cc26470d9` 的正式 V1 evidence
  `bb2ce3153c31d3acefd89b999dca62394b59f5e2bd8f207809bc5cf3d458e1c6` 为 10/10
  required checks passed、`unverified_scenarios` 为空、全量 1507 passed/4 个既有 Windows
  symlink skips。首次 run 因补充条目占用受控 `REC-09` 标题而保留 1 failed/1506 passed/4
  skipped；仅标题 remediation 的精准回归通过后，current subject 才取得上述正式 V1。
- 独立 H1 implementation review `REV-0037` / context
  `22f2de7b232cda6468afbc5d363f489b3419da482424076c81d8c2805fd048a3` 为 APPROVE、
  findings 为空。P2-ESC-01 只以共享 observation-to-escalation/refusal integration 为输入；
  P2-HOOK-01 只以两类实际 Hook facts 与受限 CLI/CI 的 decision semantic parity 及上述限制为
  输入。在这些边界内，12.6 五步、`CH12-EXIT-01/02` 与 Chapter 12 completion 已投影完成。
- 本 H2 投影改变了 subject；TASK-0023 仍须对投影后 current subject 重新取得正式 V1、独立
  implementation review、code approval 与 Gate，方可形成 merge readiness。Chapter 13 未初始化，
  Phase 02 仍 in progress。
