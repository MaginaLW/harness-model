# 阶段二验收矩阵

状态：`completed`。本矩阵把阶段二六项进入输入映射到已提交的实现、测试和可重放证据。
Chapter 13/Phase 02 的完成结论来自两类互补事实：精确绑定原 subject/attestation 的不可变
REVIEW + V2 + CI/Gate 历史，以及阶段结束时对当前实现执行的完整回归基线。它不把历史
TASK-0028 H1 写成当前 merge readiness；当前 TASK-0028 正确保持
`merge_readiness: reverification_required`。

每行均保留 artifact 路径、完整 commit/attestation、可重放 argv、结果与限制。路径均相对
仓库根目录；哈希和 receipt 细节见[阶段二证据索引](phase-02-evidence-index.md)，最终质量结果见
[阶段二验收报告](phase-02-acceptance-report.md)。

| 输入 ID | 实现与规格 | 定向测试 | artifact 路径 | commit / attestation | reproduce argv | 结果 | 已知限制 |
|---|---|---|---|---|---|---|---|
| P2-REV-01 | `src/aiflow/review_service.py`；`docs/implementation/chapter-08-structured-review.md` | `tests/unit/test_review_package.py`；`tests/integration/test_review_command.py`；`tests/e2e/test_phase_02_negative_self_hosting.py` | `.ai/tasks/TASK-0028/reviews/REV-0055-r0001.json`；`.ai/tasks/TASK-0028/reviews/REV-0056-r0001.json` | H1 subject `b7c7fb4a0bab1a2a4b0d9a59edfe237839f3779d` | `python -m pytest tests/unit/test_review_package.py tests/integration/test_review_command.py tests/e2e/test_phase_02_negative_self_hosting.py -q` | 双阶段审核、latest-current-review 与 stale 拒绝均通过；H1 双审核是已审计历史事实 | H1 审核已随 subject 变化而 stale，不能作为当前 TASK-0028 或未来变更的批准 |
| P2-V2-01 | `src/aiflow/verification_service.py`；`docs/implementation/chapter-09-v2-policy-contracts.md`；`docs/implementation/chapter-10-independent-verifier-v2-evidence-gate.md` | `tests/integration/test_verify_command.py`；`tests/acceptance/test_phase_02_self_hosting.py` | `.ai/policy/verification-levels.yaml`；`.ai/tasks/TASK-0028/evidence-h1-b7c7fb4a.json` | H1 subject `b7c7fb4a0bab1a2a4b0d9a59edfe237839f3779d` | `python -m pytest tests/integration/test_verify_command.py tests/acceptance/test_phase_02_self_hosting.py -q` | 有序 14-check V2、两阶段 evidence、current-binding 拒绝和 H1 14/14 passed 均有证据 | H1 final evidence 只证明原 subject 的执行，不能跨 subject 或 task 复用 |
| P2-VER-01 | `src/aiflow/verifier_service.py`；`docs/implementation/chapter-10-independent-verifier-v2-evidence-gate.md` | `tests/acceptance/test_phase_02_self_hosting.py`；`tests/e2e/test_v2_verifier_scenario.py`；`tests/e2e/test_phase_02_negative_self_hosting.py` | `.ai/tasks/TASK-0028/verifier-contexts/1faa4f460ad3f666398707c9570e34a17a9e19d6333c172629de4bb9b81295df.json` | H1 subject `b7c7fb4a0bab1a2a4b0d9a59edfe237839f3779d` | `python -m pytest tests/acceptance/test_phase_02_self_hosting.py tests/e2e/test_v2_verifier_scenario.py tests/e2e/test_phase_02_negative_self_hosting.py -q` | 不同且非空 actor、最小 context、freshness 与 same/empty actor 拒绝均通过 | actor 是 task-local 审计标签，不是人员、模型或外部身份认证 |
| P2-MUT-01 | `src/aiflow/mutation_evidence.py`；`.ai/mutations/phase-02-critical-manifest.json`；`docs/implementation/chapter-11-acceptance-integration-mutation.md` | `tests/unit/test_mutation_manifest.py`；`tests/integration/test_mutation_manifest_contract.py`；`tests/e2e/test_phase_02_negative_self_hosting.py` | `.ai/mutations/phase-02-critical-manifest.json`；`.ai/tasks/TASK-0028/evidence-h1-b7c7fb4a.json` | H1 mutation digest `2028bd7cbdeebd26033e3d8dd36728e87362f71f638f2a89087425f73da8530e` | `python -m pytest tests/unit/test_mutation_manifest.py tests/integration/test_mutation_manifest_contract.py tests/e2e/test_phase_02_negative_self_hosting.py -q` | 固定五项 manifest、public consumer、H1 five-killed 和 survived fail-closed 均通过 | collection/action/artifact 严格绑定当前事实；负向 E2E 隔离 survived consumer 语义，不替代完整 binding suite |
| P2-ESC-01 | `src/aiflow/observation_service.py`；`src/aiflow/observation_decision.py`；`docs/implementation/chapter-12-runtime-observations-hooks.md` | `tests/integration/test_observation_escalation.py`；`tests/integration/test_escalate_command.py`；`tests/e2e/test_phase_02_negative_self_hosting.py` | `docs/superpowers/state/chapters/chapter-12.yaml`；`tests/integration/test_phase_02_self_hosting.py` | Chapter 12 projection `741790f14ccdc79748a1c83a83536c88fd6095bd` | `python -m pytest tests/integration/test_observation_escalation.py tests/integration/test_escalate_command.py tests/e2e/test_phase_02_negative_self_hosting.py -q` | observation→escalation/refusal 与 scope-overrun 后 begin 拒绝均通过 | 仅覆盖受支持的结构化 observation；结论不授权执行也不允许自动降级 |
| P2-HOOK-01 | `tools/hooks/`；`src/aiflow/cli.py`；`docs/implementation/chapter-12-runtime-observations-hooks.md` | `tests/integration/test_tool_wrappers.py`；`tests/integration/test_phase_02_self_hosting.py` | `tools/hooks/pre_commit.py`；`tools/hooks/pre_command.py`；`tests/integration/test_phase_02_self_hosting.py` | Chapter 12 projection `741790f14ccdc79748a1c83a83536c88fd6095bd` | `python -m pytest tests/integration/test_tool_wrappers.py tests/integration/test_phase_02_self_hosting.py -q` | 支持事实上的 Hook/CLI/CI decision semantic parity 回归通过 | 不证明跨平台 live Hook、未安装客户端、IDE/GUI/remote Git、自由 shell、通用拦截或 OS sandbox |

