# Review Package

## 审核目标

对 `TASK-0175`（分支 `codex/mutation-attribution-0526983f`，`base_commit=0526983f2e3e9bea6080b55c71a0479fac5798b4`，`subject_commit=f444677e5952a9f8c068dcebb27450de888a7f8a`，预审核提交 `HEAD=348122f41d77c03cca31640e6d879e0a09e59ed8`）执行独立实现审核，裁决：

1. 移入的 17 个 V2 变异归因实现与测试文件是否与已审核提交 `e92b288265454017f2c59c5b9833408291a5ed55` 逐字节一致、无范围外代码修改，且逻辑完整真实（无硬编码或空壳实现）；
2. 单轮 Windows V2 正式验证证据（14 项检查、覆盖率、5/5 原生变异 `killed` 及 7 份本地未跟踪私有原件）是否真实、完整、可复现并满足 `spec.md` 与 `V2` 门禁要求；
3. 是否批准进入 `aiflow verify --finalize`、`approve --type code`、本地 `aiflow gate` 及后续私有 Ubuntu V2 回放。

## 背景

`TASK-0175` 为所有者 A01 选项 1b 批准的后继任务：在合并 PR #185（仅测试性能优化，提交 `0526983f2e3e9bea6080b55c71a0479fac5798b4`）后的最新 `origin/main` 基线上，替代 `TASK-0167`、`TASK-0174`（保留 `FAILED` 历史记录）与 PR #180 交付 V2 变异归因。前置步骤已完成 `classify`（`REVIEW / V2`）、`freeze`（`spec_sha256=c14d94092efbfc390a085fe6bb8eb0a16c95119b360953e331d8fb95e7c33e9f`）、`REV-0001` 独立设计审核（`APPROVE`）、`spec` 批准、`begin`、17 文件移入提交 `f444677e`、`sync`、单次 `targeted_mutation_v2` 行动批准（`action_sha256=f6d08ab8fb882747bd6d907c3ba779b28842985440117bc667e6f2b6072b2e08`），以及独立验证者 `r2b-independent-verifier` 执行的单轮正式 Windows V2 验证。

## 代码地图

17 个受控交付文件（位于 `task.yaml` `allowed_scope` 内，与 `e92b2882` 对应 blob 完全一致）：

- 模式定义：`.ai/schemas/mutation-evidence.schema.json`（新增 `2.0` 契约、`subject_materials_sha256`、`execution_log_v2`、受限 `report` 与 `lifecycle`）。
- 核心实现（8 个模块）：
  - `src/aiflow/mutation_protocol.py`：封闭 16 KiB 报告线协议、`REVIEWED_INPUT_SHA256`（5 项检测输入摘要）及 fail-closed `classify_report`。
  - `src/aiflow/mutation_process.py`：基于 Windows Job 的 `ProcessLifecycle` 观测与 `preflight_mutation_runtime` / `run_bounded_process`。
  - `src/aiflow/mutation_materials.py`：从 `subject_commit` Git blob 读取受控材料闭包并校验工作区文件及已加载 `aiflow.*` 模块字节/函数/类/上下文管理器一致性。
  - `src/aiflow/mutation_reporter.py`：`-I -B` 受控 pytest 子进程报告器，校验测试输入/目标摘要/traceback 位置/异常类型与语义签名。
  - `src/aiflow/mutation_runner.py`：单次授权令牌消费与发射声明、主工作树快照、无 filter 检查、串行一次性 detached worktree 执行、AST 精确变异与清理验证。
  - `src/aiflow/mutation_evidence.py`：跨进程锁下原子消费单次行动批准、生成与严格回放 `2.0` 不可变证据与日志，并与 `1.0` 历史只读消费者 `read_historical_mutation_evidence` 严格隔离。
  - `src/aiflow/process_runner.py`：`run_node_process` 增加受验 `max_output_bytes` 参数以按流 16 KiB 检测首个溢出字节。
  - `src/aiflow/verification_service.py`：将原生变异工具版本常量更新为 `aiflow-mutation-evidence-v2`。
- 测试与辅助（8 个文件）：
  - `tests/mutation_evidence_helpers.py`
  - `tests/unit/test_mutation_evidence.py`、`tests/unit/test_mutation_runner.py`、`tests/unit/test_process_runner.py`
  - `tests/integration/test_mutation_runner_contract.py`、`tests/integration/test_verify_command.py`
  - `tests/e2e/test_phase_02_negative_self_hosting.py`、`tests/e2e/test_phase_02_self_hosting_scenario.py`
- 治理账本：`.ai/tasks/TASK-0175/*`（含 `REV-0001`、`REV-0002`、`evidence.json`、`action-use-*.md`、`review-contexts/*`、`verifier-contexts/*`，零 `logs/` 跟踪文件）。

## 语义变更

- **证据模型 1.0 / 2.0 显式分离**：`load_targeted_mutation_evidence` 与 `consume_targeted_mutation_evidence` 仅接受包含 `subject_materials_sha256`、`baseline_report`/`mutant_report`、`baseline_lifecycle`/`mutant_lifecycle` 与完整动作消费链的 `2.0` 证据并 fail-closed 重验；旧 `1.0` 仅由 `read_historical_mutation_evidence` 只读解析且永不满足当前 Gate。
- **行动批准单次消费与防旁路**：运行前先在跨进程锁外/内完成预检，预检失败则在写入 `action-use-<sha256>.md` 与追加 `consumed` 事件前中止；发射前通过独占 `action-launch-<sha256>.json` 声明及设备/inode 核验，防止重放或重复启动。
- **进程与材料边界**：`mutation_process.py` 与 `process_runner.py` 将输入校验与边界防护置于外部进程与 I/O 边界；`mutation_materials.py` 与 `mutation_reporter.py` 仅校验 Git blob、检出文件及已加载模块一致性；新增各模块职责单一、共用校验与路径检查不引入分支标志位或多余抽象层，满足“同业务规则、同向演进、合并不增标志位”三条件。

