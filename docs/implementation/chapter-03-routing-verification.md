# Chapter 3：分流与验证等级

Chapter 3 将任务拆为可独立审计的决策单元。分类服务读取已验证的
Policy 与任务记录，为每个单元形成可持久化的 route、验证等级、规则编号和
解释；它不调用模型，也不执行推送、合并、部署、删除或其他外部动作。

## 决策单元与输入门

`decision_units` 是 task 记录中的对象列表，而不是自由文本。解析时会按
`decision_unit_id` 稳定排序，并对每个对象执行 Schema 与交叉字段检查：单元
必须属于当前任务、影响范围不得为空、可逆性必须是已知枚举值，且权限需求只能
使用已声明的 `spec_approval`、`code_approval` 或 `action_approval`。不合格输入
不能进入分类。

Policy 条件由受限谓词解释器执行。它只允许 `equals`、`not_equals`、`in`、
`contains_any`、`contains_all`、`exists`、`is_empty` 和
`greater_than_or_equal`，字段仅能使用受限点号路径。每次求值只输出稳定的布尔
结论和不含输入值的解释，因此不执行 Python 表达式、正则或任意函数。缺字段严格
遵循规则声明的 `error`、`match`、`no_match` 策略；要求完整保护条件的规则在
事实缺失时不会产生 AUTO，分类会保守地给出阻塞或 REVIEW 结论。

## route 规则与汇总

硬规则与普通路由规则均按显式优先级求值，所有命中的规则都会保留。有效结论按
`BLOCK > REVIEW > ASK > AUTO` 取最严格值；同优先级给出不兼容结论、BLOCK
缺少恢复条件、或 AUTO 缺少完整护栏，都会变成带规则编号的可解释 BLOCK。

没有规则命中时，系统使用具名 `ROUTE-DEFAULT-REVIEW`。这条默认规则是 Policy
的一部分，故不存在隐式 AUTO。任务级 route 仅汇总未完成单元，已完成单元的原始
结论仍保留；如果所有单元都完成，摘要显示 `completed`。

## V0/V1 独立判定

验证等级只读取单元的变更特征、可用检查和验证 Policy，不读取 route。机械、局部、
非行为性变更，并且 V0 所需检查完整时，可以是 V0；行为或代码变化、跨文件/模块
交互、回归风险、低错误可检测性或非机械工作均要求 V1。缺少必需验证工具会记录
`VERIFICATION-TOOLS-MISSING` 阻塞原因，绝不降为 V0。

任务验证等级同样只汇总未完成单元的最高等级，且保留每个单元的规则编号、解释和
阻塞原因。这使 AUTO+V1、ASK+V0、REVIEW+V1 都是合法且可审计的组合，而不是
route 到 V 等级的硬编码映射。

## 分类记录、状态和可追溯性

`aiflow classify TASK-ID --actor ACTOR` 仅接受 NEW，以及已记录解除条件的
BLOCKED/ESCALATED 任务。它拒绝缺少决策单元、损坏 Policy、Git 基线不匹配和超出
允许范围的影响路径。每份 `classification.json` 记录每个单元的 route 与 V、命中
规则和有序解释，以及 Policy 版本/摘要、分类输入摘要、`base_commit`、
`subject_commit` 和分类时间；绝对 checkout 路径和动态展示字段不进入输入摘要。

相同输入、Policy 和提交身份会复用既有分类记录。升级可直接记录原因；降低 route
或验证等级必须先有解除记录，且需要匹配当前输入与 Policy 摘要的人工授权。分类
先原子写入记录，再推进状态：BLOCK 或验证阻塞进入 `BLOCKED`，ASK 进入
`WAITING_FOR_ASK`，REVIEW 进入 `WAITING_FOR_SPEC_REVIEW`，其余进入
`READY_TO_IMPLEMENT`。

## CLI 输出示例

CLI 的标准输出只显示任务 ID 和有效 route；完整审计细节位于该任务的
`classification.json` 与状态事件中。以下是四类黄金输入的示例：

```text
> aiflow classify TASK-1001 --actor codex
TASK-1001 AUTO

> aiflow classify TASK-1002 --actor codex
TASK-1002 ASK

> aiflow classify TASK-1003 --actor codex
TASK-1003 REVIEW

> aiflow classify TASK-1004 --actor codex
TASK-1004 BLOCK
```

这些输出仅表示分类结论：AUTO 也不授权真实外部动作；任何推送、合并、部署、删除、
凭据处理或付费调用仍须遵循单独的批准与 Gate。
