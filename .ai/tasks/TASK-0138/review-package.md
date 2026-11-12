# TASK-0138 Review Package

## 审核目标

裁决 subject `4ea9cd02a9c7beadb9acc0a92561d18e8b278786` 的当前实现是否满足冻结规格，支持 A26 的同 verifier final、code 批准与源 Gate。

## 背景

冻结规格见 spec.md，原基线仍为 `1f748a99b97842b9eca7abf4be454d348bf78759`。A25 的两 fixture 修复在 Linux 留下 26 项真实失败；A26 仅在 producer_coordination 增加两行，明确合成工具库存不声明 API-derived OS roles。先通过真实早期 Linux CI，随后执行 native11；所有旧失败和次数保留。

## 代码地图

生产入口为 src/aiflow/node_ci.py、node_execution.py、installed_mutations.py、initialization.py 和验证服务；权威合同见 docs/superpowers/specs/node-ci.md。复用冻结设计 REV-0014 及 REV-0016 已覆盖的未变生产审查；本次差异仅 tests/unit/test_node_ci.py 的合成 fixture。普通 synthetic-tool 原件仍经过实际字节、size、SHA、identity、nlink 检查，独立真实宿主/API 负例保留。

## 语义变更

实现普通安装、真实平台关联、闭合角色原件及原 LOCAL 主机联合 Gate。A26 不改生产代码、Policy、schema、Norm、锁、工作流、断言、skip/xfail 或门槛；只使合成 fixture 在 Linux 到达原定事务边界。

## 风险

当前实施裁决必须绑定新快照，不能重贴 native10 或 F6 的旧版本证明。37-distribution 环境、F6 普通安装与容量只按真实旧归属和已审生产等价复用。先前 Linux 失败及首次认证准备的目录 guard 失败原件均保留；原进程/EOF/Job/cleanup、85/90 和单次额度不放松。

## 证据

已验证：早期 head `957d3a3668c0502ed5d12262e650841f93676f3c` 的 quality run 42430794236 与 artifact run 42430794253 均成功。Ubuntu 为 7250 passed、83 项原跳过，982.74 秒，原 26 项失败全部消失；完整质量门通过。早期产物不用于目标。

已验证：native11 的 `run-20261108T011237961379Z` 完整 V2，14 项全部通过，7324 passed、9 项原跳过，pytest 4126.21 秒，原五组变异全部 killed。原基线 core diff 为 2857/3172，即 90.0693568726%；两域 combined total 均超过 85%，analysis 无适用 diff。正式外层调用 4161.578 秒、returncode 0、cleanup confirmed，无超时或流溢出，八项生命周期标记均真。

当前 pre_implementation_review 快照为 `93981945c70ad54c73ad6d9916189ab7b4cb7045cdfa9e96b67506183eba3eaa`；evidence SHA `cb3183790392a9caeb69a541809e91cd0af6a1f87f7142ecd6b57ae88548bb78`。verifier 为 native-host-roles-verifier，context 为 `0668f3a56c953b1234f80c060928a979c3d4c3b1a614b27577719ab6f946f45f`。公共复现入口为 verify TASK-0138；本次 full 额度已消费，不重复运行。

未验证及待完成：当前正式实施审核、同 verifier final、code 批准和源 Gate；随后唯一最终 metadata 同步及最终 source quality/artifact 两项 CI。目标 LOCAL、私有 CI、原主机 combined Gate 尚未开始；本地或早期 PASS 不能替代它们。

## 审核问题

- 当前证据、冻结规格、原基线与正式实施审核是否绑定同一新 subject 和快照？
- 两行修复是否保留普通工具原件检查、全部原断言与独立真实宿主/API 负例？
- 未变生产实现及历史 managed declaration 修复的既有结论是否仍覆盖当前状态？
- 是否保留旧失败、原预算和次数，并清楚区分当前源结论与尚未完成的最终发行、目标链路？

## 推荐结论

建议 APPROVE，须由独立审核者对当前实际快照正式裁决；同 verifier final、code 批准和源 Gate 仍需实际通过。本包不新增权限，执行只依照 A23/A25/A26 的真实范围、预算、次数和停止条件。
