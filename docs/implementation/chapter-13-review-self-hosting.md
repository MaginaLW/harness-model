# Chapter 13：REVIEW / V2 自举与 CI Gate

当前权威投影是 Chapter 13.1–13.6、四项 exit checks、Chapter 13 与 Phase 02 均已完成。
完成依据由精确绑定原 subject/attestation 的 TASK-0025/TASK-0028 REVIEW + V2 + CI/Gate
历史和阶段结束时的当前整库质量基线共同组成。TASK-0028 的后续 H2 投影改变了 subject，
所以它当前仍正确显示 stale approval/evidence 与 `merge_readiness: reverification_required`；
阶段完成没有改写 task ledger，也不是 TASK-0028 当前 merge approval。

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
- 用户已批准上述 frozen spec 进入有界实现；H1 subject
  `b7c7fb4a0bab1a2a4b0d9a59edfe237839f3779d` 的 single-use targeted mutation action
  `7dcbd975b1721e6e314e8955b012aa7b5b82dcdacade06b1d428214c3e39c0dc` 已消费；
- H1 final evidence 文件 SHA-256 为
  `4fc5729ef5e40f468b8966e35696a84e47b2de05e363d517293ac9e2f9823662`，
  `REV-0056 APPROVE` 后的 code-approval attestation 为
  `f35d3094a8385806abff2996691e5224bedb00e2`；
- 成功的 CI-003 action
  `5a3071cd2e446dea89d5b8acb5c6c26399cf69a4ba141da0f3995706bfa28020` 已消费；
  H2 的第三个 current-subject mutation action 尚未生成或批准，push、merge、deploy、close
  和远程动作也未获授权。

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

H1 已在 subject `b7c7fb4a0bab1a2a4b0d9a59edfe237839f3779d` 上闭环。独立 Verifier
`/root/task28_h1_verifier` 的 local-final V2 为 14/14 passed；`MUT-V2-001`–`005` 按
manifest 顺序全部 killed，`unverified_scenarios: []`，local verification snapshot 为
`5d761ba9f24dbbb2f9746bc99c4a5f292fb04390039605c57a11b1731dcfcafb`。Mutation artifact
digest 为 `2028bd7cbdeebd26033e3d8dd36728e87362f71f638f2a89087425f73da8530e`；
`REV-0056 APPROVE` 绑定 context
`287db9c8c642a0e65a79f32392f270b25fdd7abd7a03a500d04851781196cfb1`。Final evidence、
code approval 和 local Gate 均通过，code-approval evidence digest 为
`a2589f30cdbf763fd930d924b2829f7ba2158ba4b4dd0841760dfd4af09e6d3b`。

CI-003 随后在 governance audit head
`fd32681ea39418f4176d72738cbe7dc8b8fca5ca` 上成功。Receipt
`.ai/tasks/TASK-0028/action-use-5a3071cd2e446dea89d5b8acb5c6c26399cf69a4ba141da0f3995706bfa28020.md`
的文件 SHA-256 为 `3d420bb8ec5845287744b6e19b1890997dba58fdfab158803a84a0bcf86eff94`。
CI evidence 为 14/14 passed、五项 immutable mutation replay 全 killed、零 unverified，
attestation 为 governance-only，CI snapshot 为
`95802c483238bb2eab86ee1528b8c736134bcd44b61a5a560dd27a5893ed5b53`，external evidence
文件 SHA-256 为 `55e957e41c32009feeb04e3781323d12f16b48d84b148ec457870d87bcdffa13`。
External-evidence Gate passed，规范化输出 SHA-256 为
`962262ea382a517a2fa46bed825c7659a3a33547f9018aa4b1961e247ce1fec3`。Checkout 明确使用
LF，源 task、源工作树与 refs 保持不变，精确 worktree 和 run directory 均已清理。较早失败和
cleanup receipts 继续保留在 task-local 历史中；它们不替代成功的 CI-003。

