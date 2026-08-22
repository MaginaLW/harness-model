# TASK-0004 实现审核包

## 审核目标

确认阶段二独立规划、Chapter 8 初始化和单一过期 action fixture 修复符合冻结规格，且没有把规划写成已实现的 V2 或独立验证能力。

## 背景

阶段一 `0.1.0` 已完成。TASK-0004 最初仅规划阶段二；首次 V1 在 2026-08-22 发现集成测试中的固定到期时间已经失效，因此按 `scope_expanded` 升级为 REVIEW、重新分类和冻结，并取得 spec approval 后修复该 fixture。

## 代码地图

- `docs/superpowers/specs/2026-08-22-phase-02-review-verification-design.md`：阶段二边界和兼容性设计。
- `docs/superpowers/plans/2026-08-22-phase-02-review-verification-implementation-directory.md`：Chapter 8–13 实施顺序。
- `docs/superpowers/state/overall.yaml`、`docs/superpowers/state/chapters/chapter-08.yaml`：规划状态。
- `docs/implementation/chapter-08-structured-review.md`、`README.md`：入口和追踪。
- `tests/integration/test_governance_paths.py`：将已到期的成功路径 fixture 改为明确远期时间。

## 语义变更

运行时语义没有变化。规划层把阶段二标记为 planning 并固定当前仓库为首个跨模块 REVIEW 目标；测试层只确保“未到期 action 可批准”的成功用例不随日历日期失效，既有过期拒绝测试保持不变。

## 风险

主要风险是规划提前宣称 V2/独立 Verifier 已实现，或远期 fixture 掩盖到期拒绝行为。文档明确这些能力仍为后续章节；独立的过期 fixture 继续覆盖拒绝路径。未执行任何 push、merge、deploy、delete、publish 或外部动作。

## 证据

已验证：subject `bd37506518f080be0d213c1173c1063488b10574` 上 contract、scope、Ruff、格式、mypy、unit、全量回归、覆盖率和 diff coverage 全部通过；全量结果为 `584 passed, 3 skipped`，跳过项均为 Windows symlink 权限限制。定向治理/批准测试为 `9 passed`。

未验证：未验证 V2、独立 Verifier、定向变异、完整 Hooks、V3、模型路由或资源调度，因为本任务未实现这些能力；未执行任何外部 CI、push、merge 或发布。

## 审核问题

- 规划是否清楚区分 Chapter 8 与后续 V2/Gate 工作？是。
- 时间 fixture 修复是否改变生产 action 到期判断？否。
- 当前证据是否与同一 subject、spec 和 Policy 绑定？是。

## 推荐结论

APPROVE。规划边界、失败记录、范围升级、测试修复和 V1 evidence 相互一致，可批准 TASK-0004 进入最终合并就绪状态。
