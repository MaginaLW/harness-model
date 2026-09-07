# TASK-0047 规格决定包

## 审核目标

请项目所有者决定是否批准 [冻结规格](spec.md) 的两项治理修复，并明确同意仅本任务
精确清单内的必要回归测试、4 个可执行示例输入、3 份边界说明与治理代码同任务交付的
隔离例外。默认隔离规则仍适用于其余工作；这不是未来任务的通用豁免。

## 背景

原后续清单中的 ASK 修复已由 TASK-0046 / PR #33、#34 完成交付，效果基线也已有第一条
真实样本。本任务处理余下的风险输入与本地动作权限缺口，不重新索取旧任务批准。
TASK-0028、被否决/暂缓方案与阶段三仍按原决定保留。

## 代码地图

- 风险字段：decision-unit schema、decision_units 与 classification_service。
- 硬规则与显式只读允许集合：四份 Policy、policy schema 和 policy evaluator。
- 前置动作检查：tools/hooks/pre_command.py；它只检查类别，不执行命令。
- 精确回归/输入/说明清单：task.yaml；没有目录 glob，不修改旧任务、旧 contract fixture
  或 mutation 执行器。可信执行边界设计见 action-boundary-design.md。

## 语义变更

1. 新分类要求 Agent 显式填写风险类别及受控动作；缺字段是零写的可修正输入错误，
   不自动排到人审。历史读取保留，旧部署/生产删除正向 token 不被空数组压掉。
2. 本地动作检查只有 Policy 明列 read 可通过；未知类别默认拒绝，六项高风险仍拒绝。
   不把本地 action 批准接成 push/merge 放行，不影响既有定向 mutation 消费保护。

## 风险

- 依赖旧的不完整分类输入或任意动作字符串的调用必须更新；必要测试输入随代码同树验证。
  因此请求上述有界隔离例外，不能以 skip/xfail 或推迟测试维持表面通过。
- Policy 升为 2.3.0 后，旧绑定失效；本任务也需一次现行 policy_changed 恢复及当前规格
  批准。集中完成最终规则后处理，不修改绑定规则来绕过，不预先批准未来代码。
- 此修复仍不能保证 Agent 的风险陈述属实或拦截所有客户端。可信服务端身份、原子授权
  消费和外部执行器未实现，也不在本次授权内；仅靠本地标签无法补齐它们。
- 实际人工工作分钟、成熟缺陷观察及同类对照仍缺失，不能据此宣称可靠性/人工成本改善。

## 证据

已完成而非待实现的事实：

- 文档与首条匿名效果观察：提交 `426b80b`，32 项相关测试与 whitespace 通过。
- Hook 当前未知动作默认允许的描述纠错：提交 `9f367af`，只读 unknown 探针返回
  `pre-command allowed`（未执行任何外部动作），37 项 wrapper/入口/skill 测试通过。
  文档明确 TASK-0047 只是待批方案，没有把拟实现行为写成已上线。
- 初稿冻结及范围审查在 `d890c0f` 保留；REV-0078 的两项技术发现已修复并追加解决记录，
  最终两位独立审查者均建议 APPROVE。最终结构化设计建议为 REV-0079。
- CLI 已重新分类并冻结为 REVIEW / V1；status 为 WAITING_FOR_SPEC_REVIEW，
  唯一 Missing 是 spec_approval。当前无人的 spec/code/action 批准、无实现、无最终验证。
- 最终账本/审查接口定向检查：contracts 与 review command 共 97 项通过，
  TASK-0047 validate、scope 及 whitespace 通过。

当前冻结规格 SHA-256 为 `cc835f26a7434a511db85ad6c4afa3f9ce8ea090f6ed3d8b98b792b3f337df8a`。
唯一当前设计上下文是 design-review-context-final.json；初稿与基线恢复前的 r2 诊断快照
均保留供追溯，不能取代 final 上下文或作为批准来源。

以上定向测试只支持已完成的文档阶段，不代替本修复未来完整 V1、覆盖率、实施审查或 Gate。

## 审核问题

是否批准该冻结规格及仅本次精确必要配套的隔离例外，允许 Agent 开始实现？
批准不包含 push、merge、部署、删除、凭据导出、付费调用或任何外部系统配置变更。

## 推荐结论

技术建议 APPROVE。项目所有者尚未决定，不把技术建议记录为人类批准。
获批后连续完成范围内实现、测试、恢复与提交；只有 CLI 确实要求新决定或具体外部授权时
才提出请求，不对机械步骤逐次询问是否继续。

### 实现后的当前决定入口（追加）

