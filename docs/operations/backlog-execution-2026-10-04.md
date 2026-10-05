# 当前待办执行：2026-10-04

所有者本次要求读取待办、设立持续目标并完成任务，授权必要的常规本地工作。持续目标已经
设立；本文件记录实际执行顺序、写入归属和完成条件。来源为
[当前七项待办](follow-up-backlog-2026-09-22.md#2026-10-04-收尾核定与下次待办)，
不将历史收尾窗口的“不启动”描述套用为本轮禁止准备。

本轮初读核定：主检出为 `f9deb7b`，分支 `codex/e4-followup-status`；三个用户未跟踪计划
保留。TASK-0064 在自己的工作区仍为 FAILED / REVIEW / V2，Missing
`retry_reason_or_escalation`；TASK-0063 仍为 BLOCKED / REVIEW / V2，Missing
`block_resolution`。两者 classification fresh、approvals current、evidence stale。
TASK-0064 未跟踪的原生 `evidence.json` 保留，不移动、不入库；原失败及 SPENT action 不改写。

资格执行前的本地实施阶段，TASK-0065 已有源码提交 `e64f6aa`、独立测试提交 `4f23e5c`
及 sync/本地证据提交 `8aefd27`。root 独立 111 个纯 fake 测试/0.58 秒、Ruff、format、
两源码 strict mypy 和 whitespace 通过，五文件固定字节保持。当时真实资格尚未执行，
独立 outer 预审的关闭再试与 deadline 缺口正在新版本修复，完整 V2/动作批准仍未完成。
回读类型错误原件及另立诊断均保留，不重写检查输出。

### 2026-10-05 单次资格 007 的限定矩阵接纳

007 在三路独立静审后只执行一次，UTC
`2026-10-05T10:34:03.330Z–10:38:14.760Z`。真实完成工具 `e4d681` 返回 0，
controller exit 0；单次 consumer `fc9282` 返回 0，结论为
`PASS_LIMITED_REQUIRED_REAL_MATRIX_ONLY`。34 项必需生产 case 及三个控制完成；
两项 console 因实际 `AllocConsole` 返回 false / WinError 5 保持
`UNMEASURED_CONSOLE_RESOURCE`，不计入通过项。未经测量的平台和异常 OS fault
收尾仍为 UNKNOWN。原节点源码、断言、时序和生产五文件没有修改。

root 退出立即观察的原始 QPC 为 `3558206820201`，frequency `10000000`，
high-resolution true，距原 300 秒矩阵期限尚余 `68.3302239` 秒；这是真实退出
观察的上界，不是精确退出时刻。537 份 raw 输出及 539 个精确输出名称核验一致，
完整 consumer guard 8388 项相等；root 的 7236 固定输入与 32 prepared 文件
前后 snapshot SHA 均为
`4f20cc7ce416ca83b9a64b8a4693ed9c361ba8161b5b5d6e8802f8a6ecca50bd`。
实际案例与生命周期两路非作者复核均无阻断 finding，分别封存为
`windows-qualification-actual-case-review-007/report.json` SHA
`4afe87d4e6793e83b016af1629223b6a9b2f210ddb0d2beb5f8b6bdc63336592` 和
`windows-qualification-execution-lifecycle-actual-review-007/report.json` SHA
`9e68820c42d6f892597e37a3f66cbd69b3efe5d8b63e6d30861dc59243aac907`。
29 份正常释放回执的 `cleanup_complete=false` 原值保留；正常存活子进程的自然退出
不改写先前状态。003、005、006 的实际失败及原件仍保留，本次不重跑旧请求。

新的具体单次 mutation 提案位于 `task0065-mutation-action-proposal-002/action.json`，
规范 SHA `5ec33e688add3f138a1fd4a912ce563e67dd47efd7269bec947bab5712da496a`，
有效至 `2026-10-06T10:54:45Z`。独立行动审查结论仅为 `GO_FOR_REQUEST`，报告
`task0065-mutation-action-review-002-external-001/report.json` SHA
`3db0477b4210359037018245b75cb858c579cc5c18af8541cc2584ee9737178c`。
具体行动及本次原生临时清理正在请求真实批准，尚未记录批准、消费或启动完整 V2。
固定五项、每 detector 60 秒、DEVNULL 元数据范围及原 14 检查/预算保持。
native V2 自身不独立强制 CI 的 85% 总覆盖率和 whitespace；之后须从同一 coverage
数据检查 85% 并检查完整变更 whitespace，发布仍须当前完整 CI 证据。

预算计数器的薄外层/入口草案 `budget-current-c7-implementation-draft-001/` 完成
49 项纯检查，两名非作者分别复核入口身份和外层时钟/收尾。实际 007 接纳引用仍未
写入草案；只有另建最终封存包后才可进行新的单次诊断。未运行原 counter 三节点、
完整预算或 mutation。TASK-0065 仍为 IMPLEMENTING，Missing `implementation_result`；
TASK-0066 既有规格决定待回复，七项目标仍 active。

### 2026-10-05 单次资格 006 的局部结果与 parser 比较失败

006 三路独立静审实际完成后只执行一次，UTC
`2026-10-05T04:12:38.958Z–04:14:37.169Z`。完成工具返回 1、controller exit 2；
三个前置控制及 CPython 3.11 的 16 个生产 case 返回各自范围内 PASS，包含原
timeout 函数的实际调用、自然完成 live child 和 venv timeout tree。随后 CPython
3.13 的首个原 timeout case 在执行函数前报 `AssertionError: original node AST changed`，
worker exit 2。矩阵没有完成，没有 positive consumer、完整 V2 或整体任务验收。

最后 case 的 stderr 为 0 字节，主因在 `worker-result.json` 的 `error` 和
`worker-failure-terminal.json` 的 `primary`，不能因 stderr 空或错误读取
`primary_error` 字段而宣称无异常。该函数在 AST guard 前已 import 部分 aiflow
代码，但原测试的 compile/exec/call 尚未发生。root 前后 7191 固定输入及 28
prepared 文件的完整 snapshot 字节相同；283 个实际原件的前后 hash、属性和名单
一致，索引为 `windows-qualification-root-failure-diagnosis-006/`
`facts-and-original-hashes.json`，SHA256
`fe0b2535ccf6076d29b4bf87da7ee5dbd5054aa1da2bf28441accf0d6832d6a8`。
实际 root/case 目录分别为 `windows-qualification-root-execution-006/` 和
`windows-qualification-execution-006/`，本次失败请求不重跑。

独立的两个纯 stdlib parser 诊断读取相同 source：3.11 的 default AST dump SHA256
仍为原绑定 `b54756d0d32a138bd3b5526aaafe8f613faff2a882d53b6d271efb6a27b31803`，
3.13 为 `88f632d205e07b713485c0c22c134e00af5ad17d96823dd773589d3e7e2c545d`。
测试全文件 raw hash、按 worker `read_text` 通用换行语义提取的 753-byte 函数文本
hash 保持；物理 CRLF slice 与该规范化文本的字节数不能混称。[官方 AST 文档](https://docs.python.org/3.13/library/ast.html)
记录了新增字段及 default dump 的空字段显示差异。非作者完整字段分解已封存，
报告 SHA256 为 `2d72a667cb44bbd2f3095040954e0fe38adff86d82d6b66b547ce5ed3c7cb0a7`：
共同字段的值、类型及顺序相同，schema 仅新增空 `type_params`，默认 dump 则省略
原空列表。实际资源终态仍由另一角色核查，不把该表示差异写成生产故障或完整
预算结论；17 个必需生产单元和两个 console 单元未启动。

本次并行 **3 名 sub-agent** 分别负责作者 parser 根因提案、非作者同 source/字段
语义核查和非作者实际资源收尾；主 agent 独占原件索引及文档。旧三个 review 线程
遇到模型 capacity、未产出结论，不算 GO；新的默认设置 case reviewer 已实际
完成 006 静审，没有切换模型。之后的新修复仍须独立冻结、复审、另立单次请求。

发布库存的新快照为 27 个静态提交建议、39 个路径（24 历史账本、15 文档），
三条原分支均继承禁发 `52474d9`。另立干净基线工作区后，15 文档已按源 Git blob
投影并暂存，尚未提交；发现五处相对链接依赖未纳入的账本或用户未跟踪计划，
因此不称完整可发布包，也不复制该用户计划或未经治理的账本。外仓最新 18 GET
窗口 UTC `03:33:32–03:35:42` 的 CI/runner 状态未变；两条 repo metadata 临时
clone 字段已在新请求最终封存前脱敏，旧原件不改，私有 runtime 不进入发布包。

### 2026-10-05 单次资格 005 失败，事件参数冲突另立修复

005 在三路独立静审通过后实际只执行一次，UTC
`2026-10-05T03:24:43.952Z–03:24:53.301Z`。完成工具返回 1，控制器实际 exit 2；
首个 `outer-normal` worker exit 3 为其预定控制值，但 controller 在记录成功事件时
发生 `TypeError: execute.<locals>.emit() got multiple values for argument 'kind'`。
事件名与 dispatch 类型同时绑定同一个形参，故 `PASS_CONTROL_ONLY` 只是未获终态
验收的提议。timeout/crash 控制、34 个必需生产 case 及完整 V2 均未启动。

root 前后 7128 个固定输入和 27 个 prepared 文件的完整 snapshot 字节相同。实际
outer receipt 报告 parent signaled、active processes 0、terminate 0、各自有 handle
close 单次；已转移 child handle 的 acquisition 完整且单次确认关闭。这些是该失败
控制的范围内资源证据，不代表完整资格通过，也不改写未知字段。25 个实际原件的
前后字节、哈希、文件属性和精确名单相同，索引位于同一树外 runtime 的
`windows-qualification-root-failure-diagnosis-005/facts-and-original-hashes.json`，SHA256
`0229a1b8a75b2b07af75032caa831ee96108fa3ca261c24ab828e5deacb53bba`。
实际 root/case 原件分别保存在 `windows-qualification-root-execution-005/` 与
`windows-qualification-execution-005/`；005 请求不重跑。

本阶段并行 **3 名 sub-agent**：两个分别只读核事件故障和资源终态，一个独占新的
006 请求作事件形参最小修复与纯 fake 检查。主 agent 负责独立原件索引、原生状态、
文档和之后的新单次入口。006 不改生产五文件、worker、原节点、断言或时序；修复
→ 冻结 → 三路独立审查 → 新单次真实资格 → 终态验收仍串行，完整 V2 尚未启动。

I1 revision009 已独立差异复审为 `GO_FOR_PREPARATION`，仅确认日志尾 seek、native
错误主因及 observer 异常下 close 路径的三处修复，报告 SHA256 为
`e8d77bb9091de030e82bf865425f59596ce7d5443811b66071997544bcfdd63f`。
24 个纯 fake 检查不代替 OS/copy/VM/SSH 验证。原生 status 最新回读仍为 TASK-0065
IMPLEMENTING、Missing `implementation_result`；TASK-0066 WAITING_FOR_SPEC_REVIEW、
Missing `spec_approval`，两工作区 tracked 干净。既有 spec 请求仍待真实回复。

### 2026-10-05 验证环境隔离及资格 004 静审

主检出原 Python 3.11 环境的 editable 安装指向主检出源码，而原生验证子进程会清除
`PYTHONPATH`。因此另外创建 TASK-0065 专用环境，沿用实际 27 个依赖版本，正常安装
候选工作区的 editable 包；最小 `PATH`/`SystemRoot` 下的只读来源诊断 exit 0，确认
`aiflow` 来源为候选源码、pytest 来源为新环境。安装前后旧 1602 个固定输入及依赖
metadata 的字节、哈希和记录属性均相同；候选工作区仅新增被既有规则忽略的 egg-info，
tracked 工作区干净。该诊断没有启动 V2、mutation 或资格 case。

环境证据位于 `${RUNTIME_ROOT}/harness-model-backlog-20261004-001/`
`task0065-native-verification-environment-001/`，`after.json` SHA256 为
`45796b27dc36034c3369a62c98c32b1fcb0f8fa305d8174ad2655cac544164c1`。
新环境的 3251 个文件已纳入资格 004 的绑定；该包冻结 27 文件、7086 输入、1085 项
启动缺失约束和 34 个必需 case（原 14×2，加三个实际 venv 目标各两个 case）。
绑定 SHA256 为 `22f8dcb95faed1f8cfe333058a36224f3d58ffaa7ddffb50e28dc5002d602b1c`，
manifest 为 `e34d8a531720ce757759429bff8f2f34ab39c3faa0b80264a85fd7f59c998110`。

三路独立静审分别负责身份/启动、资源/期限、case/终态。case 角色通过，资源角色发现
`normal-live-child` 的具体可恢复缺口：远端 DuplicateHandle 已成功、只有出生记录
rename 失败且独立日志仍健康时，现有记录没有远端句柄值，接收端不能恢复登记。
失败路径不会报告 PASS，但不满足已取得句柄的完整账本约定，故 004 不执行。新 005
仅复用已有 acquisition 协议修复该路径，保留自然完成证明、所有原断言和时序；原
753 字节 timeout 节点、生产五文件、004 冻结原件及失败 003 均不改写。
本次修订并行 **1 名 sub-agent** 独占新 worker，作者负责串行装配/冻结；之后仍经
**3 名独立 sub-agent** 差异审查，主 agent 负责新单次入口、实际执行和终态验收。

预算请求 002 两个静态 P1 已修正，独立复审为 `GO_FOR_PREPARATION`，报告 SHA256
`f0e468555f2921da8568390f7e266935972feb28a232d3a13e02ca64880b3c02`。它只准备三个
既有节点的 Git 调用意图计数与 phase wall time，outer 绑定仍 null、执行保持 blocked；
没有完整预算已解决的结论。I1 revision008 的资源审查另有日志 API 返回值和原 native
错误主因保留缺口，原件封存，009 在树外修订；TASK-0066 spec 决定仍待真实回复。

### 2026-10-05 单次真实资格失败及 I1 原生准入

资格包 003 经三路独立静审后仅一次实际执行，UTC
`2026-10-05T01:24:01.124Z–01:24:02.253Z`，控制器 exit 2。第一个 `outer-normal`
控制进程在 self birth 检查失败；接收端随后缺 transfer acquisition ledger，保持
`UNKNOWN_ACQUISITION_REGISTRY / complete=false`。timeout/crash 控制和 28 个生产
case 均未启动，原 timeout 节点没有执行。失败清理原件报告仅自有 outer Job 一次
terminate，parent signaled、active processes 0、各 close 单次；空剩余句柄列表不能
替代完整登记证明。前后 1602 个固定输入匹配，本次请求不重试，完整 V2 未启动。

root 原件目录为 `${RUNTIME_ROOT}/harness-model-backlog-20261004-001/`
`windows-qualification-root-execution-003/`；actual case 原件在同根
`windows-qualification-execution-003/`。root 新增事实/原件哈希索引为
`windows-qualification-root-failure-diagnosis-003/facts-and-original-hashes.json`，
SHA256 `13c9a71f4ae3af27d95dbd13a2efaec81d084c94404b4fd3eff3cf88351a4a8f`。
独立诊断确认 raw JSON 整数精确；venv redirector 会新建执行解释器，raw launcher birth
与脚本 self birth 等同的框架假设不可接受。该 worker 实际 self 值未写入原件，保持
未知；这不是生产候选故障或预算耗尽的证据。新请求另行冻结，不移除出生身份检查。

该诊断阶段启用 **3 名 sub-agent** 分别核控制器、资源终态和 case 身份协议；作者
另安排 **2 名研究 sub-agent** 核官方 launcher 与 ABI。独立预算测量准备和 I1 admission
投影准备各启用 **1 名 sub-agent**，分别独占新的私有叶目录；主 agent 负责原件索引、
状态整合和文档。新资格修复 → 冻结 → 独立审查 → 单次真实资格 → 原生完整 V2 串行。

TASK-0066 已实际 classify/freeze 并记录非作者正式 Design Review APPROVE，阶段提交
`434bf68`。冻结 spec SHA256 为
`dcd67fa8220ad10a4c0cc62c5975a5c4f2cfe77b523e9c714b5fe21e4f5eec7f`；
native 为 WAITING_FOR_SPEC_REVIEW / REVIEW / V2，分类 fresh，Missing `spec_approval`。
spec 批准请求已提出但尚未收到回答；cold copy、VM、SSH、服务和 CI 动作未获批或执行。
原准备提交 `826d063` 因 native 要求 classify 时 HEAD 等于初始 base，已通过保留 durable
ref 后 soft reset 恢复准入基线，工作文件保留；修正记录在自身 preparation 目录，
旧提交可恢复。没有改写既有 F/TASK-0064 或失败证据。

并行追加的独立工作为 **3 名 sub-agent**：offline 诊断静审、I1 边界静审、外仓实时
只读刷新；与原五个职责分离、没有共享写入。静审结束后，原 Windows 作者改为独占
I1 新请求实现树外目录，原资格作者独占新的可执行资格 controller 目录，独立 reviewer
只读冻结草案。所有 OS 资格须先完成 outer 审查/自资格，VM 高风险动作须待具体批准。

## 执行顺序与完成条件

| 项目 | 本轮工作及完成条件 | 当前状态 |
| --- | --- | --- |
| Windows 超时处理 | 以封存候选形成精确生产 scope、支持矩阵、错误/资源语义和安全基线；另建治理 Task，真实 Design Review、Missing 所需决定后实施并完整验证 | TASK-0065 实施已提交；007 必需 34 项及三个控制限定接纳，两 console 未测得；具体 mutation 提案待批准，完整 V2 未启动 |
| 完整测试预算 / TASK-0064 | 以原 run 和耗时原件定位累计成本；性能变更单独准入，实际确定候选依赖后合法承接或恢复；全部 14 检查、原预算、85%/90% 保持 | schema 002收益不足不采用；offline caller 002已完成，当前完整预算仍待实测 |
| F / TASK-0063 | 区分原历史窗口的已执行导入与原生收尾；确定真实恢复 scope 和依赖，按 native Missing 推进；新 context 如需新真实来源则独立取得 | BLOCKED，恢复方案核查中 |
| 外仓双通道 / 实际应用 | 只读刷新准确 SHA、完整 CI 和 runner；实际 POSIX 恢复或 Apply/部署须先有精确目标与独立准入 | Windows success，POSIX queued/0 steps；Linux 停用约定已定位 |
| I1 / I2 | 从实际使用缺口选择生命周期或可信目标；按幂等、权限、完整等价验证及可执行恢复条件准入 | TASK-0066 正式 Design APPROVE，WAITING_FOR_SPEC_REVIEW；Missing spec_approval，VM/动作未批准或执行；I2 新目标未选 |
| E5 / I5 / Phase 3 / Phase 4 | 分别形成最小需求和样本/隐私/度量/真实 V3 边界材料；按独立进入门选择方向，缺失不补造 | 61 公开 task 样本盘点及缺失规则草案已备，真实进入门未满足，实施未启动 |
| 远端发布 | 核对累计候选及本机内容，选择排除配置 `52474d9` 的干净基线；审核和准确 required CI 后按具体动作授权发布 | 发布清单核查中，未写远端 |

## 并行与串行

第一阶段启用 **6 名 sub-agent**，分别只读研究 Windows 设计、安全测试预算、F 恢复、
外仓实时证据、后续阶段进入门和累计发布清单。各 agent 输出调查结果，无共享文件写入。
主 agent 独占本文件和权威入口，核 native 状态并整合。

第二阶段使用 **2 名新增 sub-agent**，分别独立审查安全基线和准备文档；Windows 作者
独占新区唯一测试文件，其余文档作者各自独占一个新文件。schema 测量准备复用原预算
研究 agent，实际执行必须等待脚本独立核对。安全 tests/docs 与治理源码/账本分开。
每个治理 Task 的写入者唯一，禁止并发修改同一文件或版本绑定。

所有者批准规格后的实施阶段并行 **5 名 sub-agent**：一个独占两份生产源码、一个
独占三份安全测试、一个准备独立真实 Windows qualification、一个准备累计成本
offline caller 分区、一个准备非作者审查矩阵。后两者与实施无共享写入，资格产物
只在树外受控 runtime。主 agent 独占原生任务机械状态、主文档、整合和阶段提交。
源码/测试接口先对齐；固定候选 → 纯 fake/静态检查 → 独立技术审查 → 实际资格 →
新单次 action 与完整 V2 → 正式 Review/finalize/code/Gate 串行，不以准备矩阵替代审核。

设计整合 → 安全基线 → 新治理准入 → Design Review → 必需规格决定 → begin → 源码实现
→ subject sync → 具体单次 action → 完整原生验证 → Implementation Review/finalize/code
决定/Gate 串行。正式完整验证期间冻结源码与 refs；不能将局部通过写成整体通过。
F 准入、真实匹配来源、preflight、record、原生收尾也串行。

E5/I5 准备和外仓只读核查可与本地设计并行；后继实施只在进入门满足后开展。最终发布的
候选、审核、准确 CI、protected merge 与独立远端证明串行，不复用 PR #44 旧批准或 CI。

## 授权记录与保留

本次授权用于完成待办所需的常规本地准备、任务机械步骤、可恢复修复、检查和本地提交，
不改变运行时权限设置。项目规定的真实 spec/code 决定以及删除、push、merge、部署、
凭据导出、付费调用仍按具体材料和类型分别绑定；技术审核不替代人类风险决定。
请求决定前完成可审查材料并运行 native status，只请求实际缺项。

既有记录与日志追加式保留；不把旧失败、取消报告、未执行 POSIX、未选择需求或未来阶段
标为完成。实现和验收结果在发生后追加到本文件及相应原生任务，持续目标保持 active。

## 本轮已经完成的准备

- 安全基线已在独立干净工作区提交 `d4f72ac`，作者检查 20 passed / 18.52 秒，独立
  检查 20 passed / 1.40 秒；Ruff、format、whitespace 均通过。唯一新增测试模块，
  原生产源码与原测试未改，无 skip。所有 launch/timeout cleanup 均 fake，无 OS 资格结论。
- [Windows 生产设计](windows-production-design-2026-10-04.md)明确两个原候选资源保留
  缺口；TASK-0065 已在真实 base `ab07bcd` 准入为 REVIEW/V2。首轮独立 Review 的
  三项 finding 原样保留，修订经 spec_changed 升级/resolve/classify/freeze；新规格采用
  公共 Win32 backend、12 公共字段和 8 个原子 active+retained 槽位，不以 patch/build
  或未测缩小支持。新 context 独立 APPROVE 已原生记录，准备提交 `1d4731c`；
  所有者明确回复“批准”，native approve/begin 已完成，提交 `01949da`，状态
  IMPLEMENTING / REVIEW / V2、approvals current，Missing `implementation_result`。
- [F 后继决定](f-successor-decision-2026-10-04.md)核定原真实导入已发生，但当前五个
  测试路径越界且 HEAD 不等于 subject，不能直接 resolve 后吸收新源码。
- [外仓现场证据](external-follow-up-evidence-2026-10-04.md)确认 dotfiles 新 SHA 完整
  CI 成功；r3s 新 SHA 的 Windows 已 success、POSIX queued/0 steps。Linux runner
  离线符合既有主动停用约定，受控恢复接单的实际材料仍在核查。
- [后续阶段合同提案](phase-entry-proposals-2026-10-04.md)已形成，阈值/资产/保留期等
  未冻结；[干净发布包](publication-package-2026-10-04.md)静态列明历史 32 路径及排除524。
- [预算决策](verification-budget-decision-2026-10-04.md)保留 schema/deepcopy 候选
  NO_GO；新脚本两名 reviewer 静态 PASS，唯一启动因绑定 workspace 不可用失败，
  未生成 claim/result/guard，速度 UNKNOWN，无换解释器或重试。原性能业务目录已
  不存在，F 业务目录为空，原 refs 仍在；消失原因 UNKNOWN。独立资产清单确认 F
  75 文件与 TASK-0064 的 61 native 文件及审计原件均匹配；原 DEVNULL streams 不可恢复。
- 新绑定 002 唯一实测完成、独立终态复核确认24对照/4隔离/106+6+1200调用，26输入
  producer guard相等。局部paired收益不足，不采用两种表示；cold elapsed字段覆盖
  问题原样保留，既非完整预算PASS也不修旧失败。下一证据为已有raw profile caller分区。
- I1原 guest已形成具体隔离冷启动草案，新增`restrict=on`只供BOOT身份核查、保留
  服务21/22状态；冷备、image检查、实际隔离及有效新action尚未执行/批准。

以上是具体准备及安全基线的完成，七项待办的生产、原生验收和发布仍按前述条件推进。
