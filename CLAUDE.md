# Claude Code Instructions

Claude Code 遵循与其他 Agent 相同的项目规则：

## 当前自举模式

当前 [bootstrap 标记](.ai/bootstrap-mode.yaml) 是本仓库自用治理模式的唯一开关。
- 标记为 `status: active` 时，harness-model 自身的本地代码、配置、CI 和文档工作不要求创建 AI Flow task，也不要求 spec/code approval、`verify` 或 Gate；按用户范围直接实现、测试并小步提交。只有用户明确要求测试 AI Flow 产品行为时才调用 AI Flow skill。
- 该例外不是 AI Flow Policy 的 `AUTO` route，不修改 `.ai/policy/`；删除、push、merge、deploy、凭据导出或付费调用仍须人类显式批准，并受可用的平台权限与 branch protection 约束。
- 只有项目所有者在项目完成后明确要求启用 AI Flow，才移除标记并恢复完整自用审批。

## AI Flow 正式启用后的规则

1. 代码、配置、CI 或行为变更必须进入 AI Flow；CLI 尚未实现时按实施目录执行。
2. 不得绕过任务状态、允许范围、所需批准或验证门。
3. 不得自行降低分流或验证等级；范围、风险、依赖、权限、规格或 Policy 变化时必须升级或重新分类。
4. 删除、推送、合并、部署、凭据、付费调用等高风险动作必须单独获批。
5. 批准和证据必须绑定当前规格、Policy 与 `subject_commit`；变化后重新验证。
6. 可执行 Policy 与 CLI 上线后以其确定性结论为准，不在 Agent 文件中复制规则表。

启动：先读取 bootstrap 标记；仅在标记未启用或用户明确要求测试 AI Flow 时，运行 `python -m aiflow --help` 并按任务状态使用 CLI。

入口：[通用 Agent 规则](AGENTS.md) · [项目总览](README.md) · [Policy](.ai/policy/) · [模板](.ai/templates/) · [CLI](src/aiflow/cli.py) · [MVP 设计](docs/superpowers/specs/2026-08-01-ai-code-collaboration-mvp-design.md) · [实施目录](docs/superpowers/plans/2026-08-01-ai-code-collaboration-mvp-implementation-directory.md)
