# Review Package

## 审核目标

决定是否接受 TASK-0005 在 subject `3c32b5cc97924cb84eafcf0702cf6f842829dd53` 上完成的 Chapter 8 结构化 design/implementation 双阶段审核实现。

## 背景

阶段一仅有八节 Markdown 审核包。Chapter 8 增加不可变、版本绑定的 review context/record 和结构化 finding，同时保留原批准、evidence 与 Gate 兼容边界。

## 代码地图

- `src/aiflow/review_service.py`：context、record、revision、freshness 与验证服务。
- `src/aiflow/cli.py`：`review context|record|resolve|show` 命令面。
- `src/aiflow/approval.py`：design/implementation review 的批准前置检查。
- `.ai/schemas/review-*.schema.json`：双阶段 context 与 record 契约。
- `tests/unit/test_review_records.py`、`tests/integration/test_review_command.py`、`tests/e2e/test_review_scenario.py`：契约、CLI 与闭环回归。

## 语义变更

REVIEW 任务的 spec approval 现在要求当前且可批准的 design record；code approval 在旧审核包和 passed local evidence 之外，额外要求当前且可批准的 implementation record。implementation context 提供 committed numstat 与验证摘要，但不复制完整 patch、日志或实现对话。

## 风险

- context 绑定不足可能允许陈旧审核支持批准。
- revision 覆写或事件选择错误可能绕过较新的拒绝结论。
- 新前置条件可能破坏阶段一 REVIEW fixture、V1 evidence 或 Gate reason code。
- diff/evidence 摘要若包含过多内容，会扩大审核数据面。

## 证据

- 已验证：TASK-0005 V1 evidence 结论 `passed`，10 个 required checks 全部 passed；完整 regression 为 `604 passed, 3 skipped`，跳过项均为 Windows symlink 条件。
- 已验证：diff coverage 90%；Ruff、format check、mypy、scope、contract 均 passed。
- 未验证：未执行 push、merge、deploy、真实外部副作用或任何禁止动作；这些也不属于本章实现范围。
- implementation context：`550b879972ad0a83a08a432277bb71db05d2e60bc44aefb609ddac2e880a6a61`。
- evidence digest：`eac6f3ac919bc8932d66e1f090a9e1161cbbffe7c086706e45bf37609f2a51ea`。

## 审核问题

- 当前实现是否满足冻结规格的双阶段互斥、不可变 revision 和 freshness 规则？
- implementation context 是否足以定位 committed diff 并复现验证，同时保持最小数据边界？
- approval、validate、旧 Markdown、V1 evidence 与 Gate 兼容性是否完整？
- 是否存在未关闭的 high/critical finding？

## 推荐结论

若独立 implementation review 未发现未关闭的 high/critical finding，建议 `APPROVE`。
