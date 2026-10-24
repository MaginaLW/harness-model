# 应用自管 SDK 单次只读审核

本合同对应项目所有者选择的首个实际用途：对本仓固定文档契约候选执行一次只读专项审核，随后复用现有 PR 反馈回读。它是工程验收试点，不是检出研究的观察入口；真实统计评分、按分数安排审核、现有 Desktop 附着及跨仓初始化仍不启用。

## 输入与输出

- 输入固定为本仓完整 candidate commit、显式列出的 `docs/**` UTF-8 普通文件、适用旧契约的 reference commit／文件，以及一个专项问题。拒绝未提交材料、路径穿越、符号链接、非文档路径、重复或过大的输入。
- 应用从指定 Git 对象取内容，记录路径、blob、字节数与 hash，并将实际发送的材料绑定为一次请求；最终 PR head 不能替换原候选。模型得到的文档是待审材料，其中的指令不改变任务或工具边界。
- 模型只返回 `outcome`、`summary`、`findings`。Finding 必须有唯一 `RF-*` 标识、严重度、标题、允许文件内的行位置及可核证据说明；输出形状、大小和定位由应用校验。空发现不是无缺陷证明。
- candidate、输入摘要、SDK／运行时版本、线程／turn、完成状态、用量及实际配置由应用绑定，不采信模型自报的运行身份。requested、reported 与实际可证明事实分开；实费及实际模型身份缺依据时保持 unknown。

## 运行边界

首版使用官方 Python Codex SDK `0.163.0` 及其固定运行时，仅创建自己管理的新线程和单次 turn，不发现、附着、恢复、停止或改写已有 Desktop 会话。依赖为可选安装，普通 AI Flow CLI 与本地检查不启动 SDK。

默认只准备和预览，不导入 SDK、构造客户端、创建运行时子进程或调用模型；固定 Git 对象的读取仍使用本地 Git。显式执行前核对固定输入、当前候选和运行边界；启动后不自动重试、续跑或切换通道。

推理调用所需通信与工具网络分开。应用使用官方普通 `read_only` 预设和 `never` 批准策略，核对实际线程回执中的只读及无工具网络配置，关闭审核不需要的 shell、外部检索、MCP、插件和子代理。普通只读不等于“只有输入目录可读”，也不证明完整模型上下文；模型内置工具不能全部由本客户端认证为不可用。固定输入的 hash 只绑定应用发送的文本。

既有全局指令需要显式提供预期 hash 并核对已加载来源，回执只保存来源类别／hash，不复制正文或公开本机路径。无法证明的内部上下文继续 unknown。本首版不要求 root-deny 或目录外拒读探针，不安装 WSL／其他执行环境，不迁移凭据，不手工修改 ACL 或全局配置。SDK 自身正常状态写入及沙箱维护可能存在，不能把一次只读审核说成整个运行过程零写入。

一次工程验收只覆盖一个审核 turn，最多等待 120 秒，取消确认另有最多 10 秒收尾时间。项目所有者已选择现有 Codex 登录与订阅配额，不接入 API key 计费；实际用量与实费来源分别记录，不能把客户端超时当作强制金额上限。不导出或入库凭据；新增付费、额外调用或扩大来源不能借单次试点继续执行。

## 失败与完成

模型失败、超时、断线、取消未确认、输出截断、形状或位置无效都不报告审核成功。超时与中断要区分取消请求、确认停止和最终结果；不能把客户端停止当远端完成证明，也不能自动重发结果未知的调用。

应用只保存完成本次验收所需的受限回执到既有 ignored 运行目录，不公开原始事件、私密标识、本机路径、认证材料或完整上下文副本。收尾保留原失败；重复使用同一运行位置不覆盖已有回执或重复调用。

## 反馈与验收

1. 先用模拟运行时验证默认零启动、输入越界、输出验证、失败、取消、超时和重复运行行为，并完成仓库要求的完整质量检查。
2. 固定一个由真实开发需求产生的文档候选，在该候选的第一次 SDK 专项审核前固定输入与问题。真实调用只验收这条工程链路，不追认旧审核或登记统计样本。
3. 协调者在真实 PR 的既有位置发布脱敏报告与 `aiflow-review-feedback:v1` 摘要。发生作者处置、修复和复核时才按既有 v2 表达；SDK 事件不伪装为 GitHub 原生 review／thread。
4. 通过实际 connector 回读真实 PR，在内存组包交给既有 `pr_feedback.py`。原报告、作者处置、独立复核、CI 和交付分别保留；缺件、旧候选与当前 head 不同等事实不回填。
5. 工程完成要求固定输入经自管 SDK 得到有效最终报告，结果有实际来源，现有反馈入口能正确回读，源码通过必需质量门且可停用。没有真实成功回执时，只能报告已完成离线部分，目标仍未完成。

