# TASK-0052 PR43 continuation review package

## 审核目标

审查固定基线 `7b940bf67743673755ac872ed6ff32e9d1d87ca1` 的 PR43 接续发布。
本任务仅追加自身治理记录；测试夹具修复已单独 task-free 提交。

## 背景

TASK-0051 的本地 Windows V1 和独立审核通过，但真实 Linux required CI 失败。
旧任务按 scope_expanded 保留为 BLOCKED；新任务继续原 PR，不修改旧规格或证据。
所有者明确批准、充分授权持续完成；技术审查和各动作批准分别记录。

## 代码地图

最初交付为 tools/runner/RunnerInspection.psm1、tools/evidence/selection_review.py
及对应测试/说明。最新 `7b940bf` 只给 tests/unit/test_runner_inspection.py 的一个
disk-probe 合成场景加入 6 行 fixture 适配。TASK-0052 只允许自己的账本文件。

## 语义变更

生产代码不变。该测试在任意宿主上使用 Windows 词法构造合成路径；模块内 Join-Path
负责词法拼接，进程内 global Join-Path 抛错哨兵确保没有意外回到宿主盘查询。
全部原参数与断言保留，没有跳过失败场景。其他测试不受此子进程内函数影响。

## 风险

旧 CI 为 3 failed / 2233 passed / 2 skipped，失败发生在不存在 C 盘的 Join-Path，
尚未进入磁盘断言；不能用此前 Windows 成功掩盖该 Linux 失败。新 Linux 结果必须
由新候选 required CI 给出。Task-local 零可执行差异不代替累计生产代码覆盖。
既有路径检查不保证恶意并发文件系统隔离，选材预检不认证身份或产生 Gate。

## 证据

已验证：`7b940bf` 的 9 个 disk 参数与完整 runner 156 项通过，Ruff、format、strict
mypy、whitespace 通过；移除模块局部适配器的内存反例确实触发宿主哨兵退出 1。
没有本地 Linux 环境，没有将 Windows 复核称作 Linux 验收。

原生产工具/core blob 与 `2393c67` 完全一致。该固定源码完整质量记录为 2238 passed、
含三个 Python 工具总覆盖 88.8607%（9445/10629）、累计差异覆盖 99%（203 行、缺 1）。
这是该原版本的累计生产覆盖，测试文件变更另由本轮目标验证、新正式 V1 和新 CI 覆盖。
旧 TASK-0051 原始 V1、20 日志、设计/实施审核、已执行动作和失败 CI 全部保留。

未验证：本包创建时新正式 V1、独立实施审核、code/action 批准、Gate、最终 required
CI 和 merge 尚待实际完成。不会因为旧测试或旧批准存在而认为新候选已完成上述步骤。

## 审核问题

- 新测试是否保留原断言并隔离宿主路径查询，而未放宽生产边界或测试验收？
- 原生产覆盖、修复测试、本任务正式 evidence 与最终 CI 是否分别绑定正确版本？
- 旧失败是否保留，后续每次外部动作是否重新检查目标、期限、保护和精确 head？

## 推荐结论

APPROVE。现有局部验证支持继续正式检查；实施与发布的后续事实由对应真实记录决定。
E3、外仓写入交接、后续条件阶段及 TASK-0028 选项 C 保持原边界。
