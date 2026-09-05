# 审批开销治理与未完成任务收敛实施目录

状态：`not_started`
治理模式：仓库维护模式（`.ai/bootstrap-mode.yaml` 为 active）
active Policy：`2.2.0`
统计基线：`main` 提交 `3ce0e06`，账本全量 38 个 task
归档说明：[文档归档](../../archive/README.md)

本目录取代章节 1–7 的逐任务执行文档（已归档），把两类此前分散的工作收敛到一处：仍未
收尾的 15 个 task，以及针对「AI Flow 反而增加了人类审批次数」这一问题的治理改造。

本目录只是计划。它不构成批准、不授权发布、tag、推送、合并、部署、删除、凭据导出或任何
外部动作，也不改变阶段三的进入门。其中任何一项进入实施时，仍按 `AGENTS.md` 判断是否
必须创建 AI Flow task。

## 1. 背景：实测到的问题

项目的两个初始目标是「减少人类审批次数」和「提高 AI 完成的可靠度」。对 `.ai/tasks/`
全量账本与 `main` 提交历史的统计显示：可靠度目标已达成（13/13 chapters 完成、V0/V1/V2
闭环、CI 质量门禁在真实 PR 上生效），审批次数目标未达成，且方向相反。

| 指标 | 实测值 |
|---|---|
| 账本 task 数 | 38 |
| 路由分布 | REVIEW 28 / AUTO 9 / ASK 1 |
| REVIEW 的来源规则 | `ROUTE-DEFAULT-REVIEW` 17 次，`HARD-REVIEW-CI-CD` 11 次 |
| 批准记录总数 | 113 条（首次 65，重复 48，重复占 42.5%） |
| 重复批准构成 | spec 25、action 20、code 3 |
| 账本事件总数 | 998 |
| `main` 非 merge 提交 | 382，其中 169 条（44.2%）只改动 `.ai/tasks/` |
| 返工类事件 | escalated 32、verification_failed 24、implementation_retried 19 |

### 1.1 五个放大机制

**M1 —— 默认不信任。** `.ai/policy/routing.yaml` 中 `ROUTE-DEFAULT-REVIEW` 是
priority 0 的兜底规则，而 `ROUTE-AUTO-EXPLICIT-GUARDS` 要求 `scope.clear`、
`impact.level=low`、`reversibility ∈ {reversible, conditionally_reversible}`、
`verification.automatic`、`external_side_effects` 为空五项同时成立，任一字段
`missing` 即 `error`。因此 17 次 REVIEW 的实际含义是「没凑齐 AUTO 的条件」，而不是
「识别出了风险」。

**M2 —— 自指放大。** `AGENTS.md` 维护模式的升级清单是 `.github/workflows/**`、
`.ai/policy/**`、`.ai/schemas/**`、`src/aiflow/**`、`.gitignore` 与 `.gitattributes`、
任务账本本身，以及任何有外部副作用或不可逆的动作。其中的路径项几乎等于本仓库的
全部源码，`HARD-REVIEW-CI-CD`（priority 780）另外命中 11 次。结果是维护模式对本
仓库的自研工作豁免接近零 —— 这解释了为什么进入维护模式后体感没有改善。

**M3 —— 批准绑定精确 commit。** `src/aiflow/freshness.py` 中 `code_approval` 绑定
`(base_commit, subject_commit, policy_sha256, spec_sha256)` 并附加 `evidence_sha256`
与 `evidence_current`；`spec_approval` 绑定 `(base_commit, policy_sha256, spec_sha256)`。
由此：任何 fixup 提交使 code 批准失效；`base_commit` 变化（rebase）使 spec 与 code 批准
同时失效；`policy_sha256` 变化使所有在途 task 的所有批准同时失效。48 条重复批准中 28 条
由 `subject_commit` 变化驱动。

`subject_commit_synchronized` 的同步容差目前只用于 `classification`，没有用于任何
approval —— 账本（`.ai/tasks/*/events.jsonl`）里已有 79 条同步事件证明这条链可审计，
但批准侧用不上它。

**M4 —— action 批准是一次性券。** `.ai/schemas/approval.schema.json` 强制 action 类型
必须携带 `single_use: true` 与 `expires_at`；`.ai/policy/permissions.yaml` 无条件
`deny_automatic` push、merge、deploy、delete、secret_export、paid_external_call。
实测 20 条 action 重复批准中，有 12 条与前一条的全部绑定字段完全相同 —— 人被要求把同一
件事批第二遍，唯一原因是上一张券已被消费。

这里必须区分「Policy 要求」与「代码强制」，二者当前并不重合：

- **push 与 merge 只有 Policy 要求，没有任何代码拦截。** `aiflow` CLI 没有 push、merge
  或 deploy 子命令，`close` 的定位是 "record an externally completed merge"；
  `src/aiflow/gate.py:531` 与 `src/aiflow/status_service.py:211` 在计算批准新鲜度前都
  显式跳过 `approval_type == "action"`。账本可以佐证：AUTO 任务 TASK-0037（PR #8）与
  TASK-0039（PR #12）的 `approvals.json` 均为 `[]`，终态事件是
  `merge_approved_automatically` + `merge_recorded`，全程 0 次 action 批准。9 个 AUTO
  task 中只有 TASK-0031 手工补记了 4 条 push/merge 类 action 批准。
- **真正被代码单次消费的只有 `targeted_mutation_v2`。** 消费逻辑在
  `src/aiflow/mutation_evidence.py`（重放追加式事件求已用 digest，并以 `open("x")` 独占
  创建 `logs/action-launch-<action_sha256>.json`，冲突即 `ACTION_APPROVAL_USED`）；过期
  由 `src/aiflow/approval.py` 的 `validate_action_file()` 与 `approval_is_current()` 强制。
  `freshness.py` 的 `FRESHNESS_ACTION_USED` / `FRESHNESS_ACTION_EXPIRED` 分支目前没有任何
  生产调用方，只被 `tests/fixtures/freshness/decision-table.json` 覆盖。

