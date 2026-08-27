# Task Specification

## 目标

完成 Chapter 13.1 的治理初始化：在不进入真实自举实现的前提下，新建 Chapter 13
权威状态并冻结未来跨模块 `REVIEW + V2` 自举试点的候选写入范围、只读代码地图、
验证要求、排除项和 fail-closed 边界。仅在当前 TASK-0024 subject 的正式 V1 与独立
审核通过后投影 13.1 完成；13.2 保持未开始，Phase 02 保持 `in_progress`。

## 范围

1. 本任务允许修改的业务路径精确限定为两个：
   `docs/superpowers/state/chapters/chapter-13.yaml` 和
   `docs/superpowers/state/overall.yaml`。TASK-0024 的 task-local 治理记录由 AI Flow
   按追加式规则维护；其他历史 task 记录不得修改。
2. Chapter 13 state 必须绑定已提交的 Phase 02 design/implementation plan 和已完成的
   Chapter 12，初始化 13.1–13.6 六项任务、每项五步，共 30 steps；依赖为
   `chapter-12 completed`。四个退出检查逐项对应实施目录第 183–186 行，初始化时均
   `pending`。
3. H1 只创建候选状态：Chapter 13 与六项任务保持 `pending`，overall totals 更新为
   13 chapters、77 tasks、408 steps、24 exit checks；completed 保持
   12/71/378/20，evidence items 保持 15，tracking 指向
   `chapter-13 / 13.1 / null`。Phase 03/04 仍 `not_started`。
4. 只有 H1 current subject 的正式 V1 与独立 implementation review 均通过后，H2 才可
   将 Chapter 13 置为 `in_progress`、13.1 置为 `completed` 且
   `completed_steps: [1,2,3,4,5]`，把 overall completed 更新为
   12/72/383/20、evidence items 更新为 16，并把 current task 指向 13.2。
   H2 只追加 `EVT-OVERALL-CH13-13.1-COMPLETE-001`，不得改写旧 history。
5. Chapter 13 state 必须保存未来 13.2 自举任务的非授权候选写入范围：
   `tests/acceptance/test_phase_02_self_hosting.py`、
   `tests/integration/test_phase_02_self_hosting.py`、
   `tests/e2e/test_phase_02_self_hosting_scenario.py`、
   `docs/implementation/chapter-13-review-self-hosting.md`、
   `docs/superpowers/state/chapters/chapter-13.yaml` 和
   `docs/superpowers/state/overall.yaml`。未来 task-local 治理目录仍由 AI Flow
   单独创建。
6. 未来 13.2 的只读代码地图可引用现有 Policy、schemas/contracts、
   `src/aiflow` 的 review/approval/verification/evidence/Gate/observation/CLI 核心、
   `tools/hooks`、阶段二 mutant manifest 及既有 unit/integration/acceptance/E2E
   测试；这些路径不是 TASK-0024 或未来 13.2 的写入授权。若真实实现需要修改其中任一路径，
   必须先记录 scope/behavior/policy/verification 变化，扩展未来 task 的 scope，
   重新分类、冻结和取得新的 spec approval。
7. 未来真实自举 task 必须新建独立 AI Flow 记录，并以当前 Policy 重新分类。其决策事实
   必须请求 acceptance、integration、targeted mutation 与 independent verifier，
   因而目标验证为 V2；route 与 verification level 仍由 Policy 分别确定，不在本状态文件
   复制规则表或手工降级。
8. 未来 V2 通过至少要求：不同的非空 Implementer/Verifier actor、当前 frozen spec 和
   Policy、设计审核、V1 全集、acceptance、integration、五项 targeted mutants 全部
   killed、无 unverified scenarios、不可变 verifier context、implementation review、
   current code approval、CI simulation 与 Gate。actor 字符串不构成外部身份认证。
9. 既有 P2-REV-01、P2-V2-01、P2-VER-01、P2-MUT-01、P2-ESC-01 和 P2-HOOK-01
   只作为进入输入和历史证据索引，不能替代未来 task 当前 subject 的 review、approval、
   evidence 或 Gate。Hook/CLI/CI parity 仍只覆盖已证明的两类 Hook facts 和支持平台，
   不扩展为自由 shell、所有客户端、跨平台 live Hook 或 OS sandbox。

## 非目标

