# TASK-0138 Review Package

## 审核目标

裁决 subject `4665993c23fa6c1c623184ea7fc0eee64833dfe9` 的源端实现是否满足冻结规格，支持 A25 范围内的本地 code 批准与源 Gate。

## 背景

本任务实现 Node CI 普通安装、真实平台关联与完整原件回放合同。冻结规格见 `spec.md`，原比较基线为 `1f748a99b97842b9eca7abf4be454d348bf78759`。A22 补两测试文件的八项拒绝边界回归；A25 仅修复两个合成 fixture 的宿主可移植性，保留真实宿主拒绝门。旧失败、用量及版本归属保留。

## 代码地图

主要入口为 `src/aiflow/node_ci.py`、`node_execution.py`、`installed_mutations.py`、`initialization.py` 和验证服务；权威合同见 `docs/superpowers/specs/node-ci.md`。精确范围与依赖见冻结规格、分类和正式设计审核 REV-0014。复用 `reviews/REV-0015-r0001.json` 已覆盖的未变生产代码审查；本次需要绑定新 subject、两 fixture 修复及完整快照的正式实施审核。

## 语义变更

提供闭合声明、普通安装与生产 admission、固定运行角色、完整材料验证及原 LOCAL 主机的联合 Gate；仅允许 managed @2 的精确可选声明，保持现有资源和历史完整性。A22、A25 不改生产代码、Policy、schema、Norm、锁或门槛；A25 的局部 OS 代理仅作用于合成测试 fixture，不替换全局 OS 或 pathlib，不修改断言、skip 或 xfail。

## 风险

平台认证、原件来源、版本新鲜度、容量与进程归属由既有拒绝合同约束。REV-0015 已评价历史 managed declaration 缺陷已解决；本次受影响审核须核实该结论在新快照仍成立。旧源 quality CI 的 Linux fixture 失败是真实失败，本机通过不代替修复后的 Linux CI。外部动作仍遵守 A23、A25 的范围、次数和停止条件。

## 证据

已验证：native10 的 `run-20261107T162343895705Z` 完整 V2，14 项检查通过；7324 passed、9 项原条件跳过，pytest 用时 4099.71 秒，五组原变异全部 killed。core 完整 diff 为 2857/3172，90.0693568726%；双域 combined total 均超过 85%，analysis 无适用变更行。正式 Job cleanup confirmed，八项生命周期标记均真，完整调用 4128.469 秒且未超时。快照为 `d36aad3ed0f4337d05e61b94ca8c2444d37ea232dcd517744057d6b3affd7d3b`，由 `native-ci-portability-verifier` 实际产生，当前阶段为 pre_implementation_review。完整复现入口为公共 `verify TASK-0138`；本次完整额度已经消费，不重复运行。旧 native9、失败原件及 F6 普通安装与容量证据保留，F6 仅按其真实旧版本及已审 production-equivalence 复用。

未验证及待完成：当前快照正式实施审核、同 verifier final、code 批准与源 Gate；随后向既有 PR #150 正常同步一次并核实新两项源 CI。目标新任务 LOCAL/CI 及原主机 combined Gate 尚未验收。不得以本地 fixture、旧安装或源端 PASS 替代这些事实。

## 审核问题

- 当前完整快照、冻结规格和实施审核是否绑定同一 subject 与原基线？
- 历史声明缺陷是否仍由当前代码及永久回归解决，A25 是否只修复合成 fixture，且所有旧失败和质量门槛保留？
- 源端结论与尚未发生的发布、目标接入是否明确区分？

## 推荐结论

建议 APPROVE，须由独立审核者对当前快照正式裁决；同 verifier final、code 批准和源 Gate 仍需实际完成。此包不授予发布、目标写入、私传或付费许可；相关许可仅来自已收到的 A23、A25。
