# 维护收尾与待办

## 2026-09-22 PR #42 合并与本轮关闭

[PR #42](https://github.com/MaginaLW/harness-model/pull/42) 已于 08:06:49 UTC 合入 main
（`ae0e3d3`）。最终 head `1d76edd` 的 required CI 通过：Linux 2102 passed、
1 Windows-only skip、核心覆盖率 88.03%；本地含工具测试 2103 passed、总覆盖
88.58%、累计差异覆盖 96%。TASK-0050 正式 V1、独立审查和本地 Gate 均通过，
核对远端父提交、树及源码祖先后已关闭 MERGED、Missing: none。

账本现为 49 项：41 MERGED / 7 BLOCKED / 1 APPROVED_FOR_MERGE。工具与本轮 E1
诊断已发布；条件阶段、外仓交接和 TASK-0028 选项 C 保留。动作及关闭回执仅追加
本地，不递归再发布；详见 [TASK-0050 关闭记录](../../.ai/tasks/TASK-0050/publication-closeout-001.md)。
下文关于最终发布尚待执行的文字属于此前观察窗口，原文保留。


## 2026-09-22 最终源码与发布治理追加核定

证据导出边界补充修复后，固定源码 `5ecde71` 在干净检出重新通过 **2103 项测试**，
含新工具总覆盖率 **88.58%**、差异覆盖率 **96%**，七组质量检查全部通过。
工具实施维持 task-free；外部发布另由 [TASK-0050](../../.ai/tasks/TASK-0050/spec.md)
按 REVIEW / V1 前瞻执行。先前只保存授权回执的发布流程遗漏如实保留，不倒签。
PR #42 的旧候选 CI 不能覆盖最终源码；实际发布状态以后续真实回执为准。
详见[最终验证和流程纠正](local-tools-closeout-2026-09-22.md#最终源码补充核验与发布流程纠正)。
此前 2100 项、88.57% 是第一次源码检查的历史结果，以下原文保持。


## 2026-09-22 持续推进后的追加核定

[PR #41](https://github.com/MaginaLW/harness-model/pull/41) 已于 06:27:32 UTC 合入 main，
合并提交 `aeaed58`；TASK-0049 的关闭账本及入口记录现已发布，不再仅保存在本地。
该 PR 的精确 head `1c40b63` 通过 required CI：1958 项测试、88.03% 总覆盖率，
其余原质量检查通过。未重复关闭 TASK-0049。

证据移交与 I1 受控工具发现已实现并完成独立审查和干净检出验证：2100 项测试通过，
含新增工具的总覆盖率 88.57%、差异覆盖率 96%。具体工具、实际材料检查和范围见
[本轮实施与验证](local-tools-closeout-2026-09-22.md)。E1 当前窗口已形成
[登记试点诊断](pilot-evidence-review-2026-09-22.md)，其中外仓应用和 E3 仍有明确边界。
I1 的其他生命周期及后续条件阶段未因此全部完成；三个用户原稿保持原样。

以下“本轮关闭账本仅保存于本地”及“通用移交/发现方案待选”属于此前快照，
当前完成范围以本段及链接记录为准；历史原文保留。

## 2026-09-22 PR #40 合并后追加核定

[PR #40](https://github.com/MaginaLW/harness-model/pull/40) 已于
2026-09-22 06:11:51 UTC 通过普通 merge 合入 main，合并提交为 `4399352`。
精确受检 head 为 `9ab3ca4`；required `ai-quality-gate` 已通过，完整测试
1958 项通过，Linux 总覆盖率 88.03%、差异覆盖率 100%，原质量阈值保持不变。

旧待办 1（TASK-0048 关闭记录及后续文档发布）和 2（`begin` 与 spec approval
新鲜度一致性缺陷）均已通过 PR #40 完成。TASK-0048 不重复关闭；TASK-0049
已在核对真实合并、提交祖先及合并树后由 CLI 关闭为 `MERGED`、`Missing: none`。
本地账本现在为 **48 项：40 MERGED / 7 BLOCKED / 1 APPROVED_FOR_MERGE**。
详见 [TASK-0049 发布与关闭记录](../../.ai/tasks/TASK-0049/publication-closeout-001.md)。

本轮 TASK-0049 关闭账本与这次入口更新仅保存于本地，未纳入 PR #40 受检 head，
不声称远端 main 已包含这些后续记录，也不因追加回执派生新一轮发布。
TASK-0028 维持选项 C，七项 BLOCKED 不自动恢复；E1 按需、E3 等待自然双产品案例，
E4 / I1–I5 / 后续阶段继续保留原条件，详见[最新待办入口](follow-up-backlog-2026-09-22.md)。

以下同日及更早段落保留原观察时点；其中“关闭记录尚未发布”和 `begin` 未修复
已由本段更新，不再作为当前待办。

## 2026-09-22 当前核定

[PR #39](https://github.com/MaginaLW/harness-model/pull/39) 已通过 required CI 并合入
main。TASK-0048 已在本地关闭为 `MERGED`、`Missing: none`；本地账本现在为
**47 项：39 MERGED / 7 BLOCKED / 1 APPROVED_FOR_MERGE**。TASK-0028 仍需重验，
维持选项 C；七项 BLOCKED 不自动恢复实施。

核定时本地 head 为 `7eec053`、远端 main 为 `7dad5c0`。本地关闭记录尚未发布，
不属于 PR #39 的受检候选 `2dffdf0`；远端账本仍是关闭前状态。真实发布与关闭依据见
[TASK-0048 追加记录](../../.ai/tasks/TASK-0048/publication-closeout-001.md)。

后续统一见[待完成项目清单](follow-up-backlog-2026-09-22.md)：本地收尾记录发布、
已复现的 `begin` 批准绑定一致性缺陷、按需 E1 复核与真实 E3 双产品案例，以及满足
条件后才选择的 E4 / I1–I5 / 阶段三四。E2 设计和本次同仓双平台采用已经完成。
本次仅梳理记录，不启动新实施或发布；反馈仍执行无问题且无请求即 no-op。

以下各日期段落保留历史观察，其中 TASK-0048 实施中、尚未注册 Linux 和早期统计
不再描述当前状态；以本段及链接的最新清单为当前入口。

## 2026-09-20 当前核定

2026-09-20 所有者决定：两个登记试点的[反馈与回灌](feedback-loop.md)，以及 VPS 连续
回执整理，改为仅在有实质问题或用户明确请求时执行。无问题且无请求直接 no-op；
普通完成、版本差异、登记上一笔 CI 不派生新提交和验证，不递归制造回执。
原始证据与必要安全检查保留。下文 2026-09-09 的“每次收尾触发”决定作为历史保留，
当前触发规则以本段及闭环指南为准。

本轮从 `d40971a` 重新读取：当前分支为 `codex/self-hosted-runner-inventory`；
账本是 **47 tasks：38 MERGED / 7 BLOCKED / 1 APPROVED_FOR_MERGE / 1 IMPLEMENTING**。
TASK-0048 为 REVIEW/V2、`Missing: implementation_result`；TASK-0028 仍需重验，
维持选项 C。下文 46 项及“没有实施中 task”属于历史快照，不再描述当前状态。

本轮[ZCode 试点复盘与接续](zcode-retrospective-2026-09-20.md)已核对两个外仓当前
检出、回灌记录及证据缺口；不把旧 CI、目标自述或方法采纳当成当前验收。
任务 02 的最新已记录节点是 [WHPX 阶段 57](../implementation/task02-runtime-integration.md#whpx-实际启动与阶段-57-收尾)，
已经记录真实 Linux 启动；“尚未安装 Linux”仅为早期准备结论。完整 POSIX 仍保留
阶段 55 退出 124；新 boot 的低权限/挂载准入、原单项、完整门和接入仍须按该节点
顺序推进。本轮没有重查 guest 现场，不把历史运行状态写成当前在线。

本轮先完成只读复盘与本仓方法改进。外仓写入交接、真实双产品 E3、任务 02 实施结果
及阶段三准入均未因此完成；三份既有未跟踪计划稿保留，不纳入本轮提交。

首次盘点日期：2026-09-07。盘点基线为 `c9343c2`；当时远端 main 经只读查询为 `1f28583`，
当时开放 PR 和 issue 均为 0。本页是当前工作入口，不替代任务账本与 Gate；
历史统计和决定保留在[原处置目录](../superpowers/plans/2026-09-03-approval-overhead-and-open-task-consolidation-directory.md)。

2026-09-08 更新：TASK-0047 已通过 PR #35、#36 完成交付，现行 Policy 为 `2.3.0`。
下文保留原快照，并将已修复问题与仍未实现的能力分开，不把旧待办重复升级成人审。

2026-09-09 接入更新：已观察 `ai-agent-dotfiles` 接入后的真实代码任务，并将五项反馈
纳入本仓接入指南、观察方法和示例，见 [ZCode 外仓试点反馈](zcode-adoption-feedback.md)。
这是文档方法改进，不表示目标仓整链验收通过，也未启动阶段三。

2026-09-09 试点扩展：按项目所有者要求，将 `r3s-VPS` 加入后续 ZCode 工作范围，
复用该仓已有 `AGENTS.md` 与离线 Strict 入口；本轮仅只读盘点和登记，未执行该仓业务任务。
接手入口、已有修改与验证边界见[外仓试点清单](adoption.md#已登记的外仓试点)。

2026-09-09 闭环更新：所有者选择为已登记试点统一采用任务收尾触发的
[反馈、改进、回灌与再观察](feedback-loop.md)，当前包括 `ai-agent-dotfiles` 与 `r3s-VPS`。
本轮准备方法和首次接入提示词；目标仓仍由各自 Agent 在当前任务结束后持久化入口、执行
首次回灌并记录实际应用版本。不设置后台定时器，也不改变原有门禁或阶段三进入条件。

## 当前任务 02

2026-09-13 所有者已明确授权完成任务 02。完整范围、验收矩阵和当次事实见
[基础设施执行记录](../superpowers/plans/2026-09-13-runner-infrastructure-execution.md)，
运维与工具入口见[自托管执行基础设施](self-hosted-runners.md)。当前推进只读盘点、
独立回执契约和真实 Linux 环境；整体仍为 `IN_PROGRESS`。下文此前只读准备和迁移
结果均保留原观察时点，不代表本轮完整退出，也不覆盖新的执行记录。

## 已完成

2026-09-13 后续执行：[E1 核查、E2 设计与 Linux 候选准备](follow-up-preparation-2026-09-13.md)。
dotfiles 历史 Step 3 的两个固定提交已取回 37/37 成功 CI，原本地日志缺失仍保留；
私有试点在核查中已由另一任务推进 main，采用结果由其当前持有者核定。
本轮完成 E2 最小 guided 设计与树外 Linux 候选，按所有者确认保持目标只读。
E3 的双产品会话和逐项复核链仍不足，E4/E5 与阶段三/四未启动。以下旧快照保留观察时点。

2026-09-13 凌晨收尾：[9 月 12 日新增计划的统一后续入口](../superpowers/plans/2026-09-12-plan-closeout-and-next-steps.md)。
可信私有目标的 Windows runner 最小迁移已达 PILOT_PASS；完整 workflow 与 main 采用
尚未完成，具体运行资料保留本机受限交付记录。后续先准备同仓 Linux 接入，再核对正式
采用；跨 Agent 主线继续沿用 E1–E5，可独立开展最小设计。本轮仅做规划与文档收尾，
不启动这些后续阶段。下段账本、外仓 dirty 状态和分支数据保留为 9 月 12 日较早核查快照，
不替代接手时的实际读取，也不由新 CI 结果覆盖旧业务版本的验收。

2026-09-12 当前执行入口：[ZCode 试点收尾与跨 Agent 协作执行目录](../superpowers/plans/2026-09-12-zcode-review-fix-execution.md)。
本次重新核对账本仍为 46 tasks：38 MERGED / 7 BLOCKED / 1 APPROVED_FOR_MERGE；
TASK-0028 仍需 reverification，继续保留选项 C。核查起点 `68f3dcb` 相对 main `f633c03`
领先 13 个本地提交；远端没有开放 PR，PR #38 的成功 CI 只覆盖其历史 head。

两个外仓均已有实际接入与后续反馈：dotfiles 已记录应用 `68f3dcb`，最新自身进度为
36/52，但 Task 6 Step 3 全量收尾结果仍未入库核实；r3s 已记录两轮反馈和本地 Strict，
当前仍缺成功的双通道 CI 回执，且存在状态文档与 manifest 未提交修改。本次只读核查，
未重跑外仓检查或访问生产。后续先补齐各自交付证据，再利用现有独立审查案例验证
Review–Fix–Verify 交接；早期“待首次接入”描述仅保留为历史快照，不再是当前待办。

- 阶段一、二：13/13 chapters、77/77 tasks、408/408 steps、24/24 exit checks 均 completed。
  这是交付与验证状态，不代表真实人工耗时或缺陷率已经下降。
- 旧账本收敛：TASK-0008、0029、0032、0033 已有被取代或阻断说明；TASK-0040、0041、0043
  为已否决/阻断的设计，保留历史记录，不为清零数量而重新开启。
- 审批整改：B0–B2 停止，B3 已按“如实记录执行边界”解决，B4 暂缓。
  它们不是待自动执行的四章计划。
- TASK-0044：历史批准聚合修复、低干预操作入口和只读统计工具已随 PR #31 合入 main。
  合并前其记录分支 `codex/reduce-human-intervention` 的 Gate 为 AUTO/V1 PASS；
  1630 passed / 4 平台 skip，总覆盖率 87.81%，变更覆盖率 100%。
  外部交付及真实合并记录见下节，不需要新的本地 spec/code 批准。
- 本轮文档收尾：纠正状态说明中“bootstrap 标记不存在、每项变更必建 task”，
  修正处置目录顶层状态、B3 状态与 README 在途说明。
- TASK-0046：ASK 义务修复已通过 PR #33 合入，关闭记录已通过 PR #34 发布；
  REVIEW+ASK 先等待方向选择，再保留原 REVIEW 审核，BLOCK 优先级不变。
  当前状态 MERGED，Missing / Next 均为 none，不需要重新批准或移植旧候选。
- TASK-0047：显式风险类别与受控动作输入、旧正向风险兼容、pending/begin 新鲜度校验、
  未知动作默认拒绝及相关回归已通过 PR #35 合入；PR #36 已发布真实关闭记录。
  字段缺失是 Agent 可补齐的零写输入错误，不自动产生新的 ASK 或人审要求。

交付后固定快照 `2e00d78` 的运行账本共有 45 个 task：37 MERGED / 7 BLOCKED /
1 APPROVED_FOR_MERGE，最后一项是保留原处置决定的 TASK-0028。后续新 task 会改变数量；用
`python tools/analysis/approval_overhead.py --format text` 读取最新快照。

新增固定快照 `d501027` 的账本共有 46 个 task：38 MERGED / 7 BLOCKED /
1 APPROVED_FOR_MERGE。没有实施中的 task；7 条 BLOCKED 是已登记的替代、失败或否决
历史，不是待自动重启的队列。TASK-0028 仍按选项 C 保留，不能为清零而直接 close。
编号上限 TASK-0047 不等于 47 个运行账本，也不等于阶段计划中的 77 个实施条目。

## 外部交付更新

[PR #31](https://github.com/MaginaLW/harness-model/pull/31) 已于 2026-09-07 合入 main，
合并提交为 `00d1838f23d1b02b02f5b4bc0eb64fe11a2504ed`。其精确 PR head `9a2d5ee`
通过必需的 [ai-quality-gate](https://github.com/MaginaLW/harness-model/actions/runs/34108909215)：
Linux 全量 1634 passed，总覆盖率 87.80%，18 个可执行变更行全部覆盖；
whitespace、Ruff、format、mypy 均通过。未绕过保护，未删除源分支。

已核实合并提交包含 TASK-0044、0045 的 subject 与受检 PR head，并通过 CLI 为两个
任务追加 `merge_recorded` / MERGED。后续账本交付 [PR #32](https://github.com/MaginaLW/harness-model/pull/32)
也已通过自身的 [required CI](https://github.com/MaginaLW/harness-model/actions/runs/34109822587)
并合并为 `8ee402d`：1634 passed，总覆盖率 87.80%，没有新增可执行源码行。
关闭记录已进入 main；不提前关闭未来工作，也不改写旧证据。

[PR #33](https://github.com/MaginaLW/harness-model/pull/33) 已合并为 `9baa0cb`，
[PR #34](https://github.com/MaginaLW/harness-model/pull/34) 已合并为 `2e00d78`。
精确受检 head 分别为 `deb05ad`、`e10c8a3`，两次 required CI 均成功：
各 1657 项测试通过，总覆盖率 87.90%；实现有 19 个可执行差异行且全部覆盖，
关闭记录没有新增可执行源码行。TASK-0046 仅对真实实现合并执行一次 close。
重新只读查询时远端 main 为 `2e00d78`，开放 PR / issue 均为 0；这不是持续监控结果。

[PR #35](https://github.com/MaginaLW/harness-model/pull/35) 已正常合并为 `0fa7d05`，
[PR #36](https://github.com/MaginaLW/harness-model/pull/36) 已正常合并为 `65589da`。
两次 required CI 各通过 1,721 项测试，总覆盖率 88.04%；实现的 36 个可执行差异行
全部覆盖，账本 PR 无可执行差异。远端维护模式 CI 执行完整质量门，并非远端 task Gate；
实现合并前单独核对的本地 TASK-0047 Gate 为 PASS。历史 Windows V1 的 88.14% 不变。
精确 head、CI、合并时间及祖先核验见[交付记录](../../.ai/tasks/TASK-0047/review-notes.md#2026-09-07-实际合并与关闭)。

所有者随后另行要求分支清理：5 个本地、4 个远端的已合并且无工作区占用分支已删除，
提交历史、备份、试点、未合并分支与所有工作区保留。恢复映射见
[清理记录](../../.ai/tasks/TASK-0047/branch-cleanup.md)。`d501027` 是最初仅本地保存的
清理审计，本次维护文档交付包含该提交；发布须使用新的交付授权，不复用删除授权。

## 剩余工作与明确处置

| 项目 | 当前证据与下一步 |
|---|---|
| 本轮交付 | 上轮修复、本轮文档与维护修复已通过 PR #31 合入 main；TASK-0044、0045 的真实关闭记录已通过 PR #32 发布，不再是待实现功能。 |
| 工作区忽略规则 | TASK-0045 的仓库级 `/.claude/worktrees/` 规则已随 PR #31 合入，新克隆可继承；仅忽略根目录下的 worktree 副本，保留 `.claude/skills/` 等配置可见。验证记录见该任务的 `evidence.json` 与核查补记。 |
| ASK 义务修复 | 已由 TASK-0046 独立实现、完整验证并通过 PR #33、#34 交付；旧 `1033a46` 仅作为代码参考，没有复用旧任务批准或失败证据。 |
| 风险输入与动作默认拒绝 | TASK-0047 已通过 PR #35、#36 交付并关闭；无需重做已完成实现或重新批准旧代码。 |
| TASK-0028 历史收尾 | 代码已在 main，状态仍需重验；在 `8ee402d` 的 main 上实测 Gate 有 9 条拒绝理由，旧 10 条为另一历史快照，分支上下文会影响输出。维持已有选项 C；仅在所有者选择重验或改变历史处置方式后推进，不用 `close` 绕过已记录的决定。 |
| 效果验证 | 已固定[基线、方法与两次真实交付观察](effect-observations.md)：分别记录 TASK-0046、0047 的可见请求组与批准记录；人类工作分钟、同类修复前对照及成熟缺陷观察仍缺失，不宣称成本或缺陷率改善。继续在实际工作结束时追加已有事实，不为补统计新增人工请求或自动采集。 |
| 现有 AI 工具接入 | 两个登记试点已持久化闭环入口并产生后续窗口；dotfiles 的两段独立评审已成为第六项方法。按[执行目录](../superpowers/plans/2026-09-12-zcode-review-fix-execution.md)先核对当前全量收尾证据，再准备最小双工具交接。实际回灌版本以目标记录为准，不是后台同步，不宣称效率/可靠度改善或阶段三/四已启动。 |
| 已登记的引擎边界 | 下节区分 TASK-0047 已修复项与未实现的可信外部执行能力；后者需要新的设计输入，不是本次收尾遗漏。 |
| `r3s-VPS` ZCode 试点 | 已有 R1、grok/x.ai 与 fixture/CI 的目标记录；最新应用 upstream 记为 `3a0bb34`。当前重点是 CI 零步骤失败的证据收尾及两文件 dirty 边界；本地 Strict 和目标生产记载不能代替当前双通道 CI。第六项方法在下一安全收尾时评估适用性；本仓本次未执行其测试或生产动作。 |

ASK 旧候选所在工作区仍被 Git 注册，盘点时干净且处于 detached 状态，
HEAD 为 `6091b47`。其旧 TASK-0042 验证为 FAILED；main 的同号 task 是另一项
`.gitattributes` 工作，已 MERGED。必须保留这一区别，不能复用批准、证据或直接搬入账本。

旧 `musing-dijkstra-a7c360` 目录已不存在，无需删除。保留分支与试点分支用于不可变提交
引用和未合入工作，不作批量清理。`codex/maintenance-closeout` 仍被独立工作区占用，
本地和远端分支均保留；不是可在普通分支清理中顺带删除的目录。

## 风险控制项的当前处置

以下沿用首次盘点的五项编号，更新处置而不删除历史问题的来由：

| 原问题 | 2026-09-08 处置 |
|---|---|
| 1. 缺少 `impact_categories` 时可能漏识别风险 | TASK-0047 已修复：新分类要求显式风险字段，缺项零写拒绝；历史读取与严格同身份 no-op 保留，不重写旧任务。 |
| 2. 部署/生产删除仅靠 `planned_actions` 自由文本匹配 | 已增加有类型的 `controlled_actions`，并保留旧精确 token 的正向风险。分类事实仍不能证明任意真实 shell 动作，后半项是执行边界，不声称已解决。 |
| 3. 通用 action freshness 没有生产消费者 | 保留非执行性兼容接口；不接入伪授权路径。现有定向 mutation 使用独立的受控消费流程。 |
| 4. 未知 action 默认自动允许 | TASK-0047 已修复：仅 Policy 明列 `read` 可允许，未知类别默认拒绝，六项高风险继续拒绝。 |
| 5. push/merge 缺少通用强制执行点 | 仍是明确限制；每次真实外部动作须单独授权，本地 actor 不是可信身份。 |

第 2 项的真实动作证明及第 3、5 项的外部执行能力，需要先确定可信身份根、服务端授权
与原子消费、固定操作范围、凭据托管、审计和恢复边界；不能仅靠增加本地批准文件解决。
设计输入见[动作执行边界](../../.ai/tasks/TASK-0047/action-boundary-design.md)，本次不授权
选择、部署或接通新执行器，不放宽质量门禁，也不重开已否决的审批整改方案。

## 暂不进入的路线

[阶段三](../implementation/phase-03-entry-inputs.md)仍 not_started：缺少冻结的样本标准、
真实 V3 用例/沙箱回滚边界和统一 telemetry 口径。V3、模型路由、信任评分和资源调度
是后续路线，不属于当前版本的未完成承诺。本次不改变这些进入门。

## 重放入口

- `python tools/analysis/approval_overhead.py --format text`：账本快照。
- `python -m aiflow status TASK-0044`：读取当前关闭状态；合并前 Gate 需在其历史记录
  分支/版本上重放，不能将终态任务在后续 main 上的旧证据绑定当作新的待审核请求。
- `python -m aiflow status TASK-0028` 与 `python -m aiflow gate TASK-0028 --format json`：历史阻断。
- `python -m aiflow status TASK-0045`：读取本轮配置修复的关闭状态；合并前 Gate 事实
  见该任务核查补记及其记录版本。
- `python -m aiflow status TASK-0046`：读取已交付 ASK 修复的关闭状态。
- `python -m aiflow status TASK-0047`：读取风险输入修复的关闭状态；后续维护动作仅追加
  独立 action 审计，不重复关闭任务或改变其历史实现证据。
- `git log main..claude/unruffled-gates-41d3ec --oneline`：旧候选历史，不等于当前待实现清单。
- 远端开放项、保护配置与分支位置会变化，交付前重新读取；本页的只读快照不是授权。
