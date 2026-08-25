# Review Package

## 审核目标

确认 TASK-0015 在 subject `9d48321d825a09a299bd7df0e70b716b2b598430`
上的 Chapter 11.5 实现满足冻结规格：真实 local V2 只能消费当前 task、subject、
spec、Policy、classification 与权威 manifest 共同绑定的 targeted-mutation artifact；
五项结果必须完整、有序且全部为 `killed`，否则 verification、code approval 与 Gate
统一 fail closed。本审核也确认 V0/V1 不运行 mutation，且当前成功记录来自一次明确
批准、不可重用的 production collection。

## 背景

任务 base 为 `17ab98cf879cf913e91dfcdf69861b387eabf7ac`，路线为
`REVIEW + V2`。当前冻结规格 SHA-256 为
`59be2e15f5bf1b1d118bc63c7d05f864e5547717f062f64e8546fb0ef6b5cade`，
Policy SHA-256 为
`f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`，
classification input SHA-256 为
`a9cd100f35aae520fb178d07764ff927df34e0115101180910ad5efd69c40d2a`。

早期 action 历史保持不可变：`36fbb908…44ff6b` 未消费且已陈旧；
`165b0ba2…41dd33` 已消费但在 mutation 执行前因旧 subject/HEAD preflight 停止；
`afeaeaf1…196dcf` 已消费并真实发现 `MUT-V2-003` survived，因而 V2 正确失败。
随后仅隔离修正该 detector，形成当前 subject。最终 action
`ed3ae68b…2354dff` 被单次消费，产生通过的五项记录。最终 implementation review
`REV-0016` 绑定 context
`fd07f7c5b869a88471584af4f7952e8e9a9462a1219207a2001da62fc968ad78`，
两路独立只读审查均未发现 P0-P3 finding。

## 代码地图

- `src/aiflow/mutation_evidence.py`：action/receipt/ledger/launch 绑定、生产记录入口、
  public loader、canonical digest、manifest 与结构化日志重验，以及共享的 complete-killed
  consumer。
- `src/aiflow/mutation_runner.py`：固定五项 runner、detached task-owned worktree、封闭
  operator、subject 到 governance-attestation HEAD 的祖先关系校验和 cleanup 不变量。
- `src/aiflow/verification_service.py`：local V2 的唯一 production collection 调用图、
  pre-review evidence 与 runner-free finalization。
- `src/aiflow/approval.py` 与 `src/aiflow/gate.py`：复用同一 loader-backed consumer，
  不信任 evidence 内嵌 outcome。
- `.ai/schemas/evidence.schema.json`、`.ai/templates/evidence-v2.json` 与 contract fixture：
  封闭的 artifact identity、五项有序 projection 和 snapshot 绑定。
- unit、integration、acceptance 与 E2E tests：覆盖 all-killed、survived、unverified、
  missing、stale、tampered、duplicate、unknown、action 重放、V1 non-regression、
  approval/Gate 同源拒绝与 finalization 不启动 runner。
- `.ai/tasks/TASK-0015/`：冻结规格、分类、设计/实现审查、action 与 use receipts、
  verifier context、最终 evidence 和追加式事件历史。

## 语义变更

完整 local V2 现在先在 public recorder 内验证精确 single-use action approval，并在任何
runner 调用前以排他 receipt 和 consumed event 固化消费；runner 再独立重放 action、
receipt、ledger、launch claim、Git ancestry 和 governance-only 边界。固定 runner 完成后，
public loader 重算顶层 canonical digest 与逐项 log hashes，验证 task/base/subject/spec/
Policy/classification、manifest/runner source、五项 identity/order/raw facts/outcomes、
uncovered 集合及 main-tree unchanged。verification 只投影 loader 已接受的结果。

