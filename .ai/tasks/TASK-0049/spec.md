# TASK-0049：begin 与 spec approval 新鲜度一致性

## 目标

TASK-0048 的 `closeout-begin-binding-001.json` 已记录：status 显示批准有效且仅缺
begin，begin 却因 subject 不同拒绝，READY 状态又不允许补 spec 批准。
当前源码还遗漏 base 绑定检查。修复应统一采用既有 `spec_approval` 新鲜度规则：
base_commit、policy_sha256、spec_sha256；subject-only 变化不使规格批准失效。

## 范围

仅修改 `src/aiflow/task_service.py` 的 `_require_ready_artifacts`：对每个 REVIEW
决策单元寻找正确类型、正确单元且通过共享 `evaluate_freshness` 的规格批准。
当前绑定来自任务 base、当前有效 Policy 和实际冻结规格摘要。保留分类新鲜度检查、
无有效批准时的 `BEGIN_APPROVAL_INVALID`、完整单元覆盖要求和历史批准记录。
AUTO 路径及 code/action 的 subject、证据与消费绑定均保持既有语义。
不修改 Policy、Schema、状态机或批准允许状态，不重写 TASK-0048 的证据。

## 验收条件

- 只有 subject 变化、base/policy/spec 保持一致且分类当前有效时，status 与 begin 一致。
- base、policy 或 spec 缺失或不符仍拒绝；错误批准类型、其他单元批准不能代替。
- 历史失效记录与一条当前有效记录共存时，当前记录可以满足对应单元。
- 必需的每个 REVIEW 单元均须有有效批准；拒绝路径不得推进状态或追加成功事件。
- 安全文档与回归测试按维护模式单独提交，不纳入本治理任务源码范围。
- 实现后通过完整测试、85% 总覆盖率、90% diff coverage、whitespace、Ruff、
  format、mypy，以及当前 CLI 要求的验证与独立审查。

## 禁止动作

禁止 push、merge、deploy、delete、secret_export、paid_external_call。
三个既有未跟踪原稿不纳入提交，不改历史挂起任务，不启动条件性阶段。

## 错误行为

缺少或失效的 base/policy/spec、错误类型与单元必须拒绝；分类失效仍在原检查点
拒绝。质量门失败保留失败证据并修复，不把 status 或独立技术审查当作人类批准。

## 回滚

未发布源码采用有界前向恢复提交；已记录事件、失败证据与批准不删除、不覆盖。

## 执行顺序

主 agent 建立、分类和冻结规格；两名 sub-agent 并行进行缺陷核查与发布范围核对。
获得所需规格批准后，主 agent 串行 begin、实现和固定候选；回归与独立审查可由
不同 agent 并行执行，最终由主 agent 汇总验证、处理 CLI 缺项并提交。
尚未批准规格时不修改受控源码。回退使用后续有界修复提交，保留账本和证据。
push/merge 等动作须对最终具体候选另行授权；本任务不包含真实外部执行。
