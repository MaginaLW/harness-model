# TASK-0052 发布及关闭记录

[PR #43](https://github.com/MaginaLW/harness-model/pull/43) 于 2026-09-22T11:08:56Z 普通合入 main，
合并提交 `48bf777106b9fdfef1ddf83d3abc95859fb8e580`。核对真实远端后只关闭一次：MERGED、Missing: none。

## 固定版本与验证

- 工具源码：`2393c672e72d7f27fbfd8042e3ca51a99affadc2`；随后只有一处已审文档澄清。
- 正式 subject/base：`7b940bf67743673755ac872ed6ff32e9d1d87ca1`；正式执行 HEAD：`b9fac3872e803a078a7d7030ecd3677fec62b16f`。
- 受检发布 head：`45a220f33cd0af4eda18f86896321f02bf8d62d8`；实际远端基线：`ae0e3d3fb070d1fa00ff25b086d8a49e9d222db9`。
- 原始 V1 evidence SHA256：`11bc835dee1a2b1c10ac5f9f5240db1baeaeae6f5e09009843e4f957b54830da`。

独立干净源码检查 2238 passed，含三个 Python 辅助工具的行及分支总覆盖率
88.8607%（9445/10629），累计差异覆盖 99%（203 行、缺 1 行）。Ruff、format、
内核及工具 strict mypy、whitespace 全通过。PowerShell 行为另由真实子进程测试验证，
不纳入 Python 行覆盖。初版质量运行因审查发现 PSDrive 问题中止，原日志保留且不算通过；
最终修复及独立前后反例已核对。

正式 V1 十项必需检查均通过，无超时；单元 1600、全量回归与覆盖率轮各 2238 passed，
核心覆盖率 88.1167%（8520/9669）。任务仅追加治理文件，subject 按现有规则保留任务
基线；该零可执行差异不替代累计工具覆盖。独立设计 REV-0001、实施 REV-0002 通过，
代码批准后本地 Gate 为 passed。源码、正式验证和动作证据分别绑定，不混用摘要口径。

精确发布 head 的 required CI run `35718869675`、check/job `106716773595`
成功，名称 ai-quality-gate、app 15368。Linux 为 2236 passed、2 Windows-only skips，
核心覆盖率 88.03%；Ruff、format、mypy、whitespace 通过。远端 CI 差异无核心可执行行；
维护模式 Verify and Gate 为 skipped，本地正式 V1/Gate 单独提供证据。

## 保留的失败与修复

原 TASK-0051 在发布 head `587dcb0` 的 Linux CI 出现 3 failed / 2233 passed /
2 skipped，因测试 fixture 调用真实 Join-Path 查询不存在的 C 盘，未合并。原始 CI、
Windows V1、批准和已执行两动作完整保留；该任务按 scope_expanded 保持 BLOCKED。
独立 task-free 提交 `7b940bf` 只加入 6 行测试路径适配及宿主查询哨兵，原断言及
参数均保留，生产 tools/src 与 `2393c67` 的 blob 完全一致。9 个相关用例、完整
runner 156 项、Ruff/format/strict mypy/whitespace 通过；本任务重新执行完整 V1
和新候选 Linux CI，不把旧失败覆写或倒记为 TASK-0051 合并完成。

## 实际动作与范围

push、PR 正文更新、merge 逐项登记当前所有者明确指令对应的动作批准，绑定精确目标、
head/base、参数、期限和单次意图。每个实际写动作紧前重新检查远端及期限；保留三次
命令参数、stdout/stderr、退出码和回执。全部在授权窗口内执行，未强推、删分支或绕过保护。
这些是执行者核对事实，不表示通用 Gate 或 wrapper 已具备可信原子消费能力。

required check 严格模式、enforce admins、禁止强推及删除等保护与基线相同；合并父提交
恰为上述 base 与 head，合并树等于候选树，正式 subject 和工具源码均为祖先，之后才 close。
自正式基线起只修改 TASK-0052；累计远端范围另核对 33 个既有文件（包括 TASK-0051 失败记录），旧 TASK-0050 仅追加
既有真实关闭记录。三个用户草稿未纳入候选，历史批准、事件、失败和被中止日志均保留。

本地账本共 51 项：42 MERGED / 8 BLOCKED / 1 APPROVED_FOR_MERGE。TASK-0028 选项 C、
七项更早 BLOCKED 及被接续的 TASK-0051 失败、外仓写入交接、自然双产品 E3 和后续条件阶段保持原处置。
本轮没有服务生命周期、provider 或外仓业务验收结论。

动作批准、执行回执、关闭事件及本文件是发布后本地追加，不在上述受检 PR head 内；
不递归派生另一轮发布。原始日志和移交材料保存在树外，最终包以独立读回结果为准。
