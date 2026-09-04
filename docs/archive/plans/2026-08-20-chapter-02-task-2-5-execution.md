# Task 2.5 执行计划

**目标：** 实现受状态、规格、分类、批准和 Git 基线约束的 `begin`，以及只记录已发生外部合并的 `close`。

**授权与绑定：** 用户要求持续推进并按大块提交。本计划绑定基线提交 `fa7f342`、实施目录与 MVP 设计当前摘要，以及 Task 2.1—2.4 已验证产物。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: begin/close 改变治理状态，但所有 Git 操作均只读，close 不执行 merge；以隔离临时仓库集成测试验证。
- allowed scope: `src/aiflow/cli.py`、`src/aiflow/task_service.py`、`tests/integration/test_begin_close_commands.py`、本计划及进度状态。

## 实施边界

1. READY begin 必须存在 `spec_frozen`、完整当前分类、所需 REVIEW spec 批准，并保持仓库 ID、HEAD 和业务脏路径基线。
2. FAILED retry 必须给出理由；失败事件标记范围扩大、新依赖、新权限、不可验证或高风险副作用时拒绝并要求 escalate。
3. close 仅允许 APPROVED_FOR_MERGE，使用参数数组和十秒超时验证 commit 对象存在，只追加 `merge_recorded`，不运行 merge、push 或远程 API。
4. 覆盖正常 begin、缺规格、无效批准、业务 Git 漂移、普通重试、必须升级、提前 close、未知 commit 和成功 close。

完成并通过定向、全量、Ruff、格式、mypy、diff 检查后提交实现，再记录绑定提交的完成证据并推进 Task 2.6。
