# Task Specification

## 目标

完成 Chapter 12.4：把现有 `tools/hooks/pre_command.py` 从只返回 active Policy permission /
workflow 结果的薄检查器，扩展为只提交明确高风险命令事实的 Hook adapter。对 active Policy
禁止自动执行的规范 action，Hook 必须构造绑定当前 task、base、subject、active Policy 且
`source=hook_pre_command`、`kind=high_risk_command` 的 immutable observation，并且只委派
Chapter 12.2 的共享 `apply_observation` service 记录 canonical refusal。Hook 不得执行命令、
解析自由 shell、消费 action approval、复制 decision/Policy 表，亦不得把任何 observation
decision 解释为允许执行。

## 范围

1. 实现允许范围固定为 TASK-0020 `task.yaml` 中的六个精确业务路径：
   `tools/hooks/pre_command.py`、`tests/integration/test_tool_wrappers.py`、
   `tests/integration/test_observation_escalation.py`、Chapter 12 实施追踪文档、Chapter 12
   状态文件和 overall 状态文件。task-local 治理记录仍按 AI Flow 规则追加。
2. 保留现有必填 `--action` / `--target` 结构化接口、`check_pre_command` 的 Policy-derived
   permission seam，以及 allowed / denied / error 的 exit 0 / 2 / 1 形状；可增加可选
   `--task`。不得接受一个待解析或执行的命令字符串、argv 数组、shell 方言、环境变量、
   stdin/stdout/stderr 或 credential/secret。空白 target 在 Policy 判断前继续以既有
   `HOOK_TARGET_INVALID` 失败；非空 target 的完整 observation contract 校验只发生在
   Policy-denied high-risk path。
3. `action` 必须先只经现有 `evaluate_action_permission(load_policy_bundle(root), action)`
   规范化并决定是否禁止自动执行。active Policy 当前六类禁止自动 action 固定为 `push`、
   `merge`、`deploy`、`delete`、`secret_export` 和 `paid_external_call`；Hook 不得另写第二份
   action 清单或 permission 表。Policy 自动允许的 action（例如 `read`）保持现有 allow，且
   不解析 observation、不解析或读取 task（即使调用方提供了 `--task`）、不调用 persistence
   service，也不产生 audit。当前 Policy 未列出的非空 action label 按既有 permission seam
   归入自动允许路径，不得由 Hook 自行增加 allowlist 或把它重新分类为“未知高风险动作”；
   该路径把非空 target 当作不解释、不执行的 opaque label，不宣称其满足 high-risk contract。
4. 仅对 Policy 禁止自动执行的 action，解析当前 task。显式 `--task` 必须可严格读取；省略时
   必须恰有一个未 `MERGED` task，否则以稳定 `HOOK_TASK_AMBIGUOUS` 失败。不得从环境、Git
   分支名、最近修改目录、target 或用户文本猜测 task；该 resolver 只负责 task identity，
   不复制 Policy 或 state decision。
5. 仅对上述 Policy-denied high-risk path，以 Policy 返回的 normalized action 和原始受限 `target_ref`
   构造一个 JSON-compatible payload，再经 `parse_observation` 得到 immutable
   `Observation`。绑定字段只能来自严格 task record 与同一 active Policy bundle：版本
   `1.0`、当前 `task_id`、`base_commit`、`subject_commit`、`policy_sha256`、source
   `hook_pre_command`、kind `high_risk_command` 和最小 `summary.action/target_ref`。
   `target_ref` 必须服从现有 observation contract 的长度和安全字符约束；不得预先 strip、
   修复、展开或回显非法 target。
6. Hook 只能调用现有公开 `apply_observation(repository_root, task_id, observation,
   actor="hook_pre_command")`，并且对一次 high-risk check 恰调用一次。不得导入或调用
   `record_task_event`、`escalate_task`、transition helper、approval consumer 或内部 decision
   table；binding 校验、canonical refusal audit、幂等重放和中断恢复完全由 12.2 core 负责。
