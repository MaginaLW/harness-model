# Chapter 9：V2 Policy、contracts 与分类

状态：completed
阶段二目标仓库：`harness-model`

## 本章结果边界

本章将 active Policy 升级为 `2.0.0`，定义并解析严格的 V2 验证计划，增加 route-independent V2 选择事实，并为 classification 与 evidence 建立显式版本分支。旧 V0/V1 记录继续使用 `schema_version: "1.0"`，不会被自动迁移或静默重写。

V2 在 Chapter 9 仍是 contract-only 能力。`aiflow verify` 遇到 V2 时会在解析计划或启动检查前以 `VERIFY_V2_NOT_EXECUTABLE` 拒绝。独立 Verifier、V2 evidence writer、Gate V2 判定和 targeted mutation 执行属于 Chapters 10–11。

## 当前进度

| 任务 | 状态 | 证据 |
|---|---|---|
| 9.1 有序 V0/V1/V2 Policy | completed | 四份 Policy 统一为 `2.0.0`；loader 按 1.x/2.x 严格分支 |
| 9.2 V2 必需检查 | completed | 完整 V1 prefix + acceptance、integration、targeted_mutation、independent_verifier |
| 9.3 route-independent 分类 | completed | 封闭的 `verification_requirements`、稳定 rule IDs、V2 聚合与升降级比较 |
| 9.4 版本化 contracts | completed | classification/evidence `1.0` 与 `2.0` 分支、V2 正反 fixtures |
| 9.5 集成与文档 | completed | plan/parser/status/拒绝路径测试、README 与章节状态 |

## Policy 与选择规则

- Policy `1.x` 只接受恰好有序的 V0/V1；Policy `2.x` 只接受恰好有序的 V0/V1/V2；其他主版本、重复、缺失和乱序均拒绝。
- V1 必须逐项保留 V0 的完整 check 定义前缀；V2 必须逐项保留 V1 前缀，并按固定顺序追加四项 required checks。
- decision unit 的 `verification_requirements` 可省略；出现时必须包含四个布尔字段且不能有未知字段。任一字段为 true 即选择 V2，并记录对应稳定 rule ID。
- route 规则不读取 V2 facts。相同 verification facts 在 AUTO、ASK、REVIEW 或 BLOCK 标签下得到相同验证等级。
- 多 decision unit 取未完成单元的最高等级；已完成 V2 单元保留明细决定，但不抬高剩余任务等级。

## Contract 兼容性

| Contract | `1.0` | `2.0` |
|---|---|---|
| classification | effective 和单元明细仅 V0/V1 | effective 必须 V2，且至少一个单元明细为 V2 |
| evidence | 仅 V0/V1，禁止 V2 专属字段 | 仅 V2，要求 verifier actor/context、design/implementation review refs、四项 required checks 与 mutation manifest/results |

旧 fixtures 保持原内容和回放语义。V2 的 missing、invalid 与 extra-field fixtures 分别隔离验证缺失字段、版本/等级错误和 `additionalProperties: false`。

## 治理与验证证据

- active Policy 变更按冻结规格完成 `policy_changed` escalation → task-local resolution → classify → freeze → fresh design review → fresh spec approval。
- 两份额外字段负向 fixture 的窄范围修订另行完成 `spec_changed` 恢复、subject sync、独立复审和最终范围批准。
- 核心提交：`e17a34d`；fixture 隔离修复：`f21887e`；active Policy test helper 整合：`fa89a32`；版本明细约束：`fc33612`。
- 定向交叉矩阵：`160 passed, 1 skipped`。
- classification/contract 定向补强：`79 passed`。
- 累计回归：`639 passed, 3 skipped`；跳过项均为 Windows symlink 能力条件。

## 后续章节边界

Chapter 10 才能实现独立 Verifier 上下文、actor 隔离、V2 evidence 写入与 Gate 回放。Chapter 11 才能实现 targeted mutation 执行与预算。Chapter 9 不以 V1 fallback、伪造 passed evidence 或占位命令执行替代这些能力。
