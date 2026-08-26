# Review Package

## 审核目标

确认 TASK-0017 在 subject `ea1fc62cb25e1a32e5d8aea365c118d4c69f9ea9` 上完成
Chapter 12.1 的版本化 observation contract 与纯不可变 parser/type 层：五种 kind、四种
source、task/base/subject/Policy 绑定和 kind-specific minimal summary 均按冻结规格
fail closed；同时确认实现没有越入 12.2–12.5 的 decision、持久化、CLI、Hook 或 CI
adapter，也没有改变 Policy、Gate、state machine 或既有 evidence/approval 结论。

## 背景

任务 base 为 `2e627da10f699b94584cc90e5565e25c1c57fb77`，确定性分类为
`REVIEW / V1`。classification input SHA-256 为
`fef922a06af2cf71410982e17b662eace620e067c8db15ea50939d116a4b6f3e`，冻结规格
SHA-256 为 `159b3887cc16127361724e431baccc9cba3aed1c6e72df989eaec2ede1761911`，
active Policy SHA-256 为
`f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`。
设计审核 `REV-0019` 绑定 context
`9cf9be4d0acf8075d71ab4d9fca37b6f848c265ee1e3c39520377df7bc794d20`，结论
APPROVE 且 findings 为空。

首个 subject `d81740879bca69d03eaf18e84212fedfd568c6f2` 的正式 V1 如实失败：
9/10 required checks 通过，唯一失败为 diff coverage 87%（门槛 90%）。任务进入 FAILED，
没有 code approval；随后按同一冻结规格 retry，只增加三个 fail-closed parser/serializer
防御测试并保留失败 evidence 历史，形成当前 subject `ea1fc62…f9ea9`。当前 subject 的正式
V1 已重跑通过。

## 代码地图

- `.ai/schemas/observation.schema.json`：closed v1 根契约、五 kind、四 source、严格版本
  绑定、三类判别 summary、repository-relative path 与 safe target 约束。
- `.ai/templates/observation.json` 和 `tests/fixtures/contracts/**/observation*.json`：
  canonical 示例及 extra/invalid/missing 固定负例。
- `src/aiflow/contracts.py`：把 `observation` 注册到固定 schema 目录与 registry。
- `src/aiflow/observation.py`：冻结 enums/dataclasses、纯 `parse_observation` 与
  `serialize_observation`；无 I/O、Policy 读取、ledger 写入或 decision。
- `tests/unit/test_contracts.py`、`tests/unit/test_observation.py`：通用 contract matrix、
  五 kind/四 source round-trip、不可变性、非 mutation、safe path/target、未知字段和
  non-echo fail-closed 覆盖，包括首轮 V1 的定向 remediation。
- `docs/implementation/chapter-12-runtime-observations-hooks.md`、Chapter 12/overall state：
  只完成 12.1 并把指针移到 12.2；12.2–12.6 与两个 chapter exit checks 仍 pending。
- `.ai/tasks/TASK-0017/`：classification、冻结规格、设计审核、首轮失败与 retry、当前
  passing V1 evidence 及追加式事件。

## 语义变更

仓库现在可以对 JSON-compatible observation payload 做确定性 contract validation，并
解析为 tuple-backed、frozen Python facts，再无损序列化。契约固定五种 observation kind
和四种 source；路径 summary 只接受规范 repository-relative 路径，高风险命令 summary
只接受 active Policy 2.1.0 的六种规范 action 与最长 255 字符的 safe `target_ref`，
evidence summary 只接受 closed artifact/reason enums。

该语义只定义事实形状，不决定 `record`、`escalate` 或 `refuse`，不验证 source 身份，
不比较绑定 currentness，不写 task event，也不安装或修改 Hook。Chapter 12 的总体状态为
in progress，累计 tasks `66/71`、steps `353/378`、evidence items `10`，当前指针 12.2；
Chapter 12 两项退出检查仍未通过。

## 风险

