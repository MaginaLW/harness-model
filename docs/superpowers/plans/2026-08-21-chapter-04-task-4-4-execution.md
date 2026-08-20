# Task 4.4 执行计划

**目标：** 实现确定性的路径范围判断、Git 变更路径收集和 AUTO 运行前护栏，使自动执行只在当前冻结规格、完整配置和声明范围内开始。

**授权与绑定：** 用户要求按章节持续推进并逐章完成。本计划绑定基线提交 `5cc3835594285e3d3bb5c3d2e96eca9de93fe276`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: AUTO 前置检查决定是否允许无人值守开始，需覆盖路径逃逸、未跟踪与重命名等边界；本任务只实现确定性护栏，不扩大动作权限或降低现有 route/V。
- allowed scope: `src/aiflow/scope.py`、`src/aiflow/workflow.py`、`src/aiflow/task_service.py`、必要的 Git 邻接修正、`tests/unit/test_scope.py`、`tests/integration/test_auto_preflight.py`、直接相关 fixture、本计划和 Chapter 4/总体状态。
- forbidden actions: 不推送、不合并、不部署、不执行外部动作；不得把作用域失败静默降级为允许，也不得在代码中复制 Policy 路由表。

## 完成边界

1. 规范化仓库相对路径，采用路径段级 glob 语义，拒绝绝对路径、`..` 和指向仓库外的符号链接。
2. 收集 base commit 到 HEAD 的新增、修改、删除、重命名路径，以及 tracked/untracked 工作树变化；只排除明确的本地缓存。
3. 当前任务治理目录作为系统写入路径处理，其他任务治理路径不获例外。
4. AUTO begin 前统一检查所有未完成单元、冻结规格、批准缺失、禁止动作、作用域与验证配置；失败稳定拒绝，新增风险保持保守结论。
5. 允许路径、前缀逃逸、大小写、未跟踪、删除、重命名、符号链接、治理路径和多决策单元测试通过。
6. 定向测试、累计回归、Ruff、Mypy 与 diff 检查通过后完成 Task 4.4 并本地提交。
