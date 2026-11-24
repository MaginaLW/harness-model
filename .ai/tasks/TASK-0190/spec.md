# TASK-0190 · 扩展严格 mypy 门禁至 tools/ 并加固治理面清单

## 目标

在基线 `ae5dc1aaaf80875efff96ee7610a1ca4c939bdd4`（分支 `codex/governance-surface-and-tools-mypy-v2`）上完成项目所有者于 2026-11-24 直接批准的 B1 与 B2 治理加固：将 `tools/` 纳入严格 `mypy` 检查，并将 `setup.py`、`MANIFEST.in`、`tools/hooks/**` 纳入 `HARD-REVIEW-GOVERNANCE-SURFACE` 与 `AGENTS.md` 升级清单。

## 范围

仅允许修改以下路径：
- `.ai/tasks/TASK-0190/**`（本任务治理账本，不含临时日志目录 `logs/` 入库）
- `pyproject.toml`（`[tool.mypy]`：`files = ["src", "tools"]`，补充 `explicit_package_bases = true` 与 `namespace_packages = true`）
- `.ai/policy/verification-levels.yaml`（V1 与 V2 的 `mypy` 检查命令由 `["{python}", -m, mypy, src]` 改为 `["{python}", -m, mypy]`，保持 `policy_version: "2.6.0"` 不变）
- `.ai/policy/hard-rules.yaml`（`HARD-REVIEW-GOVERNANCE-SURFACE` 的 `conditions[0].value` 新增 `setup.py`、`MANIFEST.in`、`tools/hooks/**`，保持 `policy_version: "2.6.0"` 不变）
- `AGENTS.md`（「当前治理模式」升级清单句中补充 `setup.py`、`MANIFEST.in`、`tools/hooks/**`）
- `tests/unit/test_policy.py`（更新 V1/V2 `mypy` 命令断言并验证上述 3 项路径位于 `HARD-REVIEW-GOVERNANCE-SURFACE`）
- `tests/integration/test_github_workflow.py` 与 `tests/integration/test_templates_and_policy.py`（新增回归测试：维护模式下修改 `setup.py`、`MANIFEST.in` 或 `tools/hooks/pre_command.py` 时，`resolve_task.py --route` 必须要求创建实现任务）

已有能力复用与边界说明：
- 直接复用既有 `mypy`、`pytest`、`ruff`、`tools/ci/resolve_task.py` 与 `.ai/policy/*.yaml` 规则机制，不新增自定义检查脚本或配置开关，容错与路径校验仍仅位于 CLI/文件解析边界。

授权与自失效条件式预授权说明：
1. **所有者直接批准记录（2026-11-24）**：项目所有者已于 2026-11-24 直接批准本任务范围内的 B1（将 `tools/` 纳入严格 `mypy` 门禁）与 B2（将 `setup.py`、`MANIFEST.in`、`tools/hooks/**` 纳入 `HARD-REVIEW-GOVERNANCE-SURFACE` 与 `AGENTS.md` 升级清单）。
2. **Policy 自失效的条件式预授权（依 `docs/operations/low-intervention.md`）**：本任务修改 `.ai/policy/verification-levels.yaml` 与 `.ai/policy/hard-rules.yaml` 后会更新 `policy_sha256` 并触发 `policy_changed`。当且仅当以下三项条件同时满足时，授权按常设授权在新 Policy 下重新记录 `spec` 批准而不重复请求人类重签：
   - 冻结规格摘要 `spec_sha256` 保持不变；
   - 独立审核者在新 Policy 下给出 `APPROVE` 结论且无未关闭的 critical/high 发现；
   - `effective_route`（以及验证等级）未发生任何降低，且符合 `AGENTS.md`「常设授权」的全部条件。

## 非目标

- 不修改所有 4 个 `.ai/policy/*.yaml` 文件中的 `policy_version: "2.6.0"`。
- 不修改 `tests/integration/test_acceptance_traceability.py`（尤其是第 289 行历史回放文档断言）。
- 不修改 `src/aiflow/**`、`tools/**` 业务源码，不引入无关配置开关、备用分支、额外抽象层或顺手重构，不降低任何 CI 门禁或覆盖率阈值。

## 验收条件

1. `uv run --locked --extra dev python -m mypy` 通过，覆盖 `src` 与 `tools` 全部源文件（0 issues）。
2. 目标单元测试与集成测试、`ruff check`、`ruff format --check` 全部通过。
3. 正式运行 `uv run --locked --extra dev python -m aiflow verify TASK-0190 --actor author-track-b2`，V1 全部 10 项检查通过（含全量测试、总覆盖率 >= 85%、diff coverage >= 90%、mypy、ruff check/format）。
4. 经历 `policy_changed` 升级、解决、重分类、冻结与独立复审 `APPROVE` 后，重新记录 `spec` 与 `code` 批准，`aiflow gate TASK-0190` 通过；推送分支 `codex/governance-surface-and-tools-mypy-v2` 并开 PR 合入 `main`，CI `ai-quality-gate` 全绿通过。

## 禁止动作

- 禁止修改 `policy_version: "2.6.0"`、禁止改写历史任务/证据/日志、禁止把 `.ai/tasks/TASK-0190/logs/` 暂存或提交到 Git。
- 禁止自审（设计审核与实现审核均须由独立审核者 `@reviewer-track-b2` 完成）、禁止未通过 Gate/CI 或未经授权强推/改写历史/直接推送 `main`。
- 禁止执行 `deploy`、`delete`、`secret_export`、`paid_external_call`。

## 错误行为

- 若 `classify` 意外判为 `V2`（非预期 `V1`），或出现越界文件、Schema/Policy 校验失败、`mypy`/测试失败，必须立即停止推进并按规则升级或报告。
- 发生 `policy_changed` 自失效时，禁止直接手改状态或绕过 CLI；必须通过 `aiflow escalate` -> `resolve` -> `classify` -> `freeze` -> 独立复审的完整受治理路径恢复。

## 回滚

所有改动均位于独立分支 `codex/governance-surface-and-tools-mypy-v2` 上且为可逆的配置文件、文档与测试更新；在合入 `main` 前可直接丢弃分支或回退提交，合入后可通过反向 PR 回滚，无需恢复远端不可逆状态。
