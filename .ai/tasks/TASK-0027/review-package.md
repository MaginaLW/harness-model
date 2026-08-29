# Review Package

## 审核目标

确认 TASK-0027 在当前 subject `f8208d2254c49984ffdbd9879b5a7fb6cd73f65e` 上仅删除
明确获批的 10 个 `.reasonix` 运行时元数据文件，并在根 `.gitignore` 新增 `/.reasonix/`，
使目录当前不存在且未来再生成时保持未跟踪。批准仅允许进入本地只读 Gate，不授权任何远程动作。

## 背景

任务 base 为 `71aca9d80a70672d309afeaa82e265359efac1bf`，确定性分类为
`REVIEW / V1`。classification input SHA-256 为
`d6df74c4d1a78448cf0bfc86f01b23b79cefb9f446480f9b6022e8eb78226dd8`，冻结规格
SHA-256 为 `8886ffb724e5d2630564dff3891e413272a9853c02264ad5b497831197e9df94`，
active Policy SHA-256 为
`f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`。

独立设计审核 `REV-0051` / context
`15808398e3c80332519b17b468df7cbe0b9afd0771891d2f96637fffdbf587b7` 为 APPROVE。
用户取得当前 spec approval，并为精确清单单独批准一次 action SHA-256
`e409dac2cb7cf25273f626918e6d39ff414aa1f3cfa712139295ec7995df0480`。该 action 已由同摘要
receipt 记录为 consumed，未重试或复用。独立实现审核 `REV-0052` / context
`f410dac22d0ea50ab99e77bd7329e8cbef95f618bd847fbbc6b44897a4806f19` 为 APPROVE，
findings 为空。

## 代码地图

- `.reasonix/desktop-topic-*.json`：删除 4 个桌面主题运行时元数据文件。
- `.reasonix/tasks/*/{events.jsonl,snapshot.json,task.lock}`：删除两个历史桌面会话下的 6 个
  运行时文件。
- `.gitignore`：新增唯一根锚定规则 `/.reasonix/`。
- `.ai/tasks/TASK-0027/action-delete-reasonix.json`：绑定获批目标、父 subject、清单约束、
  到期时间与单次使用条件。
- `.ai/tasks/TASK-0027/action-use-e409dac2cb7cf25273f626918e6d39ff414aa1f3cfa712139295ec7995df0480.md`：
  保存删除前置检查、精确路径、消费结果与恢复方法。
- `.ai/tasks/TASK-0027/**`：保存规格、分类、双阶段审核、批准、evidence 与 append-only events。

## 语义变更

仓库不再跟踪 `.reasonix` 桌面运行时状态；当前物理目录已删除，后续同名目录或文件再生成时
由根 `.gitignore` 保持未跟踪。删除没有扩展到 `.reasonix` 外部，也没有修改源代码、测试、
Policy、依赖、锁文件或阶段状态。父提交保留全部 10 个文件，可通过后续受治理变更恢复。

## 风险

- `.reasonix` 中的历史桌面标题和会话运行时记录已从当前版本删除；需要时只能从父提交恢复。
- ignore 规则会隐藏未来 `.reasonix` 内容；这是本任务目标，但不应扩展为忽略其他隐藏目录。
- action approval 已消费，不能用于其他目录、清单、subject 或重试。
- 当前 Windows 主机有四个既有 symlink 条件跳过，不能据此证明其他平台的 symlink 能力。
- 未执行或授权 push、merge、deploy、publish、凭据、网络、外部模型或付费调用。

## 证据

- 已验证：删除前 tracked 与实际文件清单均为 10、未知 untracked 为 0、reparse point 为 0；
  receipt 保存相同清单、action digest、父提交和恢复方式。
- 已验证：当前 `.reasonix` 物理目录不存在，`git ls-files -- .reasonix` 无输出，
  `git check-ignore -v --no-index .reasonix/probe.json` 命中根 `.gitignore` 第 10 行规则。
- 已验证：当前 V1 evidence 为 `passed`，绑定当前 subject、规格、Policy 与 classification；
  10/10 required checks 通过且 `unverified_scenarios: []`。
- 已验证：unit 为 1079 passed、3 skipped；完整 regression 与 coverage collection 均为
  1527 passed、4 skipped；Ruff、format、mypy、contract、scope 与 diff coverage 均通过。
- 未验证：push/merge/deploy、真实远程系统、未来 `.reasonix` 内容或任何 Phase 2 状态推进；
  这些均不属于本任务。

## 审核问题

- 删除前清单、action approval 和 receipt 是否精确绑定同一 10 个路径及父 subject？
- base..subject 是否仅包含 `.reasonix` 十文件删除、`.gitignore` 一行和 task-local 治理记录？
- 当前工作树是否确实没有 `.reasonix` 目录或 tracked 条目，且未来 probe 被根规则忽略？
- 删除是否可由父提交恢复，且 action authorization 未被重试或复用？
- V1 evidence 与实现审核是否绑定当前 subject、规格、Policy 和 classification？

## 推荐结论

`APPROVE`（仅进入本地只读 Gate；不授权 push、merge、deploy、task close 或任何外部动作）。