## Chapter 13 exit 映射

| exit | 验收依据 | 状态 |
|---|---|---|
| CH13-EXIT-01 | TASK-0028 H1 在其精确 subject 上完成 design/implementation 双审核、独立 local-final V2、code approval/local Gate 和隔离 CI/Gate；13.4 再覆盖关键拒绝路径 | passed；这是不可变时序证据，不是当前 TASK-0028 merge-ready 声明 |
| CH13-EXIT-02 | H1 local evidence 14/14、五项 killed、零 unverified，CI-003 在治理 attestation HEAD 重放 14/14、五项 immutable mutation、独立 verifier/context 并通过 Gate；最终又以 LF checkout 和保留的 task-local artifact 在 `f35d3094a8385806abff2996691e5224bedb00e2` 只读复放 local Gate | passed；clean clone 不含 ignored runtime artifact，须按索引附带原 artifact，不能搬到新 HEAD |
| CH13-EXIT-03 | Chapter 12 Hook/CLI/CI same-fact parity，加上 13.4 scope、review、actor 和 mutation 负向 E2E | passed；仅限已列出的结构化事实和 semantic fields |
| CH13-EXIT-04 | 最终 diff、task ledger、状态与质量命令审计未引入 V3、模型路由、资源调度、push/merge/deploy/凭据/付费调用或其他未经授权外部动作 | passed；阶段三仍 `not_started` 且进入门未满足 |

## 阶段二总验收

| 检查 | 证据 / 命令 | 状态 |
|---|---|---|
| 六项输入映射 | 本矩阵六行、证据索引和 executable path checks | passed |
| 阶段一 V0/V1 与试点仍可验证 | `python -m pytest tests/integration/test_acceptance_traceability.py -q` | passed |
| 状态、task evidence、spec/Policy hash 一致 | YAML/ledger 审计；`python -m aiflow validate TASK-0025`；`python -m aiflow validate TASK-0028`；两者 `status --format json` | passed；TASK-0028 的 stale evidence/approval 被显式投影为 `reverification_required` |
| 质量与 Gate | full pytest、Ruff、format、mypy、branch coverage、diff-cover，以及精确历史 attestation 的只读 Gate；结果见验收报告 | passed |
| 失败和限制保留 | 追加式 ledger/review/action-use/evidence、负向 E2E、本文限制列与 Phase 3 非授权输入 | passed |

## 不可变历史与可编辑投影

`.ai/tasks/**` 内的 event、review/context、approval、action-use receipt、evidence snapshot 和失败
记录保持追加式。矩阵、索引、状态、README、CHANGELOG 与操作文档是当前交付投影；它们可以
描述历史事实，但不能使旧 approval/evidence 变新。bootstrap 标记允许本仓库用常规本地质量
基线完成自身 Chapter 13，不修改产品 Policy，也不授予 merge、push、deploy 或阶段三能力。
