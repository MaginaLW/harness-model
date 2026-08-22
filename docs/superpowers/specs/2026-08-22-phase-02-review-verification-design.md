# 阶段二：审核与强化验证设计

状态：proposed
日期：2026-08-22
目标仓库：`harness-model`
阶段一基线：`0.1.0` / `695da6419cfc6157411ff8488dbeed70dfdf5c61`

## 1. 背景与进入结论

阶段一已经完成 12 项验收、4 类真实试点、干净检出验证和 `0.1.0` 基线。`docs/implementation/phase-02-entry-inputs.md` 提取了六类仍有证据支持的缺口：结构化审核、V2、独立 Verifier、定向变异、动态升级和完整 Hooks。

阶段二把当前 `harness-model` 固定为第一个跨模块 REVIEW 自举目标。目标变更天然跨越 Policy、contracts、CLI、状态、evidence、Gate、Hooks 和测试；若错误地声明高强度验证已经通过，治理变更可能在证据不足时被放行，因此其业务风险和测试边界都足够明确。

进入阶段二不等于直接启用 V2。现有运行时只能权威执行 V0/V1，所以先以现有 `REVIEW + V1` 建立结构化审核契约，再按版本化兼容方式增加 V2。

## 2. 目标

阶段二要交付一条可重放的跨模块 REVIEW 路径：

1. 设计审核和实现审核使用不同阶段、不同输入和不同版本绑定。
2. V2 在 V1 之上增加验收、集成、定向变异和独立 Verifier 证据，不改变旧 V0/V1 记录的语义。
3. Verifier 只使用可审计的最小上下文，并且不能与 Implementer 使用同一任务角色标识。
4. 运行期观察到范围、Policy、验证或权限变化时只升级或拒绝，不自动降级。
5. Hook、CLI 和 CI 调用同一确定性核心，对相同事实得到相同结论。
6. 当前仓库最终用新能力完成一次 design review → implementation → independent verification → implementation review → CI/Gate 自举试点。

## 3. 非目标

- 不实现 V3、安全扫描、故障注入、生产 dry-run 或回滚演练。
- 不实现模型注册、模型调用、自动模型选择、成本统计、信任评分或多模型路由。
- 不实现资源调度器、DAG 调度、租约、抢占或跨主机编排。
- 不运行全仓库通用变异测试，只验证本阶段新增的关键治理保障。
- 不把 task record 中的 actor 字符串描述成外部身份认证。
- 不自动 push、merge、publish、deploy、删除或执行真实高风险命令。

## 4. 不变量

1. route 与 verification level 是独立维度；跨模块事实不能直接覆盖 route 结论。
2. 新能力只能提高或维持要求，不能让已有任务自动降级。
3. spec、Policy、base commit、subject commit 或行为性 subject 发生变化时，相关批准和 evidence 必须按既有 freshness 规则失效。
4. `code` approval 继续只接受当前任务的本地 passed evidence；CI 外部 evidence 只由 Gate 作为权威输入，二者不互换。
5. subject evidence 与 governance-only attestation 保持分离，治理记录不能伪装成 subject 代码变化。
6. Hook 只采集事实并调用共享核心，不复制 Policy 决策表。
7. 所有新增 contracts 继续拒绝未知字段；兼容性必须通过显式版本演进实现。

## 5. 目标工作流

### 5.1 设计审核

设计审核发生在实现开始前，绑定 frozen spec、Policy 哈希和 base commit。审核包至少包含：目标、功能上下文、拟议代码地图、语义变化、风险、未验证项、明确问题和推荐结论。

设计发现项拥有稳定 ID、严重度、位置/主题、证据、处置状态和处置说明。未关闭的高严重度发现、`REQUEST_CHANGES`、`REJECT` 或 `BLOCKED` 结论不能形成有效 spec approval。

### 5.2 实现审核

实现审核发生在 subject commit 和权威验证 evidence 已存在之后，绑定实际 diff、subject commit、evidence 哈希和当前 spec/Policy。它复核“实现是否符合批准设计”，不能复用设计审核结论代替代码审核。

### 5.3 独立验证

V2 Verifier 获得最小上下文：原始目标、已批准规格、代码地图、subject diff 摘要、验收条件、已知限制和复现入口。上下文不包含 Implementer 对话或非必要内部推理。

本阶段的独立性是可执行的任务记录约束：Implementer 与 Verifier 的非空 actor 标识必须不同，Verifier actor、上下文摘要/哈希、命令和 subject commit 写入 evidence。它不是人员身份认证。

### 5.4 Gate

V2 Gate 在现有 freshness、approval 和 Git attestation 事实之上增加：必需检查齐全、独立 Verifier、最小上下文、设计审核、实现审核及定向变异均有效。输入损坏仍与门禁不满足分开报告。

## 6. 版本化契约

### 6.1 审核记录

新增审核记录应采用独立版本化 schema，不扩写旧 approval 文件来承载全部发现：

- `review_stage`: `design | implementation`
- `review_id`、`task_id`、`actor`、`conclusion`
- `spec_sha256`、`policy_sha256`、`base_commit`
- 实现审核额外包含 `subject_commit`、`evidence_sha256`
- `context_package` 摘要和哈希
- `findings[]`: ID、severity、location、evidence、status、resolution

