# Review Package

## 审核目标

确认 TASK-0028 的 H1 subject
`b7c7fb4a0bab1a2a4b0d9a59edfe237839f3779d` 完整实现冻结规格中 V2 CI
attestation 与 Gate 分层部分，并允许进入本地只读 Gate。该批准不授权隔离 CI simulation、
临时目录创建或清理、H2 state 投影、第二或第三次 targeted mutation、push、merge、deploy、
task close 或其他外部动作。

## 当前绑定

- Base commit：`3f3ead9eeb3cc1039be58627994a3a0d58102534`
- Subject commit：`b7c7fb4a0bab1a2a4b0d9a59edfe237839f3779d`
- Frozen spec SHA-256：
  `657bac588589c0fabb9c8d6a108ab9077cd101c9648f55d0d3f5e71299f06877`
- Classification input SHA-256：
  `28204d9e485e11ca0948982038798e99f8148512a491550e80f4ebeb1e14a75a`
- Active Policy SHA-256：
  `f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`
- Current design review：`REV-0055` / context
  `0d3efee5c9ef2b73936729c5e6fecd88cc2e10756b7ff33823d83acff91e0e71` / `APPROVE`
- Current implementation review：`REV-0056` / context
  `287db9c8c642a0e65a79f32392f270b25fdd7abd7a03a500d04851781196cfb1` / `APPROVE`

`REV-0053 / RF-001` 的原 documentation-only 缺口已保留并通过范围扩展、重新分类、重新冻结和
新设计审核结构化处置。`REV-0054` 首次批准同一设计上下文；`REV-0055` 在规格变更 resolution
完成后重新确认完全相同的 current context，作为当前设计审核引用。

## 代码地图

- `src/aiflow/verification_service.py`：V2 CI 在任何 plan/check 前加载并严格校验 current
  task-local local-final evidence；从该证据派生 verifier actor，经 public consumer 只读重放
  immutable mutation artifact，并拒绝 V2 CI partial/provisional 调用。
- `src/aiflow/gate.py`：V2 external Gate 分层合取 local-final readiness/review/code-approval
  与 external CI checks/snapshot/verifier/context/design/mutation/attestation；V0/V1 和 local V2
  路径保持不变。
- `tests/integration/test_verify_command.py`：覆盖 actor 派生/不匹配、source evidence 缺失或
  stale/tampered、真实 artifact log tamper、public consumer replay、task 零写及 runner 前拒绝。
- `tests/integration/test_gate_command.py`：覆盖 local-final + CI pre positive，以及 local 或 CI
  任一 check、snapshot、review、context、mutation、attestation 失效时 fail closed。
- `docs/implementation/chapter-13-review-self-hosting.md`：记录 H1、隔离 CI simulation 与 H2 的
  独立时序和授权边界；H1 未修改两份 state 文件，13.3 仍为 pending。

除 task-local append-only governance/evidence 外，H1 业务改动只涉及上述五个文件。

## 语义与安全边界

V2 CI 不再生成固定的 mutation-missing sentinel。它只接受 current、local、final、passed、
双审核和 verifier context 均有效的 V2 source evidence；source 无效时在 runner 前拒绝。通过后，
CI 只读使用既有 public consumer 重新验证 artifact、manifest、runner source、五项结果与日志摘要，
不会调用 mutation recorder、action consumer 或 mutation runner，也不会写 task 目录。

External CI evidence 仍保持 `pre_implementation_review`，只证明本次执行和 attestation；它不会
伪造新的 implementation review，也不能替代 local-final evidence 或 code approval。Gate 分别
验证两侧事实，任一侧缺失、陈旧或被篡改均拒绝。

## 证据

- H1 final evidence：`.ai/tasks/TASK-0028/evidence-h1-b7c7fb4a.json`，文件 SHA-256
  `4fc5729ef5e40f468b8966e35696a84e47b2de05e363d517293ac9e2f9823662`；schema 2.0、
  `mode=local`、`phase=final`、`conclusion=passed`。
- Verification snapshot：
  `5d761ba9f24dbbb2f9746bc99c4a5f292fb04390039605c57a11b1731dcfcafb`；Verifier
  `/root/task28_h1_verifier`，context
  `1faa4f460ad3f666398707c9570e34a17a9e19d6333c172629de4bb9b81295df`。
- 14/14 required checks passed；`MUT-V2-001`–`MUT-V2-005` 全部 killed；
  `unverified_scenarios: []`。单次 H1 mutation action digest
  `7dcbd975b1721e6e314e8955b012aa7b5b82dcdacade06b1d428214c3e39c0dc` 已且仅已消费一次。
- Unit：1079 passed、3 skipped；完整 regression 与 coverage：1560 passed、4 skipped；
  integration：450 passed、1 skipped；acceptance：9 passed。所有 skip 均为既有 Windows
  symlink 创建限制。
- Diff coverage 为 94%（95 个变更行中 90 个覆盖）；Ruff check、format check、mypy、
  AI Flow validate/scope 与 `git diff --check` 均通过。
- 独立实现审核 `REV-0056` 为 `APPROVE`，findings 为空，并绑定相同 subject、snapshot、规格、
  Policy 与 classification。

## 风险与未验证项

- 隔离 CI simulation 尚未执行；它需要在 code-approval attestation 形成后生成第二个精确 action，
  再取得用户单独批准。当前 code approval 不包含该授权。
- H2 两份 state 投影尚未发生；H1 本地 Gate 和 CI simulation/Gate 全部通过后才可进入 H2。
- H2 改变 subject 后必须重新取得第三个 single-use mutation action、完整 V2、独立实现审核、
  finalize、code approval 与本地 Gate；H1 证据不能替代 H2 merge readiness。
- 未执行或授权 push、merge、deploy、远程 CI、网络、凭据、付费调用或 task close。

## 审核问题

- V2 CI 是否在 runner 前严格校验 current local-final source，并只读重放已有 mutation artifact？
- Actor 派生、显式 actor 匹配、task 零写及 recorder/action/runner 零调用是否保持 fail closed？
- Gate 是否正确分层并合取 local-final 与 external CI 的各自事实，且未放宽 V0/V1/local V2？
- H1 是否只修改五个允许的业务路径且保持 13.3 pending？
- 当前批准是否明确限于本地只读 Gate，并保留后续两个独立 action approval 边界？

## 推荐结论

`APPROVE`（仅批准当前 H1 subject 进入本地只读 Gate；不授权隔离 CI simulation、H2、
targeted mutation、临时目录操作、push、merge、deploy、task close 或其他外部动作）。
