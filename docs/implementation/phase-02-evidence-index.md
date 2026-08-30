# 阶段二可重放证据索引

状态：`in_progress`。本索引服务 Chapter 13.5：定位阶段二证据、给出重放命令，并防止将
历史 task-local 事实误当作当前 task 或 future subject 的通过结论。它与
[阶段二验收矩阵](phase-02-acceptance-matrix.md) 配套；阶段二尚未完成。

## 使用规则

1. 先以 `python -m aiflow validate <TASK-ID>`、`python -m aiflow scope <TASK-ID>` 和
   `python -m aiflow status <TASK-ID> --format json` 确认当前绑定与 merge readiness。
2. `review`、`approval`、`action-use`、mutation artifact 和 V2 evidence 必须匹配同一 task、
   base、subject、frozen spec、Policy、classification 和（CI 时）attestation；不匹配即 stale。
3. 仅用每行列出的命令重放确定性测试。targeted mutation、临时 worktree 或清理仍需要当前、
   精确、single-use 的 action approval；本索引不授权它们。
4. 本文保存路径、哈希和限制，不能替代 structured record、Gate 或独立审核。

## 章节证据

| 输入 | 主要 artifact 路径 | commit / attestation | 重放 argv | outcome | known limits |
|---|---|---|---|---|---|
| P2-REV-01 | `docs/implementation/chapter-08-structured-review.md`；`src/aiflow/review_service.py`；`.ai/tasks/TASK-0028/reviews/REV-0055-r0001.json`；`.ai/tasks/TASK-0028/reviews/REV-0056-r0001.json` | Chapter 8 core `8305ed6`；TASK-0028 H1 subject `b7c7fb4a0bab1a2a4b0d9a59edfe237839f3779d` | `python -m pytest tests/unit/test_review_package.py tests/integration/test_review_command.py -q` | structured design/implementation review and freshness checks implemented | TASK-0028 H1 reviews are historical after the H2 state projection; they cannot approve the current subject |
| P2-V2-01 | `docs/implementation/chapter-09-v2-policy-contracts.md`；`docs/implementation/chapter-10-independent-verifier-v2-evidence-gate.md`；`.ai/policy/verification-levels.yaml`；`.ai/tasks/TASK-0028/evidence-h1-b7c7fb4a.json` | Chapter 9 core `e17a34d`；H1 subject `b7c7fb4a0bab1a2a4b0d9a59edfe237839f3779d` | `python -m pytest tests/integration/test_verify_command.py tests/acceptance/test_phase_02_self_hosting.py -q` | ordered V2 contract and H1 14/14 final evidence recorded | current final evidence must be regenerated after any binding change; H1 is not merge-ready now |
| P2-VER-01 | `src/aiflow/verifier_service.py`；`.ai/tasks/TASK-0028/verifier-contexts/1faa4f460ad3f666398707c9570e34a17a9e19d6333c172629de4bb9b81295df.json` | verifier-context SHA-256 `1faa4f460ad3f666398707c9570e34a17a9e19d6333c172629de4bb9b81295df` | `python -m pytest tests/acceptance/test_phase_02_self_hosting.py tests/e2e/test_v2_verifier_scenario.py -q` | independent nonempty actor and minimal-context contract covered | labels are not identity authentication; new current subject needs a fresh independent verifier |
| P2-MUT-01 | `.ai/mutations/phase-02-critical-manifest.json`；`src/aiflow/mutation_evidence.py`；`.ai/tasks/TASK-0028/evidence-h1-b7c7fb4a.json` | H1 mutation evidence SHA-256 `2028bd7cbdeebd26033e3d8dd36728e87362f71f638f2a89087425f73da8530e` | `python -m pytest tests/unit/test_mutation_manifest.py tests/integration/test_mutation_manifest_contract.py -q` | five fixed mutants are loader-validated; H1 records five killed outcomes | collection/replay is current-binding and action-gated; H1 artifact cannot be reused for new subject; 13.4 negative E2E pending |
| P2-ESC-01 | `src/aiflow/observation_service.py`；`src/aiflow/observation_decision.py`；`docs/implementation/chapter-12-runtime-observations-hooks.md` | Chapter 12 projection subject `741790f` (historical chapter evidence) | `python -m pytest tests/integration/test_observation_escalation.py tests/integration/test_escalate_command.py -q` | deterministic escalation/refusal decision core implemented | no authorization or automatic downgrade; 13.4 scope/Policy/permission negative E2E pending |
| P2-HOOK-01 | `tools/hooks/pre_commit.py`；`tools/hooks/pre_command.py`；`tests/integration/test_tool_wrappers.py` | Chapter 12 projection subject `741790f` (historical chapter evidence) | `python -m pytest tests/integration/test_tool_wrappers.py tests/integration/test_phase_02_self_hosting.py -q` | supported Hook/CLI/CI semantic parity covered | excludes cross-platform live Hook, GUI/IDE/remote Git and shell-language parsing; no OS sandbox claim |

