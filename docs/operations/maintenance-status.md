# 维护收尾与待办

## 2026-10-01 复制对照完成，准备有界并发设计

10组/20次isolated复制实际exit0，101文件逐份bytes/mode/mtime及实体隔离通过。
原median47.12235ms、私有4线程34.77265ms，10组均快；known资源已交回。
真实taskkill helper exit128保留，不称清理成功；输入前后相等，历史未知仍unknown。
便携记录为`.ai/tasks/TASK-0056/parallel-copy-cost-diagnostic-016.md`。
2名sub-agent并行提出实现建议和独立预审，root准备新的spec_changed准入。
拟只优化当前owner的warm snapshot复制：按原DFS批次drain后递归及copystat，
保留DirEntry、失败聚合、实际partial及无retry；原型尚非获准实现。
候选实际完整warm成本与原600仍待验证，原门禁及55、发布、F条件保持。

## 2026-10-01 读取对照无一致改善，转测复制成本

20原函数/20私有binary调用实际exit0，输入相等、known资源已交回。
原median1.18330ms、私有median1.19145ms，配对10快/10慢，无一致改善。
不选择binary生产改动；记录为`.ai/tasks/TASK-0056/binary-reader-cost-diagnostic-015.md`。
下一步2名sub-agent分别准备、独立审查四线程物理复制私有成功域对照，执行串行。
仅稳定普通可写目录、至多256文件；比较isolated copy，计入启动、drain及目录元数据。
复制原型改变错误/部分结果顺序，readonly目录风险未解决，尚未选为生产实现。
原600仍FAILED，原14项/5 mutation/85%/90%及55、发布进入条件保持。

## 2026-10-01 Schema 读取成本已短测

20原函数/20独立分解调用实际exit0、输入前后相等、known资源已交回。
原whole median1.25015ms；分解每18项的readUTF8 median0.72270ms，JSON0.24435ms。
分解开销未知，不合计medians或外推原600；便携记录为
`.ai/tasks/TASK-0056/schema-phase-cost-diagnostic-014.md`。
下一步2名sub-agent准备及独立审查仅成功域的binary UTF8读取私有对照，执行串行。
保持全部18当前读取及JSON/Resource顺序；原型缺正式兼容守卫，未选择生产实现。
并发复制原型也未运行，readonly目录提前copystat风险阻止直接替换；原门禁保持。

## 2026-10-01 定向成本诊断已完成

两个完整原生命周期用例实际2 passed/12.30s、exit0，输入前后相等，known资源已交回。
样本内Registry1105次完整调用累计2.3318896s；YAML解码约0.084s，225 hit/27 miss，
无超限文本。观察包装开销未知，数据不外推867或原600；旧失败仍保留。
源分支便携记录为`.ai/tasks/TASK-0056/lifecycle-cost-diagnostic-013.md`。
下一步2名sub-agent并行准备和独立核对Schema原语分解微测，实际执行串行；
保持18项当前读取、JSON/Resource构造和原错误顺序，不共享mutable Registry。
尚未选择生产优化，原14项/5 mutation/85%/90%及后继55、发布进入条件保持。

## 2026-10-01 完整耗时诊断与定向成本测量

固定现有 source98b5db7 / B589 的私有完整诊断实际完成：collect867，
866 passed、1 既有 FIFO skip、639.96s，pytest/driver/launcher 实际 exit0。
输入与原断言前后相等，known-owned 资源已交回；未知历史后代仍未知。
耗时仍超过原600，不能替代原生V2；便携证据见源分支
`.ai/tasks/TASK-0056/integration-durations-diagnostic-012.md`，记录 `b024366`。
最长10.65s的真实管道超时测试及原10s要求保留，其他慢阶段分散于治理生命周期。
下一步只准备两个原生命周期用例的有包装成本诊断，私有100s；
2名sub-agent分工准备与独立审查，主agent记录和整合，实际重活串行。
观察包装的身份和开销变化须明示，不从两个用例推算完整867或600收益。
未选择singlewarm、Schema缓存或CParser；后续实现仍须明确重新准入。
action005/完整V2/独立Review/Gate及后继55/发布条件仍未完成，85%/90%保持。

## 2026-10-01 当前成本短测与诊断方向

两个串行私有短测均实际exit0、输入前后相等且known-owned资源已交回。
Schema原函数100次median1.6873ms；fixture20次真实warm全部命中，median88.7757ms，
单次source扫描median4.9492ms。类别重叠，不据此推算完整600或声明候选收益。
fixture晚期taskkill实际128不算cleanup成功；三个已知实体的实际终态支持释放。
证据见源分支`.ai/tasks/TASK-0056/current-cost-diagnostics-011.md`、记录`98f219b`。
暂不选择改变瞬态观测时机的singlewarm方案，也不实施Schema缓存。
下一步独立核对builtin pytest per-test耗时报告诊断的边界，定位实际长用例；
新增报告选项和私有诊断预算明确不替代原native600，旧失败、action005/V2/Gate缺项保留。
2名sub-agent分别负责私有运行准备与独立边界审查，主agent记录，重活串行。
后续修复仍须明确准入；原测试断言、14项检查/5项mutation及85%/90%保持。

## 2026-10-01 现有 3.14 原期限诊断失败

固定 source `98b5db7` / frozen `b5898529` 的现有 3.14.7/core 私有比较完成：
原 external188 为 187 passed/1 原 FIFO skip/145.87s、实际 exit0；原 integration
完整 collect867，但原 EXEC-012/600 秒在 600162ms 超时，没有完整 summary。
源码/原 AST/旧证据/refs/index/topology 前后相等，known-owned 终态核验已交回；
taskkill 实际255及未观察后代的限制如实保留。便携原件为源分支
`.ai/tasks/TASK-0056/runtime314-diagnostic-010.md`，记录提交 `3d2cbd1`。
不正式选择 3.14，不重复同候选600；action005/第五原生V2和Gate仍未完成。
下一步先短测真实夹具的当前读取、snapshot、copy与warm成本；任何一次完整
warm扫描候选必须明确重新准入、保留所有当前安全检查和旧用例，不声称与旧
瞬态故障观测时机严格等价。2名sub-agent并行独立边界审查与短测准备，执行串行。
Schema Registry共享尚无安全隔离证明，不实施；原期限/85%/90%及下游条件保持。

## 2026-10-01 直接入口前置结果与原期限失败

固定 source `98b5db7` / own HEAD `d0199e4` / frozen spec `b5898529…` 的独立
前置实际完成：新增窄测试12/12、完整fixture65/65（零跳过）、原external-review
187 passed/1 原POSIX FIFO跳过，分别1.82s/47.38s/142.17s，全部实际exit0。
原完整integration实际collect867，在原EXEC-012/600秒期限600183ms超时；
没有summary或原pytest退出码，不把91%部分进度记为完整通过。原件和known-owned
终态证明已保留，source/原AST/旧证据/refs/index/topology前后相等，资源已交回。
TASK-0056仍IMPLEMENTING；action005与第五完整V2未启动，313正式选择条件仍失败。
便携结果为源分支 `.ai/tasks/TASK-0056/direct-endpoint-prerequisites-009.md`，
记录提交 `3b54586`。不重跑相同失败候选、不调整预算或质量门禁。
接下来仅对已安装锁定314.7与当前已修复源做原external188私有诊断对照；当前
规格允许非formal诊断，正式314需新规格准入、设计Review及原完整前置，不能凭
旧未修复失败时长推断收益。两名sub-agent并行负责独立诊断与只读runtime/发布
准备，测试资源串行。TASK55/57、CI311和真实F匹配原件的进入条件均保持。

## 2026-10-01 直接入口规格准入已完成

