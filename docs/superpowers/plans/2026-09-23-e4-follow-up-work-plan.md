# E4 启动前交接与后续工作计划

## 2026-09-30 最新核定与后继准入

本轮实际 CLI 确认 `TASK-0048` 为 `MERGED`、`Missing: none`；本次同仓
Windows/Linux 接入、同 SHA 双 lane、main 采用、真实 guest 重启后业务、串行恢复、
正式 V2 与治理关闭均已完成，见[任务 02 执行目录](2026-09-13-runner-infrastructure-execution.md)
和[发布关闭记录](../../../.ai/tasks/TASK-0048/publication-closeout-001.md)。不重复注册、
执行 CI 或关闭该任务；当前 guest/runner 在线状态仍须当次观察，不能沿用历史回执。

E4.1 契约与本地验收已经由 `TASK-0054` 完成，分支为
`codex/e4-external-review-contract@fd560d9`，实现 subject 为 `23793f7`。
本轮恢复该分支检出后实际 `validate` 通过，`status` 为 `APPROVED_FOR_MERGE`、
`Missing: external_merge`，批准为 `current`、证据为 `passed`，`gate` 为 PASS。
下方 A–C 及“工程实施未启动”保留 2026-09-23 的计划时点，不要求重复已完成的工作。

已提交 V1 审核包中的单元 1656 passed、全量回归与覆盖率重跑各 2294 passed、
总覆盖率 88.12% 和可统计差异覆盖率 100% 均为历史结果，本轮没有重跑。
旧忽略目录中的原始日志是否可恢复尚未确认；当前结构与治理核对不等于原始日志
已恢复，也不代表远端 CI、推送或合并已经完成。

接续从下方 D 的 E4.2 独立治理规格与设计准入开始：本轮在
`codex/e4-report-import` 准备 `TASK-0055`，先冻结原件加载、来源/目标匹配、
预检与不可变记录边界，再按当前 CLI 缺项取得准入。E4.1 的发布与合并是独立
工作线，不作为本地后继规格准备的额外前置；推送、合并及新增外部动作另需授权。
I1 其余生命周期、I2 更多目标、E5、I5 与阶段三/四仍按原条件选择；三份未跟踪
用户草稿和阶段 61 的旧 index 保留。本段只校准最新入口，下方历史计划完整保留。

状态：计划已整理，工程实施未启动。接手时以本文件和
[启动前规格](../specs/2026-09-23-zcode-report-import-preflight.md)为入口；
本文件安排顺序、职责和验收，具体契约语义仍由规格维护。

