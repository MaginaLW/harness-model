# ZCode 试点收尾与跨 Agent 协作执行目录

日期：2026-09-12。用途：把当前任务、ZCode 实验和新增 Review–Fix–Verify 方案整合为
后续执行顺序。本次交付是状态核查、执行目录和交接样例；下列未完成工作没有因此执行。
这是日期固定的计划快照，目标项目的实时状态仍以各自原有任务入口为准。

## 1. 当前结论与推进顺序

继续在已经登记的 `ai-agent-dotfiles`、`r3s-VPS` 上完成真实任务和反馈闭环。近期重点是
**补齐已有交付的证据断点，再把已有独立审查经验组织成可移交的问题、修复与复核记录**。
先验证这种交接是否可用，再决定确定性内核需要增加哪些能力。

执行顺序：

1. **E1：现有试点证据收尾。** 分别确认 dotfiles 的全量收尾门和 r3s 的 CI 阻塞。
2. **E2：最小协作设计与交接准备。** 复用现有审核、验证和 Gate；定义轻量交接的边界。
3. **E3：一项真实工作完成双工具交接。** 优先复用现有审查案例；缺失历史证据不能补造。
4. **E4：按证据决定是否建设内核桥接。** 需要时拆出受治理任务，先离线验证。
5. **E5：条件性扩展。** 外仓初始化、真实 provider、阶段三/四分别满足自己的进入条件。

E1 的两个项目可独立推进，E2 可与只读证据核查并行；同一业务目录只有一个活跃写入者。
E3 实际修改须在目标仓已有任务范围与安全交接边界内进行。没有真实业务需求就不制造
试验修改，没有新反馈或适用版本差异就 no-op。

## 2. 核对基线与任务账本

| 对象 | 2026-09-12 本次读取结果 | 含义 |
|---|---|---|
| 本地工作分支 | `codex/zcode-document-pilot`，核查起点 `68f3dcb08fc563e997baf12ca80fa5f14f07ed92` | 相对 main 领先 13、落后 0；本次文档提交会继续推进该分支 |
| 远端 main | 只读 `ls-remote` 返回 `f633c036cc2a0394f7b1efb20efe4d91ba944255` | 与本地 main 一致；不能把试点分支上的方法说成已发布到 main |
| 远端交付 | 开放 PR 为 0；PR #38 已合并，受检 head `bbec6e0` 的 `ai-quality-gate` 为 SUCCESS | 历史 CI 不覆盖当前 13 个本地提交；未发现两个 ZCode 分支的远端同名 ref |
| 分支保护 | main 的 required check 为 `ai-quality-gate`，strict 和 enforce_admins 均启用 | 只读查询，不改变保护，不授予发布权限 |
| 本地已有改动 | 新增方案原稿为未跟踪文件，其他文件在核查开始时干净 | 原稿保留，本次不改写、不代为提交；本目录独立包含必要执行结论 |
| 阶段投影 | 阶段一、二完成：13/13 章、77/77 计划任务、408/408 步、24/24 exits | 计划计数不同于运行账本，也不同于外仓自己的 Phase 2 |
| 运行账本 | 46 tasks：38 MERGED、7 BLOCKED、1 APPROVED_FOR_MERGE | 没有正在实施的运行 task；7 条历史 BLOCKED 不是待重启队列 |
| TASK-0028 | `reverification_required`，Missing 为 `reverification`；当前 Gate 拒绝 10 项 | 与分支、HEAD 和工作区有关的本次快照；继续保留选项 C，不自动重验或 close |
| TASK-0047 | MERGED；Missing / Next 均 none | 原功能已交付，试点的后续记录不代表重新打开该 task |
| 治理与未来阶段 | 维护模式 active；Policy 2.3.0；phase-03 / phase-04 均 not_started | 阶段三进入门仍 blocked；本目录不改阶段状态或既有批准 |

核对来源：[overall state](../state/overall.yaml)、[维护入口](../../operations/maintenance-status.md)、
[阶段三输入](../../implementation/phase-03-entry-inputs.md)，以及本次只读 CLI / Git / GitHub 查询。
未切分支、未修改外仓、未调用 ZCode 或模型 API，也未执行目标仓测试或生产检查。

新增方案原稿为 `2026-09-12-harness-model_cross-agent_review-fix_plan_2026-09-12.md`，
位于本目录；读取时 SHA-256 为
`85ca4db1d74c138b54dffaf0cadf3ecbf0b70a65abfa486a90a7ebdd5e957a72`。
它以 main `f633c03` 为基线，标注“方案草案、非实施授权”。当前分支相对它没有 `src/`
或 `tests/` 差异，因此其已有内核能力判断仍可参考；试点状态和实施优先级须按本次更新。

