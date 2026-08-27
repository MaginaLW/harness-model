# Review Package

## 审核目标

确认 TASK-0025 在 current subject
`7191ca4c9c0bc23b75af9599ebb381ed077aa081` 上完成 Chapter 13.2 的真实、隔离本地
`REVIEW / V2` 自举试点：H1 新增离线 acceptance、integration、E2E 测试与实施说明，H2
只投影 13.2 completed；current subject 已重新取得完整 V2、独立 implementation review 与
final evidence。同时确认 13.3、四个 Chapter 13 exit checks、Chapter 13 和 Phase 02 均未完成，
本批准只允许进入本地只读 Gate，不授权任何远程动作。

## 背景

任务 base 为 `7c0bfd807954df8be934d99c7e0a565e4fa2ddcb`，确定性分类为
`REVIEW / V2`。classification input SHA-256 为
`2d6cc68d05c4b89d0749700f71ddd98c1c3336cf7d227d59425af802c33e4bd4`，冻结规格
SHA-256 为 `04f951e922a1183b750111b101b9e47532c9bd9261225c289e6faa5237262318`，
active Policy SHA-256 为
`f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`。
独立设计审核 `REV-0046` / context
`cbdf00194a21d792a13f7b14c75298b1cf1bff67a479feabe5a413c1876dc599` 为 APPROVE，
用户按相同绑定重新批准 spec。

H1 corrected subject `f08b0b8cfc3c6b3f81ff4ddba0dc68cb6b2b3694` 完成五个非状态业务文件，
通过 14/14 V2、五项 targeted mutation 与独立 `REV-0047`，其 final evidence 已固化为
`.ai/tasks/TASK-0025/evidence-h1-f08b0b8c.json`。H2 随后只修改两份 state 文件，形成 current
subject `7191ca4c9c0bc23b75af9599ebb381ed077aa081`；H1 action、evidence 和 review 只作为
投影时序前提，不作为 current H2 通过事实。

首次 H2 action `f3b1f405...dad1ff` 被单次消费，五项 mutant 均 killed，但 integration 因
pytest 临时仓库中的 `git symbolic-ref` 超过固定 10 秒而失败，authoritative evidence 因此
正确记录为 failed。失败 evidence、receipt 与诊断记录均已保留；随后精确失败用例的独立、
非权威诊断通过，但没有追溯修改失败结论。新的 retry action
`a9d4a2898b62772b0737e39399262cf2a8ca714b2f0427e3e2eb88a7e7941103` 经用户单独批准并
恰好消费一次，产生 current passing V2。首次失败 action 与 mutation artifact 仅为历史，未被
current evidence 复用。

## 代码地图

- `tests/acceptance/__init__.py`：空 package marker，仅解决默认 pytest import mode 下的同名
  模块收集冲突。
- `tests/acceptance/test_phase_02_self_hosting.py`：从公开 contract/CLI 视角验证 current
  REVIEW/V2 bindings、十四项 required checks 与不可复用旧证据。
- `tests/integration/test_phase_02_self_hosting.py`：覆盖双阶段 review、spec/code approval、
  evidence finalization、Gate 前置事实及支持范围内 Hook/CLI/CI decision parity。
- `tests/e2e/test_phase_02_self_hosting_scenario.py`：分离真实 historical replay、明确标记的
  modeled non-authoritative positive 与 current fail-closed scenarios。
- `docs/implementation/chapter-13-review-self-hosting.md`：记录 H1/H2 时序、复现、证据、
  mutation receipt、限制与恢复路径。
- `docs/superpowers/state/chapters/chapter-13.yaml`：只完成 13.2 五步，保留 13.3–13.6 和四个
  exit checks pending。
- `docs/superpowers/state/overall.yaml`：将 tracking 指向 `chapter-13 / 13.3 / null`，完成计数
  更新为 12 chapters、73 tasks、388 steps、20 exit checks 和 17 evidence items，并只追加
  `EVT-OVERALL-CH13-13.2-COMPLETE-001`。
- `.ai/tasks/TASK-0025/**`：保存 classification、spec、批准、双阶段 review、H1 immutable
  evidence、两次 H2 action/receipt、失败与重试证据、verifier contexts 和 append-only events。

## 语义变更

