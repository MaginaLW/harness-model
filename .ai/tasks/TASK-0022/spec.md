# Task Specification

## 目标

完成 Chapter 12.5：增加受限的 `aiflow observe` CLI/CI adapter，使 CLI apply、CLI dry-run
和 CI read-only 三种入口与现有 Hook 共同复用同一 observation parser、当前 task/Git/Policy/
classification 绑定检查和确定性 decision core。对相同受支持事实，各入口必须产生相同的
非授权 decision 语义；CI 与 dry-run 不得写 task ledger。实现和证据必须如实限定 shell、
Hook 安装及平台覆盖，不得宣称通用命令或操作系统安全沙箱。

## 范围

1. 实现允许范围固定为 TASK-0022 `task.yaml` 中的九个精确业务路径：
   `src/aiflow/observation_service.py`、新增 `src/aiflow/observation_adapter.py`、
   `src/aiflow/cli.py`、两个 unit test、一个 integration parity test、Chapter 12 实施追踪文档、
   Chapter 12 状态文件和 overall 状态文件。task-local 治理记录仍按 AI Flow 规则追加。
2. 新增命令固定为 `aiflow observe TASK-ID --input FILE --mode {apply,dry-run,ci}
   [--actor ACTOR]`。`TASK-ID` 必须显式给出；adapter 不搜索、推断或选择 active task。
   `--input` 只读取一个本地 UTF-8 JSON object，并必须通过现有 `observation` contract 与
   `parse_observation`；不得从 stdin、环境变量、shell 字符串、argv 数组或网络接收事实。
   JSON 语法错误、重复 key、未知字段、非 object、读取失败和 contract 错误以稳定、非回显的
   `AiflowError` / `ContractError` 失败。
3. 三种 mode 与 source/actor 的组合为封闭集合：`apply` 只接受 `source=cli` 且要求非空
   `--actor`；`dry-run` 只接受 `source=cli` 且禁止 actor；`ci` 只接受 `source=ci` 且禁止
   actor。任一 mismatch 必须在 audit、state transition 或其他写入前 fail closed。现有 Hook
   仍可直接向 service 提交自己的 `hook_pre_commit` / `hook_pre_command` source，adapter 不得
   伪装或代发 Hook source。
4. 将现有 current-facts 检查收敛为公开只读
   `evaluate_observation(repository_root, task_id, observation)`：它严格验证 task identity、
   state、base/subject、repository/branch/HEAD/ancestry、active Policy 和 current
   classification input，再只调用现有 `decide_observation`。不得复制或修改 decision/Policy
   表，不得写 task、event、state、approval 或 evidence。
5. `apply_observation` 保留 12.2 的 task-local audit、幂等重放和只经 `escalate_task` 的单调
   escalation 行为；它必须在读取或写入 ledger 前继续拒绝 `source=ci`，随后复用
   `evaluate_observation`。本任务不得改变五类 observation 在任何 route/V 上的 disposition、
   reason、required conditions、target route 或 `execution_allowed=false` 结论。
6. adapter 的 `apply` mode 只委派 `apply_observation`，输出已有 audit/escalation event 的
   非敏感类型与 sequence；重放继续沿用既有 audit identity，不重复写入。`dry-run` 和 `ci`
   mode 只能委派 `evaluate_observation`，不得调用 `apply_observation`、`record_task_event`、
   `escalate_task` 或 transition/approval helper。这里的 detached/read-only 指可读取当前已提交
   task、classification、Policy 与 Git binding，但 task 目录、state、events 和 approvals 在
   命令前后必须逐字节不变。
7. 所有成功解析并得出 decision 的调用只向 stdout 输出一个确定性 JSON object，包含协议版本、
   task、mode、ledger effect、现有 canonical serialized decision，以及 apply-only 的可选
   audit/escalation event reference；不得输出原始 observation、summary、target、paths、actor、
   环境、stdout/stderr 或凭据。无效输入/状态 exit 1；有效 observation 因
   `execution_allowed=false` 在三种 mode 均 exit 2。不得存在把观察结论解释为执行许可的 exit 0。