因此 M4 的实际开销落在 REVIEW 路径与 V2 targeted mutation 上，而不是 AUTO 任务的 PR
流程；push/merge 的重复授权是流程约定造成的人工开销，不是系统拦截造成的。

**M5 —— 账本推进被计入人类工作。** `bind classification` → `bind subject` →
`record verification and gate` → `close` 是纯机械步骤，但目前各自成为独立提交，并夹在
人类审批点之间。一次纯文档变更（TASK-0037）产生 5 个非 merge 提交：4 个纯账本提交
（`a8ebbd8` bind classification、`8b652cf` bind subject、`641fb11` record verification
and gate、`8dd0596` close）与 1 个有效提交（`c389f56`，且该提交本身仍夹带账本文件）。
全局 44.2% 的非 merge 提交只改动 `.ai/tasks/`。

### 1.2 根因

可靠性被实现为「每一步都绑定当前版本并要求人类确认」，而不是「让机器能自证这一步安全」。
V0/V1/V2 已经是很强的自动判据（V1 起有单元测试、完整回归、mypy 与 90% diff coverage，
V2 另加 acceptance、integration、targeted mutation 与独立 verifier；V0 只有 contract、
scope、Ruff、format 与 smoke，不含任何测试。注意 85% 总覆盖率阈值**不在**
`.ai/policy/verification-levels.yaml` 里 —— V1/V2 的 `coverage_xml` 检查不带
`--cov-fail-under` 也没有 `threshold`，`pyproject.toml` 亦无 `fail_under`；85% 只由
`.github/workflows/ai-quality-gate.yml` 的 CI 步骤强制），但当前 Policy 中**验证强度
换不到任何审批豁免**：
审批与验证是两条并行相加的门，而不是「验证足够强则审批可减」。M1–M5 都是这一根因的表现。

## 2. 目标与非目标

### 目标

1. 把「默认 REVIEW、AUTO 是例外」反转为「验证充分即 AUTO、硬风险仍拦截」，且不降低任何
   CI 质量门禁的检查项与阈值。
2. 让与被审内容无关的变化（rebase、格式化、无关 fixup）不再作废已有批准。
3. 让低风险的重复性动作（push、门禁通过后的 merge）不再逐次索要一次性批准。
4. 把机械的账本推进从人类审批路径中移除。
5. 把 15 个未收尾 task 全部给出明确的终态或收尾动作，使账本不再有长期悬挂状态。

### 非目标

1. 不放松硬风险规则。`HARD-BLOCK-EXTERNAL-SENSITIVE`、`HARD-BLOCK-IRREVERSIBLE-NO-BACKUP`、
   `HARD-BLOCK-VERIFICATION-TOOL-MISSING`、`HARD-REVIEW-PRODUCTION-DATA-DELETE`、
   `HARD-REVIEW-SECRETS-AUTH`、`HARD-REVIEW-CI-CD`、`HARD-REVIEW-DEPLOYMENT`、
   `HARD-REVIEW-REAL-EXTERNAL-ACTION` 八条全部保持不变。其中 `HARD-REVIEW-CI-CD`
   （priority 780）是当前账本里唯一实际命中过的 `HARD-*` 规则（11 次，即第 6 节
   「`HARD-*` 规则命中次数」的全部来源），B1 尤其不得削弱它。
2. 不降低 CI 质量门禁：完整测试、85% 总覆盖率、90% diff coverage、whitespace、Ruff、
   format、mypy 与 `main` 分支保护均不变。
3. 不重写、不删除、不移动既有任务记录、证据与日志。
4. 不改变 delete、secret_export、paid_external_call、deploy 的单独获批要求。
5. 不进入阶段三，不实现 V3、模型路由、信任评分或资源调度。

## 3. 执行原则

1. Part A 与 Part B 相互独立，可分别推进；Part B 内部按 B1 → B3 → B2 → B4 的顺序，
   先做只改 Policy 与 schema 的部分，再做改动 `src/aiflow/**` 语义的部分。
2. 触及 `.ai/policy/**`、`.ai/schemas/**`、`src/aiflow/**` 或任务账本的每一章，按
   `AGENTS.md` 升级清单创建 AI Flow task；纯文档章节可走 task-free 例外。
3. 每章形成独立提交，附冻结规格与验证证据。
4. 任何一章都不得以「减少审批」为由跳过 Gate、降低 route/V 或绕过分支保护。
5. Policy 语义变更必须同时提供负向测试：证明硬风险路径仍然被拦截。

## 4. Part A：未完成任务收敛

当前 15 个未收尾 task 的完整事实与建议终态。**A 部分的任何一步都会改动 `.ai/tasks/`，
属于升级清单，须走 AI Flow。**

| Task | 状态 | subject 是否已在 `main` | 事实与建议终态 |
|---|---|---|---|
| TASK-0001 | APPROVED_FOR_MERGE | 是 | 工作已合并，仅从未执行 `aiflow close`。按 A1 收尾。 |
| TASK-0002 | APPROVED_FOR_MERGE | 是 | 同上 |
| TASK-0003 | APPROVED_FOR_MERGE | 是 | 同上 |
| TASK-0004 | APPROVED_FOR_MERGE | 是 | 同上 |
| TASK-0005 | APPROVED_FOR_MERGE | 是 | 同上 |
| TASK-0006 | APPROVED_FOR_MERGE | 是 | 同上 |
| TASK-0007 | APPROVED_FOR_MERGE | 是 | 同上 |
| TASK-0009 | APPROVED_FOR_MERGE | 是 | 同上 |
| TASK-0026 | APPROVED_FOR_MERGE | 是 | 同上 |
| TASK-0027 | APPROVED_FOR_MERGE | 是 | 同上 |
| TASK-0028 | APPROVED_FOR_MERGE | 是 | 工作已合并，但 `README.md` 记录其 `merge_readiness` 为 `reverification_required`。收尾前须先按当前 subject 重新验证，不得直接以历史证据关闭。 |
| TASK-0032 | APPROVED_FOR_MERGE | 否 | subject `7a27dd9` 只存在于 `backup/task-0033-work`。同一目标已由 TASK-0036（`claude/repository-hygiene-redo`）在当前 main 上重做并合并。按「被取代」收尾，保留原证据。 |
| TASK-0033 | VERIFYING | 否 | 同一分支；同一目标已由 TASK-0037（`claude/cli-first-principle-redo`）重做并合并。需先用 TASK-0034 交付的中断验证收尾能力退出 VERIFYING，再按「被取代」收尾。 |
| TASK-0008 | BLOCKED | — | 阻塞原因 `task_description_changed`；账本已记录 `implementation delivered under TASK-0009`。按「被取代」收尾，无实施工作。 |
| TASK-0029 | BLOCKED | — | 阻塞原因 `verification_unavailable`（coverage 超 600 秒）。该根因已由 TASK-0030 的时间预算加固解决，任务目标已由 TASK-0031 完成并合并。按「被取代」收尾。 |

