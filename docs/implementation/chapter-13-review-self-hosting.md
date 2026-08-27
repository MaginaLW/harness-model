# Chapter 13.2：REVIEW / V2 自举试点

状态：H1 implementation review 修正中。REV-0045 已对首个 H1 candidate 请求修改；该次
single-use action、mutation、pre-review evidence 和审核结论均作为历史事实保留，不得重用为
修正后 subject 的 current 证据。循环边界已由修订规格拆成 historical replay、
`modeled_non_authoritative` contract model 和测试外层 authoritative closure；修订设计审核
`REV-0046 r0001` 已通过，但修正后 subject 尚未取得新的 V2、implementation review、code
approval 或 Gate。本说明同时给出自引用 subject 和后续 task-local artifact 的确定性解析规则，
避免通过改写本文中的 commit 字面量不断制造新 subject。

## 当前治理绑定

- base 为 `7c0bfd807954df8be934d99c7e0a565e4fa2ddcb`。
- 修正后 current subject 是包含本说明、空 package marker 和三份测试的提交，并以
  `.ai/tasks/TASK-0025/task.yaml` 的 `subject_commit` 及相应
  `subject_commit_synchronized` event 为唯一权威值。本文不嵌入该自引用提交的字面量；否则
  每次填写字面量都会再次改变被填写的提交。
- 分类为 `REVIEW / V2`；classification input 为
  `2d6cc68d05c4b89d0749700f71ddd98c1c3336cf7d227d59425af802c33e4bd4`。
- active Policy 为 `2.1.0`，SHA-256 为
  `f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`。
- frozen spec SHA-256 为
  `04f951e922a1183b750111b101b9e47532c9bd9261225c289e6faa5237262318`。
- 独立设计审核为 `REV-0046 r0001 APPROVE`，context 为
  `cbdf00194a21d792a13f7b14c75298b1cf1bff67a479feabe5a413c1876dc599`；用户已基于该
  context 批准修订规格继续本地实现，但未批准 targeted mutation 或远程操作。

actor label 只是 task-local 字符串，不是人员或外部身份认证；V2 仍要求当前 Implementer 和
Verifier 均非空且不同。

## 已执行的 H1 审核尝试

首个 H1 candidate 是 `fe30565e669aa047088b0c25c085effeb2b4bdbc`，其事实如下：

- single-use action SHA-256 为
  `9740af8fafb53760e829f94fd3c34d252a742fd42f2928e16272f32ee91d2cfa`；receipt 为
  `.ai/tasks/TASK-0025/action-use-9740af8fafb53760e829f94fd3c34d252a742fd42f2928e16272f32ee91d2cfa.md`，
  状态为 `recorded`，不可重用。
- 独立 Verifier 为 `/root/task25_h1_verifier`；verifier context 为
  `.ai/tasks/TASK-0025/verifier-contexts/0ecbe5fba9605ed6906e9bab2ab939e4bd004584f139d49da31ac4807673e8fd.json`。
- pre-review V2 evidence 在提交 `ef1f32d42b935ef2f7d8acfdc805a95399b33317` 的
  `.ai/tasks/TASK-0025/evidence.json` 中；snapshot 为
  `4ac2f36d103f05d6a3c9b4e3666b8b0dfc81503d3affdc0b18827e93858994b2`，14/14 checks passed，
  `unverified_scenarios: []`。
- targeted-mutation evidence ref 为
  `.ai/tasks/TASK-0025/logs/MUTRUN-20260827T123628Z-5dec129d8c0ead69/targeted-mutation/evidence.json`，
  canonical SHA-256 为 `eea607ff7d518f9f72118398396c6e16da193de7fa94987ebd54c749935a6016`；
  `MUT-V2-001`–`MUT-V2-005` 均为 `killed`。
- 独立 implementation review 为 `REV-0045 r0001 REQUEST_CHANGES`，context 为
  `69d6b4302b69e7ee3d003aadae58a9a90b3a91c6c43babc1ddb4b97e7fd158ca`，绑定上述 snapshot。
- versioned replay bundle manifest 为
  `.ai/tasks/TASK-0025/historical-snapshots/h1-fe30565/manifest.json`，包含 20 个逐文件哈希锁定的
  task-local 文件和 62 个 source-commit non-task input 摘要；bundle SHA-256 为
  `4076b379a431e45a831a591efd2586492b955acf3c6e9b237232ccb720c26580`。bundle 内容提交为
  `51eadb142151f69ac50c4248110275a02b83b51f`；为避免自引用，后续
  `.ai/tasks/TASK-0025/historical-snapshot-h1-fe30565-record.md` 在提交
  `dacae9caf1691f3d62cb0b5465a2f672602cbc51` 中绑定该内容提交与摘要。