7. 任一规范 high-risk observation 在共享 service 成功处理后仍保持
   `pre-command denied` / exit 2 与既有 `ACTION_PERMISSION_DENIED` failure code。12.2 对
   high-risk command 在 AUTO/ASK/REVIEW/BLOCK 和 V0/V1/V2 上均只给出 `refuse`、
   `action_approval_required`、`execution_allowed=false`；Hook 不得把 required condition、已有
   approval 或任一路由解释为 allow，也不得执行所描述动作。
8. 任意 action 的空 target、Policy-denied path 的非法 action/target contract、task
   missing/ambiguity、缺失或陈旧
   base/subject/Policy/classification、错误 repository/branch/HEAD/ancestry、不支持 state、
   audit 冲突及 persistence failure 均继续经既有 `AiflowError` main path 输出稳定非敏感
   message 并 exit 1；不得转换为 allow 或普通 permission deny。
9. focused tests 必须同时覆盖薄 wrapper seam 与真实临时 Git/task ledger：六类 high-risk
   action 的精确 payload/binding、所有 route 的 canonical refusal、状态不变、无 escalation、
   固定 actor、exactly-once、重放幂等、自动允许 action 无 observation 副作用，以及 target、
   task、service、audit、stale binding 的 fail-closed 行为。
10. 仅在当前 implementation subject 的正式验证与所需实现审核均通过后，将 12.4 的五个步骤
    和 evidence 投影为 completed，并把 overall 指针移至 12.5；12.5–12.6、
    `CH12-EXIT-01/02`、P2-ESC-01/P2-HOOK-01 的最终退出结论保持 pending。投影后的 subject
    必须重新取得正式验证与独立实现审核，方可进入 code approval / Gate。

## 非目标

1. 不执行 `push`、`merge`、`deploy`、`delete`、`secret_export`、`paid_external_call` 或任何
   其他命令/动作；不调用 subprocess、shell、PowerShell、cmd 或 bash，不安装 Hook，不修改
   index，也不尝试拦截真实操作系统进程。
2. 不解析命令字符串、argv、alias、pipe、redirection、wildcard、variable expansion、quote
   或 shell grammar；`action` / `target` 只是结构化、受限事实，不宣称等价于真实 shell。
3. 不验证、读取、消费或自动生成 single-use action approval。observation decision 的 required
   condition 只是审计事实与恢复要求，本 Hook 始终拒绝所观察的 high-risk action。
4. 不产生 `scope_out_of_bounds`、`policy_changed`、`controlled_file_changed` 或
   `evidence_missing` observation；不修改 pre-commit、observation/decision/service、Policy、
   contracts、state machine、task/Git context、CLI、Gate、approval 或 evidence 行为。
5. 不实现 12.5 `aiflow observe`、Hook/CLI/CI parity、CI detached-ledger、dry-run/JSON 协议或
   平台覆盖声明；不完成 12.6 README、operations、recovery 文档同步。
6. 不完成 P2-ESC-01、P2-HOOK-01 或 Chapter 12 exit checks，不宣称通用命令/操作系统安全
   沙箱，也不保证能拦截 GUI、IDE、remote 或未集成本 wrapper 的调用路径。

## 验收条件

1. wrapper tests 证明 `--action` / `--target`、help、现有 stable output 与 exit code 保持兼容；
   可选 `--task` 只用于 high-risk observation binding。Policy 自动允许 action 返回 allow，且
   不解析 task/observation、不调用 persistence service；即使提供不存在或歧义的 `--task`，
   自动允许 path 也不读取它。空 target 对所有 action 仍失败；非空自动允许 target 不进入
   high-risk contract validator。
2. 参数化测试证明六类 Policy-denied action 使用 Policy normalized value，payload 的
   schema/task/base/subject/Policy/source/kind/action/target 与当前事实精确一致；actor 固定为
   `hook_pre_command`，不能由 argv、target 或环境注入，`apply_observation` 恰调用一次。
