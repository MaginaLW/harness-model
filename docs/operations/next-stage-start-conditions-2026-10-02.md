# 下阶段启动条件：2026-10-02

## 2026-10-08 Task65 Action005 revision002 已独审，等待具体批准

当前 source `499f00ff74e6c169defe81e46899b98c97221fbc`；机械同步 commit `f988bbb3280eb5ce889b4cb1bab609e072501640`。
2026-10-07T16:35:38Z 原生查询为 IMPLEMENTING / Missing implementation_result；规格批准与当前 Design APPROVE 保持。
新 Action005 revision002 canonical `a51f8ed47b49e3bac71aa91cc206d96e4ba416d306e068c4e4b41d1525efee46`。
到期 2026-10-10T16:25:45Z，启动余量至少90分钟；完整14项/原4110秒逐项预算、CI85%同新run完整XML与90%diff、固定5项baseline/mutant各60秒DEVNULL保持。
具体动作 `${RUNTIME_ROOT}/task0065-action005-exact-preparation-002/action.draft.json`；启动器 `${RUNTIME_ROOT}/task0065-action005-native-launcher-preparation-002`。
非作者独审为 APPROVE_FOR_ACTION_APPROVAL_REQUEST，0 unresolved，Execution_GO=false；`${RUNTIME_ROOT}/task0065-action005-independent-review-001` manifest `8080d1c2b86c1e15bf3edfc86434a945896938088db3e5ff4763fe0f50db1873`。
原算法有界清理仅覆盖本次新建pytest容器、system-temp下新mutation工作区及关联新Git登记、owned detector进程树；排除父目录、旧空间/登记及历史证据。
旧 revision001 `b87880e73793cfb0b457f7f37166707ca0dd9db862088b1476d4530d37efbe55` 的 F01/NO_GO 原件保留；revision002仅静态修正原清理范围误述，不构成清理执行证明。
上述16:35查询对新canonical的 matching current action grant 为 null；原 Action004 仍 SPENT，旧失败保持。
本阶段仅支持请求人类批准，尚未获得 Action005 执行授权、物化动作或启动验证；新批准及 fresh admission 仍需按原生事实完成，不重复请求仍有效的规格批准。

## 2026-10-08 核定：Task68 完整验证失败，Task65 超时观察与局部 QA 已提交

以下为本地 2026-10-08 的证据核定；运行及外仓观测时点均以 UTC 明示。
Task68 唯一完整原生 V2 `run-20261007T131235907044Z` 于
2026-10-07T14:01:34.5646008Z 终态：14 项中 10 PASS、4 FAIL。
regression、coverage、integration 分别在 900032、1200047、600031 ms 超时；
diff coverage 因同 run 的 coverage.xml 缺失失败，85% 总体与 90% diff 未获证明。
原生 evidence SHA256 `4795b8de1f36149c058a834da9c6f404c3e47e9b80c8a0b146ed5a04cd71a49b`；
Action001 `0463b271fb460b7df626b341640a035a11ed87f02385910fe1371ea5f25c6b89`
已消费且不可复用（SPENT）。原执行包封存 59 payload / 60 files，manifest
`ec0a1e9d9fa7eb4e7275d8668c16df08496b5c550ff29edf67ed7e0077e6d1d5`，
位于 `${RUNTIME_ROOT}/task0068-native-v2-action001-execution-001`。
机械诊断恢复 event21（2026-10-07T15:50:21Z）、commit
`c16e77f3f23768a81f857633462eb5ccbdf23655` 使任务回到 IMPLEMENTING；
该阶段 status 缺 implementation_result。旧失败、SPENT、20-event 前缀及三条批准保留，
source `21f90a59940b888e7233b76fc3ee43f915f378ad` 保持；此恢复没有执行第二轮完整验证。

