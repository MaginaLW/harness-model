# Task Specification

## 目标

在 `.ai/policy/routing.yaml` 中新增**一条** AUTO 规则，使「范围清晰、可自动验证、可逆、
无外部副作用、且未命中任何 `HARD-*` 规则」的 **medium 影响**决策单元判为 AUTO；八条
`HARD-*` 规则与 `ROUTE-ASK-MULTIPLE-DIRECTIONS` 的优先级全部保持在其之上，
`ROUTE-DEFAULT-REVIEW` 保留为兜底。

## 依据

对账本 38 个 task 的实测：17 个 `ROUTE-DEFAULT-REVIEW` 决策单元（均为单 DU）**全部且仅**
因 `impact.level: medium` 未匹配 `ROUTE-AUTO-EXPLICIT-GUARDS`；`scope.clear`、
`reversibility`、`verification.automatic`、`external_side_effects` 四项守卫在这 17 个单元中
本来就全部满足。因此本任务只放宽 `impact.level` 一个维度，不触碰其余守卫。

## 范围

- `.ai/policy/routing.yaml`：新增规则、提升 `policy_version`。
- `tests/unit/test_routing.py`、`tests/integration/test_classify_command.py`：正向与负向用例。
- 执行目录：记录本章结论。

拟新增规则（priority 取 50，位于 `ROUTE-AUTO-EXPLICIT-GUARDS` 的 100 之下、兜底的 0 之上）：

```yaml
- id: ROUTE-AUTO-VERIFIED-MEDIUM
  priority: 50
  route: AUTO
  explanation: Verifiable, reversible, side-effect-free medium-impact work with a clear scope stays AUTO.
  match: all
  conditions:
    - field: scope.clear
      operator: equals
      value: true
      missing: error
    - field: impact.level
      operator: in
      value: [low, medium]
      missing: error
    - field: reversibility
      operator: in
      value: [reversible, conditionally_reversible]
      missing: error
    - field: verification.automatic
      operator: equals
      value: true
      missing: error
    - field: verification.tools_missing
      operator: equals
      value: false
      missing: error
    - field: external_side_effects
      operator: is_empty
      value: true
      missing: error
```

## 非目标

1. **不修改 `.ai/policy/hard-rules.yaml` 的任何一条。** 八条 `HARD-*`
   （`HARD-BLOCK-EXTERNAL-SENSITIVE`、`HARD-BLOCK-IRREVERSIBLE-NO-BACKUP`、
   `HARD-BLOCK-VERIFICATION-TOOL-MISSING`、`HARD-REVIEW-PRODUCTION-DATA-DELETE`、
   `HARD-REVIEW-SECRETS-AUTH`、`HARD-REVIEW-CI-CD`、`HARD-REVIEW-DEPLOYMENT`、
   `HARD-REVIEW-REAL-EXTERNAL-ACTION`）的 id、priority、条件与命中结果均不变。
2. **不把路由与验证等级耦合。** `route_task` 与 `verification_for_task` 目前各自只读
   `decision_units`，后者显式声明 "without route input"。本任务不引入让路由条件读取已算出
   的验证等级的机制；「验证充分」只通过决策单元自身的事实表达。
3. 不删除、不降低 `ROUTE-DEFAULT-REVIEW`，不改 `ROUTE-ASK-MULTIPLE-DIRECTIONS`。
4. 不改动 CI 质量门禁的任何检查项与阈值，不改 `main` 分支保护。
5. 不改动 `permissions.yaml`；push、merge、deploy、delete、secret_export、
   paid_external_call 六项仍需单独人类批准。
6. 不改动 `impact_categories` 的枚举（本任务过程中发现其无 policy/governance 取值，
   属另行处理的缺口，不在本范围内）。

## 验收条件

| 检查 | 预期 |
|---|---|
| `python -m pytest tests/unit/test_routing.py -q` | 通过 |
| `python -m pytest tests/integration -q` | 通过 |
| `python -m pytest tests/acceptance -q` | 通过 |
| `python -m pytest -q` | 通过 |
| `python -m mypy src` | 通过 |
| `python -m ruff check .` / `--format --check` | 通过 |
| 八条 `HARD-*` 的命中结果重放 | 与改造前逐条一致 |
| 38 个历史 classification input 重放 | 给出新旧路由分布对比，且由 REVIEW 转 AUTO 的每一项均可逐条说明其不属于硬风险 |
| 负向用例 | 缺字段、外部副作用非空、不可逆、`tools_missing: true`、`impact.level: high` 五类均**不得**判为 AUTO |

## 禁止动作

push、merge、deploy、delete、secret_export、paid_external_call，以及任何外部系统调用。
本任务只在本地修改文件并运行验证。

## 错误行为

- 任一条件字段缺失时按 `missing: error` 处理，不得默认成立，必须回落到兜底 REVIEW。
- `impact.level: high` 不匹配本规则。
- `external_side_effects` 非空、`reversibility: irreversible`、
  `verification.tools_missing: true`、`scope.clear: false` 任一成立即不匹配。
- 命中任何 `HARD-*` 或 ASK 规则时，其更高优先级结论优先，本规则不得覆盖。

## 回滚

改动仅限受版本控制的文本文件。回滚方式：还原 `.ai/policy/routing.yaml`（含
`policy_version`）与两个测试文件，重新运行 `python -m aiflow classify` 即可恢复原分类结论。
历史 evidence 与 approval 均绑定各自的 `policy_sha256`，不因本任务被重新解释。
