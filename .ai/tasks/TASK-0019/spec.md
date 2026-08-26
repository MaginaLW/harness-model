# Task Specification

## 目标

完成 Chapter 12.3：把现有 `tools/hooks/pre_commit.py` 从只返回 scope/workflow
precondition 的薄检查器，扩展为只构造并提交编辑后范围事实的 Hook adapter。当完整变更集
超出当前 task `allowed_scope` 时，Hook 必须创建绑定当前 task、base、subject、active Policy
且 `source=hook_pre_commit`、`kind=scope_out_of_bounds` 的 immutable observation，并且只委派
Chapter 12.2 的共享 `apply_observation` service 执行确定性 decision、task-local audit 与必要的
单调升级。Hook 自身不得复制 route/V 或 Policy 表、直接写事件/状态，亦不得把任何
observation decision 解释为允许提交。

## 范围

1. 实现允许范围固定为 TASK-0019 `task.yaml` 中的六个精确业务路径：
   `tools/hooks/pre_commit.py`、`tests/integration/test_tool_wrappers.py`、
   `tests/integration/test_observation_escalation.py`、Chapter 12 实施追踪文档、Chapter 12
   状态文件和 overall 状态文件。task-local 治理记录仍按 AI Flow 规则追加。
2. 保留现有 `--task` 接口和 `_resolve_task_id` 行为：显式 task 必须可严格读取；省略时必须
   恰有一个未 MERGED task，否则以既有 `HOOK_TASK_AMBIGUOUS` 失败。不得从环境、Git 分支名、
   最近修改目录或用户文本猜测 task。
3. 保留现有完整 changed-path 语义：使用当前共享 collector 收集 base-to-subject committed、
   subject-to-HEAD attestation 及 tracked/untracked/deleted/renamed worktree 路径，再使用共享
   `assess_scope` 归一化和分类。不得缩窄为仅 staged diff，也不得自行实现第二份 glob/path
   matcher；current-task governance 与 cache 例外继续由共享 scope core 决定。
4. 仅当 `ScopeAssessment.out_of_scope` 非空时，按其已排序、去重、repository-relative 的精确
   路径构造一个 JSON-compatible payload，再经 `parse_observation` 得到 immutable
   `Observation`。绑定字段只能来自严格 task record 与 active Policy bundle：版本 `1.0`、当前
   `task_id`、`base_commit`、`subject_commit`、`policy_sha256`、source `hook_pre_commit`、kind
   `scope_out_of_bounds` 和最小 `summary.paths`；不得接受或记录自由文本、shell、argv、环境、
   stdout/stderr、credential 或 secret。
5. Hook 只能调用现有公开 `apply_observation(repository_root, task_id, observation,
   actor="hook_pre_commit")`。不得导入或调用 `record_task_event`、`escalate_task`、transition
   helper 或内部 decision table；record/refuse/escalate、audit-first、幂等重放、中断恢复及
   单调 route 行为完全由 12.2 core 负责。
6. in-scope 且 workflow preconditions 通过时保持现有 `pre-commit allowed` / exit 0，且不得
   构造、决定或持久化 observation。任一 out-of-scope observation 在共享 service 成功处理后
   仍保持 `pre-commit denied` / exit 2，并保留既有 `SCOPE_EXPANDED` failure code；即使共享
   decision 为 `record`，也绝不放行。所有 `AiflowError` 继续由现有 main 路径输出稳定非敏感
   message 并 exit 1；不得把 service/audit/绑定失败转换为 allow 或普通 scope deny。
7. focused tests 必须同时覆盖薄 wrapper seam 与真实临时 Git/task ledger：in-scope 无副作用，
   REVIEW 越界追加一个 refusal 且 state 不变，AUTO/ASK 越界只经既有 escalation path 单调到
   REVIEW，BLOCK 越界只记录且仍拒绝提交；相同 observation 重放不重复 audit/escalation，
   source/bindings/actor/path 摘要精确，task ambiguity 与 service failure 均 fail closed。
8. 仅在当前 implementation subject 的正式验证与所需实现审核均通过后，将 12.3 的五个步骤
   和 evidence 投影为 completed，并把 overall 指针移至 12.4；12.4–12.6、
   `CH12-EXIT-01/02`、P2-ESC-01/P2-HOOK-01 的最终退出结论保持 pending。

## 非目标

1. 不实现 12.4 `pre_command`、high-risk-command observation、action/target 解析、拒绝审计或
   任意命令执行；不修改 `tools/hooks/pre_command.py`。
2. 不实现 12.5 `aiflow observe`、CLI/CI adapter、Hook/CLI/CI parity、CI detached-ledger
   行为、dry-run/JSON 协议或平台支持声明。
