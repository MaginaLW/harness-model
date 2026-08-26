# Task Specification

## 目标

完成 Chapter 12.1：建立一个版本为 `1.0` 的严格 observation contract，以及只负责
验证、解析和序列化的不可变 Python 类型层。契约覆盖
`scope_out_of_bounds`、`policy_changed`、`controlled_file_changed`、
`high_risk_command`、`evidence_missing` 五类事实，并成为后续 12.2–12.5 决策、
持久化、CLI、Hook 与 CI adapter 的唯一结构化输入。

## 范围

1. 新增 `.ai/schemas/observation.schema.json`，使用 JSON Schema 2020-12，根对象和
   所有嵌套对象均关闭未知字段。每项 observation 必须包含 `schema_version`、
   `task_id`、`base_commit`、`subject_commit`、`policy_sha256`、`source`、`kind` 和
   `summary`；四个 source 固定为 `hook_pre_commit`、`hook_pre_command`、`cli`、
   `ci`。
2. `summary` 必须由 `kind` 判别并只允许对应的最小事实：
   - scope、Policy 和受控文件变化只携带非空、去重、repository-relative、正斜杠
     路径集合，拒绝绝对路径、反斜杠、空段和 `.`/`..` 逃逸；
   - 高风险命令只携带 active Policy 的规范 action 类别和受限的 `target_ref`，
     `target_ref` 不得包含空白、控制字符、shell 运算符、引号、反引号、变量扩展或
     重定向；不得接受完整 argv 或自由 shell 文本；
   - evidence 缺失只携带受限的 artifact 类型和稳定 reason code，不携带日志、输出或
     evidence 正文。
3. 根绑定严格校验 `TASK-[0-9]{4,}`、40 位小写 Git commit 和 64 位小写 Policy
   SHA-256；`kind` 与 `summary` 不匹配必须拒绝。
4. 在 `src/aiflow/contracts.py` 注册命名 contract `observation`；新增
   `src/aiflow/observation.py`，提供冻结 dataclass/枚举、纯解析函数和确定性
   JSON-compatible serialization。解析不得读取仓库、时间、环境或 task ledger，不得
   修改输入；规范输入必须 round-trip，集合型字段在不可变模型中使用 tuple。
5. 新增 canonical template、valid fixture，以及 extra/invalid/missing 三类固定负例；
   扩展通用 contract matrix，并新增 focused parser/type tests。
6. 新建 Chapter 12 实施文档，并仅在实现、验证和所需审核事实成立后把 12.1 的五个
   步骤及 evidence 投影为 completed；Chapter 12 其余任务和两个退出条件保持 pending，
   overall 当前指针移至 12.2。历史状态只追加，不重写既有章节证据。
7. 实现允许范围仅为 TASK-0017 `task.yaml` 中列出的 13 个精确路径；task-local 治理
   文件按 AI Flow 规则单独记录，不借此扩展产品代码范围。

## 非目标

1. 不实现 observation 到 `record` / `escalate` / `refuse` 的映射，不调用或修改
   `escalate_task`，不写 observation/refusal ledger，也不改变任务状态机。
2. 不新增 `aiflow observe`，不修改 `cli.py`、`tools/hooks/**`、CI workflow、Gate、
   Policy、permissions、evidence/approval/review schemas 或现有 V0/V1/V2 结论。
3. 不解析、保存或执行 PowerShell、cmd、bash 等自由 shell 命令；不宣称拦截 IDE、
   GUI/remote Git 或提供通用安全沙箱。
4. 不实现 Chapter 12.2–12.6、Chapter 13、V3、真实模型路由、资源调度、安全扫描或
   外部服务。

## 验收条件

1. JSON Schema 和通用 contract matrix 对五类 kind、四类 source、全部必需绑定和
   kind-specific summary 给出确定性结论；合法 template/fixture 通过，extra、invalid、
   missing fixtures 均以稳定 JSON Pointer 错误失败。
2. focused tests 证明 parser 返回冻结、不可变且可比较的类型，不修改输入；规范 payload
   `parse -> serialize` 与原 payload 相同，重复解析和序列化结果一致。
3. 负例覆盖未知根/summary 字段、未知 kind/source/action、缺失绑定、大小写或长度错误的
   hash、空/重复/逃逸/绝对/反斜杠路径、kind/summary 错配，以及空白、shell 运算符、
   引号、变量扩展或重定向形式的 `target_ref`。验证错误不得回显未知或潜在敏感值。
4. 新 contract 不放宽现有 schema；现有 contract fixtures、task/event consistency、
   V0/V1 evidence 与 Gate 测试保持原结论。12.1 不产生 task event、decision 或外部副作用。
5. `aiflow validate TASK-0017`、`aiflow scope TASK-0017`、focused tests、全量 pytest、
   Ruff、format check、mypy、分支覆盖、相对 base 的 diff coverage（至少 90%）和
   `git diff --check` 全部通过；最终验证等级以当前 Policy 的确定性分类为准。
6. Chapter 12 状态只完成 12.1 的五个步骤；12.2–12.6 和 `CH12-EXIT-01/02` 保持
   pending，overall 计数与当前指针一致，不提前声明 P2-ESC-01 或 P2-HOOK-01 已完成。

## 禁止动作

禁止 push、merge、deploy、delete、secret export、package publish、付费外部调用、
凭据访问或任何真实高风险命令执行。测试只构造内存/fixture 输入，不调用网络、不运行
被观察的命令；任何后续高风险动作必须取得独立、版本绑定的 action approval。

## 错误行为

任何未知字段/枚举、缺失或陈旧绑定、非规范路径、kind/summary 错配、自由命令载荷、
疑似 shell 语法、日志/env/stdout/stderr/credentials 字段都必须 fail closed，并只返回稳定、
不含原始敏感值的错误。若实施发现必须修改 Policy、Hook、CLI、Gate、state machine、
evidence contract 或范围外文件，必须停止并以 `policy_changed`、`scope_expanded`、
`spec_changed` 或相应原因重新治理，不得在当前规格内自行扩展或降低 route/V。

## 回滚

代码、schema、template、fixture、测试和状态投影均通过后续受治理提交反向修改；
TASK-0017 的 task、classification、spec、review、approval、evidence 与 event 历史保持
追加式审计，不删除、不重写。未完成或验证失败时，Chapter 12.1 保持或恢复为 pending，
不得把叙述性文档当作通过证据。