仓库现在具有一个可离线重放的 Phase 02 REVIEW/V2 自举试点。测试内 historical replay 与
modeled positive 只证明历史事实或 contract 组合语义；它们不是 current readiness。只有 outer
AI Flow 对 current subject 生成的完整 V2、独立 implementation review、code approval 和 Gate
共同形成当前门禁事实。

Chapter 13.2 五步均为 completed；13.3–13.6 和四个 exit checks 仍为 pending，Chapter 13 与
overall/Phase 02 保持 in_progress。当前任务没有执行 CI simulation，没有完成 13.3，也没有
宣称 Chapter 13 或 Phase 02 完成。

## 风险

- verifier/implementer actor 是可审计字符串标签，不是外部身份认证。
- task-local mutation artifact 与日志受本地执行环境约束；可提交 receipt 提供摘要和引用，
  不扩大为跨机器可用保证。
- 当前 Windows host 的四个既有 symlink skips 不证明 Linux/macOS live Hooks 或所有客户端。
- Hook parity 不扩展为自由 shell 解析、通用命令拦截或操作系统安全沙箱。
- 首次 H2 integration timeout 的失败证据永久保留；诊断通过不替代 current retry V2，retry
  action 也已消费且不可复用。
- 未执行或授权 push、merge、deploy、publish、凭据、网络、付费调用或其他远程动作。

## 证据

- 已验证：final V2 evidence 为 `passed` / `final`，canonical SHA-256 为
  `4c5c8806a1a31977bb0ed0848294f30bf87ab36109f8edd9cb3bd7779b3f32e3`；文件字节
  SHA-256 为 `a54d7443edaa55a26f6da36f2ab53bb394f993083629fa1383c159efb6f99dc8`。
- verification snapshot SHA-256 为
  `e95517a7be2758c2551b5c78479b0f1a3b1407082a845c9808e0af50e71ac134`；verifier 为
  `/root/task25_h2_verifier_r2`，context 为
  `760023540a0560e312e9136945bb7171560a4b776a0c626eb106e933d45b7c03`。
- 14/14 required checks passed，`unverified_scenarios: []`。unit 为 1079 passed、3 skipped；
  full regression 与 coverage collection 均为 1527 passed、4 skipped；acceptance 为 9 passed；
  integration 为 417 passed、1 skipped。skip 均为既有 Windows symlink 创建限制。
- diff-cover 对本次测试/文档/state diff 报告 no executable coverage lines sentinel；未宣称数值
  或 100% coverage。Ruff、format、mypy、contract、scope 与 smoke 均通过。
- current mutation evidence SHA-256 为
  `bcd31de3becb50818db6828b4f8e90986ae52aefb618fd5a814f7295838cd483`；
  `MUT-V2-001` 至 `MUT-V2-005` 按 manifest 顺序全部 killed，uncovered 为空。
- 独立 implementation review `REV-0048` / context
  `63a0a3df4196b1cec9b2f79e5f0e21065c54acf990f8869b5bc2bc63eccfd6e7` 为 APPROVE，
  findings 为空；final evidence 同时绑定 design `REV-0046` 与 implementation `REV-0048`。
- 未验证：13.3 CI simulation、Chapter 13 exit checks、Chapter 13/Phase 02 completion、跨平台
  live Hooks、自由 shell 拦截、操作系统沙箱以及任何 push、merge、deploy 或其他远程动作。

## 审核问题

- 七个业务路径是否完整实现冻结规格，且 H1/H2 分阶段范围没有扩展到 runtime、Policy、
  schemas、manifest 或 Hooks？
- current H2 evidence 是否来自新的完整 V2 与新 action，而非 H1 或首次失败 H2 artifact？
- 13.2/13.3、counts、tracking、history、chapter evidence 与 H1 immutable ref/hash 是否一致？
- historical replay、modeled positive、actor、Hook、platform 与 sandbox 限制是否如实保留？
- code approval 与 Gate 是否精确绑定 current subject、canonical evidence、REV-0048 context 和
  active Policy，同时保持 13.3、CI simulation 和全部远程动作未授权？

## 推荐结论

`APPROVE`（仅进入本地只读 Gate；不授权 push、merge、deploy、task close、13.3 投影或任何
其他远程动作）。
