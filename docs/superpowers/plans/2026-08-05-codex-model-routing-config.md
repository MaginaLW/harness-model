# Codex 模型路由配置决定（已按运行时能力修正）

## 决定

在项目范围内把主会话默认值设为 `gpt-5.6-sol / high`，把原生 sub-agent
默认值暂设为 `gpt-5.6-terra / medium`，并将单个会话的并发 sub-agent 上限设为 2。
应用的 **Advanced** 模型选择器仍可按单轮覆盖主会话默认值。

当前不把 `gpt-5.6-luna` 配成 Sol 的原生 sub-agent。Codex 0.147.0-alpha.1.2 的有效模型目录把
Sol/Terra 标为 Multi-Agent v2、Luna 标为 v1；v2 的 active-backend 过滤因此只向
`spawn_agent` 暴露 Sol 和 Terra。配置 Luna 虽能通过 TOML 解析，却会在运行时被拒绝，
或者在部分路径上静默继承成 Sol。

## 范围与依据

- 配置文件：`.codex/config.toml`
- 仅影响本项目的 Codex 会话，不修改用户全局 `C:\Users\Magina\.codex\config.toml`。
- 依据：本机 `models_cache.json` 的实际 `multi_agent_version` 分别为 Sol=v2、
  Terra=v2、Luna=v1；当前 `spawn_agent` 模型枚举也只有 Sol 和 Terra。
- 官方配置文档支持 `agents.default_subagent_model`，但配置值不能绕过运行时的
  active-backend 模型兼容性过滤。
- 既有会话日志显示，上一轮方案曾把目标主线程的下一轮直接切成
  `gpt-5.6-luna / max`，再要求其子线程继承 Luna。这不是 Sol → Luna sub-agent，
  因而撤销该方案。
- `ultra` 会主动触发多代理并显著增加用量；项目默认降为 `high`，需要时可在 UI
  中按轮选择 Max 或 Ultra。

## AI Flow 手工记录

- CLI 状态：`aiflow` 当前仅提供 help/version，尚未实现任务状态、Policy 和审批门。
- 执行方式：按仓库 `AGENTS.md` 与实施目录要求，采用本决定文件记录本次配置变更；不创建伪造的
  `TASK-*` 运行时记录，不改变既有章节状态。
- 允许范围：修正项目 Codex 配置、仓库 Agent 规则和本决定记录。
- 禁止动作：不修改全局配置、不启动 sub-agent、不提交/推送、不删除文件、不进行付费调用。
- 可逆性：恢复本次三个文件的变更即可回到原方案。
- 验证：用 Python `tomllib` 解析配置；检查主模型、原生 sub-agent 模型、推理档位、
  并发上限，并与当前模型目录的 Multi-Agent 版本相符。
- `subject_commit`：当前工作树未提交，故记为 `N/A (uncommitted working tree)`。

## 生效条件

配置需要在新建或重新加载的 Codex 项目会话中生效。首个验证 sub-agent 应检查其线程
元数据为 `gpt-5.6-terra / medium`，不得只凭主会话提示词推断模型。

若任务必须由 Luna 执行，可从 Advanced 选择器启动独立 Luna 任务，或用显式
`codex exec -m gpt-5.6-luna` 工作进程；必须将其记录为独立 worker，而不是原生
sub-agent。不要修改 `models_cache.json` 或维护项目级模型目录来伪造 v2 兼容性，
因为缓存会刷新，且 UI 对项目级自定义模型目录仍有已知过滤问题。

待上游将 Luna 与 Sol 的 Multi-Agent backend 对齐、且 `spawn_agent` 实际枚举包含
`gpt-5.6-luna` 后，可把默认值恢复为 Luna，并用新任务的子线程元数据做端到端验证。