8. parity 定义为相同事实在以下 decision 语义字段上完全一致：`schema_version`、
   `disposition`、`reason_code`、`current_route`、`current_verification_level`、
   `execution_allowed`、`required_conditions` 和 `target_route`。`observation_sha256` 正确包含
   source，因此不同 source 的 digest 必须不同；mode、ledger effect 和 apply-only event
   metadata 也不属于语义 parity。不得宣称不同入口的 JSON 字节或用户可见文案相同。
9. core/adapter matrix 覆盖五类 observation、四种 route 和 V0/V1/V2。真实 Hook end-to-end
   parity 只覆盖目前实际支持的两类事实：pre-commit 的 `scope_out_of_bounds` 与 pre-command
   的 `high_risk_command`；另外三类只证明 core、CLI 和 CI 语义，不声称现有 Hook 能产生。
   in-scope edit 必须保持 Hook allow 且无 observation；六类 Policy 禁止自动 action 均须覆盖。
10. parity integration 使用相互隔离的临时 Git/task ledger，确保 apply/escalation 不改变后续
    入口的比较前提；覆盖 task ambiguity、显式 task/payload mismatch、binding drift、path
    escape、unknown fields、malformed/duplicate-key JSON、apply replay，以及 dry-run/CI 对完整
    task 目录的零写入。stale 或错误事实必须在所有入口 fail closed，且不回显调用者载荷。
11. 实施追踪文档必须明确：Git Hook 不能拦截未安装 Hook 的客户端、IDE save、GUI/remote Git；
    pre-command 只接受结构化规范 action/target，不能安全解释 PowerShell/cmd/bash、alias、pipe、
    redirection、quote、wildcard 或 expansion；本次 Windows 本地测试和既有 symlink skips 不
    证明 Linux/macOS live Hook 安装或所有 host 行为；系统不是通用命令/OS sandbox。
12. 仅在当前 implementation subject 的正式验证与所需实现审核均通过后，将 12.5 的五个步骤
    和 evidence 投影为 completed，并把 overall 指针移至 12.6；12.6 与 `CH12-EXIT-01/02`
    保持 pending。可记录 P2-ESC-01/P2-HOOK-01 的当前技术证据已建立，但不得在 12.6 和章节
    最终退出证据前宣称 Chapter 12 完成。投影后的 subject 必须重新取得正式验证与独立实现
    审核，方可进入 code approval / Gate。

## 非目标

1. 不修改 `tools/hooks/pre_commit.py`、`tools/hooks/pre_command.py`、observation/decision
   schema、Policy、route/V matrix、state machine、approval、evidence、Gate 或 CI workflow；
   parity 通过薄 adapter 和测试现有入口证明，不在 Hook 内增加第二份规则。
2. 不执行或代理 observation 描述的 push、merge、deploy、delete、secret export、paid call
   或任何命令；不消费 action approval，不安装 Hook，不修改 index，不拦截真实 OS 进程。
3. 不解析自由 shell、argv、alias、pipe、redirection、wildcard、variable expansion、quote、
   environment、stdin/stdout/stderr、credential 或 secret；不尝试用 target 猜测真实命令。
4. 不允许 CI/dry-run 写 task-local audit、escalate state、同步 subject、生成 approval/evidence，
   或以任何方式自动降级 route/V。CI read-only 结论不能替代 merge Gate 或正式 evidence。
5. 不完成 12.6，不修改现有未跟踪 TASK-0021 所允许的 README、operations hooks、quickstart、
   recovery 文档，不完成 Chapter 12 exit checks，也不开始 Chapter 13。
6. 不调用网络、外部模型、外部服务或付费能力；不 push、merge、deploy、delete、发布包或访问凭据。

## 验收条件

1. CLI help 精确暴露 `observe` 的显式 task、input、封闭 mode 与 conditional actor 契约；三种
   valid invocation 输出可重复解析的 canonical JSON 并 exit 2，invalid invocation 只输出
   稳定非敏感错误并 exit 1。
2. unit tests 证明 `evaluate_observation` 对五类事实复用完整 current binding 与原 decision
   matrix、零写入；`apply_observation` 在任何 ledger read/write 前拒绝 CI，并对 Hook/CLI
   source 保持既有 record/refuse/escalate/idempotence。
