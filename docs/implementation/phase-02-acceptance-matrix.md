# 阶段二验收矩阵

状态：`in_progress`。本矩阵是 Chapter 13.5 的可追踪验收索引，不是阶段二完成声明。
它把阶段二的六项进入输入映射到已提交的实现、测试和证据，并明确区分当前可重放
事实、历史事实与仍待完成的 Chapter 13.4/13.6 闭环。阶段二的最终五项检查仍全部
需要在最终 attestation 上重新执行。

每行均保留 artifact 路径、commit 或 attestation、可重放 argv、结果与限制；任何一项
都不能只由叙述满足。路径均相对仓库根目录。哈希、命令和收据的详细索引见
[阶段二证据索引](phase-02-evidence-index.md)。

| 输入 ID | 实现与规格 | 定向测试 | artifact 路径 | commit / attestation | reproduce argv | 当前结果 | 已知限制 |
|---|---|---|---|---|---|---|---|
| P2-REV-01 | `src/aiflow/review_service.py`；`docs/implementation/chapter-08-structured-review.md` | `tests/unit/test_review_package.py`；`tests/integration/test_review_command.py` | `.ai/tasks/TASK-0028/reviews/REV-0055-r0001.json`；`.ai/tasks/TASK-0028/reviews/REV-0056-r0001.json` | H1 subject `b7c7fb4a0bab1a2a4b0d9a59edfe237839f3779d` | `python -m pytest tests/unit/test_review_package.py tests/integration/test_review_command.py -q` | 双阶段审核契约和 Chapter 13 H1 的 design/implementation 审核均有记录；H1 仅为历史前提 | H1 审核已随其 subject 失效，不能作为当前 TASK-0028 或阶段二 final approval；13.4 的 stale-review E2E 尚待闭环 |
| P2-V2-01 | `src/aiflow/verification_service.py`；`docs/implementation/chapter-09-v2-policy-contracts.md`；`docs/implementation/chapter-10-independent-verifier-v2-evidence-gate.md` | `tests/integration/test_verify_command.py`；`tests/acceptance/test_phase_02_self_hosting.py` | `.ai/policy/verification-levels.yaml`；`.ai/tasks/TASK-0028/evidence-h1-b7c7fb4a.json` | H1 local subject `b7c7fb4a0bab1a2a4b0d9a59edfe237839f3779d` | `python -m pytest tests/integration/test_verify_command.py tests/acceptance/test_phase_02_self_hosting.py -q` | V2 的 14 项有序 checks、两阶段 evidence 和 current-binding 拒绝已实现；H1 14/14 passed 是可审计历史事实 | H1 final evidence 不可跨 subject 复用；最终 attestation HEAD replay 仍待 current subject 与 phase-final audit |
| P2-VER-01 | `src/aiflow/verifier_service.py`；`docs/implementation/chapter-10-independent-verifier-v2-evidence-gate.md` | `tests/acceptance/test_phase_02_self_hosting.py`；`tests/e2e/test_v2_verifier_scenario.py` | `.ai/tasks/TASK-0028/verifier-contexts/1faa4f460ad3f666398707c9570e34a17a9e19d6333c172629de4bb9b81295df.json` | H1 verifier context bound to subject `b7c7fb4a0bab1a2a4b0d9a59edfe237839f3779d` | `python -m pytest tests/acceptance/test_phase_02_self_hosting.py tests/e2e/test_v2_verifier_scenario.py -q` | 不同且非空 Implementer/Verifier actor、最小 context 与 freshness 拒绝均已覆盖 | actor 是 task-local 审计标签而非外部身份认证；H1 的独立性事实不证明新 subject 的 verifier 独立性 |
| P2-MUT-01 | `src/aiflow/mutation_evidence.py`；`.ai/mutations/phase-02-critical-manifest.json`；`docs/implementation/chapter-11-acceptance-integration-mutation.md` | `tests/unit/test_mutation_manifest.py`；`tests/integration/test_mutation_manifest_contract.py` | `.ai/mutations/phase-02-critical-manifest.json`；`.ai/tasks/TASK-0028/evidence-h1-b7c7fb4a.json` | H1 mutation artifact digest `2028bd7cbdeebd26033e3d8dd36728e87362f71f638f2a89087425f73da8530e` | `python -m pytest tests/unit/test_mutation_manifest.py tests/integration/test_mutation_manifest_contract.py -q` | 固定五项 manifest、public consumer 和 all-killed projection 已实现；H1 五项均 killed 是历史 receipt/evidence 事实 | mutation artifact 绑定 task/base/subject/spec/Policy/classification，不能重用；13.4 survived/missing mutant E2E 和 current action-approved collection 仍待完成 |
| P2-ESC-01 | `src/aiflow/observation_service.py`；`src/aiflow/observation_decision.py`；`docs/implementation/chapter-12-runtime-observations-hooks.md` | `tests/integration/test_observation_escalation.py`；`tests/integration/test_escalate_command.py` | `docs/superpowers/state/chapters/chapter-12.yaml`；`tests/integration/test_phase_02_self_hosting.py` | Chapter 12 completion projection `741790f`（历史章级证据） | `python -m pytest tests/integration/test_observation_escalation.py tests/integration/test_escalate_command.py -q` | observation 到 escalation/refusal 的共享 deterministic core 已实现且为非授权结论 | 仅覆盖受支持结构化 observation；Chapter 13.4 的 scope/Policy/permission escalation negative E2E 尚待闭环 |
| P2-HOOK-01 | `tools/hooks/`；`src/aiflow/cli.py`；`docs/implementation/chapter-12-runtime-observations-hooks.md` | `tests/integration/test_tool_wrappers.py`；`tests/integration/test_phase_02_self_hosting.py` | `tools/hooks/pre_commit.py`；`tools/hooks/pre_command.py`；`tests/integration/test_phase_02_self_hosting.py` | Chapter 12 completion projection `741790f`（历史章级证据） | `python -m pytest tests/integration/test_tool_wrappers.py tests/integration/test_phase_02_self_hosting.py -q` | Hook、CLI、CI 在支持事实上的 decision semantic parity 已有回归测试 | 不证明 Linux/macOS live Hook、未安装客户端、IDE/GUI/remote Git、自由 shell 解析、通用命令拦截或 OS sandbox |

