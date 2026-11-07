# TASK-0138 Review Package

## 审核目标

裁决 subject `2b0125494b18148300955cc3bfead00a45ceadd0` 的源端实现是否满足冻结规格，支持本地 code 批准与源 Gate。

## 背景

本任务实现 Node CI 普通安装、真实平台关联与完整原件回放合同。冻结规格见 `spec.md`，原比较基线为 `1f748a99b97842b9eca7abf4be454d348bf78759`。A22 仅补两测试文件的八项拒绝边界回归；旧失败、用量及版本归属保留。

## 代码地图

主要入口为 `src/aiflow/node_ci.py`、`node_execution.py`、`installed_mutations.py`、`initialization.py` 和验证服务；权威合同见 `docs/superpowers/specs/node-ci.md`。精确范围与依赖见冻结规格、分类和正式设计审核 REV-0014；当前实施审核为 `reviews/REV-0015-r0001.json`。

## 语义变更

提供闭合声明、普通安装与生产 admission、固定运行角色、完整材料验证及原 LOCAL 主机的联合 Gate；仅允许 managed @2 的精确可选声明，保持现有资源和历史完整性。A22 不改生产代码、Policy、schema、Norm、锁或门槛。

## 风险

平台认证、原件来源、版本新鲜度、容量与进程归属由既有拒绝合同约束。正式实施审核已依据当前代码、永久回归及完整快照评价历史 managed declaration 缺陷已解决，当前无未决发现。源端成功尚不证明真实发布或目标 CI 接入；外部动作仍须其适用授权。

## 证据

已验证：native9 的 `run-20261107T025235011205Z` 完整 V2，14 项检查通过；7324 passed、9 项原条件跳过，五组变异全部 killed。core 完整 diff 为 2857/3172，90.0693568726%；双域 combined total 均超过 85%，analysis 无适用变更行。正式 Job cleanup confirmed，八项生命周期标记均真。快照为 `64093d50157bbb9a48b06716384f267a03220dc95abb81f9625334481c756978`；正式 REV-0015 APPROVE 与同 verifier final 均绑定该快照。完整复现入口为公共 `verify TASK-0138`，本次不重复已接受检查。旧 F6 普通安装与容量仅按其真实旧版本及已审 production-equivalence 复用。

未验证：真实源 artifact 发布、目标新任务 LOCAL/CI 及原主机 combined Gate。不得以本地 fixture、旧安装或源端 PASS 替代这些外部事实。

## 审核问题

- 当前完整快照、冻结规格和实施审核是否绑定同一 subject 与原基线？
- 历史声明缺陷是否由当前代码及永久回归解决，且所有旧失败和质量门槛保留？
- 源端结论与尚未发生的发布、目标接入是否明确区分？

## 推荐结论

APPROVE：正式 REV-0015 无未决发现，完整 V2 与同 verifier final 已通过；允许按常设授权完成本地 code 批准和源 Gate。此包不授予发布、目标写入、私传或付费许可。
