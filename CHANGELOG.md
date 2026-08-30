# Changelog

本项目使用语义化版本。阶段一仅固定本地可安装、可审计的 MVP 基线；不代表 package 已发布到外部 registry。

## Unreleased

### Fixed

- `aiflow status` 现在区分事件重放得到的历史 lifecycle state 与当前 `merge_readiness`；当 `APPROVED_FOR_MERGE` 的 classification、evidence 或 REVIEW approval 已失效时，明确报告 `reverification_required`，不再把唯一缺失条件显示为 `external_merge`。

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
