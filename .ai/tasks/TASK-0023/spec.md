# Task Specification

## 目标

完成 Chapter 12.6 与 Chapter 12 退出：把 README、Hooks、Quickstart、Recovery 和
Chapter 12 实施文档校正到已合并的 Chapter 11、Chapter 12.1–12.5 与
`aiflow observe` 事实，补齐可执行的 fail-closed 恢复说明；仅在当前 subject 的正式
V1 与独立审核通过后，将 12.6 五步、P2-ESC-01/P2-HOOK-01 的当前证据和
`CH12-EXIT-01/02` 投影为完成。Chapter 13 保持未初始化，Phase 02 仍未完成。

## 范围

1. 允许修改的业务路径精确限定为七个：
   `README.md`、`docs/operations/hooks.md`、
   `docs/operations/quickstart.md`、`docs/operations/recovery.md`、
   `docs/implementation/chapter-12-runtime-observations-hooks.md`、
   `docs/superpowers/state/chapters/chapter-12.yaml` 和
   `docs/superpowers/state/overall.yaml`。TASK-0023 的 task-local 治理记录按 AI Flow
   规则追加。
2. README 必须删除“Chapter 12 仅初始化、当前 12.1、Hook/运行期 observation 未实现”
   等旧叙述，准确区分 Chapter 11 已完成、12.1–12.5 已合并、12.6/Chapter 12 exit 在
   H1 阶段仍 pending，并在最终 H2 投影后表述 Chapter 12 已完成、Chapter 13 尚未初始化。
   不能把 TASK-0015/TASK-0022 的历史通过事实复用于其他 task、subject、spec、Policy 或
   classification。
3. Hooks 文档必须记录精确命令
   `aiflow observe TASK-ID --input FILE --mode {apply,dry-run,ci} [--actor ACTOR]`：
   `apply` 只接受 `source=cli` 且要求非空 actor，并可能追加 task-local audit 或单调
   escalation；`dry-run` 只接受 `source=cli` 且禁止 actor；`ci` 只接受
   `source=ci` 且禁止 actor，后二者对完整 task 目录零写。输入只来自一个本地 UTF-8 JSON
   object，重复 key、未知字段、stdin、environment、自由 shell 和网络均不接受。
4. 所有有效 observation 都保持 `execution_allowed=false` 并 exit 2；输入、contract、
   binding 或 state 错误 exit 1；不存在以 exit 0 授权动作。pre-command 对 Policy 禁止的
   canonical high-risk action 在审计后仍固定拒绝，不消费 action approval、不执行命令。
   文档必须说明可选 `--task`、高风险 task 解析和 fail-closed ambiguity。
5. Quickstart 必须把 Chapter 11 的 V2 描述更新为已实现 acceptance、integration、
   action-approved targeted mutation 与 independent verifier 的 current-version 流程；保留
   partial/provisional evidence 不可进入 Gate、CI attestation 不替代 local evidence/review/
   approval 的边界。只读 observe 示例不能把空演示 task 伪装成有 current binding 的成功输入，
   并必须解释 exit 2 是有效的非授权结论。
6. Recovery 必须移除“Chapter 11.2–11.5 尚未实现、live V2 必然失败”的旧诊断，改为从当前
   task/version 的 action approval、immutable mutation artifact、pre evidence、implementation
   review、finalize、code approval 与 Gate 恢复；missing/stale/tampered/non-killed/unverified
   均 fail closed，不能借用 TASK-0015 artifact。
7. Recovery 新增 observation/Hook/observe 恢复条目：先 `status`、`validate`、必要时
   `scope`，再用 `dry-run` 复现只读路径；修正 current task/base/subject/Policy/
   classification/Git binding 后重建新的 immutable input，禁止改写旧 event/digest 来“刷新”。
   只有确需审计当前事实时才使用 apply；exit 2 不得触发所描述动作，exit 1 必须先修复事实或绑定。
8. 实施文档必须补记 TASK-0022 final subject
   `893ce6bc7f31a20a964776bbbc2b7e5a2c280d90`、current V1、`REV-0035`、
   code approval、external merge event 25 和 merge-record governance commit
   `d51721b92694d6684e4d3fd14079a18b321a449c`，并删除“TASK-0022 当前仍待最终
   V1/review/Gate”的过时句。
9. H1 先完成入口/运维正文和 Chapter 12 实施文档的 12.6 候选说明，同时保持 Chapter 12
   state、overall 完成计数、README/实施文档的最终完成状态为 pending。只有 H1 current subject
   的正式 V1 与独立 implementation review 均通过后，H2 才可投影：
   12.6 `completed_steps: [1,2,3,4,5]`、两个 Chapter 12 exit checks passed、
   Chapter 12 completed 和一项绑定 TASK-0023 的 chapter-exit evidence。
10. H2 的 overall 精确保持 totals 为 12 chapters、71 tasks、378 steps、20 exit checks，
    并更新 completed 为 12/71/378/20、evidence items 为 15；tracking 保持
    `current_chapter: chapter-12`、`current_task: null`、`current_step: null`。
    Phase 02 的 next chapter 可记为 Chapter 13，但不得新建 chapter-13 state、增加 totals、
    开始 13.1 或宣称 Phase 02 完成。历史只追加
    `EVT-OVERALL-CH12-12.6-COMPLETE-001`，不改写旧事件。
