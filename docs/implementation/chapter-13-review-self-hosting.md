# Chapter 13.2：REVIEW / V2 自举试点

状态：H1 实施中。本说明描述 TASK-0025 已冻结的本地试点契约和计划；它不记录尚未发生的
subject、action、mutation、evidence、implementation review、code approval、Gate 或 merge 事实。

## 当前治理绑定

- base 与当前 subject 均为 `7c0bfd807954df8be934d99c7e0a565e4fa2ddcb`。
- 分类为 `REVIEW / V2`；classification input 为
  `36500db4687910d92260c80b48ede24ce9a740ae7f5f4bde5cb77f5e29879e50`。
- active Policy 为 `2.1.0`，SHA-256 为
  `f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`。
- frozen spec SHA-256 为
  `625ac850cfbfedc05c5af636b4f274faacc8325aa806caee7f47f9ec16bb5a4c`。
- 独立设计审核为 `REV-0044 APPROVE`，context 为
  `1833cc40e1f5a4bdd5e7ce59e2233965325dce8b30ecf1c94ddfa45586b790e7`。

actor label 只是 task-local 字符串，不是人员或外部身份认证；V2 仍要求当前 Implementer 和
Verifier 均非空且不同。

## H1 / H2 时序

H1 只新增空的 acceptance package marker、acceptance、integration、E2E 三份离线覆盖以及
本说明。提交 H1 的五份业务文件并 sync 后，独立 Verifier 才能为 H1 current subject 生成
pre-review V2 evidence。该过程须先有
精确、current、single-use 的 targeted-mutation action approval；固定 manifest 的五项 mutant
按既有 runner 顺序仅各运行一次 baseline detector 与 mutant detector。通过的 pre evidence、
同一 snapshot 的独立 implementation review 与 finalize 才形成 H1 final evidence；其不可变
task-local snapshot 必须另存，不能由 H2 覆盖。

H2 仅在上述 H1 时序事实完整后投影 Chapter 13.2 state。投影使 subject 改变，因此 H1 的
action、receipt、evidence 和 review 只能作为时序前提，不能作为 H2 current 通过。H2 必须
重新 sync、重新生成 action、重新获得 single-use approval、重新执行 V2、独立审核和 finalize；
之后才可请求 code approval 并运行本地只读 Gate。权威的后续事实只写入 TASK-0025 task-local
artifacts，不由本文代填。

## 离线复现与边界

计划中的 focused 命令是：

```powershell
python -m pytest tests/acceptance/test_phase_02_self_hosting.py -q
python -m pytest tests/integration/test_phase_02_self_hosting.py -q
python -m pytest tests/acceptance/test_phase_02_self_hosting.py tests/integration/test_phase_02_self_hosting.py -q
python -m pytest tests/e2e/test_phase_02_self_hosting_scenario.py -q
python -m aiflow verify TASK-0025 --actor <independent-verifier>
```

以上四个 pytest 命令只组装或验证公开 contract/service facts：正向闭环、相同或空 actor、survived/missing/
unexecuted mutant、scope overrun，以及陈旧或篡改的 review、evidence、snapshot 和 CI attestation
均须 fail closed。它们不创建 action、不启动 mutation runner、不运行 Hook 描述的动作，也不做
网络、推送、合并、部署、凭据或付费调用。

支持范围内的 Hook、CLI 和 CI parity 比较同一 decision fields，不要求 source-sensitive digest、
ledger effect、event metadata、JSON bytes 或文案相同。该限定不扩展为跨平台 live Hook、全部客户
端、自由 shell 解析、通用命令拦截或 OS sandbox。恢复通过新的受治理 current subject 前向修正；
历史 task-local 账本、action、receipt、context、review 和 evidence 均保持追加式。
