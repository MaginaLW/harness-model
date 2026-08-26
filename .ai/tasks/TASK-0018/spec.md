# Task Specification

## 目标

完成 Chapter 12.2：在 12.1 的严格、不可变 `Observation` 之上建立唯一共享的
确定性 decision/persistence 核心。核心必须把每项当前绑定的事实映射为 `record`、
单调 `escalate` 或 `refuse`，输出封闭且可重放的决定；task-local adapter 只追加
观察/拒绝审计事件，所有状态变化只委派给既有 `escalate_task`。任何结果都不得降低
route 或 verification level，也不得授权继续执行被观察的高风险动作。

## 范围

1. 新增 `.ai/schemas/observation-decision.schema.json`，使用 JSON Schema 2020-12，
   根对象及嵌套对象均关闭未知字段。版本固定为 `1.0`，字段至少包含 canonical
   `observation_sha256`、`disposition`、稳定 `reason_code`、`current_route`、
   `current_verification_level`、恒为 `false` 的 `execution_allowed`、非空且去重的
   `required_conditions`，以及仅 `escalate` 可携带的 `target_route`。目标 route 只能是
   `REVIEW` 或 `BLOCK`；`record` / `refuse` 不得携带目标 route。
2. 新增冻结的 decision 类型、严格 parser/serializer 和纯函数 mapper。observation
   identity 是 `serialize_observation` 结果按 UTF-8、sorted keys、紧凑 separators 计算的
   SHA-256。mapper 只接受已解析 `Observation`、当前 route 与当前 verification level；
   不读取仓库、时间、环境、Policy 或 ledger，不修改输入，也不产生外部副作用。
3. 决定矩阵固定如下，四个 source 对同一 kind、route、V 必须得到相同结果：
   - `scope_out_of_bounds`：`AUTO` / `ASK` 单调升级到 `REVIEW`，使用既有
     `scope_expanded` escalation reason；`REVIEW` 拒绝并要求重新分类/冻结受影响规格；
     `BLOCK` 仅记录“已处于最高路由”的非许可事实。
   - `policy_changed`：`AUTO` / `ASK` 升级到 `REVIEW`；`REVIEW` 维持 `REVIEW` 的
     version invalidation，均使用既有 `policy_changed` escalation reason；`BLOCK` 仅
     记录并保持 `execution_allowed=false`，不得从通常已是 `BLOCKED` 的状态再次调用
     `escalate_task`。所有分支都要求按当前 Policy 重新分类；“维持”不是降级或批准。
   - `controlled_file_changed`：`AUTO` / `ASK` / `REVIEW` 均拒绝，要求确认受控文件、
     重新分类并使相关 approval/evidence 按 freshness 规则失效；`BLOCK` 仅记录，仍不
     允许继续。
   - `high_risk_command`：所有 route 均拒绝；required condition 必须是与当前版本绑定的
     single-use action approval。决定只能使用规范 action 和受限 `target_ref`，不能扩展为
     argv、自由 shell 或权限授予。
   - `evidence_missing`：`AUTO` / `ASK` / `REVIEW` 均拒绝，要求对应 artifact 恢复为当前且
     passed；`BLOCK` 仅记录，不能把缺失、invalid、stale 或 not-passed 解释为通过。
   `record` 只表示无需再次改变已为 `BLOCK` 的 route；`execution_allowed` 仍为 false，
   不能被调用方解释成 allow。
4. 新增 task-local application service。它必须先加载 task、当前 classification、active
   Policy 和 Git context，核对 observation 的 task/base/subject/Policy 绑定、classification
   input freshness、route/V 与受支持 task state；任一不一致均在写入前 fail closed。
   `source=ci` 只能调用纯 mapper，持久化 adapter 必须拒绝，避免修改 detached CI ledger。
5. `record` 追加 `observation_recorded`，`refuse` 追加 `observation_refused`；两者都是不改变
   `current_state` 的 task-local event，payload 只含 canonical observation、decision 和它们的
   digest。`escalate` 先追加同一 `observation_recorded`，再仅以固定、安全、由枚举和 digest
   组成的参数调用既有 `escalate_task`；不得复制 route/Policy 表或直接调用状态转换函数。
   若第二步失败，调用必须失败关闭，保留首个审计事实；相同 observation 的重试不得重复
   追加事实，并须继续完成或如实返回仍未完成的 escalation。
6. 仅在 `src/aiflow/state.py` 的封闭 `NON_STATE_EVENTS` 集合中注册
   `observation_recorded` 和 `observation_refused`，并用既有 `create_record_event` 路径验证；
   不得新增状态、transition、precondition 或让这两类事件改变 `current_state`。
7. 新增 canonical template、valid fixture 以及 extra/invalid/missing 三类固定负例；扩展
   通用 contract matrix，并新增 focused unit/integration replay tests。测试必须覆盖五类
   kind、四类 source、AUTO/ASK/REVIEW/BLOCK、V0/V1/V2、重复调用、陈旧绑定、错误状态、
   CI 持久化拒绝及 escalation 中断恢复。
