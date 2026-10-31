# Task Specification

## 目标

使本仓常规推送和合并在项目所有者给定的受限常设授权内无需逐次人工审批或单次 action 账本记录，同时保留已有质量门禁、显式禁令和 Policy 对自动动作的默认拒绝。

## 范围

受治理变更限 `AGENTS.md`、`.ai/policy/hard-rules.yaml`、`.ai/policy/permissions.yaml`、`.ai/policy/routing.yaml`、`.ai/policy/verification-levels.yaml`、`.ai/schemas/policy.schema.json`、`src/aiflow/task_service.py`、`src/aiflow/gate.py` 与 `src/aiflow/policy.py`。配套 docs 和 tests 为本任务基线之前的独立 task-free 阶段，必须与治理变更一同交付，不单独发布。执行范围包括本任务目录中的追加治理记录。

常设授权仅限已授权目标的本仓正常交付：将单个已核候选提交推送到公开仓 `MaginaLW/harness-model` 的 `refs/heads/codex/*` 分支，不推其他 refs 或 tags；创建 PR；适用任务完成独立审核、verify 和 Gate、当前 PR head 所有 required checks 与分支保护满足后，以 merge commit 合并到本仓 main。Agent 执行前核对仓库、ref、当前 subject、审批适用性、任务禁令和实际目标仓规则。升级清单内的改动仍须按真实外部事实走 AI Flow；其他 task-free 改动不因以上常规交付动作的外部性单独建 task。其他外部或不可逆动作升级要求不变。

permissions Policy 中 push、merge 保持 deny_automatic，将 required_approval 定义为 standing_or_action：在上述常设范围内或具备单次 action 批准时满足对应过程要求，且仍遵守所有其他限制；deploy、delete、secret_export、paid_external_call 仍为 action。Schema 对旧 action 保持兼容，standing_or_action 仅可用于 push/merge；不扩大自动 allowlist。hard-rules 的真实外部动作说明与此一致，保留原 REVIEW 路由、条件和优先级。四份 Policy 版本同步升级至 2.6.0。

新 task 仅在目标仓完整 Policy 及该仓 Schema 验证通过且对应 push/merge 规则标记 standing_or_action 时，不把该项自动动作限制复制到 task 的 forbidden_actions。其他默认禁令保留，所有显式 --forbid-action 保留，混合规则逐项判断；旧 Policy 保持旧默认，旧任务和恢复标记不改写。非法、重复或不一致 Policy 在预留 task ID 前拒绝；权限 Policy 中顶层和嵌套 mapping 的重复键也必须拒绝，不能让后值覆盖绕过限制。AUTO begin 和 AUTO Gate 均合并有效 Policy 的完整自动禁令和任务显式禁令匹配 planned_actions，保持原粗粒度预检；REVIEW Gate 不声称强制这些禁令，Agent 仍须遵守。Hook 对全部六项继续拒绝，不认证授权人、不解析真实命令和目标；不主动调用此必拒 wrapper 的例外覆盖常设授权内 push/merge 及所有者明确授权的具体此类动作，已安装 Hook 和服务器拒绝仍有效。

本后继任务以 `db7b86ec8c710048758657799d1f3e42f7e41e7c` 为基线；它包括 task-free 文档和测试先行阶段以及 TASK-0121 的冻结规格、独审和范围阻塞记录。TASK-0121 因独审发现的 YAML merge 回归测试位于其基线后而保持 BLOCKED；本任务重新分类、审核和验证，不复用其版本绑定批准或证据。经过预审的本地源码候选 patch SHA-256 为 `0726a98a0cf8e54c818a96ad0960a9b0e5a7defdb9c8f3c3965b782f8064a22d`；仅在本任务正式规格审核批准后检查并应用，须对照最终源码与本规格及独立实现审核，不能以候选或旧任务的预审代替本任务正式检查。

本任务创建时实际未传 `--forbid-action`，六项默认禁令来自当时 Policy；该来源只依据本次调用与创建代码核实，不推及其他任务。项目所有者在本次会话明确同意本仓受限推送和合并常设授权的修改并要求完成交付；不声称所有者审阅过具体设计或实现。

## 非目标

不修改 CI 检查、85% 总覆盖、90% diff 覆盖、分支保护或其他阈值；不改写任何历史 task、批准、evidence、日志或任务禁令；不重新解释来源未知或明确禁止的旧任务动作。不得直接推 main、强推或改写已推送历史、推 tags 或跨仓交付；部署、删除数据、导出凭据、付费调用、未经授权私有材料传输和真实 ASK 等仍按现有要求单独决定。此任务不构建可信执行器、身份认证、目标解析或原子单次消费，不声称它们已经由 CLI/Gate/Hook 实现。

## 验收条件

- 新旧 Policy 分别校验通过；standing_or_action 仅在 push/merge 且 deny_automatic 规则上有效，其他动作和未知值拒绝；六项 Hook 对实际动作仍拒绝、自动允许集合仍仅 read，其他四项 action 要求不变。
- 新任务的默认、逐项混合、显式 push/merge 禁令、旧 Policy、旧任务、损坏或不一致 Policy 及目标仓 Schema 绑定的跨 cwd 直接 API 测试通过。非法输入在 task 分配与写入之前拒绝。
- 对真实 AUTO begin/Gate 的正负测试证明完整 Policy 默认自动禁令仍阻止 push/merge 声明计划，正常 edit 正向通过且显式任务禁令仍生效。测试不能替代 Agent 对真实目标和命令的核对。
- 本任务以真实 facts、冻结规格和独立设计审核进入实施；变更 Policy 后按实际 CLI 状态执行 sync、policy_changed 升级、条件解决、重分类、重新冻结、独立审核与当前批准，不复用旧 Policy 绑定。完整适用原生 verify、独立实现审核、code 批准及 Gate 均通过；完整测试、85% 总覆盖、90% diff、whitespace、Ruff、format、mypy 与 required CI 不降低。披露实际 skips 和验证环境。
- 以所有者本次直接授权和当前生效的旧 Policy 处理本次对外动作，不提前依赖尚未合入的新规则；逐次 action 的已有要求在旧 Policy 生效期间保留，并核对目标、当前版本、授权、期限和单次使用。required CI 绑定当前 PR head 并成功后再 merge commit。
- 提交的本任务记录、证据、源码与文档检查已知敏感数据和本机路径；不得重写既有记录以消除旧内容。

## 禁止动作

不得执行授权范围以外或被旧任务明确/来源未知禁止的动作；不得将用户对本任务目标的授权伪称为对未完成实现的细节审核。不得忽略已安装 Hook、服务器拒绝或使用不匹配版本的审核、批准、证据。

## 错误行为

Policy 或 Schema 解析、版本、交叉引用、权限值、仓库绑定、任务状态、分类、新鲜度、显式禁令、审核、验证或 CI 有缺失、损坏、失效或冲突时拒绝相应推进并保留现场；不补造通过或降低 route。发现本机路径等不允许公开的材料时先在新生成源头修复，不覆盖历史记录。

## 回滚

按仓库规则独立评审后以 Git revert 恢复相关已合并提交；保留所有历史及新任务的审核、事件和证据，不改写已推送历史。公开内容可能已被外部读取，不能保证完全撤回。
