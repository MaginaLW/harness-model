# Task 5.3 执行计划

**目标：** 为 provisional 与最终验证建立确定性的 Git 清洁度、版本同步和完整变更范围边界。

**授权与绑定：** 用户要求按章节持续推进并逐章完成。本计划绑定基线提交 `7510aeec05413e45a2358ee0973bb6ab6552015e`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: 最终证据必须绑定一个清洁且范围合法的被审提交；provisional 可以观察脏工作树，但不能被误作 Gate 通过。
- allowed scope: `src/aiflow/git_context.py`、`src/aiflow/scope.py`、必要的 workflow/task event 邻接接口、`tests/integration/test_verification_git_scope.py`、本计划和 Chapter 5/总体状态。
- forbidden actions: 不创建业务提交、不自动改写 base commit、不生成 evidence/approval、不实现 verify/gate CLI、不推送/合并。

## 完成边界

1. provisional 明确允许业务脏变化但输出不可放行；最终验证只允许当前任务治理记录脏变化，并绑定开始时 HEAD。
2. committed/worktree 的新增、修改、删除、rename/copy 两端、子模块、未知未跟踪与 symlink escape 均纳入范围判定。
3. subject 同步仅在 repository ID、branch、base 可达且不变时允许；base 永不自动更新，返回可审计同步事件事实供后续 verify 持久化。
4. 当前任务治理路径单独允许，其他任务治理路径拒绝；base..subject 业务路径必须满足任务允许范围。
5. 干净最终、脏 provisional、脏最终、rename/delete 越界、其他任务、分支、不可达 base 与覆盖产物位置测试通过。
6. 定向测试、全量回归、ruff、format、mypy、diff check 与精简双重复核通过后本地提交。
