# 基于 origin/main (0526983f) 交付 V2 变异归因实现与测试

## 目标

在最新 `origin/main` 基线提交 `0526983f2e3e9bea6080b55c71a0479fac5798b4`（已合并 PR #185 仅测试性能优化）上创建后继分支 `codex/mutation-attribution-0526983f` 与任务 `TASK-0175`，逐文件无修改移入已审核提交 `e92b288265454017f2c59c5b9833408291a5ed55` 中的 17 个模式、生产代码与测试文件，依所有者 A01 选项 1b 完成单轮 Windows V2 与私有 Ubuntu V2（7 份本地新鲜原件）正式验证、独立审核、批准、本地 Gate 与替换 PR 交付，并替代 `TASK-0167`、`TASK-0174`（保留 `FAILED` 历史记录）与 PR #180。

## 范围

唯一实现代码与测试范围为 `task.yaml` `allowed_scope` 所列 17 个明确文件（与 `e92b288265454017f2c59c5b9833408291a5ed55` 对应 Git blob 逐一完全一致），以及本任务治理账本 `.ai/tasks/TASK-0175/`：

1. `.ai/schemas/mutation-evidence.schema.json`
2. `src/aiflow/mutation_evidence.py`
3. `src/aiflow/mutation_materials.py`
4. `src/aiflow/mutation_process.py`
5. `src/aiflow/mutation_protocol.py`
6. `src/aiflow/mutation_reporter.py`
7. `src/aiflow/mutation_runner.py`
8. `src/aiflow/process_runner.py`
9. `src/aiflow/verification_service.py`
10. `tests/e2e/test_phase_02_negative_self_hosting.py`
11. `tests/e2e/test_phase_02_self_hosting_scenario.py`
12. `tests/integration/test_mutation_runner_contract.py`
13. `tests/integration/test_verify_command.py`
14. `tests/mutation_evidence_helpers.py`
15. `tests/unit/test_mutation_evidence.py`
16. `tests/unit/test_mutation_runner.py`
17. `tests/unit/test_process_runner.py`

行为与技术契约边界：不引入新外部依赖、未请求配置开关、冗余抽象层或顺手重构；复用语言标准库与既有 `aiflow` 路径，参数与容错校验仅置于不可信输入与外部 I/O 边界。五项检测契约沿用基线声明，`tests/integration/test_verify_command.py` 规范 LF SHA-256 为 `5991bead1b4d67a83890da1ec16a0b1bac7aff005a49978a09d28324760fa9ed`。共享 Windows 受控进程挂起创建、验证 Job 对象成员后恢复，检测进程 stdin 为空且每流上限 16 KiB，预检不合格则在持久消费单次行动批准前停止；1.0 与 2.0 证据格式由公共消费者显式区分。

正式验证预算边界（所有者 A01 选项 1b 批准单轮额度）：在本任务完成 `classify`、`freeze`、独立设计审核、`spec` 批准、`begin`、17 文件移入提交、`sync` 及单次 `targeted_mutation_v2` 行动批准后，执行 **1 轮 Windows V2**（全量 14 项检查含 5 项 `phase-02-critical` 原生变异串行执行，预检 10 秒、每对基线/变异 60 秒与每流 16 KiB），且仅在 Windows V2 全部通过并生成 7 份本地未跟踪原件后，执行 **1 轮私有 Ubuntu V2**（WSL2 `HarnessModelValidation` 离线回放 `aiflow verify --ci` 与 `aiflow gate`，使用同一 7 份本地新鲜原件、不触发新原生变异）；两平台均禁止自动重试。

## 非目标

本任务不修改 `d:\Repos\harness-model` 主工作区、`C:\Users\Admin\.codex\worktrees\task-0163-delivery\harness-model`（`TASK-0167` 保留为历史记录）以及 `C:\Users\Admin\.codex\worktrees\task-0174-delivery\harness-model`（`TASK-0174` 保留为 `FAILED` 历史记录及其日志与 7 份私有原件）；不触及已由所有者明确延后的 R1 `B1–B6` 事项（包括 `TASK-0169`/`TASK-0171`/`TASK-0173` 的 `forbidden_actions`、GitHub 受保护 Environment、独立 GitHub App、分支保护或端到端 CI 串接）；不触及 R4 明确暂停或中长期项（`agent-bridge` Stage B、`TASK-0094`/`TASK-0095`、Phase 3/4 等）；不将私有原件提交或上传至公开 Git、GitHub PR 或公开 runner，也不削弱任何 CI 质量门禁或强制合并。

