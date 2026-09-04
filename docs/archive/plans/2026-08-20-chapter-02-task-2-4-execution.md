# Task 2.4 执行计划

**目标：** 实现数据化状态图、封闭非状态事件、严格事件重放，以及事件已追加但物化任务替换中断后的自动恢复。

**授权与绑定：** 用户要求持续推进并按大块提交。本计划绑定基线提交 `a2b4fcc0a7f7f84053581b3ff241e2abbc2965fd`、实施目录与 MVP 设计当前摘要，以及 Task 2.1—2.3 已验证产物。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: 状态转换影响全部后续治理门；使用静态黄金转换夹具、逐边测试和中断恢复测试，不增加独立审计层。
- allowed scope: `src/aiflow/state.py`、`src/aiflow/task_service.py`、`tests/unit/test_state.py`、`tests/fixtures/state/transitions.json`、本计划及进度状态。

## 实施边界

1. 以不可变映射定义允许边、事件类型和前置条件类别；黄金夹具独立手写。
2. 普通转换 API 拒绝自循环；`task_created`、`spec_frozen`、`approval_recorded`、`evidence_generated`、`state_recovered` 只由封闭非状态事件 API 创建。
3. 重放严格检查 Schema、连续序号、前态链和合法事件，返回确定终态。
4. 持久化顺序为：生成新任务和事件、写 staged task、追加并 fsync 事件、替换 task；替换失败保留事件。
5. 读取发现事件终态领先时，修复物化状态并追加 `state_recovered`，不丢弃合法事件。

## 退出检查

```powershell
python -m pytest tests/unit/test_state.py -q
python -m pytest -q
python -m ruff check .
python -m ruff format --check src tests
python -m mypy src
git diff --check
```

完成后提交实现与测试，再记录绑定该实现提交的完成证据并推进 Task 2.5；不实现 begin/close CLI。
