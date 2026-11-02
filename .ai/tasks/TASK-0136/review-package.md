# TASK-0136 implementation review package

## 审核目标

审核原始 base 5a802cd1bb60a23d01bc0fa0a7922026176855f6 至 subject b7d893f70dba6c13c0d6b9693005e69a17db03f4 的完整本地 Node revision 2 实现。冻结规格为 1ed3a60a275ebdd5c6fbd90c97742d4a24a50465709a42be535ff30c920909ae；实现审核绑定稳定快照，code approval 必须绑定完整 final evidence。

## 背景

普通安装的 agent-bridge-node@2 需要完整 V0/V1/V2 生命周期，以及固定 Istanbul 覆盖率、离线产品断言、五个真实 installed mutation 和可复查的原件。权威合同是 docs/superpowers/specs/node-v2-installed-lifecycle.md，SHA256 0051a57b4bfec08efcd8e0d08ea011b0c9c7621ab060b8f22df833a913136d93。本阶段保持 native 与 revision 1 行为；Node CI 和实际目标仓应用由后续独立阶段交付。

## 代码地图

- src/aiflow/node_execution.py、node_verification.py、verification.py：固定计划、实际材料、进程原件、Istanbul/product 派生及 native 输出封存。
- src/aiflow/installed_mutations.py、installed_probe.py：独立安装副本、五对真实执行、闭合清单和只读 replay。
- src/aiflow/verification_service.py、verifier_service.py、review_service.py、evidence.py：准入、不可变 pre、稳定快照审核与同一 verifier final。
- src/aiflow/approval.py、gate.py、freshness.py、status_service.py：从真实原件派生的 installed facts、批准恢复及最终门禁。
- policy.py、verification_level.py、initialization.py、cli.py 和两个 Schema：显式版本分支与原子消费者接入；既有打包资源入口保持有效。

## 语义变更

显式增加 Policy3.2/profile2/local evidence3.2 分支，保留完整 V1 前缀及固定 V2 检查。actual installed run 与 Node run 使用同一个独占 IMUT；公开 JSON 不授予 Current。覆盖率和产品结果从固定全量报告、原始坐标域和真实进程结果派生。适用 native helper 必须在第一次成功 node_check 后封存完整两文件输出，并在后续执行、结束和 replay 保持相同字节及身份。实现审核绑定 snapshot，final 由原 verifier 封存，code approval 绑定完整 final digest。

R5 只补充有意义的拒绝、I/O、保留和无写入回归，并将 synthetic fixture 目录叶名缩短；所有既有断言、固定原生变异、原 base、完整 diff 分母和质量阈值保留。51 个生产文件及 25 项资源原字节未变。

## 风险

本合同依赖固定工具、配置和 trusted-host 输出模型，不声明独立 CS-to-IL 认证。版本、输入或原件漂移必须拒绝。隔离 fixture 和结构性失败文档不构成普通安装或原生执行证明。actor 标签不是人类亲审或身份认证。既有失败、已消费 action、旧审核及日志保留；本包不授予公开私有派生元数据、目标仓交付或仓库设置修改权限。

## 证据

已验证：本次完整 native V2 的 14 项 required checks 全部 passed；6502 passed、9 项既有受控 skipped、0 failed/error，pytest 2911.96 秒且未超 3000 秒。core combined 89.93109928%，analysis combined 97.50390016%；原始 base 完整生产 diff 为 967/1042 = 92.80230326%。五个 fresh native mutation 的真实 baseline 均为 0、mutant 为 1，全部 killed，无超时或主树变化。原始日志在 logs/run-20261102T061050177428Z/；五个变异原件在 logs/MUTRUN-20261102T065928Z-1323abd3318794ca/。

已验证：独立 REV-0006/r1 为 APPROVE、findings 为空；implementation context 为 27100d93e3b4182477fa9d2daf89922fc881fdf685cfbd6bc52edfc052a7c718；snapshot 为 8efff10d5d71fc9e5487b30f0b3750b7ef4cc8e069729de3c442d02ec56f9d9c。原 verifier context 6a1b4d61a0d7e30006c7d81f63a8e3e88b02ad723fb84ed7e0d0fc2274dafc85 下完成一次 finalize，没有重跑 suite/mutation/probe。完整 final canonical SHA256 为 1d80bee436104a185b1452eb257c747dae16ef504392dc2e2886525901a2b7d6，raw SHA256 为 d8771ce99427834ad407191befc2ee236fb1f3502ea3c34bf9eef92c7171833d。不可变 pre 的 raw SHA256 仍为 907b8542379722ae7b71d4338a175ac3b3b91651f60627706c9fdee4705e3025。普通 direct 和 sdist-rebuilt 的补充生命周期原件已在原范围核验，未重新标记为本轮新运行。

未验证：当前候选的远端 required CI、公开发布、Node CI 和真实目标仓应用尚未交付。本包未执行真实 SDK/model/WeChat 调用、凭据导出、付费调用、设置修改或历史改写。

## 审核问题

- 新的版本分支是否在所有消费者保留 native/revision1 的拒绝和验收语义？
- 进程、覆盖率、产品、五对 mutation、native 输出及 original-root 原件是否由同一闭合材料链派生？
- pre、snapshot review、同 verifier final 与完整 final code approval 的不同绑定是否准确且无恢复旁路？
- 原始 base、1042 行分母、85/90 阈值、3000 秒预算和所有失败原件是否完整保留？

## 推荐结论

APPROVE。当前完整原始差异已独立审核，最终验证通过且无未关闭 critical/high。按常设授权记录当前完整 final evidence 的 code approval，再由实际 Gate 和远端 required checks 判断相应交付步骤。
