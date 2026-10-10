# Agent Instructions

本仓库用于构建可审计的 AI 代码协同系统。

## 当前治理模式

项目所有者已明确决定进入仓库维护模式；`.ai/bootstrap-mode.yaml` 处于 active，task-free 例外已启用。代码、配置、CI 或行为变更不再强制创建 AI Flow task。未经项目所有者新的明确决定，不得移除该标记或单方面恢复强制 task 模式。

维护模式**只**解除任务账本的强制性。以下一律不放松：CI 质量门禁的每一项检查与阈值（完整测试、85% 总覆盖率、90% diff coverage、whitespace、Ruff、format、mypy）；`main` 的分支保护与 required check；高风险动作按下方常设授权处理；既有任务记录、证据与日志仍是追加式的，不得重写或删除。

仍须走 AI Flow 的升级清单：`.github/workflows/**`、`.ai/policy/**`、`.ai/schemas/**`、`src/aiflow/**`、`.gitignore` 与 `.gitattributes`、任务账本本身，以及任何有外部副作用或不可逆的动作。其余变更由 CI 质量门禁把关。

AI Flow CLI 保持完全可用，下述规则在使用它时仍然完整适用。对清单之外但风险较高、需要留痕或需要人类决策的变更，同样应主动创建 task；恢复强制模式只需删除标记文件。

## 常设授权

项目所有者于 2026-10-10 授予以下常设授权以减少人工介入；修改或撤销本节须项目所有者明确决定，Agent 不得扩大自身权限。

- **Agent 自主执行**：升级清单之外的改动可推送分支、开 PR、在 required check 通过后以 merge commit 合并（可启用 auto-merge），并删除已合并分支；任务关闭记录随后续 PR 提交。
- **Agent 代为记录批准**：升级清单内的 AI Flow 任务，在独立 Agent 审核结论为 APPROVE 且无未关闭的 critical/high 发现、verify 通过、无外部副作用、不触及授权文件时，可以 `project-owner` 记录 spec、code 与本地 action 批准，理由须注明“常设授权”；同样条件下可推送、开 PR 并按上条合并。
- **仍须项目所有者逐次决定**：授权文件（本节、`.ai/policy/hard-rules.yaml`、`.ai/policy/permissions.yaml`、分支保护与仓库设置）；削弱 CI 门禁或降低阈值；ASK 方向选择；部署、删除数据、凭据导出、付费调用、强推或改写已推送历史、删除 `archive/*` 标签或未归档的工作。
- **例外上报**：同一问题连续两轮 REQUEST_CHANGES、CI 失败且无法修复、或遇到上述范围外的动作时停止并请求决定；其余情况完成后只发摘要。
- **记录方式**：过程只记录在 CLI 账本与 PR 描述中；`docs/` 只写长期有效的用法、设计与当前状态，不新增按日期的过程记录；审核输入不另存副本，`resolve` 直接引用 `reviews/` 中的记录。

## AI Flow 规则

1. 选择进入 AI Flow 的变更必须走完整流程；CLI 尚未实现的部分，按实施目录执行并记录决定。
2. 不得绕过任务状态、允许范围、所需批准或验证门。
3. 不得自行降低分流或验证等级；范围、风险、依赖、权限、规格或 Policy 变化时必须升级或重新分类。
4. 常设授权之外的删除、部署、凭据、付费调用等高风险动作必须单独获批。**该要求由人类与 Agent 自觉遵守，系统当前不强制**：没有任何代码路径检查 push/merge 的批准，pre-command wrapper 只拒绝、不授权。边界与后果见 [Hooks](docs/operations/hooks.md)。
5. 批准与证据按类型绑定不同的版本事实（例如 spec 批准并不绑定 `subject_commit`）；以 CLI 的 `Missing:` 与新鲜度输出定位缺项，本文不复制字段表（见规则 6）。**请求人类批准前先跑一次 `status`，只补 `Missing:` 列出的项**；缺项可能是 Agent 应完成的机械步骤，并不都需要人类。合并就绪与批准覆盖以 `gate` 为准，输出冲突时先诊断；系统未判失效的批准不得重复请求。
6. 可执行 Policy 与 CLI 上线后以其确定性结论为准，不在 Agent 文件中复制规则表。
7. 模型选择与职责分离：仓库不固定主会话或 sub-agent 的型号与推理档位，沿用用户选择和运行时默认。跨模型委派以当前工具实际暴露的能力及兼容性为准；独立 worker 不得标作原生 sub-agent，不得通过切换主会话或改写模型目录伪造兼容性。涉及模型身份的结论须核对实际线程元数据，历史型号不作为当前默认或权限依据；详见[模型选择与代理职责](docs/operations/model-selection.md)。
8. 安全改动（文档、测试）与治理面改动（`.github/workflows/**`、`.ai/policy/**`、`.ai/schemas/**`、`src/aiflow/**`）应放进**不同的 task**；适用维护模式例外的安全改动直接 task-free。任务路由取各单元的最严重值，同 task 内拆分不改变任何审批；拆分减少等待耦合，不减少批准总数。Agent 连续完成已授权范围内的检查、修复、验证、账本推进与阶段提交，无须逐步询问“是否继续”；只有缺少真实方向决定或所需授权时才请求人类，详见[低干预工作方式](docs/operations/low-intervention.md)。
9. 合并 PR 只用 merge commit：仓库已禁用 squash 与 rebase 合并，因为证据与批准绑定具体提交 SHA，改写历史会让它们脱离 `main`。不得强推或改写已推送的提交；同步基线时把 `main` 合并进分支，不做 rebase。已因 squash 脱离 `main` 的证据提交由已推送的 `archive/*` 标签保持可达（如 `archive/claude-simplify-architecture`），不得删除这些标签。

启动：运行 `python -m aiflow --help`。维护模式下 task 不再是每次变更的前置条件；决定使用 AI Flow 时，为该变更创建或恢复 task 并按 CLI 状态推进。

入口：[项目总览](README.md) · [Policy](.ai/policy/) · [模板](.ai/templates/) · [CLI](src/aiflow/cli.py) · [MVP 设计](docs/superpowers/specs/2026-08-01-ai-code-collaboration-mvp-design.md) · [实施目录](docs/superpowers/plans/2026-08-01-ai-code-collaboration-mvp-implementation-directory.md) · [外仓反馈闭环](docs/operations/feedback-loop.md)
