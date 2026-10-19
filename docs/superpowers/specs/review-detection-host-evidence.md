# 宿主只读证据接入候选

状态：`review-detection-host-evidence-v0.1`，`scope_decision=approved_once`，`read_state=closed`。所有者已明确批准第 3 节的一次有界只读，该轮已结束，不形成常设或重试权限。[原准入](review-detection-admission.md#2-来源职责与保存)的公开 Git／PR 范围保持；宿主返回值例外仅限这次明确批准，不修改自动快照白名单、Schema、权限或账本，不启动观察窗口。

上述状态只涵盖第 1–4 节的已关闭范围；第 5–6 节是独立的后续候选，尚未采用或执行，不恢复原次数。

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

## 5. 后续最小接入候选

状态：`review-detection-host-intake-v0.1`，`scope_decision=pending`，`read_state=not_started`。只准备未来新自然任务的证据接入，不补读已关闭对象、不重试 goal／线程、不追认旧审核。当前没有满足下述条件的宿主数据通道，**本候选不提出可执行读取请求**；批准文档也不授权接入、采集或付费动作。

### 当前通道与缺口

| 已核通道面 | 可得事实及不能替代的证据 | 后续处理 |
|---|---|---|
| 本仓固定 Git／公开 PR 回读 | 可核契约、候选、公开声明及报告原文；不能认证宿主派发、实际输入或预算。 | 继续复用既有公开范围，不索取重复批准。 |
| 当前工具定义中的 `read_thread`、`get_goal`、`get_usage_limits` | 分别为摘要、当前 goal、账户共享限额；均不足以提供完整实际请求、独立性或任务实费。 | 本次不调用；已关闭 goal 次数不复用，账户读取也不在原授权内。 |
| 静态 App Server 的 turn／item／thread 读取与 token 通知 | 协议可描述协作与用量；当前没有核定绑定此 Desktop 的可调用通道。 | 不猜 socket、不启服务、不订阅来试通；待有受支持的真实通道说明后另定范围。 |
| 完整实际请求、输入暴露覆盖、任务时间上限与货币结算来源 | 尚无已核通道；费用不能从账户限额、tokens 或价格换算取得。 | 分别保留 unavailable／unknown；不得以授权本身填补可用性。 |

[官方协议](https://learn.chatgpt.com/docs/app-server)与第 1 节本地静态基线须分别核对。该基线的 `thread/items/list` 没有条目类型或字段投影，整页可能包含消息、prompt、reasoning、工具输出；`limit=1` 不限制单项字节数。`thread/read` 即使不含 turns，必需的 `preview` 字段仍可能包含正文。接收后再过滤已经读取正文；条目时标及 cursor 形状不能从另一版本移植。

### 每项事实的最小证据

以下是原件核对要求，不是新增 Schema、采集器或证据包格式。各项必须能关联同一自然任务、固定候选、职责与实际阶段；有一项命中不传递成立到其他项。

| 目标事实 | 最小原件与覆盖要求 | 缺口及停止条件 |
|---|---|---|
| 实际派发 | 宿主已有派发项及对应接收／开始来源，关联固定候选、输入版本、审核或裁定职责、原预算；区分请求、接受、开工、完成及失败。 | 协作项的 sender／receiver／status 只支持所记录关联，prompt／model 不证明完整请求或实际后端；对象关联不唯一则停止。 |
| 完整实际输入 | 对实际请求及后续可见材料的覆盖依据和暴露顺序，涵盖指令、工具定义、继承上下文、候选／契约及工具读取；明确不可见、脱敏、截断或未覆盖部分。 | 不导出受保护指令、隐藏 reasoning 或秘密；无法核定必要覆盖则完整性 unknown。协作 prompt、全部可见 items、hash、脱敏清单或 debug 重建均不能自行认证完整输入。 |
| 独立性 | 作者／被测审核者／裁定者的职责分离，以及各自实际输入覆盖、暴露顺序和裁定固定原件；裁定前未获被测报告、答案、根因、修复或后继结果须有覆盖依据。 | 新线程、fresh context、角色名称或“未读”声明均不足；缺覆盖不认证未提示、隔离或统计独立，不追加盲审补证。相关组与方法条件仍另核。 |
| 时间预算与关闭 | 原授权适用工作、数值上限与单位、计量起止／时钟口径、实际耗时和停止／关闭来源；交代 root、子代理、工具、失败及重试的归属。 | goal 累计、turn 时长、CI timeout／耗时、报告公开或 PR 合并不替代本次预算；范围不可比不算剩余，不补零或无限。 |
| 费用预算与关闭 | 原货币上限、币种、计费或分摊口径，以及能绑定本工作的已发生／待结算费用来源和关闭依据；明确是否覆盖子代理、工具、失败及重试。 | 当前 unavailable；订阅、账户窗口、token 数和估算不证明零费用、实际费用或强制限额。未结算与未知分开，不把部分账目当完整关闭。 |

### 通道落实后才形成一次授权

先由宿主能力提供方给出**不含运行正文或凭据**的受支持接口／导出说明、实际版本和既有宿主绑定办法，列清返回面、分页、大小限制及已有来源定位；不通过读取对象来猜通道，也不假定存在导出服务。只有资料足以核定真实接入方式后，才在原 PR／CLI 形成填实的单次范围：

- 指定未来自然任务、固定候选与精确对象的核定办法；公开说明仅用匿名阶段，不入库私密 ID 或映射。
- 列出实际方法／已有原件、每次必然接收的内容及接收者；整页正文须明示，不能称“仅元数据”。若通道不能在读取前落实要求的范围和响应上限，则不调用。
- 填明最多调用数、每对象次数、页数、可强制的响应字节上限及停止时限，说明不翻页或准许的精确分页边界；这些是待落实参数，不是沿用第 3 节的次数或虚设服务能力。
- 来源从公开 Git／PR 扩到私密宿主返回值，须由所有者对实际暴露范围作一次明确决定；账户／费用来源另列真实返回面与授权。读取授权不含新模型、付费调用、服务启动、配置改动、日志／SQLite、遥测、订阅或后台等待。
- 只在内存核对已有原件，原 PR／CLI 追加匿名关联、覆盖依据和缺口，不保存响应、输入副本、原始费用明细或私密映射，不新建结果库。无法在此保存边界内支持复核的事实保留 unknown，不以不可复核摘要代替。

当前不能填实的通道、对象和限额继续标缺，不请求空白采集许可。需新建导出、启用遥测或改变保存边界时，先提交对应具体方案及风险决定，不借本候选实施。[官方遥测说明](https://learn.chatgpt.com/docs/config-file/config-advanced#observability-and-telemetry)不是既有读取凭据，也不能追补启用前的实际输入。

获准后的路径仍须在通道／宿主／对象不匹配、返回超范围、截断、失败、预算耗尽或覆盖冲突时立即停止，不更换来源、对象或自动重试。只接受有依据的窄事实，其余保留未知；上述证据及数据／方法／质量条件未全部核定前，不设置 `T0/T1`、不登记合格单位、不估计或更新评分。

## 6. 通道核定与单次握手授权候选

状态：`review-detection-host-channel-v0.1`，`scope_decision=pending`，`read_state=not_started`，`binding=unknown`。本节把第 5 节的通道前提细化为可检查的请求、返回面与拒绝条件，**尚不可执行，也不请求现在批准连接**；不是第 3 节读取重试或线程／goal 读取授权。

### 现有来源能核定到哪里

| 项目 | 当前可核事实 | 尚未核定 |
|---|---|---|
| 本地 CLI | 静态 `codex --version` 为 `0.152.1`；`app-server proxy --help` 提供 `--sock <SOCKET_PATH>`。 | 没有实际 socket 或它属于当前 Desktop 的依据；CLI 版本不等于当前 Desktop／server 版本。不得探默认 socket、枚举进程或读取配置／环境来补。 |
| 当前工具定义 | 提供摘要、goal 和账户限额接口；未暴露原始 `initialize`、`thread/turns/list` 或当前 Desktop 连接描述的匹配入口。 | 工具存在不证明代理所连 server 的版本、会话归属或协议返回范围；不通过旧对象调用试通。 |
| 既有静态协议 | `protocol/v1/InitializeParams.json` 与 `InitializeResponse.json` 可核握手字段；不是实际连接返回。 | 未取得运行版本、实现能力或接入凭据；不启动 proxy／daemon／app-server 验证。 |

成功握手在此静态基线**必需返回** `codexHome`、`platformFamily`、`platformOs`、`userAgent`。其中 `codexHome` 是本机绝对路径，可能含个人信息，不能包装成“只接收版本号”；各字符串均无 `maxLength`。响应没有独立 `serverVersion`、build、Desktop 实例或任务绑定字段；`userAgent` 也没有保证可解析版本或身份的格式。平台相同、目录相同或版本字符串相同均不能认证本次 Desktop 绑定。

[官方握手及通知说明](https://learn.chatgpt.com/docs/app-server#initialization)规定每连接一次 `initialize` 并确认 `initialized`。`optOutNotificationMethods` 只按精确方法名屏蔽通知，不能通配，且不适用于请求、响应或错误；不能据此保证只接收一条成功响应。静态 JSON-RPC 错误可带任意 `data`，通知／服务器请求可能携带路径、正文或认证／工具相关材料；不由“只发 initialize”推定这些流量不会到达，也不响应任何认证或工具回调。

### 待填实的单次范围

以下是**拟议上限与请求内容**，不是现有通道已经支持的限额。缺任一前提就保持 blocked，不创建连接：

| 待核项 | 具体候选与停止边界 |
|---|---|
| 端点和绑定 | 宿主提供方须从既有、受支持来源给出一个精确端点及其绑定此 Desktop 实例的可复核办法，另给实际 server 版本／构建与相应协议依据；不得从本地 CLI 或将来的 UA 猜配。当前这些值缺失，不公开端点、凭据或私密映射。 |
| 次数与时限 | 最多建立 1 次新客户端连接、发送 1 次 `initialize` 请求；仅在匹配成功响应后发送 1 次 `initialized` 确认，然后关闭自身连接。总时限拟定 5 秒、无重连／重试／分页，不停止宿主服务，不读取任何线程或 goal。 |
| 接收范围与上限 | 成功响应四字段，以及实际通道可能发送的错误／通知／服务器请求，必须先明确真实范围、接收者和是否含个人信息；拟定整个接收流上限 64 KiB。先证明既有通道能在接收前落实该范围和字节上限；仅客户端收满后截断、过滤或关闭不满足此要求。当前协议无此服务端参数或保证，故尚不能执行。 |
| 授权对象 | 通道及限制核实后，所有者才能对这个填实的一次连接／握手及其实际暴露范围明确决定；不是纯数值读取，也不承诺握手绝对无日志或连接状态效果。不能用文档批准、原第 3 节批准或“只读”标签代替。 |
| 保存与反馈 | 原始响应、路径、错误正文、认证材料及映射不落盘、不公开；仅内存核对，原 PR／CLI 追加匿名阶段、是否匹配和缺口。无来源可复核的版本或绑定仍 unknown；不把握手成功当实际派发、完整输入、独立性或预算端点。 |

候选请求固定为下式；`clientInfo.version` 是本候选客户端标识，不是宿主版本。它不 opt-in 实验 API 或 attestation，不设置扩展，也不保证排除所有服务器回调：

```json
{"id":1,"method":"initialize","params":{"clientInfo":{"name":"harness_model_channel_check","version":"0.1.0"},"capabilities":{"experimentalApi":false,"requestAttestation":false,"mcpServerOpenaiFormElicitation":false}}}
```

只有资料先证明端点／绑定、实际版本、全部可能接收范围和接收前限额，才形成可提交批准的单次授权。当前缺口不能通过握手本身反向补成连接许可；不探测或自动等待通道出现，不增加导出／采集器、配置或遥测。即使未来握手获准且成功，后续任务读取仍须按第 5 节另形成具体范围，不自动续接；`T0/T1` 与观察入口继续未设置。

## 7. 已核通道的选择与落实顺序

官方文档、本机静态帮助和当前可调用工具定义的核对已完成；结论限于这些来源。第 3 节仍为 `closed`，第 5、6 节的实际接入／握手仍为 `not_started`，Desktop 绑定仍为 `unknown`。当前没有可执行的原始宿主证据读取通道；这不推断平台不存在其他能力。

| 入口 | 已核支持关系 | 本项目当前可用边界 |
|---|---|---|
| App Server 客户端协议 | [官方 App Server](https://learn.chatgpt.com/docs/app-server#protocol)描述 JSON-RPC、stdio、WebSocket 和 Unix socket；文档同时说明 app-server 命令及 WebSocket 尚属实验性、不支持生产工作负载。 | 可作为后续集成的协议依据；文档未提供本次 Desktop 实例的端点或绑定证明。新启 server 不等于连接当前 Desktop。 |
| `codex app-server proxy --sock` | 本机 `0.152.1` 静态帮助说明将 stdio 字节转发到已运行的控制 socket；上述官方页面没有给出该子命令的接入约定。 | 参数存在不证明精确 socket、归属、协议版本或接收前限额；不探测默认路径，不运行 proxy 试通。 |
| `codex --remote` | [官方 CLI](https://learn.chatgpt.com/docs/cli/reference)描述连接 app-server 的终端 UI；本机帮助同时列出 `--remote-auth-token-env`。 | 不是任意 JSON-RPC 证据读取入口，不读取令牌或启动终端会话来补证。 |
| `--code-mode-host` | 官方协议与本机帮助均将其作为 app-server 到 Code Mode 执行宿主的出站连接，区别于 `--listen`。 | 不能据此绑定既有 Desktop，也不提供本项目所需的派发／输入导出。 |
| `codex remote-control` | [官方开发命令](https://learn.chatgpt.com/docs/developer-commands#codex-remote-control)用于管理 daemon／配对；本机帮助有 `start`、`stop`、`pair` 与 `--json`。 | 不是限定任务的只读证据导出。官方所述 `--no-daemon` 未在本机该帮助中出现，不能照搬新文档参数或为此升级环境。 |
| 应用内远程连接与当前工具 | [官方远程连接](https://learn.chatgpt.com/docs/remote-connections)描述设备配对和 SSH；当前工具仅暴露摘要、goal、共享限额等相关入口，未暴露原始握手／turn 读取及 Desktop 连接描述。 | 远程操作能力不等于证据导出；工具定义核对不调用对象，不读取其他聊天、账户、配置、进程或日志。 |

静态 `--version`／`--help` 不建立上述连接，但也不能承诺二进制启动绝对零写入：本机返回临时 PATH alias 创建被拒绝的警告，帮助和版本仍成功退出。该警告不作为宿主不可用的根因，不提权、重试或修改 PATH 来消除它。CLI 版本仍不代表 Desktop／server 版本。

后续只收敛到以下依赖，不再新增猜测端点的命令或未接入的采集器：

1. 宿主能力提供方给出既有受支持入口、精确端点的取得办法、当前 Desktop 绑定依据及实际 server／协议版本；材料不含凭据、正文或私密映射。
2. 核对该入口上全部可能接收内容、接收者与接收前可落实的范围／字节上限。协议队列、分页条数、通知 opt-out 和客户端收到后过滤均不替代第 6 节条件。
3. 仅在这些事实齐备后填实第 6 节的一次连接范围，按其实际暴露面取得所需决定；后续任务读取仍另按第 5 节核范围。当前不提出空白连接或采集请求。
4. 在等待真实通道资料及自然候选期间，继续使用[现有离线演练](../../operations/review-detection-preparation.md#不依赖真实任务的离线演练)和检查器。实际派发、完整输入、独立性、时间／费用及真实准入各自保留缺口，不由文档或演练通过关闭。

## 8. 资料获取、安装版本与人工移交

### 先区分系统 CLI、安装包与运行实例

Windows 注册安装包元数据可通过 `Get-AppxPackage -Name OpenAI.Codex` 取得，仅读取名称、版本及包清单即可定位安装组件，不需要读取用户配置或会话。本次核得的三个版本事实分别为：

| 来源 | 已核事实 | 不能据此认定 |
|---|---|---|
| 系统 PATH 中的 CLI | `0.152.1`；前述旧帮助及静态 Schema 属于此版本。 | Desktop 的 bundled CLI 或运行 server 使用同一版本。 |
| 注册的 `OpenAI.Codex` 包 | `26.1013.4894.0`；包清单的应用入口为 `app/ChatGPT.exe`。 | 当前窗口的进程身份、端点或运行 server 构建。 |
| 该包的 `app/resources/codex.exe` | 实际 `--version` 为 `0.163.0-alpha.10.2`；其静态帮助及 `generate-json-schema --experimental` 已另核。 | 该二进制正服务当前 Desktop，或已取得连接／读取许可。 |

[官方故障说明](https://learn.chatgpt.com/docs/reference/troubleshooting#feature-is-working-in-the-codex-cli-but-not-in-the-chatgpt-desktop-app)明确 Desktop 与系统 CLI 可以包含不同版本。这里保留两个静态基线，不用新包版本改写旧读取，也不把安装事实提升为运行绑定。生成的协议是忽略目录中的构建材料，不包含宿主响应，不随文档提交。

新版静态 Schema 的 `InitializeResponse` 仍要求 `codexHome`、`platformFamily`、`platformOs`、`userAgent`，没有独立 server build／Desktop 实例字段或字符串 `maxLength`；JSON-RPC 错误的 `data` 仍可为任意值。现有候选使用的 `clientInfo` 与 capabilities 字段仍存在，但这只核语法，不批准连接。新版另有可选 `explicitGatewayOauth`，其描述涉及 server gateway runtime 状态；本候选不设置它，也不承诺 initialize 普遍无状态效果。`thread/turns/list` 的 `limit` 仍为页条数，`itemsView=notLoaded` 仍只是省略 items，均不限制整个返回字节数。

其他返回面不能照搬旧版：新版 item cursor 可为字符串或对象锚点，条目可带 producer 实际记录的可空起止时标；Turn 的错误信息新增任意字符串／对象兜底，服务器请求中的 MCP elicitation 另有 `openai/userVerification` 形状。这些结构与旧静态基线分别核对，既不证明实际运行提供它们，也不证明仅握手时会或不会收到它们。elicitation 所传输入 Schema 中的 `maxLength`／`maxItems` 不是传输或累计响应限制。

### 自动检查的停止点

安装包内 CLI 新提供 `app-server daemon version`，帮助仅说明打印本地 CLI 和运行 app-server 的版本 JSON。本轮只读取其 `--help`；公开文档未给出该命令是否连接／自动启动、读取哪些状态、完整返回字段和大小限制，亦未说明如何确认属于当前 Desktop。因此不执行实际查询，也不把同一命令转交用户手工代跑。

系统及包内 `doctor --help` 均只有格式与展开选项，没有仅采集端点的选项。[官方 doctor 说明](https://learn.chatgpt.com/docs/developer-commands#codex-doctor)覆盖配置、认证、runtime 和 thread inventory 等检查；`--summary` 只改变显示，`--json` 只说明输出脱敏，不能据此推断采集范围缩小。本轮未运行完整 doctor，未读取进程、配置、会话或日志。

### 需要用户查看或询问的内容

1. 按 [Settings 说明](https://learn.chatgpt.com/docs/app/settings)在 Windows 用 `Ctrl+,` 打开设置，查看 `Connections` 中已有页面。只记录栏目及是否有直接提供的端点／server 信息，不开启功能。[远程连接说明](https://learn.chatgpt.com/docs/remote-connections)中的 `Set up`／`Add`、允许访问及扫码会开始设置或配对，并非端点信息查询。当前用户已确认有 Connections、页面仅见远程访问开关或配对入口；这一查看已完成，无须重复，也未取得原始端点。
2. 需要维护方提供资料时，回到输入框键入 `/`，选择实际显示的反馈入口。按[官方反馈说明](https://learn.chatgpt.com/docs/reference/troubleshooting#feedback-and-logs)检查现有 session、logs／diagnostics 等附带选项，取消附带；文档没有保证默认勾选状态。无法确认取消时关闭弹窗，不提交。只传下面的文字，不导出会话或诊断包。用户已报告反馈提交；当前尚未取得维护方回复，无须重复提交。
3. 对回复分别核对下表。反馈 session ID、连接设置可见、同版本或同目录均不替代 Desktop 绑定。若该版本没有受支持入口，记录这一明确限制，不开启配对、新服务或日志寻找替代。

| 资料 | 向宿主提供方索取的可复核说明 |
|---|---|
| 端点与 Desktop 绑定 | 该 OS／版本是否支持外部只读客户端连接已运行 Desktop；官方端点取得步骤，以及端点关联当前实例的依据。先要方法与脱敏依据，不索取凭据或私密映射。 |
| 运行版本与返回面 | 实例的实际 server build、匹配的版本化协议／Schema，以及 initialize 上全部成功、错误、通知和服务器请求的可能字段。安装版本或静态 Schema 不能代填实际版本。 |
| 接收前限制 | 是否有既有机制能在数据交给本项目接收者前落实范围和累计 65,536 字节上限；明确计数单位、实施位置、是否覆盖错误／异步消息、超限行为及适用 build。 |
| 新版版本查询命令 | `app-server daemon version` 是否仅查询已有 daemon、会否自动启动或读取配置；JSON 字段、是否含本机路径、大小限制及它与当前 Desktop 的关系。 |

累计 64 KiB、5 秒及一次连接仍是第 6 节的本仓候选约束，不是平台承诺。[官方协议](https://learn.chatgpt.com/docs/app-server#protocol)的 bounded queues、消息分帧，以及[通知 opt-out](https://learn.chatgpt.com/docs/app-server#notification-opt-out)不能证明这些约束已落实。若现有接口只能在客户端收取后过滤，继续保持缺口；需要改变候选时另行评估，不静默放宽。

可供用户自行核对并提交的文字草稿：

> Windows 上安装的 OpenAI.Codex 为 26.1013.4894.0，包内 CLI 为 0.163.0-alpha.10.2，PATH CLI 为 0.152.1。Connections 只显示远程访问和配对设置。我想让本地只读客户端连接当前已运行的 Desktop app-server，不新启服务、不导出会话。请问受支持的端点获取、Desktop 实例绑定和实际 server 版本核验办法是什么？initialize 连接上可能返回哪些内容，是否有接收前范围及累计字节上限？另外，`app-server daemon version` 是否只查询已有 daemon，具体读取和返回哪些信息，能否确认属于该 Desktop？若当前不支持，请直接说明。

### 维护方回复后的核对步骤

用户已报告提交反馈，当前不重复提交、追问或操作连接设置。等收到新回复后，按以下顺序移交和核对；本清单不要求用户代跑诊断或版本查询命令。

1. **用户提供回复入口**：给出脱敏后的相关原文、来源／工单引用、回复日期和所述版本；不附令牌、二维码、完整本机路径、会话或诊断包。不明确的版本和适用范围保持未知。
2. **Agent 核支持范围与实例绑定**：按上表先核 OS／build 是否支持外部只读客户端连接已经运行的 Desktop，再核官方端点获取方法及当前实例的绑定依据。反馈 session ID、设置入口、同目录或同版本不代替绑定；明确不支持时记录适用版本与限制，不用配对、新服务、配置／日志读取或 socket 探测绕过。
3. **Agent 核版本与全部返回面**：分别对照实际运行 server build、匹配的版本化协议／Schema，以及 `initialize` 的成功、错误、通知和服务器主动请求；特别核正文、本机路径及身份字段的可能范围。仅有成功示例、安装版本或静态 Schema 时列明未覆盖项。
4. **Agent 核接收前限制**：逐项核范围和累计 65,536 字节限制的计数单位、实施位置、错误／异步消息覆盖、超限行为及适用 build；另核候选的时限和次数能否落实。客户端收到后过滤／截断不能关闭接收前限制的缺口，64 KiB／5 秒／一次连接不写成平台保证。
5. **若建议版本查询命令，先核说明**：对 `app-server daemon version` 核是否只查询既有 daemon、是否可能自动启动或读取配置、完整 JSON 字段与大小／路径暴露，以及与当前 Desktop 的关系。资料不全继续留缺；资料齐备也不在本轮执行。
6. **汇总材料状态，保持暂停**：Agent 在现有文档中整理来源、适用版本、已核项、具体缺口和下一步所需材料，不代替用户向维护方发送消息。资料齐备时也只更新准备状态；当前真实评分、自动审核和宿主连接继续暂停，后续实际动作须在具体范围下另核所需决定，不因收到回复自动连接。

自然任务原件另按[配合与核对清单](../../operations/review-detection-preparation.md#自然任务出现后的配合与核对清单)保留。两类材料各自核对，维护方说明不能认证实际派发、完整输入、独立裁定或预算关闭。

取得资料仍不自动授权握手或后续对象读取；继续按第 5、6 节填实实际范围。实际派发、完整输入、独立性和预算端点分别保留未知，`T0/T1` 与观察窗口不因资料准备而启动。
