# Changelog

本项目使用语义化版本。`0.1.0` 与 `0.2.0` 均固定本地可安装、可审计的源码基线；不代表
package 已发布到外部 registry。

## Unreleased

暂无。

## 0.2.0 - 2026-08-30

### Added

- 完成阶段二 Chapters 8–13：结构化 design/implementation review、V2 两阶段 evidence、独立 verifier、acceptance/integration、五项定向变异、运行期 observation、受限 Hook/CLI/CI parity 和真实 REVIEW 自举闭环。
- 新增阶段二六项输入验收矩阵、可重放证据索引、最终验收报告，以及 same/empty actor、survived mutation、越界升级和 stale review 的 fail-closed E2E。
- 新增阶段三进入输入；明确内部记录口径、真实 V3 用例和统一 telemetry contract 仍未满足，因此不授权阶段三实现。

### Changed

- 总体状态完成为 13/13 chapters、77/77 tasks、408/408 steps、24/24 exit checks；Quickstart 和 Recovery 增加历史/current readiness 区分、阶段二重放与矩阵漂移恢复。
- 阶段二历史验收完成时继续使用 package version `0.1.0`；本次审查收口由项目所有者将当前源码包提升为本地 `0.2.0` 基线，不创建 tag、不发布 registry，也不移除 bootstrap 标记。
- 自举 CI 改用固定 `uv 0.12.5` 验证并消费 `uv.lock`，以一次带分支覆盖率的完整 pytest 同时执行 85% 总覆盖率、90% diff coverage、PR 范围 whitespace、Ruff、format 与 mypy 门禁；普通 V1/V2 CI 复用同一锁定环境。

### Fixed

- `aiflow status` 现在区分事件重放得到的历史 lifecycle state 与当前 `merge_readiness`；当 `APPROVED_FOR_MERGE` 的 classification、evidence 或 REVIEW approval 已失效时，明确报告 `reverification_required`，不再把唯一缺失条件显示为 `external_merge`。
- 将 `ai-quality-gate` 的总时限从 15 分钟提高到 35 分钟，覆盖历史 V2 约 20.5 分钟的实际验证时长及安装、Gate 和 runner 波动；修正阶段二 design/plan 与 Chapter 12 的完成状态漂移。
- Quickstart 与当前阶段二证据索引的手工 coverage 重放现在把 `.coverage` 与 XML 写入独立临时 run directory，并执行 85% 总覆盖率与 90% diff-cover 门槛；历史实施目录明确标注旧简写命令不可直接重放。

### Known limitations

- TASK-0028 的 H1 REVIEW/V2/CI/Gate 只对原 subject/attestation 有效；当前记录正确为 `reverification_required`，阶段完成状态不刷新其 approval/evidence。
- actor 仍是 task-local 审计标签，不是人员、模型或外部身份认证；负向 mutation E2E 隔离 consumer 语义，完整 binding 由 integration/self-hosting suite 覆盖。
- 未证明跨平台 live Hook、所有客户端、IDE/GUI/remote Git、自由 shell、通用命令拦截或 OS sandbox；未实现 V3、模型路由、信任度、费用优化、资源调度或编排器。
- 除历史 single-use action 批准和范围明确的精确 task-owned worktree/OS-temp cleanup 外，不删除仓库或业务数据；本次所有者授权仅覆盖收尾分支 push、PR 与 CI 全绿后的 `main` 保护配置，不授权 merge、deploy、凭据导出、付费调用、package publish 或其他外部动作。

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
