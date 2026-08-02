# Agent Instructions

本仓库用于构建可审计的 AI 代码协同系统。

1. 代码、配置、CI 或行为变更必须进入 AI Flow；CLI 尚未实现时，按实施目录执行并记录决定。
2. 不得绕过任务状态、允许范围、所需批准或验证门。
3. 不得自行降低分流或验证等级；范围、风险、依赖、权限、规格或 Policy 变化时必须升级或重新分类。
4. 删除、推送、合并、部署、凭据、付费调用等高风险动作必须单独获批。
5. 批准和证据必须绑定当前规格、Policy 与 `subject_commit`；相关内容变化后重新验证。
6. 可执行 Policy 与 CLI 上线后以其确定性结论为准，不在 Agent 文件中复制规则表。

入口：[项目总览](README.md) · [MVP 设计](docs/superpowers/specs/2026-08-01-ai-code-collaboration-mvp-design.md) · [实施目录](docs/superpowers/plans/2026-08-01-ai-code-collaboration-mvp-implementation-directory.md)
