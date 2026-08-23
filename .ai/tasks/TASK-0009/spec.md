# Task Specification

## 目标

完成 Chapter 10：为 V2 建立可重放的角色独立性、最小 Verifier 上下文、两阶段 evidence 和 Gate 判定，同时保持 V0/V1 的契约、哈希及执行语义不变，并修复仅有当前任务治理提交时 `begin` 无法继续的基线兼容问题。

## 范围

1. 角色事实：Implementer 取当前实现周期最近一次 `implementation_started` 或 `implementation_retried` 事件的非空 actor；Verifier 取 `aiflow verify --actor`；Reviewer 继续取现有结构化 design/implementation review 记录。角色标识经 trim 后按精确字符串比较，不被解释为人员或外部身份认证。
2. 新增严格的 `verifier-context` 契约和 task-local immutable 存储。上下文只包含任务目标、冻结规格、代码地图/允许范围、subject diff 的路径与 numstat 摘要、验收条件、已知限制、复现 argv，以及 task/repository/base/subject/spec/Policy/classification 绑定；不得包含 Implementer 对话、内部推理、完整 patch、原始日志或凭据。
3. Verifier context 使用 canonical JSON（UTF-8、排序键、紧凑分隔符）计算 SHA-256，保存到 `.ai/tasks/<TASK-ID>/verifier-contexts/<sha>.json`；文件名、内容与当前版本事实必须一致。
4. `aiflow verify TASK-ID --actor ACTOR` 对 V2 在启动任何验证进程前要求 Implementer 与 Verifier 均非空且不同，并生成/复用当前 Verifier context。V0/V1 不增加该要求。
5. V2 evidence 使用显式两阶段契约解决 implementation review 与 evidence 互相引用：
   - `pre_implementation_review`：包含 verifier、context、design review、checks 与稳定 `verification_snapshot_sha256`，不包含 implementation review 引用；可供实现审核绑定，但 Gate 必须拒绝。
   - `final`：在 snapshot 不变的前提下补入当前 implementation review 引用；只有 final evidence 才可进入 V2 Gate。
   - snapshot 为 evidence 的 canonical 投影摘要，排除 `phase`、`review_refs.implementation` 和摘要字段本身；其余验证、版本、actor、context、design review、checks、subject 与 attestation 事实全部纳入。
6. V2 implementation review context 使用 `schema_version: "2.0"` 和 `verification_snapshot_sha256` 绑定上述稳定投影；现有 V0/V1 review context `1.0` 继续绑定完整 `evidence_sha256`，字节与回放语义不变。
7. `aiflow verify TASK-ID --actor ACTOR --finalize` 只在当前 pre evidence 已通过、Verifier actor/context/snapshot 当前且 implementation review 可批准时补齐 final 引用；它不重跑命令、不改变 snapshot 中的验证事实。
8. Chapter 10 不执行 Chapter 11 拥有的 acceptance、integration 与 targeted mutation。当前 V2 live run 只可执行既有 V1 前缀，新增三项以 `unverified` 和稳定 reason code 写入 pre evidence；`independent_verifier` 仅在 actor/context 校验通过时记录为 passed。因此当前 live V2 结论必须 failed，不能进入 implementation review 或 final Gate。测试可以用完整、确定性的 passed fixtures 验证两阶段 finalization 与 Gate 回放。
9. V2 Gate 在现有 freshness、approval、scope 与 Git attestation 之上验证：final phase、snapshot 可重算、Verifier 与 Implementer 不同、context 当前且未篡改、design/implementation review 引用可批准并绑定同一版本事实、全部 required checks passed、mutation 结果非空且全部 killed、local/CI evidence 与 attestation HEAD 边界正确。
10. V2 code approval 继续依赖当前 local final evidence；外部 CI evidence 只用于 Gate attestation，不替代 local evidence 或 code approval。
11. `begin` 的 Git 基线检查允许 `subject_commit..HEAD` 仅包含当前任务 `.ai/tasks/<TASK-ID>/**` 治理提交；仍拒绝任何业务路径、其他任务治理路径、分支/仓库不符或超出创建时 dirty baseline 的工作树变化。该兼容只消除治理提交死锁，不同步 subject、不放宽实现范围。

