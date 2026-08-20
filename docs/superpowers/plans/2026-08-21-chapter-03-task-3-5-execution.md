# Task 3.5 执行计划

**目标：** 实现 `aiflow classify` 的确定性分类、完整记录、受控状态推进、幂等性和无授权降级保护。

**授权与绑定：** 用户要求持续推进直至完成本章，并按大块提交。本计划绑定基线提交 `847a1a2a8cd0d1d24eb009e76d098b0910f71565`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: classify 同时写分类记录和状态事件，必须完整绑定 Policy、输入和 Git 提交并拒绝未授权降级；使用集成决策表和故障注入验证。
- scope change: 为保存实施目录要求的完整记录，最小扩展 classification Schema/fixtures；为符合既定 `classify→freeze→begin` 顺序，移除 `CLASSIFIED→READY_TO_IMPLEMENT` 上过早的 `spec_frozen` 条件，但 `begin` 的冻结门保持不变；新增可记录的解除事件类型。
- allowed scope: `src/aiflow/cli.py`、`src/aiflow/classification_service.py`、`src/aiflow/state.py`、`.ai/schemas/classification.schema.json`、`tests/fixtures/contracts/{valid,invalid}/classification*.json`、`tests/fixtures/state/transitions.json`、`tests/integration/test_classify_command.py`、直接相关现有测试、本计划及 Chapter 3/总体状态。

## 完成边界

1. 仅允许 NEW 初次分类、具备解除记录的 BLOCKED/ESCALATED 重分类，以及同一稳定身份的幂等 no-op。
2. 逐单元保存 route、V 等级、全部命中规则、有序解释和阻塞原因；顶层绑定 Policy 版本/摘要、输入摘要、base/subject commit 与时间。
3. 分类输入摘要仅包含稳定判定事实，排除状态时间、工作区展示字段和绝对 checkout 路径。
4. 按 BLOCK、ASK、REVIEW、AUTO 前置条件推进；任何 route/V 降级必须有具名解除/授权记录，升级自动允许但留因。
5. 拒绝仓库不匹配、未解释范围扩大、缺决策单元和损坏 Policy；分类写失败不得推进状态。
6. 四类场景、幂等、Policy/输入变化、升级/降级和写失败测试及全量质量门通过后提交并推进 Task 3.6。