Task65 首次通信超时的可选观察已提交，治理 source commit
`499f00ff74e6c169defe81e46899b98c97221fbc`；安全测试独立 commit
`3489113fd95d3ecf02eaca12d8b3edaee9113999`。仅按既有读取顺序保存标量状态和
monotonic 时间，不记录原始输出或敏感信息；它不是截止瞬间的原子采样，不能倒推旧超时因果。
最终 94 项 fake-only 合约测试 PASS（0.49s），Ruff、format（136 files）、mypy（45 files）PASS；
首次 format FAIL 原件保留，修正仅改两处换行且完整 AST 相同。
非作者静态及格式后独审为 STATIC_APPROVE，0 unresolved finding；格式后独审 manifest
`6246a692ec0a7ff6ca575e554070428ecf5be1d3e46e93b541d8636caece84a8`。
证据分别在 `${RUNTIME_ROOT}/task0065-timeout-observation-local-qa-001` 和
`${RUNTIME_ROOT}/task0065-timeout-observation-formatted-review-001`；QA 仅封存顶层常规文件，
保留的 mypy-cache/temp 子树未读取、未哈希。上述结果不构成完整 V2、CI 85%/90% 或 Windows
OS qualification；旧 Action004 已 SPENT，新的完整验证仍须具体 Action 批准及 fresh admission。

Task68 单一既有节点一次 cProfile 实测为 1 PASS（pytest 2.90s、进程 elapsed 3.375s），
`${RUNTIME_ROOT}/task0068-single-node-profile-001` 为 PARTIAL_DIAGNOSTIC_PASS，
12 payload / 13 files，manifest `d35821f620152971a4815ee0b89abeb27a148f3cde0dfb3ddad333b29879f5c9`。
该节点生产 Git 30 次 / 0.823s，fixture Git 13 次 / 0.619s，contract validation
159 次 / 0.558s，其中 schema registry 0.389s 属嵌套成本，不可相加。
原 timeout 的 active node 与共同根因仍 UNKNOWN；尚无经证明的成本优化，原 schema 成本优化
NO_GO 与 Git 新鲜度边界保持，不扩大 Task64/68 冻结规格，也不以该局部结果验收或恢复 Task67。

外仓快照010仅覆盖 2026-10-07T13:56:57.5409514Z–13:58:01.1624122Z：
前后 main `3e1663ee998b886b63238fe197d9f7a2a3a4ce73` 相同，Validate run
[37630229655](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/37630229655)
为 in_progress / null；四项 check 均匹配该 head，gates success、三个 shard in_progress，
combined status pending / 0 contexts。required-status-checks GET 实际 HTTP404
“Branch not protected”；required names 与整体 required CI 为 UNKNOWN，不推断其他规则。
`${RUNTIME_ROOT}/external-current-head-ci-010` 已逐项核对 25 payload / 26 files，manifest
`e9fde2c2f1361ec0e66a55c3bfe623de4065888cd4f9d465fbb4323fee5ad8a2`；
此历史窗口不表示本次核定时远端状态，未新增 GET、CI dispatch 或远端写入。
七项目标尚未全部完成，既有进入、验收、发布门保持；下文原记录完整保留为早先时点。

## 2026-10-07 Task68 Action001 已批准并真实启动完整验证

人类已批准 Action001 revision002 的一次完整原生 V2；原生 human/action 批准为
2026-10-07T13:06:30Z 的 event17，Action canonical
`0463b271fb460b7df626b341640a035a11ed87f02385910fe1371ea5f25c6b89`。
批准账本阶段 commit `6564c53f0f165be71c1d964ced42dce3f88d9927`，
source `21f90a59940b888e7233b76fc3ee43f915f378ad` 与已批准规格保持。
实际 fresh native admission 后，封存入口唯一调用；预启动只读检查于13:12:33 UTC通过，
原生进程于13:12:34.2037473Z真实启动，managed PID37196，独立verifier为/root/f_recovery。
原生 run 为 `run-20261007T131235907044Z`；完整14项、原逐项预算及85%总体/90%diff
阈值、固定5项baseline/mutant各60秒DEVNULL与本次所有的有界清理保持，无整轮自动重试。
当前仍待原生终态、各项结果及同run覆盖率；启动、guard通过或局部测试不代表验收。
源代码、ref和账本由本次验证冻结；既有失败和SPENT原件保留。
批准与启动证据分别在 `${RUNTIME_ROOT}/task0068-action001-root-approval-admission-001`
及 `${RUNTIME_ROOT}/task0068-native-v2-action001-execution-001`；运行包尚未终态封存。
下文“请求批准、尚未运行”等段落保留为早先时点，不再表示当前授权状态。