### Chapter A1：已合并任务的账本收尾

状态：`completed`（2026-09-04）。TASK-0001–0007、0009、0026、0027 共 10 个 task 已收尾为
`MERGED`，账本悬挂状态由 12 降至 2。

**执行中修正的一个前提。** 本章原写「逐个定位其进入 `main` 的合并提交」，该前提不成立：
这 10 个 task 的 subject 全部位于 `main` 的第一父主线上，是直接提交，**不存在任何合并
提交**——它们都早于本仓库的第一个 PR（PR #1，2026-08-30）。因此 `--merge-commit` 取
subject 自身，即工作进入 `main` 时所处的提交；账本中 `merge_commit == subject_commit`
对审计者自解释为「直接落到 main，无独立合并提交」。这不属于本章任务 4 所说的「合并提交
不可唯一定位」，而是已唯一定位且恰为 subject。

**一处连带改动。** `tests/integration/test_acceptance_traceability.py` 有一条断言要求
TASK-0001（阶段一验收报告的 report task）停留在 `IMPLEMENTING`/`VERIFYING`/`VERIFIED`/
`APPROVED_FOR_MERGE` 之一，收尾后触发失败。核实结论：该断言守的是状态机位置而非 Gate 结果
——收尾**之前** `aiflow gate TASK-0001` 就已是 `REJECT`（`GATE_REPOSITORY_CHANGED`、
`GATE_SCOPE_CHANGED`、`GATE_CLASSIFICATION_STALE`、`GATE_EVIDENCE_STALE` 四项），收尾只是
再加一项 `GATE_STATE_INVALID`。该 task 的验收证据位于 `docs/pilots/results/`，按哈希绑定，
不依赖 live task state。因此把 `MERGED` 加入允许集合，并把测试名由
`..._in_gate_capable_state` 改为 `..._in_expected_state` 以免名称失真；「不得为未开始、
BLOCKED 或 FAILED」的保护保持不变。该测试无任何外部引用。

`close` 的实际写入范围经确认符合追加式要求：`events.jsonl` 每个 task 仅 +1 行、零删除；
`task.yaml` 只更新 `current_state` 与 `updated_at` 两行的当前状态投影，无历史记录被重写。

#### 进入条件

- 每个目标 task 的 `subject_commit` 经 `git merge-base --is-ancestor` 确认已在 `main`。
- 对应的合并提交可定位（`aiflow close` 需要 `--merge-commit`）。
- TASK-0028 不在本章范围内，另见 A2。

#### 任务

1. 为 TASK-0001–0007、0009、0026、0027 逐个定位其进入 `main` 的合并提交。
2. 逐个执行 `python -m aiflow close <TASK_ID> --result merged --merge-commit <SHA> --actor <ACTOR>`。
3. 不修改任何既有 approval、evidence、event 或日志；`close` 只追加终态事件。
4. 记录哪些 task 因合并提交不可唯一定位而无法机械收尾，并单独说明。

#### 验证

```powershell
python -m aiflow status <TASK_ID>
python -m aiflow validate <TASK_ID>
git diff --check
```

#### 退出条件

- 10 个目标 task 的 `current_state` 均为 `MERGED`，或已逐个记录不可收尾的确切原因。
  ✅ 10/10 已为 `MERGED`，`aiflow validate` 全部通过。
- 账本无内容被重写；`git log` 显示相关文件只有追加。
  ✅ `events.jsonl` 零删除行；`task.yaml` 仅状态投影两行变化。

### Chapter A2：阻塞与在途任务处置

状态：`partial`（2026-09-04）。TASK-0032、TASK-0033 已收尾为 `BLOCKED`；TASK-0008、
TASK-0029 经核对早已是带完整阻塞记录的 `BLOCKED`，无需再动。账本已无 `VERIFYING`
状态。**仅 TASK-0028 未完成，且被人类批准阻塞（见下）。**

**执行中发现的一个机制事实。** 状态机没有「被取代／作废」终态：`MERGED` 是唯一无出边的
终态，`BLOCKED` 只能回到 `CLASSIFIED`，`escalate --reason-code` 的封闭枚举里也没有
supersede 类取值。因此「按被取代收尾」在机制上只能表达为
`escalate --to BLOCK --reason-code task_description_changed`，把取代关系写进 `impact` 与
`existing-work` —— 这正是 TASK-0008 当初使用的形式。TASK-0033 需先用 TASK-0034 交付的
`verify --abandon` 退出 `VERIFYING`（记 `VERIFY_RUN_ABANDONED`，`VERIFYING → FAILED`），
再 block。**一个显式的 `SUPERSEDED` 终态是 B 系列之外值得单独考虑的改进**：当前把「工作被
更好的重做取代」和「工作被外部条件卡住」压进同一个 `BLOCKED`，两者的运维含义并不相同。