11. P2-ESC-01 只以现有 observation-to-escalation integration 事实为依据；
    P2-HOOK-01 只以支持范围内 Hook/CLI/CI semantic parity 与明确限制为依据。两者可作为
    Chapter 12 exit 的已满足输入，但不得扩展为所有 observation 都有 Hook、跨平台 live Hook、
    全客户端拦截或系统级沙箱。
12. H2 投影后的新 subject 必须重新取得正式 V1、独立 implementation review、code approval
    与 Gate，方可形成 merge readiness。

## 非目标

1. 不修改 `src/`、`tests/`、`tools/hooks/`、Policy、schema、template、CLI、Gate、
   verification、approval、state machine 或历史 task 记录。
2. 不修改、移动、归档或删除主工作树中未跟踪的 TASK-0021；其处置需要独立明确授权，且不得
   混入 TASK-0023。
3. 不创建 `docs/superpowers/state/chapters/chapter-13.yaml`，不初始化或开始 Chapter 13，
   不新增 Chapter 13 的 tasks/steps/exit totals，也不完成 Phase 02。
4. 不安装 Hook，不执行 observation 描述的命令，不消费 action approval，不解析自由
   PowerShell/cmd/bash、alias、pipe、redirection、quote、wildcard、variable/command
   expansion、argv、environment、stdin/stdout/stderr 或 credential。
5. 不宣称不同 source 的 digest、mode、ledger effect、event metadata、JSON bytes 或文案相同；
   parity 只限冻结规格定义的 decision semantic fields。
6. 不调用网络、外部模型、外部服务或付费能力；不 push、merge、deploy、delete、发布包或
   访问凭据。

## 验收条件

1. 七个业务路径之外无变更；TASK-0021 和 `.reasonix` 不进入 diff、commit 或 evidence。
2. README、Hooks、Quickstart、Recovery 与实施文档不再包含已被 Chapter 11/TASK-0022
   当前事实取代的 pending 叙述，且链接和命令名称存在。
3. `aiflow observe --help` 与文档协议一致；apply/dry-run/ci source/actor、exit 1/2、
   zero-write 和 non-authorizing 说明与当前实现一致，不要求或暗示 exit 0。
4. 文档准确记录 semantic parity 的包含/排除字段、Hook E2E 仅两类事实，以及 Windows、
   四个既有 symlink skips、Linux/macOS live Hook、未安装 Hook、IDE/GUI/remote Git、
   free-shell 和 non-OS-sandbox 边界。
5. V2 文档准确记录 acceptance/integration/targeted mutation/independent verifier 已实现，
   同时保持 current binding、action approval、partial evidence、CI attestation 与 Gate 的
   fail-closed 限制。
6. Recovery 能从 stale observation binding、exit 1、exit 2、Hook ambiguity、
   mutation evidence stale/missing/tampered/non-killed/unverified 等状态给出不绕过 ledger、
   Policy、review、approval 或 Gate 的可执行步骤。
7. TASK-0022 仍为 MERGED；subject `893ce6bc7f31a20a964776bbbc2b7e5a2c280d90`、
   external merge event 25、`REV-0035` context
   `f424e758b3519848b9d0ea68ddf07df81ad9c631bd20869d1aff7085d1538b0b`、
   canonical V1 evidence
   `9054a208781ba61ff65cd03b30fee6e58168a8865c49ee7ebc0e4dc4e723fd58`
   与 governance commit `d51721b92694d6684e4d3fd14079a18b321a449c` 引用一致。
8. H1 正式 V1 与独立审核通过前，12.6、两个 exit checks、Chapter 12 completion 和 overall
   完成计数保持 pending；H2 只在此前提后应用，且新 subject 再次正式 V1/独立审核。
9. H2 的 Chapter 12 task、exit、chapter evidence、overall counts/current pointer/future-phase
   note 与追加历史事件相互一致；Chapter 13 不存在 state file且未计入 totals。
10. `aiflow validate TASK-0023`、`aiflow scope TASK-0023`、Markdown/YAML/链接/引用一致性、
    `git diff --check`、Policy 选定的全部 V1 checks、独立设计审核与两阶段实现审核全部通过；
    `unverified_scenarios` 为空。

## 禁止动作

禁止 push、merge、deploy、delete、secret export、package publish、凭据访问、网络、付费或
其他外部服务调用，以及任何真实命令/Hook 安装/Chapter 13 初始化。未来外部动作必须获得与
当时 task/spec/Policy/subject/action 绑定的明确批准。

## 错误行为

若文档命令与当前 CLI 不一致、把 exit 2 当作许可、暗示 approval 让 pre-command 自动放行、
复用其他 task/version 的 V2 或 observation evidence、把 Windows wrapper 测试扩展为跨平台
live Hook、修改七个业务路径之外文件、提前完成 Chapter 13/Phase 02、计数/指针/evidence
不一致，或 H1/H2 的验证审核时序缺失，必须 fail closed、保持 Chapter 12 pending 或重新治理，
不得用叙述替代证据。

## 回滚

所有文档与状态变更通过后续受治理提交反向修改：恢复旧文档正文、将 12.6 与两个 exit checks
恢复 pending、Chapter 12 恢复 in_progress、overall completed counters/evidence items 回退到
11/70/373/18/14，并把 current task 恢复 12.6。TASK-0023 的 task、classification、spec、
review、approval、evidence 与 event 历史保持追加式，不删除、不重写。未完成、验证失败或审核
未通过时不得投影 Chapter 12 完成。