`consume_targeted_mutation_evidence` 是 verification、code approval 和 Gate 的共同事实源。
任一缺失、陈旧、篡改、重复、未知、非 killed、日志不一致或 cleanup/主树失败都不会被
内嵌 projection 掩盖。V2 pre-review evidence 在结构化 implementation review 后通过
runner-free `--finalize` 封存 review ref；V0/V1 的检查集合和执行行为保持不变。

## 风险

- task-local mutation evidence 与结构化日志按设计被 `.gitignore` 排除；可提交 receipt
  是本机 artifact 的 hash index，不声明跨 checkout 或机器可用。
- independent verifier 使用不同 actor label 并由上下文绑定，但本地工具不认证外部
  身份；该限制已在 evidence 的 tool summary 中明确。
- Windows 主机无法创建真实 symlink 的若干测试被 skip；路径 containment、解析边界
  与拒绝行为仍由可运行的词法/模拟测试覆盖。
- 历史失败和 survived artifacts、已消费 action 与 launch claim 必须永久保留，不能
  清理或重用；任何新的真实 mutation transaction 都需要新的精确 action approval。
- Chapter 11 的最终完成/退出状态投影、integration merge、push、task close 与后续章节
  启动尚未执行；它们不由本代码批准授权，并须遵循各自治理边界。

## 证据

- 已验证：final local V2 evidence 为 `passed`，phase 为 `final`，14/14 required checks
  全部通过，`unverified_scenarios` 为空；verification snapshot SHA-256 为
  `6b96ff977cfb491f10dcfc083f4366d1299b778254a1d778b1b7a45248e3c7ec`。
- 已验证：unit 为 `628 passed, 3 skipped`；全量 regression 与 branch coverage collection
  均为 `948 passed, 4 skipped`；integration 为 `305 passed, 1 skipped`；acceptance 为
  `7 passed`；changed-line coverage 为 `91%`（429/467），超过 90% 门槛。Ruff、format、
  mypy、contract、scope 与 smoke checks 同时通过。
- 已验证：唯一成功 record
  `MUTRUN-20260825T165450Z-1b35a08a31b37fce` 的 canonical SHA-256 为
  `483af46c5f517952be8b0382737d04bcb57ff7a11db6910ba886a11c1429e312`；
  `MUT-V2-001` 至 `MUT-V2-005` 均为 baseline exit `0`、mutant exit `1`、
  `killed`、未 timeout，`uncovered_mutation_ids` 为空且 `main_tree_unchanged=true`。
- 已验证：action `ed3ae68b…2354dff` 的用户批准、sequence 121 consumed event、
  non-reusable receipt、exclusive launch claim 与 recorded result 绑定一致；Git worktree
  registry 中没有 mutation worktree 残留。
- 已验证：设计审查 `REV-0015` 与实现审查 `REV-0016` 均为 `APPROVE` 且无 findings；
  final evidence 同时绑定两者 context。
- 未验证且未授权：integration merge、push、deploy、delete、package publish、凭据或
  付费外部调用、task close，以及 Chapter 11 最终状态投影。

## 审核问题

- production collection 是否只能由当前绑定的精确 single-use action 启动一次？
- public loader 与 shared consumer 是否对 artifact、日志、manifest、顺序、digest 和
  currentness 做完整重验，并在任一非全 killed 情况下 fail closed？
- verification、code approval 与 Gate 是否确实共享 consumer，没有信任内嵌 outcome
  的旁路？
- V2 finalization 是否只绑定当前 implementation review，且绝不再次解析或执行 runner？
- V0/V1 non-regression、范围、质量门和当前 governance-only worktree 是否足以进入代码
  批准门，同时保持 merge/close/状态投影为未授权后续步骤？

## 推荐结论

`APPROVE`。当前 subject 的 final V2 evidence、五项真实 mutation 结果与两路独立审查
一致且通过；未发现阻止代码批准的遗留 P0-P3 问题。本结论不授权 merge、push、deploy、
delete、task close、Chapter 11 最终状态投影或任何新的 mutation transaction。
