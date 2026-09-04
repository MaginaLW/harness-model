# Task 4.1 执行计划

**目标：** 建立统一、可解释的工作流前置条件模型，实现规格完整性检查、稳定摘要与 `aiflow freeze`。

**授权与绑定：** 用户要求按章节持续推进并逐章完成。本计划绑定基线提交 `6560f5d4bce1f2fb57888abf561630a71929598f`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: 规格摘要和统一前置条件会成为后续 answer、approve、begin 与 verify 的治理基础，需要契约测试和累计回归，但不增加额外审核层。
- allowed scope: `src/aiflow/workflow.py`、`src/aiflow/specification.py`、`src/aiflow/cli.py`、直接相关的 task/schema/state/storage 修正、`tests/unit/test_workflow.py`、`tests/unit/test_specification.py`、`tests/integration/test_freeze_command.py`、必要 fixture、本计划及 Chapter 4/总体状态/README。
- forbidden actions: 不推送、不合并、不部署、不调用真实外部动作；freeze 不得隐式批准或改变 route。

## 完成边界

1. 每个工作流条件返回 `pass/fail/not_applicable` 和稳定原因码，失败按安全优先级稳定排序。
2. 规格七个必需节存在且非空，拒绝占位符、不可执行措辞和仅空复选框验收条件。
3. `aiflow freeze TASK-ID --actor ID` 在允许状态规范化规格、写入摘要与时间并追加可重放事件，不改变 route 或审批状态。
4. 规格直接编辑可确定性检测；显式重新冻结生成新事件，并为后续批准失效提供版本边界。
5. 定向测试、CLI help、全量相关回归、Ruff、Mypy 与 diff 检查通过后完成 Task 4.1 并本地提交。