TASK-0056 当前为 IMPLEMENTING。冻结规格 `b5898529…` 已完成真实独立设计
审查 REV-0007/r1（APPROVE，无 Findings）、按所有者既有充分授权的 spec
批准和原生 begin；准入账本提交为 `eceb23d`。保留全部旧规格、失败与消费回执。
本阶段并行启用 2 名 sub-agent：一名仅实施三处 fixture 工具函数及追加测试，
另一名准备未参与实现的独立验收；主 agent 统一提交。固定候选后，窄用例、完整
fixture、原 external-review 和完整 integration600 串行执行；实际全部前置通过
后才进入新的完整 V2。原选择器、期限、覆盖率、CI 和发布进入条件保持。
按所有者要求的限定报告搜索已结束，未找到目标匹配的 harness-model 原件；
实际找到的 dotfiles 历史报告不能替代正向 F。未启动 provider 或 F 导入。

## 2026-10-01 直接入口候选与剖析计时边界

原source `e3790a4` 的40次只读Git入口配对查询及2次status守卫全部exit0；
输出bytes一致，源码/refs/index未变，配对差值中位13.4795ms、19/20正值。
这只是单argv的候选收益，不证明完整语义等价或integration600通过。
四完整模块实际194 passed/367.30s/exit0，逐ID三阶段完整；原始cProfile
出现9 entry/49 edge的inline>total，全部函数成本归属unknown，不用于生产修复。
已知自有进程退出，资源交回；原600失败及全部历史原件保持。

Task56已重新分类REVIEW/V2并冻结精确直接mingw64夹具/runtime候选，最新spec
`b5898529`；当前subject `87f4c04`，仅增加安全说明，夹具实现尚未开始。
MINENV算法不改，但实际所选Git parent/PATH改变必须新绑定；原53用例、完整
原选择器与600秒、14 checks/5 mutations和85%/90%门槛保持。独立设计审查
与安全测试准备由2名sub-agent并行，root串行准入/固定源码/验证/统一提交。
依据为源分支 `endpoint-and-profile-diagnostics-008.md` 和 `design-amendment-006.md`。
Task55/57仍待实际Gate，真实F原件在已搜索范围未找到，不扩大provider阶段。

## 2026-10-01 当前候选的完整被动耗时诊断

固定 source `e3790a4` 的原完整 integration 私有诊断已 actual exit 0：
854 passed / 1 原 FIFO skip / 818.91 秒，无外层超时。855 个收集 ID 逐阶段
完整相符，新 53 项均全阶段通过；源码、旧证据、HEAD/status/common refs 未变，
已知自有进程全部结束并交回。36 模块阶段和 818.164 秒，其中 external-review
217.340、verify 136.797、新 fixture 55.662 秒；这些不是内部成本或根因证明。
原 integration600 失败保持，较长诊断不替代门禁；未启动 action005/完整 V2。
依据为 `integration-passive-diagnostic-007.md`。下一步测量具体剩余成本再决定
最小修订；不因不同来源构建标记、Git wrapper 静态分析而宣称运行时更快。

## 2026-10-01 文件身份修复与运行时前置检查

TASK-0056 已按最新冻结规格 `2cefeedd` 重新准入，REV-0006/r1、spec approval
与 begin 完成。治理实现仅改 Windows 文件身份第五分量：可用 birthtime_ns，
仅属性缺失回退 ctime_ns；POSIX 和其余读取守卫保持。测试与普通说明为独立
task-free 安全提交，当前 source `e3790a4`、自有账本 head `3e691bd`。
19 项安全测试在锁定 3.11.9、3.13.15、3.14.7 均实际通过，无 skip；3.13 的
原完整 external-review 模块为 187 passed / 1 既有 FIFO skip / 177.93 秒。

随后原 integration600 实际失败：`run-20260930T160128817732Z`，600188ms、
RUNNER_TIMEOUT、pytest exit unknown，driver/launcher exit 1。partial 无
terminal summary，不能推定末尾 53 项或 skip 身份。源码、HEAD、common refs
与八份旧证据摘要未变，自有进程已结束并交回；数值 PID 复用未被当作自有进程。
尚未满足正式选择 3.13 的条件，action005 与第五轮完整 V2 均未启动。
便携依据为源分支 `runtime-prerequisite-failure-006.md`，所有历史失败保留。

下一步串行准备只记录阶段耗时的完整选择器诊断，再按实际瓶颈决定修订；原
600 秒门禁保持。并行 2 名 sub-agent：独立 verifier 负责诊断，另一名准备
Task55 transport 安全测试和只读性能分析；主 agent 保留证据、同步状态。
Task56 完整 V2/Review/finalize/批准/Gate → Task55 准入及自身 Gate → Task57
required CI/已授权发布仍串行。真实 F 原件未在搜索范围找到，不扩大 provider 阶段。

## 2026-09-30 固定夹具候选的原集成期限检查

初始夹具已实现并固定源码 `097f9af92a4c9bbad35378f34b3d5d48dd143b01`；
原测试 AST、原 builder 主体、期限与断言均保持。完整守卫短测的二十次 warm
均值为 0.113194 秒，原 builder 为 0.373655 秒，但该收益没有证明全集通过。
独立原 integration 检查 `run-20260930T144431946840Z` 实际超时：600156ms、
RUNNER_TIMEOUT、pytest exit unknown，driver exit 1。源码/HEAD/旧证据前后
相同，自有进程已退出并交回。partial 有 783 dot 和 1 skip，无 summary，
不能确认 skip 身份或最终 53 项全部完成。此为 prerequisite，不是第五轮 V2。

未创建或消耗 action005、未启动完整 V2、未进行正式实现 Review/finalize/代码
批准或 Gate PASS。TASK-0056 仍 IMPLEMENTING，旧四轮 FAILED 保留。当前
并行 2 名 sub-agent：一个核查整套真实 owner 使用和剩余成本，另一个只准备
隔离 Python 3.13 比较；后者不是原生运行时切换或验证通过。正式基线仍 3.11，
范围或运行时变化仍须重新准入。TASK-0055/0057 与 F 的进入条件保持。
便携依据为源分支 `fixture-integration-prerequisite-failure-005.md`。

## 2026-09-30 初始测试仓库夹具修订准入

完整 integration profile 的函数分析已完成。Schema 文件实际读取与检查保持
必要；Git 等累积时间重叠、双导入 helper 的 profile 标签存在合并边界，不能
据此相加或认定超时根因。另一个独立原环境短测实际 exit 0、无超时：二十次
原初始仓库创建平均 0.36051 秒，完整物理复制加当前三目录指纹平均 0.05784 秒；
二副本的工作区、index、commit 修改互不污染且不影响 seed。这个局部测量尚未
包含完整资格守卫，不证明原 600 秒检查或完整 V2 通过。

TASK-0056 已按 `spec_changed` 原生重新分类并冻结为 REVIEW/V2，当前规格
SHA `3a782321645c40b71cf4921a7322872bf45285bf009218edb3e1d4d9310c53ce`。
实际独立 REV-0005/r1 为 APPROVE、无 finding；所有者既有授权下的当前 spec
approval 和 begin 已完成，状态 IMPLEMENTING。准入账本提交
`c99998571a117a5b071c03cc9caa0e47efe8395d`；旧 e3fc 规格保存为
`spec-design-004.md`，四轮 FAILED、原证据与已消耗动作全部保留。