## 2026-10-07 Task68 Action001封存独审并请求具体批准，Task65单节点实测完成

Task68 Action001 revision002及一次启动器已封存，非作者独审为
GO_FOR_SPECIFIC_ACTION_APPROVAL_REQUEST，0 unresolved finding；仅支持具体批准请求。
Action canonical `0463b271fb460b7df626b341640a035a11ed87f02385910fe1371ea5f25c6b89`，
expiry2026-10-10T12:00:00Z、启动余量至少90分钟，实际verifier为/root/f_recovery。
完整14项、原4110秒逐项预算总和、85 branch总体/90 diff、固定5项各60秒DEVNULL
及原本次调用所有的有界清理保持；没有新outer wall或整轮自动重试。
Data26payload manifest `24e36092a20a9e9ca3d2e7fba9b76fc6066c61b8a190ecb89217211780a21e93`；
launcher19payload manifest `fd82370e89260ed468adf74bdd5c486c337a12ee5c9ad13603c195ad1bd4ec8d`。
独审10payload seal `cfef087c6be44c43e23ece074a653da1a1723a0a461773f9061fb34489d37841`，
7001行/6992union与9trees双读稳定，只是启动前有限输入证明。
唯一非原生时间相等条件已修复、旧candidate raw保留，未重批或执行来凑同秒。

Root fresh status仅缺implementation_result，scope eligible且reason空、原spec批准current；
实际native API验证该Action DTO/canonical，但matching action approval仍缺。
原生Design context839d90b7与verifier context421356b8是不同schema，分别读取、不混用；
Root初读错误断言保留并修正，只读错误未触发批准/验证/消费。
已向人类请求这一具体Action批准；此记录时尚无新grant、final approved HEAD或fresh
launch admission，完整V2尚未运行，不以80项targeted PASS代替验收或Task67恢复。

Task65普通单节点 tests/unit/test_git_context.py::test_unparseable_head_is_rejected
一次实测恰1 PASS/2.13秒，setup/call/teardown、parentexit0、双EOF和关闭回执完整，
无超时/terminate/重试。封存20payload manifest
`36c89cdb14fb785d5692a5de115ff77cca9c18354a3d5bda1c439892bc4f1ef2`。
40项SHA/size不变；部分before大整数经过V8 Number丢精度，不能宣称全40精确stat。
节点不是已知旧active node，原三timeout根因UNKNOWN、10PASS/4FAIL、Action004SPENT不变。
以下各段保留历史时点，七项目标及其余验收、进入和发布门仍保持。

## 2026-10-07 外仓当前快照009：dotfiles main变化，当前requiredCI未知

官方GitHub仅8次只读GET，窗口12:27:30–12:28:35 UTC。dotfiles main变为
`3b11989d65046492034da08d947ea790d2a06b29`；API本次返回run35448682368为
2026-09-19的旧head eeedc461，4项jobs中3个shard失败、gates成功，与当前main不匹配。
当前main全部requiredCI仍UNKNOWN，不标当前main失败、不继承008的旧成功。
r3s main8898f48c未变、run37499267909仍queued，POSIX未开始、Windows成功；
Linux22 API offline原因未调查。没有重跑CI、主机/服务动作或远端写入。
快照 `${RUNTIME_ROOT}/external-current-read-009` 已封存31payload，manifest
`2fbe54d4ab95887d4604b7ee9ce388993b71fac6b6d1a442daae66a541cff8bc`。
分次latest1读取不代表全部required检查；I2互信/Apply和Phase4未获证明。
以下各段保留历史时点，七项目标和Task65/68最新本地结果仍按各自原件判断。

## 2026-10-07 Task65 完整验证失败并进入诊断准备，Task68 定向80项通过

