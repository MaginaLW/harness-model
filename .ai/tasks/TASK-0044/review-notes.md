# TASK-0044 核查补记

## 调用方事实更正

冻结规格中的“唯一生产调用方是 CLI status”应更正为：本次改变的 `approvals` 与
`merge_readiness` 展示字段仅由 CLI 展示，未被 Gate 或执行前提用来授权。
`tools/hooks/pre_commit.py` 也调用 `summarize_task`，但只消费 `observed_head`（第 54 行）
和 `current_state`（第 80 行）；这两个字段未被本次修复改变。

核查命令：`rg -n 'summarize_task|\.approvals|merge_readiness' src tools`。
本补记纠正风险分析中的调用方表述，不改变冻结的目标、修改范围、输出契约、验收条件、
分流、验证等级或任何授权。原规格与事件保留，采用追加说明记录核查结果。

## 已完成的独立审查

独立审查确认按 REVIEW 单元和批准类型收集当前有效记录与 Gate 的覆盖语义一致，
freshness 的原有版本绑定继续生效。旧记录共存不阻断当前记录，不同单元和批准类型
不能相互替代；Gate、Policy、权限与状态转换未修改。
定向 status 回归 29 项通过，实际 REVIEW 生命周期涵盖 status/Gate 对照与只读快照。
完整验证结果以本任务 CLI 生成的 evidence 与当前 Gate 为准。

## 本地验证结果

- 实现提交：`b8cd477a1b7b96632df15b2b3cbf70d67066e6e9`。
- `aiflow verify TASK-0044 --actor codex`：AUTO / V1，10 项检查全部 passed，
  状态自动推进到 APPROVED_FOR_MERGE。
- 全量回归：1630 passed / 4 skipped，395.82 秒；带覆盖率运行：
  1630 passed / 4 skipped，480.42 秒。四项 skip 均为既有 Windows symlink 能力限制。
- 总覆盖率（含分支）：87.81%，独立运行 coverage report --fail-under=85 通过。
- 以变更前 `1f28583` 为比较基线的 diff coverage：18 个可执行变更行，100%，
  --fail-under=90 通过。
- Ruff、format、mypy、whitespace 通过；本地 Gate PASS，reason_codes 为空。
- 证据：`evidence.json`；原始日志与覆盖率数据保留于本地忽略目录
  `logs/run-20260907T043857406410Z/`。
- 本任务批准记录为 0 条；全仓批准总数仍为 119。这是本轮账本事实，不能推广为
  真实人类耗时已下降某个比例。

本轮没有执行推送、合并或远端 CI；本地通过不等于平台 required check 已运行。

## 后续外部交付与关闭

以上为本地验证阶段的历史记录。项目所有者随后明确授权推送收尾分支、创建 PR，
并在 required CI 全绿后合并。PR #31 的精确 head `9a2d5ee` 已通过远端 CI：
1634 passed，总覆盖率 87.80%，18 个可执行变更行覆盖率 100%，质量检查全部通过。

PR #31 于 2026-09-07 实际合并为 `00d1838f23d1b02b02f5b4bc0eb64fe11a2504ed`。
合并前本任务在原记录分支 Gate PASS；合并后确认该 SHA 已进入 origin/main，
且本任务 subject `b8cd477` 与受检 PR head 均为其祖先，再通过 `aiflow close`
追加真实 `merge_recorded` 并进入 MERGED。未修改旧批准、证据或历史事件。
后续 main 不再等于旧证据绑定版本，不因此对已合并任务重新请求 spec/code 审核。