1. 不修改 `src/`、`tests/`、`tools/hooks/`、`.ai/policy/`、
   `.ai/schemas/`、`.ai/templates/`、mutation manifest、CLI、Gate、approval、
   evidence 或状态机行为。
2. 不开始 13.2，不创建其 task/worktree，不运行真实 V2、independent verifier、
   targeted mutation、CI simulation 或 Gate，也不形成未来 task 的批准。
3. 不修改 README、CHANGELOG、operations 文档、Phase 02 验收矩阵、阶段三输入或
   Chapter 12；这些分别属于后续 13.5/13.6 或独立治理范围。
4. 不宣称 Phase 02 完成，不实现 V3、安全扫描、故障注入、模型调用/路由、资源调度、
   DAG/跨主机编排、通用变异、通用命令拦截或操作系统安全沙箱。
5. 不复用其他 task/version 的 classification、spec approval、review、evidence、
   action approval 或 code approval；不把历史通过事实描述成未来 task 的 current 通过。
6. 不执行 push、merge、deploy、delete、publish、secret export、付费调用、外部模型或
   真实高风险命令。

## 验收条件

1. 业务 diff 只包含两个允许的 state 文件；主工作树既有 `.reasonix` 改动和所有历史
   task 记录不进入 TASK-0024 diff、commit 或 evidence。
2. `chapter-13.yaml` 的 dependency、六项任务、30 steps、四个 exit checks、候选
   自举范围、只读代码地图边界和 future-task re-governance 规则与 Phase 02 design/plan
   一致。
3. H1 的 overall totals/current pointers/completed/evidence items 与 Chapter 13 pending
   状态一致；不得提前完成 13.1。H2 只能在 H1 V1 与独立审核通过后应用，且
   12/72/383/20、evidence 16、13.2 pending/current 和追加 history 相互一致。
4. 未来自举 envelope 明确请求四项 V2 requirements，并保留相同 actor、陈旧或篡改
   context/review/evidence、survived/missing mutant、unverified scenario、范围越界未升级、
   Hook/CLI/CI 结论不一致时的拒绝语义。
5. `aiflow validate TASK-0024`、`aiflow scope TASK-0024`、YAML 解析、状态计数和引用
   一致性、`git diff --check` 及 Policy 选定的全部 V1 checks 通过；当前环境没有
   required verification tool missing。
6. 设计审核绑定当前 base/spec/Policy/classification context 且无未关闭 high/critical
   finding；spec approval 只能在该审核通过后产生。
7. H1 与 H2 分别取得当前 subject 的正式 V1 和独立 implementation review；最终 H2
   重新取得 code approval 与 Gate，`unverified_scenarios` 为空后才可形成 merge
   readiness。

## 禁止动作

禁止 push、merge、deploy、delete、publish、secret export、付费或其他外部服务调用，
禁止访问凭据、安装或执行 Hook、运行 observation 所描述的动作，以及提前创建/执行
13.2。软件安装仅在本任务必需验证工具确实缺失、用户已有明确授权且不会扩展仓库范围时
允许；若安装改变依赖、锁文件、Policy 或可重放环境，必须先记录变化并重新治理。

## 错误行为

若 Chapter 12/ TASK-0023 的完成事实不成立、任一总数/指针/步骤/退出检查不一致、候选范围
模糊或越界、把只读代码地图当作写权限、提前开始 13.2/Phase 03、降低未来 V2 requirements、
复用陈旧 review/evidence/approval、把 actor 当作外部身份、扩大 Hook 支持结论，或 H1/H2
验证审核时序缺失，必须 fail closed。未来实现若需要修改候选 allowlist 外路径，必须停止、
记录 observation/escalation 并用新的 task version 重新分类、冻结和批准，不能静默扩展。

## 回滚

所有状态变更通过后续受治理提交反向修改：移除未被后续任务依赖的
`chapter-13.yaml`，将 overall 恢复为 12 chapters、71 tasks、378 steps、20 exit
checks，completed 12/71/378/20、evidence items 15，tracking 恢复
`chapter-12 / null / null`，并恢复“Chapter 13 尚未初始化”的 Phase 02 note。
TASK-0024 的 task、classification、spec、review、approval、evidence 与 event ledger
保持追加式，不删除或重写；若后续 Chapter 13 任务已经绑定该状态，则必须另建治理任务
执行前向修正，不能直接移除历史。