3. adapter tests 参数化覆盖 mode/source/actor 全组合、严格 JSON/duplicate key、显式 task
   binding、canonical result envelope、apply event refs、dry-run/CI 不调用 mutation helper、
   不回显 payload，以及错误优先级不产生部分写入。
4. parity matrix 证明五类 kind × 四 route × 三 V 的 semantic projection 对
   hook_pre_commit、hook_pre_command、cli、ci source 相同且都不授权；source-sensitive digest
   各不相同，所有 target route 单调不降级。
5. 真实临时仓测试证明 pre-commit 越界和 pre-command 六类高风险 action 的 Hook audit decision
   与 CLI apply/dry-run、CI mode 语义一致；所有受支持的越界/高风险事实均在动作前 exit 2，
   in-scope edit 保持 allow/无 observation。每个写入入口使用隔离仓，避免状态串扰。
6. CI/dry-run 前后完整 task 目录内容 hash 相同；monkeypatch 同时证明未调用
   `apply_observation`、`record_task_event` 或 `escalate_task`。apply replay 不重复 audit，且不会
   因已有 approval 或 BLOCK route 变成 allow。
7. malformed/duplicate/unknown-field JSON、path escape、非法 target、task ambiguity、显式 task
   mismatch、陈旧 base/subject/Policy/classification、错误 repository/branch/HEAD/ancestry、
   unsupported state、audit conflict 和 persistence failure 均 exit 1/fail closed，stderr 不含
   原始 payload、path、target 或潜在敏感值。
8. 现有 Hook wrapper、observation parser/decision/service、generic escalation、Policy permission、
   task ledger、V0/V1/V2 evidence、approval、Gate、CLI 和 CI 测试保持原结论。
9. `aiflow validate TASK-0022`、`aiflow scope TASK-0022`、focused tests、全量 pytest、Ruff、
   format check、mypy、分支覆盖、相对 base 的至少 90% diff coverage 和 `git diff --check`
   全部通过；正式验证等级以 active Policy 的当前分类为准。
10. Chapter 12 状态只完成 12.5；12.6 和两个 chapter exit checks 保持 pending，overall 计数
    更新为 tasks 70/71、steps 373/378、evidence items 14，当前指针为 12.6，不提前声明 Chapter
    12 或 Phase 02 完成。

## 禁止动作

禁止 push、merge、deploy、delete、secret export、package publish、凭据访问、网络、付费或
其他外部服务调用，以及任何真实高风险动作。本任务只允许本地文件、隔离临时测试仓库和既有
本地验证工具；未来外部动作必须获得与当时 task/spec/Policy/subject/action 绑定的明确批准。

## 错误行为

任何 mode/source/actor 非法组合、隐式 task 选择、非 UTF-8/非 object/重复 key/未知字段输入、
自由 shell/argv/environment/敏感载荷、task/base/subject/Policy/classification/Git 绑定陈旧或交叉、
unsupported state、CI/dry-run 写 ledger 或触发 transition、decision/Policy 表复制、route/V 降低、
`execution_allowed=false` 被解释为 allow、apply 部分写入、audit 冲突或 persistence failure 被
吞掉都必须 fail closed。若实现需要修改九个业务路径之外的文件、现有 schema/Policy/Hook/
state/Gate/evidence/approval 语义，或需要网络、外部/付费调用、真实 action、12.6 文档或 chapter
exit 状态，必须停止并以 `scope_expanded`、`policy_changed`、`spec_changed` 或对应 reason
重新治理，不得自行扩展、降级或借用 TASK-0021 范围。

## 回滚

代码、测试和状态投影通过后续受治理提交反向修改：删除 `observe` 子命令与 adapter，恢复
`observation_service` 的私有 current-facts 结构和原 CI persistence guard，删除 parity tests，
并把 12.5 恢复 pending、overall 指针移回 12.5 及相应计数。TASK-0022 的 task、classification、
spec、review、approval、evidence 与 event 历史保持追加式审计，不删除、不重写。未完成、验证失败
或审核未通过时 12.5 保持 pending；不得用 narrative、dry-run 输出或 Hook 文案替代正式证据。
