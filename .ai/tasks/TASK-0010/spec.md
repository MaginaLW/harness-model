# Task Specification

## 目标

基于 TASK-0009 已绑定的 V1 验证、结构化审核、代码批准和只读 Gate 事实，完成 Chapter 10 的退出核验与人工状态投影对齐，并将 Chapter 11 初始化为尚未开始的下一章节。所有文档必须继续明确：Chapter 10 只交付 V2 actor/context/evidence/Gate 契约与可重放实现，真实 live V2 在 Chapter 11 检查落地前仍必须失败。

## 范围

1. 更新 `docs/implementation/chapter-10-independent-verifier-v2-evidence-gate.md`，记录 Chapter 10 退出结论、证据绑定和仍然有效的 live V2 限制。
2. 更新 `docs/superpowers/state/chapters/chapter-10.yaml`：六项任务、30 个步骤和两个退出检查完成；记录 TASK-0009 subject、基线 attestation HEAD、验证结果、结构化审核与 Gate 结论；清空已解除 blocker。
3. 更新 `docs/superpowers/state/overall.yaml`：修正运行时任务记录标志、章节/任务/步骤/退出检查计数、当前章节指针和阶段二说明，并只追加本次状态变化记录。
4. 更新 `docs/superpowers/state/README.md`，移除“CLI、Policy、运行时任务尚不存在”的历史性错误说明，明确人工状态投影与 AI Flow 运行时账本的职责边界。
5. 更新 `README.md`，把 Chapter 10 描述为完成，同时准确说明 Chapter 11 尚未实现 acceptance、integration、targeted mutation，因此 live V2 仍不能通过。
6. 新建 `docs/superpowers/state/chapters/chapter-11.yaml`，只初始化 Chapter 11 的五项任务、25 个步骤、两个 pending 退出检查及进入依赖；不得把任何 Chapter 11 能力写成已实现。

## 非目标

- 不修改 `src/`、`.ai/policy/`、schema、templates、测试或运行时行为。
- 不实现 Chapter 11 acceptance、integration、mutation manifest/runner 或 passed live V2。
- 不实现 Chapters 12–13、V3、Hooks、模型路由或资源调度。
- 不批量恢复、重验或关闭 TASK-0001 至 TASK-0007。
- 不把 TASK-0008 写成已完成；其 BLOCKED 账本保持追加式历史。
- 不记录未经证明的 external merge，也不执行 `aiflow close`。

## 验收条件

1. 基线事实可重放：在 `ed9ef1e5a781713e1798075c3013a4a1727d0375` 上，`aiflow validate TASK-0009`、`aiflow scope TASK-0009` 和 `aiflow gate TASK-0009 --format json` 分别有效、scope-valid、passed；`8eee9c1..ed9ef1e` 仅包含 TASK-0009 自身治理路径。
2. Chapter 10 状态为 completed；任务 10.1–10.6 均为 completed；30/30 步完成；CH10-EXIT-01/02 均为 passed；章节证据绑定 TASK-0009 subject `8eee9c1`、attestation HEAD `ed9ef1e` 和当前 evidence/review/approval 记录。
3. overall 状态与章节文件一致：完成 10 章、60 个逻辑任务、323 个步骤和 16 个既有退出检查；初始化 Chapter 11 后总量为 11 章、65 个任务和 348 个步骤，当前章节为 chapter-11、当前运行时任务为空，Chapter 11 完成计数保持为零。
4. Chapter 11 状态为 pending，依赖 Chapter 10 completed；11.1–11.5 与两个退出检查均为 pending，blocker 明确要求先创建新的 AI Flow 行为性任务并完成分类、冻结、设计审核和所需批准。
5. README、Chapter 10 追踪、overall 和 Chapter 11 状态对边界表述一致：Chapter 10 契约与测试完成不等于真实 live V2 passed；Chapter 11 未执行的三项检查仍以 unverified 导致失败。
6. `docs/superpowers/state/README.md` 不再声称 `src/`、`.ai/tasks/`、Policy 或 CLI 不存在，并明确以 CLI 的确定性结论为运行时权威。
7. `uv run aiflow validate TASK-0010`、`uv run aiflow scope TASK-0010`、Ruff、format、mypy、全量 pytest、`git diff --check` 和状态一致性复核全部通过；独立实现审核没有未关闭高严重度发现。

## 禁止动作

- 禁止 push、merge、deploy、delete、secret export、paid external call 和 `aiflow close`。
- 禁止修改允许范围外的文件，禁止用自然语言替代 TASK-0009 evidence/review/approval/Gate 事实。
- 禁止将 fixture 中的 passed V2 路径描述为真实 live V2 验证成功。

## 错误行为

- 若 TASK-0009 的基线 subject、evidence、review、approval 或 Gate 事实无法核对，不得把 Chapter 10 标为 completed。
- 若计数、依赖、当前章节指针或 Chapter 11 pending 状态不一致，验证必须失败。
- 若实际需要修改代码、Policy、schema、测试或扩大文档范围，必须升级、重新分类、重新冻结并重新取得所需批准。
- 若无法证明 external merge 已发生，保持 TASK-0009 为 APPROVED_FOR_MERGE，不得制造 merge_recorded 事件。

## 回滚

所有变化均为本地、版本化文档与任务治理记录，可通过后续反向提交恢复；不得改写或删除 TASK-0008/TASK-0009 的既有追加式事件与证据。
