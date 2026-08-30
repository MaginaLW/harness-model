# 阶段二可重放证据索引

状态：`completed`。本索引定位阶段二不可变 task/attestation 证据与当前基线重放入口，并防止
把历史通过误报为当前或未来 subject 的 merge readiness。它与
[阶段二验收矩阵](phase-02-acceptance-matrix.md)和
[阶段二验收报告](phase-02-acceptance-report.md)配套。

## 使用规则

1. 对运行时 task 先执行 `validate` 和 `status --format json`；lifecycle state 与
   `merge_readiness` 必须分别读取。
2. review、approval、action-use、mutation artifact 和 V2 evidence 只对同一 task、base、
   subject、spec、Policy、classification 与 CI attestation 有效；不匹配即 stale。
3. target mutation、临时 worktree、清理和外部动作仍需要当时适用的精确 action approval；
   本索引和 Phase 2 完成状态都不授权重新执行。
4. 历史 replay 必须在指定 commit 的隔离 checkout 中只读运行。当前实现回归证明兼容性，
   不能刷新旧 approval 或 evidence。

## 六项输入

| 输入 | 主要 artifact 路径 | commit / attestation | 重放 argv | outcome | known limits |
|---|---|---|---|---|---|
| P2-REV-01 | `docs/implementation/chapter-08-structured-review.md`；`src/aiflow/review_service.py`；`.ai/tasks/TASK-0028/reviews/REV-0055-r0001.json`；`.ai/tasks/TASK-0028/reviews/REV-0056-r0001.json` | Chapter 8 core `8305ed68aaec83ecc093c30c0afed8ea7d3cc98a`；H1 subject `b7c7fb4a0bab1a2a4b0d9a59edfe237839f3779d` | `python -m pytest tests/unit/test_review_package.py tests/integration/test_review_command.py tests/e2e/test_phase_02_negative_self_hosting.py -q` | structured design/implementation review、latest-current-review 和 stale 拒绝通过 | H1 review 是历史事实，不是 current approval |
| P2-V2-01 | `docs/implementation/chapter-09-v2-policy-contracts.md`；`docs/implementation/chapter-10-independent-verifier-v2-evidence-gate.md`；`.ai/policy/verification-levels.yaml`；`.ai/tasks/TASK-0028/evidence-h1-b7c7fb4a.json` | Chapter 9 core `e17a34dca5530dc71149004a5f5a5a6dad96ea70`；H1 subject `b7c7fb4a0bab1a2a4b0d9a59edfe237839f3779d` | `python -m pytest tests/integration/test_verify_command.py tests/acceptance/test_phase_02_self_hosting.py -q` | ordered V2 contract 与 H1 14/14 final evidence 可审计 | evidence 在 binding 变化后必须重新生成；H1 当前不是 merge-ready |
| P2-VER-01 | `src/aiflow/verifier_service.py`；`.ai/tasks/TASK-0028/verifier-contexts/1faa4f460ad3f666398707c9570e34a17a9e19d6333c172629de4bb9b81295df.json` | context SHA-256 `1faa4f460ad3f666398707c9570e34a17a9e19d6333c172629de4bb9b81295df` | `python -m pytest tests/acceptance/test_phase_02_self_hosting.py tests/e2e/test_v2_verifier_scenario.py tests/e2e/test_phase_02_negative_self_hosting.py -q` | independent nonempty actor、minimal context 与 same/empty actor 拒绝通过 | actor label 不是外部身份或模型认证 |
| P2-MUT-01 | `.ai/mutations/phase-02-critical-manifest.json`；`src/aiflow/mutation_evidence.py`；`.ai/tasks/TASK-0028/evidence-h1-b7c7fb4a.json` | H1 mutation SHA-256 `2028bd7cbdeebd26033e3d8dd36728e87362f71f638f2a89087425f73da8530e` | `python -m pytest tests/unit/test_mutation_manifest.py tests/integration/test_mutation_manifest_contract.py tests/e2e/test_phase_02_negative_self_hosting.py -q` | five fixed mutants、H1 all-killed 与 survived fail-closed 可重放 | collection/action/artifact current-bound；negative E2E 只隔离 consumer survived 语义 |
| P2-ESC-01 | `src/aiflow/observation_service.py`；`src/aiflow/observation_decision.py`；`docs/implementation/chapter-12-runtime-observations-hooks.md` | Chapter 12 projection `741790f14ccdc79748a1c83a83536c88fd6095bd` | `python -m pytest tests/integration/test_observation_escalation.py tests/integration/test_escalate_command.py tests/e2e/test_phase_02_negative_self_hosting.py -q` | deterministic escalation/refusal 与 scope-overrun begin 拒绝通过 | 无执行授权或自动降级；只覆盖结构化 observation |
| P2-HOOK-01 | `tools/hooks/pre_commit.py`；`tools/hooks/pre_command.py`；`tests/integration/test_tool_wrappers.py` | Chapter 12 projection `741790f14ccdc79748a1c83a83536c88fd6095bd` | `python -m pytest tests/integration/test_tool_wrappers.py tests/integration/test_phase_02_self_hosting.py -q` | supported Hook/CLI/CI semantic parity 通过 | 排除跨平台 live Hook、GUI/IDE/remote Git、shell-language parsing 与 OS sandbox |

## Chapter 13 自举历史（not current approval）

