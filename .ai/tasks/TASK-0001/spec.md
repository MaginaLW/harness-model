# Task Specification

## 目标

在不合并四个试点分支、不在主 HEAD 重跑旧任务 Gate 的前提下，汇总四个隔离试点的脱敏证据，建立十二项可自动追踪的阶段一验收矩阵，并使本报告任务通过验证和 Gate。

## 范围

- `docs/pilots/results/**`：四个试点的脱敏摘要、来源哈希和报告任务 ID。
- `docs/implementation/phase-01-acceptance-matrix.md`：十二项验收追踪表。
- `tests/integration/test_acceptance_traceability.py`：追踪完整性自动检查。
- 当前任务自身的 `.ai/tasks/TASK-0001/**` 治理记录由系统例外管理。

## 非目标

- 不合并、改写或删除四个试点分支/worktree。
- 不修改生产代码、Policy、Schema 或原始外部 artifact。
- 不在主 HEAD 上对四个旧试点任务重新执行 Gate。
- 不执行 push、merge、deploy、delete 或 package publish。

## 验收条件

1. 四个结果目录均记录脱敏 task ID、source branch、repository ID、pilot base、subject/attestation commit、CI/Gate 摘要、人工观察和已核对的外部文件 SHA-256。
2. 验收矩阵严格包含 `ACC-01` 至 `ACC-12` 各一次，每项有原始要求、实现文件、定向测试、演示命令、证据路径、结论和限制。
3. 结论只能为 `passed` 或 `blocked`；不得包含待定或占位状态，不得只有文字声明而没有可定位证据。
4. `python -m pytest tests/integration/test_acceptance_traceability.py -q` 通过，并确认发布前无 blocked 项。
5. 报告任务形成自己的 subject/attestation commit，权威 verify 与 Gate 通过，任务 ID 写入 `docs/pilots/results/report-task-id.txt`。

## 禁止动作

- push、merge、deploy、delete、secret export、paid external call、package publish。
- 重新 Gate 四个旧试点任务，或将主 HEAD 冒充为旧试点 attestation HEAD。

## 错误行为

外部哈希不匹配、试点 source branch/commit 不唯一、本地引用不存在、十二项 ID 缺失/重复、结论非 `passed|blocked`、报告任务证据过期或 Gate 失败时，验收必须失败；范围、Policy、权限或验证需求变化必须升级/重分类。

## 回滚

本任务只新增文档、脱敏结果摘要、追踪测试和任务治理记录。如需恢复，由后续获批任务以显式 revert commit 撤销；不直接删除历史证据或改写旧试点。
