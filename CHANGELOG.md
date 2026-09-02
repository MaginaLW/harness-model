# Changelog

本项目使用语义化版本。`0.1.0` 与 `0.2.0` 均固定本地可安装、可审计的源码基线；不代表
package 已发布到外部 registry。

## Unreleased

### Added

- `aiflow verify <TASK-ID> --abandon --actor <ACTOR> --reason "<WHY>"` 为被中断的验证运行提供确定性收尾：把没有产出任何结果的运行如实记为失败并迁移到 `FAILED`，随后按既有 REC-04 路径重试。此前一轮被中途终止的验证会把任务永久卡在 `VERIFYING`——`verify` 只接受 `IMPLEMENTING` 或重启状态，`begin` 只接受 `READY_TO_IMPLEMENT` 或 `FAILED`，唯一可达出口是抬高路由的 `escalate`。作废只追加事件并迁移状态，不写入、不修改也不删除任何 evidence 或运行日志；它不与 `--check`、`--finalize`、`--ci` 组合，要求非空 `--reason`，并拒绝任何不处于 `VERIFYING` 的任务，因此已经记录结果的运行不会被覆盖。对应恢复条目见故障恢复手册 REC-11。

### Fixed

- 修复 CI 任务解析在 base 分支前移后无法唯一确定任务的缺陷。`tools/ci/resolve_task.py` 原先用两点 `git diff base head` 比较两棵树，一旦 base 合入了另一个任务的记录，该任务目录会作为 head 侧变更出现，解析随即以「must identify exactly one .ai/tasks/TASK-* directory」失败——即使 head 完全没变。改为以 merge-base 起算的三点 `git diff base...head`，只反映本 PR 引入的变更。显式 `AI_FLOW_TASK_ID` 的优先级、零个或多个任务目录的拒绝路径与原错误文案均不变。

- active Policy 升至 `2.2.0`，将 V1/V2 完整回归与 coverage XML 的时限分别调整为 900 秒和 1200 秒，并将 `ai-quality-gate` job 上限调整为 90 分钟以覆盖 68.5 分钟的 V2 最大固定串行预算及安装、Gate 和 runner 波动；检查集合、命令、parser、required 状态、85% 总覆盖率和 90% diff coverage 门槛均保持不变。
- 修复正式 `pull_request` CI 在 detached SHA checkout 下的 branch binding：仅在 governance detection 后为 formal path 创建/覆盖以 `github.head_ref` 命名、显式指向 event head SHA 的 runner-local 分支，并校验前后 SHA/branch 与 ref 格式；不 fetch、不 push，bootstrap path 不变。
- 修复 hosted runner 的临时根不一致：仅 formal `Verify`/`Gate` 将 Python `TMPDIR` 显式绑定到 `${{ runner.temp }}`，使 run、evidence、Gate 与 artifact 同根；CLI strict-descendant 与 output containment 约束不放宽，bootstrap 和其他步骤不变。

## 0.2.0 - 2026-08-30

### Added

- 采用 MIT License，并以 PEP 639 的 `MIT` SPDX expression 和显式 license file 发布包元数据。
- 完成阶段二 Chapters 8–13：结构化 design/implementation review、V2 两阶段 evidence、独立 verifier、acceptance/integration、五项定向变异、运行期 observation、受限 Hook/CLI/CI parity 和真实 REVIEW 自举闭环。
- 新增阶段二六项输入验收矩阵、可重放证据索引、最终验收报告，以及 same/empty actor、survived mutation、越界升级和 stale review 的 fail-closed E2E。
- 新增阶段三进入输入；明确内部记录口径、真实 V3 用例和统一 telemetry contract 仍未满足，因此不授权阶段三实现。

### Changed

- 总体状态完成为 13/13 chapters、77/77 tasks、408/408 steps、24/24 exit checks；Quickstart 和 Recovery 增加历史/current readiness 区分、阶段二重放与矩阵漂移恢复。
- 阶段二历史验收完成时继续使用 package version `0.1.0`；本次审查收口由项目所有者将当前源码包提升为 `0.2.0`，明确结束 bootstrap 自举，并授权合并后创建 `v0.2.0` tag 与 GitHub Release；不发布 package registry。
- 自举 CI 改用固定 `uv 0.12.5` 验证并消费 `uv.lock`，以一次带分支覆盖率的完整 pytest 同时执行 85% 总覆盖率、90% diff coverage、PR 范围 whitespace、Ruff、format 与 mypy 门禁；普通 V1/V2 CI 复用同一锁定环境。
- 移除 bootstrap 标记并恢复正式 AI Flow 自用治理；退出 PR 继续依据目标分支的 active 标记执行质量门，后续 PR 在不更换 required check 名称的前提下进入 task resolution、`verify` 与 Gate。

### Fixed

