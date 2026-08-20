# Task 2.6 与 Chapter 2 退出计划

**目标：** 实现严格只读的 `aiflow status` 文本/JSON 摘要，完成状态核心说明和第二章累计退出检查。

**授权与绑定：** 用户要求继续下一部分并按大块提交。本计划绑定基线提交 `0891dccfadebd3b7696b948382c01c0c8cdc7685`、实施目录与 MVP 设计当前摘要，以及 Task 2.1—2.5 已验证产物。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: status 是只读诊断，但本任务决定是否跨章；运行章节完整回归并内联完成需求与质量复核，不增加独立审计层。
- allowed scope: `src/aiflow/cli.py`、`src/aiflow/task_service.py`、`src/aiflow/status_service.py`、`tests/integration/test_status_command.py`、`docs/implementation/chapter-02-task-state.md`、本计划及进度状态。

## 完成边界

1. 摘要固定输出身份、状态、route/verification 可用性、下一事件、缺失条件、commit/Git、批准和证据新鲜度。
2. 文本与稳定 JSON 双格式；读取不修复、不更新时间戳、不写事件。
3. 覆盖 NEW、WAITING、READY、IMPLEMENTING、FAILED、VERIFIED、APPROVED、MERGED；损坏日志和物化不一致返回非零。
4. 章节说明只解释目录、原子/恢复、状态图、命令示例和排错，不复制 Policy 规则。
5. 运行实施目录 Task 2.6 的全部单元、集成、Ruff、mypy 和 diff 检查；通过双复核后提交并推进 Chapter 3 / Task 3.1。
