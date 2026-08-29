# Review Package

## 审核目标

确认 TASK-0026 在当前 subject
`10393cf59cd8dc1b1306f5295a75b84fc072f423` 上完整实现冻结规格：Quickstart 提供基于
`uv.lock` 的可复现安装、项目解释器入口和环境自检；根 `.gitattributes` 仅保证历史
snapshot 以现有 LF Git blob 字节检出。批准范围仅为进入本地只读 Gate，不授权 push、
merge、deploy、delete 或其他外部动作。

## 背景

任务 base 为 `8503660358c20a065a4d2101e682fb58654ba2c1`，当前确定性分类为
`REVIEW / V1`。classification input SHA-256 为
`121aa42e0065e96e41c28a2df1cdc5bdf4c77dd6fb517c3856c05349bde28d72`，冻结规格
SHA-256 为 `4fe15dd34b934e8469f64f303b700b61d2ceddf2e30c40049e44aa3650dedcae`，
active Policy SHA-256 为
`f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`。

原 Quickstart subject `cfd447ef7c997bd2ad80d778d8229d1420ef0afb` 的首次 V1 暴露 Windows
`core.autocrlf=true` 会把 TASK-0025 的哈希绑定 historical snapshot 检出为 CRLF。任务已按
append-only 流程升级为 REVIEW，扩展范围仅到根 `.gitattributes`，重新冻结并取得设计审核
`REV-0049` APPROVE 与用户 spec approval。当前实现审核 `REV-0050` / context
`7147c1d126976575ce15f033caaefebc7ee7ce8c1ac1d024638d2e4de82897e1` 为 APPROVE，
findings 为空。

## 代码地图

- `docs/operations/quickstart.md`：提供锁定 `uv` 安装、标准 `venv` + `pip` 回退、
  Windows/POSIX 显式项目解释器入口，以及锁文件、依赖和 CLI 自检说明。
- `.gitattributes`：唯一规则为
  `.ai/tasks/*/historical-snapshots/** text eol=lf`，不改变普通源码、当前 task 记录或其他路径。
- `.ai/tasks/TASK-0026/**`：保存升级原因、冻结规格、分类、批准、失败与通过 evidence、
  双阶段结构化审核和 append-only events。
- `.ai/tasks/TASK-0025/historical-snapshots/**`：内容与 Git blob、manifest 均未修改；只按新属性
  重新物化工作树字节。

## 语义变更

干净克隆现在可以优先使用 `uv sync --locked --all-extras` 建立仓库专用环境，也可使用标准
`venv` 回退；命令显式指向项目解释器，避免把系统 Python 的 `No module named aiflow` 误判为
项目缺陷。历史 snapshot 在 Windows `core.autocrlf=true` 下仍以 LF 检出，因此按字节
SHA-256 绑定的 replay evidence 可重放。没有修改依赖、锁文件、Policy、测试期望、manifest、
历史 evidence 或 `.reasonix`。

## 风险

- `.gitattributes` 的 glob 必须保持仅覆盖 historical snapshots；扩大范围会改变其他文本文件的
  checkout 语义，需要重新治理。
- 当前主机为 Windows；四个 symlink 用例因主机无创建能力而条件跳过，不能据此证明所有平台
  的 symlink 行为。
- macOS/Linux 命令由文档、锁文件和现有测试覆盖，但本次没有在真实 macOS/Linux 主机执行。
- 本批准不包含 `.reasonix` 删除；该清理必须进入独立 AI Flow 任务，避免污染当前范围。
- 未执行或授权 push、merge、deploy、delete、package publish、凭据、网络或付费调用。

## 证据

- 已验证：当前 V1 evidence 为 `passed`，绑定 subject `10393cf59cd8dc1b1306f5295a75b84fc072f423`、
  当前规格、Policy 与 classification；10/10 required checks 全部通过，
  `unverified_scenarios: []`。
- 已验证：unit 为 1079 passed、3 skipped；完整 regression 为 1527 passed、4 skipped；coverage
  收集再次为 1527 passed、4 skipped。skip 均为既有 Windows symlink 创建限制。
- 已验证：TASK-0025 manifest 的 20/20 snapshot 文件 SHA-256 与当前工作树完全匹配；
  `git check-attr` 返回 `text: set`、`eol: lf`，snapshot 对 Git 没有内容差异。
- 已验证：锁文件检查、dry-run 精确同步、`pip check`、CLI help、Phase 2 self-hosting E2E、Ruff、
  format、mypy、contract、scope 与 diff coverage 均通过。
- 未验证：真实 macOS/Linux checkout、未来 `.reasonix` 独立删除任务、push/merge/deploy 和任何
  Phase 2 状态推进；这些均不属于 TASK-0026。

## 审核问题

- Quickstart 是否同时保留锁定安装和无 `uv` 回退，且没有要求全局安装或修改系统策略？
- `.gitattributes` 是否只约束历史 snapshot，并保持 manifest、Git blob 与 20 个文件摘要不变？
- 当前 V1、实现审核和批准是否绑定同一 subject、规格、Policy 与 classification？
- `.reasonix`、依赖、锁文件、测试期望和历史 evidence 是否确实未混入本任务？
- 风险、平台限制和未授权外部动作是否如实保留？

## 推荐结论

`APPROVE`（仅进入本地只读 Gate；不授权 push、merge、deploy、delete、task close 或其他外部动作）。
