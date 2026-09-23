# ZCode 报告导入：E4 启动前规格

状态：启动前准备；尚未实施 E4.1 或 E4.2。所有者于 2026-09-23 选择的实际消费动作是
“将 ZCode 审查报告校验并导入既有 AI Flow 任务”。本文件把该选择收敛为可分类、可评审的
最小输入，不授权通过外部报告批准任务、调用 provider 或执行报告中的指令。

## 1. 需求、证据与固定边界

[E2 设计](2026-09-13-cross-agent-review-fix-loop.md)和 E3 最小真实双产品文档案例已经完成。
[本轮缺口核查](../../operations/e4-gap-assessment-2026-09-23.md)证明现行
`review record --input` 接收本项目的结构化 Review，而不是自然语言报告导入器：
外部 F1、verified、来源与 fix attempt 不能直接塞进现行 RF/status/顶层字段。
原核查时只有人工引用需求，因此没有选定内核范围；本次所有者新增了明确的机器消费需求。

实际 E3 原报告 SHA256 为
`80e9ebd7de1891a214075741a88abd134518195ceee6edcfd927855ac6e77ecd`，受审仓库为
`ai-agent-dotfiles`，受审提交为 `51044a55fc0dd8991e2ac25dad36fb1369a9027b`。
该报告只复核两份目标文档，不能作为 harness-model TASK-0053 的正式实现 Review。
将原件及经核定的 dotfiles/51044a55 `source_subject` 指向该不同仓库的既有任务，
必须在比较后、写入前拒绝；这是可使用真实输入的负例，不是凭 SHA 自动理解原文。
成功导入的正例在 E4 实施时用明确标注的离线 fixture 验证，之后另用匹配目标任务的
真实 ZCode 报告验收。不得把修改真实报告中的仓库/SHA或合成会话当作真实产品证据。

最小能力缺口是：没有受确定性校验约束的外部报告来源和问题引用容器，可作为当前
AI Flow task 的附属记录。第一批选 E4.1 契约与兼容；写入服务/CLI 留给后继 E4.2。
旧 Review、Finding、evidence、approval、状态机和 Gate 含义保持原样。

## 2. 第一个实现单元：E4.1 契约与兼容

拟新增一个独立版本的 `external-review` 契约及明确标注的正/负 fixture，并登记到现行
contract registry。它不是 `review-record` 2.0，不迁移旧记录，不复用 REV/RF 名字伪装
已完成正式审核，不加入 approval 或 Gate 的放行条件。

拟实现范围只包含独立 Schema、contract registry 的最小登记及对应契约检查；
治理文件与安全样例/测试按仓库约定拆分。实际文件清单、任务基线、Policy 摘要与分流
在新 AI Flow task 冻结前从当时 HEAD 重新取得。本准备阶段不创建虚假的冻结批准或
把预计 REVIEW/V1 当作 CLI 已分类事实。

建议的 Schema 1.0 输入由操作者从原报告核定并填写，不自动解析任意 Markdown，
不从措辞猜测严重度、完成状态、模型或身份。字段族如下：

| 字段族 | 必须表达的事实 | 校验与边界 |
| --- | --- | --- |
| 格式 | 独立 artifact kind 与 schema version | Schema 拒绝未知版本和字段；重复 JSON 键由 E4.2 原始字节加载器拒绝 |
| 目标 | target_context：task_id、repository_id、review_stage、base、subject（implementation）、context_sha256 | 从目标现行 context 核对；design 不添加虚假的 subject/evidence |
| 原件受审对象 | source_subject：原报告实际受审仓库标识、阶段、base、subject 及事实出处 | 与 target_context 分开；经操作者核定的原件事实参与比较，缺失或 unknown 不得进入通过校验的记录 |
| 来源 | product=ZCode、不含鉴权的来源定位、报告版本/原始字节 SHA256、取得方式 | 无法公开的定位用私有保管标识；不存访问凭据；声明不等于身份认证 |
| 完成状态 | completed / incomplete / tool_unavailable / timeout、实际覆盖及未审范围 | completed 且 findings=[] 才可表达完成零问题；其余保留未完成原因 |
| 外部问题 | 原问题 ID、标题、受审文件/行、原始优先级或 unknown、报告内证据定位 | F1/F2 原值保留；不自动改为 RF 编号或把 P1 猜成 high |
| 映射建议 | 可选的现有 task/review/finding 复合引用，或待映射标记 | 不按标题/行号自动合并；跨 review 的同号 RF 不等价 |
| 复核表述 | 原始处置/复核结论及其来源引用 | verified/resolved 自述不能升级为现行 evidence 或可批准 Review |

模型身份、费用和独立性认证可为 unknown；它们不阻止原始来源附属材料被校验保管，
但也不会被填充成虚假已认证事实。不明严重度允许作为原始待映射值保留，禁止据此
生成正式 Finding。缺来源、错误版本或无法核对原件摘要则不得成为通过校验的导入输入。

原件 SHA 只绑定字节，不能证明 envelope 对原文受审对象的描述真实。第一版要求操作者
核定并记录 `source_subject` 的原文出处及核定方式；导入器比较这些已提供的结构化事实，
不声称自动理解 Markdown 或认证操作者声明。来源对象尚未核定时，预检报告缺项，
不把填写了合法 target_context 的任意原件当作匹配报告。真实错仓负例必须保留
dotfiles/51044a55 的 source_subject，不使用篡改后的来源事实构造通过结果。
来源仓库标识应携带标识种类：已有 AI Flow UUID，或不含凭据的仓库定位。后者与目标
UUID 的对应关系必须有明确核定记录，不能按仓库简称猜测或为未接入 AI Flow 的仓库
虚构 UUID。E4.1 冻结时确定该映射的具体字段及 fixture，E4.2 不接受缺少映射的记录。