**TASK-0028 的收尾成本，是第 1 节问题的一个活样本。** 其 `status` 显示
`merge_readiness: reverification_required`、`Missing: reverification`，且
classification／approvals／evidence 三者全部 `stale`。它是 REVIEW / V2 任务，诚实收尾需要：
重新分类 → 重新冻结规格 → **人类 spec 批准** → 完整 V2 重验（实施目录记该串行成本可达
68.5 分钟）→ **人类 code 批准** → `close`。也就是说，为一个**代码早已在 `main`、且不产生
任何代码改动**的 task 收尾，要付出两次人类批准和一次完整 V2 —— 这正是 M1/M3 所描述的
「审批与验证是并行相加的门」。本章不自行绕过该门；TASK-0028 保持
`APPROVED_FOR_MERGE`，等待项目所有者决定是走完重验，还是按被取代／已落地另行处置。

#### 进入条件

- A1 完成，或明确决定与 A1 并行。
- TASK-0034 交付的中断验证收尾能力可用（该 task 已 MERGED）。

#### 任务

1. TASK-0033：用 TASK-0034 的收尾路径退出 `VERIFYING`，再按被 TASK-0037 取代记录终态。
2. TASK-0032：按被 TASK-0036 取代记录终态，明确保留 `backup/task-0033-work` 作为原证据。
3. TASK-0008：按被 TASK-0009 取代记录终态。
4. TASK-0029：按被 TASK-0031 取代、且阻塞根因已由 TASK-0030 解决，记录终态。
5. TASK-0028：先按当前 subject 重新验证，通过后再收尾；未通过则如实记录，不得以历史
   证据伪造 merge-ready。

#### 验证

```powershell
python -m aiflow status <TASK_ID>
python -m aiflow gate <TASK_ID>
python -m aiflow validate <TASK_ID>
```

#### 退出条件

- 5 个 task 均处于终态或有明确记录的阻塞理由。
  ⚠️ 4/5 已达成（TASK-0008、0029、0032、0033）；TASK-0028 待人类批准。
- `backup/task-0033-work` 的保留理由写入文档，不被误删。✅ 已写入 TASK-0032 的
  `next_step` 与本章。该分支（tip `a21171b`，本地与
  `origin` 均在）相对 `main` 领先 11 个提交，保存着 TASK-0032 的 subject `7a27dd9` 与
  TASK-0033 的 subject `7278e10`，两者都不在 `main` 上；而这两个 task 的 `task.yaml`
  仍声明 `branch: codex/repository-hygiene`、TASK-0029 声明 `branch: codex/formal-ci-canary`，
  这两个分支连同 `chore/preserve-task-0031-failed-evidence` 都已不在本地和 `origin` 上。
  因此 `backup/task-0033-work` 是这些提交的唯一留存位置。
- 账本中不再存在无人负责的 `VERIFYING` 或 `BLOCKED` 状态。✅ 已无 `VERIFYING`；
  4 个 `BLOCKED` 均带 reason code、impact 与 existing-work 处置说明。

### Chapter A3：文档一致性修复

#### 进入条件

- 无前置依赖；纯文档，走 task-free 例外。

#### 任务

1. `docs/implementation/phase-03-entry-inputs.md` 的「当前禁止声明」写有「不得重建
   `.ai/bootstrap-mode.yaml`」，但项目所有者已明确决定重建并进入维护模式（TASK-0038）。
   更新该条，使其与 `AGENTS.md`、`README.md` 一致，并保留原决定的历史说明。
2. `docs/superpowers/plans/2026-08-05-codex-model-routing-config.md` 与
   `2026-08-08-external-worker-routing-implementation.md` 含本机用户名绝对路径
   （`C:\Users\<用户名>\...`），与仓库卫生要求冲突。改为占位符，不改变技术结论。
3. `2026-08-08-external-worker-routing-implementation.md` 是一份从未执行、且输入材料
   （本机临时目录）已失效的计划。明确标注其状态为「未执行」并给出废止或重写的决定点，
   不要让它继续被当作在途计划。
4. **两处本机路径不得清理，必须原样保留。**
   `docs/archive/plans/2026-08-02-chapter-01-task-1-1-tdd-replay-remediation.md` 的内容被
   `docs/superpowers/state/chapters/chapter-01.yaml` 的 `plan_sha256`（`5dd172aa…`）绑定，
   改动会使该哈希失配；`chapter-01.yaml` 自身的 `environment_result` 记录属于追加式历史
   证据。两者都在既有记录不得重写的范围内，本章只在文档中登记这一例外，不做替换。

#### 验证

```powershell
python -m pytest -q
python -m ruff check .
git diff --check
git grep -nF "Users\" -- docs
```

#### 退出条件

- 三处不一致均已修正或已记录明确决定。
- 仓库 tracked 的**活跃**文档中不再出现本机用户名绝对路径；仅归档的
  `2026-08-02-chapter-01-task-1-1-tdd-replay-remediation.md` 与 `chapter-01.yaml` 的历史
  `environment_result` 保留原值，且该例外已写入[文档归档](../../archive/README.md)。

## 5. Part B：审批开销治理

四章按 B1 → B3 → B2 → B4 推进：先做只改 Policy 与 schema、语义影响可局部验证的部分，
再做改动 `src/aiflow/**` 判定语义的部分。**四章全部触及升级清单，每章须走 AI Flow。**

### 实测结论：基于路径的 AUTO 放宽在本仓库无收益（2026-09-05）

在为 B1 寻找一条更窄的替代路径时（只放宽「`impact_scope` 完全落在 `docs/**`/`tests/**`
内」的单元），实测结果否定了整条思路：

| | |
|---|---|
| REVIEW 决策单元总数 | 30 |
| `impact_scope` 全落在 `docs/**` + `tests/**` | 2 |
| 其中属兜底 REVIEW（非 `HARD-*`） | 1 |
| 且 `impact.level == low` | **0** |