Chapter 8 只实现该记录及其 freshness/approval 前置关系，不改变 evidence schema 或 Gate。

### 6.2 V2 evidence

V2 在后续章节通过 evidence schema 的新版本实现，至少新增：

- acceptance 与 integration 检查结果；
- verifier actor 与最小上下文哈希；
- design/implementation review 引用；
- targeted mutation 清单、killed/survived 结果和日志引用；
- 明确的未覆盖项。

旧 V0/V1 fixture、已落盘 evidence 和 Gate 回放必须保持兼容；V3 与未知级别继续被拒绝。

## 7. 失败语义

以下情况必须阻止推进，不得用自然语言“已确认”覆盖：

- 审核阶段、必需字段或版本绑定缺失；
- 结论不是可接受结论，或存在未关闭高严重度发现；
- spec、Policy、base/subject commit 或 evidence 已陈旧；
- V2 缺少任一必需检查、Verifier 与 Implementer 相同、最小上下文被篡改；
- 任一定向 mutant survived 或未执行；
- Hook 观察到范围越界或高风险命令，却未产生升级/拒绝事件；
- CLI、Hook、CI 对相同输入产生不一致结论。

## 8. 测试策略

阶段二使用四层确定性、离线测试：

1. 单元测试：schema、parser、finding、freshness、独立性和 Policy 规则。
2. CLI/集成测试：双审核命令、批准前置、V2 verify/evidence/Gate、升级和 Hook parity。
3. E2E：成功自举及相同 actor、陈旧审核、survived mutant、范围越界等拒绝路径。
4. 定向变异：只破坏本阶段关键保障，并证明相应测试失败。

所有章节仍运行 Ruff、格式、mypy、全量 pytest、分支覆盖率和 `git diff --check`。新增代码差异覆盖率不得低于现有 90% 门槛。

## 9. Policy 影响评估

- Chapter 8 不修改 routing/verification Policy，也不改变 Gate；它只为现有 REVIEW 路径增加可审计的审核前置条件。
- Chapter 9 将修改 `.ai/policy/verification-levels.yaml`、相关 classification facts 和 versioned contracts，属于治理行为变化，必须重新 classify、freeze 和 spec approve。
- Chapters 10–11 扩展 evidence/Gate 对 V2 的解释，但不得改变旧 V0/V1 evidence 的结论。
- Chapter 12 增加观察事件与 Hook 入口；决定仍由共享 Policy/core 产生，Hook 自身无权降低 route/V。
- 任一章节若实际影响超出上述评估，必须记录 `policy_changed`、`verification_changed`、`scope_changed` 或对应 escalation reason 后重新定级。

## 10. 分章边界

| 章节 | 主题 | 核心交付 |
|---|---|---|
| Chapter 8 | 结构化双阶段审核 | 审核 schema、最小审核上下文、发现处置、approval/freshness 前置，不改 Gate |
| Chapter 9 | V2 契约与分类 | 版本化 Policy/contracts、V2 选择规则、旧 V0/V1 兼容 |
| Chapter 10 | 独立 Verifier 与 ai-verify | 最小验证上下文、actor 隔离、V2 evidence 与 Gate |
| Chapter 11 | 验收、集成与定向变异 | V2 检查编排、mutant 清单、killed/survived 证据 |
| Chapter 12 | 升级观测与完整 Hooks | 编辑/命令观察事件、共享核心、Hook/CLI/CI parity |
| Chapter 13 | 自举 REVIEW 试点与阶段二验收 | 当前仓库真实闭环、验收报告和阶段二退出基线 |

这种顺序避免用尚未实现的 V2 验证 V2 自己，也避免在审核契约稳定前修改 Gate。

## 11. 可追踪验收

| 输入 | 交付章节 | 退出证据 |
|---|---|---|
| P2-REV-01 | 8 | 两阶段审核 fixture、发现处置与 freshness 测试 |
| P2-V2-01 | 9、10 | V2 Policy/contracts、verify/evidence/Gate 回放 |
| P2-VER-01 | 10 | 不同 actor、最小上下文和篡改拒绝测试 |
| P2-MUT-01 | 11 | 定向 mutant 全部 killed 的可重放 evidence |
| P2-ESC-01 | 12 | 观察事件到 escalation 的集成测试 |
| P2-HOOK-01 | 12 | Hook/CLI/CI parity 与支持边界说明 |

Chapter 13 汇总六项证据并完成真实跨模块 REVIEW + V2 试点。

## 12. 批准点

- 本设计和实施目录提交后，Chapter 8 行为性实现必须创建独立 `REVIEW` 任务，并获得绑定 frozen spec、Policy 与 base commit 的 design/spec approval。
- Chapter 9 修改 verification Policy 时必须升级/重新分类、重新冻结并重新批准。
- code approval 只能在当前 subject commit 的权威验证与实现审核通过后产生。
- 任何高风险 action 仍需单独 action approval；本阶段计划不授权此类动作。