> 2026-09-27 更新：dotfiles `codex/ci-regressions-e4-preflight@3b835f1` 已通过
> [合并提交 `68ef2ec`](https://github.com/MaginaLW/ai-agent-dotfiles/commit/68ef2ecedca3e9071178dcab8b805cecdafbba53)
> 进入 `main`；[`main@6c814f1` 的完整 Validate](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/36303730680)
> 四个 job 均成功。下方 2026-09-23 的分叉基线与 dotfiles 独立集成工作包保留为历史快照，
> 不再重复集成；来源见[外仓整合记录](https://github.com/MaginaLW/ai-agent-dotfiles/blob/6c814f18e981edfa1cad7185915ed7c177857bc0/status/active/live-safety-hardening.md#L4121-L4149)。

## 1. 本次交接基线

2026-09-23 的只读核对如下；执行后续任务时重新取得当时基线。

| 对象 | 已核定事实 | 接手含义 |
| --- | --- | --- |
| harness-model 本地 | 收尾提交 `eda49f7c67d2a424884f0bea833bd0f31fc2a4dd`；tracked clean，三份用户草稿保留未跟踪 | 本计划随后独立提交；不把草稿纳入候选 |
| harness-model 远端 | main `48bf777106b9fdfef1ddf83d3abc95859fb8e580`；原分支 `codex/self-hosted-runner-inventory` 为 `a8bfdf0d00d90371baca287e8310908555dc9d66` | 本地待发布差异还包含 TASK-0053 的既有追加记录，不能按“仅这份计划”判断整个推送范围 |
| dotfiles 修复分支 | `codex/ci-regressions-e4-preflight` 为 `3b835f143616c91fff3249ba7881996ea4876cf7` | [固定 CI](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/35873759132) attempt 1、四个 job 成功、42 套件全部通过 |
| dotfiles main | `48f17e1565b4f6b95a1f904c9ebce2cda6f5484b` | 与修复分支共同祖先为 `627ef3f`，main 侧 7 个提交、修复侧 3 个提交；修复分支尚无 PR |
| E4 | E3 最小真实案例已完成；所有者已选定“将 ZCode 审查报告校验并导入既有 AI Flow 任务” | 下一项为 E4.1；不重做 E3，不把方向选择再次列为缺项 |

[上一阶段收尾记录](../../operations/e4-preflight-closeout-2026-09-23.md)绑定修补及验证事实。
私有证据集合 `E4-CI-REPAIR-20260923` 保留 README、三个 CI 回执及原始日志；
最终 CI 回执 SHA256 为 `c5d967bbe2f8987d6d89245e0ae5ddfdb512483e60f4480a2224c855883eff63`。
本次不覆盖这些回执、旧失败或既有账本。旧 `harness-env` 超时根因仍 unknown。

## 2. 推荐主线：E4.1 → E4.2

优先开始 E4.1 的治理准入。dotfiles 集成和主仓记录发布是独立工作线，不作为
E4.1 契约实现的额外前置。下表的 sub-agent 数均不含主 agent；总并发容量为两名。

| 阶段 | 工作与依赖 | sub-agent 数与职责 | 完成条件 |
| --- | --- | --- | --- |
| A：E4.1 准入 | 串行固定基线、创建独立治理 task、运行实际分类、冻结规格、设计审查，并按 `status` 的 Missing 项推进 begin | 办理步骤 0；设计审查时顺序启用 1 名独立只读 reviewer，主 agent 处理反馈 | CLI 确认实际准入；不预填 task 编号、风险等级或批准结论 |
| B：E4.1 实现 | 依赖 A；先冻结字段，再并行编写契约和安全样例 | 1；独占五份测试/fixture，主 agent 独占两份治理文件 | 独立 `external-review` 契约注册，C1–C4 定向检查通过，旧格式不放宽 |
| C：E4.1 验收 | 依赖 B；固定候选后，主 agent 执行完整必需检查 | 2；分别只读审查契约/来源边界、兼容/测试覆盖；不互写文件 | 完整测试、85% 总覆盖率、90% diff coverage、whitespace、Ruff、format、mypy；正式审查和 Gate 按实际任务要求完成 |
| D：E4.2 设计 | 依赖 E4.1 契约验收；串行冻结目标选择规则、输入契约、导入入口和合成样例，再完成治理准入 | 办理步骤 0；设计审查时顺序启用 1 名独立只读 reviewer | 目标选择/来源映射规则、预检/记录协议及不可变落盘边界可验证 |
| E：E4.2 实现 | 依赖 D 准入；模块接口冻结后并行推进，文件归属在该 task 中列出 | 2；一名负责加载/预检单元，一名负责安全测试；主 agent 负责记录/CLI 集成 | I1–I7 通过，随后完整必需检查和独立审查；旧 Review/approval/evidence/Gate 含义保持 |
| F：真实导入验收 | 依赖 E；使用与目标任务匹配、来源经核定的真实 ZCode 报告 | 1；只读核对原件、绑定和结果；主 agent 串行执行消费动作 | 原件/目标匹配，重复输入 no-op，错误或漂移零写拒绝，真实结果可追溯 |

若主线与独立工作线同时推进，最多保留两名 sub-agent；例如 B 的测试占一名，
另一名可做 dotfiles 只读集成差异审查。C、E 已占满容量，其他工作排队。
发布、合并、任务状态变更和最终集成均由主 agent 按依赖串行执行。

### E4.1 的固定最小分工

- 主 agent：新 `.ai/schemas/external-review.schema.json`，以及
  `src/aiflow/contracts.py` 的一项 registry 登记。
- 测试 sub-agent：`tests/unit/test_contracts.py`、
  `tests/fixtures/contracts/valid/external-review.json`，以及 invalid 目录中的
  `external-review.extra.json`、`external-review.invalid.json`、`external-review.missing.json`。

治理与安全单元分开走对应流程；维护模式允许的安全测试可 task-free，拆分不减少
所需批准。字段未冻结时先准备样例结构，Schema/登记就位后才串行运行集成验证。
设计冻结时确认字段/version、仓库标识的核定映射、各阶段 base/subject 规则、
未完成原因和资源上限。原件受审对象必须与目标 context 分别表达；摘要不认证身份。
E4.1 仅提供契约校验，不宣称现有 `aiflow validate TASK-ID` 已获得导入能力。

### E4.2 的实际输入和停止点

开始 D 时冻结目标选择规则、输入契约和合成样例；到 F 取得真实报告后，重新固定
当时目标 task、仓库、阶段、base/subject/context 摘要，以及原报告版本、原件 SHA
和经核定的 `source_subject`。匹配目标的真实 ZCode 报告属于 F 的验收材料，
**不是 A 的前置缺项**。已有 dotfiles/51044a55 原报告保留为错目标负例；
离线正例标明 synthetic，不修改真实报告来制造匹配。

导入按“零写预检 → 核定完整输入 → 明确记录并重新校验 → 不可变附属记录”实施。
同版本相同完整输入 no-op；同版本内容或映射冲突拒绝；新版本追加。
重复 JSON 键、原始字节上限、漂移和路径边界属于 E4.2 加载/写入层验收。
不执行报告文本，不将 F1/P1/verified 自动提升为正式 Finding、severity 或批准。
只按所选消费动作完成 guided 导入；E4.3/E4.4 另按真实关联或恢复缺口决定范围。

## 3. 独立工作线及优先级

| 顺序 | 工作包 | 分工与验收 | 与 E4 的关系 |
| --- | --- | --- | --- |
| 可与 A/B 并行 | dotfiles 修复集成 | 主 agent 在独立检出核对当时 main 与三个修补的逐项必要性；1 名 sub-agent 只读检查生产改动影响。保留适用断言，处理冲突后固定新候选，运行针对性验证和新候选完整 CI；按现有有效授权及缺项执行发布/PR/合并 | 旧 42/42 不能覆盖合并后的源码；不自动整合原仓工作，不阻塞 E4.1 |
| 需要发布记录时 | harness-model 收尾记录发布 | 先核对远端到完整候选的所有差异，识别既有 TASK-0053 追加记录；按升级清单处理发布 task。1 名 sub-agent 做候选范围/证据核对，主 agent 串行执行验证和已获授权动作 | 不复用旧固定候选的动作批准，不要求为发布记录而实施 E4 |
| 次要诊断 | harness-env 超时可观测性 | 若选定维护工作或自然复发，先保留真实两流/阶段日志并做受控超时复现；0 名 sub-agent，单写入者。以成功捕获诊断为验收，不提高预算来宣称根因解决 | 当前没有已定位的生产缺陷；不重复跑完整 CI 只为制造新样本 |

推送、PR、合并等外部动作在执行时核对当前授权覆盖；已有有效授权直接沿用，
只补实际缺项。本次计划不新增这些动作，也不请求空泛批准。
运行 dotfiles 组合树测试前，先证明 public CLI 夹具的 RepoRoot、身份与默认路径
均指向受控隔离对象；生产路径变化可能改变旧拒绝分支，不能直接在宿主沿用旧前提。
合并后另核对远端状态、提交父子关系和实际 required CI，不能以本地 `close` 替代。

## 4. 保留项与接手清单

E5、扩仓/更多平台、真实 provider、通用可信执行、阶段三/四保持条件路线。
阶段三的样本充分性与隐私/偏差规则、真实 V3 沙箱及回退案例、版本化度量须另行满足；
阶段四还依赖阶段三退出证据与真实协调需求。TASK-0028 选项 C 和历史 BLOCKED
处置保留，不因计划更新自动恢复；不把账本历史数量当作新增待办数量。

下次接手按以下顺序完成一个可验收阶段：

1. 读本计划、启动前规格和维护入口；核对 Git、当前写入者及任务状态。
2. 从 A 开始 E4.1 准入；若选择独立集成工作线，使用独立检出并固定其版本。
3. 按表中职责委派，先确定文件独占范围，再开始写入。
4. 完成该阶段检查、复核与小步提交；报告实际候选、已执行验证和未执行范围。

本次交付仅更新计划和入口：本地阶段提交，链接/历史保全/文件范围检查；
未创建 E4 task、begin、改内核、重跑 CI 或执行远端写入。
