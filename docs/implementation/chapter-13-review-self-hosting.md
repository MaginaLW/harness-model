# Chapter 13：REVIEW / V2 自举与 CI Gate

当前权威进度是 Chapter 13.1、13.2 已完成，13.3 由 TASK-0028 推进中。13.3 的 H1
只实现 V2 CI attestation 与 Gate 分层、匹配 integration tests 和本说明；
`docs/superpowers/state/chapters/chapter-13.yaml` 与 overall state 在 H1 保持 13.3
`pending`。只有 H1 current V2、实现审核、code approval、隔离 CI simulation 和 Gate
都通过后，H2 才能投影 13.3 完成。13.4–13.6、四个 Chapter 13 exit checks、Chapter 13
和 Phase 02 均未完成。

## Chapter 13.2 已完成事实

TASK-0025 的最终 H2 closure 已完成，不再处于“implementation review 修正中”：

- subject：`7191ca4c9c0bc23b75af9599ebb381ed077aa081`；
- classification：`REVIEW / V2`，Policy `2.1.0`；
- 最终重试 action：
  `a9d4a2898b62772b0737e39399262cf2a8ca714b2f0427e3e2eb88a7e7941103`，已单次消费；
- final V2：14/14 required checks passed，`MUT-V2-001`–`MUT-V2-005` 按 manifest
  顺序全部 killed，`unverified_scenarios: []`；
- verification snapshot：
  `e95517a7be2758c2551b5c78479b0f1a3b1407082a845c9808e0af50e71ac134`；
- independent implementation review：`REV-0048 APPROVE`，context
  `63a0a3df4196b1cec9b2f79e5f0e21065c54acf990f8869b5bc2bc63eccfd6e7`；
- code approval：event 54；code-approval attestation commit：
  `b96e5f168a74a6450515dbda2b9006f503e3dc5f`；
- external merge ledger：event 55；governance commit：
  `8503660358c20a065a4d2101e682fb58654ba2c1`。

TASK-0025 的首个 H1 candidate、`REV-0045 REQUEST_CHANGES`、historical replay bundle、
失败的首次 H2 action 和 10 秒临时 Git timeout 都继续保存在 task-local 历史中。它们只证明
时序和 fail-closed 恢复，不能替代上述 final H2 binding，也不能跨 task、subject、spec、
Policy 或 classification 复用。

## TASK-0028 治理绑定

- base：`3f3ead9eeb3cc1039be58627994a3a0d58102534`；
- classification：`REVIEW / V2`；classification input：
  `28204d9e485e11ca0948982038798e99f8148512a491550e80f4ebeb1e14a75a`；
- frozen spec：
  `657bac588589c0fabb9c8d6a108ab9077cd101c9648f55d0d3f5e71299f06877`；
- active Policy：`2.1.0`，SHA-256
  `f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`；
- 初版设计审核 `REV-0053 REQUEST_CHANGES` 发现 CI V2 无 passing Gate 路径；`RF-001`
  经 scope/spec escalation、重新分类和冻结后以 revision 2 结构化解决；
- 当前设计审核为 `REV-0055 APPROVE`，context
  `0d3efee5c9ef2b73936729c5e6fecd88cc2e10756b7ff33823d83acff91e0e71`；
- 用户已批准上述 frozen spec 进入有界实现，但尚未批准任何 TASK-0028 targeted mutation、
  临时 worktree/run-directory 清理、push、merge 或远程动作。

actor label 只是 task-local 审计字符串，不是人员、模型或外部身份认证。Local V2 的
Implementer 与 Verifier 仍必须是不同的非空规范化字符串。

## REV-0053 发现的 CI 缺口

修复前，V2 `verify --ci` 把 targeted mutation 固定投影为
`MUTATION_EVIDENCE_MISSING`：CI 不会重新执行 mutation，这是正确边界，但也没有调用既有
public consumer 只读重放 current immutable artifact。同时，CI 输出是
`pre_implementation_review` evidence；Gate 若把 external CI evidence 当作唯一 V2 source，
会因为它没有绑定该 CI snapshot 的 implementation review 而拒绝。强行把 CI evidence 标为
`final` 会伪造不存在的 review，不能作为修复。

13.3 的最小修复采用双输入、fail-closed 语义：

1. task-local current local-final V2 evidence 提供 final phase、local verification snapshot、
   design/implementation review、code-approval source 和 current artifact identity；