## 风险

- **长耗时全量测试回归风险**：17 个文件引入大量原生与契约测试，在未优化基线上曾触发 `3000s` 超时；已在 `0526983f` 基线通过纯测试优化缓解，本次 Windows V2 实测 `unit_tests` 耗时 `1734110 ms`（约 28.9 分钟），低于 `3000s` 上限。
- **私有原件泄露与污染风险**：`.ai/tasks/TASK-0175/logs/` 含 7 份本地私有原件与运行日志；已核验 `.gitignore` 规则及 `git ls-tree -r --name-only HEAD .ai/tasks/TASK-0175/` 与 `git status --short` 均无 `logs/` 跟踪或未忽略泄露。
- **公开 CI 阻断风险**：因 R1 `B1–B6` 已由所有者明确延后，公开 GitHub Actions `ai-quality-gate` 在缺少私有原件时仍可能阻断公开 PR 合并；按 `spec.md` 规定仅如实记录状态、不削弱门禁或强行合并。

## 证据

- **已验证**（`r2b-independent-verifier` 单轮正式 Windows V2，执行命令 `python -m aiflow verify TASK-0175 --actor r2b-independent-verifier`；独立审核核验提交 `348122f41d77c03cca31640e6d879e0a09e59ed8`）：
  - Git 范围与字节一致性：`git status --short` 为空；`git diff f444677e e92b2882 -- <17 files>` 为空；`5/5` `REVIEWED_INPUT_SHA256` LF SHA-256 匹配；`review context --stage implementation` 字节级复现 `689bb9908f4ac13960b10ee0068005947ffb8d3b12ea1f21cc7b07aa6432b154`。
  - `.ai/tasks/TASK-0175/evidence.json`（`verification_snapshot_sha256=3ba7032f48cf15186cd6cc22d83ff14b80850d8f6313670d1feae781f34d2fed`）：`14/14` 必需检查全部 `passed`（`contract`、`scope`、`ruff_check`、`ruff_format_check`、`smoke`、`unit_tests` `1734110 ms` / `4982 passed, 9 skipped`、`regression_tests`、`mypy`、`coverage_xml` 核心合并覆盖率 `90.06%`、`diff_coverage` `92%`、`acceptance`、`integration`、`targeted_mutation` `5/5 killed`、`independent_verifier`）。
  - 7 份未跟踪本地私有原件（`action-launch-*.json`、`targeted-mutation/evidence.json` 与 `MUT-V2-001..005.json`）均存在且字节数与 SHA-256 摘要核对一致（`mutation_evidence_sha256=75bbb31a7b0395cc7d4e55dbda3343364bd91ad1e5ad82fa4d4afb13d7ccb82b`）。
  - 独立实现审核记录：`REV-0002`（`reviews/REV-0002-r0001.json`，`r2b-independent-implementation-reviewer`）已记录。
- **未验证**：
  - `aiflow verify --finalize`、`approve --type code` 与本地 `aiflow gate TASK-0175` 尚待本审核完成后执行；
  - 私有 Ubuntu V2（WSL2 `HarnessModelValidation` 离线回放同一 7 份本地新鲜原件并执行 `aiflow verify TASK-0175 --ci` 与 `aiflow gate`）尚未执行；
  - 远端分支推送、替换 PR 创建与 PR #180 关闭尚未执行。

## 审核问题

- 17 个移入文件是否与 `e92b2882` 逐字节一致且无任何范围外或历史保护区（`d:\Repos\harness-model`、`TASK-0167`、`TASK-0174`、`TASK-0169/0170/0171/0173`、PR #150、`archive/*`、`pilot/*`）改动？已核验一致且未触及。
- Windows V2 `14/14` 检查、`90.06%` 核心覆盖率、`92%` diff coverage 与 `5/5` 原生变异 `killed` 是否存在硬编码、空壳实现或私有原件泄漏？经逐文件审查及摘要核验，无任何作弊或泄漏。
- 单次 `targeted_mutation_v2` 行动消费记录与 7 份本地私有原件是否满足后续 `verify --finalize` 与私有 Ubuntu V2 离线回放前置条件？已核验满足。

交付边界五项自检结论：

1. 目标与关键假设是否清楚：清楚，基于 `0526983f` 交付 17 个已审核 V2 变异归因文件并按 A01 选项 1b 完成单轮 Windows V2 与后继私有 Ubuntu V2 验证，不触及延后的 R1 `B1–B6` 与 R4 暂停项。
2. 是否已核实语言标准库与代码库既有复用机会：已核实，充分复用 `ast`、`hashlib`、`subprocess`、`tempfile`、`msvcrt`/`fcntl` 及既有 `aiflow.approval`、`aiflow.contracts`、`aiflow.git_context`、`aiflow.process_runner` 等模块。
3. 各修改模块是否存在更简单的直接实现：无更简单且可维持相同 fail-closed 安全性与契约隔离的替代方案。
4. 新增抽象、分支或配置项是否均有当前明确依据：所有新增模块、Schema 字段与 `max_output_bytes` 参数均直接对应 `spec.md` 与 `V2` 归因/单次消费契约，无多余开关或投机抽象。
5. 是否只触及了任务范围边界内的文件：是，仅修改 `allowed_scope` 内 17 个受控文件与 `.ai/tasks/TASK-0175/` 治理账本（人工打断核验：`S=0 / Q=0 / U=0 / H=1`）。

## 推荐结论

APPROVE
