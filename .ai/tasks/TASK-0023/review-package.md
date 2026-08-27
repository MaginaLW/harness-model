# Review Package

## 审核目标

确认 TASK-0023 在 current subject
`67acd2af690136cf5ab73888c81ae7a86ae1ea2d` 上完成 Chapter 12.6 与 Chapter 12
退出：五份入口/运维正文准确反映 Chapter 11、12.1–12.5、`aiflow observe` 和
fail-closed 恢复事实；12.6 五步、P2-ESC-01/P2-HOOK-01 的受限支持输入、
`CH12-EXIT-01/02`、Chapter 12 与 overall 完成计数一致投影，同时保持 Chapter 13
未初始化、Phase 02 未完成，并保留所有 Hook、平台、shell 和非沙箱边界。

## 背景

任务 base 为 `d51721b92694d6684e4d3fd14079a18b321a449c`，确定性分类为
`REVIEW / V1`。current classification input SHA-256 为
`a1a39c4d14329d0a11838ee294f63e61e9510ac793b3ac6747a0758f0658f1f6`，冻结规格
SHA-256 为 `237f9578c30ae0b09467036bd8ee3623859d27d513018c67318a9454eaabfd3f`，
active Policy SHA-256 为
`f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`。

用户绑定上述分类与 Policy 批准从 BLOCK 降为 REVIEW/V1；独立设计审核 `REV-0036` /
context `7ec6072ea19c8d0ff52b411cbc7418d456c6e8a4619e3d9d40d22750a89d56bd`
通过后，H1 形成文档 checkpoint `4c5392caf8d11f117468b1364b1e20a62c09eab3`。
首次正式 V1 因补充恢复条目占用封闭的 `REC-09` 标题而保留失败 evidence；仅标题 remediation
形成 `965e7e92eb8fa694659cf69d89b9325cc26470d9`，精准回归和正式 V1 均通过，独立
H1 implementation review `REV-0037` / context
`22f2de7b232cda6468afbc5d363f489b3419da482424076c81d8c2805fd048a3`
为 APPROVE。

H2 随后只投影 Chapter 12.6、两个 exit checks、章节状态和 overall 计数，形成 current
subject `67acd2af690136cf5ab73888c81ae7a86ae1ea2d`。该 subject 已重新取得正式 V1；最终
implementation review `REV-0038` / context
`33d2d98fbab8335480909f44bcdbc6d0dcb80fac250e2d50411cf634d1998e49`
为 APPROVE、findings 为空。H1 evidence/review 只作为投影时序前提，没有替代 current
subject 的最终验证与审核。

## 代码地图

- `README.md`：公开当前状态、阶段实施目录与 observation/Hook 能力边界。
- `docs/operations/hooks.md`：精确记录 observe 协议、pre-commit/pre-command 语义、
  mode/source/actor、zero-write、exit 1/2 与 non-authorizing 约束。
- `docs/operations/quickstart.md`：记录 Chapter 11 current-version V2、partial/provisional
  evidence、CI attestation 与只读 observe 示例。
- `docs/operations/recovery.md`：保留 REC-01–REC-08 封闭标题，并补充 observation、Hook、
  observe 与 V2 的 fail-closed 恢复路径。
- `docs/implementation/chapter-12-runtime-observations-hooks.md`：记录 TASK-0022 最终事实、
  TASK-0023 H1/H2 时序、验证、审查和限制。
- `docs/superpowers/state/chapters/chapter-12.yaml`：完成 12.6 五步、两个 exit checks 与
  `EVD-CH12-12.6-001`。
- `docs/superpowers/state/overall.yaml`：完成计数为 12 chapters、71 tasks、378 steps、
  20 exit checks、15 evidence items；tracking 为 chapter-12/null/null，Chapter 13 只作为
  future phase next pointer 而未初始化。
- `.ai/tasks/TASK-0023/**`：冻结规格、分类、批准、两阶段审核、V1 evidence 与追加事件。

## 语义变更