`_AUTO_GUARDS`（`routing.py:15`）强制每条 AUTO 规则的条件集必须是其超集，其中含
`('impact.level','equals','low','error')`。唯一那个纯 docs/tests 的兜底 REVIEW 单元
（TASK-0024/DU-001）声明的是 `medium`。因此一条合规的窄 AUTO 规则能转化的单元数为 **0**；
即便忽略 `impact.level`，收益也只有 1/30。

#### 原因是分类粒度，不是规则

18 个非纯 docs/tests 的兜底 REVIEW 单元，其 `impact_scope` 普遍把安全路径与治理面路径
**捆在同一个决策单元里**：

```
TASK-0005  .ai/schemas/review-context.schema.json, .ai/templates/...
TASK-0008  .ai/schemas/verifier-context.schema.json, .ai/schemas/evidence.schema.json
TASK-0010  README.md, docs/implementation/..., docs/superpowers/state/README.md
```

这与 M2（自指放大）同源：本仓库的工作就是构建治理系统，因而几乎每个变更都会触及治理面。
由此得到一条比 M1–M5 更强的结论：

> **任何基于路径的 AUTO 放宽在本仓库都不可能产生收益，因为分类的粒度单位（决策单元）
> 本身就混合了安全与不安全的路径。**

#### 数据指向的杠杆：决策单元粒度

把一个 task 的文档改动与引擎改动拆成**两个决策单元**，前者可合法走 AUTO，后者走 REVIEW。
这不需要修改引擎或 Policy —— 是任务分解的**实践**问题，成本远低于 B0/B1 的任何一版设计。

**未验证的推断：** 现有 9 个 AUTO 单元全部声明 `low`，17 个兜底 REVIEW 全部声明 `medium`，
提示作者对小而纯的单元确实倾向声明 `low`。但「拆分后作者是否会把文档单元声明为 `low`」
现有数据无法回答，须实际试行若干 task 后再评估。

#### 对 Part B 各章的影响（逐章，不笼统）

| 章节 | 是否受影响 | 理由 |
|---|---|---|
| **B0**（治理面守卫） | **前提消失** | 它存在的唯一目的是作为 B1 的前置条件 |
| **B1**（放宽 `impact.level`） | **前提消失** | 其收益依赖路径/影响级别维度的放宽，实测为 0 |
| B2（批准绑范围） | 不受影响 | 针对 48/113 重复批准，来自 freshness 绑定，与路由无关 |
| B3（action 批准分级） | 不受影响 | 针对 action 一次性券，与路由无关 |
| B4（账本推进自动化） | 不受影响 | 针对 169/382 纯账本提交，与路由无关 |

因此 **B0 与 B1 应当停止**，除非先解决决策单元粒度问题；B2、B3、B4 的实测依据独立成立，
可各自单独推进。

### 实测结论：B2 的收益同样为 0，开销主要来自实践（2026-09-05）

对 B2 的两项放宽做反事实测量，收益均为 0：

| B2 放宽项 | 可消除的重复批准 |
|---|---|
| (a) `code_approval` 容忍有同步链的 `subject_commit` 变化 | **0** |
| (b) `base_commit` 改为 merge-base 未变即新鲜 | **0** |

(a) 为 0：全账本仅 3 条 `code` 重复批准，三条**同时**变更了 `spec_sha256` 与
`evidence_sha256` —— 规格与证据都变了，重批准本就应当发生。
(b) 为 0：`base_commit` 在任何相邻批准之间从未变化。

#### 48 条重复批准的真实构成

| 类别 | 条数 | 占比 |
|---|---|---|
| freshness 确实要求的（spec/policy/evidence 变更） | 17 | 35% |
| **Policy 从未要求的** | **11** | **23%** |
| action 批准（`gate.py:531`、`status_service.py:211` 均跳过） | 20 | 42% |

那 11 条中，9 条是 `spec` 类型且仅 `subject_commit` 变化 —— 而
`freshness.py` 中 `spec_approval` 的绑定字段是 `(base_commit, policy_sha256, spec_sha256)`，
**不含 `subject_commit`**；另 2 条绑定字段完全相同。**这 11 次人类批准，系统一次都没要求过。**

#### 根因已定位并修复

`AGENTS.md` 原规则 5 写作「批准和证据必须绑定当前规格、Policy 与 `subject_commit`」——
一概而论，对 `spec_approval` 不成立，且违反其自身规则 6（不在 Agent 文件中复制规则表）。
Agent 依散文行事，于是在每次 subject 变化后重新请求引擎并不要求的 spec 批准。

已更正规则 5：不再复制字段表，改为指向 `aiflow status` 的 `Missing:` 输出作为唯一权威，
并要求请求人类批准前先跑一次 `status`。`tests/integration/test_agent_entry_files.py`
原本把那句错误表述钉死为核心原则，一并更正为钉住原则而非字段表。

#### 结论：引擎层面已无可做

| 设计 | 对「减少审批」的实测收益 |
|---|---|
| B1（放宽 `impact.level`） | 0（且被审核否决） |
| B0（治理面守卫） | 0（且被审核否决） |
| B2（批准绑范围） | **0** |
| B4（账本推进自动化） | 按其自身规格「不改变任何审批点」，减的是提交噪声 |

四次尝试，四次为 0。48 条重复批准中 31 条（65%）源于实践而非引擎要求。因此
**B0、B1、B2 应当停止**；有实测支撑且零成本的两项改动已写入 `AGENTS.md` 规则 5 与规则 8。
B3 与 B4 的实测依据独立成立，但两者针对的都不是人类批准次数。

### Chapter B0（新增）：治理面守卫 —— B1 的前置条件

状态：`blocked`（2026-09-05）。TASK-0041 已开立并冻结规格，独立设计审核 REV-0001 结论为
`REQUEST_CHANGES`，8 条 open 发现。**第一次尝试的设计同样不成立。**

#### 失败原因是语义性的，不是覆盖面