3. 本任务只产生 `scope_out_of_bounds`。不产生 `policy_changed`：真实 Policy 编辑会先使当前
   classification freshness 失效，不能在 Hook 中绕过。也不产生 `controlled_file_changed`：
   仓库当前没有权威 controlled-file registry，Hook 不得硬编码隐含清单。需要这些能力时必须
   另行明确 registry/freshness 设计并重新分类、冻结和批准。
4. 不修改 observation/decision/service、scope、Git context、Policy、contracts、state machine、
   CLI、Gate、approval 或 evidence 行为；不得增加第二份 route/verification/permission 表。
5. 不完成 12.6 README、operations、recovery 文档同步；README 的当前指针陈旧事实留在 12.6
   统一修正，不作为本任务扩展业务范围的理由。
6. 不安装 Hook、不执行 `git commit`，不修改 index，不修复或移动用户文件，也不宣称 Git Hook
   可以拦截 IDE 保存、GUI/remote Git、未安装 Hook 的客户端或通用操作系统动作。

## 验收条件

1. wrapper tests 证明 `--task`/唯一 active task、help、in-scope allow 和既有稳定输出保持兼容；
   in-scope 调用不会加载 active Policy、构造 observation 或调用 persistence service。
2. 参数化测试证明 out-of-scope payload 的 schema/task/base/subject/Policy/source/kind/paths 与
   shared scope assessment 精确一致；actor 固定为 `hook_pre_commit`，不能由 argv 或环境注入。
3. 真实临时仓 integration 证明 REVIEW refusal、AUTO/ASK escalation 和 BLOCK record 都只产生
   12.2 已定义的 canonical audit/state 结果；Hook 无直接 ledger/state 写入 seam，所有结果均
   exit 2，`record` 仍不允许提交。
4. 重放测试证明首次 audit 后 task-local governance path 不污染下一次 scope observation；同一
   canonical observation 不重复追加 audit/escalation。event/payload/digest 冲突、委派中断和
   retry 继续服从 12.2 既有结论。
5. missing/ambiguous task、非法/逃逸路径、缺失或陈旧 base/subject/Policy/classification、错误
   repository/branch/HEAD/ancestry、不支持 task state、未知/篡改 audit 或 persistence failure
   均 fail closed；输出不回显 observation payload、路径正文或敏感原值。
6. 现有 scope/workflow、observation/parser、decision/service、generic escalation、task ledger、
   pre-command、V0/V1/V2 evidence、approval、Gate 和 CLI 测试保持原结论。
7. `aiflow validate TASK-0019`、`aiflow scope TASK-0019`、focused tests、全量 pytest、Ruff、
   format check、mypy、分支覆盖、相对 base 的 diff coverage（至少 90%）和
   `git diff --check` 全部通过；正式验证等级以当前 Policy 的确定性分类为准。
8. Chapter 12 状态只完成 12.3；12.4–12.6 和两个 chapter exit checks 保持 pending，overall
   计数与 12.4 指针一致，不提前声明 P2-ESC-01 或 P2-HOOK-01 完成。

## 禁止动作

禁止 push、merge、deploy、delete、secret export、package publish、凭据访问、网络、Grok、
付费或其他外部服务调用，以及任何真实高风险动作。本任务只允许本地文件、临时测试仓库和
既有本地验证工具；未来外部动作必须获得与当时 task/spec/Policy/subject/action 绑定的单次批准。

## 错误行为

任何 task ambiguity、路径逃逸、未知 observation 字段/枚举、陈旧或交叉 task 绑定、Policy /
classification drift、route/V 降低、`record` 被解释为 allow、Hook 直接写 ledger/state、绕过
`apply_observation`/`escalate_task`、自由 shell/敏感载荷、重复矛盾 audit、service failure 被吞掉、
out-of-scope 返回 exit 0 或 in-scope 产生 observation 都必须 fail closed。若实现需要修改六个业务
路径之外的文件，或需要 Policy/controlled-file observation、dry-run/JSON、CLI/CI/pre-command、
Policy/service/state/Gate/evidence 行为，必须停止并以 `scope_expanded`、`policy_changed`、
`spec_changed` 或对应 reason 重新治理，不得自行扩展或降低 route/V。

## 回滚

代码、测试和状态投影通过后续受治理提交反向修改；回滚须同时恢复 pre-commit 的旧 scope /
workflow-only 行为、删除新增 Hook observation 测试，并把 12.3 恢复 pending、overall 指针移回
12.3 及相应计数。TASK-0019 的 task、classification、spec、review、approval、evidence 与 event
历史保持追加式审计，不删除、不重写。未完成、验证失败或审核未通过时 12.3 保持 pending；
不得用 Hook 输出、未绑定 observation 或叙述文档替代正式证据。