上述事实是 13.3 当时完成投影的时序前提。H2 subject 若要成为 TASK-0028 的当前 merge
candidate，仍必须取得第三个、绑定该 subject 的 single-use mutation action，重新运行完整
V2、独立实现审核、finalize、code approval 和 local Gate；不要求再次执行 CI simulation。
Chapter 13 后续 13.4–13.6 在 active bootstrap 例外下完成本仓库的测试、索引、文档和状态
基线，不以 TASK-0028 为 merge candidate，因此不伪造这条新 transaction。H1 evidence/review/
approval/CI receipt 仍不能充当 H2 merge readiness，TASK-0028 也未自动 close、merge 或 push。

## 13.4 负向 E2E

`tests/e2e/test_phase_02_negative_self_hosting.py` 从公开 CLI、service 和 Gate 边界覆盖五个
fail-closed 场景：

- V2 verifier 与 implementer 相同，或 actor 规范化后为空，均在 plan/runner 前拒绝；
- fixture 生成的 immutable mutation artifact 中存在一个真实 `survived` result 时，public CI
  consumer 返回 `MUTATION_EVIDENCE_NOT_KILLED`，Gate 返回
  `GATE_V2_MUTATION_NOT_KILLED`；current binding、manifest/source digest 与 review freshness
  的完整组合边界继续由既有 integration/self-hosting suite 覆盖；
- `scope_out_of_bounds` observation 只经公开 `apply_observation` 记录 observation、escalation 和
  `ESCALATED` 状态，随后 `begin` 仍被拒绝；
- 同一 current context 中较新的 `REQUEST_CHANGES` 覆盖较早的 `APPROVE`，finalize 返回
  `REVIEW_OUTCOME_NOT_APPROVABLE`，code approval 不产生新记录；
- 上述陈旧审核继续由只读 Gate 投影为 `GATE_V2_EVIDENCE_NOT_FINAL` 和
  `GATE_V2_REVIEW_STALE`，不会被旧 evidence 或旧 approval 掩盖。

测试在每个拒绝点前后比较 task-local 文件字节或对应 ledger/approval 集合；CI replay 还确认
source task、refs 和 external evidence 均未被失败路径改写。测试只构造 task-local fixture，未
消费真实 action、未执行外部命令，也不扩大 live Hook、外部身份认证或 OS sandbox 的支持范围。

## 13.5–13.6 验收与阶段收口

[阶段二验收矩阵](phase-02-acceptance-matrix.md)固定六项输入及其实现、测试、artifact、完整
commit/hash、重放 argv、结果和限制；[证据索引](phase-02-evidence-index.md)另外固定 TASK-0028
H1/CI-003 与 TASK-0025 的历史 binding，并由 traceability 测试核对路径、hash 和 current
TASK-0028 subject。最终 pytest、Ruff、format、mypy、branch coverage、diff-cover 与历史
attestation Gate 结果记录在[阶段二验收报告](phase-02-acceptance-report.md)。

README、CHANGELOG、Quickstart、Recovery 和人工状态投影已同步完成；package 仍为本地
`0.1.0`，未 tag 或发布。[阶段三进入输入](phase-03-entry-inputs.md)只记录可用事实和三个仍未
满足的门槛，Phase 3 保持 `not_started`。bootstrap 标记未移除；除历史 action 批准和本轮
范围明确的精确 task-owned worktree/OS-temp cleanup 外，未删除仓库或业务数据，也没有实现
或授权 V3、模型路由、资源调度、push、merge、deploy、凭据导出或付费调用。

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
python -m pytest tests/e2e/test_phase_02_negative_self_hosting.py -q
```

普通 pytest、local Gate 或设计批准都不授权 targeted mutation、临时目录清理或外部动作。
支持范围仍不扩展为跨平台 live Hook、全部客户端、自由 shell 解析、通用命令拦截、OS sandbox、
V3、模型路由或资源调度。恢复只能通过新的受治理 current subject 前向修正；历史 task-local
ledger、action、receipt、context、review 和 evidence 保持追加式。