## 验收条件

1. 工作区与基线检查：在干净独立 worktree 的分支 `codex/mutation-attribution-0526983f` 上完成任务创建（`base_commit = 0526983f2e3e9bea6080b55c71a0479fac5798b4`），`aiflow classify` 确定为 `REVIEW / V2`，冻结本规格并通过独立设计审核（`REV-0001` `APPROVE`）、`spec` 批准与 `begin`。
2. 代码移入与行动批准：17 个目标文件与 `e92b288265454017f2c59c5b9833408291a5ed55` 字节一致且无范围外代码更改，5 项 `REVIEWED_INPUT_SHA256` 全部匹配；提交后执行 `aiflow sync`，并依当前 `subject_commit` 与 `classification_input_sha256` 批准单次 `targeted_mutation_v2` 行动文件。
3. 单轮 Windows V2 验证：独立验证者执行一次 `aiflow verify TASK-0175` 退出码为 0，14 项检查全部通过（全量 pytest 在未改变的 `3000s` 时限内完成、核心分支覆盖率 >= 85%、变更行覆盖率 >= 90%、whitespace、Ruff check/format、mypy、5/5 原生变异 `killed`），本地 `.ai/tasks/TASK-0175/logs/` 生成 7 份新鲜未跟踪原件。
4. 独立实现审核、定稿与本地 Gate：独立实现审核记录 `REV-0002` `APPROVE` 且完成 `review-package.md`（含五项交付边界自检），`aiflow verify --finalize` 与 `approve --type code` 后 `aiflow gate TASK-0175 --format json` 返回 `passed: true`、`reason_codes: []`，`aiflow validate` 与 `aiflow scope` 全部通过。
5. 单轮私有 Ubuntu V2 回放：在 WSL2 `HarnessModelValidation` 离线复现提交与 7 份本地新鲜原件后，执行 `aiflow verify TASK-0175 --ci` 与 `aiflow gate`，确认 `conclusion == "passed"`、`passed == true` 且未新增原生变异。
6. 交付与如实记录：推送单分支 `refs/heads/codex/mutation-attribution-0526983f` 并开启替换 PR（引用 `TASK-0175`、Windows V2 与私有 Ubuntu V2 结果，明确替代 `TASK-0167`、`TASK-0174` 与 PR #180），关闭 PR #180 并注明新 PR 与 `TASK-0175`；若公开 GitHub Actions `ai-quality-gate` 因 R1 `B1–B6` 延后而缺少私有原件继续阻断合并，如实记录实际状态而不绕过门禁或强行合并。

## 禁止动作

禁止修改 `d:\Repos\harness-model`、`TASK-0167` 或 `TASK-0174` 历史工作区与产物；禁止执行未获批准的 `deploy`、`delete`、`secret_export`、`paid_external_call` 或跨仓写入；禁止在 Windows V2 或私有 Ubuntu V2 失败/中断时自动重试、消耗额外验证额度或改用合成输出替代原生实测；禁止将 `.ai/tasks/TASK-0175/logs/` 下的 7 份私有原件加入 Git 暂存区、提交、推送或上传至 PR；禁止强推、改写已推送历史、删除 `archive/*`/`pilot/*`、关闭 PR #150 或削弱分支保护与 CI 门禁。

## 错误行为

若工作区脏状态、基线提交 `0526983f`、17 文件字节一致校验、`REVIEWED_INPUT_SHA256`、`subject_commit` 或 `classification_input_sha256` 任一项不匹配，立即中止对应步骤并以 `aiflow` 合同错误或状态阻断记录；若单轮 Windows V2 或私有 Ubuntu V2 任一检查、原生变异、覆盖率或 Gate 失败或发生进程中断，立即停止并不重试，保存实测诊断并按 `aiflow escalate` 上报阻塞状态；不得忽略审核发现、降低严重度或在公开 `ai-quality-gate` 未通过时合并 PR。

## 回滚

`TASK-0175` 位于独立新分支 `codex/mutation-attribution-0526983f` 与独立 worktree，未改动 `main`、`TASK-0167` 与 `TASK-0174` 历史记录。若需放弃本候选，保留既有 `TASK-0175` 账本以维持可审计性或通过独立新提交/关闭替换 PR 撤回交付分支影响，绝不强推、重写已推送提交或删除已归档历史证据。