Task65 Action004 的唯一完整调用已结束，实际 run
`run-20261007T110154452542Z` 为 FAILED，十四项10 PASS /4 FAIL。
regression、coverage、integration 分别耗尽原900/1200/600秒通信预算；
diff coverage 因本 run 的 coverage.xml 缺失失败。Unit2112 PASS、acceptance9 PASS
和固定五项 mutation PASS 不代替完整验收或CI85/diff90。原始证据SHA256
`623ad02f55dfb746626a458a967adcd933ed545998ef9cf8dddd85a7c5a27457`。
Action004 已原生消费、SPENT且不可复用；没有再次运行完整验证。
执行封存 `${RUNTIME_ROOT}/task0065-native-v2-action004-execution-001`，manifest
`43a5370a5bd35d083f3bdb895ad830445990cdb49703104d6c8d7e2ca9e65f75`。
启动器旧terminal canonical字段保留实际object写入缺陷；其他独立原件确认消费绑定，
不改写该字段、不以此撤销SPENT或授权重试。

Root按fresh status缺项机械begin，event33仅恢复IMPLEMENTING诊断准备，source不变；
阶段commit `2003f634c0b82b2a1fcc82bb684da1c35b833993`。原event32失败、全部旧原件保留。
独立只读诊断已封存，manifest
`dd4f82d590c500b54cb107f3b9e6b5b3592a4cffe7036a698cded6a126e3c13b`。
三项根因仍UNKNOWN：通信超时可由parent未终态或输出流未EOF任一项触发，
现有日志只有terminate/release后回执。最后打印模块不能确定active node。
后续仅准备单节点普通测量，不新增Action005或性能修复，不改变原预算和门禁。

Task68 独立一次修复后定向测试实际80 PASS，0失败/错误/skip/xfail/xpass，
真实Windows junction契约通过，旧三个Policy夹具案例全部通过；原77/3失败保留。
80项耗时88.32秒，独立结果封存
`${RUNTIME_ROOT}/task0068-classification-recovery-targeted-result-002`，manifest
`fce44d2252ac8245afd80c87de2f4440ff6fb7a4a8fad22091e8015a6407033e`。
实际结果report SHA256
`fade4fc0ff85b605a7fad9b16fbbdefe92f43c843be3d69356bb4cef2d18be75`。
OwnGov观察记录commit `2c75958680f5320bf5fe57f8fce7f64ffe9fac69` 后，native status
IMPLEMENTING/Missing implementation_result，classification fresh、approvals current、clean。
source21f90a5、原spec和唯一生产修改未变；定向PASS不是完整V2、CI85/90或Task67恢复。
Task68 自己的Action001与启动器准备中，尚无该具体完整验证动作批准或执行。

本阶段两名sub-agent并行负责Task65有限诊断与Task68动作/启动器准备；
独立非作者动作审查在封包完成后串行进入，root账本与文档提交串行。
七项目标active；F/Task64/Task67、I1/I2/E5/I5/Phase3/4和远端发布门未关闭。
下面各段保留历史时点。

## 2026-10-07 Task68 当前Design/状态恢复不代替验证进入条件

独立安全fixture单提交21f90a5、实际public sync/event10、当前绑定resolution与重新分类
已完成；当前Design REV0681/r1 APPROVE实际record，原规格与human批准仍有效。
root机械状态ack保留原行并标明实际operator，native begin/event16及OwnGov3df333e后
status IMPLEMENTING/implementation_result/fresh/current/clean。重复CLI输出以R100保留
原字节与metadata到preparation；native validate真正PASS，无validator绕过。

原77PASS/3FAIL保留；修复后实际tests和完整V2尚未执行。专用环境27pins/origin读回、
静态夹具独审及当前Design不构成验收。Task65本轮获批唯一完整调用仍待终态；Task68
targeted80和完整V2按资源依赖串行，必须准备自己的真实动作批准、独立Verifier和全部
14项/原预算/85+90；不能复制Task65 grant或以局部输出解除进入门。
F63/64、Task67、I1/I2/E5/I5/Phase3/4、七项目标和发布条件保持。
详见[当前执行记录](backlog-execution-2026-10-04.md)；下方保留历史状态。

## 2026-10-07 Action004 实际启动与 Task68 安全验证closure

Action004 新具体人类批准已原生event29登记，最终批准HEAD7853d52；独立本人verifier
唯一启动原十四项V2（run `run-20261007T110154452542Z`）。Unit raw局部结果已结束，
完整evidence/mutation/行动消费/85CI+90diff仍待本轮终态，不能提升进入条件。
原失败、已消费动作与全部旧原件保留，无自动重试。

