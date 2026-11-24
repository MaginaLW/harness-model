# Review Package

## 审核目标

对 `TASK-0191`（分支 `codex/mutation-attribution-delivery`，`base_commit=c1037f503c3c53f35e2911468149fd05763fa2a3`，`subject_commit=aa231effb973007ddb42b9c10bd8dad8f02f2729`，预审核提交 `HEAD=632d6c05388d13a0dd315cc1d824bbda9599b37e`）执行独立实现审核，裁决：

1. 移入并适配至 `BASE_A` 的 17 个 V2 变异归因模式、实现与测试文件是否严格落在 `allowed_scope` 内、真实完整（无硬编码或空壳实现），且完整保留 Wave 1（测试优化）与 Wave 2A/2B 既有修复；
2. 单轮独立 Windows V2 正式验证证据（14 项检查、覆盖率、5/5 原生变异 `killed` 及独立验证者工作树中的 6 份脱敏变异 JSON）是否真实、完整、零凭据/隐私泄露并满足 `spec.md` 与 `V2` 门禁要求；
3. 是否批准进入 `aiflow verify --finalize`、`approve --type code`、`delivery-authorization.md`（及仅 `git add -f` 6 份授权变异 JSON）、`aiflow gate` 与 PR 交付。

## 背景

`TASK-0191` 为 Wave 3 — Track A（所有者 2026-11-24 批准的选项 A1：PR #186 变异归因在最新 `main` 基线 `BASE_A` 上的公开披露交付）。前置步骤已完成 `classify`（`REVIEW / V2`）、`freeze`（`spec_sha256=fd8bb94382f06fc9ef36ca0c8ea0c94ba9b9dd41dce24d23ee06a830f1f4dd55`）、`REV-0001` 独立设计审核（`APPROVE`，`a9884ea4`）、常设授权 `spec` 批准、`begin`、17 文件交付提交 `aa231eff`、`sync`、单次 `targeted_mutation_v2` 行动载荷独立审核与常设授权批准（`action_sha256=11ad4f13061f8f8503445e4c954ebe0644d10b95ba638c56eee1c342d09df4c1`），以及独立验证者 `independent-verifier-track-a` 完成的单轮正式 Windows V2 验证（`632d6c05`）。

## 代码地图

17 个受控交付文件（严格匹配 `task.yaml` `allowed_scope` 及 `0526983f..2dd4e8e7` 非任务文件列表）：

- **11 个逐字节移入文件**（与 `2dd4e8e7` Git blob 一致）：
  - 模式定义：`.ai/schemas/mutation-evidence.schema.json`
  - 核心引擎与隔离材料：`src/aiflow/mutation_evidence.py`、`src/aiflow/mutation_materials.py`、`src/aiflow/mutation_process.py`、`src/aiflow/mutation_runner.py`、`src/aiflow/verification_service.py`
  - 测试与夹具：`tests/mutation_evidence_helpers.py`、`tests/e2e/test_phase_02_negative_self_hosting.py`、`tests/e2e/test_phase_02_self_hosting_scenario.py`、`tests/integration/test_mutation_runner_contract.py`、`tests/unit/test_mutation_evidence.py`
- **3 个 Wave 1 / 2A 重叠文件**（在 `BASE_A` 上仅叠加 PR #186 增量）：
  - `src/aiflow/process_runner.py`：保留 Wave 2A `_environment()` 对 `ssh-keygen` 与 `ProgramData` 的支持，新增 `max_output_bytes` 参数与边界校验。
  - `tests/unit/test_process_runner.py`：保留 Wave 2A PATH 与系统环境变量测试，新增 `max_output_bytes` 越界拒绝与 Windows Job 16 KiB 溢出边界单测。
  - `tests/integration/test_verify_command.py`：保留 Wave 1 模块级种子仓缓存（`_prepare_verified_v2` 等），在 `test_v2_ci_real_consumer_rejects_tampered_log_before_plan_or_runner` 叠加 `replay_synthetic_mutation` 增量。