- `aiflow status` 现在区分事件重放得到的历史 lifecycle state 与当前 `merge_readiness`；当 `APPROVED_FOR_MERGE` 的 classification、evidence 或 REVIEW approval 已失效时，明确报告 `reverification_required`，不再把唯一缺失条件显示为 `external_merge`。
- 将 `ai-quality-gate` 的总时限从 15 分钟提高到 35 分钟，覆盖历史 V2 约 20.5 分钟的实际验证时长及安装、Gate 和 runner 波动；修正阶段二 design/plan 与 Chapter 12 的完成状态漂移。
- Quickstart 与当前阶段二证据索引的手工 coverage 重放现在把 `.coverage` 与 XML 写入独立临时 run directory，并执行 85% 总覆盖率与 90% diff-cover 门槛；历史实施目录明确标注旧简写命令不可直接重放。
- 真实 Linux PR CI 现在按 TASK-0025 原始 CRLF 工作树条件重放历史 snapshot；clean-checkout 在 uv 环境不含 pip 时使用锁定工具链中的 uv 离线安装，并把 Actions 的 detached checkout 投影为绑定同一 SHA 的本地测试分支；平台专属进程与文件锁 API 保留运行时分支，同时可通过 Linux mypy；Quickstart 的 uv 依赖检查不再假定环境内存在 pip。
- GitHub workflow 的 checkout、Python 与 uv setup actions 已升级到官方 Node 24 运行时版本，消除 hosted runner 的 Node 20 弃用兼容警告。

### Known limitations

- TASK-0028 的 H1 REVIEW/V2/CI/Gate 只对原 subject/attestation 有效；当前记录正确为 `reverification_required`，阶段完成状态不刷新其 approval/evidence。
- actor 仍是 task-local 审计标签，不是人员、模型或外部身份认证；负向 mutation E2E 隔离 consumer 语义，完整 binding 由 integration/self-hosting suite 覆盖。
- 未证明跨平台 live Hook、所有客户端、IDE/GUI/remote Git、自由 shell、通用命令拦截或 OS sandbox；未实现 V3、模型路由、信任度、费用优化、资源调度或编排器。
- 除历史 single-use action 批准和范围明确的精确 task-owned worktree/OS-temp cleanup 外，不删除仓库或业务数据；本次所有者授权覆盖收尾分支 push、PR、`main` 保护、bootstrap 退出、PR 合并、`v0.2.0` tag 与 GitHub Release，不授权 deploy、凭据导出、付费调用、package registry publish、远端分支删除或其他外部动作。

## 0.1.0 - 2026-08-21

### 交付能力

- 唯一任务记录、事件重放和受控状态迁移。
- 基于可执行 Policy 的 AUTO、ASK、REVIEW、BLOCK 决策单元分流与 V0/V1 验证。
- ASK 选项/决定、REVIEW 规格/代码/单次动作批准，以及有证据的 BLOCK 恢复。
- 文件范围、禁止动作、commit 版本绑定、失效规则、统一 verify 和只读 Gate。
- GitHub Actions/工具薄适配层、本地/CI 一致门禁契约和脱敏 evidence。
- 可重放的 AUTO、ASK、REVIEW、BLOCK 黄金场景与四个隔离真实试点。
- Quickstart、八类故障恢复手册、十二项验收矩阵和干净检出端到端测试。

### 明确非目标

- 未实现 V2/V3、验收/变异测试编排、独立 Verifier 或多模型交叉验证。
- 未实现真实模型路由、信任度自动更新、资源调度或独立编排器。
- 未自动执行 push、merge、deploy、delete、package publish 或其他外部动作。
- 未宣称已在外部 GitHub 仓库启用分支保护；阶段一交付的是 workflow 和配置清单。

### 已知限制

- 阶段一验证强度只有 V0/V1，高风险工作仍必须 BLOCK 或等待后续能力。
- ASK 选项的实质语义差异仍需人工审阅；CLI 只强制结构和决定留痕。
- 初始决策单元的详细分类事实目前需在首次 classify 前写入 task record。
- Windows 无符号链接权限时，三个逃逸防护测试会显式 skip；其他平台约束测试仍执行。
- 阶段一试点是本地受控分支/worktree，没有验证 push、合并、部署或 package registry 行为。

### 从 0.1.0.dev0 迁移

- CLI 命令和参数保持不变；`python -m aiflow --version` 现返回 `0.1.0`。
- `.ai` Schema 和 Policy 仍为 `1.0`/`1.0.0`，本次无 task artifact 数据迁移。
- 旧 task 记录可读，但代码、spec、Policy 或 subject commit 变化后必须按原规则重分类/冻结/验证/批准，不得复用 stale evidence。
- 安装方式为 `python -m pip install -e ".[dev]"`；本地版本固定不授权发布 package。
