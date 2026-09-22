# TASK-0049 实现审核包

## 审核目标

审核 `begin` 是否与权威 spec approval 新鲜度一致，并继续拒绝缺失或失效的
base/policy/spec。规格授权仅覆盖本次修复和独立回归；本包不是 code 或发布批准。

## 背景

TASK-0048 已记录 status 显示规格批准有效、begin 却因 subject 不同拒绝。
源码核查又确认 begin 漏查 base。用户批准本任务规格后，按 CLI 完成精确测试
依赖范围澄清、重新分类、冻结、独立 design review、spec 批准和 begin。
原 base `10b13d17001b3decce17080bc3773fcfe8f5a8fc` 未改变。

## 代码地图

- `src/aiflow/task_service.py::_require_ready_artifacts`：唯一生产源码修改。
- `src/aiflow/freshness.py::evaluate_freshness`：复用既有 spec 规则，未修改。
- `tests/integration/test_begin_close_commands.py`：独立 task-free 回归提交
  `25f48e4eb1c7126eae13eff6a1abf55dfe527d0b`；仅作为累计候选的集成审查依赖。
- 固定实现 subject：`d05beb274290c90aad67f986efdaac49a4e0967b`。

## 语义变更

每个 REVIEW 单元的 spec 批准按 task.base_commit、当前 Policy 摘要和实际冻结规格
摘要调用共享 freshness evaluator。subject-only 变化不使规格批准失效；错误或缺失
base 会拒绝。保留批准类型和单元匹配、分类新鲜度、AUTO 早退、原错误码及批准历史。
code/action 的 subject、evidence 和消费约束没有改动。

## 风险

改变实现入口的批准判定，需防止意外放行其他失效绑定。回归覆盖缺失/错误绑定、
错误类型/单元、历史有效记录共存及多 REVIEW 单元，并检查拒绝零写。
缺 policy/spec 的记录仍可能先被 Schema 拒绝；这不是省略 freshness 验证。
三个用户原稿保留在原工作区；正式验证在同分支、同 repository identity 的干净
检出执行，其环境和日志位于树外专用材料目录，未将本机路径或凭据提交。

## 证据

已验证：以下本地结果已与固定提交及原始证据核对。
未验证：新候选的远端 required CI 与实际发布尚未执行，不能由本地结果代替。

旧源码新增用例实测 30 passed、3 failed，分别对应 subject-only、base stale、base
missing。修复后同文件 33 passed；定向 Ruff/format 与累计 whitespace 检查通过。
独立源码技术审查未发现问题。固定 subject 的完整 V1 十项检查全部 passed：单元
1320 passed；全量回归与覆盖率轮各 1958 passed；总覆盖率 88.12%，显式
`coverage report --fail-under=85` 退出 0；diff-cover 为 100%（1 个可执行差异行），
保留 90% 门槛。契约、scope、Ruff、format、mypy、smoke 与累计 whitespace 通过。
原始 evidence SHA256 为 `2e44856dac3270f5fe2c1de56f774336b2570e7e5a56b0f941b5d8c1feb5ca7f`。
结构化独立实现审查及证据保存边界见 verification-closeout-001.md。

## 审核问题

1. spec 批准是否只按既有权威 base/policy/spec 规则判断，并覆盖每个 REVIEW 单元？
2. 分类门、其他批准类型和历史记录是否保持，错误绑定是否仍拒绝且无写？
3. 固定 subject 的完整质量门及独立实现审查是否通过，原始证据能否核对？

## 推荐结论

完整 V1 已通过，推荐代码审核结论 APPROVE；独立实现审查以当前结构化记录为准。本包不冒充用户
code 批准；不得据此推送、合并或关闭尚未实际合并的任务。