## 3. ZCode 实验实际走到了哪里

证据分三类：**本次静态可复核**是已读取的固定提交、代码、规则和记录；**项目记载**是
目标项目对历史检查或执行的陈述；**缺失**表示没有可用结果或绑定。静态核对不等于本次
重新执行测试、独立重放生产任务或认证模型身份。

| 窗口 | 已有事实及证据强度 | 尚未闭环 / 下一步 |
|---|---|---|
| 本仓 2026-09-08 只读和文档试点 | TASK-0047 的两份 observation 保留只读读取和小范围文档修改结果 | 只证明有限接入行为，不重跑已经消费的历史授权，不当作编码效果数据 |
| dotfiles 首轮 `8bc666c` → `3a2ff6b` | 真实 Task 2/3，目标自报进度 6/52 → 20/52；五项反馈已进入本仓方法。部分原始测试摘要已删除，只能按项目记载保留 | 不补造旧摘要；继续区分局部、全量和 CI 的被测版本 |
| dotfiles SchemaVersion 后续窗口 | 固定源码可确认消费端漂移直到 `895c54f` 才修正；目标记录随后 `881047a` 的 Validate run `34430424975` 为 37/37、0 failure/timeout | 本次未读取该远端 run 原始结果；按项目记载保留历史成功，不能覆盖当前 HEAD。此前“曾修复”声明被后续事实纠正 |
| dotfiles Task 6 Step 3，实现 `0e04a2c`，收尾文档 `f54a4d6`，当前工作区干净 | 项目记载两段独立评审：设计前纠偏、diff 审查发现两个缺陷及一个失败注入缺口；两次评审取消后缩小范围。目标已记录应用 upstream `68f3dcb` | 状态入口虽写 36/52、Step 3 complete，但全量 `run-tests.ps1 -All` 最后仍记“未返回”，且是 closeout gate。实际被测 commit/tree 待回执确认，不能用文档提交代替；先取最终结果再判断 Step 4 |
| r3s 首次接入及第二反馈窗口 | 目标记录已持久化规则并有 R1、grok/x.ai 窗口；反馈形成非确定输出比较、逐层配置核对、脱敏摘录检查等方法 | 生产结果仅按目标历史记录陈述；本次没有访问生产，不将离线检查扩大为当前线上可用性 |
| r3s 当前 `df6b001` | 项目记载本地 Strict 16/16；该提交记录前一实现 `157a3b5` 的四次零步骤/未分配 runner 的 CI 失败。工作区另有 `docs/PROJECT_STATUS.md` 和 `tools/artifacts.manifest.json` 修改，追加 `df6b001` 的第五次同类失败 | 当前缺成功的双通道 CI 回执；额度原因仅为项目推测，先核实失败层次。未提交记录不能当作已交付；不自动重试、推送或生产操作 |

两个项目已经超过“首次接入待执行”的状态，本仓部分入口还保留该早期描述；本次更新
入口摘要，同时保留历史观察。本仓五项反馈还衍生出第六项“分阶段且限制范围的独立审查”。
dotfiles 已记录应用 `68f3dcb`；r3s 最新记录到 `3a0bb34`，第六项是否适用留到其安全收尾
时逐条评估，不能仅因 upstream 更新就覆盖目标规则。

dotfiles 首轮提到移出执行范围的 content-aware helper，后续 Task 5 已记载旧路线退休。
后续检查应追踪替代覆盖及发现范围连续性，不能直接安排“恢复旧 helper”。

外仓证据入口（相对于各自 Git 根目录，接手时重读当前摘要）：

- `ai-agent-dotfiles`：`AGENTS.md`、`docs/ZCODE.md`、`STATUS.md`、
  `status/active/live-safety-hardening.md`；固定 `f54a4d6` 的 `STATUS.md:3054–3055`
  及 active 记录 `1229–1231` 指明全量检查待返回，`tests/live-plan.tests.ps1:167–171`
  和 `STATUS.md:2836–2839` 说明旧路线退休。
