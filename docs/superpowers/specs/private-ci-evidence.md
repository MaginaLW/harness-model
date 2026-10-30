# 原生 CI 私有证据传递候选

本文提出可审阅的候选，不表示已有可用通道或隔离环境，也不授权传输原件、创建存储、修改仓库设置或降低门禁。没有经授权且验证可用的通道时，原生 CI 回放保持阻断；本地模拟或 bootstrap 质量检查不能代替它。

## 现状与边界

本仓公开，普通 Actions artifact 对有仓库读取权限的用户可下载；私有原件、未审查的诊断日志和含路径的输出不能放入公开仓的 artifact、cache、工作流日志或状态描述。[GitHub artifact 权限](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts)。现有 [workflow](../../../.github/workflows/ai-quality-gate.yml) 的正式模式运行 `verify --ci` 和 Gate 并上传诊断目录，维护模式只运行 bootstrap 质量检查；启用私有回放前须审查所有输出和上传路径。

## 每次任务的材料

按当前任务、完整审核历史和 local-final evidence 确定精确清单，而不是复制整个任务目录：

- `.ai/tasks/<TASK>/` 中适用的 `task.yaml`、`spec.md`、完整 `events.jsonl`、`classification.json`、`approvals.json`、local-final `evidence.json` 和引用的 verifier context；从可信原位置冻结并认证完整 `reviews/` 与 `review-contexts/` 命名空间及其清单。逐个将 `review_recorded`、`review_finding_resolved` 事件与审核修订、上下文、摘要和事件顺序交叉核对，证明没有遗漏较新的拒绝审核或后续修订；不能证明完整性则阻断。按实现版本核对所需的 action 描述、批准和单次消费回执。
- local-final evidence 引用的唯一 `logs/<MUTRUN>/targeted-mutation/evidence.json`，及该记录引用的五份 `logs/MUT-V2-00[1-5].json`。普通检查日志是否属于实际消费闭包须对具体版本核实；不能推断摘要可以替代原件。
- 与任务绑定的仓库身份、Policy、Schema、manifest、引擎和检测器材料，以及可达的 Git base、subject 和 attestation HEAD。已在精确检出中存在的材料从该检出读取；其余只按审核过的清单补入，不能覆盖不同字节或改写原件。

[CI evidence 加载](../../../src/aiflow/verification_service.py)、[变异证据消费](../../../src/aiflow/mutation_evidence.py)和 [Gate](../../../src/aiflow/gate.py)是当前行为的权威入口。具体文件闭包须随实际引擎版本及任务重算；缺少必需材料时报告不可回放。`.ai/tasks/*/logs/` 被 [忽略规则](../../../.gitignore)排除，干净检出不会自动带上这些原件。

## 候选机制

所有者可选择受限私有存储和一次性私有执行环境，由被授权的发布者为单次任务提供只读原件。存储服务、执行位置、可用权限和隔离能力均尚未确定；候选可使用私有仓库的独立作业或等效环境，但不得假定其已存在或符合要求。访问仅限指定操作人和执行身份，凭据最小权限、仅覆盖所需对象；不把私有原件或凭据交给公开仓的普通作业。

仅允许经独立审核的同仓候选及其精确 base、subject、attestation HEAD、工作流、脚本和依赖闭包；禁止 fork、Dependabot、来源不明或已改变的候选，以及未审核的动态脚本、动作和输入。同仓本身不代表可信。审核和 SHA 比对不能阻止代码读取或外传同一环境中的原件和凭据：必须先证明可信执行闭包、网络及运行环境的隔离边界，否则拒绝运行。GitHub 明确警告不要在特权的 `pull_request_target` 或 `workflow_run` 上下文中执行不可信 PR 代码；环境审批也不提供自托管 runner 的进程隔离。[安全参考](https://docs.github.com/en/actions/reference/security/secure-use) · [环境边界](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)。

发布者提供经可信渠道认证的逐文件清单，绑定规范相对路径、大小与 SHA-256，以及仓库身份、任务、task branch、base、subject、attestation HEAD、Policy、manifest 和引擎版本。摘要验证字节一致性，不认证发布者。接收端按现有 CLI 语义建立精确受控分支，核对仓库身份、`base → subject → HEAD` 祖先链，以及索引和工作树的治理范围；不能将 detached HEAD 或额外改动静默视为合法上下文。接收端拒绝缺项、额外项、重复、路径穿越、链接、覆盖冲突、摘要不符、过期绑定及不明来源；原始字节保持不变。随后运行该精确候选的原生 `verify --ci` 和 Gate，任一失败、缺失或清理状态未知均不记为通过。

临时副本建议最多保留七天，或在完成后更早到期；原始账本与证据继续按既有追加式规则保留。期限、自动到期与删除均须所有者决定。私有执行日志及诊断也须受同等访问控制；公开侧只允许经审核的固定结果和候选 SHA，不输出原件、原始 stdout/stderr、路径或凭据。GitHub 的实际保留期限与可配置范围见[官方说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)。

私有作业的结果摘要或投影本身不是公开仓 required check。若需要公开检查，还须单独设计和授权发布身份、最小检查写权限、准确 SHA 和现有 required check 的对应关系，并验证实际远端结果；不得仅凭本地或私有回放声称 required CI 通过。

## 决定与验收

实施前须由所有者指定并授权：接收服务及位置、允许传输的具体材料和敏感分类、操作人及执行身份、可信候选的审核和隔离方式、保留与删除规则、费用与外部传输，以及必要的仓库设置和检查发布权限。现有服务、访问控制、原件敏感内容、网络隔离和公开检查映射均未核实。

验收须在经授权的隔离环境对真实精确候选回放，并验证缺失、篡改、旧版本、错误身份、重复或越界路径、未知材料、非允许来源和 HEAD 变化均失败；包含省略较新 `REQUEST_CHANGES`、遗漏后续审核修订、detached HEAD、错误分支、不可达祖先和索引或工作树额外更改的反例。核查私有材料未流入公开输出，原件字节未变，成功结果与实际远端检查绑定一致。上述任一条件不能证明时保持阻断。
