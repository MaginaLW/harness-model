# 维护收尾与待办

首次盘点日期：2026-09-07。盘点基线为 `c9343c2`；当时远端 main 经只读查询为 `1f28583`，
当时开放 PR 和 issue 均为 0。本页是当前工作入口，不替代任务账本与 Gate；
历史统计和决定保留在[原处置目录](../superpowers/plans/2026-09-03-approval-overhead-and-open-task-consolidation-directory.md)。

2026-09-08 更新：TASK-0047 已通过 PR #35、#36 完成交付，现行 Policy 为 `2.3.0`。
下文保留原快照，并将已修复问题与仍未实现的能力分开，不把旧待办重复升级成人审。

## 已完成

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
| 现有 AI 工具接入 | 已准备[轻量接入指南](adoption.md)、ZCode 提示词、可合并规则及只读仓库盘点。真实试点尚需一个具体项目与正常工作项；没有修改外部仓库、全局配置或运行付费模型。完整引擎跨仓库初始化/定位/事实录入/CI 适配是条件性产品化工作，不是轻量试点前置，也不启动阶段三/四。 |
| 已登记的引擎边界 | 下节区分 TASK-0047 已修复项与未实现的可信外部执行能力；后者需要新的设计输入，不是本次收尾遗漏。 |

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
