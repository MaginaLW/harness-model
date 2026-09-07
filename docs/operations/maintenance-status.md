# 维护收尾与待办

盘点日期：2026-09-07。盘点基线为 `c9343c2`；当时远端 main 经只读查询为 `1f28583`，
当时开放 PR 和 issue 均为 0。本页是当前工作入口，不替代任务账本与 Gate；
历史统计和决定保留在[原处置目录](../superpowers/plans/2026-09-03-approval-overhead-and-open-task-consolidation-directory.md)。

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

交付后固定快照 `8ee402d` 的运行账本共有 44 个 task：36 MERGED / 7 BLOCKED /
1 APPROVED_FOR_MERGE，最后一项是保留原处置决定的 TASK-0028。后续新 task 会改变数量；用
`python tools/analysis/approval_overhead.py --format text` 读取最新快照。

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

## 剩余工作与明确处置

| 项目 | 当前证据与下一步 |
|---|---|
| 本轮交付 | 上轮修复、本轮文档与维护修复已通过 PR #31 合入 main；TASK-0044、0045 的真实关闭记录已通过 PR #32 发布，不再是待实现功能。 |
| 工作区忽略规则 | TASK-0045 的仓库级 `/.claude/worktrees/` 规则已随 PR #31 合入，新克隆可继承；仅忽略根目录下的 worktree 副本，保留 `.claude/skills/` 等配置可见。验证记录见该任务的 `evidence.json` 与核查补记。 |
| ASK 义务修复 | `1033a46` 提供 4 个源码文件与对应测试的候选修复：同一单元同时命中 REVIEW 和 ASK 时不能丢失方向选择义务。当前源码仍按最终 route 找 ASK，问题存在。建议作为下一项独立任务重新移植并验证，不直接合并旧分支。 |
| TASK-0028 历史收尾 | 代码已在 main，状态仍需重验；在 `8ee402d` 的 main 上实测 Gate 有 9 条拒绝理由，旧 10 条为另一历史快照，分支上下文会影响输出。维持已有选项 C；仅在所有者选择重验或改变历史处置方式后推进，不用 `close` 绕过已记录的决定。 |
| 效果验证 | 已固定[交付后账本基线与观察方法](effect-observations.md)，但真实人工打断、耗时、返工工作量和缺陷率仍未知；尚未运行自动采集或实际效果对照。 |
| 已登记的引擎缺口 | 见下节。属于后续风险控制设计/实现，不混入本次文档与目录忽略修复。 |

ASK 候选所在的 `claude/unruffled-gates-41d3ec` 工作区仍被 Git 注册且干净，
HEAD 为 `6091b47`。其旧 TASK-0042 验证为 FAILED；main 的同号 task 是另一项
`.gitattributes` 工作，已 MERGED。必须保留这一区别，不能复用批准、证据或直接搬入账本。

旧 `musing-dijkstra-a7c360` 目录已不存在，无需删除。保留分支与试点分支用于不可变提交
引用和未合入工作，不作批量清理。本轮独立工作区保留到交付结束，不影响上轮记录分支。

## 后续风险控制缺口

以下为当前源码确认的限制，优先形成可验证的独立修复，不以“收尾”名义放宽规则：

1. `impact_categories` 可缺失，而 secrets/auth 与 CI/CD 两条硬规则使用
   `missing: no_match`，缺字段时无法捕获对应风险。
2. 生产删除与部署通过 `planned_actions` 的自由文本字面量匹配，表达和实际动作之间有缺口。
3. `freshness.py` 的 action 批准分支未接通生产消费者；现有定向变异消费路径另行实现。
4. 六个禁止自动动作以外的未知 action 在 `evaluate_action_permission` 中默认自动允许。
5. push/merge 的人工批准要求是已登记的流程边界，没有通用强制执行点。
   可信身份与执行边界须先有设计，不能把本地 actor 标签当作身份认证。

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
- `git log main..claude/unruffled-gates-41d3ec --oneline`：ASK 候选提交。
- 远端开放项、保护配置与分支位置会变化，交付前重新读取；本页的只读快照不是授权。
