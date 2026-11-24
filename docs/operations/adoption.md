# 接入现有 AI 工作流

从一个已有质量检查的项目和一项低风险真实任务开始。先确定 Agent 从哪里读取项目约定、用什么命令验收，再选择需要的接入方式。

## 选择接入深度

| 层次 | 当前用途与边界 |
|---|---|
| 工作约定 | 推荐起点。合并少量通用规则到目标项目已有指令入口，保留本项目原有安全与治理规则；不安装依赖、Hook 或后台服务。 |
| 项目验证 | 沿用目标仓库已定义的测试、静态检查与 required CI。没有检查时如实标缺失，不靠复制本仓 Python 命令制造通过结果。 |
| 完整 AI Flow | 仅在确实需要确定性任务分流、版本绑定审批与证据 Gate 时评估。版本化[资源包](resource-bundle.md)、Python/Node [非覆盖初始化](initialization.md)和[普通安装的 Node 本地验证](node-verification.md)已交付。完整接入的待验收项见[完整引擎边界](#完整引擎的跨仓库边界)。轻量试点可独立开展。 |

全局指令保存跨项目偏好，项目入口写本仓特有的约束、验证命令和授权边界。重复使用的流程可写成技能，`SKILL.md` 的描述说明何时调用，操作细节留在正文和引用文件中。[Agent Skills 规范](https://agentskills.io/specification#progressive-disclosure)

插件适合在支持它的宿主中分发一组技能、命令或连接配置。任务需要访问外部系统时，核实当前宿主实际暴露的 MCP 工具、具体操作及所需授权。仓库内已有 CLI 可以完成的验证，直接运行该 CLI。[ZCode 插件](https://zcode.z.ai/en/docs/plugin) · [MCP 服务能力](https://modelcontextprotocol.io/docs/learn/server-concepts)

## 先做只读盘点

核对 Git 根目录、当前提交和已有修改，再从目标项目的指令与 CI 找到验证命令及需人类决定的动作。如果普通 Git 克隆已有提交、根目录的 `.git` 是目录且存在 `.ai/`，可从根目录运行 `python -m aiflow init inspect --target .` 检查已有安装。保留工作区原状，缺少提交、测试或 CI 时记明缺项。

## ZCode 首批试点

以智谱 / Z.ai 的 ZCode Agent 为例，从项目根打开工作区。新任务依次读取用户级和当前工作区的 `AGENTS.md`，不会递归读取子目录或展开 import/include。将必须执行的规则写在入口，按需阅读细节。[ZCode 项目指令](https://zcode.z.ai/en/docs/agents#project-instructions-file)

1. 核对目标已有规则，只按需合并[项目规则片段](../../examples/adoption/project-rules.md)中缺少的条款，并查看 diff。
2. 在新任务用[试点提示词](../../examples/adoption/zcode-pilot-prompt.md)核对项目根与验证命令；有具体工作项时再执行。
3. 沿用用户的模型、费用和权限设置，按目标仓原有检查验收。记录这一次实际完成的动作和观察到的结果。

## 已登记的外仓试点

| 项目 | 当前约定 |
|---|---|
| `r3s-VPS` | 保留现有项目规则、`docs/PROJECT_STATUS.md` 和目标仓验证命令；发现实质问题或用户明确请求时按[反馈流程](feedback-loop.md)处理。远程访问、生产变更与敏感数据处置各按目标仓授权。 |
| `ai-agent-dotfiles` | 所有者已于 2026-10-10 暂停试点登记。继续使用 ZCode 维护该仓，恢复反馈试点须由所有者重新登记。 |

历史窗口、被测版本和当时的未验证项见[试点反馈](zcode-adoption-feedback.md)及[执行目录](../superpowers/plans/2026-09-12-zcode-review-fix-execution.md)。接手时读取目标仓当前状态。

## 真实任务的执行与收尾

- 从脚本和 CI 核实命令、写入位置和检查范围。接口或配置有变时，沿生产端到消费者走一条真实路径，检查最终结果；变更测试发现范围时说明新增、停用及替代检查。
- 分别记录本地检查、远端 CI 与发布的被测版本和结果。读取门禁自身的退出码，失败从该次原始日志定位；保留原始失败及重跑关联，对外仅引用脱敏摘录。
- 需要独立评审时，实现前列出设计决策点，实现后界定 diff 范围。按目标仓门禁复核发现，权限和发布仍按原有规则办理。
- 在项目现有进度入口记录提交、工作区状态、遗留项和证据。实测耗时、预算和超时分别记录；证据缺失写 `unknown`。按任务需要查阅[试点反馈](zcode-adoption-feedback.md)、[复盘](../archive/operations/zcode-retrospective-2026-09-20.md)和[效果观察口径](effect-observations.md)。

当前摘要可以沿用下面的结构，填入已有事实即可，不要求每个任务另建文件：

```text
当前候选：<commit/tree>；工作区：<clean/dirty/unknown，相关未提交范围>
正在做 / 下一步：<当前工作与尚未完成项>
验证：<局部、全量、CI 各自的结果和被测版本；未执行项明确列出>
运行前提与命令：<准确命令；用途；写入范围；隔离环境和必要前提>
证据 / 历史：<可读取脱敏摘要、失败与重跑记录、原有历史条目的指针>
```

## 将反馈应用回试点

仅为[仍在登记的试点](#已登记的外仓试点)处理有实质内容的反馈或用户明确请求。沿用[反馈与回灌流程](feedback-loop.md)，按目标仓授权验证、提交适用变更。普通收尾、版本差异或登记上一笔回执无需启动流程。新增项目须所有者登记。

## 如何判断值得推广

在接下来自然发生的同类任务中观察，不新建逐次填报或审批程序。
每个完成窗口由 Agent 根据已有事实汇总一次，复用
[效果观察口径](effect-observations.md#下一批真实工作如何观察)：

- 分开记录业务/风险决定、已有有效决定的重复请求、产品权限弹窗；看不到弹窗全量时写 `unknown`。
- 保留任务类型、提交范围、原有验证结果、明确返工和交付后缺陷观察状态。
  没有人类自报用时就写 `unknown`，不拿聊天等待时间或批准条数换算人时。
- 若有可比旧任务，按相同类型与观察窗口比较原始值、样本数及缺失项。
  没有对照或缺陷观察尚未结束时，只报告可用性，不宣布效率或可靠度改善。

当真实任务能在原有质量门下完成、重复流程请求没有出现且规则接入没有冲突时，
经所有者登记后可推广到下一个低风险项目；这只是渐进推广依据，不是统计上的效果证明。
若必需检查被跳过、边界动作越权、规则冲突或重复请求增加，暂停该项目的扩展，
先定位原因。只撤回这次新增的规则条款，保留用户改动、原有保护与失败证据；
不要删全局配置、历史账本或通过关闭保护恢复“流畅”。

## 再推广到 Codex 和其他工具

Codex 的[官方 AGENTS.md 文档](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
规定了从项目根到当前目录的指令发现，并在同目录优先使用 `AGENTS.override.md`。
这与 ZCode 的工作区入口不同；修改后需在新运行中核对实际加载的规则。
这里使用官方说明校准入口，不修改全局 Codex 设置或现有模型路由。

对其他 Agent，只适配其经核实的指令入口，不假设它会自动读取 `AGENTS.md`、
`CLAUDE.md` 或本仓的 Skill。纯聊天、文档类 AI 没有代码工作区和 CI 时，复用目标、
边界、验证证据与必要决定的原则即可，不要求伪造 Git task。
每次只推广一个工具与项目组合，复用已完成的项目检查，不反复让人确认相同事实。

## 完整引擎的跨仓库边界

当前 `0.2.0` 的[Quickstart](quickstart.md)针对 harness-model 的完整克隆。
仅安装 wheel 或执行 `pip install` 并不能把另一仓库变成 AI Flow 项目：

- 普通 wheel 分发 `src/aiflow` 及[版本化资源包](resource-bundle.md)：15 份 Schema、四份 Policy 种子和规格模板。
  安装不会创建目标 `.ai`；运行时仍需目标自己的 `.ai/repository-id`、Policy、Schema、模板与任务存储。不得复制本仓身份、历史 task、批准、证据或维护模式标记。
- 完整克隆内的业务 CLI 可从 Git 工作树根或内部子目录调用；内部任务、Policy、
  模板及默认 Schema 使用同一定位根，Schema 来自 `<root>/.ai/schemas`。
- 新 task 在 `freeze` 与首次 `classify` 前，由 Agent 按实际情况使用 `facts` 预览和录入显式风险事实，见
  [Quickstart 用法与恢复边界](quickstart.md#分类前风险事实录入)。命令只用于原 Git 绑定下、尚未冻结或分类的 `NEW` 任务，
  不推断缺省事实，不证明声明真实，也不授权执行；缺机械字段不是向人类求批的理由。
- 本仓 CI 命令、路径、85% / 90% 阈值及维护模式是本仓约束，不是外仓通用安装模板。
  外仓必须映射自己的质量检查与治理模式，不能通过复制 bootstrap 标记跳过原有 Gate。

`facts` 提供显式风险事实的本地录入入口，[PR #138](https://github.com/MaginaLW/harness-model/pull/138)已交付版本化资源分发。
[PR #140](https://github.com/MaginaLW/harness-model/pull/140)已交付 `init preview/apply/inspect/migration-plan`：
`native-python-v1` 面向已有提交、Python 源码及 `[project].name`、尚无 `.ai` 的普通 Git 工作树；
apply 限 Windows x64、CPython 3.11、本地 NTFS。它生成目标自己的 UUID，不覆盖旧配置；
精确恢复与重放边界见[初始化用法](initialization.md)。初始化不准备验证工具或依赖。
已交付 Node 非覆盖初始化、[本地 V0/V1](node-verification.md)及[普通安装的本地 V2](node-verification.md#revision-2-local-v2)。目标 Node CI、combined Gate 与真实 agent-bridge 接入待验收。当前状态见[维护收尾与待办](maintenance-status.md#版本与用途)。

CLI 的定位与兼容边界见[仓库根定位规格](../superpowers/specs/repository-root.md)：
无环境覆盖时使用最近 Git 工作树根；该根缺少 `.ai` 时拒绝，不借用父仓资源；
环境覆盖导致越过嵌套 `.git` 边界时拒绝。普通 linked worktree 使用自己的根。
业务命令在非 Git 或 bare 仓库中拒绝；help、version 和参数错误保持原有仓外行为。
调用过程不 `chdir`。用户文件参数 `--input`、`--options-file`、`--output`、
`--evidence`、`--action-file`、`--ci-run-dir` 的相对路径仍以调用目录为准。
根定位本身不执行初始化、目标资源写入或 CI 适配，也不授权复制源仓身份。

真实项目需要这一层时再按本仓 AI Flow 创建治理变更并验证干净外仓端到端流程；
它不阻塞轻量试点，也不授权自动恢复强制 task、阶段三/四、模型路由或可信外部执行器。
现有 [Hook wrapper](hooks.md)仍不执行或授权 push/merge，不能拿来伪装通用安全控制面。

已交付资源的构建与读取见[资源包用法](resource-bundle.md)，初始化命令与恢复见[初始化用法](initialization.md)；目标验证配置、完整接入及启动材料见
[完整引擎跨仓初始化方案](sdk-and-engine-plan.md#完整引擎跨仓初始化)。
同文另列[应用自管 SDK 客户端](sdk-and-engine-plan.md#应用自管-sdk-客户端)；两条路线互不依赖，
方案记录不代表开始安装、连接或真实调用，当前状态仍以[维护收尾与待办](maintenance-status.md)为准。

## 当前收尾边界

试点登记见[当前清单](#已登记的外仓试点)，产品与阶段门限见[维护状态](maintenance-status.md)。早期案例与当时的检查结果保留在[历史版本](https://github.com/MaginaLW/harness-model/blob/220242b156a79477f9cdbfd843ec15c304164177/docs/operations/adoption.md)。
