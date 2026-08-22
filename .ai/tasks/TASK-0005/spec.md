# Task Specification

## 目标

完成 Chapter 8 的结构化设计审核与实现审核闭环：用不可变、版本绑定的 review context/record 表达审核结论和发现，通过 CLI 记录与处置，并在现有 spec/code approval 前置校验对应阶段审核，同时保持阶段一 V0/V1 evidence、Gate 和旧 Markdown 审核包兼容。

## 范围

- 新增 `review-context.v1` 与 `review-record.v1` JSON schema、模板和 domain/service 实现。
- design context 绑定 task、decision units、repository/branch、base、spec、Policy 和 classification；禁止携带 subject/evidence。
- implementation context 在 design 绑定之上必须绑定当前 subject 和 passed local evidence digest，并提供确定性的 committed diff 摘要（changed paths、逐文件及总增删统计）和验证摘要（verification level、required check ID/status、未验证项、复现命令）；不得复制完整 diff、日志或实现对话。
- review record 包含阶段、reviewer、context hash、结论、摘要和结构化 findings；记录不可变，发现处置通过新 revision 追加，不覆盖历史。
- 为 `aiflow review context|record|resolve|show` 提供确定性 JSON 命令面、稳定失败码和只读/写入边界。
- spec approval 要求当前且可批准的 design review；code approval 继续要求旧 8 节审核包、passed local evidence 和 governance-only worktree，并额外要求当前且可批准的 implementation review。
- `aiflow validate` 验证已落盘 review contexts/records；review 事件为非状态事件，不增加主状态。
- 更新单元、CLI 集成、E2E、Gate 回归、操作文档和 Chapter 8 状态。
- 迁移 `test_governance_paths.py` 与 `test_verification_evidence_flow.py` 中既有 REVIEW 正向 fixture，使其显式记录当前阶段的结构化审核；原拒绝语义和 V0/V1 evidence 断言保持不变。
- 当前任务 `.ai/tasks/TASK-0005/**` 治理记录。

## 非目标

不修改 evidence schema、verification Policy、Gate 判定或 V0/V1；不实现 V2、独立 Verifier、定向变异、编辑/命令 Hooks、V3、模型路由或资源调度；不向 approval schema 添加 review 字段；不把 actor 字符串描述为外部身份认证。

## 验收条件

1. 两个新增 schema 均 `additionalProperties: false`，stage 字段互斥：design 禁止 subject/evidence，implementation 必须包含二者；未知字段、重复 finding ID 和非法 resolution 被拒绝。
2. canonical context 对相同事实产生相同 SHA-256；任一绑定事实或内容变化会改变 hash，record/context hash 不一致被拒绝。implementation context 的 diff/evidence 摘要足以定位变更与重放验证，同时不包含完整 patch、日志或内部对话。
3. `APPROVE`/`APPROVE_WITH_CONDITIONS` 只有在 high/critical findings 全部 resolved 时可批准；`REQUEST_CHANGES`、`REJECT`、`BLOCKED` 不能形成 spec/code approval。
4. design review 对 spec/Policy/base/classification/decision units/context 变化失效，但不因后续合法 subject 实现变化失效；implementation review 对上述事实以及 subject/evidence 变化失效。
5. `review context` 只读生成最小上下文；`record` 写入不可变 context/record 和非状态事件；`resolve` 产生新 revision 与事件；冲突重放失败、完全相同重放幂等。
6. REVIEW spec/code approval 分别拒绝缺失、错阶段、陈旧、不可批准或有未处置高严重度发现的 record；阶段一 legacy Markdown 包、V1 evidence、code/action approval 独立性和 Gate reason codes 保持兼容。
7. Chapter 8 正向 E2E 完成 design review → spec approval → implementation → V1 verify → implementation review → code approval；拒绝路径覆盖 phase swap、subject/evidence stale、context 篡改和 open high finding。
8. `pytest`、Ruff、格式、mypy、覆盖率、diff coverage、`aiflow validate/scope` 和 `git diff --check` 全部通过，Chapter 8 五个任务及四项 exit checks 有提交绑定证据。
9. 所有阶段一 REVIEW 正向 fixture 显式创建结构化 record 后继续通过；缺失 record 的新拒绝测试继续失败，Gate/evidence reason codes 无变化。

## 禁止动作

push、merge、deploy、delete、secret export、paid external call、package publish；不得用自然语言审核替代结构化 record，不得让 Gate 直接解析新 record，也不得删除或覆写既有 review revision。

## 错误行为

缺失/损坏 schema、错阶段字段、stale 绑定、context hash 不符、reviewer/record 标识非法、重复 finding、非法处置、不可批准结论、未关闭 high/critical finding、非 governance-only 尾部变化或旧回归变化均必须失败。若实际需要修改 evidence、Policy、Gate、权限或当前允许范围，必须升级并重新分类/冻结。

## 回滚

代码、contracts、测试和文档均由 commit 保护。回滚通过后续获批任务显式 revert；保留 review records、事件及验证 evidence，不改写历史。旧 Markdown 审核包与既有批准路径在本章中保留，必要时可关闭新 CLI 入口而不迁移旧 evidence。