Task68 同spec与生产源未变；旧Policy安全fixture独立task-free阶段只增加精确验证closure，
真实event9临时BLOCK。其actual sync/resolution/current分类/Design/修复后测试仍待完成。
七项、F63/64、Task67、I1/I2/E5/I5/Phase3/4及远端发布门均未据此关闭。
详见[当前执行记录](backlog-execution-2026-10-04.md)；下方保留历史状态。

2026-10-07 定向结果补记：Task68 source0dc233c已原生sync/event8，账本14fe42f；
80项实际77PASS/3FAIL、20新契约及真实junction通过，旧Policy dirty fixture兼容待解。
有限源码独审与static通过不当完整V2或解除Task67 BLOCK/I1资格；Task65 Action004
once001计数NO_GO、002仅最小修订准备，新grant/完整V2仍无。见
[当前定向结果](backlog-execution-2026-10-04.md#2026-10-07-task-0068-定向回归-7780旧-policy-fixture-兼容待解)。

2026-10-07 规格回复后补记：Task68当前spec已获真实用户批准，native event6/7与阶段
f48243c/e30fa8f已完成；当前IMPLEMENTING/implementation_result。单源码恢复入口修复已实现，
Ruff/format/mypy通过，targeted回归与源码独审进行中；不是完整V2、Task67解除BLOCK或I1资格。
Task65 Action004新动作及once入口独审仍待，不解除下方阶段/发布门。见
[当前Task68](backlog-execution-2026-10-04.md#2026-10-07-task-0068-当前规格已批准并进入实现)。

2026-10-07 封包补记：Task65 Action004 revision002仅完成非作者具体封包独审，
50有效检查/5 DTO拒绝向量通过，必要finding0；680新增pyc语义UNKNOWN、007仍为有限历史资格。
当前Task65 IMPLEMENTING/implementation_result，Task67 BLOCKED/block_resolution，
Task68 WAITING_FOR_SPEC_REVIEW/spec_approval且classifier未改。尚无新动作批准/完整V2；
once launcher、真实final HEAD与fresh launch条件仍准备，不解除I1或下方任何阶段门。见
[Action004封包](backlog-execution-2026-10-04.md#2026-10-07-action004-封包独审通过尚未批准或执行)。

2026-10-07 后续补记：一次prefix005普通诊断越过原review-record写入点并在原测试103行
的verify_task入口 STOP，未进入producer；Task65随后仅完成native机械begin/event28，
阶段41d6b59、当前IMPLEMENTING/Missing implementation_result。新Action004尚在fresh
环境与绑定准备，旧FAILED/SPENT保留，没有完整重试或I1资格完成。Task68仍待当前规格
决定且classifier未改，Task67仍BLOCK；不解除本页其余阶段门。见
[前缀与重试准备](backlog-execution-2026-10-04.md#2026-10-07-短路径前缀到达验证入口task-0065-重试准备)。

2026-10-07 追加：独立恢复任务 TASK-0068 当前 frozen REVIEW/V2 设计已通过独审并原生记录，
治理阶段提交 `c233b33`，clean/fresh、WAITING_FOR_SPEC_REVIEW / Missing `spec_approval`。
基线契约6 RED/14 PASS是实现前缺口，生产源码未改；它不解除 Task67 BLOCK、Task65失败或 I1 资格门。
普通 file-API 对照支持 review-record 临时写入的路径命名空间因素，完整超时共同根因仍未知；
新普通短父目录仅当前结构准入，未发生完整重试。真实规格、诊断和后续限制见
[本轮新增核定](backlog-execution-2026-10-04.md#2026-10-07-task-0068-设计已审查短路径诊断继续)。

2026-10-07 当前窗口补记：TASK-0067 已获批执行完整V2但原生 FAILED（10/14），
随后 BLOCKED / Missing `block_resolution`。I1公开接口已有实现不等于实际 lifecycle
backend资格；声明恢复及重分类治理限制另在准备，不解除下列进入门。
TASK65原FAILED/SPENT仍保留；普通前缀观察已捕获review record原子临时写入
FileNotFoundError，未进入verify/mutation，原完整超时根因及后续进入门仍未解决。

外仓008只读窗口 UTC 07:18:53–07:19:22：dotfiles 当前 main `b1da25da…` 的
latest Validate run37575131851 attempt1 已 completed/success，4/4 jobs success；
r3s 当前 main `8898f48c…` 的 run37499267909 queued，POSIX queued、Windows success。
这个精确 workflow 成功不表示所有 required CI、可信 backend、I2 扩仓或实际 Apply 完成。
下方2026-10-03“dotfiles当前准确CI”是历史窗口；来源及当前限制见
[008窗口](external-follow-up-evidence-2026-10-04.md#2026-10-07-当前-sha-的-dotfiles-validate-已成功r3s-仍排队)
和[当前待办](backlog-execution-2026-10-04.md#2026-10-07-task-0067-获批执行失败声明恢复已-block)。

2026-10-03：[报告回收](zcode-report-recovery-2026-10-03.md)完成指定核查，三份终稿附勘误，
ZN-02 取消/无报告，独立评估不替代原报告。[F 具体规格](f-real-import-acceptance-2026-10-03.md)
用新 design 目标承接受审对象，实际准入/context 及匹配来源仍依下列条件串行办理。
dotfiles 当前准确 CI 已补证成功；r3s 缺当前 SHA 的 POSIX 执行，不解除 I2 或阶段门。

2026-10-02 接续补记：四项准备任务已实际提交到 ZCode 对应项目，ID 和应用状态快照见
[任务安排的最新回读](zcode-next-stage-assignments-2026-10-02.md)。本轮发送阶段并行 3 名原生 sub-agent：
权限/审计保全、项目元数据、文档核查；主 agent 串行 UI 与统一提交。以下进入门保持，不因任务已提交而自动满足。

E4 已通过 PR #44 交付，TASK-0054/0055/0056/0057/0062 已在真实远端证明后关闭。
本页补充后继进入门，不重开已交付实现。现在可启动四项 ZCode **只读准备任务**，
详见[任务安排](zcode-next-stage-assignments-2026-10-02.md)；准备完成不等于实施门已满足。

## 逐项启动门

| 阶段 | 当前可开展 | 实施启动前必须齐备 | 缺项时处置 |
| --- | --- | --- | --- |
| F：真实报告导入验收 | 原件/绑定缺项核对和合法新目标准入方案 | 新的真实 native 目标、合法状态及冻结范围；准确匹配的真实未改 ZCode 原件；当前 context、来源/受审版本证据；受控输入及消费动作 | 不向 MERGED/FAILED 历史目标导入，不用 synthetic 替代 |
| I1：安装/更新/恢复复用 | 从真实使用或故障需求整理缺口 | 明确工具/生命周期范围、幂等和不重复注册、不覆盖凭据、不扩大 ACL、可执行恢复、验证和授权 | 无实际需求则保留；本次不另造 harness-env 工作 |
| I2：扩仓/平台 | 两个既有试点分别核对证据 | 每次选一个实际可信目标；权限/平台、检查等价性、准确候选完整 CI、可执行回退及目标项目准入 | 试点核对不等于新增接入完成，不自动扩到所有仓库 |
| E5 | 分别评估引擎采用、provider、可信执行 | 三个方向各自的实际需求/范围/授权；引擎的目标兼容验证；provider 的 adapter、身份/费用/数据边界；可信执行的身份根、服务授权/原子消费、固定参数、凭据托管、审计/恢复 | 不从 runner 接入、本地 actor/approval 推断完整能力 |
| I5 / Phase 3 | 进入门证据矩阵和冻结方案提案 | 下节三门齐备，并另行准入设计、Policy 影响评估、实施目录和验证矩阵 | 仍 not_started，不采集新费用/私密数据，不实现 V3、模型路由、信任评分或调度 |
| Phase 4 | 整理真实协调需求 | Phase 1–3 接口稳定、Phase 3 真实退出证据；量化多仓/平台/模型协调成本；真实暂停/恢复和集中审批需求；独立规格与准入 | 不启动队列、锁、租约、调度器或跨主机服务 |

## F：必须串行取得的证据

1. 协调者通过原生 CLI 准入**新目标**，明确 repository/stage/base/allowed scope，分类、冻结规格并生成当前 context。
   design 仅接受 `WAITING_FOR_SPEC_REVIEW` / `READY_TO_IMPLEMENT`；implementation 仅接受
   `VERIFYING` / `VERIFIED` / `WAITING_FOR_FINAL_REVIEW` / `APPROVED_FOR_MERGE`，且 evidence 新鲜通过。
   不向 MERGED 0054–0057/0062 或失败发布任务套用旧报告。
2. 目标准入后才安排匹配的真实报告，保留原始字节与实际来源证据。source 的 stage/base
   （implementation 还包括 subject）须与 target 相等；target 的 task/repository/stage/base/context
   （implementation 还包括 subject）须与当前 native context 相等。design 不添加 subject。
   source 仓库 UUID 或经核定的精确 locator mapping 必须对应 target repository_id。
   SHA 只绑定字节；真实会话、provider/model/version、受审版本按实际来源核定，不能改旧 task ID/context/source subject 凑匹配。
   provider/model/version 无法核实则 UNKNOWN；导入器不认证外部身份。
3. 按[导入接口](external-review-import.md)对受控输入执行零写 preflight，确认实际
   `ready` / `already_recorded` / `cleanup_required`；record 携带本轮 `--expected-preflight-sha256`，重读全部输入、目标和历史。
   路径、大小、严格 JSON、repository mapping、漂移和恢复继续遵守现有合约。
4. 退出记录应有真实来源、准确目标、实际 preflight/record、不可变追加、相同完整输入 no-op，
   以及版本冲突/漂移/错误目标零写拒绝证据。新反例按新目标冻结验收范围执行，不用历史 synthetic 冒充本次执行。
   中断先核真实状态，不盲删或重试。原件/私有日志留受控运行材料，不提交机器路径、用户名或凭据。
5. 导入不自动产生正式 Review/Finding/批准或改变 Gate；正式审核、原生验证与关闭仍走目标流程。

当前缺合法新目标及其匹配真实原件；既定有界搜索未找到现成匹配报告，不表示全局无报告。
本轮准备任务不创建目标，也不作为 F 的目标匹配原件。

## I5 / Phase 3：三个进入门

1. **冻结样本规则并证明充分。** 数量或可判定充分性规则、任务/角色分层、保留期、隐私、访问、偏差检查均明确，
   按规则核对真实样本。未定阈值列待决，不自行补数。
2. **批准真实 V3 用例和边界。** 指定实际高风险任务、资产、故障、受控沙箱、dry-run、损失边界、备份、
   可执行回滚目标、逐动作批准点、退出验收标准及拟采集证据。真实 V3/回滚执行证据在准入实施后形成，
   用作 Phase 3 退出验收；既有 V2/定向变异/Hook/元数据不能代替 V3。
3. **冻结版本化度量合同。** 费用/调用来源、返工归因、review 缺陷严重度、工具失败分类、任务/角色/模型身份事实、
   缺失值、脱敏/访问/保留规则统一。可现在提合同草案，真实采集另行准入；不能先执行未准入 Phase 3 来补进入门。

以[阶段三输入](../implementation/phase-03-entry-inputs.md)与原生 Policy 判定为准。提案不等于阈值已冻结、
模型身份已认证或能力/效率/可靠度改善；进入实施和高风险执行仍需对应准入与实际授权。

## 分工与保留边界

- 本轮主 agent 独占两份新记录和三个权威入口；2 名原生 sub-agent 分别只读核启动门和 ZCode 项目/任务元数据。
  编辑、复核、提交与各次 UI 发送串行。四项 ZCode 准备任务可并行，只在自己项目的会话输出，无共享文件写入；它们是外部 worker。
- F 准入 → 报告 → preflight → record → 原生收尾串行，一目标一写入者。E5/I5 准备与试点核对不依赖 F 完成；
  后续实施再按独立模块、容量和文件归属确定并发。
- 0053 push-only，0058–0060 准确 CI 失败，0061 FAILED，0028 Option C 和七项历史 BLOCKED 处置保持，历史全文保留。
  本页不授权删除、部署、扩仓、改账户/模型/权限或自动重试。
- E4 post-Q 闭账及本地整合记录仍只在本地，不因任务安排宣称已发布到远端。
