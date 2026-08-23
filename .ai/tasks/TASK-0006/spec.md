# Task Specification

## 目标

完成 Chapter 9 的 V2 Policy、版本化 classification/evidence contracts 与 route-independent 分类闭环：V2 严格包含 V1，显式 V2 facts 才能升级，旧 V0/V1 任务和已落盘记录保持原语义。本章只定义并解析 V2，不生成 V2 evidence、不执行 V2 验证，也不改变 Gate。

## 范围

- 将四份 Policy 的 `policy_version` 同步升级为 `2.0.0`，verification levels 必须按 `V0, V1, V2` 有序且各级为前一级的语义相同前缀。
- V2 在完整 V1 checks 后只新增 `acceptance`、`integration`、`targeted_mutation`、`independent_verifier`，顺序固定且全部 required；不得把未实现检查静默回退为 V1 或伪装为 passed。
- decision unit 新增可选、封闭的 `verification_requirements`：`acceptance_required`、`integration_required`、`targeted_mutation_required`、`independent_verifier_required` 四个布尔字段。对象缺失时完全保留旧 V0/V1 结果；任一为 true 时选择 V2，并记录对应稳定 rule ID；route 计算不读取这些 facts。
- `classification.schema.json` 通过显式版本分支保留 `1.0 => V0/V1`，增加 `2.0 => effective V2`；classification service 仅在 effective level 为 V2 时写 `2.0`，V0/V1 新旧输出继续写 `1.0`。
- `evidence.schema.json` 通过显式版本分支保留 `1.0 => V0/V1`，定义 `2.0 => V2` 的 verifier actor/context hash、design/implementation review refs、四项 required checks 和 targeted mutation manifest/results；本章不生成该 evidence。
- verification plan parser 能确定性解析 V2 固定顺序；执行服务必须在解析或启动任何 V2 check 前以稳定错误码 `VERIFY_V2_NOT_EXECUTABLE` 明确拒绝 V2，直到 Chapters 10–11 实现独立 Verifier、evidence writer 和 mutation 编排。
- status 能识别并显示 V2 classification；现有 verify/Gate 对 V0/V1 的行为与 reason codes 不变。
- 更新 Policy/schema/selection/parser/status 的单元和集成测试、V2 contract/plan fixtures（含未知额外字段拒绝样例）、README、Chapter 9 实施与状态文档，以及本任务 `.ai/tasks/TASK-0006/**` 治理记录。

## 非目标

不实现 V2 验证执行、`ai-verify`、Implementer/Verifier actor 隔离、V2 evidence 写入、Gate V2 规则、验收执行器、mutation runner、Hooks/CI 扩展、V3 或真实外部动作；不修改旧 V0/V1 fixture 内容，不自动迁移或重写历史 classification/evidence。

## 验收条件

1. Policy loader 只接受恰好有序的 V0/V1/V2；拒绝 V3/未知、重复、缺失、乱序、前缀篡改、V2 extra 缺失或 optional。
2. V2 plan 解析顺序为完整 V1 prefix 后接四项固定 checks；V0/V1 plan fixture 和 argv 完全不变，执行入口不得 fallback 到 V1。
3. 每个 V2 requirement 均独立产生 V2 和稳定 rule ID；对象缺失或全 false 保持现有 V0/V1；多 decision unit 取 V2 最高级，completed V2 unit 不抬高未完成任务等级但保留其 decision。
4. route 标签变化不改变相同 verification facts 的级别；V1→V2 为 upgrade，V2→V1 为 downgrade 并要求既有授权恢复流程。
5. classification/evidence `1.0` 继续只接受 V0/V1；V2 必须使用 `2.0` 且满足新增字段。V2+1.0、V1+2.0、未知版本/级别、缺失 verifier/review/mutation/check 均被拒绝。
6. 旧 contract/golden/classification/freshness/evidence/Gate 回放测试原样通过，无静默重分类。
7. `pytest`、Ruff、format、mypy、coverage、diff coverage、`aiflow validate/scope` 与 `git diff --check` 通过；Chapter 9 五项任务和三项退出条件有提交绑定证据。
8. 修改 active Policy 后必须执行完整二次治理：`escalate --to REVIEW --reason-code policy_changed`；在 TASK-0006 内写入绑定新 Policy hash 的处置证据并执行 `resolve --condition policy_changed`；随后重新 `classify`、`freeze`，生成绑定新 Policy hash 的 fresh design context/record，并取得新的 spec approval。旧 design review/spec approval 不得复用；最终 code approval 绑定当前 subject、V1 evidence 与 implementation review。

## 禁止动作

push、merge、deploy、delete、secret export、paid external call、package publish；不得通过放宽旧 schema、修改旧 fixture、把 V2 当 V1 执行或伪造 V2 passed evidence 来取得兼容。

## 错误行为

未知/乱序 levels、任一高级别缺失或篡改低级别 prefix、V2 check 非 required、非法/残缺 verification requirements、版本与级别不匹配、V2 contract 缺独立性/审核/mutation 绑定、V2 执行 fallback 或启动任何 check、Policy 版本不一致、旧 V0/V1 输出漂移均必须失败。范围、Policy、facts、权限或相邻章节边界变化时必须升级并重新冻结批准；缺少 `policy_changed` resolve evidence 时不得重新分类。

## 回滚

代码、Policy、schema、fixtures、测试和文档均由本地 commit 保护。回滚通过后续获批任务显式 revert；不改写 TASK-0006 事件、审核、批准或验证历史。旧 V0/V1 schema 分支和 fixtures 始终保留，V2 可在未启用执行服务时保持 contract-only。
