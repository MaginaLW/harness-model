# TASK-0051 发布审核包

## 审核目标

裁决这次 runner 路径修复与证据选材预检的正式发布。TASK-0051 自基线
`8bdbcc07052fe7210a9d8fe7b4f6a240ad7a66f6` 起只修改自己的治理记录；远端累计范围从 `ae0e3d3`
起另有 16 个既有文件，含已关闭 TASK-0050 的真实追加记录，不复用其批准。

## 背景

所有者当次要求继续后续任务两小时，此前已明确批准并充分授权持续完成。
维护模式允许 tools/tests/docs task-free；真实 push、PR 创建及 merge 仍由本独立
AI Flow 任务前瞻治理。此处的技术审查、CLI 状态与所有者方向/动作授权分别保留。

## 代码地图

既有源码：`tools/runner/RunnerInspection.psm1` 与对应单元测试/健康检查说明；
`tools/evidence/selection_review.py` 与对应单元测试/移交说明。预检复用 bundle
安全路径和限额；runner 的 JSON、路径状态与固定 native probe 共用路径观察器。
本任务仅新增 `.ai/tasks/TASK-0051/**`，禁止在此任务内再改上述实现。

## 语义变更

runner 在文件元数据读取前拒绝非本机/未确认盘，核对原生盘与 PowerShell PSDrive
Root 一致性，然后从根逐级检查；遇到 reparse 立即停止。磁盘余量只读已确认本机根。
选材预检只处理显式 evidence 引用和 producer/staged 映射，识别漏日志、漏原件、
仅 CRLF 差异和实质冲突，不自动补选、修改原件、认证 Git 身份或执行 Gate。

## 风险

初版独立审查安全复现了 PSDrive 命名空间错配；向前修复后，同一反例由接受变为
拒绝且零文件元数据访问，普通本地对照仍通过。初版 full-quality-001 已中止，
部分日志保留且不算通过。路径检查不提供抵御恶意并发替换的文件系统隔离。
task-local 零可执行差异不能替代累计源码覆盖。远端最终 head/base、保护或 required
check 改变时，停止对应动作并重新核对。原工作区三个用户草稿不属于发布候选。

## 证据

已验证：固定源码 `2393c672e72d7f27fbfd8042e3ca51a99affadc2` 的干净检出完成 2238 项测试；含内核及三个可选
Python 工具的总覆盖率 88.8607%（9445/10629），累计差异覆盖率
99%。Ruff、format、内核及工具 strict mypy、whitespace 均通过。
PowerShell 行覆盖不由 Python XML 证明，其行为由真实 PowerShell 子进程测试验证。
其后的提交只澄清一处 Get-PSDrive 文档措辞，源码与测试 blob 未变并单独检查 whitespace。

两组技术交叉审查已完成且无未解决发现；最终 runner+discovery 208 项兼容测试通过。
真实 Task50 88 项选材得到 10 checks / 20 日志引用与四份匹配的 CRLF 原件；明确漏选
日志和原件的两个变体分别准确报缺项，历史原件摘要未变。修复后真实 Windows 空 PATH、
缺项、错版与 UNC 拒绝四场景通过。Task49 历史 43 项选材也经只读引用预检。

未验证：本包创建时 TASK-0051 正式 V1、独立实施审查、code/action 记录、本地 Gate、
最终远端 CI 和真实合并尚待依序完成；只有后续实际记录能更新这些状态。无新增服务
生命周期、外仓验收、双产品 E3、provider 或后续阶段完成结论。

## 审核问题

- 固定源码、当前 task、累计远端范围及受检版本是否对应各自证据？
- PSDrive 修复是否关闭了可复现问题且未把 mock/同产品审查冒充外部真实验收？
- 发布前是否分别满足当前批准、Gate、精确 required CI 与保护要求？

## 推荐结论

APPROVE。已完成的设计和源码验证支持继续本任务；正式实施批准和每项实际外部动作
仍须在其对应证据与当前 CLI 条件满足后执行，不由本推荐自动获得完成结论。

## 正式 V1 追加事实

正式 V1 于 2026-09-22T10:05:28Z 完成，十项 required checks 全部 passed / exit 0，
无超时。单元 1600 passed，全量回归与覆盖率轮各
2238 / 2238 passed；核心覆盖率独立复算
88.1167%（8520/9669），任务内差异无可执行覆盖行。累计工具覆盖继续
使用前述独立源码证据，不混用口径。

正式 subject 与 base 均为 `8bdbcc07052fe7210a9d8fe7b4f6a240ad7a66f6`，执行时已提交 HEAD 为
`1e480afa1f5e0ea90f3709064d940df3c5029f7c`。CLI 按现有规则把此后仅 TASK-0051 治理文件的提交视为 attestation，
因此保留原 subject；这不是未提交源码或手工改写绑定。完整范围和工作区由正式 scope
检查及单独累计范围审查核对。原始 evidence SHA256 为
`a8344c31b77d1dc172f10e33f7eaaa1db7b81e952e43b4e61de2daaf0cae1b3d`，二十份原始 stdout/stderr 日志保留。

上文“未验证”的正式 V1 项现由此实测结果更新；本包追加时实施技术审查、code/action
批准、Gate、最终远端 CI 及合并仍须各自完成。其他场景与条件阶段边界不变。
