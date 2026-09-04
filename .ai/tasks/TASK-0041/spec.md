# Task Specification

## 目标

让**治理面变更无法在不经人类审核的情况下被路由走**：新增一个按路径匹配的谓词运算符，
并据此新增 `HARD-REVIEW-GOVERNANCE-SURFACE` 规则，锚定决策单元的 `impact_scope`，覆盖
`.ai/policy/**`、`.ai/schemas/**`、`src/aiflow/**`、`.github/workflows/**`。

## 依据

TASK-0040 的独立设计审核（REV-0001，8 条 open 发现）确认：现有 `HARD-*` 兜底并不可靠。
`HARD-REVIEW-SECRETS-AUTH` 与 `HARD-REVIEW-CI-CD` 的条件均为 `missing: no_match`，
而 `impact_categories` 在 `decision-unit.schema.json` 中**不是必填**，因此这两条规则在字段
缺失时静默失效。本任务是放宽 AUTO（原 Chapter B1）的**前置条件**，不是它的替代。

选择锚定 `impact_scope` 而非 `impact_categories` 的理由：`impact_scope` 是 decision-unit
schema 的**必填**字段，账本中 41 个 task 无一缺失；且 `aiflow scope` 会用真实 git diff 对
`allowed_scope` 做交叉校验，因此路径是**被强制**的，而类别只是自声明。

## 已核实的引擎事实（B1 在这几点上写错过，此处以代码为准）

1. **有效路由按严重度取最大，与 priority 无关。** `src/aiflow/routing.py:245`
   `effective = max((hit.route for hit in hits), key=ROUTE_ORDER.index)`，
   `ROUTE_ORDER = ("AUTO","ASK","REVIEW","BLOCK")`。priority 只决定写入证据的 `rule_id`
   （并受 `routing.py:168` 同优先级冲突检查约束）。因此**新增一条 REVIEW 规则只会提升严重度，
   不可能削弱任何既有结论**。
2. **`missing: error` 产生 BLOCK，不回落 REVIEW。** `src/aiflow/predicates.py:89`
   明确 "A missing ``error`` field is intentionally an error rather than a false"。
   本规则因此使用 `missing: match`（fail-closed：字段缺失即视为命中 → REVIEW）。
3. **`policy_version` 必须四文件同步。** `src/aiflow/policy.py:150` `_validate_cross_file`
   要求 `versions` 集合长度为 1，否则 `POLICY_VERSION_MISMATCH`。四个
   `.ai/policy/*.yaml` 因此全部在范围内，且只改 `policy_version` 行（`hard-rules.yaml` 另加规则）。
4. **`_AUTO_GUARDS` 是引擎级 AUTO 守卫下限**（`routing.py:15`，`routing.py:164` 要求超集）。
   本任务只新增 REVIEW 规则，**不触碰它**。

## 范围

- `src/aiflow/predicates.py`：新增 `path_matches_any` 运算符。语义为
  「实际值是字符串列表；对其中**任一**元素，若与期望列表中**任一** glob 模式匹配则命中」，
  使用 `fnmatch.fnmatchcase`，路径分隔符先归一为 `/`。非列表实际值按现有
  `_require_sequence` 抛 `PREDICATE_TYPE_INVALID`。
- `.ai/schemas/policy.schema.json`：`operator` 枚举补 `path_matches_any`。
- `.ai/policy/hard-rules.yaml`：新增规则（priority 取 810，位于
  `HARD-REVIEW-PRODUCTION-DATA-DELETE` 的 800 之上、`HARD-BLOCK-*` 的 980 之下）：

```yaml
- id: HARD-REVIEW-GOVERNANCE-SURFACE
  priority: 810
  route: REVIEW
  explanation: Changes to the governance engine, policy, schemas or CI definition require review.
  match: all
  conditions:
    - field: impact_scope
      operator: path_matches_any
      value:
        - ".ai/policy/**"
        - ".ai/schemas/**"
        - "src/aiflow/**"
        - ".github/workflows/**"
      missing: match
```

- `.ai/schemas/decision-unit.schema.json`：`impact_categories` 枚举补 `governance`
  （仅供审计标注，本规则不依赖它）。
- 四个 `.ai/policy/*.yaml`：`policy_version` 同步提升到 `2.3.0`。
- `tests/unit/test_predicates.py`、`tests/unit/test_routing.py`、
  `tests/integration/test_classify_command.py`：新增用例。
- 执行目录：记录本任务与 B1 的依赖关系。

## 非目标

1. **不修改 `_AUTO_GUARDS`，不新增或放宽任何 AUTO 规则。** 原 Chapter B1 的放宽在本任务
   完成并验证前不得推进。
2. 不修改既有八条 `HARD-*` 规则的 id、priority、条件或命中结果。
3. 不把 `impact_categories` 改为必填 —— 那会使 41 个历史 task 记录不再通过 schema 校验。
4. 不改动 `permissions.yaml` 的 `forbidden_automatic_actions` 六项（仅动其 `policy_version` 行）。
5. 不改动 CI 质量门禁的检查项与阈值，不改 `main` 分支保护。
6. 不引入除 `path_matches_any` 外的任何新运算符，不改动既有运算符语义。

## 验收条件

| 检查 | 预期 |
|---|---|
| `python -m pytest tests/unit/test_predicates.py tests/unit/test_routing.py -q` | 通过 |
| `python -m pytest tests/integration -q` / `tests/acceptance -q` / `python -m pytest -q` | 通过 |
| `python -m mypy src`；`ruff check` / `format --check` | 通过 |
| 新规则正向 | `impact_scope` 含 `.ai/policy/routing.yaml`、`.ai/schemas/x.json`、`src/aiflow/y.py`、`.github/workflows/z.yml` 四类各自触发 REVIEW |
| 新规则负向 | `impact_scope` 仅含 `docs/**` 或 `tests/**` 时**不**触发 |
| fail-closed | `impact_scope` 缺失时按 `missing: match` 命中 REVIEW |
| 既有规则不变 | 八条 `HARD-*` 在 41 个历史 task 上的命中结果逐条不变 |
| 无削弱 | 41 个历史 task 重放后，无一 task 的 route 严重度低于改造前 |
| 自指检查 | 本 task（TASK-0041）自身的 `impact_scope` 触发新规则，即它自己被该规则捕获 |

## 禁止动作

push、merge、deploy、delete、secret_export、paid_external_call，以及任何外部系统调用。

## 错误行为

- `path_matches_any` 的实际值非字符串列表时抛 `PREDICATE_TYPE_INVALID`，不得静默不匹配。
- 期望值非列表时同样抛错。
- 四个 Policy 文件 `policy_version` 不一致时必须 `POLICY_VERSION_MISMATCH` 失败，不得部分加载。
- 新运算符未同步进 `policy.schema.json` 时，Policy 校验必须失败而非跳过。

## 回滚

改动仅限受版本控制的文本文件。回滚 = 还原 `predicates.py`、两个 schema、四个 Policy 文件
与测试，重新运行 `python -m aiflow classify`。历史 evidence 与 approval 绑定各自的
`policy_sha256`，不因本任务被重新解释；`2.3.0` 为 minor 提升，不触发 major 不兼容路径。
