# 宿主只读证据接入候选

状态：`review-detection-host-evidence-v0.1`，`scope_decision=approved_once`，`read_state=closed`。所有者已明确批准第 3 节的一次有界只读，该轮已结束，不形成常设或重试权限。[原准入](review-detection-admission.md#2-来源职责与保存)的公开 Git／PR 范围保持；宿主返回值例外仅限这次明确批准，不修改自动快照白名单、Schema、权限或账本，不启动观察窗口。

## 1. 实核的协议能力与版本边界

以下是本地 `codex-cli 0.152.1` 的静态协议基线，不表示当前 Desktop 正在运行同一二进制、接口已可附着或已有运行原件。可在忽略的构建目录复核：

```console
codex --version
codex app-server generate-json-schema --experimental --out build/host-evidence/protocol
codex debug prompt-input --help
```

生成物只是公开类型描述，不是新研究输入 Schema 或运行记录；不得提交生成目录或以它证明实际派发。`--experimental` 只控制生成的字段，不启用宿主配置或运行采集。

| 静态入口／类型 | 此基线实际字段 | 能力边界 |
|---|---|---|
| `thread/turns/list` | `itemsView` 可取 `notLoaded`；Turn 的 `id/status/items` 必需，`startedAt/completedAt/durationMs` 可缺失或 null。 | 时间是 turn 粒度，不是某项派发时间；秒级时间与毫秒时长分开，不填造缺值。 |
| `thread/items/list` | `ThreadItemEntry` 只有 `item/turnId`；cursor 是 string 或 null。 | 此基线没有条目级起止时间；不能照搬新版文档中的额外时间字段或对象型 item anchor。 |
| `collabAgentToolCall` | `id/tool/status/senderThreadId/receiverThreadIds/agentsStates`；`prompt/model/reasoningEffort` 可选。 | 可关联可见协作记录；字段名、角色或 model 值不单独认证实际后端、完整输入或隔离。 |
| `thread/goal/get` | `goal` 可为 null；已有 goal 含 `objective/status/threadId/createdAt/updatedAt/tokensUsed/timeUsedSeconds`，`tokenBudget` 可缺失或 null。 | 目标累计不自动等于本次审核投入；没有 goal 就不创建，不重置目标或补预算。 |
| `thread/tokenUsage/updated` | `threadId/turnId` 和 `tokenUsage.last/total`；含 input/cachedInput/output/reasoningOutput/total 等计数。 | 不是货币账单；没有证明其汇总覆盖 root、子代理及重试，就不相加或作预算剩余。 |
| `thread/read`、`debug prompt-input` | Thread 可返回 `preview/name/cwd/path` 等；调试命令可输出 model-visible input list。 | thread 元数据也可能含正文片段；重建调试输入不等于抽取当前 Desktop 某次实际请求，不能执行 dump 来补原件。 |

[官方 App Server 文档](https://learn.chatgpt.com/docs/app-server)描述持久化读取与生命周期；本地版本需另核。即使取得全部可见 items，也未证明完整 system／developer／工具定义、继承材料或所有实际读取。不同线程及 fresh context 不证明进程隔离、未受提示或统计独立。

[官方遥测说明](https://learn.chatgpt.com/docs/config-file/config-advanced#observability-and-telemetry)另提供 turn／tool 时长和 token 指标，但须对应启用与真实来源；本候选不启用 OTel、不设置 exporter 或 prompt 日志。[Agents API usage](https://developers.openai.com/api/docs/guides/agents-api/observability)属于另一产品，且不是最终账单，不能当作当前 Desktop 的实测。

## 2. 本轮已完成与仍缺的事实

已核静态 CLI／Schema 和官方接口语义，并按批准的一次范围结束通道核定与已有 goal 回读。当前任务原生 goal 接口的脱敏投影为 `goal_present=false`，未取得可用 goal 对象；不创建 goal，不补零预算或用其他返回字段推定预算。可调用工具未暴露匹配的 `thread/turns/list` 参数面及当前 Desktop 绑定通道，线程路径未调用即停止；不以摘要接口、CLI proxy 的存在或猜测 socket 代替。调用与限额明细只留在原 PR。

未读取会话、日志、SQLite、凭据或任务正文，未启动 app-server、模型、调试输入 dump 或 collector；未保存宿主响应或私密 ID 映射。现有应用工具的摘要接口不被本页当成完整请求导出。

真实派发仍缺绑定具体候选、输入及预算的宿主原件；实际输入仍缺完整可见材料与暴露时序；独立性仍缺职责之外的运行依据。可空 turn 时间、token 数或阶段报告不能补时间上限、货币上限、实际费用和关闭。没有这些事实不等于平台没有相关能力，也不由静态能力产生真实准入。

## 3. 已批准的一次读取范围

以下范围已由所有者明确批准一次，将来源从公开 Git／PR **有限扩展到指定任务的宿主返回值**。该轮已结束；未使用的次数不转成下一轮、自动发现、重试或后台等待权限。原边界保持：

- 目标仅为当前任务及至多两条已知、明确指定的子代理线程；使用已核定的精确 ID，不枚举聊天或猜 ID，不追溯其他任务。
- 仅在已有、受支持且能核定属于当前 Desktop 的只读通道上，分别最多一次 `thread/turns/list`，显式 `itemsView="notLoaded"`、`limit=1`、`sortDirection="desc"`，不翻页。若最新 turn 不是指定对象，停止该路径，不按邻近时间猜配。响应含 turn 元数据及可能的 `error` 结构；原文错误信息不公开。
- 对当前任务最多一次读取**已有** goal。该原生响应必然可能包含 `objective` 目标文字，不能宣称只接收数值；所有者的范围决定须涵盖这一实际返回面。不允许接收目标文字时不调用；null 保留 null，不新建 goal、不改预算或目标。
- 无匹配通道、身份不能绑定、接口／字段不兼容或读取失败时，保留具体 unavailable／unknown 并停止；不新启 daemon／app-server、resume、turn/start、线程、订阅、OTel 或后台监测来补证，不机械重试。
- 仅在内存核对；原 PR／CLI 追加匿名阶段、字段可得性、已核关联和缺口，不保存响应、私密 ID 映射、原会话或目标正文副本，不公开原始目标、错误信息或本机路径。

该候选有界为最多三次 turn 读取和一次当前 goal 读取，不是新的推理、审核或付费调用预算；不访问账户、凭据、账单或价格接口，不把 tokens 乘单价冒充已结算费用。返回字段存在也不认证预算强制执行。

## 4. 本候选明确不覆盖的后续读取

`thread/items/list` 没有按条目类型或字段投影的请求参数，可能返回 user／agent 消息、prompt、reasoning 和工具输出；先取整页再过滤已经读取正文，不能包装成“仅元数据”。`thread/read` 的 preview、目标正文之外的聊天内容、调试 prompt-input 和会话文件也不由第 3 节覆盖。若实际派发关联只能从这些内容取得，保留缺口，另把必然接收的真实范围交所有者决定；不默认加开下一阶段。

第 3 节的批准及某项读取成功也只可能补限定 turn／goal 的窄事实。它不能独自补齐协作派发、完整实际输入、独立性或货币预算／费用，因此不能关闭全部 `VERIFY_*`，不能认证旧审核，也不能设置 `T0/T1`、登记合格单位、真实估计或更新评分。