## Chapter 13 exit 映射

| exit | 验收依据 | 当前状态 |
|---|---|---|
| CH13-EXIT-01 | 真实跨模块 `REVIEW + V2` 的双审核、独立验证、local code approval/Gate 与隔离 CI/Gate；索引中的 TASK-0028 H1 receipt 只作为历史时序依据 | pending：current subject 仍须 fresh V2、implementation review、finalize、code approval 和 local Gate，且须完成 13.4 |
| CH13-EXIT-02 | current attestation HEAD 上重放 acceptance、integration、targeted mutation 与 independent verifier；逐项 artifact/hash/argv 见证据索引 | pending：不得用 H1 的旧 subject/evidence 代替 final replay |
| CH13-EXIT-03 | Chapter 12 的 Hook/CLI/CI same-fact parity 及 13.4 负向 E2E | pending：仅支持范围内的 semantic parity 可以宣称 |
| CH13-EXIT-04 | 非目标检查、task-local action/receipt、状态与最终审计均不包含 V3、模型路由、资源调度或未经授权的外部动作 | pending：必须在 final audit 中以实际 diff、ledger 和命令结果确认，不能只靠本文声明 |

## 阶段二总验收（最终 attestation 执行）

| 检查 | 最终证据 / 命令 | 当前状态 |
|---|---|---|
| 六项输入映射 | 本矩阵六行、证据索引及全部路径校验 | mapped；尚未作为 phase-final 通过 |
| 阶段一 V0/V1 与试点仍可验证 | `python -m pytest tests/integration/test_acceptance_traceability.py -q` | pending final run |
| 状态、task evidence、spec/Policy hash 一致 | `python -m aiflow validate <CURRENT-TASK>`；`python -m aiflow scope <CURRENT-TASK>`；state YAML/ledger 审计 | pending final run |
| 质量与 Gate | `python -m pytest -q`；`python -m ruff check .`；`python -m ruff format --check .`；`python -m mypy src`；coverage/diff-cover；`python -m aiflow gate <CURRENT-TASK> --format json` | pending final run |
| 失败和限制保留 | 追加式 task ledger、review revision、action-use receipt、evidence 与本文限制列 | mapped；final audit 须验证未被覆盖或静默改写 |

## 不可变历史与可编辑投影

`.ai/tasks/**` 内的 events、review/context、approval、action-use receipt、evidence snapshot 与
失败记录是追加式审计历史，不能为协调矩阵而改写。本文和证据索引、状态的物化投影、README、
CHANGELOG 与操作文档属于后续受治理提交可更新的说明；更新也不能把历史 H1 结论写成 current
merge readiness。最终结论只来自当时 current task、subject、spec、Policy、attestation 和 Gate。