项目入口不再把 Chapter 11 V2 或 Chapter 12.1–12.5 描述为未实现。`aiflow observe` 仍只
消费显式 task 和本地 UTF-8 JSON object；`apply` 只接受 `source=cli` 和非空 actor，
`dry-run` 只接受 `source=cli` 且禁止 actor，`ci` 只接受 `source=ci` 且禁止 actor。有效
observation 恒为 `execution_allowed=false` / exit 2；无效输入或 current binding/state 错误
exit 1，不存在 exit 0 授权。

pre-command 的空 target 在读取 Policy/task 前失败，auto-allow 路径不读取 task 或产生
observation；六类 Policy 禁止的 canonical high-risk action 经共享 service 审计后仍固定拒绝，
不消费 action approval、不执行命令。semantic parity 只比较 decision fields，不要求
source-sensitive digest、mode、ledger effect、event metadata、JSON bytes 或文案相同。

Chapter 12 completion 只建立在支持范围内的 observation-to-escalation/refusal 与两类真实
Hook facts 上。overall 保持 `in_progress`，Chapter 13 没有 state 文件，也未增加 tasks、steps
或 exit totals。

## 风险

- 当前证据运行在 Windows 临时 Git/task ledger 和 wrapper entrypoint；4 个既有 symlink skips
  不证明 Linux/macOS live Hook 安装或全部 host 行为。
- 未安装 Hook 的客户端、IDE save、GUI/remote Git 与绕过 wrapper 的调用未被证明可拦截。
- pre-command 只接受结构化 canonical action/target，不解析 PowerShell、cmd、bash、alias、
  pipe、redirection、quote、wildcard 或 variable/command expansion；系统不是通用命令拦截器
  或操作系统安全沙箱。
- Chapter 13 尚未初始化，Phase 02 尚未完成；本任务不能开始 13.1 或宣称阶段二完成。
- 未执行或授权 push、merge、deploy、secret export、package publish、凭据、网络、付费或
  其他外部动作。远程操作仍需独立、版本绑定的用户批准。

## 证据

- 已验证：current canonical V1 evidence SHA-256：
  `6efd308a73ef251e2234bc4fe697cc957e71a5f1759b3b9ddc1e9dad2ac16069`；
  evidence 文件字节 SHA-256：
  `8d8b279db88fe53641e708f5de0a3e3e5d5f9460255885dfadfb7b69a0e04142`。
- current subject 的 V1 为 10/10 required checks passed，`unverified_scenarios: []`。
- 普通全量 pytest 为 1507 passed、4 skipped；coverage 全量同样通过。四项 skip 均为当前
  Windows host 上既有 symlink 创建限制。
- docs-only diff 对配置的 `src/aiflow` coverage source 没有 executable lines；diff-cover
  sentinel 被确定性判为 pass，但不表示数值或 100% coverage。
- validate、scope、Ruff、format、smoke、unit、full regression、mypy、coverage XML、
  diff coverage、YAML parse、跨 chapter 计数、引用、Markdown links 与 `git diff --check`
  均通过。
- `REV-0038` 独立批准 current subject；第二项独立一致性复核为 clean。
- 未验证场景：Linux/macOS live Hook 安装、未安装 Hook 的客户端、IDE/GUI/remote Git、
  自由 shell 或系统级拦截；这些均为明确非声明边界，而非 Gate 放行依据。

## 审核问题

- 七个业务路径是否完整实现冻结规格，且没有扩展到源码、Policy、CLI、TASK-0021 或 Chapter 13？
- observe/pre-command/V2/recovery 文档是否与 current implementation 和 fail-closed 语义一致？
- P2-ESC-01/P2-HOOK-01 是否只在已有 evidence 的支持范围内满足两个 Chapter 12 exits？
- Chapter 12、overall、history、tracking、future phase 与 12/71/378/20/15 是否一致？
- current subject、正式 V1 evidence、`REV-0038` 与 code approval 输入是否保持同一绑定？
- 所有平台、Hook、shell、non-OS-sandbox、Chapter 13 和远程动作限制是否如实保留？

## 推荐结论

`APPROVE`（仅进入本地 code approval 与只读 Gate；不授权任何 push、merge 或其他远程动作）。
