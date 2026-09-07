# Task Specification

## 目标

修复 status 的历史批准聚合错误：旧批准保留在追加式账本时，当前有效的替代批准应恢复
对应 REVIEW 单元的批准覆盖；摘要不得因此误报必须重新验证。

## 范围

- src/aiflow/status_service.py：只读批准状态及其合并就绪摘要。
- tests/integration/test_status_command.py：复现问题、真实 Gate/status 对照及边界回归。

独立的入口文档与统计工具已在本任务 base 前以 task-free 维护工作交付。
本任务中的测试是该状态修复的直接验收，不混入独立的文档或测试清理工作。
风险为 low：唯一生产调用方是 CLI status；Gate、执行前提与授权不消费该摘要。
变更可由 Git 恢复，无外部副作用；展示行为及回归风险均如实声明，由 Policy 决定验证等级。

## 非目标

不修改 Policy、schema、Gate、freshness、批准写入或权限；不自动代替人类批准，
不恢复已停止的 B0–B4，不重写任何历史账本，不改变 CI 质量阈值。

## 验收条件

- 对当前 classification 中每个 REVIEW 单元，至少存在当前有效的 spec 批准。
- WAITING_FOR_FINAL_REVIEW、APPROVED_FOR_MERGE、MERGED 阶段还要求对应 code 批准；
  实现前的 spec-only 阶段不预先要求 code。仍由原 freshness 函数核实类型绑定。
- 同一单元的旧 stale 与新 fresh 记录共存时，以有效覆盖判断；另一单元缺批准仍不能被掩盖。
- 无当前 code、无所需单元批准或损坏的批准记录均不能报 current。
- 无分类却有 spec/code 记录时保守报 stale；action-only 保持原 not_applicable 行为。
- status 不写文件，保留原输出字段；真实 REVIEW 生命周期回归中 Gate PASS 时摘要
  为 gate_required，不把摘要宣称为 Gate 或外部动作授权。
- 上述定向测试、完整 active Policy 验证、85% 总覆盖率、90% diff coverage、
  Ruff、format、mypy、whitespace 与最终 Gate 全部通过。

## 禁止动作

push、merge、deploy、delete、secret_export、paid_external_call，及任何外部系统写入。

## 错误行为

继续使用严格账本与批准契约校验。未知分类或不能证明覆盖时保持非 current；
发现修复必须触及 Gate、权限、Policy 或批准绑定语义时重新评估并升级范围，不能以摘要修复名义放宽授权。

## 回滚

通过新的 Git 回退提交恢复本任务的源码与测试；保留本任务及所有历史批准、证据、事件。
创建时可选的本机路径提示未纳入 task 事实，以免将工作机路径提交到版本控制。
