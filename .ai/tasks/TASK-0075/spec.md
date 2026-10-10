# Task Specification

## 目标

任何决策单元的 `impact_scope` 与治理面路径重叠时，路由至少为 REVIEW，不再取决于实现者自报的影响等级；治理面路径清单写在 `.ai/policy/hard-rules.yaml` 中，由项目所有者控制。

## 范围

- `src/aiflow/predicates.py`：新增运算符 `overlaps_paths`：字段为路径模式列表，值为治理面路径模式列表；两侧先用 `normalize_repository_path` 规范化（拒绝绝对路径、`.`、`..`、空段等，按 `PREDICATE_TYPE_INVALID` 处理）并统一 casefold，再各取首个通配段（含 `*`、`?` 或 `[` 的段）之前的字面前缀，按路径段比较，任一侧前缀是另一侧前缀（含相等、`**` 的空前缀）即视为重叠。判断保守：宁可多判重叠。
- `.ai/schemas/policy.schema.json`：运算符枚举加入 `overlaps_paths`，并用 if/then 要求其 `value` 为非空字符串数组，使 Policy 加载时即拒绝非法值。
- `.ai/policy/hard-rules.yaml`：新增 `HARD-REVIEW-GOVERNANCE-SURFACE`（REVIEW，priority 750，`match: all`，条件 `impact_scope overlaps_paths [".github/**", ".ai/**", "src/aiflow/**", "tools/ci/**", "AGENTS.md", "CLAUDE.md", "pyproject.toml", "uv.lock", ".gitignore", ".gitattributes"]`，`missing: match`，即缺少 `impact_scope` 时按重叠处理）；四个 Policy 文件版本升至 `2.5.0`。
- `tests/**`：运算符单元测试（重叠、不重叠、宽泛通配、`[`/`?` 通配、大小写、非法输入、Policy 加载拒绝非法值）；路由测试（自报低影响但范围含 `src/aiflow/**` 的单元得到 REVIEW，纯 `docs/**`、`tests/**` 单元仍可 AUTO）；为合成路由单元补 `impact_scope`；更新固定 Policy 版本或规则数量的断言。
- `examples/scenarios/**`：ask-conflict-strategy 的 `impact_scope` 改为非治理路径（`src/app/conflicts.py`）以保持 ASK；review-workflow-change 的期望增加新规则 ID 与说明。
- `README.md`、`docs/operations/quickstart.md`、`docs/operations/recovery.md`：当前 Policy 版本号与一句规则说明。
- `.ai/tasks/<本任务>/**`。

## 非目标

- 不改变其他路由规则、验证等级、批准、证据或 Gate 语义；不改历史任务及其绑定的旧 Policy。
- 不检查 `allowed_scope`（AUTO 改动已受 AUTO 单元 `impact_scope` 约束）。
- 不执行 push、merge、deploy、delete 或任何外部动作。

## 验收条件

- `impact.level: low`、其他 AUTO 条件均满足但 `impact_scope` 含 `src/aiflow/storage.py` 的单元分类为 REVIEW，命中 `HARD-REVIEW-GOVERNANCE-SURFACE`；同样事实而 `impact_scope` 只有 `docs/**` 的单元仍为 AUTO。
- `impact_scope` 为 `["**"]` 或 `["src/**"]` 时判为重叠；`["tests/**"]`、`["docs/operations/x.md"]` 不重叠。
- golden 场景：AUTO、BLOCK 场景结果不变；ask-conflict-strategy 改用非治理路径后仍为 ASK；review-workflow-change 仍为 REVIEW，规则 ID 增加 `HARD-REVIEW-GOVERNANCE-SURFACE`。
- 完整质量检查通过：全量 pytest 带 `--cov-fail-under=85`、diff coverage ≥90%、ruff、mypy、`git diff --check`；AI Flow `verify` 与 `gate` 按 CLI 结论通过。

## 禁止动作

push、merge、deploy、delete、secret_export、paid_external_call；不修改其他任务目录。

## 错误行为

- `impact_scope` 缺失时按重叠处理（至少 REVIEW）；含非法路径时按类型错误阻断分类，而不是放行。
- 运算符值不是字符串列表时 Policy 加载失败。

## 回滚

`git revert` 本任务实现提交即可恢复 Policy 2.4.0 与原运算符集合。