3. 真实临时仓 integration 证明 AUTO、ASK、REVIEW、BLOCK 的 high-risk command 都只产生一条
   12.2 canonical `observation_refused` audit，state 不变且没有 `task_escalated`；所有结果均
   exit 2，BLOCK 也绝不记录为 allow。
4. 重放测试证明同一 canonical observation 不重复追加 refusal；不同 action/target 产生不同
   observation identity，audit payload/digest 冲突和委派失败继续服从 12.2 既有结论。
5. 任意 action 的空白 target、Policy-denied path 的 contract-invalid action/target、
   high-risk path 的缺失/显式不存在/歧义 task、陈旧或交叉 task 绑定、错误
   Git/Policy/classification/state、未知/篡改 audit 及 persistence failure 均在执行任何动作前
   fail closed；stderr 不回显 observation payload、target 原值或潜在敏感内容。
6. 现有 pre-commit、Policy permission、observation/parser、decision/service、generic
   escalation、task ledger、V0/V1/V2 evidence、approval、Gate、CLI 和 CI 测试保持原结论。
7. `aiflow validate TASK-0020`、`aiflow scope TASK-0020`、focused tests、全量 pytest、Ruff、
   format check、mypy、分支覆盖、相对 base 的 diff coverage 门和 `git diff --check` 全部通过；
   若 configured coverage source 对 `tools/` diff 无 executable coverage lines，只能如实记录
   diff-cover sentinel 的确定性结论，不得宣称 100%。正式验证等级以当前 Policy 分类为准。
8. Chapter 12 状态只完成 12.4；12.5–12.6 和两个 chapter exit checks 保持 pending，overall
   计数更新为 tasks 69/71、steps 368/378、evidence items 13，当前指针为 12.5，不提前声明
   P2-ESC-01 或 P2-HOOK-01 完成。

## 禁止动作

禁止 push、merge、deploy、delete、secret export、package publish、凭据访问、网络、付费或
其他外部服务调用，以及任何真实高风险动作。本任务只允许本地文件、临时测试仓库和既有
本地验证工具；未来外部动作必须获得与当时 task/spec/Policy/subject/action 绑定的明确批准。

## 错误行为

任何被当作待解析/执行输入的自由 shell/argv/环境/敏感载荷、任意 action 的空 target、
Policy-denied 但不能由 frozen `HighRiskAction` / command-summary contract 表示的 action 或
target、high-risk path 的 task ambiguity、陈旧或交叉 task/base/subject/Policy/classification
绑定、route/V 降低、
high-risk observation 未审计、`refuse` 或 required condition 被解释为允许、Hook 直接写
ledger/state、消费 action approval、绕过 `apply_observation`、重复矛盾 audit、service failure
被吞掉或任一 high-risk path 返回 exit 0 都必须 fail closed。若实现需要修改六个业务路径之外
的文件，或需要 Policy/core/state/CLI/CI/Gate/evidence 行为、命令执行、approval consumption、
dry-run/JSON 或 12.5 parity，必须停止并以 `scope_expanded`、`policy_changed`、
`spec_changed` 或对应 reason 重新治理，不得自行扩展或降低 route/V。Policy 自动允许的未知
非空 action label 不属于错误路径；Hook 必须保持现有 allow 语义且不得解释或执行其 target。

## 回滚

代码、测试和状态投影通过后续受治理提交反向修改；回滚须恢复 pre-command 的旧
Policy/workflow-only 行为、删除新增 high-risk observation 测试，并把 12.4 恢复 pending、
overall 指针移回 12.4 及相应计数。TASK-0020 的 task、classification、spec、review、approval、
evidence 与 event 历史保持追加式审计，不删除、不重写。未完成、验证失败或审核未通过时
12.4 保持 pending；不得用 Hook 输出、已有 action approval 或叙述文档替代正式证据。
