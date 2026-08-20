# Task 4.2 执行计划

**目标：** 校验 ASK 选项并实现 `aiflow answer`，保存完整选择、稳定摘要和回答后的冻结规格，同时保留混合 REVIEW 门。

**授权与绑定：** 用户要求按章节持续推进并逐章完成。本计划绑定基线提交 `c7f7a0403a4b4e4f948a93281e3d70b77fc8c048`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: ASK 回答会写决定、变更并冻结规格并推进状态，需要结构契约、恢复边界和混合 ASK+REVIEW 回归，但不验证程序无法证明的语义互斥性。
- allowed scope: `src/aiflow/ask_service.py`、`src/aiflow/cli.py`、`src/aiflow/specification.py`、`src/aiflow/task_service.py`、必要的 storage/state/Schema 邻接修正、`tests/integration/test_answer_command.py`、直接相关测试 fixture、本计划和 Chapter 4/总体状态。
- forbidden actions: 不推送、不合并、不部署；ASK 回答不得替代 REVIEW 批准，也不声明选项语义互斥已被程序证明。

## 完成边界

1. options 文件严格满足 2—4 个唯一选项、完整非空字段、至多一个推荐项，选择必须存在，理由和 actor 非空。
2. `answer` 只允许 `WAITING_FOR_ASK`，事件保存完整选项、选择、actor、时间和理由，`decisions.md` 生成稳定人类摘要。
3. 选择写入规格“已冻结决策”节并重新校验、冻结；ASK-only 进入 `READY_TO_IMPLEMENT`，仍含 REVIEW 单元则进入 `WAITING_FOR_SPEC_REVIEW`。
4. 非法输入不修改任务；相同回答可安全重放或确定性拒绝，不吞掉 REVIEW 门。
5. 定向测试、CLI help、累计回归、Ruff、Mypy 与 diff 检查通过后完成 Task 4.2 并本地提交。
