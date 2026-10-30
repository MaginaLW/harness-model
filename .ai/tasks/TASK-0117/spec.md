# Task Specification

## 目标

按项目所有者明确决定，允许对其明确授权的具体 push/merge 不主动调用必然拒绝的 pre-command wrapper，同时保留任务禁令和质量门禁。

## 范围

仅修改 `docs/operations/hooks.md` 的 pre-command 流程说明。保留 wrapper 被调用时的原有拒绝行为；仅豁免项目所有者明确授权的具体 push/merge 的主动调用，其他动作保持既有流程。目标为公开仓库 `MaginaLW/harness-model`，在受审 subject 固定后向 `codex/approved-action-hook` 推送、开 PR，required checks 通过且绑定版本有效时以 merge commit 合并。

本任务以经本地 V1 和独立实现审核的 CLI 源码提交 `2cf78ea653b75c421d2fbbde155e55d92e508e78` 创建，以避免新任务记录本机路径。一次性启动包装仅在原 CLI 已发现的编号上并入各实际 worktree 已占用的任务编号，未更改编号保留、分类、状态或批准逻辑；包装 SHA-256 为 `51934658749b11d032a0f4c941b63d095d91e8dfdf15c90253894822b0d91c6c`。实际 `start` 未传入任何 `--forbid-action`；task 文件中的六项 `forbidden_actions` 来自当时 Policy 的默认自动动作限制。该来源是本次已知启动事实，不能反推其他任务的禁令来源。

## 非目标

不改写任何已有任务、证据或日志，不转移 TASK-0114 的明确禁令，不将来源未知的旧任务禁令解释为默认项。不修改 Policy、Schema、wrapper 代码、CI、阈值或分支保护；不移除、禁用或绕过实际集成的 Hook 或服务端拒绝。文档不宣称 wrapper 放行、CLI 验证授权人身份或自动强制单次消费。

## 验收条件

- 文档明确具体 owner 授权的 push/merge 可不主动调用必拒 wrapper；显式或来源未知的任务禁令、实际 Hook 与服务端拒绝仍生效。
- 对本任务 push/merge 分别记录精确 action 的目标、subject/ref、条件与有效期并人工核对授权；保留独立审查、当前验证、Gate、required CI 和 merge commit。
- 当前规格独立设计审核、当前 subject 独立实现审核、完整适用 V1 与 code 批准均有效，所有必需检查与覆盖率阈值不降低。
- 不将本地 Gate 或 wrapper 未调用解释成外部动作授权；目标仓的 required check 未通过时不合并。

## 禁止动作

不执行未经所有者明确授权的 push/merge；不覆盖任务明确或来源未知的禁令；不执行 deploy、数据删除、凭据导出、付费调用、强推或改写已推送历史。保留 Policy 默认禁止自动动作的数组；它不构成对本任务已获所有者明确授权动作的显式额外任务禁令。

## 错误行为

当授权、目标、绑定、风险事实、审核、验证、来源或目标仓权限缺失、失效或有冲突时停止相关动作；不得忽略真实 Hook 或服务器拒绝，不伪造通过、不改写旧记录。其余独立工作继续。

## 回滚

按仓库规则审阅后以 Git revert 恢复文档；历史任务、审核和验证记录保留。已公开内容可能已被外部读取，无法保证撤回。