## Chapter 13 self-hosting history (not current approval)

`TASK-0028` H1 is necessary audit history for 13.3, but its subject is not the current HEAD and
must not be reported as current merge-ready.
The H1 paths and hashes below remain useful for byte-level historical replay only:

| artifact | path | immutable identifier / outcome |
|---|---|---|
| H1 local final V2 evidence | `.ai/tasks/TASK-0028/evidence-h1-b7c7fb4a.json` | file SHA-256 `4fc5729ef5e40f468b8966e35696a84e47b2de05e363d517293ac9e2f9823662`; subject `b7c7fb4a0bab1a2a4b0d9a59edfe237839f3779d`; 14/14 passed, five killed, no unverified scenarios |
| H1 design / implementation review | `.ai/tasks/TASK-0028/reviews/REV-0055-r0001.json`；`.ai/tasks/TASK-0028/reviews/REV-0056-r0001.json` | `APPROVE`; implementation review context `287db9c8c642a0e65a79f32392f270b25fdd7abd7a03a500d04851781196cfb1` |
| H1 CI simulation receipt | `.ai/tasks/TASK-0028/action-use-5a3071cd2e446dea89d5b8acb5c6c26399cf69a4ba141da0f3995706bfa28020.md` | attestation `f35d3094a8385806abff2996691e5224bedb00e2`; audit head `fd32681ea39418f4176d72738cbe7dc8b8fca5ca`; CI 14/14, five replayed killed, Gate passed |
| H1 verifier context | `.ai/tasks/TASK-0028/verifier-contexts/1faa4f460ad3f666398707c9570e34a17a9e19d6333c172629de4bb9b81295df.json` | SHA-256 `1faa4f460ad3f666398707c9570e34a17a9e19d6333c172629de4bb9b81295df`; task-local actor only |

Historical replay starts with the non-mutating self-hosting suite:

```powershell
python -m pytest tests/acceptance/test_phase_02_self_hosting.py -q
python -m pytest tests/integration/test_phase_02_self_hosting.py -q
python -m pytest tests/e2e/test_phase_02_self_hosting_scenario.py -q
```

These tests validate frozen/historical facts and fail-closed models; they do not refresh approvals,
produce current V2 evidence, consume action approval, or execute external actions.

## Final replay checklist (not yet satisfied)

The final attestation must run these commands against the then-current Chapter 13 task and record
the resulting hashes in its task-local evidence/receipt rather than editing the historical rows above.

```powershell
python -m aiflow validate <CURRENT-TASK>
python -m aiflow scope <CURRENT-TASK>
python -m aiflow status <CURRENT-TASK> --format json
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy src
git diff --check
python -m aiflow gate <CURRENT-TASK> --format json
```

It must additionally run the frozen 13.4 negative E2E set (same/empty actor, survived or missing
mutation, scope/Policy/permission escalation, stale review/evidence), a current action-authorized
V2 collection/finalize/review/code-approval/local Gate sequence, coverage/diff-cover, and the
attestation-HEAD CI replay. The final audit must preserve failed receipts, unverified facts and
platform limitations; it must not implement or claim V3, model routing, resource scheduling, push,
merge, deploy, credential export, paid calls or other unauthorized external actions.
