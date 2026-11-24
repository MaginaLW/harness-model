# 维护收尾与待办

## 当前状态

本页只回答当前能力、版本、阻塞和下一步边界；规则以 [AGENTS.md](../../AGENTS.md) 为唯一权威，操作流程见[低干预工作方式](low-intervention.md)。历史计划和 NEW/BLOCKED 任务不是执行队列。

**当前方向：仓库维护。** 入口治理和已授权的维护收口已完成，后续按具体需求或可复现问题推进；Stage B、旧 mutation 加固、真实评分、自动审核、Desktop 附着及 Phase 3/4 继续暂停。维护交付不自动恢复这些工作，Policy、授权和质量阈值保持不变。

**G（影子验收）暂缓。** 保留现有配置，暂不新增 App。

**治理资料归属**：[治理建议](../archive/operations/HARNESS_MODEL_GOVERNANCE_RECOMMENDATIONS.md)与[执行计划](../archive/operations/HARNESS_MODEL_GOVERNANCE_EXECUTION_PLAN.md)已从 dotfiles 归入本仓，原文按规划时点保留；其中“待执行”“本次未执行”描述原文编写阶段。实际治理已由 [PR #154](https://github.com/MaginaLW/harness-model/pull/154) 合入：P0/P1/P2/P5 收口，P3/P4 按证据不实施；入口固定集合字符减少 53.62%，实际 token 与自然任务工时效果未测。Stage B 与旧加固仍停止。

### 版本与用途

| 对象 | 固定版本与用途 | 可用结论及限制 |
|---|---|---|
| 主线与原候选 | [PR #185](https://github.com/MaginaLW/harness-model/pull/185) 的合并提交 `0526983f` 是 #186 候选的历史基线，包含 [PR #181](https://github.com/MaginaLW/harness-model/pull/181) / `TASK-0163`、收尾 [PR #183](https://github.com/MaginaLW/harness-model/pull/183) 和文档同步 [PR #184](https://github.com/MaginaLW/harness-model/pull/184)。随后合入的 [PR #188](https://github.com/MaginaLW/harness-model/pull/188)（`285bcee3`）记录了暂缓 G 影子验收的决定。原候选 [PR #169](https://github.com/MaginaLW/harness-model/pull/169) 已关闭，原分支保留在 `a78bcc80`。 | 可用 `git branch -vv` 确认本地 `main` 跟踪 `origin/main`；[任务记录](../../.ai/tasks/TASK-0163/task.yaml) |
| V2 变异归因候选 | `codex/mutation-attribution-0526983f` / `2dd4e8e7`；[PR #186](https://github.com/MaginaLW/harness-model/pull/186)（`TASK-0175`，替代并关闭 [PR #180](https://github.com/MaginaLW/harness-model/pull/180)）。 | Windows V2 与私有 Ubuntu V2（`--ci`）14/14 及本地双端 Gate 通过，7 份私有原件仅留存本机；公开 `ai-quality-gate` 因缺本地原件保持阻塞，未合并。 |
| 治理修复的收尾基线 | `main` 合并提交 `3ef032a1`。TASK-0162 的账本已记录实现合并提交 `94632d43`，状态为 `MERGED`。 | 下列源码、安装包及跨仓候选各自绑定固定提交和验收结果，即使版本号相同也须核对来源。[任务记录](../../.ai/tasks/TASK-0162/task.yaml) |
| Stage B 停止时的原主根与旧 WIP | `codex/agent-bridge-phased-adoption` / `4ab57ce5b0291ec2841c90782a751c920e284403`。 | 当时已核对八个暂存 mutation/schema 文件、TASK-0094/0095/0124 及三份未跟踪建议稿的路径和内容校验值。材料归原任务保管，不得整文件覆盖、stash、reset、clean 或当作重复删除。 |
| 已验收本地候选 | 普通安装候选 `c60b663427e73ca2d551d7a9aca2dc68b443c954`；Stage A 自有治理根。 | 原记录报告本地采用通过，不代表本维护基线含有全部候选代码，也不代表 Stage B 验收。 |
| 普通安装的本地 Node V2 | `agent-bridge-node@2` / Policy `3.2.0` 已合入 main。合并提交 `dd894e41` 交付已安装原生引擎的固定变异执行与重放。合并提交 `39898f30` 交付本地预验证、独立实现审核、同一验证者终结、代码批准与 Gate。 | #148 的必需 `ai-quality-gate` 在最终提交 `1f2f2cdf` 通过。[固定变异 #147](https://github.com/MaginaLW/harness-model/pull/147) · [本地生命周期 #148](https://github.com/MaginaLW/harness-model/pull/148) · [CI run 41427419940](https://github.com/MaginaLW/harness-model/actions/runs/41427419940) |
| source6 发布候选 | `5ce4cbd841a4656d346c9b17938a0b42d5f1d897`；[PR #150](https://github.com/MaginaLW/harness-model/pull/150) 仍打开。 | 该候选的源仓检查通过。历史记录包含 Native、7354 项测试/9 项跳过、变异及源 Gate/CI；目标 Node CI、combined Gate 与真实 agent-bridge 接入仍待验收。 |
| 已停止消费候选 | agent-bridge TASK-0017 / REVIEW / V2；原独立目标根及原任务所有者保留现场。 | 原记录为 BLOCKED，Missing: block_resolution；历史干净封账 `d1fbd37a7df351610021b0a4a509073a573d8cab` 属较早窗口，不冒称 probe5 后新 HEAD。 |

### 已完成的维护收口

- 原 PR #169 的 0–4 批已完成交付。16 篇历史文档已归档，13 个旧入口保留转引。治理修复覆盖审批来源、子目录 Hook 的任务选择与观察记录绑定、Schema 校验器缓存、SDK 的只读 Git 查询，以及 Linux 受控子进程的 Git 查找顺序。原 PR 已关闭，原分支保留作对照。[文档归档 #170](https://github.com/MaginaLW/harness-model/pull/170) · [实现 #175](https://github.com/MaginaLW/harness-model/pull/175) · [原候选 #169](https://github.com/MaginaLW/harness-model/pull/169)
- PR #171、#172、#174 已关闭，三者的实现均已通过 #175 合入。原分支仍可用于核对各自的审核和 CI，其中 #172 的 Linux 运行保留原失败结论。[#171](https://github.com/MaginaLW/harness-model/pull/171) · [#172](https://github.com/MaginaLW/harness-model/pull/172) · [#174](https://github.com/MaginaLW/harness-model/pull/174) · [#172 的失败记录](https://github.com/MaginaLW/harness-model/actions/runs/44325839473)
- TASK-0162 在实现提交 `8012c415` 上通过 Linux 原生 V1 的全部 10 项检查。pytest 通过 4,701 项、跳过 77 项，核心覆盖率 90%，差异覆盖率 97%。实现与收尾 PR 各自在最终提交上通过必需 CI。维护者可按 PR 内容核对任务验证、历史记录和质量检查分别何时运行。[本地审核与实测结果](../../.ai/tasks/TASK-0162/review-package.md) · [收尾 #176](https://github.com/MaginaLW/harness-model/pull/176) · [CI 路由说明](github-branch-protection.md)
- TASK-0163 在基线 `928e135d` 上完成五项定向 V2 变异检测归因的本地规格交付与三轮独立审核（REV-0001～REV-0003 均为 `APPROVE`），交付提交 `657326d3` 通过本机 V1 的全部 10 项检查（pytest 通过 4,769 项、跳过 9 项，核心覆盖率 90%）。该交付仅固定规格与验收口径，不包含运行时归因实现、真实变异或私有 CI 运行；合并提交 `97593906` 已随合并提交 `33c0b9cd` 记为 `MERGED`。[规格](../../.ai/tasks/TASK-0163/spec.md) · [审核摘要](../../.ai/tasks/TASK-0163/review-package.md) · [PR #181](https://github.com/MaginaLW/harness-model/pull/181) · [收尾 #183](https://github.com/MaginaLW/harness-model/pull/183)
- [PR #185](https://github.com/MaginaLW/harness-model/pull/185)（合并提交 `0526983f`，`ai-quality-gate` 通过）仅优化 4 个测试文件（`test_node_profile_contract.py`、`test_installed_mutations.py`、`test_git_context.py`、`test_begin_close_commands.py`），不改动 `src/aiflow/**`、`.ai/policy/**` 或 CI/覆盖率阈值，用例数保持 `4,778 == 4,778`，将 Windows 全量 `--cov-branch` 耗时压回 `3000s` 门禁内；同期已移除已合入的 `codex/governance-verified-closeout` 工作树与本地分支并关闭原候选 [PR #169](https://github.com/MaginaLW/harness-model/pull/169)。
- 在基线 `0526983f` 上，后继任务 `TASK-0175`（[PR #186](https://github.com/MaginaLW/harness-model/pull/186)，分支 `codex/mutation-attribution-0526983f`，交付提交 `2dd4e8e7`）原样迁入 17 个已审核实现与测试文件，通过独立设计与实现审核（`REV-0001`/`REV-0002` 均为 `APPROVE`）、单轮 Windows V2（14/14，`unit_tests` `1734s`，核心覆盖率 `90.06%`，差异覆盖率 `92%`，5/5 变异 `killed`）、私有 Ubuntu V2 `--ci` 重放（14/14，`457s`，核心覆盖率 `89.73%`，差异覆盖率 `90%`，7 份私有原件仅留本机）及双端本地 Gate，已替代并关闭原 [PR #180](https://github.com/MaginaLW/harness-model/pull/180)（`TASK-0165`）；前序 `TASK-0167`（`BLOCKED`）与超时停下的 `TASK-0174`（`FAILED`，`unit_tests` 触及 `3000s`）原件保留不动。因 7 份私有原件不入库，PR #186 的公开 `ai-quality-gate`（[run 44915489569](https://github.com/MaginaLW/harness-model/actions/runs/44915489569)）在 `Verify and Gate` 失败。恢复条件见[剩余缺口与推进条件](#剩余缺口与推进条件)。
- **受保护 CI 验签 v1。** `TASK-0181` 的本地正式 V2 以 `FAILED` 结束。后继 `TASK-0182` 在获批的本地 Ubuntu 槽内完成唯一一次正式 V2，14/14 项必需检查通过，5/5 个固定变异均被检出。实现以 `ad2fc6e6` 合入 main，账本随收尾 PR 记为 `MERGED`。验签工作流默认关闭，仅允许从受保护的 main 手动触发。经项目所有者批准，该任务的 1 份变异证据和 5 份检测日志已公开。[实施审核包](../../.ai/tasks/TASK-0182/review-package.md) · [六份公开记录](https://github.com/MaginaLW/harness-model/commit/e8a26ec91dfe4b165a2f364c7772a5fd51ee32c2) · [实现 #191](https://github.com/MaginaLW/harness-model/pull/191) · [收尾 #192](https://github.com/MaginaLW/harness-model/pull/192) · [验签工作流](../../.github/workflows/private-replay-receipt.yml)
- **受保护 CI 验签 v2。** v2 使用受保护变量 `PRIVATE_REPLAY_V2_APPROVAL_COMMITMENT` 绑定批准文件的精确字节，核对 main、PR head、工作流 attempt，以及专用 App 暂存的正文与 SSHSIG 签名。历史 R2 原件仅保存在本机。`TASK-0185` 的软件提交 `7858fa73` 通过一次正式本地 V2，14 项必需检查全部通过，5 个固定变异全部检出，本地 Gate 通过。项目所有者批准公开最终账本和本轮六份变异 JSON。公开 `ai-quality-gate` 在交付 head `ed39cf20` 通过，软件以 `3ce1094f` 合入 main。[实现 #195](https://github.com/MaginaLW/harness-model/pull/195) · [最终账本](../../.ai/tasks/TASK-0185/task.yaml) · [披露范围](../../.ai/tasks/TASK-0185/delivery-authorization.md)
- **单次回放的 v3 验签。** 验签器保留 v1 和历史 v2（`round="R2"`），为省略 `round` 的 v3 使用独立 SSHSIG namespace。正文、签名、PR head、main、运行 attempt 或必需检查不匹配时，验证失败。软件提交 `366cd006` 的独立本机 V2 通过 14/14 项检查，检出 5/5 个固定变异。公开必需检查在 `6d51f04c` 通过，软件以 `1eeccab9` 合入 main，`TASK-0187` 已关闭。[软件 #198](https://github.com/MaginaLW/harness-model/pull/198) · [任务账本](../../.ai/tasks/TASK-0187/task.yaml) · [披露范围](../../.ai/tasks/TASK-0187/delivery-authorization.md)

[PR #157](https://github.com/MaginaLW/harness-model/pull/157)已合并 Windows 新任务事件的规范 UTF-8/LF 字节修复、clean-checkout 的 Git/构建/安装/CLI 配置隔离及离线 wheel 验收，并保留资源包规范化与大小限制说明。TASK-0149 的独立设计与实现审核通过，原生 Windows V1 的十项检查通过（6507 passed、9 项条件跳过），本地 Gate 与当前候选 required CI 通过；[PR #158](https://github.com/MaginaLW/harness-model/pull/158)已合并任务关闭记录，账本状态为 MERGED。证据见[任务记录](../../.ai/tasks/TASK-0149/task.yaml)与[验收索引](../../.ai/tasks/TASK-0149/evidence.json)，原始日志仍在实际验收克隆中。

[草稿 #128](https://github.com/MaginaLW/harness-model/pull/128)和[草稿 #131](https://github.com/MaginaLW/harness-model/pull/131)已由上述交付替代并关闭，未合并旧候选，原分支和失败材料保留。配置隔离不提供 OS 沙箱，也不清除所选 HEAD 自身可达的历史；超时不证明全部后代已停止。

[PR #149](https://github.com/MaginaLW/harness-model/pull/149)已因后继替代而关闭，未合并：只读 Git 保护已由 [PR #151](https://github.com/MaginaLW/harness-model/pull/151)以子进程环境 `GIT_OPTIONAL_LOCKS=0` 交付，LF 修复由 PR #157 交付。旧分支、TASK-0139 的 FAILED 状态、失败原件和缺失验收继续保留；关闭不表示旧候选验收通过，后继证据不能移用于该候选。[PR #150](https://github.com/MaginaLW/harness-model/pull/150)仍打开且未合并，目标 LOCAL、私有 CI 与 combined 验收仍未完成。

[PR #161](https://github.com/MaginaLW/harness-model/pull/161)（合并提交 `5599ad6e`，Ubuntu `ai-quality-gate` 通过）与 [PR #162](https://github.com/MaginaLW/harness-model/pull/162)（合并提交 `5afe908b`，Ubuntu `ai-quality-gate` [run 43676489608](https://github.com/MaginaLW/harness-model/actions/runs/43676489608) 通过）已完成工程克制与低打断规范的两阶段内化，分别合入 [低干预工作方式](low-intervention.md)、[效果观察口径](effect-observations.md)、[项目规则采用示例](../../examples/adoption/project-rules.md)、[AGENTS.md](../../AGENTS.md)、AI Flow 模板及 [ai-flow 技能](../../.agents/skills/ai-flow/SKILL.md)。[TASK-0154](../../.ai/tasks/TASK-0154/task.yaml) 原件保留在合并树中，因本机 Windows `V1` `pytest --cov-branch` 触发 3000s `RUNNER_TIMEOUT`（另预存 `test_incomplete_source_distribution_cannot_build_wheel` 在中文 Windows GBK 解码下失败）而保持 `BLOCKED`（`verification_unavailable`）历史状态，不回填本地 `VERIFIED`；PR #162 已由项目所有者审阅后基于远端 Ubuntu CI 全量通过授权合并，见 [审核包](../../.ai/tasks/TASK-0154/review-package.md)。

[PR #164](https://github.com/MaginaLW/harness-model/pull/164)（合并提交 `509941b9`）、[PR #165](https://github.com/MaginaLW/harness-model/pull/165)（`TASK-0155`，合并提交 `a376ad4c`）、[PR #166](https://github.com/MaginaLW/harness-model/pull/166)（`TASK-0156`，合并提交 `3f51bd04`）与 [PR #167](https://github.com/MaginaLW/harness-model/pull/167)（合并提交 `4836820a`）已完成项目瘦身与过度建设治理收口：归档 `15` 篇未引用运维记录与精简 `17` 处 Windows 临时测试夹具，将 `git_context.py` 分支任务检索批量化（`git cat-file --batch`）并统一 `status_service` / `gate` 策略及范围新鲜度校验，正式退场从未接入主引擎的 `11` 个外围 `tools/analysis/*.py` 脚本及 `18` 个专属测试文件（`-18,119` 行，测试套件精简至 `4,742 passed`、`core` 总分支覆盖率 `90% >= 85%`、`diff_coverage >= 90%` 与 `mypy`/`ruff` 门禁阈值不变），随 [PR #167](https://github.com/MaginaLW/harness-model/pull/167) 将 `9` 篇退役分析说明及示例归档至 `docs/archive/operations/` 并同步更新活跃链接；`TASK-0155` 与 `TASK-0156` 均已完成独立设计与实施审核（`APPROVE`）、本地原生 V1 全项通过及远端 `ai-quality-gate` 通过并按 `MERGED` 关闭账本。此后已通过非强制 `git worktree prune/remove` 与 `git branch -d` 清理已合入/失效临时工作树（`15 -> 10`）及 `35` 个已合入 `codex/*` 本地分支，完整保留主根 `4ab57ce5` WIP、open [PR #150](https://github.com/MaginaLW/harness-model/pull/150)、全部 `archive/*` 引用、`pilot/*` 分支及未合入本地工作树。

### agent-bridge 阶段 B 当前收尾

**完整接入未完成，最新手动主探针5失败后已封账停止。** 最新失败为 L exit1、空 `AssertionError`，仅能定位至启动身份/绑定区域；具体断言和根因仍 UNKNOWN。临时 Process 策略已恢复；N 不存在、L 退出不能证明 carrier 独立性或 owned cleanup。

原件静态核对已确认，准备材料的前驱链声明与 supervisor、controller 两处检查引用的前驱层级不一致。在固定维护基线 `bdd4fef3e1ae4a331c738e07e932c4749cd05c0c` 的 `src`、`tools`、`tests` 中按精确名称核对，未发现这些私有 helper 的生产消费者，本轮 P3 生产代码修改不实施。私有修复留待原工作线恢复时核定。原执行缺少 traceback，历史实际首个异常断言仍为 UNKNOWN。静态诊断回执保留在原主根的 `build/co/campaign/stage-b/target-subject-recovery/diagnosis/static-binding-review.json`。

累计 probe5/5、policy7/8、Set14/16。LOCAL14、产品 record/verify、PR3 新同步、私有 CI 和 combined Gate 均未启动。源/目标的旧消耗、失败、UNKNOWN 与全部资源上界保留，剩余预算和未用槽位不恢复执行许可；不修复后重跑、不提出新恢复轮。PR150/PR3 在原停止记录中保持打开，本文不冒称已合并或实时远端状态。

本地失败原件：`build/co/campaign/stage-b/target-subject-recovery/probe-failure-closeout.json`（忽略目录，不能随公开文档发布）。旧根、空 worker 目录和全部原件不动。精确历史计数、额度、候选与 Windows 边界见[接入计划](../superpowers/plans/agent-bridge-integration.md)，两者均不批准恢复。

## 剩余建设主线

### 当前能力进度

| 能力 | 已有结果 | 尚缺或保持暂停 |
|---|---|---|
| Phase 1/2 治理基础 | 确定性分流、版本绑定、结构化审核、V2、独立 verifier、required CI；维护模式以 AGENTS 为准。 | 无 V3、通用命令拦截、OS 沙箱或可信动作执行；批准文字不是运行时强制。 |
| 非评分准备（S0/S1） | [事实快照](effect-observations.md#固定提交的事实快照)；[正式账本回读](../archive/operations/review-feedback.md)、[PR 回读](../archive/operations/pr-feedback.md)、[只读建议](../archive/operations/review-advisory.md)已归档（脚本于 PR #166 退场）。 | 来源认证、实际身份、人时/费用、独立真值和原子一致性仍有 unknown；记录数不是独立样本。 |
| 离线工具（S2 局部，已归档） | [公开外部参考](../archive/operations/benchmark-reference.md)、[输入检查与原件定位](../archive/operations/review-detection-input.md)、[区间计算](../archive/operations/review-detection.md)、[合成分析](../archive/operations/review-detection-analysis.md)、[合成反馈](../archive/operations/review-feedback-simulation.md)（对应脚本于 PR #166 退场）。 | synthetic 结果不能改标为真实数据；尚无生产评分、校准或自动路由效果证明。 |
| SDK | [单次文档审核及可选上下文节点](../superpowers/specs/sdk-readonly-review.md#使用)已交付。 | 默认关闭；一次真实审核不证明长期效果，新实际调用需明确任务、输入与范围。 |
| 跨仓引擎 | main 已合并[资源包](resource-bundle.md)、[非覆盖初始化](initialization.md)、[Node 本地 V0/V1](node-verification.md)及[普通安装的本地 Node V2](node-verification.md#revision-2-local-v2)。 | 目标 Node CI、combined Gate 与真实 agent-bridge 接入待验收。source6 和 Stage A 的证据按上表对应版本读取。 |

### 既定离线范围的收口

现有离线范围已交付；没有新增必做准备队列。具体新需求或可复现问题才触发受影响部分的修改和检查；复用现有接口，不为填队列增加采集器、Schema 或服务。

本地遥测草稿已单独留存。Python V0/V1 的逐项验证结果保存在任务 `evidence.json` 的 `checks[]` 中。`status` 给出检查结论，`reason_code`、`timed_out` 和日志引用用于追查失败。即使进程退出码为零，检查本身仍可判定失败。[超时证据示例](../../.ai/tasks/TASK-0154/evidence.json)

### 剩余缺口与推进条件

- **工作流标记 #197、#194。** #197（`74222ee5`）与 #194（`0bcd65db`）的工作流标记和配套测试内容相同，均在首次 checkout 前显示事件提交和工作流来源提交。两者的账本、回放和必需检查各自绑定候选 head，公开 `ai-quality-gate` 均在 `Verify and Gate` 失败。#197 的历史回放绑定主线 `6a4a6456`。#194 保留 `TASK-0183` 已用完的一次正式本地 V2 记录。[后继 #197](https://github.com/MaginaLW/harness-model/pull/197) · [原候选 #194](https://github.com/MaginaLW/harness-model/pull/194)
- **本机后继 `TASK-0188`。** 在主线 `20c0a895` 准备软件提交 `4dfb2f89` 和账本候选 `470dedba`。单次离线 Ubuntu V2 经独立审核和同一验证者定稿，14 项必需检查、5 个固定变异和本地 Gate 通过。在同一候选上的离线 `verify --ci` 回放通过 14 项必需检查、5 项维护检查和 Gate。pytest 通过 4,869 项、跳过 77 项，核心覆盖率 89.83%。回放核验 5 个已有变异，新增变异执行为零，原件与账本的前后摘要一致。原件及未签名回放摘要留在本机，候选尚未公开。离线回放的 `--ci-run-dir` 使用 `TMPDIR` 的严格子目录，输出文件位于该回放目录内。
- **签发与发布。** `TASK-0188` 的两份验收结果各自绑定上列主线与候选。生产签发（3S）与检查发布（3P0）继续 `HOLD`。主线或候选变化后须重新绑定回放证据。恢复时登记签发责任人、受信公钥指纹和专用 App。受保护工作流从主线获取验签器，摘要取该提交中的 Git 文件字节。当前合并门要求 GitHub Actions（App ID `15368`）的 `ai-quality-gate`，专用 App 的 `private-v2-receipt/verified` 若要参与合并门，须单独确定接入方式。[受保护工作流](../../.github/workflows/private-replay-receipt.yml)
- **变异归因 #186。** `TASK-0175`（`2dd4e8e7`）单独交付变异归因。Windows 与私有 Ubuntu V2 各通过 14/14 项，两端本地 Gate 通过。七份私有原件仅存本机，当前 head 的公开必需检查失败。仅在明确需要交付变异归因时恢复，复核该 head 的证据及必需检查。标记候选的结果不能用于 #186 的合并验收。[变异归因 #186](https://github.com/MaginaLW/harness-model/pull/186)
- **暂缓的回放工作。** `TASK-0169` 的受保护验签工作流候选已通过私有 Ubuntu V2 与本地 Gate，原任务状态为 `APPROVED_FOR_MERGE`。`TASK-0170` 的单仓 GitHub App 合成检查已返回 `completed/success`，该任务依据本机 `READBACK/RESERVED/0` 诊断在 `c0fb8172` 以 `BLOCKED` 收口，剩余外部额度为 0。`TASK-0173` 的 Linux `--ci-sandbox` 隔离工作（`IMPLEMENTING`）继续暂缓，其预留的一次私有 Ubuntu 正式 V2 尚未使用。启动前须由项目所有者针对该任务、提交、规格、独立验证者及单次动作明确放行，各原任务的授权边界继续有效。[TASK-0170 合成检查](https://github.com/MaginaLW/harness-model/runs/136411424968)
- **G 的恢复条件。** 仅在确有正式切换需求时恢复影子验收。合成成功、预期拒绝、普通维护 PR 检查各保留一次，三项均未使用（0/3），每项均不重试。
- **真实观察**：B（3-A 非评分准备、3-B 独立 V3）、首用途、`review_detection`、95% 等尾区间/总宽不超过20个百分点及有限研究范围已采用，不重复请求这些决定。真实自然任务的预声明候选、旧契约、实际输入/职责/原预算、完整报告、独立裁定与预算关闭原件仍缺；`T0/T1` 未设置，不制造样本、不启动30日窗口。见[观察准备](../archive/operations/review-detection-preparation.md)、[准入](../superpowers/specs/review-detection-admission.md)。
- **宿主接入**：仍缺受支持的既有 Desktop 通道、实例绑定、实际 server/协议版本、全部返回面及接收前累计限制。既有[issue #55904](https://github.com/openai/codex/issues/55904)是回复入口，未在本轮重查回复；不重复提问、不重启已关闭读取。新材料按[核对步骤](../superpowers/specs/review-detection-host-evidence.md#维护方回复后的核对步骤)处理，齐备也不自动连接。
- **Phase 3/4**：Phase 3 仍 `not_started`；[进入输入](../implementation/phase-03-entry-inputs.md)的样本门 partial、真实 V3/统一度量 not_met 保留。3-A 单独完成不打开整体退出或 Phase 4。
- **旧 mutation 加固**：TASK-0094 范围扩大后 BLOCKED；TASK-0095 尚待规格审核，私有 CI 原件传递/重放、Ubuntu 进程树约束和旧账本隔离三个 medium 发现未关闭。旧核对仅证明 c60b663/a231941 未覆盖八文件 WIP；本轮未独立比较 source6，不能推断可丢弃；旧探针绑定有漂移，恢复前须重新核定规格、材料与消费者。TASK-0124 的资源包目标已有后继交付，旧 NEW 不倒填成功。
- **恢复决策**：本轮只完成治理；是否恢复 Stage B 或旧加固，由所有者另行决定具体目标、基线、风险和额度。治理过程中没有新授权缺口需要用旧预算填补。

## 条件性能力

完整引擎产品化、provider、固定动作可信执行及 V3 均按真实需求分别准入，详见[合同提案](../archive/operations/phase-entry-proposals-2026-10-04.md)与[两条路线](sdk-and-engine-plan.md)。Phase 4 另依赖整体 Phase 3 退出、稳定接口及实测协调需求。旧蓝图与宿主并发额度不是实现或运行许可。

## 旧工作线与证据边界

TASK-0063～0071 已归档，历史七项未全部验收，均不默认续跑。四条 pilot 验收分支、全部 archive refs、用户草稿、原失败/SPENT/partial/unknown、既有批准及编号保留。`archive/local-task0079-private-evidence` 含私有失败材料，不直接合并或公开推送。历史工具退役不授权恢复或删除原件；见[范围核对](../archive/operations/follow-up-completion-audit-2026-10-09.md)。

## 历史记录

不新建逐窗口台账。原账本、原件与固定 Git 版本保持可追溯：

- [本轮维护基线原状态全文](https://github.com/MaginaLW/harness-model/blob/5b82fc78987a63b686357c272f6dfdd4e0c6e96a/docs/operations/maintenance-status.md)：各 PR、离线合同及旧方向。
- 停止现场原状态仅在保留的原主根可读：`git show 4ab57ce5b0291ec2841c90782a751c920e284403:docs/operations/maintenance-status.md`。Stage A、A11–A50、失败/额度与 WIP 边界；正文中旧“先接入后瘦身”已由当前治理方向取代。
- [较早维护历史](../archive/operations/maintenance-status-history.md)与[归档索引](../archive/README.md)。main 原文也可用 `git show <固定提交>:docs/operations/maintenance-status.md` 读取。停止工作线提交尚未公开，远端不能检出；保留原本地分支和对象，不为导航公开其历史/私有原件。对象缺失时报精确缺口，不改写为成功。