本阶段仅新增三个测试 utility/验收路径并薄接入共享 builder：第一份仍由原
真实 builder 在原目标成功建成后才保存 session 私有初始副本；每次检查当前
源、配置、模板和相关环境，未知或不安全资格走原流程，物理 Git 实体独立。
原异常/partial、全部原断言与之后真实治理保持。并行 2 名 sub-agent 分别
独占测试夹具实施和独立审查/验证准备，主 agent 管理文档、账本与统一提交。
实施→固定候选→完整原 integration 600 秒检查→fresh action005 和全部原生
V2→正式 Review/finalize/批准/Gate 串行；当前未记录实现或验证通过。
TASK-0055 仍待真实依赖 Gate，TASK-0057 发布仍待两源 Gate 与 required CI；
搜索范围内尚无匹配 F 的真实原件，不调用 provider 或用错目标报告补齐。

## 2026-09-30 第四轮终态与完整集成诊断

私有完整 integration profile 已实际完成：802 项中 801 passed / 1 原 FIFO skip，
851.34 秒、pytest exit 0、外层无超时；固定 fcecddd 与源码 SHA 前后相同，
自有进程已退出并交回。首次私有 wrapper 因启动 sys.path 差异出现 collection
失败，原件保留；仅恢复原模块启动的 CWD 路径语义后完成上述第二次采集。
带 profiler 的诊断时间不视为原 600 秒检查通过；函数成本分析仍待完成。

TASK-0056 完整 `run-20260930T112131331525Z` 于 12:04:40Z 实际结束为
FAILED，14 项 required checks 中 13 passed；唯一失败是 integration 原
600 秒期限超时，actual exit null / timed_out true / 600140ms。Native Gate
实际 exit 1、REJECT。失败账本提交 `fcecddda33b8ebb7e24ef7d782f14d9c2aa2de48`；
源码 subject 仍为 `38648440f5a862edd5a7dccfb55a60aae4f6757e`。

完整 regression 为 2707 passed / 1 既有 FIFO skip、857.61 秒；coverage
同样完整通过，总覆盖率 88.9574%、diff coverage 97%；unit 1869 passed、
acceptance 9 passed。五项 mutation baseline 0 / mutant 1 / killed，无超时，
`main_tree_unchanged` true；这些通过不能替代 integration 或正式 finalize。
原证据/归档 SHA `4d2c8f05e9fc4b73ea61a8836b11b8069cdd34a4b7acf573faf513a08d2848bc`。
24 份非 null 引用、snapshot/context、旧证据和回执均经独立核验；自有进程
已退出并交回资源。action004 已消耗，不复用；未进行本轮实现 Review/finalize/code approval。

partial integration 仅有 745 个结果标记，无 F/E 或最终 summary，末尾位置
不证明单例或模块根因。下一阶段由 1 名 sub-agent 测量固定源码的完整原
integration selector，另一名只读研究独立初始 fixture 基线；主 agent 维护状态。
较长私有采集窗口仅为诊断，原 Policy 600 秒、所有阈值、选择器和 MINENV
不变。诊断→修复准入/实现→fresh action 与完整 V2→实际 Gate 串行。
TASK-0055 准入、TASK-0057 发布和条件 F 均未越过各自进入条件。

## 2026-09-30 11:21Z 第四轮完整 V2 启动时记录

TASK-0056 纯 YAML 解码复用已完成独立设计 Review、原生 spec approval/begin，
生产和安全测试分别提交。固定源码 subject 为
`38648440f5a862edd5a7dccfb55a60aae4f6757e`；准入 HEAD
`36efe4cc7cc85ccd368c2df065cd4e99f0963b9f` 仅追加本 task 账本。
70 项相关 unit 测试通过，Ruff、format、44 源码 mypy、validate 和 whitespace 通过。

完整原 external-review 模块对照为 187 passed / 1 既有 FIFO skip，187.05 秒、
退出 0。此前相同方法为 200.15 秒；独立的单次非同时观察少 13.10 秒，不能认定
整体因果或预测 V2。safe YAML 解析次数从 3586 降到 87，698 次 Policy 加载及
9872 次契约/registry 检查保持；Git 等成本存在变化与累积重叠。

fresh action004 已实际批准；最终独立 preflight 返回 ready，完整默认 14 项
原生 V2 于 `2026-09-30T11:21:30Z` 启动，run
`run-20260930T112131331525Z`。原 3.11、MINENV、预算、阈值和五项 mutation 不变。
启动时仍在运行，无完整结论、正式实现 Review/finalize 或 Gate PASS；前三轮失败
及已消费动作保留。依据为源分支 `verification-retry-003.md`。
源码/账本冻结，独立 worker 负责完整验证；另一 sub-agent 只读准备 TASK-0055
后续准入。F 匹配原件在限定搜索中未找到，后续发布仍依实际源 Gate 和 required CI。

## 2026-09-30 诊断完成与解析复用重新准入

第三轮完整 V2 的 FAILED 和两项原预算超时保留。独立 Python 3.11 完整
external-review 诊断实际 187 passed / 1 既有 FIFO skip，200.15 秒；分析测得
3586 次 safe YAML 解析累积 36.92 秒。时间存在重叠，不认定原超时根因。
隔离 Python 3.14 完整比较失败（46 failed / 101 passed / 1 skipped / 40 errors），
不用于正式 V2，不以失败执行时间宣称加速。正式验证继续使用原 3.11 基线。

TASK-0056 已对纯文本解析复用扩大必要依赖范围，原生重新分类、冻结为
REVIEW/V2，正在独立设计审查；旧冻结规格和失败证据保留。方案仅复用有界
纯 YAML 解码，每次仍实际读取文件、执行路径/Schema/Policy 验证并隔离返回值。
生产优化尚未实现，新完整重试尚未启动；全部门禁、预算与环境保持现值。

按所有者指示搜索现有 ZCode 报告：仓库、相邻 pilot artifacts、只读任务索引和
常用文档目录中未找到匹配当前 harness-model 目标的原件。找到的真实历史
dotfiles 报告 SHA `80e9ebd7de1891a214075741a88abd134518195ceee6edcfd927855ac6e77ecd`
属于另一仓库，不充作 F 正向输入；历史 UI 观察记录不能恢复缺失原件。
这只是已搜索范围的结论，不证明全局不存在。未调用 provider 或启动 F 导入。

并行 2 名 sub-agent 分别核查解析收益/隔离边界与原生准入/独立设计；主 agent
实施并统一提交。完整 V2、Review/Gate、TASK-0055 重新准入及 TASK-0057
required CI 与已授权推送合并继续串行依赖，下方历次核定保持。

## 2026-09-30 TASK-0056 第三轮完整验证核定

第三轮完整原生 V2 在候选 `4f0288b4afb608412f984fa9078b7b0692fa0e6f`
结束为 FAILED：12/14 通过，regression 与 integration 分别超过原 900 秒和
600 秒期限。完整 coverage 集合实际 2676 passed / 1 原有 POSIX FIFO skip，
合并覆盖率 88.8278%，diff coverage 打印 95%；unit 1838 passed，acceptance
9 passed。两项超时仍无完整 summary，不能据部分输出声称通过，Gate REJECT。
action003 已消费，所有失败、日志与 receipt 保留；尚无正式实现 Review/finalize。

当前先核定并提交失败记录，再用 2 名 sub-agent 分别定位耗时热点和独立审计
诊断边界；主 agent 同步维护便携证据。诊断保持完整断言和原 Policy，不能替代
原生验证。重试须有诊断依据、新 preflight 与单次动作。后续仍依 TASK-0056
Gate → TASK-0055 重新准入及 Gate → TASK-0057 required CI、已授权推送合并。
真实报告 F 的匹配原件仍未取得。见源分支 `verification-failure-003.md`；下方
历次核定保留，新结果不追改历史证据。

## 2026-09-30 TASK-0056 第二轮失败后的修复候选