`impact_scope` 与 `allowed_scope` 存的都是 **glob 模式**，不是本次变更**触及的文件**。
用模式去匹配模式，激励是反的：声明 `src/**` 合法允许编辑 `src/aiflow/` 下任何文件，但
`fnmatch("src/**", "src/aiflow/**")` 为 `False` —— **声明得越宽，越不会被守卫捕获**。
`task_service.py:203` 默认直接以 `allowed_scope` 填充 `impact_scope`，因此这不是边缘情况。

任何锚定「声明的模式」的守卫都有这个洞。守卫必须锚定**真实变更文件集**，而这只有
`aiflow scope`（验证期，读 git diff）才有；分类期拿不到。

#### 另外两条推翻了本轮规格自己的论证

1. **「新增 REVIEW 规则只提升严重度、不可能削弱任何既有结论」为假。**
   `ROUTE_ORDER = ('AUTO','ASK','REVIEW','BLOCK')`，`max(['ASK','REVIEW'])` 为 `REVIEW`。
   治理面变更若同时 `business_direction_count >= 2`，原本命中
   `ROUTE-ASK-MULTIPLE-DIRECTIONS`，改后变为 REVIEW —— **ASK 的用户选择义务被静默销毁**。
   讽刺的是，这正是本轮用来替代 B1「priority 论证」的那个机制。
2. **`missing: match` 不可达。** `impact_scope` 是 decision-unit schema 的**必填**字段
   （本轮规格还把这一点当作设计依据引用过），因此 fail-closed 分支永不触发，
   对应验收条件在测一个引擎无法产生的状态。

另有：模式清单遗漏 `.ai/bootstrap-mode.yaml`（决定 `aiflow verify`/`gate` 在 CI 中是否运行
的开关）、`.gitignore`、`.gitattributes` 与任务账本 `.ai/tasks/**`；`fnmatch` 与仓库既有
`scope.matches_scope` 是两套不兼容的 glob 方言（裸目录条目结果相反）；新增的 `governance`
类别不被任何规则读取，因此 REV-0001/RF-003 并未关闭。

#### 结论

守卫要生效，落点是 `aiflow scope`／`gate` 这类能看到真实 diff 的位置，而不是分类期的路由
规则。这是比本轮规格更大的一次设计变更，须另行立项并单独受审。**在此之前 B1 保持 blocked。**

### Chapter B1：让验证强度成为路由输入

状态：`blocked`（2026-09-04）。TASK-0040 已开立并冻结规格，独立设计审核 REV-0001 结论为
`REQUEST_CHANGES`，8 条发现全部 open，`aiflow approve --type spec` 被门禁拒绝
（`Review outcome cannot support approval`）。**本章按原设计不可推进。**

#### 审核推翻的四项前提

1. **规则无法只改 Policy 实现。** `src/aiflow/routing.py:15` 的 `_AUTO_GUARDS` 是引擎级
   硬编码白名单，`routing.py:164` 要求每条 AUTO 规则的条件集合是其**超集**，其中含
   `('impact.level','equals','low','error')`。任何放宽 `impact.level` 的 AUTO 规则都会
   触发 `ROUTING_AUTO_GUARDS_INCOMPLETE`，使整个 Policy bundle 加载失败。要实现必须修改
   `src/aiflow/routing.py` —— 它在 `AGENTS.md` 升级清单上，且不在 TASK-0040 的
   `allowed_scope` 内。这也意味着放宽会降低**所有现有与未来** AUTO 规则的守卫下限。
2. **立论测错了对象。** 「17 个只差 `impact.level`」测的是**哪个守卫挡住了 AUTO**，
   不是**是否需要人类审核**。这 17 个里有 4 个（TASK-0005、0018、0022、0024）实际收到
   **8 条审核 finding 与 7 次 `REQUEST_CHANGES`**。把它们判为 AUTO 会跳过发现了真实问题的审核。
3. **兜底的 HARD-* 规则本身就会静默失效。** `HARD-REVIEW-SECRETS-AUTH` 与
   `HARD-REVIEW-CI-CD` 的条件都是 `missing: no_match` —— `impact_categories` 缺失即不匹配，
   而 schema 并不要求该字段必填。此外 `external_side_effects` 只是执行前的自声明：
   `.ai/tasks/TASK-0018/paid-external-call-incident.md` 记录了它被证伪的案例，而 TASK-0018
   正是那 17 个样本之一。
4. **安全论证的机制写错了。** 有效路由是 `routing.py:245`
   `max((hit.route for hit in hits), key=ROUTE_ORDER.index)` —— 按严重度取最大，**与 priority
   无关**；priority 只决定写进证据的 `rule_id`。结论（HARD-* 仍然胜出）碰巧成立，但依据不同：
   保护来自严重度聚合，不是优先级排序。

另有三条：`missing: error` 实际产生 BLOCK 而非回落 REVIEW（`predicates.py:89`）；
`policy_version` 必须四个 Policy 文件同步提升（`policy.py:150` `_validate_cross_file`），
而 `allowed_scope` 只含 `routing.yaml`；`impact_categories` 枚举无 policy/governance 取值，
治理面变更无法被任何 HARD-* 规则捕获。

#### 修正后的推进顺序

审核建议的排序是**反过来的**：先补齐 `impact_categories` 的治理取值并新增一条覆盖
`.ai/policy/**`、`.ai/schemas/**`、`src/aiflow/**` 的 `HARD-REVIEW` 规则，验证它确实在这些
路径上触发；**之后**才谈放宽 AUTO。否则「HARD-* 规则仍然兜底」这个安全故事不成立 ——
而它正是放宽 AUTO 的全部依据。

`_AUTO_GUARDS` 的放宽应作为独立、显式的一次设计决策接受审核，不能夹带在一次 Policy
文件编辑里。

原章节内容保留在下，作为被推翻的设计记录。

针对 M1 与 M2。当前 `ROUTE-DEFAULT-REVIEW` 兜底导致 17 次非风险性 REVIEW。