2. external CI evidence 提供最新 attestation HEAD、governance-only 判定、重新执行的十四项
   required checks、CI snapshot、独立 verifier/context、current design review，以及通过
   public consumer 完成的 mutation artifact replay；
3. Gate 分别验证两侧。External pre evidence 不需要伪造 implementation review，但不能覆盖
   missing、stale、tampered 或 non-final local evidence；local final 也不能覆盖 CI 的失败、
   stale attestation 或 non-killed replay。

## V2 CI 只读 replay

V2 CI 在 runner 前读取 current `evidence.json`，只接受 `2.0 / V2 / local / final / passed`，
并验证 task/base/subject/spec/Policy/classification freshness、snapshot、设计/实现审核、独立
Verifier 和最小 context。CI actor 从该已验证 source 派生；调用者省略 `--actor` 是正常
workflow 路径，显式 actor 只能与 source 完全一致。

CI 仍重新运行当前 Policy 的普通 checks。Targeted-mutation check 只把 local-final evidence
交给 `consume_targeted_mutation_evidence`：public loader 重新验证 artifact 路径、canonical
digest、task/version binding、manifest、runner source、五项结果和日志摘要。CI 绝不调用
recorder、action consume/complete 或 mutation runner，也不写 task-local ledger、approval、
receipt、artifact、context 或 evidence。External evidence 只写经真实路径验证的 OS temp
run directory。

Source evidence 缺失、非 local/final/passed、freshness 或 snapshot 不匹配，显式 actor 不匹配，
artifact/projection/log/manifest 无效，或任一 mutant 非 killed，均在执行或 Gate 前 fail closed。
V0/V1 CI 和 local V2 collection/partial-check 语义保持不变。

## H1、CI simulation 与 H2

H1 业务改动只有两个 runtime seam、两个 integration test 文件和本说明。H1 subject sync 后，
必须生成绑定该 subject 的精确 `targeted_mutation_v2` action，并由用户单独批准 single-use
transaction。不同于 Implementer 的 Verifier 执行完整 14/14 V2；五项 mutant 全 killed且
无 unverified 后，独立 implementation review 绑定同一 snapshot，随后 finalize、code approval
和 local Gate。H1 final evidence 必须另存 immutable task-local snapshot，供后续投影引用。

H1 code-approval attestation 形成后，第二个独立 action 只授权一个精确 OS-temp worktree 与
一个精确 OS-temp CI run directory 的创建和清理。Simulation 固定 checkout 到 H1 attestation，
运行无 actor 的 V2 `verify --ci` 和 `gate --evidence`；预期十四项 checks、五项 killed replay、
attestation freshness 与 Gate 全部通过，源 task 目录逐字节不变。脱敏 receipt 不记录机器名、
本机用户名、绝对路径、完整日志或凭据。

只有上述 H1 与 CI facts 完整后，H2 才把 13.3 五步投影完成并指向 pending 13.4。H2 改变
subject，因此必须取得第三个 current single-use mutation action，重新运行完整 V2、独立实现
审核、finalize、code approval 和 local Gate。H1 证据只作为投影前提；H2 证据才决定最终
merge readiness。TASK-0028 不自动 close、merge 或 push。

## 定向复现与边界

实现层 focused 命令：

```powershell
python -m pytest tests/integration/test_verify_command.py -q
python -m pytest tests/integration/test_gate_command.py -q
python -m ruff check src/aiflow/verification_service.py src/aiflow/gate.py tests/integration/test_verify_command.py tests/integration/test_gate_command.py
python -m mypy src/aiflow/verification_service.py src/aiflow/gate.py
```

Chapter 13 自举回归：

```powershell
python -m pytest tests/acceptance/test_phase_02_self_hosting.py -q
python -m pytest tests/integration/test_phase_02_self_hosting.py -q
python -m pytest tests/e2e/test_phase_02_self_hosting_scenario.py -q
```

普通 pytest、local Gate 或设计批准都不授权 targeted mutation、临时目录清理或外部动作。
支持范围仍不扩展为跨平台 live Hook、全部客户端、自由 shell 解析、通用命令拦截、OS sandbox、
V3、模型路由或资源调度。恢复只能通过新的受治理 current subject 前向修正；历史 task-local
ledger、action、receipt、context、review 和 evidence 保持追加式。