拟定资源上限：单 envelope 256 KiB、最多 200 项问题、每项最多 32 条证据引用，标题
最多 512 字符，单段说明最多 8192 字符。原始大报告通过独立原件保管与摘要引用，不
以内嵌无限文本绕过 envelope 限制。这些是待新 task 冻结的工程选择，不是现有门禁。
项数和字符上限属于 E4.1 Schema；原始字节上限和重复键检查属于 E4.2 加载器，
不把 JSON Schema 对已解码对象的校验说成原始输入检查。

## 3. 后继 E4.2 的导入协议约束

E4.1 只交付可校验格式。后继导入命令名和路径由对应 task 冻结，需满足以下顺序：

1. 默认只预检：读取 envelope 和指定原件，检查长度、语法、路径/凭据边界与原件 SHA；
   外部命令、链接和建议始终是数据，不访问远端、不执行脚本。
2. 读取现有目标 context/status，核对任务、仓库、阶段、base、subject 和 context 摘要，
   并逐项比较独立 source_subject 与目标对象，缺失、未核定或不一致均拒绝。
   失效/不匹配拒绝且整个任务目录零写入；不得先补历史 context 再接受旧报告。
3. 输出结构化预检结果、缺项及拟写入的不可变附属记录。成功预检不等于导入、
   正式 Review、code approval 或 Gate；预检不重跑验证器。
4. 只有明确选择记录模式且当前任务允许该写入，才重读输入/原件/绑定后写入当前 task
   的附属来源记录。预检与写入之间变化必须拒绝，不能复用先前成功。目录应位于
   `.ai/tasks/<TASK-ID>/external-reviews/`，最终路径规则由实现 task 确定。
5. 同一来源版本、原件 SHA 和任务 context 的完整规范化输入相同才是 no-op。
   同一来源版本的原件、映射、覆盖范围或其他输入字段变化均拒绝冲突；明确的新来源
   版本追加新记录和前版本引用，不覆盖旧字节。
6. 不修改原 Review/Finding/approval/evidence，不执行 resolve，不自动追加现行状态
   事件，不替换最新正式审核。任何后续转换必须由原有 Review 接口及完整版本规则处理。

这一窄范围不实现 fix-attempt 自动编排、两轮重试策略、provider、无人值守服务、
自动审批、写外仓或 E4.3–E4.4。已有 evidence/Gate/approval 判断继续作为唯一正式入口。

## 4. 可执行验收矩阵（实施时运行，当前是预期）

| 编号 | 输入或动作 | 必须观察到的结果 |
| --- | --- | --- |
| C1 | 新契约合法零问题、合法含问题、未完成报告 | 格式合法但完成语义可区分，不转成正式通过 |
| C2 | 缺来源或受审对象、unknown schema/field、超过项数/字符上限 | Schema 可定位错误；拒绝；不写正式记录 |
| C3 | 外部 P1/unknown、F1、verified | 原值可保留为附属来源；不自动映射为 severity/RF/status |
| C4 | 所有旧 contract fixture 与 CLI 回归 | 决定和旧文件字节不变，旧格式不被放宽 |
| I1 | 当前任务匹配、来源和原件摘要一致；执行预检 | 给确定性候选与缺项，任务目录零写 |
| I2 | 同样输入明确记录两次 | 首次一个不可变附属记录，第二次 no-op，不重复处置 |
| I3 | 同来源版本改原件/映射/覆盖、旧 subject、错 repo/base/context、预检后漂移 | 写入前拒绝，整个任务目录逐字节相同 |
| I4 | 真实 dotfiles 报告及经核定的 dotfiles/51044a55 source_subject 指向 harness TASK-0053 | 比较独立来源与目标后拒绝错配；不声称仅凭原件 SHA 识别原文语义 |
| I5 | incomplete/timeout、命令式注入、私有鉴权参数或路径逃逸 | 保留未完成或拒绝输入；不执行、不泄露、不升级状态 |
| I6 | 正式 Review 已批准后仅导入旁路报告 | approval/evidence/Review/Gate 行为保持原契约，不因来源文字改变结论 |
| I7 | 重复 JSON 键、超过原始字节上限、source_subject 缺失/未核定 | 加载或绑定阶段拒绝，任务目录零写入 |

C1–C4 属 E4.1；I1–I7 属后继 E4.2，不把未实现场景计为通过。
实现保持完整必需测试、85% 总覆盖率、90% diff coverage、whitespace、Ruff、format、mypy。
原始失败、旧审批及 evidence 不重写；发布/合并另按原项目动作约束处理。

## 5. 启动前检查与阶段停止点

- 已有：E2、真实 E3 最小文档案例、现行边界的 19 项回归与六个表示探针、所有者明确选择的消费动作。
- 已准备：最小 E4.1 范围、契约字段和未知值边界、后继导入协议、正负验收矩阵。
- 待本 goal 的 CI 修复收尾：两项 dotfiles 测试失败的 RED/GREEN、固定候选完整检查、独立复核和实际结果记录。
- 真正开始 E4 时才执行：固定当时基线，创建独立治理 task，完成 CLI 分类/规格冻结、设计审查及其实际 Missing 项，然后 begin。
- 本轮停止在启动前材料；不调用 E4 begin，不修改 src/aiflow、Schema、Policy 或旧账本。

现有 dotfiles disposable-identity lab 的 setup/tool-cache ACL 缺陷属于该项目发布候选
的独立拒绝原因。修复 CI 测试不能把它改判为生产接受，也不要求在本 E4 准备中修复或
绕过它。E4 导入协议本身不依赖对真实 live home 的部署验收。