以上内容为初始规格决定时的历史快照。所有者此后已批准，Agent 已实现并启用最终
Policy 2.3.0；当前已按既有流程重分类和冻结修订规格。请以
[当前 Policy 2.3.0 规格决定包](policy23-review-package.md) 为本轮决定入口。
全量诊断仍有四项失败，三份漏列测试尚未修改；这不是代码接受或交付就绪请求。

# 当前代码审核包（正式 V1 通过后追加）

以下为当前唯一代码接受入口；以上初始规格及旧阶段描述仅保留为历史，不代表当前缺项。

## 审核目标

请项目所有者接受 TASK-0047 已实现、完整验证并独立审查的代码，绑定提交
`c0b4cb62eb8754d9364433df6ba9948ffcf43fc2`。本次只请求 code 批准，不重审规格，
不授权推送、合并、部署、删除、凭据导出、付费调用或外部配置变更。

## 背景

三个阶段的规格决定均已真实记录；必要配套全部完成，最后两文件修复后提交态
clean-clone 4 项通过，正式 V1 两轮各 1721 项全部通过。前轮失败与范围遗漏留痕保留，
未改写为成功。当前 WAITING_FOR_FINAL_REVIEW，CLI 唯一 Missing 为 code_approval。

## 代码地图

- 分类输入：classification_service、decision-unit schema、task template、hard-rules。
- 动作拒绝：permissions、policy schema、policy evaluator、pre_command wrapper。
- 启动保护：task_service 的共用 classification freshness 检查，批准绑定规则不变。
- 配套：精确清单内的测试、4 个场景输入与操作文档；clean-clone 保留真实安装链路。
- [冻结规格](spec.md)、[实现证据明细](implementation-diagnostics.md)、
  [当前实施上下文](implementation-review-context.json)提供完整边界及版本绑定。

## 语义变更

1. 新分类必须显式提供风险类别及受控动作；缺项是 Agent 可修复的零写输入错误，
   不自动进入人审。历史读取兼容；空数组不能抹掉已知部署/生产删除正向风险。
2. 只有 Policy 明列的 read 可通过本地类别检查；未知动作默认拒绝，六项高风险仍拒绝。
   通用批准不被消费，不产生外部执行权限。
3. 启动前重核分类新鲜度，过期事实或 Policy 不能借旧分类继续。四份 Policy 一次升至
   2.3.0，维护模式、批准绑定、检查、阈值、超时和 mutation 保护保持。

## 风险

风险字段不能证明真实命令语义，wrapper 也不能拦截未接入的 shell/GUI/客户端。
可信外部执行器及服务端身份、原子授权消费尚未实现，不在本轮交付范围。
本任务实际发生 3 次 spec 批准输入、6 条 DU 绑定记录；范围遗漏导致的额外介入如实
保留，没有真实人工分钟/成熟对照数据，不宣称已证实降低人工成本。

## 证据

已验证：

- 正式 V1 的 10 项 required check 全通过；普通全量 1721 passed，覆盖率全量
  1721 passed，0 failed、0 skipped、0 timed out；unit 集合另为 1115 passed。
- 总覆盖率 8523/9670，即 88.14%（要求 85%）；diff 36/36，即 100%（要求 90%）。
- 契约、范围、Ruff、format、mypy、whitespace 通过；提交态 clean-clone 4 passed。
- [REV-0082](reviews/REV-0082-r0001.json) 为当前联合技术实施审核 APPROVE：
  Dalton 独立覆盖 DU-001，Galileo 独立覆盖 DU-002、共用 begin 与主 Agent 配套修复，
  各自排除本人实现；两位均确认结论绑定最终 subject 和证据，无未解决 findings。
- [evidence.json](evidence.json) 为当前 passed 本地证据；完整日志位于
  `logs/run-20260907T165431292378Z/`。前轮 failed run 原样保留，hash 见证据明细。
- 当前 spec：`d49fde7d808e11406328e7864992bd5351dc75011656fc2b7a983d821b10006a`；
  implementation context：`00f66125b495a61cb2a056b90cfd881e6a18df8e11bbb1796858761369b5ef1e`。

未验证：当前提交的远端 CI、真实部署/外部执行和真实人工成本收益；未执行推送、合并
或部署。Gate 尚未通过，仅缺代码批准及由它推进的 APPROVED_FOR_MERGE 状态；不把
聚合 approvals stale 文案误解成现行规格批准失效，不无理由重跑已通过的 verify。

## 审核问题

是否批准上述当前提交的代码接受，允许 Agent 记录 code 批准并核对本地 Gate？
本次决定不包含任何推送、合并、部署或其他外部动作。

## 推荐结论

APPROVE。实现、完整本地验证与独立实施审查均已完成；人类代码接受仍待当前真实决定。
Agent 收到批准后仅按 CLI 记录并核对 Gate，不从先前的规格批准推定本次代码批准。