- source 是输入标签而非身份认证；12.2–12.5 必须在 adapter/core 边界另行建立来源、
  currentness、decision 与 persistence 规则。
- `target_ref` 是有界、无 shell 元字符的规范引用，但本模块既不解释也不执行目标；它不
  提供通用 shell parser 或操作系统安全沙箱。
- high-risk action enum 精确镜像当前 active Policy 的六类 automatic deny。未来 Policy
  增删类别时必须触发 `policy_changed`、重新 classify/freeze/review，而不能在 Hook 内复制
  或静默漂移。
- 路径 schema 拒绝明显 escape 和非规范分隔，但不读取文件系统、不解析 symlink；实际
  repository containment 属于后续 producer/shared core 的责任。
- subject 内保留首轮 failed evidence 的治理快照；当前 passing evidence 位于
  governance-only 工作区，并由当前 evidence digest 和事件绑定，不得把首次失败改写为
  从未发生。

## 证据

- 已验证：当前 subject 的 local V1 为 passed，10/10 required checks 全部通过，
  `unverified_scenarios: []`；diff coverage 为 91%（123 changed lines、10 missing），满足
  90% 门槛。当前 evidence 文件 SHA-256 为
  `c66cfaeef64f118af65f948238307b83f7c5b8b5632ae01a4515f1234b709d5f`，canonical
  evidence SHA-256 为
  `8027f06035455f6430d49249f9987769fd7d069d63e61b6d8726546e448c1a88`。
- 10 项通过检查为 contract、scope、ruff check、format check、smoke、unit tests、
  regression tests、mypy、coverage XML、diff coverage；复现命令为
  `python -m aiflow verify TASK-0017 --actor /root/task17_requirements`。
- 首轮 failed V1 的 9 项通过与 87% diff coverage failure 已记录在 task events、前一
  evidence snapshot 和 run logs；retry 没有修改规格、Policy、产品行为或允许范围。
- implementation review context SHA-256 为
  `215ddaf5ed0cdadc88653318f109c43b4d9a93359bac7533be98b5d9b4e0c506`；其中
  subject、evidence、spec、Policy、classification 与 23 个 base-to-subject changed paths
  均已绑定。
- 当前 `aiflow validate TASK-0017` 与 `aiflow scope TASK-0017` 通过；产品 HEAD 与 subject
  一致，工作区变更仅为 TASK-0017 task-local governance/evidence/review 文件。
- 未验证、未执行且未授权：真实 Hook/CLI/CI adapter、observation ledger、
  observation-to-escalation/refusal mapping、任意 shell 拦截、push、merge、deploy、delete、
  secret export、paid external call、package publish、Chapter 12 exit checks。

## 审核问题

- schema 的 `oneOf`/conditional 约束是否保证每个 kind 只能使用对应 closed summary，且
  unknown/missing/unsafe payload 不会回显潜在敏感值？
- Python 类型和 parser/serializer 是否真正纯、不可变、非 mutation、round-trip，且没有
  隐含仓库、时间、环境、Policy 或 task-state I/O？
- active Policy 六类 action 与证据 artifact 枚举是否足以作为 12.2 输入，同时保持未来
  Policy 变化必须重新治理的边界？
- 首轮 diff coverage 失败、retry remediation 和当前 passing V1 是否都被准确保留，没有
  以最终通过掩盖历史失败？
- Chapter 12 状态是否只完成 12.1，并明确拒绝提前声称 decision、Hook parity 或安全沙箱？
- 当前 evidence、implementation review 与 governance-only 工作区是否满足 code approval，
  同时继续保留独立的 push/merge 高风险批准门？

## 推荐结论

`APPROVE`。当前 subject 满足冻结的 Chapter 12.1 contract/type/parser 范围；首轮 V1 失败
已保留并由定向测试 remediation，当前 V1 10/10 passed、unverified 为空。若独立实现审核
未发现 P0–P3 finding，可记录 code approval 并进入只读 Gate；本结论不授权 push、merge、
deploy、delete 或任何 12.2–12.6 行为。
