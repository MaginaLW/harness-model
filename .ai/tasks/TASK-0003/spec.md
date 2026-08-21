# Task Specification

## 目标

将已通过十二项验收、四个真实试点和干净检出验证的阶段一 MVP 固定为 `0.1.0`，交付可追踪的变更记录、验收报告和有证据的阶段二输入，并通过最终全量验证。

## 范围

- 版本与锁文件：`src/aiflow/__init__.py`、`pyproject.toml`、`uv.lock`、`tests/unit/test_cli.py`。
- 发布与入口文档：`CHANGELOG.md`、`README.md`。
- 验收产物：`docs/implementation/phase-01-acceptance-report.md`、`docs/implementation/phase-02-entry-inputs.md`。
- 当前任务 `.ai/tasks/TASK-0003/**` 治理记录。

## 非目标

不实现 V2/V3、独立 Verifier、变异测试、完整高风险 Hooks、真实模型路由或资源调度；不发布 package，不创建/推送 tag，不 push、merge、deploy 或 delete。

## 验收条件

1. 包内版本、项目元数据、lock 和 CLI 测试一致为 `0.1.0`，`python -m aiflow --version` 输出 `aiflow 0.1.0`。
2. CHANGELOG 记录阶段一能力、明确非目标、已知限制和迁移规则，不宣称未实现能力。
3. 验收报告汇总十二项结论、四试点、验证命令、覆盖率、CI 一致性、未验证场景和风险接受，只引用原始证据。
4. 阶段二输入仅包含由测试/试点支持的六类缺口，并明确不自动开始阶段二。
5. 实施目录指定的 install、Ruff、mypy、全量 pytest、分支覆盖率门、e2e、version、diff 和占位扫描全部通过；十二项仍全为 passed。

## 禁止动作

push、merge、deploy、delete、secret export、paid external call、package publish、tag push，以及把本地验收写成已完成外部发布。

## 错误行为

版本不一致、任一验收项 blocked、原始证据路径缺失、覆盖率低于 85%、CI/Gate 拒绝、出现无解释占位项，或报告超出已验证范围时必须失败；新行为、Policy、权限或外部动作需求必须升级。

## 回滚

版本和文档变更均由 commit 保护。若发布基线不成立，由后续获批任务显式 revert，保留本任务的失败/通过 evidence；不改写历史、删除证据或发布更高版本来掩盖失败。
