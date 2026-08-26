# Review Package

## 审核目标

确认 TASK-0022 在 current subject
`893ce6bc7f31a20a964776bbbc2b7e5a2c280d90` 上完成 Chapter 12.5：受限
`aiflow observe` CLI/CI adapter 复用现有 observation parser、完整 current
task/Git/Policy/classification binding 与 deterministic non-authorizing decision core；
CLI apply 保留既有 task-local audit、幂等和单调升级，CLI dry-run 与 detached CI 保持零写；
支持范围内的 Hook、CLI 与 CI 只在 decision semantic fields 上证明 parity。确认状态投影只
完成 12.5，并如实保留 shell、Hook 安装和平台边界。

## 背景

任务 base 为 `65f2fb4140027ba09c6f0cbf710b26ce87a6cc5b`，确定性分类为
`REVIEW / V1`。current classification input SHA-256 为
`72068c839a2f9e46dec59e3a9c2f1f84b2715d1bd11663fd8ddbb7867f9500c7`，
冻结规格 SHA-256 为
`c73fb731b0fa1f1577203e6087b97079297b27ebdf99e68f654dc8c6034a7cc1`，
active Policy SHA-256 为
`f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`。

设计审核 `REV-0032` 通过后，实现形成 H1
`f977b977dd47482e77bbc2067c9e1a41de470f41`。H1 正式 V1 通过，但独立
`REV-0033-r0001` 对 observe help 的精确协议提出 RF-001；该 finding 在
`REV-0033-r0002` 解决。remediation subject
`741790f14ccdc79748a1c83a83536c88fd6095bd` 重新取得正式 V1 和投影前独立审核
`REV-0034` 后，才完成 12.5 文档/状态投影并形成 current subject
`893ce6bc7f31a20a964776bbbc2b7e5a2c280d90`。

current subject 随后重新取得正式 V1。最终 implementation review
`REV-0035` / context
`f424e758b3519848b9d0ea68ddf07df81ad9c631bd20869d1aff7085d1538b0b`
为 APPROVE、findings 为空；此前 H1/REV-0034 只作为投影时序前提，没有替代 current
subject 的验证与审核。

## 代码地图

- `src/aiflow/observation_service.py`：公开只读 `evaluate_observation` 复用完整
  current binding；`apply_observation` 在任何 ledger read 前拒绝 CI 并委派 evaluator。
- `src/aiflow/observation_adapter.py`：封闭 apply/dry-run/ci mode、source 与 actor
  组合，严格读取单个本地 UTF-8 JSON object，返回不回显调用者载荷的 canonical result。
- `src/aiflow/cli.py`：精确暴露
  `observe TASK-ID --input FILE --mode {apply,dry-run,ci} [--actor ACTOR]`；
  有效 observation 固定 exit 2，无效输入或状态 exit 1。
- unit tests：覆盖 evaluator 完整绑定和零写、CI persistence guard、严格 JSON/重复 key、
  mode/source/actor、输出最小化、apply replay 与 mutation helper 不可达。
- `tests/integration/test_observation_parity.py`：覆盖五类 observation、四 route、V0/V1/V2，
  区分 source-sensitive digest 与 semantic parity；实际 Hook E2E 只覆盖 pre-commit
  scope fact 和 pre-command 六类 Policy 禁止 action，并验证 in-scope 无 observation。
- Chapter 12 implementation doc、chapter state 与 overall state：只完成 12.5 五步，指针
  移至 12.6，计数为 70/71 tasks、373/378 steps、14 evidence items。

## 语义变更

`apply` 只接受 `source=cli` 且要求非空 actor，并只委派
`apply_observation`。`dry-run` 只接受 `source=cli` 且禁止 actor；`ci` 只接受
`source=ci` 且禁止 actor，两者只委派只读 `evaluate_observation`。adapter 不搜索
active task，不伪装 Hook source，不从 stdin、环境、shell、argv 或网络接收事实。

parity 只包括 decision 的 schema version、disposition、reason、current route/V、
`execution_allowed`、required conditions 和 target route。observation digest 包含 source，
因此不同入口的 digest 应不同；mode、ledger effect、apply event reference、JSON 字节和文案
不属于 parity。所有 decision 都保持 `execution_allowed=false`，不得被解释为执行许可。

## 证据

- 已验证：canonical evidence SHA-256：
  `9054a208781ba61ff65cd03b30fee6e58168a8865c49ee7ebc0e4dc4e723fd58`；
  evidence 文件字节 SHA-256：
  `3bfbc6ae787b9bdba25bb12fc09265a84c8542f00da150dc31cb351c80338303`。
- current subject 的 V1 为 10/10 required checks passed，`unverified_scenarios: []`。
- 普通全量 pytest 为 1507 passed、4 skipped；coverage 全量同为 1507 passed、4 skipped。
  四项 skip 均为当前 Windows host 上既有 symlink 创建限制。
- diff coverage 为 94%：110 changed executable lines，6 missing，门槛 90%。
- validate、scope、Ruff、format、smoke、unit、full regression、mypy、coverage XML 与
  diff coverage 全部 passed。
- 投影前 focused remediation suite 为 99 passed；RF-001 解决历史完整保留。
- 未验证：Linux/macOS live Hook 安装、未安装 Hook 的客户端、IDE/GUI/remote Git、自由
  shell 拦截、12.6、P2-ESC-01/P2-HOOK-01 与 Chapter 12 exit checks。

## 风险

- 当前证据运行在 Windows 临时 Git/task ledger 和 wrapper entrypoint；不证明 Linux/macOS
  live Hook 安装或全部 host 行为。
- Git Hook 无法拦截未安装 Hook 的客户端、IDE save、GUI/remote Git 或绕过 wrapper 的调用。
- pre-command 只接受结构化 canonical action/target，不能安全解释 PowerShell、cmd、bash、
  alias、pipe、redirection、quote、wildcard、variable/command expansion 或任意自由 shell。
- 系统不是通用命令执行拦截器或操作系统安全沙箱。
- 12.6、P2-ESC-01/P2-HOOK-01、CH12-EXIT-01/02 和 Chapter 12 完成状态保持 pending。
- 未执行且未授权任何 push、merge、deploy、delete、secret export、package publish、凭据、
  网络、付费或其他外部动作。

## 审核问题

- observe 的显式 task/input/mode/actor 协议和失败优先级是否符合冻结规格？
- dry-run/CI 是否对完整 task 目录零写，apply 是否只沿用既有 audit、幂等和单调升级？
- parity 是否只比较 semantic fields，并正确排除 source-sensitive digest 与 mode/event metadata？
- Chapter 12 是否只完成 12.5，计数/指针和所有平台、shell、Hook 边界是否如实？
- current subject、正式 V1 evidence、REV-0035 与 code approval 输入是否保持同一绑定？

## 推荐结论

`APPROVE`（仅进入本地 code approval / Gate；不授权任何远程动作）。
