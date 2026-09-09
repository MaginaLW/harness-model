# ZCode 外仓试点反馈

观察日期：2026-09-09。对象是 `ai-agent-dotfiles` 接入轻量规则后自然发生的代码工作，
不是完整 AI Flow 安装，也不是 harness-model 阶段三验收。

## 固定窗口与证据强度

接入基线为 [`8bc666c`](https://github.com/MaginaLW/ai-agent-dotfiles/commit/8bc666c8560ddde8435144eda722489ddc7f3db3)，
本次源码与收尾记录固定于 [`3a2ff6b`](https://github.com/MaginaLW/ai-agent-dotfiles/commit/3a2ff6b7cfec62d28eb72aeaf6c14269eed947ab)。
窗口内有 7 个后续提交，目标项目记录 Phase 2 Task 2、3 各完成 7/7，阶段进度从 6/52
到 20/52。这里的 Phase 2 是目标项目自己的路线，不能换算为本仓阶段三进度。

- **可复核事实：** 固定提交里的生产代码、Schema、CI、测试发现方式与文档；另有明确
  绑定 `8bc666c` 的历史 CI 失败。后者不是 `3a2ff6b` 的实际 CI 结果。
- **仅项目记载：** Task 2、3 分别报告全量 35/35、36/36 套件通过，保留了汇总文字与
  哈希，但也记载外部 JSON 摘要已删除。本次不能独立复核这两次运行的逐套件原始结果，
  更不能把收尾文档提交号当作当时实际被测版本。
- **缺失或未证明：** 这两个任务的可核实模型身份、费用、人类工作分钟、独立审核证据、
  同类对照及完整缺陷观察期；规则被显式读取不等于已经证明工具自动注入。

这两个任务窗口不是受控效果对照。本页不宣称 ZCode 或 harness-model 导致了效率或
可靠度改善，也不表示后续目标分支、CI 或工作区状态一直未变。

## 五项反馈与已落地方法

### 1. 局部通过不能代表交付链通过

固定源码中，环境构建生产端输出 SchemaVersion 3，Schema 也要求 3，但 CI 的额外判断
仍要求 2。可复核位置是[生产端](https://github.com/MaginaLW/ai-agent-dotfiles/blob/3a2ff6b7cfec62d28eb72aeaf6c14269eed947ab/scripts/harness-env-common.ps1#L1055)、
[Schema](https://github.com/MaginaLW/ai-agent-dotfiles/blob/3a2ff6b7cfec62d28eb72aeaf6c14269eed947ab/schemas/harness-env-build.schema.json#L25)
与 [CI 消费端](https://github.com/MaginaLW/ai-agent-dotfiles/blob/3a2ff6b7cfec62d28eb72aeaf6c14269eed947ab/.github/workflows/validate.yml#L184)。
历史 [CI run 34294793588](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/34294793588)
在 `8bc666c` 的机器可读产物验证步骤失败，报环境构建 JSON 无效，后续完整测试步骤未运行。
源码不一致在 `3a2ff6b` 仍可见，但不能据此编造该提交已经执行过同一次失败。

已纳入[接入指南](adoption.md#真实任务的执行与收尾)：格式/版本变更时核对生产端、
注册的 Schema、测试与 CI 消费端；局部、全量、CI、发布分别绑定实际版本和结果。

### 2. 哈希不能替代可读取的验证摘要

[Task 2 收尾](https://github.com/MaginaLW/ai-agent-dotfiles/blob/3a2ff6b7cfec62d28eb72aeaf6c14269eed947ab/STATUS.md#L2309)
与 [Task 3 收尾](https://github.com/MaginaLW/ai-agent-dotfiles/blob/3a2ff6b7cfec62d28eb72aeaf6c14269eed947ab/STATUS.md#L2384)
保留了套件总数、部分用时及摘要哈希，但记载摘要文件已删除。
现有 [test-run-summary Schema](https://github.com/MaginaLW/ai-agent-dotfiles/blob/3a2ff6b7cfec62d28eb72aeaf6c14269eed947ab/schemas/test-run-summary.schema.json#L6)
没有被测 commit/tree 字段；[DiscoveryHash](https://github.com/MaginaLW/ai-agent-dotfiles/blob/3a2ff6b7cfec62d28eb72aeaf6c14269eed947ab/scripts/test-runner-common.ps1#L231)
绑定套件名称集合，不绑定代码或测试内容。两者都不足以标识完整的被测状态。

已扩充[收尾观察提纲](effect-observations.md#下一批真实工作如何观察)：保存可读取、脱敏的
逐检查摘要及定位，关联命令、环境、被测版本和 dirty 范围；分清“可复核 / 仅项目记载 /
缺失”。在原有获准位置留存，不引入采集器；历史材料缺失不自动重跑或回填。

### 3. 套件数增加仍可能伴随回归退出

[Task 2 的测试迁移记录](https://github.com/MaginaLW/ai-agent-dotfiles/blob/3a2ff6b7cfec62d28eb72aeaf6c14269eed947ab/STATUS.md#L2286)
明确将 content-aware dry-run/drift/apply/prune 回归移到 `tests/helpers/`，由 Task 5
接续，当前 `sync.tests.ps1` 不调用；[对应断言](https://github.com/MaginaLW/ai-agent-dotfiles/blob/3a2ff6b7cfec62d28eb72aeaf6c14269eed947ab/tests/live-plan.tests.ps1#L265)
也固定了不调用的状态。这是已记录的验证范围变化，不能被“发现的全部套件通过”覆盖。
这并不否定新增备份回执测试的价值，也不直接推断原行为已经出错。

已在指南、观察提纲和[规则片段](../../examples/adoption/project-rules.md)加入发现范围审阅：
列明新增、停用、改名或移出的检查、替代验证及恢复归属；必需检查不得静默退出。

### 4. 实际耗时、超时预算和返工需要分开

[Task 2 预算说明](https://github.com/MaginaLW/ai-agent-dotfiles/blob/3a2ff6b7cfec62d28eb72aeaf6c14269eed947ab/STATUS.md#L2304)
同时写了约 86 秒和超过 90 秒上限，数值自相矛盾，不能直接作为真实超时证据。
后续记载 sync 实际 63 秒、预算 240 秒；Task 3 记载备份回执约 20.5 秒、预算 300 秒，
CI 总上限从 305 调到 310 分钟。配置上限不是实际整次运行耗时，更不是人的工作时间。

已在观察方法中分开预算、实测值、计量范围、来源和失败/重试原因；数值冲突保留疑点。
模型、费用、人时及独立审核缺乏可核实来源时用 `unknown`，不从产品名或运行时间推算。

### 5. 接手先看当前摘要，命令必须带用途与前提

固定快照的 `STATUS.md` 已有 2,777 行，含多个历史验证窗口与新收尾；
[当前路线入口](https://github.com/MaginaLW/ai-agent-dotfiles/blob/3a2ff6b7cfec62d28eb72aeaf6c14269eed947ab/STATUS.md#L2741)
和历史全文应按需读取，不能只凭较早的完成声明判断最新状态。
窗口内还曾通过 [`00ca8bf`](https://github.com/MaginaLW/ai-agent-dotfiles/commit/00ca8bf)
修正入口里的裸 `sync` 用法，说明命令名称不能替代对用途、写入范围和隔离前提的核对。
这些是交接风险线索，不是已经量化的上下文或人时浪费。

已加入五行[当前工作摘要示例](adoption.md#真实任务的执行与收尾)，并更新
[ZCode 首轮提示词](../../examples/adoption/zcode-pilot-prompt.md)：从原有权威入口获取候选
版本、脏状态、当前工作、未验证项、准确命令和证据指针，再展开相关历史；不新增第二份
权威进度表，不覆盖追加式历史。

## 本轮落地边界

五项均落实为本仓的接入方法、观察提纲和可复用示例，并接入文档索引。
没有修改目标项目、修复其 CI、恢复其暂停的回归、安装全局规则或更改测试门禁。
既有历史观察不变；本仓的新验证不能补齐目标项目的历史证据。后续在 ZCode 的正常任务中
采用这些方法，需要从更新后的示例按项目规则适配，不会自动同步到已经接入的外仓。

阶段三仍按[进入输入](../implementation/phase-03-entry-inputs.md)单独评估：这次反馈不冻结
telemetry contract，不增加自动采集、模型路由或新的批准步骤，也不授权进入阶段三。

## 后续决定：按任务收尾形成闭环

2026-09-09，项目所有者随后要求将改进应用回试点，并选择“每次任务收尾触发”。
后续执行[反馈闭环](feedback-loop.md)，由 `ai-agent-dotfiles` 的 `docs/ZCODE.md` 记录实际应用的上游
版本和接手入口。上文“不会自动同步”保留为首次反馈提交 `9f73b7e` 的交付边界，
不表示以后只收反馈、不回灌；新机制仍没有后台传输或无需核对的整文件覆盖。
是否在后续真实任务中实际执行、是否有效，须继续以新的任务记录验证，不提前写为成功。
