# Review Package

## 审核目标

审核 TASK-0130 当前 subject 94afbe32a599cfc66e46a1327c8df8307279d4e8 的完整 Node V0/V1 实现、3000 秒共享 pytest 预算和跨平台 ctypes 类型边界修复。真实 base 为无 Node 实现的 a05037749cb9f9b301e761d77cfb3b3f54c1c9f0。

## 背景

所有者明确选择 3000 秒并要求收尾。旧 TASK-0128/0129、旧失败、已消耗动作和旧批准完整保留，均不提供当前版本的通过或授权。当前范围只交付源仓 Node 本地 V0/V1；installed V2、Node CI、真实 agent-bridge 采用及 V2 归因扩张不在本轮实施范围。

## 代码地图

完整范围以 task.yaml 为准：Node 执行/材料/Job/coverage，公共 evidence/review/approval/Gate 消费者，contracts/state/policy/Git 查询，以及初始化、验证预算和对应测试。全部 Node 差异始终在真实 base..subject 及覆盖率分母内。

## 语义变更

共享完整 Native pytest 固定预算由 1200 改为 3000 秒，八处 Policy 预算同步；其他超时、14 checks、85% 总覆盖率、90% diff coverage 和五个实际固定变异不变。Policy label 仍为 2.6.0，canonical SHA 已改变，新引擎拒绝旧 1200 配置，升级不自动迁移目标 Policy。

最新修复只把两个源文件中的三行四次 Windows 专用 ctypes 属性访问改为无默认值 getattr。原平台 guard、API、调用参数、异常传播和 FFI 签名保持；将四 lookup 逆归一后，两份完整 AST 与旧候选相同。没有新增 ignore、类型配置或门禁变更。

## 风险

RF-022 medium 仍是实际当前 PR head required CI 硬条件。首轮 PR143 的覆盖率通过但 Ubuntu mypy 失败，不得据此合并。RF-026 medium 的类型修复已独立 slice APPROVE，尚须新候选完整验证与 CI。历史通用进程清理 UNKNOWN 保留，不宣称已认证。Node 的受控进程边界不提供恶意同用户沙箱。

## 证据

历史失败原件与当前结果分开：0ff2 的完整 Native 为 6 failed、5663 passed、5 skipped，原始 SHA433bde0d4fcea8ea0a856d9985da783361dda2b73a3f5d818494912472af60f3；修正 fixture 实参后，e444 完整 Native 为 5669 passed、5 skipped、1259.63 秒，14 checks 和五个实际变异通过，旧 final SHAf9a9cf8d77b02c64310435ec7de3dd0805fa84de9ac237856df05ee5bdfbc9da 已另存原件。它们不转移给新 94af 候选。

PR143 首轮真实 head e3d010a 的 run41278501102：5633 passed、41 skipped、534.45 秒；两域 85 总覆盖率、core diff2560/2825=90.619469%、Ruff/format 通过，Ubuntu mypy 最后四处 attr-defined 失败。原始日志 logs/bootstrap/ci-pr143-run41278501102.log 保留。

已验证：新三行修复 Linux/default mypy 各 60 文件通过，Ruff/format/whitespace 通过；47 个其他生产源和三个测试字节不变。受限环境三模块为 334 pass 加一个未改的旧进程树终止用例失败；诊断真实 taskkill128/operation not supported 保留，不推断完整机制。root 按当前工具批准的执行权限、同一原用例和最小环境，实际 1 pass/4.27 秒；不伪称单轮全部三模块通过。

新 subject collect-only 5674 项，与 e444 完整节点逐行相同；新 verifier context a898a00a33c40ced49019af5630fd4ed0fe48b5d76e28d2b5ae2cc466d279219。当前完整 76 包输入已冻结，SHAf38ff89997801eef14fadef0e661bfe202eead2e728d85c37238248e1b81ba29。新 ordinary wheel 061727 已真实完成两条 V0/V1 生命周期：2 passed、35 deselected、644.87 秒，包 SHA8d7daf8f3a4c7e0934decbd9a24c0d921582b15a85d3899935cd515528e24679，18 个实际进程 cleanup confirmed、正向 Gate 和 6/2 类篡改拒绝通过；summary SHAd0679a68dccd23b808cc27b9a334d0422814d33a93175c464c3d6057e3993fbc。新 sdist 验收 1 passed/68.45 秒，summary SHA21bb7e19c41356a1ef8a9ac3953018519a361c244228d6053e68ada6a0c25598：两份 sdist、四个 direct/rebuilt 轮子的全部 76 项 ZIP 字节均与新包一致，隔离安装资源 API 通过；独立 verifier 正在核验原件和当前消费者。旧 57c 轮子不提供当前 authority。先前 060850 轮因执行环境刷新没有完整终态，exit/cleanup UNKNOWN、不可验收，原件完整保留；当前新实际 verifier 从未来 Native 启动至 finalize 独立负责，不冒充旧线程身份。新 wheel/sdist 原件已由实际独立 verifier 接受（f3bca5、f56923、3dd583），错误 cwd 的初次审计失败另存保留。当前 94af 完整 Native 已真实通过：run-20261101T064500422632Z 为 5669 passed、5 既有 skipped、1022.27 秒，14 required checks、两域 branch-enabled combined 总覆盖率 85%/diff90% 和五个实际固定变异全部通过；core diff2564/2825=90.761062%。当前 pre 与 archive SHA4da827828312edb882d782d6ac228151ebc3a8b0e70ad7eee9c65e4c956c7789，snapshot65cd248dee822df2909990062017ffaf711d153af175fb2504e82abf0b89d939/contexta898；seq34 实际消费 e294，35 passed、36 WAITING_FOR_FINAL_REVIEW。当前独立 verifier 正在验收新的完整原始结果。正式当前 REV-0004 APPROVE 已登记（27 条发现保留严重度，仅 RF-022 medium open）；同一实际独立 verifier 已恰一次 finalize，final SHAa0d637ccb76d454d6c9966f7452ec88479fbfb4310efe6757443848a2052dc4f，仅 phase/review_refs 变化，原 pre 和 snapshot 不变。依常设授权已记录当前 code 批准，当前本地 Gate PASS。未验证：当前 head required CI。

## 审核问题

完整 Node 范围、真 base 分母、运行时等价和 Policy/spec/classification 的绑定是否均已核验？每项通过必须有当前原始结果；保留失败、负例和 unknown，不复用旧 action、旧 wheel 或旧审核作为新版本权威。

## 推荐结论

APPROVE_WITH_CONDITIONS。新候选须完成上述全部适用本地验证、独立实现审核通过、无未关闭 critical/high、same-verifier finalize、当前 code 批准/Gate，且实际合并的精确 head required CI 全过，才允许源仓 merge commit。RF-022 的硬 CI 条件满足后可合并该未移动 head；随后用官方 resolve 与 task close 将闭合记录追加到收尾文档 PR，该 PR 自身也必须通过精确 head CI。无需仅为 RF-022 治理修订额外移动主交付 head；不得因此省略任何实际合并 head 的门禁。
