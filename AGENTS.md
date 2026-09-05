# Agent Instructions

本仓库用于构建可审计的 AI 代码协同系统。

## 当前治理模式

项目所有者已明确决定进入仓库维护模式；`.ai/bootstrap-mode.yaml` 处于 active，task-free 例外已启用。代码、配置、CI 或行为变更不再强制创建 AI Flow task。未经项目所有者新的明确决定，不得移除该标记或单方面恢复强制 task 模式。

维护模式**只**解除任务账本的强制性。以下一律不放松：CI 质量门禁的每一项检查与阈值（完整测试、85% 总覆盖率、90% diff coverage、whitespace、Ruff、format、mypy）；`main` 的分支保护与 required check；删除、推送、合并、部署、凭据导出、付费调用等高风险动作仍须单独获批；既有任务记录、证据与日志仍是追加式的，不得重写或删除。

仍须走 AI Flow 的升级清单：`.github/workflows/**`、`.ai/policy/**`、`.ai/schemas/**`、`src/aiflow/**`、`.gitignore` 与 `.gitattributes`、任务账本本身，以及任何有外部副作用或不可逆的动作。其余变更由 CI 质量门禁把关。

AI Flow CLI 保持完全可用，下述规则在使用它时仍然完整适用。对清单之外但风险较高、需要留痕或需要人类决策的变更，同样应主动创建 task；恢复强制模式只需删除标记文件。

## AI Flow 规则

1. 选择进入 AI Flow 的变更必须走完整流程；CLI 尚未实现的部分，按实施目录执行并记录决定。
2. 不得绕过任务状态、允许范围、所需批准或验证门。
3. 不得自行降低分流或验证等级；范围、风险、依赖、权限、规格或 Policy 变化时必须升级或重新分类。
4. 删除、推送、合并、部署、凭据、付费调用等高风险动作必须单独获批。
5. 批准与证据按类型绑定不同的版本事实（例如 spec 批准并不绑定 `subject_commit`）；唯一权威是 `aiflow status <TASK_ID>` 的 `Missing:` 与新鲜度输出，本文不复制字段表（见规则 6）。**请求人类批准前先跑一次 `status`，只补 `Missing:` 列出的项**；系统未判失效的批准不得重复请求。
6. 可执行 Policy 与 CLI 上线后以其确定性结论为准，不在 Agent 文件中复制规则表。
7. Codex 原生 sub-agent 路由以当前运行时实际暴露的模型为准。当前 Sol/Terra 使用 Multi-Agent v2、Luna 使用 v1，禁止把 Luna 配成 Sol 的原生 sub-agent 默认值，也禁止通过切换既有主线程模型来伪装成 Sol → Luna。需要 Luna 时只能建立明确标注的独立 Luna 工作线程；它不是原生 sub-agent。待运行时模型目录兼容后，再恢复 Sol → Luna 并以子线程元数据验证。
8. 安全改动（文档、测试）与治理面改动（`.github/workflows/**`、`.ai/policy/**`、`.ai/schemas/**`、`src/aiflow/**`）应放进**不同的 task**，而不是同一 task 的不同决策单元 —— 任务路由取各单元的最严重值，同 task 内拆分不改变任何审批。拆成独立 task 也不减少批准**次数**，减少的是安全改动排队等待治理评审的耦合。依据与实测见[执行目录](docs/superpowers/plans/2026-09-03-approval-overhead-and-open-task-consolidation-directory.md)。

启动：运行 `python -m aiflow --help`。维护模式下 task 不再是每次变更的前置条件；决定使用 AI Flow 时，为该变更创建或恢复 task 并按 CLI 状态推进。

入口：[项目总览](README.md) · [Policy](.ai/policy/) · [模板](.ai/templates/) · [CLI](src/aiflow/cli.py) · [MVP 设计](docs/superpowers/specs/2026-08-01-ai-code-collaboration-mvp-design.md) · [实施目录](docs/superpowers/plans/2026-08-01-ai-code-collaboration-mvp-implementation-directory.md)