8. 实现允许范围仅为 TASK-0018 `task.yaml` 中列出的 18 个精确路径。对
   `src/aiflow/escalation.py`、`src/aiflow/task_service.py` 和 Policy 只能通过既有公共行为
   读取/调用；`src/aiflow/state.py` 仅允许第 6 项的两个非状态事件注册。task-local 治理
   文件按 AI Flow 规则单独记录。
9. 仅在实现、正式验证和所需审核均绑定当前 subject 且通过后，将 12.2 的五个步骤和
   evidence 投影为 completed，并把 overall 指针移至 12.3；12.3–12.6 与
   `CH12-EXIT-01/02` 保持 pending，历史状态只追加、不重写。

## 非目标

1. 不新增 `aiflow observe`，不修改 `cli.py`、`tools/hooks/**`、GitHub Actions 或其他 CI
   adapter；不实现 12.3 edit/scope Hook、12.4 pre-command Hook、12.5 parity 或 12.6 文档。
2. 不修改 active Policy、permissions、routing/verification rules、Gate、evidence、approval、
   review 或 task/event schema；除注册第 6 项的两个非状态 event name 外，不修改状态、
   transition、precondition 或状态机行为，也不新增第二份 Hook/CLI Policy 决策表。
3. 不执行或解析 PowerShell、cmd、bash 等自由命令，不消费 argv、环境、stdout、stderr、
   credential 或 secret，不宣称通用命令/操作系统安全沙箱。
4. 不自动重分类、降级 route/V、批准、解除拒绝、恢复 evidence 或消费 action approval；
   required condition 只是关闭的恢复要求，不是满足证明。
5. 不实现 Chapter 13、V3、真实模型路由、资源调度、安全扫描或外部服务。

## 验收条件

1. contract/template/fixture 与 parser tests 证明 decision 对象关闭未知字段，条件分支严格，
   canonical parse/serialize round-trip 稳定，digest 可重放且错误不回显潜在敏感原值。
2. 参数化单元测试证明五 kind 的决定矩阵在四 source 和所有 route/V 上确定；任何
   `target_route` 都不低于当前 route，verification level 原样保持，所有结果的
   `execution_allowed` 均为 false。
3. integration tests 证明 record/refuse 只追加非状态事件，escalate 仅通过现有
   `escalate_task` 产生状态事件；相同 observation 幂等，写入/升级中断时不报告允许，
   重试可恢复且不会产生矛盾决定。
4. state-core tests 证明两种新 event name 只能经 `create_record_event` 保持同一 state，
   不能作为 transition event 或满足任何推进 precondition；既有事件集合与 transition
   矩阵保持原结论。
5. 缺失/陈旧 task、base、subject、Policy 或 classification 绑定，未知 decision/reason/
   condition，非法 route/V、不支持 task state、CI 写入、篡改 event/digest 和 payload
   不一致均以稳定 reason code 在副作用前失败；已记录但未完成的 escalation 只能重试，
   不得静默视为完成。
6. 现有 observation contract/parser、generic escalation、task ledger、V0/V1/V2 evidence、
   approval、Gate 和 CLI 测试保持原结论。Hook/CLI/CI parity 不在本任务宣称通过。
7. `aiflow validate TASK-0018`、`aiflow scope TASK-0018`、focused tests、全量 pytest、Ruff、
   format check、mypy、分支覆盖、相对 base 的 diff coverage（至少 90%）和
   `git diff --check` 全部通过；正式验证等级以当前 Policy 的确定性分类为准。
8. Chapter 12 状态只完成 12.2 的五个步骤；12.3–12.6 和两个 chapter exit checks
   保持 pending，overall 计数与 12.3 指针一致，不提前声明 P2-ESC-01 或 P2-HOOK-01 完成。

## 禁止动作

禁止 push、merge、deploy、delete、secret export、package publish、付费外部调用、凭据访问
及任何真实高风险命令执行。本任务只在临时测试仓库中构造受限 observation；任何未来
高风险动作必须另获与当时 task/spec/Policy/subject/action file 绑定的单次批准。

## 错误行为

任何未知字段/枚举、非规范 observation/decision、陈旧或交叉 task 绑定、route/V 降低、
`record` 被解释为允许、未授权高风险动作、缺 evidence 被解释为通过、CI ledger 写入、
重复矛盾事实、自由 shell/敏感载荷或绕过 `escalate_task` 的状态变化都必须 fail closed。
若实现需要修改 Policy、Hook、CLI、CI、Gate、evidence、approval、超出范围第 6 项的
state machine 内容或当前允许范围外文件，必须停止并以 `policy_changed`、
`scope_expanded`、`spec_changed` 或对应原因重新治理，不得自行扩展或降低 route/V。

## 回滚

代码、schema、template、fixture、测试和状态投影均通过后续受治理提交反向修改；
TASK-0018 的 task、classification、spec、review、approval、evidence 与 event 历史保持
追加式审计，不删除、不重写。未完成或验证失败时 12.2 保持 pending，不得以叙述文档或
未完成的 observation/escalation 记录替代通过证据。