第二轮完整原生 V2 保留 FAILED：14 项中 10 项通过、4 项失败；unit 为
1838 passed，regression、coverage 与 integration 实际超时，diff coverage
因缺少 XML 退出 1。总覆盖率和差异覆盖率仍 unknown，Gate REJECT。
action002 已消费；原始日志、receipt、snapshot 和失败摘要均保留。

独立诊断定位到 Windows 测试夹具的长路径物理 I/O，以及 Git 命令超时后
没有期限的管道清理等待；最初 Git 超时原因仍 unknown。修正规格已经原生
重新准入，设计 Review、spec approval 和 begin 完成。新源码候选为
`4f0288b4afb608412f984fa9078b7b0692fa0e6f`，仅修复获准的两份测试夹具。
原逻辑路径、业务断言、命令期限、生产环境和 Policy 门禁保持现值。

四组独立完整专项通过：共享 Git 夹具 34 passed、验证命令 81 passed、
外部审查 187 passed / 1 原有 POSIX FIFO skip、E2E 28 passed。
真实 Windows 子进程继承管道的超时清理用例亦通过。这些结果支持第三轮
完整原生 V2 准入，不构成完整 V2 或 Gate PASS。当前由两名 sub-agent
分别执行独立 verifier 准入与实现审查；正式 Review 等待完整验证证据。
先完成 TASK-0056 Gate，再重新准入 TASK-0055，最后以 TASK-0057 完成
固定候选 required CI 与已获授权的推送合并。真实报告 F 的匹配输入仍待取得。
便携摘要见源分支的 `verification-failure-002.md` 和 `verification-retry-002.md`；
下方历史核定、用户草稿及无关工作树保持原样。

## 2026-09-30 TASK-0056 候选固定

TASK-0056 独立设计复审通过后，原生 spec approval 和 begin 已完成。
显式外部 pytest 临时目录实现与安全测试分阶段提交，固定候选为
`659f61cb4245112d75b119b103821bb06bae69ce`，原生 sync 已绑定该 subject。
守卫覆盖输入及物理祖先、裸仓库、身份漂移和独占新叶；pytest 摘要追加实际 argv
的规范 SHA-256，保持脱敏。独立预审未发现剩余阻塞项。
78 项守卫专项、3 项真实 runner/默认兼容用例通过，Ruff、format、43 个源码的
mypy、原生 validate 和 whitespace 检查通过；局部结果不替代完整 V2。
已交未参与实现的 sub-agent 完成全部原生 V2；当前没有完整通过、正式实现 Review、
code approval 或 Gate PASS。先取得真实 Gate，再按下方顺序接入 TASK-0055。

## 2026-09-30 持续 goal 与临时目录治理准入

所有者已设立持续 goal，授权完成当前进入条件满足的待办及必要批准、推送合并，
并要求充分使用 sub-agent。TASK-0055 第五轮失败与原始证据仍保留。
新 TASK-0056 在 `codex/e4-verification-control` 独立准入显式仓库外
`--pytest-temp-root`；原生分类为 REVIEW/V2，规格已冻结，设计复审进行中。
初次独立设计审查要求补充裸仓库拒绝及执行期漂移的原生失败记录，两项已纳入
重新冻结规格，原快照与 Review 保留。尚无实现或验证通过结论。
默认行为、Policy、阈值、时限、环境及选择器保持现值；临时目录迁移不能证明
既有超时原因或性能改善。先完成 TASK-0056 独立验证和 Gate，再显式修订
TASK-0055 的依赖范围、重新准入并完成完整 V2。发布 task 顺延为 TASK-0057；
只有实际源 Gate、发布 Gate 和固定候选 required CI 均通过才执行合并。

## 2026-09-30 E4.2 第五轮原生 V2 核定（FAILED）

E4.2 已在 `codex/e4-report-import` 完成当前实现，`TASK-0055` 固定源码 subject 为
`eb4c49a4ff77ca07f210fceae707495c8dece8be`，本次验证准入 HEAD 为
`12b8e76e195e6f13772d3d692b80fca06422d31f`。第五轮完整原生 V2 已结束，
结论为 **FAILED**：14 项必需检查中 9 项通过，尚不能形成发布 Gate PASS。

unit、regression、coverage XML、integration 分别在 300406、900203、1200328、
600172 毫秒实际超时，均无进程退出码（`exit_code: null`）。diff coverage 因缺少
coverage XML 退出 1；总覆盖率与差异覆盖率均为 `unknown`，不能据此宣称达到阈值。
9 项 acceptance 用例通过，5 项 targeted mutations 全部 killed；这些通过项保留原义，
不替代失败的完整 V2。

unit 部分日志出现的两项失败，在限定诊断中 2 passed、12.64 秒、退出 0。
这未复现原失败，原因仍为 `unknown`；限定诊断不覆盖完整运行，也不改变 V2 结论。
当前接续为定位失败并完成完整必需验证，不降低预算、阈值或检查范围。

源码与任务账本保留于既有忽略目录 `.claude/worktrees/e4-verification-disk`。
本原始文档检出不含 `TASK-0055` 账本；失败摘要提交后，可在仓库中便携读取：

```text
git show codex/e4-report-import:.ai/tasks/TASK-0055/verification-failure-005.md
```

所有者已明确授权推送、合并，授权仍有效，动作尚未执行。当前失败阻止发布；先完成
完整 V2、匹配的独立实现审查与实际 Gate，不重复请求动作授权或提前请求代码批准。
下方较早核定窗口与历史记录完整保留；E4.3/E4.4、provider、I1 其余生命周期、
I2 更多目标、E5、I5 与阶段三/四保持原进入条件。三份用户草稿和阶段 61 旧 index 保留。

本轮随后完成第五次运行的私有证据移交：显式选择 100 文件，导出与独立 ZIP
校验均退出 0，全部条目的大小及 SHA-256 匹配；23 组 producer/Git 文本映射一致，
其中 10 组仅 CRLF/LF 不同，原件分别保留。移交不恢复环境，也不产生 Gate。
便携记录为 `git show codex/e4-report-import:.ai/tasks/TASK-0055/evidence-handoff-005.md`。
TASK-0055 仍 FAILED；当前资源观察没有支持新一轮重试，失败原因尚未确认。

## 2026-09-30 最新核定与接续入口

本轮实际读取 CLI，`TASK-0048` 为 `MERGED`、`Missing: none`。其同仓 Windows/Linux
接入、同 SHA 双 lane、main 采用、真实 guest 重启后业务、串行恢复与正式治理关闭
均已完成；见[任务 02 执行目录](../superpowers/plans/2026-09-13-runner-infrastructure-execution.md)
和[发布关闭记录](../../.ai/tasks/TASK-0048/publication-closeout-001.md)。不重复注册、
运行 CI 或关闭该任务；历史运行状态不作为当前 guest 或 runner 在线证明。

E4.1 已由 `TASK-0054` 完成契约实现与本地治理验收，保存于
`codex/e4-external-review-contract@fd560d9`，实现 subject 为 `23793f7`。
本轮恢复该分支检出后实际 `validate` 通过，`status` 为 `APPROVED_FOR_MERGE`、
`Missing: external_merge`，批准为 `current`、证据为 `passed`，`gate` 为 PASS。
旧入口中的“E4 未启动”和“E4.1 待准入”保留其历史时点，不再描述当前接续顺序。

该分支已提交的 V1 审核包记录单元 1656 passed、全量回归与覆盖率重跑各 2294 passed、
总覆盖率 88.12%、可统计差异覆盖率 100%；这些是历史受审版本的结果，本轮没有重跑。
旧忽略目录中的原始日志是否可恢复尚未确认；本次 CLI 通过不替代日志恢复或远端 CI。

