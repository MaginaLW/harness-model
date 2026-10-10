# Review Package

## 审核目标

裁决 TASK-0075 实现提交 `23c5721427676d1f8756c66c04f8851133ea147a` 与测试补充提交 `4df0d739eed942d376137fe092eee0124370f42f` 是否满足冻结规格 `009dd87e05053a76828736452ce03d79aa7e5348be7e47d39e779df3a6132826`：`impact_scope` 触及治理面的决策单元至少路由为 REVIEW。

## 背景

TASK-0073 曾因自报低影响被分到 AUTO；常设授权允许 Agent 在独立审核后代记批准，因此审核下限必须由 Policy 强制。设计审核 REV-0001（REQUEST_CHANGES）→ REV-0002（APPROVE）→ Policy 2.5.0 重新分类后 REV-0003（APPROVE）。

## 代码地图

- `src/aiflow/predicates.py`：新增 `overlaps_paths`（`normalize_repository_path` + casefold，首个含 `*`/`?`/`[` 段前的字面前缀按段互为前缀即重叠；空列表视为重叠）。
- `.ai/schemas/policy.schema.json`：运算符枚举与 if/then 值约束（非空字符串数组）。
- `.ai/policy/hard-rules.yaml`：`HARD-REVIEW-GOVERNANCE-SURFACE`（REVIEW，750，十个治理面模式，`missing: match`）；四个文件升至 2.5.0。
- 测试：`tests/unit/test_routing.py`、`tests/unit/test_policy.py`、`tests/fixtures/routing/decision-table.json`、`tests/e2e/test_ask_scenario.py`。
- 场景：ask-conflict-strategy 改用 `src/app/conflicts.py`；review-workflow-change 期望增加新规则。
- 文档：README、quickstart、recovery 的 Policy 版本与规则说明。

## 语义变更

- 治理面范围的单元不再可能为 AUTO；缺失或空 `impact_scope` 也按治理面处理；非法路径阻断路由。
- 其他规则与验证等级不变。

## 风险

- 判断保守：`**`、`src/**`、`*.md` 等宽泛模式会落到 REVIEW，增加审核但不会放行。
- Policy 治理面清单比 AGENTS.md 升级清单更宽（REV-0003 RF-007），以及 maintenance-status 版本号（RF-008），留作后续文档对齐。

## 证据

- 已验证：最终 AI Flow V1 evidence `.ai/tasks/TASK-0075/evidence.json`，subject `4df0d739eed942d376137fe092eee0124370f42f`，run `run-20261010T003112374801Z`，全部检查 passed；共享 pytest 执行 `2311 passed, 1 skipped in 732.28s`。
- 已验证：实现审核 REV-0004 的 RF-002 已补 `?` 通配与反斜杠测试（对应变异体现在被杀死）；RF-001（治理面清单补 `tools/hooks/**`、`.claude/**`、`.codex/**`）与 RF-003 留作后续 Policy 任务。
- 已验证：总覆盖率 89%（`coverage report --fail-under=85` 通过），diff coverage 100%。
- 已验证：路由探针（`src/aiflow/storage.py`、`**`、`src/**`、`[s]rc/**`、大小写变体为 REVIEW；`docs/**`、`tests/**` 为 AUTO）；Policy 加载拒绝空、非列表与非字符串值；golden 场景按规格更新。
- 已验证：mypy、ruff、`git diff --check` 通过。
- 未验证：Linux CI（随 PR 执行）。

## 审核问题

1. `overlaps_paths` 是否对所有合法模式保守（不会把可能命中治理面的模式判为不重叠）？
2. 非法输入是否一律阻断而非放行？
3. golden 与既有测试的修改是否只反映新规则，没有掩盖回归？
4. 文档描述是否准确？

## 推荐结论

APPROVE：实现符合规格与三轮设计审核结论，完整验证通过。