#### 进入条件

- Part A 的账本状态已确定，或已确认 B1 不依赖 A。
- 已确认本章不修改任何 `.ai/policy/hard-rules.yaml` 规则。
- 取得绑定当前 frozen spec、Policy 与 base commit 的 spec approval。

#### 任务

1. 在 `.ai/policy/routing.yaml` 中新增一条优先级高于 `ROUTE-DEFAULT-REVIEW`、低于全部
   `HARD-*` 规则的 AUTO 规则：当自动验证可用、验证等级达到 V1 或以上、无外部副作用、
   且变更路径不落在硬风险集合时判为 AUTO。
2. 明确该规则的字段缺失语义：任一判据 `missing` 时不得默认成立，须回落到 REVIEW。
3. 保留 `ROUTE-DEFAULT-REVIEW` 作为最终兜底，不删除、不降优先级。
4. 提升 Policy 版本，并按现有兼容性约定处理版本化 contracts。
5. 为新规则补正向与负向分类测试：验证充分的低风险变更判为 AUTO；secrets/auth、CI/CD、
   部署、生产数据删除、外部副作用、不可逆无备份、验证工具缺失、凭据或敏感数据外传
   八类仍分别命中原有 `HARD-*` 规则。

#### 验证

```powershell
python -m pytest tests/unit -q
python -m pytest tests/integration -q
python -m pytest tests/acceptance -q
python -m pytest -q
python -m mypy src
python -m ruff check .
python -m ruff format --check .
python -m aiflow classify <TASK_ID>
```

#### 退出条件

- 新规则在正向与负向测试中均确定性成立。
- 用历史 38 个 task 的 classification input 重放，能给出新旧路由分布对比，并逐条解释
  由 REVIEW 转为 AUTO 的每一个 task 为何不属于硬风险。
- 八条 `HARD-*` 规则的命中结果与改造前逐条一致。

### Chapter B2：批准从绑精确 commit 改为绑范围

针对 M3。48 条重复批准中 28 条由 `subject_commit` 变化驱动。

#### 进入条件

- B1 与 B3 已完成，避免同一轮内同时改变路由与批准语义。
- 已确认改造不削弱「批准必须绑定被审内容」这一原则。

#### 任务

1. 将 `src/aiflow/freshness.py` 中已有的 `subject_synchronized` 容差扩展到
   `code_approval`：当存在完整、可审计的 `subject_commit_synchronized` 事件链把已批准
   subject 连到当前 subject 时，不触发 `FRESHNESS_SUBJECT_CHANGED`。
2. 将 `base_commit` 的比较从「精确相等」改为「merge-base 未变即视为新鲜」，使 rebase
   到新 `main` 不再作废 spec 与 code 批准。
3. 保持 `spec_sha256`、`policy_sha256`、`evidence_sha256` 的精确绑定不变 —— 被审内容、
   Policy 或证据本身变化时批准必须失效。
4. 明确新增语义的失效边界：同步链断裂、事件缺失、事件被篡改时一律回落到失效。
5. 为每一条新语义补负向测试：伪造同步链、跳跃的 subject、被改写的事件序列都必须失效。

#### 验证

```powershell
python -m pytest tests/unit/test_freshness.py -q
python -m pytest tests/integration -q
python -m pytest tests/acceptance -q
python -m pytest -q
python -m mypy src
python -m aiflow gate <TASK_ID>
```

#### 退出条件

- 无关 fixup 与 rebase 不再作废批准，且有测试证明。
- 被审内容、Policy、证据任一变化仍立即作废批准，且有测试证明。
- 历史 evidence 与 approval 的原有结论不因本次改造被重新解释为「通过」。

### Chapter B3：action 批准分级

针对 M4。20 条 action 重复批准中 12 条的绑定字段与前一条完全相同。

按 M4 的实测结论，本章的改造对象必须分两类，不能只改 schema：`push` 与 `merge` 目前只有
Policy 要求、没有代码强制，其开销来自流程约定；被代码单次消费的只有 `targeted_mutation_v2`，
实现在 `src/aiflow/mutation_evidence.py` 与 `src/aiflow/approval.py`，而不是
`freshness.py` 的 action 分支。

#### 进入条件

- 已确认 `delete`、`secret_export`、`paid_external_call`、`deploy` 四类保持单次一批。
- 取得对「push 与 merge 改为 task 级授权」的明确决定。
- 已确认改造后仍不新增任何自动执行 push 或 merge 的代码路径。

#### 任务

1. 在 `.ai/schemas/approval.schema.json` 中把 `single_use` 从 action 类型的无条件必填，
   改为按 action 类型区分：高风险四类仍强制 `single_use: true`；`push` 与 `merge` 允许
   task 级授权。
2. 定义 task 级授权的边界：一次批准覆盖该 task 在其 `allowed_scope` 内的 push，以及
   CI 门禁通过后对该 task 的 merge；`allowed_scope` 扩大即失效。
3. 把 `expires_at` 的语义从固定时窗改为随 task 终态失效，并保留显式过期时间上限。改动点
   在 `src/aiflow/approval.py` 的 `validate_action_file()` 与 `approval_is_current()`。
4. 若要调整 `targeted_mutation_v2` 的一次性消费语义，改动点在
   `src/aiflow/mutation_evidence.py`（`_used_action_digests()` 与
   `logs/action-launch-<action_sha256>.json` 的独占创建），不要误改 `freshness.py`。
5. 明确记录一项现状：`freshness.py` 的 `action_approval` 分支当前没有生产调用方
   （`gate.py:531` 与 `status_service.py:211` 均先过滤掉 action，
   `status_service.py:132` 把 `used_action_sha256s` 硬编码为 `()`）。本章要么给它接上
   调用方，要么显式记为 dead branch —— 不得让它继续以「看起来在生效」的状态留存。
6. `.ai/policy/permissions.yaml` 的 `forbidden_automatic_actions` 六项不变 —— 本章改变的
   是一次批准覆盖多少次执行，不是是否需要人类批准。