下一步为 E4.2 独立治理规格与设计准入，本轮在 `codex/e4-report-import` 准备
`TASK-0055`；按[后续工作计划](../superpowers/plans/2026-09-23-e4-follow-up-work-plan.md)
串行核定原件加载、来源/目标匹配与记录边界，再依实际 CLI 缺项进入实现。
推送、合并与新增外部动作仍需单独授权。I1 其余生命周期、I2 更多目标、E5、I5 与
阶段三/四保留原进入条件；三份未跟踪用户草稿及阶段 61 的旧 index 保持原样。
下方历史窗口完整保留，以本段和当前任务账本确定实际进度。

## 2026-09-27 dotfiles 修复线集成核定

`codex/ci-regressions-e4-preflight@3b835f1` 已通过[合并提交 `68ef2ec`](https://github.com/MaginaLW/ai-agent-dotfiles/commit/68ef2ecedca3e9071178dcab8b805cecdafbba53)
进入 dotfiles `main`。[`main@6c814f1` 的完整 Validate](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/36303730680)
四个 job 均成功；[外仓整合记录](https://github.com/MaginaLW/ai-agent-dotfiles/blob/6c814f18e981edfa1cad7185915ed7c177857bc0/status/active/live-safety-hardening.md#L4121-L4149)
保留了分支来源。下方 2026-09-23 的“分叉、待集成”与独立工作线是历史快照，不再重复集成。

## 2026-09-23 后续计划与统一接手入口

收尾已完成，[后续工作计划](../superpowers/plans/2026-09-23-e4-follow-up-work-plan.md)
明确 E4.1 准入、契约实现、验收及后继 E4.2 的依赖和 sub-agent 文件分工。
dotfiles 修复分支与新 main 已分叉，尚无该分支 PR；集成及主仓记录发布作为独立工作线，
不把旧候选 CI 外推为组合树验收。本次只更新计划和入口，E4 仍未启动。
下方窗口保留原时点，实际接手顺序以上述计划为准。

## 2026-09-23 CI 修复收尾，E4 启动前材料就绪

dotfiles 修复已推送到 `codex/ci-regressions-e4-preflight`，固定 `3b835f1` 的
[CI run 35873759132](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/35873759132)
四个 job 全部 success，42 套件全部通过，无失败或套件超时。
详细修补、失败历史及证据摘要见[收尾记录](e4-preflight-closeout-2026-09-23.md)。
已完成[启动前规格](../superpowers/specs/2026-09-23-zcode-report-import-preflight.md)；
下一阶段才固定基线、建立 E4.1 治理 task、分类/冻结/设计审查并按 CLI 准入 begin。
本轮 E4 未启动；主仓准备与关闭文档仅本地提交。下方各窗口作为历史保留。

## 2026-09-23 消费动作已选定，E4 停在启动前

所有者选择“将 ZCode 审查报告校验并导入既有 AI Flow 任务”。
[启动前规格](../superpowers/specs/2026-09-23-zcode-report-import-preflight.md)已将首批范围
收敛为 E4.1 独立外部报告契约及兼容检查；实际预检/写入留给后继 E4.2。
来源受审对象与目标任务分开绑定，原件摘要不认证身份，也不形成正式 Review 或 Gate。
本轮继续收尾 dotfiles 两项 CI 修复；E4 task 分类、冻结、设计审查和 begin 均未启动。
下方“尚无选定范围”是选择之前的核查快照，按本窗口及规格的实际验收状态推进。

## 2026-09-23 E4 进入前核查

E3 最小真实双产品案例及两仓推送已完成，发布范围见
[TASK-0053 回执](../../.ai/tasks/TASK-0053/publication-closeout-001.md)。本轮只读原件、
离线表示边界复现和 19 项现有 review 回归通过；未找到该案例被内核接口阻断的证据，
因此尚不选定 E4.1 的代码范围。详见[核查与后续入口](e4-gap-assessment-2026-09-23.md)。

dotfiles 固定 `51044a55` 的自然 CI run `35733693990` 已结束为 failure：42 套件中
40 passed、2 failed、0 suite timeout。两项实际失败分别是 root-claims-registry 内部
子进程 15 秒期限和 sync 的 released-policy dry-run 断言，底层原因仍待复现；它们不
构成 E4 缺口。新窗口不改写下方历史，也不把已完成 E3 再列为待造样本。

## 2026-09-22 PR #43 后续工具交付

[PR #43](https://github.com/MaginaLW/harness-model/pull/43) 已于 2026-09-22T11:08:56Z 普通合入 main
（`48bf777`）。本轮完成 runner 本机路径与 PSDrive 绑定检查，
以及显式证据选材预检；缺失日志、缺失原件和实质字节冲突均保留可见诊断。

固定源码 `2393c67`：本地 **2238 passed**，含 Python 工具总覆盖 **88.86%**、
累计差异覆盖 **99%**，七组质量检查通过。TASK-0052 正式 V1、独立实施审查、
代码批准和本地 Gate 均通过；精确发布 head `45a220f` 的 required CI
为 Linux **2236 passed / 2 Windows-only skips**、核心覆盖 **88.03%**。
维护模式远端 Verify and Gate 跳过，本地正式验证单独保留，不混用覆盖范围。

核对远端父提交、树与源码祖先后已关闭 TASK-0052：MERGED、Missing: none。
账本共 **51 项：42 MERGED / 8 BLOCKED / 1 APPROVED_FOR_MERGE**。详细版本与动作依据见
[TASK-0052 关闭记录](../../.ai/tasks/TASK-0052/publication-closeout-001.md)。
本轮关闭记录仅本地追加，不递归发布；三个用户草稿及旧历史保留。

E3 自然双产品案例、外仓安全交接、I1 其他生命周期及 E4/E5/I2–I5/阶段三四继续按
既有条件推进；TASK-0028 保持选项 C，七项更早 BLOCKED 不自动恢复；新增 TASK-0051 为已被本任务接续的 CI 失败历史。
本次首次 Linux CI 的 3 个失败来自合成 Windows 测试的宿主盘查询，保留为 TASK-0051
失败记录；`7b940bf` 的 6 行 fixture 修复保持所有原断言，Task52 重新完成验证后发布。
以下 PR #42 及更早段落是对应历史窗口，不作为当前待重复实施的队列。

## 2026-09-22 PR #42 合并与本轮关闭

[PR #42](https://github.com/MaginaLW/harness-model/pull/42) 已于 08:06:49 UTC 合入 main
（`ae0e3d3`）。最终 head `1d76edd` 的 required CI 通过：Linux 2102 passed、
1 Windows-only skip、核心覆盖率 88.03%；本地含工具测试 2103 passed、总覆盖
88.58%、累计差异覆盖 96%。TASK-0050 正式 V1、独立审查和本地 Gate 均通过，
核对远端父提交、树及源码祖先后已关闭 MERGED、Missing: none。

账本现为 49 项：41 MERGED / 7 BLOCKED / 1 APPROVED_FOR_MERGE。工具与本轮 E1
诊断已发布；条件阶段、外仓交接和 TASK-0028 选项 C 保留。动作及关闭回执仅追加
本地，不递归再发布；详见 [TASK-0050 关闭记录](../../.ai/tasks/TASK-0050/publication-closeout-001.md)。
下文关于最终发布尚待执行的文字属于此前观察窗口，原文保留。


## 2026-09-22 最终源码与发布治理追加核定

证据导出边界补充修复后，固定源码 `5ecde71` 在干净检出重新通过 **2103 项测试**，
含新工具总覆盖率 **88.58%**、差异覆盖率 **96%**，七组质量检查全部通过。
工具实施维持 task-free；外部发布另由 [TASK-0050](../../.ai/tasks/TASK-0050/spec.md)
按 REVIEW / V1 前瞻执行。先前只保存授权回执的发布流程遗漏如实保留，不倒签。
PR #42 的旧候选 CI 不能覆盖最终源码；实际发布状态以后续真实回执为准。
详见[最终验证和流程纠正](local-tools-closeout-2026-09-22.md#最终源码补充核验与发布流程纠正)。
此前 2100 项、88.57% 是第一次源码检查的历史结果，以下原文保持。


## 2026-09-22 持续推进后的追加核定

[PR #41](https://github.com/MaginaLW/harness-model/pull/41) 已于 06:27:32 UTC 合入 main，
合并提交 `aeaed58`；TASK-0049 的关闭账本及入口记录现已发布，不再仅保存在本地。
该 PR 的精确 head `1c40b63` 通过 required CI：1958 项测试、88.03% 总覆盖率，
其余原质量检查通过。未重复关闭 TASK-0049。

证据移交与 I1 受控工具发现已实现并完成独立审查和干净检出验证：2100 项测试通过，
含新增工具的总覆盖率 88.57%、差异覆盖率 96%。具体工具、实际材料检查和范围见
[本轮实施与验证](local-tools-closeout-2026-09-22.md)。E1 当前窗口已形成
[登记试点诊断](pilot-evidence-review-2026-09-22.md)，其中外仓应用和 E3 仍有明确边界。
I1 的其他生命周期及后续条件阶段未因此全部完成；三个用户原稿保持原样。

以下“本轮关闭账本仅保存于本地”及“通用移交/发现方案待选”属于此前快照，
当前完成范围以本段及链接记录为准；历史原文保留。

## 2026-09-22 PR #40 合并后追加核定

[PR #40](https://github.com/MaginaLW/harness-model/pull/40) 已于
2026-09-22 06:11:51 UTC 通过普通 merge 合入 main，合并提交为 `4399352`。
精确受检 head 为 `9ab3ca4`；required `ai-quality-gate` 已通过，完整测试
1958 项通过，Linux 总覆盖率 88.03%、差异覆盖率 100%，原质量阈值保持不变。

旧待办 1（TASK-0048 关闭记录及后续文档发布）和 2（`begin` 与 spec approval
新鲜度一致性缺陷）均已通过 PR #40 完成。TASK-0048 不重复关闭；TASK-0049
已在核对真实合并、提交祖先及合并树后由 CLI 关闭为 `MERGED`、`Missing: none`。
本地账本现在为 **48 项：40 MERGED / 7 BLOCKED / 1 APPROVED_FOR_MERGE**。
详见 [TASK-0049 发布与关闭记录](../../.ai/tasks/TASK-0049/publication-closeout-001.md)。

本轮 TASK-0049 关闭账本与这次入口更新仅保存于本地，未纳入 PR #40 受检 head，
不声称远端 main 已包含这些后续记录，也不因追加回执派生新一轮发布。
TASK-0028 维持选项 C，七项 BLOCKED 不自动恢复；E1 按需、E3 等待自然双产品案例，
E4 / I1–I5 / 后续阶段继续保留原条件，详见[最新待办入口](follow-up-backlog-2026-09-22.md)。

以下同日及更早段落保留原观察时点；其中“关闭记录尚未发布”和 `begin` 未修复
已由本段更新，不再作为当前待办。

## 2026-09-22 当前核定

[PR #39](https://github.com/MaginaLW/harness-model/pull/39) 已通过 required CI 并合入
main。TASK-0048 已在本地关闭为 `MERGED`、`Missing: none`；本地账本现在为
**47 项：39 MERGED / 7 BLOCKED / 1 APPROVED_FOR_MERGE**。TASK-0028 仍需重验，
维持选项 C；七项 BLOCKED 不自动恢复实施。

核定时本地 head 为 `7eec053`、远端 main 为 `7dad5c0`。本地关闭记录尚未发布，
不属于 PR #39 的受检候选 `2dffdf0`；远端账本仍是关闭前状态。真实发布与关闭依据见
[TASK-0048 追加记录](../../.ai/tasks/TASK-0048/publication-closeout-001.md)。

后续统一见[待完成项目清单](follow-up-backlog-2026-09-22.md)：本地收尾记录发布、
已复现的 `begin` 批准绑定一致性缺陷、按需 E1 复核与真实 E3 双产品案例，以及满足
条件后才选择的 E4 / I1–I5 / 阶段三四。E2 设计和本次同仓双平台采用已经完成。
本次仅梳理记录，不启动新实施或发布；反馈仍执行无问题且无请求即 no-op。

以下各日期段落保留历史观察，其中 TASK-0048 实施中、尚未注册 Linux 和早期统计
不再描述当前状态；以本段及链接的最新清单为当前入口。

## 2026-09-20 当前核定

2026-09-20 所有者决定：两个登记试点的[反馈与回灌](feedback-loop.md)，以及 VPS 连续
回执整理，改为仅在有实质问题或用户明确请求时执行。无问题且无请求直接 no-op；
普通完成、版本差异、登记上一笔 CI 不派生新提交和验证，不递归制造回执。
原始证据与必要安全检查保留。下文 2026-09-09 的“每次收尾触发”决定作为历史保留，
当前触发规则以本段及闭环指南为准。

本轮从 `d40971a` 重新读取：当前分支为 `codex/self-hosted-runner-inventory`；
账本是 **47 tasks：38 MERGED / 7 BLOCKED / 1 APPROVED_FOR_MERGE / 1 IMPLEMENTING**。
TASK-0048 为 REVIEW/V2、`Missing: implementation_result`；TASK-0028 仍需重验，
维持选项 C。下文 46 项及“没有实施中 task”属于历史快照，不再描述当前状态。

本轮[ZCode 试点复盘与接续](zcode-retrospective-2026-09-20.md)已核对两个外仓当前
检出、回灌记录及证据缺口；不把旧 CI、目标自述或方法采纳当成当前验收。
任务 02 的最新已记录节点是 [WHPX 阶段 57](../implementation/task02-runtime-integration.md#whpx-实际启动与阶段-57-收尾)，
已经记录真实 Linux 启动；“尚未安装 Linux”仅为早期准备结论。完整 POSIX 仍保留
阶段 55 退出 124；新 boot 的低权限/挂载准入、原单项、完整门和接入仍须按该节点
顺序推进。本轮没有重查 guest 现场，不把历史运行状态写成当前在线。

本轮先完成只读复盘与本仓方法改进。外仓写入交接、真实双产品 E3、任务 02 实施结果
及阶段三准入均未因此完成；三份既有未跟踪计划稿保留，不纳入本轮提交。

首次盘点日期：2026-09-07。盘点基线为 `c9343c2`；当时远端 main 经只读查询为 `1f28583`，
当时开放 PR 和 issue 均为 0。本页是当前工作入口，不替代任务账本与 Gate；
历史统计和决定保留在[原处置目录](../superpowers/plans/2026-09-03-approval-overhead-and-open-task-consolidation-directory.md)。

2026-09-08 更新：TASK-0047 已通过 PR #35、#36 完成交付，现行 Policy 为 `2.3.0`。
下文保留原快照，并将已修复问题与仍未实现的能力分开，不把旧待办重复升级成人审。

2026-09-09 接入更新：已观察 `ai-agent-dotfiles` 接入后的真实代码任务，并将五项反馈
纳入本仓接入指南、观察方法和示例，见 [ZCode 外仓试点反馈](zcode-adoption-feedback.md)。
这是文档方法改进，不表示目标仓整链验收通过，也未启动阶段三。

2026-09-09 试点扩展：按项目所有者要求，将 `r3s-VPS` 加入后续 ZCode 工作范围，
复用该仓已有 `AGENTS.md` 与离线 Strict 入口；本轮仅只读盘点和登记，未执行该仓业务任务。
接手入口、已有修改与验证边界见[外仓试点清单](adoption.md#已登记的外仓试点)。

2026-09-09 闭环更新：所有者选择为已登记试点统一采用任务收尾触发的
[反馈、改进、回灌与再观察](feedback-loop.md)，当前包括 `ai-agent-dotfiles` 与 `r3s-VPS`。
本轮准备方法和首次接入提示词；目标仓仍由各自 Agent 在当前任务结束后持久化入口、执行
首次回灌并记录实际应用版本。不设置后台定时器，也不改变原有门禁或阶段三进入条件。

## 当前任务 02

2026-09-13 所有者已明确授权完成任务 02。完整范围、验收矩阵和当次事实见
[基础设施执行记录](../superpowers/plans/2026-09-13-runner-infrastructure-execution.md)，
运维与工具入口见[自托管执行基础设施](self-hosted-runners.md)。当前推进只读盘点、
独立回执契约和真实 Linux 环境；整体仍为 `IN_PROGRESS`。下文此前只读准备和迁移
结果均保留原观察时点，不代表本轮完整退出，也不覆盖新的执行记录。

## 已完成

2026-09-13 后续执行：[E1 核查、E2 设计与 Linux 候选准备](follow-up-preparation-2026-09-13.md)。
dotfiles 历史 Step 3 的两个固定提交已取回 37/37 成功 CI，原本地日志缺失仍保留；
私有试点在核查中已由另一任务推进 main，采用结果由其当前持有者核定。
本轮完成 E2 最小 guided 设计与树外 Linux 候选，按所有者确认保持目标只读。
E3 的双产品会话和逐项复核链仍不足，E4/E5 与阶段三/四未启动。以下旧快照保留观察时点。

2026-09-13 凌晨收尾：[9 月 12 日新增计划的统一后续入口](../superpowers/plans/2026-09-12-plan-closeout-and-next-steps.md)。
可信私有目标的 Windows runner 最小迁移已达 PILOT_PASS；完整 workflow 与 main 采用
尚未完成，具体运行资料保留本机受限交付记录。后续先准备同仓 Linux 接入，再核对正式
采用；跨 Agent 主线继续沿用 E1–E5，可独立开展最小设计。本轮仅做规划与文档收尾，
不启动这些后续阶段。下段账本、外仓 dirty 状态和分支数据保留为 9 月 12 日较早核查快照，
不替代接手时的实际读取，也不由新 CI 结果覆盖旧业务版本的验收。

2026-09-12 当前执行入口：[ZCode 试点收尾与跨 Agent 协作执行目录](../superpowers/plans/2026-09-12-zcode-review-fix-execution.md)。
本次重新核对账本仍为 46 tasks：38 MERGED / 7 BLOCKED / 1 APPROVED_FOR_MERGE；
TASK-0028 仍需 reverification，继续保留选项 C。核查起点 `68f3dcb` 相对 main `f633c03`
领先 13 个本地提交；远端没有开放 PR，PR #38 的成功 CI 只覆盖其历史 head。

两个外仓均已有实际接入与后续反馈：dotfiles 已记录应用 `68f3dcb`，最新自身进度为
36/52，但 Task 6 Step 3 全量收尾结果仍未入库核实；r3s 已记录两轮反馈和本地 Strict，
当前仍缺成功的双通道 CI 回执，且存在状态文档与 manifest 未提交修改。本次只读核查，
未重跑外仓检查或访问生产。后续先补齐各自交付证据，再利用现有独立审查案例验证
Review–Fix–Verify 交接；早期“待首次接入”描述仅保留为历史快照，不再是当前待办。

- 阶段一、二：13/13 chapters、77/77 tasks、408/408 steps、24/24 exit checks 均 completed。
  这是交付与验证状态，不代表真实人工耗时或缺陷率已经下降。
- 旧账本收敛：TASK-0008、0029、0032、0033 已有被取代或阻断说明；TASK-0040、0041、0043
  为已否决/阻断的设计，保留历史记录，不为清零数量而重新开启。
- 审批整改：B0–B2 停止，B3 已按“如实记录执行边界”解决，B4 暂缓。
  它们不是待自动执行的四章计划。
- TASK-0044：历史批准聚合修复、低干预操作入口和只读统计工具已随 PR #31 合入 main。
  合并前其记录分支 `codex/reduce-human-intervention` 的 Gate 为 AUTO/V1 PASS；
  1630 passed / 4 平台 skip，总覆盖率 87.81%，变更覆盖率 100%。
  外部交付及真实合并记录见下节，不需要新的本地 spec/code 批准。
- 本轮文档收尾：纠正状态说明中“bootstrap 标记不存在、每项变更必建 task”，
  修正处置目录顶层状态、B3 状态与 README 在途说明。
- TASK-0046：ASK 义务修复已通过 PR #33 合入，关闭记录已通过 PR #34 发布；
  REVIEW+ASK 先等待方向选择，再保留原 REVIEW 审核，BLOCK 优先级不变。
  当前状态 MERGED，Missing / Next 均为 none，不需要重新批准或移植旧候选。
- TASK-0047：显式风险类别与受控动作输入、旧正向风险兼容、pending/begin 新鲜度校验、
  未知动作默认拒绝及相关回归已通过 PR #35 合入；PR #36 已发布真实关闭记录。
  字段缺失是 Agent 可补齐的零写输入错误，不自动产生新的 ASK 或人审要求。

交付后固定快照 `2e00d78` 的运行账本共有 45 个 task：37 MERGED / 7 BLOCKED /
1 APPROVED_FOR_MERGE，最后一项是保留原处置决定的 TASK-0028。后续新 task 会改变数量；用
`python tools/analysis/approval_overhead.py --format text` 读取最新快照。

新增固定快照 `d501027` 的账本共有 46 个 task：38 MERGED / 7 BLOCKED /
1 APPROVED_FOR_MERGE。没有实施中的 task；7 条 BLOCKED 是已登记的替代、失败或否决
历史，不是待自动重启的队列。TASK-0028 仍按选项 C 保留，不能为清零而直接 close。
编号上限 TASK-0047 不等于 47 个运行账本，也不等于阶段计划中的 77 个实施条目。

## 外部交付更新

[PR #31](https://github.com/MaginaLW/harness-model/pull/31) 已于 2026-09-07 合入 main，
合并提交为 `00d1838f23d1b02b02f5b4bc0eb64fe11a2504ed`。其精确 PR head `9a2d5ee`
通过必需的 [ai-quality-gate](https://github.com/MaginaLW/harness-model/actions/runs/34108909215)：
Linux 全量 1634 passed，总覆盖率 87.80%，18 个可执行变更行全部覆盖；
whitespace、Ruff、format、mypy 均通过。未绕过保护，未删除源分支。

已核实合并提交包含 TASK-0044、0045 的 subject 与受检 PR head，并通过 CLI 为两个
任务追加 `merge_recorded` / MERGED。后续账本交付 [PR #32](https://github.com/MaginaLW/harness-model/pull/32)
也已通过自身的 [required CI](https://github.com/MaginaLW/harness-model/actions/runs/34109822587)
并合并为 `8ee402d`：1634 passed，总覆盖率 87.80%，没有新增可执行源码行。
关闭记录已进入 main；不提前关闭未来工作，也不改写旧证据。

[PR #33](https://github.com/MaginaLW/harness-model/pull/33) 已合并为 `9baa0cb`，
[PR #34](https://github.com/MaginaLW/harness-model/pull/34) 已合并为 `2e00d78`。
精确受检 head 分别为 `deb05ad`、`e10c8a3`，两次 required CI 均成功：
各 1657 项测试通过，总覆盖率 87.90%；实现有 19 个可执行差异行且全部覆盖，
关闭记录没有新增可执行源码行。TASK-0046 仅对真实实现合并执行一次 close。
重新只读查询时远端 main 为 `2e00d78`，开放 PR / issue 均为 0；这不是持续监控结果。

[PR #35](https://github.com/MaginaLW/harness-model/pull/35) 已正常合并为 `0fa7d05`，
[PR #36](https://github.com/MaginaLW/harness-model/pull/36) 已正常合并为 `65589da`。
两次 required CI 各通过 1,721 项测试，总覆盖率 88.04%；实现的 36 个可执行差异行
全部覆盖，账本 PR 无可执行差异。远端维护模式 CI 执行完整质量门，并非远端 task Gate；
实现合并前单独核对的本地 TASK-0047 Gate 为 PASS。历史 Windows V1 的 88.14% 不变。
精确 head、CI、合并时间及祖先核验见[交付记录](../../.ai/tasks/TASK-0047/review-notes.md#2026-09-07-实际合并与关闭)。

所有者随后另行要求分支清理：5 个本地、4 个远端的已合并且无工作区占用分支已删除，
提交历史、备份、试点、未合并分支与所有工作区保留。恢复映射见
[清理记录](../../.ai/tasks/TASK-0047/branch-cleanup.md)。`d501027` 是最初仅本地保存的
清理审计，本次维护文档交付包含该提交；发布须使用新的交付授权，不复用删除授权。

## 剩余工作与明确处置

| 项目 | 当前证据与下一步 |
|---|---|
| 本轮交付 | 上轮修复、本轮文档与维护修复已通过 PR #31 合入 main；TASK-0044、0045 的真实关闭记录已通过 PR #32 发布，不再是待实现功能。 |
| 工作区忽略规则 | TASK-0045 的仓库级 `/.claude/worktrees/` 规则已随 PR #31 合入，新克隆可继承；仅忽略根目录下的 worktree 副本，保留 `.claude/skills/` 等配置可见。验证记录见该任务的 `evidence.json` 与核查补记。 |
| ASK 义务修复 | 已由 TASK-0046 独立实现、完整验证并通过 PR #33、#34 交付；旧 `1033a46` 仅作为代码参考，没有复用旧任务批准或失败证据。 |
| 风险输入与动作默认拒绝 | TASK-0047 已通过 PR #35、#36 交付并关闭；无需重做已完成实现或重新批准旧代码。 |
| TASK-0028 历史收尾 | 代码已在 main，状态仍需重验；在 `8ee402d` 的 main 上实测 Gate 有 9 条拒绝理由，旧 10 条为另一历史快照，分支上下文会影响输出。维持已有选项 C；仅在所有者选择重验或改变历史处置方式后推进，不用 `close` 绕过已记录的决定。 |
| 效果验证 | 已固定[基线、方法与两次真实交付观察](effect-observations.md)：分别记录 TASK-0046、0047 的可见请求组与批准记录；人类工作分钟、同类修复前对照及成熟缺陷观察仍缺失，不宣称成本或缺陷率改善。继续在实际工作结束时追加已有事实，不为补统计新增人工请求或自动采集。 |
| 现有 AI 工具接入 | 两个登记试点已持久化闭环入口并产生后续窗口；dotfiles 的两段独立评审已成为第六项方法。按[执行目录](../superpowers/plans/2026-09-12-zcode-review-fix-execution.md)先核对当前全量收尾证据，再准备最小双工具交接。实际回灌版本以目标记录为准，不是后台同步，不宣称效率/可靠度改善或阶段三/四已启动。 |
| 已登记的引擎边界 | 下节区分 TASK-0047 已修复项与未实现的可信外部执行能力；后者需要新的设计输入，不是本次收尾遗漏。 |
| `r3s-VPS` ZCode 试点 | 已有 R1、grok/x.ai 与 fixture/CI 的目标记录；最新应用 upstream 记为 `3a0bb34`。当前重点是 CI 零步骤失败的证据收尾及两文件 dirty 边界；本地 Strict 和目标生产记载不能代替当前双通道 CI。第六项方法在下一安全收尾时评估适用性；本仓本次未执行其测试或生产动作。 |

ASK 旧候选所在工作区仍被 Git 注册，盘点时干净且处于 detached 状态，
HEAD 为 `6091b47`。其旧 TASK-0042 验证为 FAILED；main 的同号 task 是另一项
`.gitattributes` 工作，已 MERGED。必须保留这一区别，不能复用批准、证据或直接搬入账本。

旧 `musing-dijkstra-a7c360` 目录已不存在，无需删除。保留分支与试点分支用于不可变提交
引用和未合入工作，不作批量清理。`codex/maintenance-closeout` 仍被独立工作区占用，
本地和远端分支均保留；不是可在普通分支清理中顺带删除的目录。

## 风险控制项的当前处置

以下沿用首次盘点的五项编号，更新处置而不删除历史问题的来由：

| 原问题 | 2026-09-08 处置 |
|---|---|
| 1. 缺少 `impact_categories` 时可能漏识别风险 | TASK-0047 已修复：新分类要求显式风险字段，缺项零写拒绝；历史读取与严格同身份 no-op 保留，不重写旧任务。 |
| 2. 部署/生产删除仅靠 `planned_actions` 自由文本匹配 | 已增加有类型的 `controlled_actions`，并保留旧精确 token 的正向风险。分类事实仍不能证明任意真实 shell 动作，后半项是执行边界，不声称已解决。 |
| 3. 通用 action freshness 没有生产消费者 | 保留非执行性兼容接口；不接入伪授权路径。现有定向 mutation 使用独立的受控消费流程。 |
| 4. 未知 action 默认自动允许 | TASK-0047 已修复：仅 Policy 明列 `read` 可允许，未知类别默认拒绝，六项高风险继续拒绝。 |
| 5. push/merge 缺少通用强制执行点 | 仍是明确限制；每次真实外部动作须单独授权，本地 actor 不是可信身份。 |

第 2 项的真实动作证明及第 3、5 项的外部执行能力，需要先确定可信身份根、服务端授权
与原子消费、固定操作范围、凭据托管、审计和恢复边界；不能仅靠增加本地批准文件解决。
设计输入见[动作执行边界](../../.ai/tasks/TASK-0047/action-boundary-design.md)，本次不授权
选择、部署或接通新执行器，不放宽质量门禁，也不重开已否决的审批整改方案。

## 暂不进入的路线

[阶段三](../implementation/phase-03-entry-inputs.md)仍 not_started：缺少冻结的样本标准、
真实 V3 用例/沙箱回滚边界和统一 telemetry 口径。V3、模型路由、信任评分和资源调度
是后续路线，不属于当前版本的未完成承诺。本次不改变这些进入门。

## 重放入口

- `python tools/analysis/approval_overhead.py --format text`：账本快照。
- `python -m aiflow status TASK-0044`：读取当前关闭状态；合并前 Gate 需在其历史记录
  分支/版本上重放，不能将终态任务在后续 main 上的旧证据绑定当作新的待审核请求。
- `python -m aiflow status TASK-0028` 与 `python -m aiflow gate TASK-0028 --format json`：历史阻断。
- `python -m aiflow status TASK-0045`：读取本轮配置修复的关闭状态；合并前 Gate 事实
  见该任务核查补记及其记录版本。
- `python -m aiflow status TASK-0046`：读取已交付 ASK 修复的关闭状态。
- `python -m aiflow status TASK-0047`：读取风险输入修复的关闭状态；后续维护动作仅追加
  独立 action 审计，不重复关闭任务或改变其历史实现证据。
- `git log main..claude/unruffled-gates-41d3ec --oneline`：旧候选历史，不等于当前待实现清单。
- 远端开放项、保护配置与分支位置会变化，交付前重新读取；本页的只读快照不是授权。
