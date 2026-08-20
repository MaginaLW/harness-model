# Chapter 4：治理交互流程

Chapter 4 把分类结论转换为可重放的治理步骤。CLI 负责结构、版本绑定、状态迁移和持久证据；人或上层 Agent 负责选项的真实语义、审核判断和授权理由。阶段一的 `approve action` 只保存批准，`close` 只记录外部已经完成的合并；系统不会执行推送、合并、部署、凭据、付费调用或批准文件描述的真实动作。

## 共同版本边界

规格通过 `aiflow freeze` 显式冻结。摘要基于规范化 UTF-8 文本，写入 task 元数据与 `spec_frozen` 事件；冻结后编辑 `spec.md` 会使 `begin`、批准和后续验证拒绝旧摘要。分类记录同时绑定稳定任务输入、Policy 摘要、`base_commit` 和 `subject_commit`。AUTO 前置检查还会重算分类输入摘要，核对当前 Policy、规格、验证配置以及 Git 变化路径。

业务路径必须同时落在 task 的 `allowed_scope` 与至少一个未完成 AUTO 决策单元的 `impact_scope` 中。glob 采用路径段语义，`*` 不跨目录，`**` 才递归；绝对路径、`..`、大小写伪装和仓库外符号链接均拒绝。只有 `.ai/tasks/<current-task>/**` 是当前任务的系统治理例外。

## AUTO 时序

```text
start → classify(AUTO) → freeze → begin → IMPLEMENTING
```

```powershell
aiflow start --objective "更新限定模块" --allow "src/module/**"
aiflow classify TASK-0001 --actor codex
aiflow freeze TASK-0001 --actor author
aiflow begin TASK-0001 --actor codex
```

AUTO 不需要人工批准，但这不是跳过门。`begin` 要求所有未完成单元均为 AUTO、冻结规格仍新鲜、没有批准/外部副作用需求、禁止动作未出现、V 配置完整，而且 base→HEAD、staged、tracked、untracked、删除和重命名两端均在范围内。新增范围、依赖、权限或不可验证信号时，先拒绝，再使用 `escalate`。

## ASK 时序

```text
classify(ASK) → WAITING_FOR_ASK → answer + 决定记录 + 规格冻结 → READY 或 WAITING_FOR_SPEC_REVIEW
```

```powershell
aiflow answer TASK-0001 `
  --options-file .\ask-options.json `
  --select OPT-02 `
  --actor owner `
  --reason "采用兼容现有调用方的方案"
```

options 文件必须绑定当前 task 和 ASK 决策单元，含 2–4 个唯一选项且最多一个推荐项。CLI 验证结构，但不会声称证明选项在语义上互斥。回答以可恢复事务同时更新 `decisions.md`、规格中的冻结决定、摘要、事件和 task 状态；缺回答时任务不能开始。混合 ASK+REVIEW 先停在 ASK，回答后仍进入 `WAITING_FOR_SPEC_REVIEW`，不会吞掉 REVIEW。

## REVIEW 与三类批准

规格批准、代码批准和动作批准互不替代：

- `spec` 只在 `WAITING_FOR_SPEC_REVIEW` 生效，为每个 REVIEW 单元绑定当前冻结规格、Policy 与 subject commit，之后进入 `READY_TO_IMPLEMENT`。
- `code` 只在 `WAITING_FOR_FINAL_REVIEW` 生效，要求八节完整的 `review-package.md`、当前且通过的 `evidence.json`，以及只有当前任务治理目录变化的 Git 上下文，之后进入 `APPROVED_FOR_MERGE`。
- `action` 校验精确目标、参数摘要、subject commit、条件、有效期和 `single_use: true`，只写批准和事件，不改变主状态，也不执行动作。

```powershell
aiflow freeze TASK-0001 --actor author
aiflow approve TASK-0001 --type spec --actor reviewer --reason "规格完整且可验证"
aiflow begin TASK-0001 --actor codex

aiflow approve TASK-0001 --type code --actor reviewer --reason "证据与审核包通过"
aiflow approve TASK-0001 --type action --action-file .\action.json --actor owner --reason "批准该精确单次动作"
```

批准集合写入 `approvals.json`，事件保留历史。规格、Policy、subject commit、证据或动作描述变化后，旧批准会变为 stale；完全相同的重试不追加重复事件。

## BLOCK、升级与恢复

`escalate` 只能提高 route。普通原因的同级转换被拒绝；只有 `policy_changed` 和 `spec_changed` 可将任务送入 `ESCALATED` 做同级重评。目标 BLOCK 进入 `BLOCKED`，其他目标进入 `ESCALATED`。事件保存旧/新 route、原因码、影响、下一步、已有成果处理方式和原分类摘要。

```powershell
aiflow escalate TASK-0001 `
  --to BLOCK `
  --reason-code credentials_required `
  --impact "实现需要未声明凭据" `
  --next-step "移除需求或取得独立授权" `
  --actor codex

aiflow resolve TASK-0001 `
  --condition credentials_required `
  --evidence-ref resolution.md `
  --reason "已移除凭据依赖" `
  --actor reviewer

aiflow classify TASK-0001 --actor classifier
```

`resolve` 只接受任务目录内存在的证据引用，并在事件中保存 SHA-256、前一分类输入、Policy、规格和 subject commit 身份。重新分类要求所有恢复条件均被覆盖，证据内容仍匹配，结果不低于请求的 route；确需降低时还必须显式使用独立的降级授权。恢复采用 `classification_pending.json` 窄事务标记，中断重试会重新核验证据哈希，不能用已修改或删除的旧证据完成恢复。

所有状态事件均包含 actor、UTC 时间和结构化 payload。`events.jsonl` 是追加历史，`task.yaml` 是可从事件重放的当前物化状态；多文件回答、批准和恢复均有任务目录内的恢复 marker，失败不会静默形成可被后续命令误用的半状态。
