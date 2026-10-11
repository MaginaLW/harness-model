# Review Package

## 审核目标

裁决冻结规格 `0314f80d794b65e6dafdad019d1d0c7cc795af2be602a559337b4a6fa780130b` 的实现，subject `8b9fa19d64f980b022e74e159c6d04f74a0fe984`。

## 背景

项目所有者已决定退役两项未使用的入口，并明确批准按本计划推进。当前为 REVIEW/V1；结构化独立结论直接引用 `reviews/REV-0002-r0001.json` 与 `reviews/REV-0003-r0001.json`，不另存审核输入。

## 代码地图

`cli.py`、`contracts.py` 移除外部审核入口与三项专用契约；verification 和 runner 移除临时根选项专用分支；八个模块使用 `state.utc_timestamp`。专用测试和夹具删除，通用安全回归保留；文档记录退役边界与恢复提交。

## 语义变更

旧子命令和旧选项由 argparse 以退出码 2 拒绝。其余 CLI、Policy、证据、Gate、observe、Hook 与 mutation 行为保持；AGENTS 只补齐升级清单，常设授权一节未改。

## 风险

调用方需停止使用已退役入口。旧源码、契约、测试及指南可从退役前提交恢复，并重新走当前治理流程；历史任务、原失败与原始报告保留。

## 证据

- 已验证：`evidence.json` 原生 V1 的 10 项 required checks 全部 passed；共享完整测试为 1804 passed in 580.25s，覆盖率 88.49% 达到 85%，diff coverage 100% 达到 90%；Ruff、format、mypy 与 whitespace 通过。
- 已验证：旧入口拒绝、移除符号零引用、TASK-0054～0062 可读、阶段二追溯与自举回归；两份绑定当前 context 的独立实现审核均 APPROVE，零发现。
- 已验证：早期手工严格运行保留为 4 failed、1800 passed；仓库内临时夹具继承父 Git 导致失败，原始 `logs/strict-full.log` 未改写。正式 runner 在仓库外默认系统临时环境完整通过。
- 未验证：远端 required CI 与发布合并尚待后续 PR 完成。

## 审核问题

- 是否只退役指定入口，并保留通用安全回归与历史读取路径？
- 是否保持原生证据、独立审核和当前 subject 的绑定，以及全部质量门禁？
- 是否保留旧失败事实，并提供完整恢复指针？

## 推荐结论

APPROVE：两位独立 Agent 已确认实现符合冻结规格，当前原生 V1 完整通过；远端合并仍须 required check 通过。