7. 补负向测试：`allowed_scope` 扩大后授权失效；task 终态后授权失效；高风险四类仍单次一批。

#### 验证

```powershell
python -m pytest tests/unit -q
python -m pytest tests/integration -q
python -m pytest -q
python -m mypy src
python -m aiflow validate <TASK_ID>
```

#### 退出条件

- 一个 task 的正常 push 与 merge 只需一次 action 批准，重试不再消耗新券。
- 六类禁止自动执行的动作仍全部需要人类批准，且仍无任何自动执行它们的代码路径。
- 高风险四类的单次一批语义有测试保护。
- `freshness.py` 的 `action_approval` 分支已接上调用方，或已在代码与文档中显式标注为
  当前无生产调用方。

### Chapter B4：账本推进自动化

针对 M5。44.2% 的非 merge 提交只改动 `.ai/tasks/`。

#### 进入条件

- B1、B2、B3 完成，账本推进的语义已稳定。
- 已确认本章不改变任何审批点，只改变机械步骤的执行方式与留痕位置。

#### 任务

1. 识别 `bind classification`、`bind subject`、`record verification and gate`、`close`
   四步中不需要人类判断的部分，合并为单条 CLI 命令。
2. 为该命令定义确定性前置条件与 fail-closed 语义：任一前置不满足即拒绝，不做部分推进。
3. 评估把账本提交移出主线历史的方案（如独立提交序列或单独引用），给出对
   `.ai/tasks/` 追加式要求、CI 任务解析（TASK-0035 已修复的 merge-base 解析）和证据
   可检出性的影响分析。**本章只交付方案与影响分析，是否实施单独决定。**
4. 不改变任何审批点：合并的是机械步骤，不是人类决策点。

#### 验证

```powershell
python -m pytest tests/unit -q
python -m pytest tests/integration -q
python -m pytest tests/e2e -q
python -m pytest -q
python -m aiflow status <TASK_ID>
```

#### 退出条件

- 单条命令可完成四步机械推进，且有 fail-closed 测试。
- 账本提交数量相对同类历史任务显著下降，并有可比数据。
- 账本仍为追加式，历史证据仍可按字节检出。

## 6. 度量

改造前后用同一口径复算下列指标，作为是否达成目标的判据：

| 指标 | 改造前基线 | 目标方向 |
|---|---|---|
| 路由分布中 AUTO 占比 | 9 / 38 | 上升 |
| `ROUTE-DEFAULT-REVIEW` 命中次数 | 17 | 下降 |
| `HARD-*` 规则命中次数 | 11 | 不变 |
| 重复批准占比 | 48 / 113（42.5%） | 下降 |
| 每 task 平均批准记录数 | 2.97 | 下降 |
| 只改动 `.ai/tasks/` 的提交占比 | 169 / 382（44.2%） | 下降 |
| CI 质量门禁检查项与阈值 | 完整测试、85%、90% diff、whitespace、Ruff、format、mypy | 不变 |

复算脚本不属于本目录交付物；统计口径以本文件第 1 节的定义为准。

## 7. 风险与边界

1. **B1 是风险最高的一章。** 反转默认值意味着分类错误的后果从「多一次人工审查」变成
   「少一次人工审查」。因此 B1 的退出条件要求逐条解释每个由 REVIEW 转 AUTO 的历史 task，
   而不是只看测试通过。
2. **B2 放宽的是绑定粒度，不是绑定本身。** 若同步链可被伪造，整个批准体系的可信度即失效；
   负向测试是本章的核心交付物，不是附带项。
3. **B3 不减少需要人类批准的动作种类。** 六类禁止自动执行的动作全部保留。
4. **A 部分会改动任务账本。** 账本在 `AGENTS.md` 升级清单内且为追加式，`close` 只能追加
   终态事件，不得回填、覆盖或删除既有记录。
5. **本目录不授权任何外部动作。** push、merge、deploy、delete、凭据导出、付费调用在改造
   完成前后都需要按当时生效的 Policy 单独获批。
6. **已核实与未核实的界线。** 第 1 节指标表与 M1–M5 中的全部计数，可在基线 `3ce0e06`
   上由 `.ai/tasks/**` 与 `git` 历史直接复算。M1–M4 的机制描述引自 `.ai/policy/**`、
   `.ai/schemas/**` 与 `src/aiflow/**` 的当前文件内容，已逐条对照源码核实；
   「13/13 chapters 完成」引自 `docs/superpowers/state/overall.yaml`。但第 1.1 节中
   「REVIEW 的实际含义」「维护模式体感」「重复批准的唯一原因」等表述，以及第 1.2 节的
   根因，是对这些计数的解释与诊断，不是测量结果。第 5 节各章的预期效果同样是设计推断，
   只有在对应退出条件的复算完成后才能称为已达成。
7. **本目录的事实经过独立复核。** 全部事实断言已由独立 agent 按集群重新推导，并对未获
   确认的断言做第二轮裁决。该过程改正了八处错误，其中包括一条被推翻的机制结论
   （M4 原先声称 AUTO 任务开 PR 至少消耗 2 次 action 批准，实际无任何代码路径强制），
   以及第 2 节非目标中漏列 `HARD-REVIEW-CI-CD` 这一处。复核覆盖第 1 节统计、
   M1–M5 机制、Part A 的全部终态判断与归档完整性。

## 8. 归档

章节 1–7 的 39 份逐任务执行文档已移入 `docs/archive/plans/`，内容未改动。归档原则、
未归档项的理由和完整路径映射见[文档归档](../../archive/README.md)。

`docs/superpowers/state/**` 仍按归档前的原路径引用这些文档，这是有意保留的：那些引用
位于绑定 `base_commit` / `subject_commit` 的 `evidence:` 列表，以及带 `raw_sha256` 的
历史 `git status` 快照中，改写会篡改历史记录。请通过归档索引的映射表解析。