`TASK-0028` H1 是完成 13.3/Chapter 13 的不可变时序证据，但不是 current HEAD approval，
must not be reported as current merge-ready。Phase 2 收口时其 current subject 为
`cb1e15b547a8280ddf7b7515f45367aec14aa490`，`status` 正确返回 approvals/evidence stale 和
`merge_readiness: reverification_required`；本次未改写 ledger 规避该结论。

| artifact | path | immutable identifier / outcome |
|---|---|---|
| H1 local final V2 | `.ai/tasks/TASK-0028/evidence-h1-b7c7fb4a.json` | file SHA-256 `4fc5729ef5e40f468b8966e35696a84e47b2de05e363d517293ac9e2f9823662`；subject `b7c7fb4a0bab1a2a4b0d9a59edfe237839f3779d`；14/14、five killed、zero unverified |
| H1 design / implementation review | `.ai/tasks/TASK-0028/reviews/REV-0055-r0001.json`；`.ai/tasks/TASK-0028/reviews/REV-0056-r0001.json` | `APPROVE`；implementation context `287db9c8c642a0e65a79f32392f270b25fdd7abd7a03a500d04851781196cfb1` |
| H1 code-approval attestation | `.ai/tasks/TASK-0028/approvals.json` | attestation `f35d3094a8385806abff2996691e5224bedb00e2`；local Gate passed |
| H1 CI-003 receipt | `.ai/tasks/TASK-0028/action-use-5a3071cd2e446dea89d5b8acb5c6c26399cf69a4ba141da0f3995706bfa28020.md` | audit head `fd32681ea39418f4176d72738cbe7dc8b8fca5ca`；receipt SHA-256 `3d420bb8ec5845287744b6e19b1890997dba58fdfab158803a84a0bcf86eff94`；CI 14/14、five replayed killed、Gate passed |
| H1 external CI evidence / Gate | CI-003 receipt 中的外部临时 artifact 摘要 | evidence SHA-256 `55e957e41c32009feeb04e3781323d12f16b48d84b148ec457870d87bcdffa13`；Gate output SHA-256 `962262ea382a517a2fa46bed825c7659a3a33547f9018aa4b1961e247ce1fec3` |
| H1 verifier context | `.ai/tasks/TASK-0028/verifier-contexts/1faa4f460ad3f666398707c9570e34a17a9e19d6333c172629de4bb9b81295df.json` | SHA-256 `1faa4f460ad3f666398707c9570e34a17a9e19d6333c172629de4bb9b81295df`；task-local actor only |

TASK-0025 另保留已合并 subject `7191ca4c9c0bc23b75af9599ebb381ed077aa081` 的 final
V2 14/14、五项 killed、独立 `REV-0048 APPROVE`、code approval/local Gate 与 merge ledger；
它证明闭环可完成，但同样不能跨 task 或 subject 复用。

TASK-0025 H1 历史 snapshot 的 `non_task_inputs` SHA 绑定原 Windows CRLF 工作树字节；跨平台
测试必须在首次 checkout 前显式固定 `core.autocrlf=true`，逐文件确认 `w/crlf` 后再校验原始
SHA。这个重放条件不适用于 TASK-0028 的 LF Gate artifact，也不授权改写任一历史 manifest。

## 当前基线重放

Phase 2 当前实现先使用以下只读/常规非覆盖率命令收口；精确结果记录在验收报告：

```powershell
python -m pytest tests/integration/test_acceptance_traceability.py -q
python -m pytest tests/acceptance/test_phase_02_self_hosting.py tests/integration/test_phase_02_self_hosting.py tests/e2e/test_phase_02_self_hosting_scenario.py tests/e2e/test_phase_02_negative_self_hosting.py -q
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy src
git diff --check
```

覆盖率重放不得使用会在仓库根生成默认 `.coverage` 的简写命令。当前重放必须按
[Quickstart 的“阶段二基线重放”](../operations/quickstart.md#阶段二基线重放)创建唯一的独立
run directory，通过 `COVERAGE_FILE` 和显式 XML 路径隔离产物，并同时执行总分支覆盖率 85%
与 `diff-cover` 变更覆盖率 90% 两项门槛。

历史 Gate 只在索引指定的 code-approval attestation 隔离 checkout 中重放；当前 TASK-0028
的 Gate 必须继续 fail closed，不能作为 Phase 2 文档基线的“修复”目标。bootstrap 自举例外
允许本地代码、测试、配置和文档用上述常规质量基线收口，但不修改 `.ai/policy/`，也不授权
V3、模型路由、资源调度、push、merge、deploy、仓库/业务数据删除、凭据导出、付费调用或
其他外部动作；精确 task-owned 临时清理仍须单独满足当时的 action/scope 边界。

本次 local Gate 复放固定 TASK-0028 code-approval attestation
`f35d3094a8385806abff2996691e5224bedb00e2`，在 checkout 前设置 `core.autocrlf=false`、
`core.eol=lf`，并附带原 task-local ignored artifact
**.ai/tasks/TASK-0028/logs/MUTRUN-20260829T140929Z-1ceeb5a57d70bcd9/targeted-mutation/**；没有重新
执行 mutation。结果为 `passed: true`、`reason_codes: []`。clean clone 本身不包含该 ignored
artifact，因此不能单独复放 Gate；CRLF checkout 会使 manifest/runner source SHA 不匹配并
正确 fail closed。这个平台/保留条件是证据限制的一部分，不得省略或写成 clean-checkout 保证。