## 非目标

- 不修改 routing/verification Policy 或 V2 选择规则。
- 不实现 acceptance、integration、mutation manifest/runner 或 mutation 预算；这些属于 Chapter 11。
- 不实现 Hooks、运行期升级或 Phase 2 真实试点；这些属于 Chapters 12–13。
- 不实现 V3、真实人员/模型身份认证、外部 Verifier API、模型路由或对话持久化。
- 不改变 design/implementation review 的发现处置语义，也不要求 Reviewer 与其他 actor 必须不同。
- 不允许 `begin` 越过任何业务代码、配置、文档或其他任务治理提交。

## 验收条件

1. verifier-context contract 的 valid/missing/invalid/extra fixtures 结果确定，canonical hash 可复算；内容、文件名、subject/spec/Policy/classification 任一篡改或陈旧均被拒绝。
2. V2 verify 对缺失 Implementer、空 Verifier、相同 actor 均在 process runner 启动前拒绝；不同 actor 生成最小 context。V0/V1 actor 与执行回归保持原样。
3. V2 pre evidence 能稳定计算 snapshot；除 phase 和 implementation ref 外任一纳入投影的字段变化都会使 snapshot 或 implementation review 失效。
4. passed pre evidence → implementation review → final evidence 的 fixture/service 流程可重放；finalize 不运行命令且不改变 snapshot。缺审核、错误 stage/ref、不可批准结论或陈旧 review 时拒绝。
5. V2 Gate 的完整 final happy path 通过；pre phase、同 actor、context 篡改、snapshot 篡改、缺失/陈旧双审核、required check 未通过、survived/unverified mutation、attestation HEAD 不同均产生稳定拒绝码。
6. 旧 V0/V1 classification/evidence/review/Gate fixtures 和 parity 结论不变；`aiflow verify` 的既有 V0/V1 行为不被倒灌 V2 要求。
7. `begin` 在 HEAD 仅前移当前任务治理路径时成功；同样历史中加入任一业务路径或其他任务路径时仍以 `BEGIN_GIT_CONTEXT_CHANGED` 拒绝。
8. Ruff、format、mypy、全量 pytest、branch coverage、diff coverage（新增 Python 差异不低于 90%）及 `git diff --check` 全部通过。
9. README、运维说明、Chapter 10 实施记录和状态追踪准确说明 actor 仅为任务标识、当前 V2 live run 仍因 Chapter 11 检查未实现而不能通过，以及治理-only begin 兼容边界。

## 禁止动作

- 禁止 push、merge、deploy、delete、凭据导出和付费外部调用。
- 不得用 `aiflow --help` 占位命令、自然语言确认、伪造 review ref 或伪造 mutation 结果生成 passed V2 evidence。
- 不得降低 route、verification level、review、approval、freshness 或 Gate 要求。

## 错误行为

- V2 actor 缺失/相同、context 缺失/篡改/陈旧必须在相应阶段确定拒绝，且验证命令不能提前启动。
- pre evidence、snapshot 不匹配、非 current review、跨 task/stage/subject/spec/Policy 引用或非 final evidence 必须阻止 Gate。
- V2 live run 中 Chapter 11 检查必须显式 unverified 并令 evidence failed；不得静默回退 V1 或把未执行记为 passed。
- 输入契约损坏继续报告为输入错误；结构合法但门禁不满足继续报告为 Gate reason codes。
- `begin` 不得把允许范围内的业务提交误当成治理提交，也不得接受其他任务治理路径。
- 实际需要修改 Policy、扩大文件范围或改变已冻结的两阶段语义时，必须显式升级、重新分类、重新冻结并重新批准。

## 回滚

所有变更仅为本地版本化代码、契约、测试和文档，可通过后续反向提交回滚。旧 V0/V1 文件不迁移、不重写；新增 V2 pre/final artifacts 可按其 schema_version 独立识别。治理-only begin 兼容可独立反向提交，不影响既有严格业务路径检查。