- `r3s-VPS`：`AGENTS.md`、`README.md`、`docs/PROJECT_STATUS.md`、
  `tools/artifacts.manifest.json`；固定 `df6b001` 的状态文件 `221` 行记录 upstream，
  `232–241` 行记录本地检查和 CI 阻塞，`273–279` 行记录 R1 后续窗口。
  CI `34675240976`、`34675461981` 及随后两次重跑共四次尝试对应 `157a3b5`；未提交补记的
  `34677265695` 对应 `df6b001`。读取 HEAD 与 dirty diff 分别标注，不能混为一个版本。
- 本仓历史输入：[ZCode 反馈](../../operations/zcode-adoption-feedback.md)、
  [收尾方法](../../operations/adoption.md#真实任务的执行与收尾)、
  [反馈闭环](../../operations/feedback-loop.md)、[效果观察](../../operations/effect-observations.md)、
  [只读试点](../../../.ai/tasks/TASK-0047/zcode-readonly-pilot-observation.md)、
  [文档试点](../../../.ai/tasks/TASK-0047/zcode-document-pilot-observation.md)。

## 4. 新方案的取舍与现有实现衔接

| 原方案方向 | 本目录处理 |
|---|---|
| 在 harness-model 增量建设，不另建治理仓库 | 保留；不重复实现 Finding、批准、任务状态机和 Gate |
| W0 边界与兼容性设计 | 对应 E2。先冻结最小交接范围与现有接口映射；正式治理契约由后续独立任务完成 |
| W1 轻量双工具试点 | 对应 E1 + E3。先核对 dotfiles 已有案例，尽量复用；不默认从零启动 PINN-tFORM 等第三仓 |
| W2 内核桥接 | 对应 E4。由实际交接缺口推动，拆分契约、导入、修复关联、Gate 和恢复测试 |
| W3 外仓初始化、W4 provider | 对应 E5。按需分开，不阻塞轻量交接，也不把无头接口写成已可用 |
| W5 自动服务、模型选择、资源协作 | 保留在条件性路线；不能借 adapter 绕过阶段三/四进入门 |

现有实现有两个必须写进设计的约束：

1. `review_service.py` 已有不可变 review revision 和 Finding resolution。
   现行 review-record Schema 使用 `REV-*` / `RF-*`，Finding 状态只有 `open/resolved`，
   且禁止未声明字段。provenance、fix attempt 和拟议协作状态不能直接写入旧 JSON。
   新字段、兼容和映射须通过正式版本化设计；本次交接样例只是文本工作材料。
2. 正式 implementation review context 要求已通过的 verification evidence；V2 还绑定
   verification snapshot。轻量“先技术 review，再修复，再验证”不能直接当作正式审核顺序。
   Fix 后应先完成当前版本要求的 verification，再生成正式 implementation review context，
   按现有规则记录审核，V2 适用时完成 finalization，再运行 Gate。早期技术评论不冒充正式批准。
   现有 resolution 也不会把原 `REQUEST_CHANGES` 自动改为 APPROVE；新 subject 仍需有效审核。

辅助技术审查可以检查固定导出的未提交 diff，并记录 base、diff 摘要和 dirty 范围；正式
就绪判定要绑定已提交版本。修复后产生新提交或测试前后有字节变化，就核对新鲜度，
不能改一下 SHA 字段复用旧通过。不同 actor 标签也不构成可信身份认证。

## 5. 后续工作包与验收

以下 E 编号仅用于本执行目录，不是新建的 `TASK-*`，也不重编号原阶段。

### E0：本次规划交付

产出：本目录、[Review–Fix–Verify 交接样例](../../../examples/adoption/review-fix-verify-handoff.md)，
以及 README、维护状态、接入与反馈闭环的当前指针。原方案和历史账本保留。
本次不实现新增命令、Schema、Policy、采集器或 adapter，不推进外仓业务任务。

验收：文件关系和引用可读；旧状态与新快照有明确时间边界；只提交本次文档/示例；
完成第 7 节本仓必需检查。E0 完成不表示 E1–E5 完成。

### E1：两个现有试点的证据收尾（最高优先级）

**E1a / dotfiles：** 由目标项目任务接手者读取 `f54a4d6` 之后的最新记录，定位 Task 6
Step 3 最后一次全量检查的进程/CI/原始摘要及实际被测 commit/tree。实现提交为
`0e04a2c`，`f54a4d6` 是后续收尾文档，实际受检状态不能只凭这两个提交推定。核对回归发现范围、
修复后独立复核及最终提交之间的对应关系。在原有 active/STATUS 入口追加最终事实。
若历史结果已不可取回，明确记缺失；确有当前验收需要时，按目标规则重新执行一次当前
验证，使用新窗口，不回填历史。全量未完成或失败时不宣布 Step 4 准入。

**E1b / r3s：** 由目标项目任务接手者先确认现有两文件修改的归属与写入权；只读核对
当前 head 的两条 CI lane 和失败日志，区分平台调度、计费提示、环境与代码失败。
本地 Strict 与 CI 分别保留；缺少明确平台信息就记录 unknown。在原记录追加真实成功
回执，或清楚标记 `blocked_external`、所需外部决定及下一次检查条件；不得写成 CI PASS。
重试 workflow、付费或生产动作按该项目授权处理，本目录不授权这些动作。

退出条件：两个项目各自能给出“当前被测状态、检查结果、可读证据、剩余阻塞、下一步”。
允许收尾结果为有证据的阻塞；这种结果只完成诊断，不算交付验收成功，也不阻塞另一项目。

### E2：最小设计与准备（原 W0 / W1 准备）

执行范围：本仓 `docs/`、`examples/`；普通准备文档按维护模式处理。以本次样例为起点，
在 `docs/superpowers/specs/` 形成 `cross-agent-review-fix-loop` 的小范围设计：

- 逐项列出现有服务、字段和测试；标出复用、适配和必须新增的部分。
- 约定 repo/base/reviewed commit、来源、Finding 映射、修复前后版本、验收引用与证据等级。
- 说明正式 review 前置 verification、stale 处理、旧 Schema 兼容及无结果/失败的区别。
- 固定一项工作、一个 Reviewer、一个活跃 Fixer、独立复核的边界；复杂方案先评设计，
  改动后按限定文件评 diff。普通文档微调不因此新增强制审核环节。
- 先给出 guided 文本交接和离线验证场景；不定义正式 telemetry contract，不采集额外费用数据。

验收：逐项能力映射与可验证退出条件齐全；没有虚构 CLI、第二套权威账本、自动人审或
未验证的产品能力。治理契约实现仍留给 E4；若设计修改治理规则，按升级清单独立建 task。

### E3：用一项真实工作验证双工具交接（原 W1）

优先候选：dotfiles Task 6 Step 3 的已有 Finding / Fix / review 链。先检查能否在已有
材料中找到两个工具及独立会话的可核实来源、固定受审版本、逐项修复和复核关联。
材料足够就形成历史案例；材料不足只列缺项，下一个自然发生的小维护任务再前瞻记录。
不能把本次补写样例当作历史当时使用过的交接包。

若该任务仍未通过 E1a，先完成其收尾；若所有候选均不适合，维持准备完成，不额外制造
业务改动。r3s 可在 CI 阻塞处置且写入权交接完成后作为备选，首次闭环选离线维护范围。
PINN-tFORM 仅保留候选，不在此次两个登记试点内自动推广。

操作：按交接样例绑定版本 → Reviewer 报问题与覆盖范围 → Fixer 最小修复 → 项目必需
检查和独立复核 → 在原有任务记录收尾。一个 Finding 建议最多两轮修复，仍失败就整理
原因和下一步，不无限重试。工具无额度/无结果保留状态，不擅自改计费通道。

验收：至少两个产品可围绕同一问题链移交，接手者不需重述完整聊天；有效问题逐项给出
验证、拒绝、重复或延期理由；无法完成要明确停止。没有 Finding 的审查可以证明审查交接，
但不能单独证明 Fix–Verify 链可用。只有版本与复核证据齐全才声明该案例闭环；不声称统计收益。

### E4：根据试点缺口建设内核桥接（原 W2，待后续选择实施）

进入条件：E2 设计和 E3 证据足以指出具体缺口，且用户选择实施该范围。对
`src/aiflow/**`、`.ai/schemas/**`、`.ai/policy/**` 或 CI 变更使用新的 AI Flow task；
安全文档/样例与治理面分开。先运行 status，补齐 Missing 中的机械步骤，只有真实所需
决定才请求人类，批准不能由本计划或旧 TASK-0047 代替。

| 顺序 | 产物与依赖 | 必需验收场景 |
|---|---|---|
| E4.1 契约与兼容 | 基于现有 Review/context/Finding 定义版本化来源、fix attempt 和映射 | 旧记录仍可读且字节不改；缺来源、非法/超长输入和未知优先级被拒绝或隔离 |
| E4.2 guided 导入/导出 | 依赖 E4.1；经校验才进入确定性记录 | 重导入 no-op；编辑产生新 revision；错误 repo/head 零写拒绝；文本不执行命令 |
| E4.3 修复、复核与 Gate 桥接 | 依赖 E4.2；复用当前 verification/review 顺序与新鲜度 | 自称已修复、旧 SHA、遗漏检查、范围越界不通过；新提交使旧结果重新判定 |
| E4.4 故障与自举 | 依赖 E4.3；离线 mock/guided provider | 中断可接续，损坏输入拒绝、重试受限、历史兼容、required 质量门全部保留 |

退出条件：离线可重放完整闭环，旧任务和 CLI 兼容，正式门禁仍由原引擎判断。
这只证明确定性桥接，不证明远端 provider、无人值守或外部动作执行器。

### E5：条件性后续路线（原 W3–W5）

- **外仓完整引擎：** 只有目标确实需要强治理时，设计非覆盖初始化、新身份、资源分发、
  root/worktree 定位、项目检查映射和恢复；轻量试点不以此为前提。
- **真实 provider：** 一次核实一种接口，另行确定数据与费用边界；覆盖超时、取消、分页、
  来源编辑和重复结果。没有结果不等于零 Finding，也不虚构 ZCode 无头命令。
- **阶段三：** 保留现有三个缺口——足够样本及隐私/偏差边界、真实 V3 用例与沙箱回滚
  边界、版本化费用/返工/审核缺陷/工具失败口径。当前只积累原有事实和候选输入。
  既有进入文档对“telemetry 是进入条件又是进入后产物”的先后表述，留给入口评估明确
  “候选输入、设计批准、正式契约”的界线；不能用措辞调整宣布门已通过。
- **阶段四：** 持久队列、租约、锁、暂停恢复与调度等仍需阶段三退出证据和量化协调需求。
  两个项目已用同一规则不等于已经需要独立编排器。

## 6. 交付、回灌与明确保留项

本分支已有 13 个本地提交，既包括方法，也包括试点授权记录和模型职责配置。将来发布前
按当前 diff 复核整个待交付范围、质量证据及批准，不能把它误报成“只有本次几份文档”。
本次仅作本地阶段提交；push、PR 外部写入、merge 和分支清理另按现有规则处理。

方法回灌继续按[原闭环](../../operations/feedback-loop.md)，仅在目标项目真实任务收尾且
写入权明确时逐条适配，记录实际已验证 upstream。r3s 的既有 Strict/独立审查和 manifest
要求不降低。本文不是让两个外仓立即同步，也不新增自动化定时器或后台采集。

TASK-0028 选项 C、七条历史 BLOCKED、旧候选/worktree、B0–B2 停止/B4 暂缓均保持原处置。
不为统计清零重验历史任务，不用当前代码通过结果覆盖旧失败。

## 7. 后续接手与检查入口

在 harness-model 根目录先执行下列只读命令，再按当前任务范围决定下一步：

```powershell
git status --short --branch
git rev-list --left-right --count main...HEAD
uv run --locked python tools/analysis/approval_overhead.py --format text
uv run --locked python -m aiflow status TASK-0028
uv run --locked python -m aiflow status TASK-0047
```

本仓 docs/examples 修订也保留完整质量门：锁文件与契约检查、全量 pytest、总覆盖率
至少 85%、diff coverage 至少 90%、whitespace、Ruff、format、mypy。实际命令以
[workflow](../../../.github/workflows/ai-quality-gate.yml)为准；输出使用获准的临时位置。
无可执行差异时记录“无可执行行”，不编造 100%；Windows skip 单列，不能充当 Linux
CI 通过。若干净克隆检查依赖已提交候选，先复核并仅提交本次文件，再完成验证；失败时
保持候选未验证，不回灌或发布。目标项目使用自己的检查，本仓结果不能代替 E1 的外仓回执。

接手提示词：

```text
读取 AGENTS.md 与 docs/superpowers/plans/2026-09-12-zcode-review-fix-execution.md，
先核对 Git、当前任务入口和证据状态。下一步优先 E1 的现有试点收尾和 E2 的最小设计，
两者可分开推进；已存在且有效的结果直接复用，缺失项显式记录。
仅执行本次指令实际授权的仓库和范围。没有外仓业务授权时，完成本仓 E2 的文档准备，
给出 E1 的明确交接缺项，不代为启动外仓任务。用原有状态入口记录事实，不新建平行账本。
治理代码走独立 AI Flow task；未获准时不进入 E4/E5，不调用付费 provider 或执行外部动作。
交付说明完成了哪个 E 项、固定版本、检查和残余限制，不能只说“方案已完成”。
```