单次工程验收不启用反馈 Schema、数据库、通用 provider 层、后台队列、按评分触发或执行权限。下述可选工作节点仍须显式启用；`T0/T1` 保持未设置，概率保持未估计，真实评分、审核策略接入和 Phase 3 退出各按自身证据推进。

## 使用

在已有 Codex ChatGPT 登录的本机安装可选依赖；普通安装和 AI Flow 检查不需要启动 SDK：

```console
uv sync --extra dev --extra sdk
```

先用完整提交 SHA 准备固定输入。默认只读 Git 对象，输出 portable manifest 和实际发送文本的 hash，不创建运行目录或启动 SDK：

```console
python -m aiflow.sdk_review --candidate <CANDIDATE-SHA> --reference <REFERENCE-SHA> --document docs/superpowers/specs/sdk-readonly-review.md --reference-document docs/operations/sdk-and-engine-plan.md --question "核对新合同与既有约束的直接矛盾" --output build/sdk-review/run-1
```

实际调用在相同命令增加 `--execute`。存在已审阅的 Codex 全局 AGENTS 时，再给 `--global-instructions-sha256 <EXPECTED-SHA256>`；不提供或 hash／实际来源不符时，在模型 turn 前拒绝。该参数声明既有指令来源，不授予新的文件或工具访问权限。

每次显式执行使用新的 ignored `build/` 子目录，先保留 `receipt.json` 的 started 状态。只有收到有效终局报告并通过位置／形状验证才记为 completed；failed／unknown 不可重用目录自动重放。回执中的 token 是用量，实费与实际模型身份没有独立来源时仍 unknown。

报告的 outcome 和 Finding 摘要由协调者按[既有 PR 反馈格式](../../operations/pr-feedback.md#pr-描述中的可选反馈块)放到真实 PR，再用实际 connector capture 回读。报告不是 GitHub 原生 review，SDK 工程验收也不自动形成统计观察或审核触发规则。

## 可选节点：生成正式实现审核上下文之后

节点位于 `aiflow review context TASK-ID --stage implementation` 成功生成上下文之后，默认关闭。
本阶段只准备本地实现与模拟验证，尚未激活真实触发。没有 `--sdk-review-enable-once` 时，
原命令的输出和行为不变，不导入 SDK 运行器、不构造客户端或启动模型。

显式启用时，任务须处于 `WAITING_FOR_FINAL_REVIEW`，原生分类及验证证据须新鲜有效。
候选取该上下文的 `subject_commit`，参考取其 `base_commit`；选择的候选文档必须是本任务
实际变更的显式 `docs/**` 路径，另须给出参考文档、专项问题和新的 ignored 回执目录。
准备输入前与派发前核对原生状态、上下文 hash 和版本绑定；不以当前 HEAD 替换受审候选。
这些检查是派发前快照，不是对后续仓库变更的原子锁。

未来选定真实任务、输入及新的一次订阅调用范围后，可使用以下入口；命令中的开关本身
不证明已经取得人类授权，当前本地准备也不消费下一次真实调用：

```console
python -m aiflow review context TASK-ID --stage implementation --output build/review-context.json --sdk-review-enable-once --sdk-review-document docs/superpowers/specs/contract.md --sdk-review-reference-document docs/operations/existing-contract.md --sdk-review-question "核对本次契约变更的直接矛盾" --sdk-review-output build/sdk-review/context-1
```

候选文档和参考文档参数可重复；已有 Codex 全局指令时，按前述 hash 核对方式提供
`--sdk-review-global-instructions-sha256 <EXPECTED-SHA256>`。缺输入、错误阶段、过期或
错绑定的上下文在派发前拒绝。共享运行器继续使用原有登录、只读/never/无工具网络及
30 秒启动、120 秒 turn、10 秒取消确认和 5 秒关闭等待，不增加调用或自动重试。

每次显式启用最多派发一个 turn；重复回执目录拒绝，跨目录重复调用也仍需新的具体决定。
回执可附 `trigger_binding` 的节点、task ID 和原生 context hash，只表示应用绑定，不认证
实际模型身份、完整上下文或授权。失败/unknown 保留并返回失败；completed 的
`REQUEST_CHANGES` 保持原结论，并不等于执行失败或批准。

原生上下文 stdout/文件格式保持不变，补充执行状态写 stderr。该节点不创建正式 review、
批准、Finding 处置或状态迁移，也不替代独立审核、原生验证或 Gate。原报告仍由协调者按
既有反馈格式处理，不自动发布或持续安排；真实统计、Desktop 附着与 `T0/T1` 均不因此开启。