- **3 个 `BASE_A` 契约锚点同步文件**（保持同一 17 文件范围，经协调者 #119 与 `REV-0001` 确认）：
  - `src/aiflow/mutation_protocol.py`：更新 `REVIEWED_INPUT_SHA256` 中随 Wave 2B/Wave 1 变更的两项规范 LF SHA-256（`tests/unit/test_policy.py` -> `32292a52c992fa5827bc5c2e446b37ce41751c0175d57237fab45b6c30a5fb9b`；`tests/integration/test_verify_command.py` -> `51857857dda18bd293e7ebf1487dd6997ac87864481e6c1ecd1c46bb0198e755`），其余 3 项与 `BASE_A` 一致。
  - `src/aiflow/mutation_reporter.py` 与 `tests/unit/test_mutation_runner.py`：同步 `MUT-V2-001` 失败锚点行号 `(206,)` 与 `MUT-V2-002` 失败锚点行号 `(1272,)` 及对应参数化合成夹具行号。

## 语义变更

- **V2 变异归因协议与独立子进程检测**：新增 `mutation-evidence.schema.json` `2.0` 严格分支、`mutation_protocol.py` 16 KiB 封闭线协议及 `fail-closed` 判定（仅精确节点、阶段、行锚点、异常类型与语义签名全部匹配且进程生命周期与材料一致时返回 `killed`，其余一律 `unverified`/`survived`）、`mutation_materials.py` Git blob 与已加载 `aiflow.*` 运行时字节/函数一致性核验、`mutation_reporter.py` `-I -B` 无第三方插件隔离报告器，以及 `mutation_process.py` Windows Job 挂起创建/恢复与 EOF/清理验证。
- **单次行动消费与历史隔离**：`mutation_evidence.py` 在跨进程锁下原子消费单次 `targeted_mutation_v2` 行动批准并生成不可变 2.0 证据，与 `1.0` 历史只读消费者 `read_historical_mutation_evidence` 严格隔离；`verification_service.py` 在 V2 流程中强制执行材料与运行时预检及归因消费。
- **进程边界与 `BASE_A` 兼容**：`process_runner.py` 新增 `max_output_bytes` 边界参数并在 `BASE_A` 上完整保留 Wave 2A `_environment()` 对 `ssh-keygen` 与 Windows `ProgramData` 的转发；`test_verify_command.py` 保留 Wave 1 种子仓缓存；`mutation_protocol.py` / `mutation_reporter.py` 同步 `BASE_A` 上两项测试输入 SHA-256 与锚点行号 `(206,)` / `(1272,)`。

## 风险

- **长耗时全量测试回归风险**：已由 Wave 1 种子仓缓存与 `BASE_A` 基线协同控制；本轮独立 V2 实测 `unit_tests` 耗时 `1654563 ms`（约 27.6 分钟），低于 `3000s` 预算上限。
- **A1 公开披露与隐私边界风险**：按项目所有者 2026-11-24 A1 授权，定稿阶段仅强制纳入 `.ai/tasks/TASK-0191/logs/MUTRUN-20261124T213451Z-e6240f97221e32c5/targeted-mutation/` 下的 6 份脱敏变异 JSON（`evidence.json` 与 `logs/MUT-V2-001.json`..`005.json`）及 `delivery-authorization.md`。已逐份核验该 6 份 JSON 内容与 SHA-256，确认零凭据、零密钥、零本机绝对路径；其余 `logs/` 运行日志保持未跟踪且不入库。

## 证据