因此该 candidate 不是 final H1，也不能支持 H2 投影、code approval 或 Gate。修正后 current
subject 必须使用新的 action 和完整 V2；上列 receipt、evidence 和 review 只证明历史时序。

E2E historical replay 只在 pytest-owned 临时目录执行本地 clone，将临时 clone 的本地 `main`
置于 `ef1f32d42b935ef2f7d8acfdc805a95399b33317`，验证 source commit、branch、bundle、20 个文件
与 62 个 non-task input 摘要后才覆盖 exact historical paths。它通过 public loader/consumer
重放 mutation，通过 public review assessment 得到 `REVIEW_OUTCOME_NOT_APPROVABLE`；不得对
`REV-0045 REQUEST_CHANGES` 调用 finalize，也不得混入外层 current TASK-0025 task-local 文件。

## H1 / H2 时序

H1 只新增空的 acceptance package marker、acceptance、integration、E2E 三份离线覆盖以及
本说明。提交 H1 的五份业务文件并 sync 后，独立 Verifier 才能为 H1 current subject 生成
pre-review V2 evidence。该过程须先有精确、current、single-use 的 targeted-mutation action
approval；旧 action digest `9740af8f…d2cfa` 已消费，绝不复用。固定 manifest 的五项 mutant
按既有 runner 顺序仅各运行一次 baseline detector 与 mutant detector。首次完整 V2 的
regression/E2E 早于该次 mutation collection，测试内只能重放上述历史 bundle 或组装明确标记
的 contract model，不能预造 current artifact。通过的 pre evidence、
同一 snapshot 的独立 implementation review 与 finalize 才形成 H1 final evidence；其不可变
task-local snapshot 必须另存，不能由 H2 覆盖。

H2 仅在上述 H1 时序事实完整后投影 Chapter 13.2 state。投影使 subject 改变，因此 H1 的
action、receipt、evidence 和 review 只能作为时序前提，不能作为 H2 current 通过。H2 必须
重新 sync、重新生成 action、重新获得 single-use approval、重新执行 V2、独立审核和 finalize；
之后才可请求 code approval 并运行本地只读 Gate。

修正后 H1 的 exact receipt 取自最新 `action_status: consumed` 的 task event；current evidence
固定为 `.ai/tasks/TASK-0025/evidence.json`，其 `verifier_context_sha256` 解析为
`.ai/tasks/TASK-0025/verifier-contexts/<sha256>.json`，其 `targeted_mutation.evidence_ref` 解析为
不可变 mutation artifact。finalize 后必须另存
`.ai/tasks/TASK-0025/evidence-h1-<subject-prefix>.json`，其中 `review_refs.implementation` 是
current implementation review binding。上述 task-local 引用和哈希是本文记录的权威后续
事实；不得用自然语言、旧 candidate 或可覆盖的 pre-review 文件替代。

测试内 `modeled_non_authoritative` 正向使用当前 TASK-0025 的 task、分类、Policy、冻结规格和
`REV-0046` design binding，并通过 public contract/evidence/Gate API 证明 APPROVE/final/Gate
组合语义。它不读取或生成 current mutation artifact，不写入严格 evidence schema 的未知字段，
也不是 current evidence、approval、review 或 readiness。唯一权威闭环始终是测试外层对 sync 后
current subject 实际生成的 V2 evidence、独立 implementation review、code approval 与 Gate。

## 离线复现与边界

focused 复现命令是：

```powershell
python -m pytest tests/acceptance/test_phase_02_self_hosting.py -q
python -m pytest tests/integration/test_phase_02_self_hosting.py -q
python -m pytest tests/acceptance/test_phase_02_self_hosting.py tests/integration/test_phase_02_self_hosting.py -q
python -m pytest tests/e2e/test_phase_02_self_hosting_scenario.py -q
```

以上四个 pytest 命令只组装或验证公开 contract/service facts：正向闭环、相同或空 actor、survived/missing/
unexecuted mutant、scope overrun，以及陈旧或篡改的 review、evidence、snapshot 和 CI attestation
均须 fail closed。它们不创建 action、不启动 mutation runner、不运行 Hook 描述的动作，也不做
网络、推送、合并、部署、凭据或付费调用。

外层权威复现命令为 `python -m aiflow verify TASK-0025 --actor <independent-verifier>`；只有在
业务提交、subject sync、精确 action file 和新的 single-use action approval 全部完成后才能运行。
普通 pytest 通过不构成该授权，也不替代 V2 evidence。

支持范围内的 Hook、CLI 和 CI parity 比较同一 decision fields，不要求 source-sensitive digest、
ledger effect、event metadata、JSON bytes 或文案相同。该限定不扩展为跨平台 live Hook、全部客户
端、自由 shell 解析、通用命令拦截或 OS sandbox。恢复通过新的受治理 current subject 前向修正；
历史 task-local 账本、action、receipt、context、review 和 evidence 均保持追加式。
