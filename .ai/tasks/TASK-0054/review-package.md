# TASK-0054 实现审查包

## 审核目标

审核 E4.1 `external-review` 1.0 契约的固定实现 subject
`23793f7071da20437b4e05b81512da85a277c958`，base
`e8e59e2b4112249c4c85c9a0eb1d510bacd9e597`。当前规格 SHA-256 为
`a33255cab106812063d671dd0d8981b440c30120e4fa9e3f140e4a77d1ee154e`，
实现上下文 SHA-256 为 `a660f9f87be200ea6881d6d56ad6b42382a6a04bf9dce012adb8b8ff2cc016eb`。

## 背景

E4.1 只定义已解析 ZCode 审查 envelope 的结构与错误诊断。设计审查先后提出
来源绑定、字段上限、敏感未知字段名和 `oneOf` 诊断问题；当前冻结规格经
`REV-0005` 独立设计审查通过，并已取得当前版本规格批准。旧设计发现和首次
中断的 V1 运行均保留在 TASK-0054 账本及日志，不作为本次通过证据。

## 代码地图

`.ai/schemas/external-review.schema.json` 定义封闭字段、来源与目标的独立阶段
条件、集合/文本上限和原始问题映射。`src/aiflow/contracts.py` 登记新契约，并仅对
该契约的直接未知字段错误返回已知父对象位置与 `additionalProperties` 约束。
四个合成 fixture 和 `tests/unit/test_contracts.py` 覆盖有效、缺失、越界、
`oneOf`、诊断脱敏及旧契约兼容。任务目录保存规格、批准、审查和验证证据。

## 语义变更

新契约保留报告来源、实际受审对象、目标 context、完成状态、原始 findings 和
待核定映射；只校验解码后 envelope。未知字段名可能含敏感输入，因此新契约的
直接额外字段诊断不回显该名称或值；判别对象可在已知父位置报告 `oneOf`。
既有契约的额外字段诊断维持原行为。契约通过不认证来源、独立性、原始字节或
目标匹配，也不写正式 Review、Finding 或批准。

## 风险

首次 V1 由错误 checkout 的可编辑安装导入造成假失败并在缺陷复核后中断；
失败事件和部分日志保留。当前正式 V1 使用本 worktree 的隔离 `.venv`，
`aiflow` 导入路径已核对，固定 subject 未改变。Schema 拒绝未声明字段，
但原件大小、重复 JSON 键、来源事实、仓库映射和路径/凭据预检属于 E4.2。
本次没有接触真实 ZCode 报告，也没有验证导入写入或外部服务。

## 证据

已验证：`aiflow validate` 与 `scope` 通过；本次 local V1 的 evidence SHA-256
`8a259b71d27c70763178cc929301626004047ec0a05f565e474b4e888c4e8e6b`
绑定上述 subject、规格、Policy 和分类，10 项必需检查全部 `passed`，无超时。
单元测试 1656 passed，全量回归及覆盖率重跑各 2294 passed；mypy 检查 41 个
源文件无问题，Ruff、format、contract、scope、smoke 均通过。覆盖率 XML 的
行覆盖率为 90.76%，行与分支合计覆盖率为 88.12%（8525/9674，高于 85% 门槛）；
diff-cover 对 `src/aiflow/contracts.py` 的 4 行可统计
变更报告 100%，超过 90% 门槛。两份独立只读源码/兼容复核对同一固定
subject 报告未见阻断问题；结构化实现审查另行登记。

未验证：E4.2 的原始报告加载、来源/目标核对、任务写入和真实报告验收；
远程 CI、推送、合并及任何外部调用。上述 V1 是本地证据，不替代这些后续阶段。

## 审核问题

- 新增诊断是否只影响 `external-review`，并避免未知键名/值回显？
- `oneOf` 判别对象和普通嵌套对象是否都定位到已知父位置？
- 固定 subject、规格、分类和本次 10 项 V1 证据是否一致？
- E4.2 的原件核对与写入是否仍被明确排除？

## 推荐结论

APPROVE：就固定 subject 与当前本地 V1 证据，未发现 E4.1 契约实现的阻断项。
本包是技术审核材料；正式实现审查、code approval 与 Gate 仍由各自 CLI
步骤独立核定。