- **已验证**：
  - 实现前置靶向检查（提交 `aa231eff`）：定向 pytest `515 passed in 92.86s`、`ruff check .` 通过、`ruff format --check .`（838 files）通过、`mypy`（61 source files）0 错误、5/5 `REVIEWED_INPUT_SHA256` LF 摘要一致。
  - 独立单轮正式 Windows V2 验证（`independent-verifier-track-a`，命令 `python -m aiflow verify TASK-0191 --actor independent-verifier-track-a`，pre-evidence 提交 `632d6c05`）：
    - `.ai/tasks/TASK-0191/evidence.json`（`verification_snapshot_sha256=353ebecd8b9274729509222762f8203ec2cd7e16982d8032ab4074c2cee30a97`，`verifier_context_sha256=ee6187d989043075478c8485dd4a82e8188ff6821595adfe14ad8550304a23a8`）：14/14 必需检查全部 `passed`（`unit_tests` `1654563 ms` / `5163 passed, 9 skipped`、核心分支覆盖率 `90%`、变更行覆盖率 `92%`（`1043` 行、`79` 未覆盖）、`ruff_check`、`ruff_format_check`、`mypy`、`targeted_mutation` 5/5 `killed`、`independent_verifier`）。
    - 行动消耗回执：`action-use-11ad4f13061f8f8503445e4c954ebe0644d10b95ba638c56eee1c342d09df4c1.md` 状态 `recorded`，`mutation_evidence_sha256=c6b59cda4df1a7b9131e52d932ce3fed0dc716f699a95aba009b6c3e40c0f8ef`。
    - 6 份授权披露变异 JSON（位于独立验证者工作树 `.ai/tasks/TASK-0191/logs/MUTRUN-20261124T213451Z-e6240f97221e32c5/targeted-mutation/`，零密钥/零隐私路径）：
      - `evidence.json`（5196 B，SHA-256 `a19282a23b9530a710c38e59483f14666696b698ac4bee1bf62a3d60a599b2ab`）
      - `logs/MUT-V2-001.json`（2536 B，SHA-256 `ac04ce453649394133becb667f50838d7ce06e24b78af0f0b2e9f2ef38e4e87e`，`killed`）
      - `logs/MUT-V2-002.json`（2768 B，SHA-256 `06a25648d394ed578cb9f8c02fbd9cfcbcfe23cd2e454ae86fdb0da2e2927c9d`，`killed`）
      - `logs/MUT-V2-003.json`（2535 B，SHA-256 `54adf7307af97ce0f4b1d735bea817a0e6306aa61f3e03e8ab481f19f8584e1d`，`killed`）
      - `logs/MUT-V2-004.json`（2491 B，SHA-256 `089cef03061efc5e2d1ecd848749d5641c91dfc6054bc51a660691e91e6908c8`，`killed`）
      - `logs/MUT-V2-005.json`（2526 B，SHA-256 `f913a0170547bfe7f7cbd1f8311e3d3f8b71466185b6425ae2d3520ac49a3c35`，`killed`）
- **未验证**：
  - `REV-0002` 独立实现审核、`aiflow verify TASK-0191 --finalize`、常设授权 `code` 批准、`delivery-authorization.md` + 6 份 JSON 强制入库及 `aiflow gate TASK-0191` 尚待完成；
  - 远端推送 `codex/mutation-attribution-delivery`、PR 创建、公开 `ai-quality-gate` 通过、merge commit 合入 `main` 及关闭被替代 PR #186 尚未执行。

## 审核问题

1. `BASE_A..aa231eff` 差异是否严格限制在 `allowed_scope` 17 个文件，且 Wave 1/2A/2B 改进（`_environment()`、`test_policy.py`、`test_verify_command.py` 种子加速）完整保留？
2. `evidence.json`（14/14）、5/5 原生变异 `killed`、`90%` 核心分支覆盖率与 `92%` 变更行覆盖率是否真实可复核且满足 `V2` 要求？
3. 6 份待披露变异 JSON 是否已核验零 secrets/credentials/本机隐私路径，且可交由 `independent-verifier-track-a` 执行 `--finalize`、`code` 批准、`delivery-authorization.md`、`git add -f` 与 `gate`？

交付边界五项自检结论：

1. **目标与关键假设是否清楚**：清楚，按所有者 2026-11-24 A1 公开披露授权在 `BASE_A` (`c1037f50`) 上交付 PR #186 17 文件实现与测试及本轮 6 份脱敏变异 JSON，保留 `codex/mutation-attribution-0526983f` 与 `TASK-0175` 原件不变。
2. **是否已核实语言标准库与代码库既有复用机会**：已核实，完整复用 `ast`、`hashlib`、`subprocess`、`tempfile`、`msvcrt`/`fcntl` 及既有 `aiflow.approval`、`aiflow.contracts`、`aiflow.git_context`、`aiflow.process_runner` 等模块。
3. **各修改模块是否存在更简单的直接实现**：无更简单且能维持同等 fail-closed 变异归因隔离与单次行动消费安全性的实现；仅对受 Wave 1/2B 影响的两处 `REVIEWED_INPUT_SHA256` 与行号锚点做最小同步。
4. **新增抽象、分支或配置项是否均有当前明确依据**：所有新增模块、2.0 Schema 字段与 `max_output_bytes` 参数均直接对应 `spec.md` 与 V2 归因契约，无多余开关或投机抽象。
5. **是否只触及了任务范围边界内的文件**：是，仅修改 `allowed_scope` 内 17 个文件与 `.ai/tasks/TASK-0191/**`，未触及任何其他文件或历史分支/工作树。

## 推荐结论

APPROVE
