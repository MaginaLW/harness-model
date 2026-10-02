# E4 启动前交接与后续工作计划

## 2026-10-02 收尾交接：下次从报告回收与待办入口接续

- E4 交付/闭账及四项任务分配已经完成。最新[ZCode 收尾快照](../../operations/zcode-next-stage-assignments-2026-10-02.md)为四会话 completed；报告内容仍待回收/审核，不重发或从历史 A 重开实现。
- 下次按[六项待办](../../operations/follow-up-backlog-2026-09-22.md)选可验收单元，依据[启动条件](../../operations/next-stage-start-conditions-2026-10-02.md)准入。报告核对可按项目并行，F 准入/真实报告/预检/记录/原生收尾串行；具体实施再确定独占范围和 sub-agent 数量。
- 本次并行两个 sub-agent 只读核状态与交接，主 agent 串行编辑、验证和本地提交。后继实施与本地记录远端发布未执行，旧快照和历史全文保留。

## 2026-10-02 最新接续：四项准备任务实际分配完成

- [ZCode 任务记录](../../operations/zcode-next-stage-assignments-2026-10-02.md)已补四个真实会话 ID/项目及准确状态快照；各项只读报告，没有重发、重启旧会话或实施后继阶段。
- 当前进入门以[启动条件](../../operations/next-stage-start-conditions-2026-10-02.md)为准；F 目标准入到导入/原生收尾仍串行，其余准备独立。原生 3 名 sub-agent 并行核权限/保全、元数据、记录；主 agent 串行 UI/文档/账本与统一提交。旧锁屏快照和历史全文保留。

## 2026-10-02 接续计划：只读准备先行，实施按进入门

- E4 已交付，后继按[启动条件](../../operations/next-stage-start-conditions-2026-10-02.md)逐项准入；不从历史 A 重开，不向已 MERGED 目标导入。
- [ZCode 四项任务](../../operations/zcode-next-stage-assignments-2026-10-02.md)只输出各项目会话报告，可并行；主 agent 串行记录/提交/分配，2 名原生 sub-agent 只读核条件与项目元数据。
- F 新目标 → 匹配真实报告 → preflight → record → 原生收尾串行；E5/I5 与外仓证据准备独立，不以 F 完成为前置。未来实施另定独占文件/并发，历史全文保留。

## 2026-10-02 最新核定：E4 实际交付完成，F 仍待真实报告

- 固定 S `993a9a0619577117417d80de96e73aa18270b464`、发布 Q `f5707ff178b760bb0215c7d5cb773cc4d06c75d6` 经 [PR #44](https://github.com/MaginaLW/harness-model/pull/44) 保护合并为 M `db3efabab562971aef1a6eb1317b679d42eeadb9`。实际独立核验及主 agent 复核 M 有序父提交 `[48bf777106b9fdfef1ddf83d3abc95859fb8e580, Q]`、M/Q 等树、完整来源历史及本地配置提交524排除；保护和质量阈值保持。
- TASK-0062 原十项 Windows V1 全通过：单元1994、回归及覆盖率轮各3008通过，分别仅保留同一既有Windows FIFO跳过；独立Design/Implementation审核、批准、准确Q Gate完成。完整 [required CI](https://github.com/MaginaLW/harness-model/actions/runs/36939643115) run36939643115/attempt1/check110627914984/app15368 SUCCESS：合约185，Linux完整测试3004通过/5既有平台跳过，总覆盖率88.92%≥85%、累计diff94%≥90%、whitespace/Ruff/format605/mypy44通过。whitespace依据原连续 `bash -e` 脚本及整步成功作顺序推断。
- 原固定证明唯一 association MISMATCH/STOP 不改写；非作者审查后的窄增量实际正向绑定合并前后同一不可变run/check-suite/job/attempt，另完成20个历史祖先在S/Q/M中的60次实际比较；其余原111项正向事实保持。复合结论 COMPOSITE_PROVEN 已复核，关联数组变化原因 UNKNOWN。
- 证明后才实际 fetch M、核本地对象并fast-forward，TASK-0054/0055/0056/0057/0062各原生close一次为MERGED、merge_commit=M，随后五份记录校验通过。本地追加治理提交 `84029ccabf6ea607c748c233615e6f0b8d53f407`，见 [TASK-0062 closeout](../../../.ai/tasks/TASK-0062/closeout-001.md)。post-Q记录不冒充属于Q/M、不递归发布；普通本地整合保留原历史、两份配置及三份用户草稿，最终事实另由独立非作者审计。
- 53保持push-only，58/59/60三次准确CI失败与61实际FAILED保留原状态及全部原件，本次成功不替历史失败闭账。I1/I2/E5/I5、Phase3/4、TASK-0028 Option C等条件阶段不启动。
- F仍缺目标匹配真实ZCode原报告：既定本地及相关PR有界只读搜索已完成且无匹配，不声称全局无报告，未执行真实导入验收、不以synthetic替代、不启动provider或付费调用。
- 最终并行2个sub-agent：非作者审计实际主工作区整合，源码作者仅独立于发布操作者核对operation记录；主agent负责三份文档、统一提交及依赖串行的本地合并。以下历史全文保留。

## 2026-10-02 最新核定：owned commit 自动维护输入已隔离，完整新发布验证待执行

- 最窄 task-free 测试修复已独立审查并提交 `e8b2f5d21fb3d1f3ff34b90c387e02769d2f1765`，只改三份测试文件：fixture SHA `279661c9d28ab94121c3d2b2f7dc15b75c6028c0849ae96cc9a0428ef9088ebd`、helper SHA `b1d40bc4feedace0f8a1b48e7920cdeee82eb5506607165452e7f61ae756e443`、test SHA `719b4f727b27369237f134a0377ac01c12a774624080e09bb4b5cbe282dc18d6`。仅真实匹配的 owned private context、可识别 leading separated `-c` 后的 commit 在最后一个 global 参数位置插入临时 `maintenance.auto=false`；不写 host/repo 配置。default、foreign、noncommit、未知 global 形式的 argv 保持原样，原环境 binder 不变。
- 新 argv binder 的函数 object/code 纳入原 `_standard_io` 顺序检查，原 direct-current entry、qualification、模板 types/names/bytes/modes、配置允许表、父环境拒绝、owner、seed、assertions/skips、copy/thread 与10秒清理完整 AST 保留。本轮固定源码全部旧103个 named tests（fixture81/helper22）完整 AST 不变，新增4个 named/10个 cases；不放宽 unknown-input 或 warm eligibility。
- 作者最终 `a091e4/0` 实际两完整相关 modules **204 passed / 0 skip /119.66s**，10新增 cases、Ruff/format、mypy44、whitespace 均实际0/retained closed。作者两组受控对照合计18条真实 Git 命令0/closed；Git `2.55.0.windows.3` 默认策略的两个 object17 输入会产生 pack/info/refs，owned commit 的最后 false 则保持 loose、不生成 refs/packs。control 未持久化；标准 git init 创建 `.git/config` 属正常初始化。
- 非作者 `9ced01/0` 真实独立对照9条 Git0/closed，7个首轮成功反例加1个仅修正私有 CONFIG 期望的参数通过；原私有首轮1退出与全部原件保留，不声称单轮8项通过。额外 info/refs、未知 system config 仍冷拒绝，dispatch object/code 漂移 direct-current 拒绝且不命中；normal/error 恢复保持。保护 tracked1964/runtime225/Gitpair/refs/index/topology/HEAD 前后完全一致。Root `28415b/0` 复核作者286件、`8961c6/0` 复核独立66件、`76ec78/0` 核实保护原件字节全等、`3ce7d1/0` 验证103旧 AST；真实 staged whitespace `ee855b/0`。
- [Git v2.55.0 commit 源码](https://github.com/git/git/blob/v2.55.0/builtin/commit.c) 与 [自动维护源码](https://github.com/git/git/blob/v2.55.0/builtin/gc.c) 支持 commit 自动维护及 command-local false 的控制点；官方12原件 HTTP200/哈希已核。历史失败 seed 的生成进程、维护前 object17 数量与唯一因果仍 **UNKNOWN**，受控对照不伪装为历史进程 trace，也不预测下一 Linux 结果。
- TASK-0061 全原生9通过/回归1失败及随后覆盖率轮成功保持原始 FAILED 结论；其35原件/20logrefs、独立45件归档已由 Root `a95d7e/0` 复核。53 push-only、58/59/60 三次准确 CI 失败与61本地失败分别保留，不用未来成功 native-close。新发布任务待实际分配，须固定新的累计源码、真实 Design/Implementation 审核、原有10项3150/3450/MINENV验证、准确Q Gate及完整 Linux required CI（85 overall/90 cumulative diff/whitespace/Ruff/format/mypy）才可 protected merge，再独立证明 M 后闭54/55/56/57与成功新发布任务。
- 最新5个显式只读 GET `633e8b/13d969/15da90/2977ad/8961e1` 均实际0/retainedclosed；Root `fe0b22/0` 复核31件 snapshot：B仍 `48bf777106b9fdfef1ddf83d3abc95859fb8e580`、feature仍 `f402bd7ab1fbe6c6415117817d3adb0ec62899ac`、PR44 OPEN/non-draft/unmerged、strict required app15368/enforce-admins完整保护不变。此 snapshot 不是 action 批准、CI 成功或 M 证明；每次远端写入仍另核新鲜事实与一次性参数。
- 两名 sub-agent 继续并行非作者累计审查/独立 operation 审计；Source admission、native、准确Q Gate、push、PR字节审核、完整CI、protected merge、证明/fetch/close/本地接回按依赖串行。主工作区17196、本地524配置与三份用户草稿保留，524不能发布。真实匹配 ZCode 原报告 F 在既定本地及相关PR搜索边界仍缺失；付费/provider与条件未满足的后续阶段不启动。


## 2026-10-02 最新核定：TASK-0061 完整原生验证失败，发布仍暂停

- 固定源码 `508cf73d10be4cdd2ca4409e706fe68ead10a69d`、规格准入提交 `b17e3879b5a1e5a95510a70bbce91ddf868e6d28` 的原有 10 项 V1 已全部真实执行；`fbda31/0` 的 CLI 退出 0 表示记录完成，原生任务与 evidence 真实结论为 **FAILED**，不能据此发布。
- 回归测试实际 `1 failed / 2997 passed / 1` 既有 Windows FIFO 跳过，720.40 秒；单元 1994 项通过。独立覆盖率轮实际 `2998 passed / 1` 同一既有跳过，848.06 秒，XML 行 `7856/8588=91.48%`、分支 `2517/3060=82.25%`；后轮成功不抹去前轮失败。其余原有检查通过，预算、选择器、MINENV 和阈值未调整。
- `test_private_system_context_drift_cannot_reuse_snapshot[factory]` 在初次 seed 资格检查、factory 修改前失败。可信位置 `_qualify:548 -> _template_fact:277` 比较投影后的类型、名称与字节；现场 seed `.git/info` 多一个普通 `refs` 文件（57 字节，SHA `26ce8b7a0e476b303b8f35537af85731c247b474eeaf30dc2523ef173da88b15`），其余模板文件字节与模式相同。非作者与作者分别只读确认，Root `d2b19d/0` 复核独立三件诊断原件；模式差异和 factory 修改不能解释该失败。
- 同一现场有 pack、reverse index、multi-pack-index 与 server-info，支持自动维护候选；实际生成进程、触发条件与唯一根因仍为 **UNKNOWN**。先研究真实 Git commit 的自动维护控制点，再做最窄 task-free 维护修复；不放宽模板比较、配置允许表、原断言或跳过条件。
- 实际 retained35744、creation134353619377042605/exit134353636332839767、launcher0/closed/no timeout；外部 tracked1952、runtime225、Git pair、refs/index/topology 的冻结前后完全一致。失败证据和20日志引用已随 `16d3373` 原样入历史，详见 `.ai/tasks/TASK-0061/native-validation-failed-001.md`。TASK-0061 未实现审核、代码批准、Gate 或任何远端写入，不能由未来成功闭为 MERGED。
- 远端仍为原第三次失败 head `f402bd7ab1fbe6c6415117817d3adb0ec62899ac`，PR44 未合并；TASK-0058/59/60 的三个准确 CI 失败记录与 TASK-0061 本地失败各自保留。后续新固定源码须有新的真实发布准入、全原生验证、非作者审核、准确 Q Gate、完整 required CI 和 protected merge/独立远端证明。54/55/56/57 与成功的新发布任务才可在实际证明后闭账；53 仍 push-only。
- 两名 sub-agent 并行：作者只修三份测试文件、核真实 Git 输入，非作者独立归档失败与审核新候选；Root 负责治理、文档、统一提交和串行发布。主工作区历史、本地配置与三份用户草稿继续保留；真实匹配 ZCode 原报告 F 在既定搜索边界仍缺失，不进入付费 provider 或未满足条件的后续阶段。


## 2026-10-02 owner 私有系统配置修复完成，进入新发布验证

安全提交9191a646a12c3ea2891303f28c223d0e787ae56e仅修改3个test-only文件；真实原run_git和bounded Popen统一选用owner私有空系统配置，父环境不写GIT_CONFIG_SYSTEM，默认、未拥有cwd及foreign路径继承原输入，non-Git命令不变。
资格事实同时绑定当前owner/factory/root/context、实际子环境和普通配置文件dev/inode/完整字节与mode；配置漂移保持固定冷读取路径，选中输入缺失或不安全时明确失败。同字节换文件、移交旧资格、更换context及可信fact函数/代码替换不能暖命中。
最终候选两个完整模块真实865896/0：194 passed、0 skipped、100.67秒；夹具152及helper42。新增10个named测试、19个参数实例；原71+22 named测试完整AST、原断言/skip、owner/seed、配置和环境守卫、allowlist、线程/复制及进程清理逻辑保持，Ruff/format/whitespace/mypy44真实通过。
独立02663a/0在最终3hash上8项真实Git反例通过；两项实质Finding均已复现并修复，正常和异常teardown、system对照、同字节inode及owner/context变化、无所有权路由已核验。主agent22bc8a/0重算作者123件，15119f/0重算非作者66件并核实际retained退出0/closed；e2f750/0另核原93 named AST及守卫。
固定SHA256：repository_fixture.py c7d1c3f82c738d7c8d7b81c3fbffe8c0ec22be7da4de8820dd0f6a02d8b5218c；test_begin_close_commands.py ea1beba55b6144145a05933a31b45fec09d95f0f6a6003334036446d52b65316；test_repository_fixture.py fe0d704ab6c5e86f2fc9919416cad6b677bac56b20367c6371001c02f2fa7ee9。
[准确镜像安装脚本](https://raw.githubusercontent.com/actions/runner-images/ubuntu24/20260927.320/images/ubuntu/scripts/build/install-git.sh)与真实受控Git对照证明system safe.directory是充分的unsupported输入候选；主agent52f7ba/0复核37件独立诊断。未直接观察失败Linux runner有效key或唯一根因，仍UNKNOWN；专项Windows成功不替代新准确head Linux整链CI。
原三次准确CI失败、观察测试首轮错误、旧193/20中间候选与事实入口反例均原样保留，不冒充最终验收。58/59/60冻结历史及名义状态不改，未来新CI成功不将它们native close MERGED；53保持push-only。
下一步真实分配新publisher并冻结实际S，执行全部原选定V1检查、非作者Design/Implementation Review、批准与准确Q Gate，随后普通推送/PR44更新、完整准确CI、保护合并和独立M证明；之后才close54/55/56/57及新publisher并整合主检出。
并行阶段启用2个sub-agent：非作者累计代码/治理审查与独立操作审计；主agent负责统一提交和准入。源码冻结、完整验证、Gate、外部动作、完整CI、证明/close串行，不在冻结期修改source/runtime/refs/index/topology。
此阶段未再次推送、合并、执行Mproof或close；F有界搜索仍缺目标匹配真实ZCode原件，条件阶段、Task28及历史BLOCKED保持，无provider或付费调用。


## 2026-10-02 TASK-0060 准确 Q CI 再次失败，先诊断系统配置

TASK-0060 的固定S14d80213已完成全部原生10/10检查、独立Design/Implementation APPROVE和准确Q Gate；Qf402bd7ab1fbe6c6415117817d3adb0ec62899ac实际普通推送并更新既有PR44，字节回读一致。
准确Q required run36914902620/attempt1/check110546355233 app15368真实FAILURE：16 failed、2928 passed、36 skipped，612.84秒；原14个CONFIG阻挡用例及新增环境隔离正向、GIT_ENV反例仍在参考init前失败。
含branch总覆盖率88.92%达到85%，pytest exit1使累计diff90、whitespace、Ruff、format、mypy均未执行；Windows完整验证与专项对照不替代Linux整链CI。
主agent实际4cf52b/0重算独立操作手回全部115件及18只读GET终态，确认准确Q/app/run/attempt/event/path/PR44真实失败；原始job log97740字节SHA2569393b35785447ea57680bc929b6785b0d80645c452bd8672530a85607f3a49cd保持。
Task60真实动作、批准事件、调用次数和失败说明已单独提交1fbf1bc；这些是post-Q本地治理，未包含于远端Q。原Task60冻结规格、Review、验证和名义APPROVED_FOR_MERGE状态保持，不用未来CI成功将58/59/60 native close MERGED。
当前Linux有效配置key/来源及唯一失败分支仍UNKNOWN；准确镜像安装脚本提供系统配置候选，须真实Git受控对照和独立审查，禁止猜测原因、扩大配置白名单、跳过原断言或放宽门禁。
并行阶段启用2个sub-agent：作者定位最小受控测试环境修复，非作者核对镜像证据与资格守卫；主agent复核历史证据及统一阶段提交。源码冻结、完整原生验证、发布、准确CI、保护合并、独立证明及close串行，依赖修复审查通过。
未合并、未执行实际M证明、未fetchM或关闭源任务；修复超出Task60 own scope，安全源码独立提交后须真实分配新publisher，完整执行全部原选定检查及准确head整链CI。最终适用close仅54/55/56/57和新publisher；53仍push-only。
F经有界本机及相关PR只读搜索仍缺目标匹配真实ZCode原件，不声称全局无报告；条件后继阶段、Task28及历史BLOCKED保持，未调用provider或付费接口。


## 2026-10-02 夹具私有测试环境修复已提交，准备新发布验证

安全测试提交b3a26da66915b9371dc52af296ead4f297b5748e只修改test_repository_fixture.py；其模块owner依赖私有HOME/XDG并移除继承GIT_*，保持系统配置和原配置、环境、模板及metadata资格守卫。
实际正常环境989081/0与原生同形最小环境5d3d69/0各133 passed、0 skipped；新增3个named测试及5个实例，原68个named测试的完整AST、断言、skip及owner原body保留。
实际Ruff、format、whitespace、mypy44通过；独立正常退出与注入body异常两项真实参考init/warm探针89b7b5/0证明环境、原owner全部字段及宿主配置字节恢复，最终无未解决Finding。
实现文件repository_fixture.py固定9fca08f11b9c528dcc725c9be0b19be2d91b8d3b983b65c7194c8933082713ff未变；测试固定d80cfff00740bf312f76922e2fd01a4cac91f9551951529df3968af198af1a03。大小写字典反例不冒充真实Linux执行，Ubuntu实际触发key仍UNKNOWN。
原132通过的中间版本、两次真实准确head CI失败及全部诊断原件保持；当前专项成功不替代新publisher的完整原生验证或准确head Linux required CI。
新publisher须真实分配、冻结、独立Review及完整原选定检查；58与59保留失败发布名义状态，未来适用native close仅54/55/56/57及新publisher，53保持push-only。
此阶段未再次推送或合并；2个sub-agent分别独立代码治理审查与操作审计，源码冻结、验证、提交、推送、PR更新、完整CI、保护合并、独立证明与close串行。
F经有界本机及相关PR只读搜索仍无目标匹配真实原件；条件后继阶段、Task28和历史BLOCKED保持原进入条件。

## 2026-10-02 TASK-0059 已推送，准确 Q CI 配置守卫失败，继续修复

新 publisher TASK-0059 已完成真实 REVIEW/V1 准入、全部原生10/10检查、独立 Design/Implementation APPROVE、代码批准与准确 Q Gate。
固定源码S6c28ca6、本次完整回归/覆盖率各2974 passed及1原FIFO skip；最终发布Q a2654bdf5c6ba02f2a5e1633d090e3b0d1cf583e已普通推送并回读，既有PR44标题/正文独立审查及字节回读一致。
准确Q的required run36901129804/check110500282851 app15368真实FAILURE：14 failed、2925 passed、36 skipped，608.39秒；四个原有用例与十个新增实例均在原UNSUPPORTED_CONFIGURATION守卫被阻挡，尚未进入参考init；原31warm skip保持。
含branch总覆盖率88.92%已达85%，但pytest exit1使累计diff90、whitespace、Ruff、format、mypy未执行。主agent另做累计whitespace实际exit0，该本地结果不替代CI。
实际Ubuntu有效配置触发key/branch仍待有界诊断；checkout日志中的safe.directory设置不足以证明唯一根因。两个sub-agent分别负责最小实现诊断与非作者独立复核，不放宽原守卫、断言、skip或门禁。
真实动作、未执行的参数绑定错误批准和准确Q失败已追加至Task59并单独提交b5dd05f；这些是post-Q本地治理，不能说已包含于Q。
修复超出Task59 own scope，须独立安全源码提交，再真实准入新publisher、执行全部原选定检查及准确head完整CI。旧58/P与59/Q失败原件保留，未来成功不使它们native close MERGED；53仍按push-only名义状态及完成记录保持。
未合并、未做M远端证明、未关闭源任务54/55/56/57；后继串行为准确推送、PR更新、完整required CI、保护合并、独立证明、fetchM与适用任务close及本地主检出整合。
F仍缺匹配真实ZCode原件；有界本机搜索与相关PR只读补查无正向结果（PR44审查/评论、PR39/43审查均为空），不据此宣称全局无报告。条件阶段、Task28及历史BLOCKED保持，不调用provider或付费接口。


## 2026-10-02 夹具参考 Git 初始化修复，专项验证通过

测试夹具不再假定安装模板与 Git 初始化目标的权限完全相同；在所有原配置、环境、Git、模板、attributes、current/pristine 守卫通过后，执行一次 owner 私有空目录参考初始化。
源模板完整 mode/bytes/types/names 继续绑定；源到两个初始化目标的 types/names/bytes 完整匹配，两个目标之间仍核对全部 metadata，包括 mode。
原 cold/hit、warm 不重新 init、snapshot/target-mode、线程和复制行为保持；未知、输入漂移及 partial 失败仍冷回退，异常诊断只输出固定类型与可信代码行。
固定两文件 SHA256 为 repository_fixture.py 9fca08f11b9c528dcc725c9be0b19be2d91b8d3b983b65c7194c8933082713ff，test_repository_fixture.py e8790190b12ffdb476bf349f2c7eb547a3da909216dc80b9785df5eea818dbb1。
原生同形 MINENV 专项实际 061bd0/0：128 passed、0 skipped、55.02 秒；Ruff 与 format-check 通过。实际新增13个 named 测试、31个参数实例，原55个 named 测试及 thread/copy/parallel AST 保留。
首次 full-env 专项受宿主 unsupported configuration 遮挡，真实失败原件保留；未修改全局配置、守卫、原断言或 skip。该宿主结果与真实 Ubuntu 唯一根因不等同。
独立实际 diff/AST 与9项私有反例通过，无未解决 Finding；共同污染、实际 mode 差异、未知异常回调及异常链均核对。原44文件 mypy 通过；额外311运行因旧 checkout 绑定被排除，不作为本实现兼容性验收。
2名 sub-agent 分别负责实现与独立审查，主 agent 负责统一阶段提交及串行发布；新 publisher 准入、完整原生检查和新准确 head CI仍待执行。
修复测试/状态文件先按维护模式独立安全提交；随后真实分配新的 publisher task，重新冻结、Review、执行全部原选定验证、批准和准确提交 Gate，再更新既有 PR44。
Task58 原 P a2894ac3 的 required CI FAILURE 保留；其 own scope 不覆盖新测试字节，不同步旧 subject、不复用旧验证、不 close MERGED。新任务承接后追加实际指针，旧 P 失败不能由新 Q 成功改写。
Task53 按 push-only 规格保持原名义状态及完成记录；Task28 和历史 BLOCKED 保持。最终适用任务只有在完整准确 Q CI、保护合并及独立远端证明后才 native close。
此阶段未再次推送、未合并、未做实际 M 证明；F 仍缺目标匹配真实 ZCode 原件，条件后继阶段保持进入条件。

## 2026-10-02 PR #44 已创建，准确提交 required CI 失败，修复进行中

累计发布实际使用 TASK-0058（REVIEW/V1），源码S715496d、发布P a2894ac3；完整原生10/10检查、非作者累计Design/Implementation APPROVE、代码批准及准确P Gate已通过。
普通推送首次180秒超时的原件和后代历史UNKNOWN保留；独立核对已知后代当前缺席后，单独新action采用仅命令局部GH凭据协议，实际exit0并回读准确P。
PR [#44](https://github.com/MaginaLW/harness-model/pull/44) 实际创建、已附加；headP/base48bf777及正文原件完全匹配，创建前严格main保护/app15368只读核对保持原设置。
准确P的required run36883821312/check110441969044在2026-10-01T15:34:30Z真实FAILURE：34 failed、2905 passed、5 skipped，663.40秒；失败全在test_repository_fixture资格检查。
含branch总覆盖率88.92%已达85%，但pytest exit1使累计diff90、whitespace、Ruff、format、mypy尚未执行。未合并、未做远端合并证明、未关闭任务。
当前最窄诊断范围是fixture的_qualify在check-attr之前；Linux模板mode差异有受控反例，真实CI唯一底层原因仍UNKNOWN，需实际定位和最小安全修复。
2名sub-agent分别负责fixture诊断/最小候选和非作者独立核对；主agent保留实际失败治理、按新源码准入/原必需验证/Gate，再串行精确推送、完整required CI、保护合并与证明。
真实动作与失败记录见[Task58追加原件](../../../.ai/tasks/TASK-0058/required-ci-failure-001.md)；其后本地治理提交66595bd尚未发布，不能说P包含动作后记录。
Task53按真实push-only完成记录保持名义APPROVED_FOR_MERGE，不为本次PR误作MERGED；Task28选项C及历史BLOCKED保持。
F仍缺目标匹配真实ZCode原报告；有界本机搜索没有正向结果，其他条件阶段沿用原进入条件。

## 2026-10-01 TASK-0057 修复与完整 Gate 通过，进入累计发布

独立累计审查发现的解析缓存 P2 已由新 TASK-0057 修复；生产提交4bcedba、安全测试与说明提交afff062分开保留。
有限 dispatch 资格检查覆盖标准 Loader 方法、实际 globals、依赖成员与配置；未知或变化时回退当前解析，不承诺任意 Python 认证或并发配置原子性。
固定源码完整原生 V2 实际14/14检查、原5/5 mutation通过；unit1994、regression/coverage2943 passed及1原FIFO skip。
XML行覆盖率91.48%、diff92.37%；完整integration912 passed及1原skip，462.99秒，保持原600秒期限。
实际独立REV-0002/r1 APPROVE；同一verifier仅一次finalize，完整snapshot与所有检查保持，真实原生event delta为0。
代码批准后治理6fa7658提交；该准确提交的Gate实际exit0、passed=true，详见TASK-0057/native-v2-final-review-gate-001.md。
旧失败、原审批与审查及TASK-0056全部106件原记录保持；审查包首次格式拒绝和三项标记修正均保留，不重跑验证。
TASK-0054/55/56/57本地实施已具备当前Gate；下一步单独准入累计发布任务，准确编号与验证等级以CLI为准。
2名sub-agent分别负责非作者累计审查和独立远端动作核验；冻结候选、完整选定检查、推送、PR、required CI、保护合并及远端证明依次串行。
此记录时未推送合并；匹配真实ZCode原报告的有界本机搜索无正向结果，F仍缺输入，条件后继阶段保持原进入条件。

## 2026-10-01 TASK-0055 Gate 通过，累计审查发现解析缓存 P2

TASK-0055 自身当前源码2e6f69f完成完整原生14/14与原5/5mutation；regression/coverage2891passed、1原FIFOskip，XMLline91.46%、diff95%。
实际独立REV-0006/r1 APPROVE，同一verifier一次finalize；首个私有引用结构审计失败保留，只读修正通过，未重跑。
代码批准后治理c810fd2提交，提交后Gate实际exit0、passed=true；记录见native-v2-final-review-gate-007.md。
累计发布预审随后实际复现解析缓存P2：同一SafeLoader方法覆盖或constructor.datetime全局替换未触发绕过，旧缓存与当前safe_load结果不同。
发布继续等待独立新治理修复；既有TASK-0056的106个原记录保留。主agent负责准入/统一提交，2名sub-agent分别准备实现与非作者设计边界审查。
修复任务编号、分类与后继发布候选以实际CLI分配和验证为准；完整原预算、选择器、85%/90%与required CI保持。
未推送合并；匹配真实ZCode报告的有界本机搜索无正向结果，F仍缺输入，条件后继阶段按原进入条件。

## 2026-10-01 TASK-0055 transport 与平台类型修复，完整 V2 待执行

TASK-0055 已导入 TASK-0056 的准确已 Gate 依赖80515e6，重新准入自身 REVIEW/V2。
transport e03bfb1 与分离的安全测试/文档72294c1完成两模块305passed、1原FIFOskip；首次新增替身失败原件保留。
额外 Linux 平台 mypy发现4个Windows API属性错误；追加规格b5cf71ea和实际独立REV-0005批准后，2e6f69f仅改4个无默认getattr表达式，原平台guard/值/调用保持。
完整 Windows与Linux平台静态mypy各44文件通过，Ruff/format通过；现有相关单元190passed，实际退出0。Linux真实进程用例仍待准确发布head的CI。
自身新source已sync并登记新单次action006；完整原生14checks/5mutations、实施Review/finalize/code/Gate尚待执行，旧依赖通过不能替代。
随后累计发布依准确source/head/base、完整required CI和既有push/merge授权；有界本机搜索未找到匹配真实报告，F仍缺输入。
此记录时未执行推送合并或provider调用，后续阶段仍按进入条件。


## 2026-10-01 修复后完整 V2 与最终 Gate 通过

TASK-0056 当前源码 9dca04d 完成默认原生 V2：14/14 检查、5/5 fixed mutation，全程保留原预算与检查。
regression/coverage 各 2831 passed + 1 原 FIFO skip；XML line coverage 91.42%、diff coverage 97%。
完整 integration600 为 906 passed + 1 原 FIFO skip，545.48 秒，原生与工具均实际退出 0。
RF-001 已由原独立 reviewer 在 REV-0009/r2 追加解决；旧拒绝原件保留，新的 REV-0010/r1 为 APPROVE。
同一独立 verifier 单次 finalize 实际退出 0，证据 phase=final；14 checks、5 mutations、snapshot/context 未变。
代码批准已登记，状态 APPROVED_FOR_MERGE；治理提交 80515e6 后 Gate 实际 exit0、passed=true。
记录见 TASK-0056 的 native-v2-current-source-passed-026.md 与 native-v2-final-review-gate-027.md。
原 40 件归档、全部 24 源码与九件旧失败/消费记录已核对；已知句柄与输出资源交回，历史未观测后代 UNKNOWN。
TASK-0055 工作树已 ff-only 导入准确已 Gate 依赖 80515e6；自身新准入、transport 修复与完整 V2/Gate 仍待完成。
随后累计发布须独立冻结候选、required exact-head CI、已授权 push/merge 与远端状态/父节点/树/祖先核验。
有界本机查找未发现匹配真实 ZCode 报告，F 缺输入；此阶段未推送合并或调用 provider。

## 2026-10-01 修复后四阶段前置通过，完整 V2 待执行

当前源码 9dca04d 在核验 HEAD 9ba0f8b 完成原四阶段：12 narrow、97 fixture、187 external + 1 原 FIFO skip。
集成实际 collect 907 unique，原 867 与新增 8 均保留；906 passed + 1 原 FIFO skip，529.81 秒退出 0。
runner 实际 530119 ms，满足原 600000 ms；完整前后快照相等，87 retained 句柄及 launcher driver 退出 0。
已知资源已交回；未 retained engine 退出与历史未观测后代 UNKNOWN。
首次集成实例未保存退出结果，保留 UNKNOWN；其唯一快照差异为 refs 摘要，原因未确认。
复验使用逐字节原脚本和原预算，三个已通过阶段保留原件复用，未削弱完整快照断言。
当前 D cold1/warm10 中位 67.5486 ms；这不代表直接观测并发选择或因果加速。
治理 4bb8a60 追加记录 025 和已原生批准的单次 action006；原规格批准有效，RF-001 仍 open。
新源码完整 14 项 V2、独立 implementation Review/finalize/code approval/Gate 尚未完成；旧 V2 仅属旧源码证据。
随后依次为 TASK-0055 重新准入与自身完整 Gate、TASK-0057 required CI/已授权发布及远端核验。
本机有界查找未发现匹配真实报告，F 缺输入；未推送合并或调用 provider。

## 2026-10-01 原生 V2 通过，源码审查要求修复

TASK-0056 的 113ecdd 候选实际完成原生 14/14 检查及 5/5 mutation；
总覆盖率 91.42%、diff coverage 97%，原 integration600 实际 898 passed + 1 原 FIFO skip，555.97 秒。
本轮 snapshot 4076be51、完整原件与 40 件归档均已核对；已知资源退出，未观测历史后代 UNKNOWN。
独立源码审查 RF-001 指出 Git fixture helper 在启动后的非超时异常分支缺少原有直接子进程清理。
安全修复 9dca04d 已提交；完整 begin/close 模块在原 MINENV 下 42 passed、28.16 秒，无跳过或超时。
治理 9ba0f8b 保存正式 REV-0009 拒绝记录及新源码绑定；状态仍 WAITING_FOR_FINAL_REVIEW。
原规格批准有效；新源码的完整前置与 V2、重新审查仍待执行，旧 RF-001 保持 open。
修复已提交，新源码仍须完整验证和新的 implementation Review；本轮未 finalize/code approval/Gate。
单次 action005 已实际消费；旧通过证据保持，不代表修复后候选已通过。
本机有界查找未发现匹配真实报告，F 缺输入；TASK-0055、发布及后续阶段依原进入条件。

## 2026-10-01 完整前置通过，原生 V2 待执行

候选 113ecdd 在核验 HEAD 1158a08 完成原四阶段：12 narrow、97 fixture、187 external + 1 原 FIFO skip。
完整集成实际 collect 899 unique、原 867 全保留；898 passed + 1 原 FIFO skip，576.91 秒退出 0。
runner 实际 577173 ms，满足原 600000 ms；源码前后一致，已知资源交回，历史未观测后代 UNKNOWN。
本候选 D cold1/warm10 中位 73.8351 ms；旧 96/1 和历次 600 失败保留，旧瞬态原因仍 UNKNOWN。
治理提交 0ae0199 追加 TASK-0056 记录 022，并绑定新的单次 action005；原 action 不复用。
此为前置 PASS；尚缺完整原生 V2、正式 Review/finalize/code approval/Gate，未推送合并。
TASK-0055 自身准入、发布及匹配真实报告 F 的进入条件保持。

## 2026-10-01 新测试输入已固定，动态验证待执行

安全提交 113ecdd 仅向新增 256 文件用例加 9 行：固定并回读两目录时间，检查源未变。
helper、原 65 用例、精确 metadata 与线程断言及原预算均保持；独立静态预审通过。
治理提交 1158a08 后原生 status/scope/validate 实际 0，fresh/current，仍缺 implementation_result。
旧 fixture 96/1 失败和单次串行 258 项等值对照保留；旧瞬态未复现，原因 UNKNOWN。
记录见 TASK-0056 的 parallel-copy-test-input-stabilization-021.md；新候选 warm/前置检查待执行。
尚无新 integration600、V2 或 Gate 通过；TASK-0055、发布和匹配真实报告 F 仍依原条件。

## 2026-10-01 warm 与端点验证完成，fixture 新用例失败

固定 4c8952b 候选实际完成 D/C 各 10 次完整 warm，中位数 73.61/102.24 ms，选择 D。
端点组实际 12/12 通过；完整 fixture 实际 collect 97，原 65 全保留，96 通过、1 失败。
失败是新增 256 文件用例的 child 目录 mtime 精确等值，差约 20 ms；原因待诊断。
原 240 秒内 51.32 秒退出 1，无超时；四 worker、线程归零、256 次复制断言先已通过。
源码与旧证据守卫一致，已知资源已交回；历史未观测子孙仍 UNKNOWN，未重试或改断言。
失败与实际测量追加至 TASK-0056 记录 020；external、原 600、action005、V2 尚未启动。
TASK-0055、推送合并与真实报告 F 保留原进入条件；当前不记为 Gate 或任务完成。

## 2026-10-01 有界复制候选已固定，实际验证待运行

安全源码独立提交4c8952b，治理收尾949c53e；native sync/status/scope/validate均exit0。
当前IMPLEMENTING/REVIEW/V2、classification fresh、approval current，仍缺implementation_result。
固定26af/eed源码经独立004预审，无剩余静态阻断；原65保持，新增静态预计32尚未collect。
线程归属、unknown终态、child回收和shutdown首失败重入已核；此不是运行/V2/Gate PASS。
完整warm与前置脚本须绑定当前实际receipt后串行执行；原600/55/发布/F条件保持。

## 2026-10-01 线程归属修复短案已接受，实施进行中

root与独立sub-agent实际核对修订短案2674ed6a，无剩余设计阻断；仍在冻结992范围。
修复须start前保留actual worker、Done后真实join；3.11中断join未知终态交原外层回收。
2名sub-agent并行实施两安全文件和只读完整warm准备；root负责治理、文档和统一提交。
此为方向接受，不是源码、测试或门禁PASS；新草稿须独立源码复核后固定候选。
旧阻断字节与失败证据保留；完整warm/原600/V2/55/发布/F进入条件均保持。

## 2026-10-01 并发复制草稿被独立预审阻断，修复启动归属

未提交的两文件草稿通过静态格式/语法/旧AST核对，但启动后、pool登记前中断可漏等worker。
独立PC-STATIC-001与实际3.11 join证明限制已追加到`parallel-copy-startup-review-diagnostic-017.md`。
旧草稿完整字节和报告保留；新增15函数/预计25cases仍未collect或执行，不是运行通过。
2名sub-agent并行准备局部owned线程修复短案与独立审查，root独占治理/文档/统一提交。
该终态修复属于冻结992既有契约；未知私有协议须复制前serial，不改原4/256和全部门禁。
完整warm D/C草稿与前置脚本尚未绑定/运行；旧600失败、action005/55/发布/F条件不变。

## 2026-10-01 有界复制设计已准入，安全实现进行中

新冻结spec992b927c经真实独立REV-0008/r1 APPROVE，原生spec approval/begin已exit0。
TASK-0056为IMPLEMENTING/REVIEW/V2，scope仍24；旧B589原件保存为spec-design-007.md。
2名sub-agent分别实施仅_copy_snapshot/新增private helpers/EOF tests，及只读独立验证准备。
原65cases和其余旧function/assertion AST保留；治理和安全提交分开。
固定候选完整warm成本、完整模块与原integration600后串行全V2/Review/Gate。
当前未有新性能或门禁PASS，action005与55、发布、F进入条件保持。

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

## 2026-10-01 直接入口候选重新准入

40个只读Git配对调用/2个status守卫实际exit0，配对差值中位13.4795ms；单argv
测量不等于完整入口等价或600秒PASS。四完整模块194passed/exit0，但原始profile
9 entry/49 edge有inline>total，全部函数成本归属unknown。计数/原件保留、资源
交回；完整855诊断和原600失败分开，不以subset替代门禁。

最新spec `b5898529` 已实际重新分类/冻结REVIEW/V2，夹具实施尚未开始；已保留
旧冻结原件和诊断008。并行2名sub-agent负责独立设计审查及两个既有路径的
安全测试准备，root独占治理。当前最小候选只支持现完整mingw64直接入口并
live绑定cmd/core；全部模板/config/attrs/source/env/owner/partial守卫保持。
实际PATH变化需新绑定。准入/begin→安全整合固定commit→完整原模块与600秒
→原生V2/正式审查/Gate→Task55自身准入及Gate→Task57 exact CI/发布串行。
全部原选择器/期限/85%/90%与CI3.11保持，真实F仍未在已搜索范围找到。

## 2026-10-01 完整被动诊断终态

原完整 integration 已收齐实际结果：854 passed / 1 原 FIFO skip / 818.91 秒，
actual exit 0，无诊断外层超时。855 个 ID 逐阶段无缺口，新 53 项全通过；
源码和旧证据未变，资源已交回。阶段数据只定位模块成本，不能证明具体 Git/
资格/校验根因。原 600 秒失败保持，未启动 action005/原生 V2 或下游准入。
随后先测量最小具体候选再决定范围与准入；运行时/入口变化须诚实绑定实际
环境与工具，所有原门禁保持。依据 `integration-passive-diagnostic-007.md`。

## 2026-10-01 元数据兼容前置结果及耗时诊断

Task56 最新 spec `2cefeedd` 的原生重新准入、独立 REV-0006/r1、当前 spec
approval/begin 已完成。source `e3790a4` 的 Windows 创建身份修复及独立安全
单元已固定：19 项 metadata 在 3.11.9/3.13.15/3.14.7 全通过且无 skip，原完整
external-review 模块在 3.13 为 187 passed / 1 既有 FIFO skip / 177.93 秒。
后续原 integration600 于 600188ms 超时，pytest exit unknown、无终态 summary；
不推定未结束用例根因或末尾 53 项通过。源码/旧证据未变，资源已交回。

action005 和完整 V2 尚未启动，正式选择 3.13 的条件尚未满足。先开展原完整
选择器的被动阶段计时，记录真实模块/用例成本；诊断期限独立，不改变原生
600 秒质量门。并行 2 名 sub-agent：独立 verifier 负责计时与证据；另一名
准备未来 Task55 transport 测试及只读成本分析。主 agent 独占账本、说明和
整合；修订准入、实施、固定候选、原预算检查、完整 V2/Review/finalize/批准/
Gate 均串行。Task55 继承实际获 Gate 的 metadata 修复，只新增 transport；
Task57 与 F 保持既有进入条件，三份用户原稿和所有历史证据保持。

## 2026-09-30 固定夹具候选的集成前置结果

固定 subject `097f9af92a4c9bbad35378f34b3d5d48dd143b01` 的完整守卫短测
有二十次实际 warm hit；独立原 integration600 却实际超时 600156ms，pytest
exit unknown、driver 1，源码和旧证据未变。partial 无 summary，不推定末尾
用例根因、skip 身份或最终 53 项全部完成。便携失败报告已追加；未启动新的
完整 V2 或创建 action005，不把前置诊断写成第五轮原生验证。

并行阶段启用 2 名 sub-agent：一名只读核查整套真实 owner 使用和剩余成本，
另一名准备隔离 3.13 比较及实际文件身份探针。主 agent 保留失败、统一状态与
准入；测试和资源密集比较串行。正式运行时仍原 3.11，比较不替代完整质量门。
若选择修订，重新准入→实施→固定候选→原 integration600→fresh action 与
完整 V2→独立 Review/finalize/批准/Gate 串行；后续 TASK-0055/0057 与条件 F
不提前启动。三份用户草稿及全部历史记录保持。

## 2026-09-30 初始仓库夹具修订实施阶段

完整 profile 的成本分析和独立原环境复制短测已完成；局部原创建均值
0.36051 秒、完整独立复制加三目录当前指纹均值 0.05784 秒，actual exit 0。
完整资格成本与原 600 秒预算内完成能力仍待实测；四轮 FAILED 不改变。

实际 native `spec_changed` resolve/classify/freeze、独立 REV-0005/r1
APPROVE、当前 owner spec approval 和 begin 已完成，TASK-0056 为
IMPLEMENTING / REVIEW / V2。冻结规格 SHA
`3a782321645c40b71cf4921a7322872bf45285bf009218edb3e1d4d9310c53ce`，
准入账本 `c99998571a117a5b071c03cc9caa0e47efe8395d`。
旧 frozen e3fc 规格另存 `spec-design-004.md`；旧失败/批准/回执保留。

并行启用 2 名 sub-agent：一名独占三个新 fixture utility/验收文件及旧
builder 薄接入，另一名保持作者独立、准备审查与原环境验证；主 agent
整理文档/账本、复核原断言和统一提交。原第一目标 builder 成功后才可保存
私有初始 snapshot，warm 复用须当前完整输入资格且实体独立；原异常/partial、
真实后续治理、原选择器/MINENV/预算/阈值不变。

串行验收：有效专项→固定候选→完整原 integration 600 秒检查→fresh action005
及全部原生 V2→正式 Review/finalize/代码批准/Gate→TASK-0055 重新准入及 Gate
→TASK-0057 fixed candidate required CI 与已授权推送合并、独立远端核验。
当前未声称实现或验证通过；F 在限定搜索内未找到目标匹配原件，仍不进入。

## 2026-09-30 第四轮失败后的集成测量阶段

第二次私有采集恢复原模块启动路径语义，完整原 802 integration cases 结束为
801 passed / 1 skip，851.34 秒、actual exit 0/no timeout；源码前后相同，
资源已交回。首次 collection 失败保留。函数成本结论→具体方案→准入/实现
仍待推进；此诊断成功不改变原 600 秒正式检查 FAILED 的结论。

run004 完整终态 FAILED13/14；integration 原 600 秒超时是唯一失败。
完整 regression 2707 passed / 1 skip、857.61 秒，coverage 88.9574%、
diff 97%，五项 mutation 均 killed；Native Gate 实际 REJECT，不进行正式
implementation Review/finalize。失败账本提交 fcecddd，源码 subject 3864844
保持；原日志、归档、三份旧回执及新 consumed action004 追加保留。

本阶段并行 2 名 sub-agent：一名独占完整原 integration 私有 profile 与
durations/只读 phase hook，记录真实开始、退出、raw 和资源交回；另一名
只读研究共享初始 fixture 的隔离、当前输入可见性与 Git 语义。主 agent
维护状态文档，不并发额外测试或改变固定源码/refs。私有较长采集窗口用于
获得完整分布，不能称作通过正式 600 秒检查。所有选择器、预算、阈值和
MINENV 保持。测量结论→必要重新准入→修复实现→固定候选→新完整 V2→
Review/finalize/批准/Gate 串行；方案没有实际测量依据前不实施优化。

TASK-0055 原 FAILED/spec/source 未变，依赖与 transport/Windows metadata
方案仅准备；TASK-0057 和真实输入 F 仍按既有条件进入。早先 E4.1 收尾
fe599c3 祖先只在文档分支，未来发布必须保留该线及实际 gated source 的完整关系。

## 2026-09-30 11:21Z 第四轮启动时计划记录

Task56 实际独立设计 Review/spec approval/begin 后，纯解码生产实现与安全
测试分别提交，固定源码 subject `38648440f5a862edd5a7dccfb55a60aae4f6757e`。
相关 unit 为 70 passed；完整原模块 profile 为 187 passed / 1 既有 FIFO skip、
187.05 秒。重复 safe YAML 调用减少、契约与 Git 调用数不变；整体时间为单次
非同时观察，不能据此认定原超时根因或完整 V2 通过。

fresh action004/独立最终准入完成，完整默认 14 项 V2 实际于 11:21:30Z 启动，
run `run-20260930T112131331525Z`。本阶段并行 2 名 sub-agent：未参与实现者
执行独立完整原生验证，另一名只读准备 TASK-0055 依赖和候选边界；主 agent
维护便携状态与统一审查材料。仅一组资源密集测试，source/ref/ledger 冻结。
预算、阈值、原 3.11 和 MINENV 保持。实际完整结果→Review/finalize/批准/Gate
串行，之后 TASK-0055 重新准入与完整 Gate，再 TASK-0057 required CI/发布。
F 匹配原件的输入条件保留；旧失败、规格与回执完整保留。

## 2026-09-30 解析复用准入与报告搜索核定

完整 3.11 模块诊断实际完成（187 passed / 1 既有 FIFO skip，200.15 秒），
测得重复 YAML 解码的累积成本；原两项完整集合超时的根因仍 unknown。
隔离 3.14 完整比较失败，不作为正式运行时或正常执行的加速结果。
TASK-0056 新规格保留原 frozen 快照，扩大最小依赖范围用于有界纯 YAML
解码复用，已原生重新分类/冻结 REVIEW/V2，正在独立设计审查。

本阶段并行 2 名 sub-agent：一名只读评估性能和边界测试，另一名核对准入并
独立设计审查；主 agent 独占生产和测试实施。准入/批准/begin、实现提交、
完整模块对照、fresh action004、完整原生 V2、独立 implementation Review、
finalize/代码批准/Gate 串行。测试每次仍读取当前文件并执行全部验证；原预算、
选择器、环境和门禁不变。不能以微基准替代完整模块或 V2。

按所有者指示完成限定报告搜索；已见真实 dotfiles 错目标报告，未见当前
harness-model F 的匹配原件。旧 UI 观察和同产品 sub-agent receipt 不替代
ZCode 原件；未启动 provider 或 F 导入。该条件保留，已授权离线工作继续。
后续依 TASK-0056 Gate → TASK-0055 重新准入与完整 Gate → TASK-0057
固定候选 required CI、推送合并与独立远端证明。下方历史计划不重写。

## 2026-09-30 第三轮完整 V2 结果与诊断阶段

候选 `4f0288b4afb608412f984fa9078b7b0692fa0e6f` 第三轮原生 V2 结束 FAILED，
12/14 检查通过；regression 与 integration 超时，原 900/600 秒预算保持现值。
完整 coverage 实际 2676 passed / 1 原有 POSIX FIFO skip，合并覆盖率 88.8278%、
diff coverage 95%；unit 1838 passed，acceptance 9 passed。Gate REJECT，
action003 已消费；没有正式 implementation Review 或 finalize。所有旧证据保留。

先串行提交本轮失败账本及便携核定。诊断阶段并行启用 2 名 sub-agent：一名以
完整模块、原断言和 native MINENV 收集私有性能证据，另一名只读核查其方案、
输出和治理边界。主 agent 统一证据与后续决策；资源密集验证不得并发，运行期间
冻结源码与 refs。profiling 属诊断，不形成 V2 PASS；尚未确定超时根因，不能先
按猜测加入缓存或放宽预算。诊断后再冻结具体修正或验证运行时并完成新 preflight、
单次动作及完整 V2。Review/finalize/批准/Gate 串行依赖真实完整结果。

TASK-0056 Gate 后才推进 TASK-0055 的依赖和新增修正重新准入；最终由
TASK-0057 绑定累积候选、required CI 与推送合并。F 输入仍缺，条件阶段不自动
启动。便携结果见源分支 `verification-failure-003.md`，下方历史计划保持原样。

## 2026-09-30 TASK-0056 修正准入与第三轮完整验证计划

第二轮完整 V2 保留 FAILED（10/14 通过）、Gate REJECT；unit 为 1838 passed，
regression、coverage、integration 实际超时，diff coverage 缺少 XML，覆盖率
unknown。action002 已消费。失败与原件见源分支 `verification-failure-002.md`。
独立诊断后，修正规格已完成原生分类、冻结、设计 Review、spec approval 和 begin。
新候选 `4f0288b4afb608412f984fa9078b7b0692fa0e6f` 修复测试侧物理 I/O 与
拥有明确进程归属的 Git 超时清理；初始 Git 超时原因仍 unknown。

保持原断言和 native 环境的四个完整专项分别为 34、81、187、28 项通过，
外部审查另有 1 项原有 POSIX FIFO skip；真实 Windows 继承管道子进程用例通过。
首次外部审查诊断在 93% 被外层诊断期限终止，无完整结论；原始部分日志保留。
后续完整专项的通过不替代完整 V2、覆盖率或 Gate。详见 `verification-retry-002.md`。

本阶段并行启用 2 名 sub-agent：未参与实现者准备并运行原生独立 V2；另一位
未参与实现者只读审查全部实现及保留证据，待完整结果和当前 context 后产正式
implementation Review。主 agent 统一批准绑定、账本和文档；完整测试运行期间
源码及 refs 冻结，不并发执行争用资源的测试。

后续阶段串行依赖为 TASK-0056 Gate → TASK-0055 依赖范围修订、重新准入、
完整 V2 与 Gate → TASK-0057 完整候选审查、发布 Gate、固定 PR head required CI、
推送合并与独立远端核验。每阶段准入和动作绑定串行；独立审查/只读准备阶段
最多启用 2 名 sub-agent，避免相同文件写入冲突。原预算、阈值、Policy 不变。
真实 F 的匹配原件仍未取得；条件阶段与 provider 不因充分授权而自动满足输入条件。

## 2026-09-30 TASK-0056 首轮完整 V2 失败与限定诊断

固定源码 `659f61cb4245112d75b119b103821bb06bae69ce` 的完整原生 V2 已于
`2026-09-30T05:24:13Z` 结束为 FAILED，14 项中 9 项通过、5 项失败，Gate REJECT。
unit 完整结果为 40 failed / 1798 passed；regression、coverage 与 integration
实际超时，diff coverage 缺少 XML，总覆盖率与差异覆盖率仍 unknown。
5 项固定 mutation 全部 killed，action001 已消费，不能复用。

便携失败记录已小步提交，可读取
`git show codex/e4-verification-control:.ai/tasks/TASK-0056/verification-failure-001.md`。
原始证据、24 个非空日志引用与 snapshot 已独立核验；辅助 audit r1 的路径解析错误
保留，r2 明确修正，原生 evidence 未修改。实现 Review、finalize 和发布尚未进行。

本阶段并行启用 2 名 sub-agent：一名用不变的原测试与原 native 进程环境，对照
长、短外部父目录；另一名完成隔离 Python/Git 的锁定依赖与实际工具入口核验。
主 agent 统一失败账本。长路径写入错误和 PowerShell 期限失败目前只是观察聚类，
不作为已证实根因。后续完整重跑须使用 fresh exact-subject action，再串行完成
TASK-0056 Gate、TASK-0055 依赖重新准入及验证、TASK-0057 发布和远端核验。
现有 goal 与推送合并授权继续有效，门禁及历史材料全部保留。

## 2026-09-30 固定候选与验证阶段

TASK-0056 设计复审、spec approval、begin 和分阶段实现提交已完成，固定候选为
`659f61cb4245112d75b119b103821bb06bae69ce`，原生 subject 已同步。
78 项守卫专项、3 项 runner/默认兼容用例及静态检查通过，独立预审没有剩余阻塞。
当前并行启用 2 名 sub-agent：未参与实现者执行完整原生 V2，另一个只读核对
TASK-0055 的依赖恢复顺序；主 agent 负责统一证据和文档。正式实现 Review 由
另一名未参与实现者在完整运行后执行。尚无完整 V2、代码批准或 Gate PASS。
后续依赖保持串行：TASK-0056 Gate → TASK-0055 范围修订与重新准入 → 完整 V2、
独立审查和 Gate → TASK-0057 发布治理及固定 PR head required CI → 推送合并核验。

## 2026-09-30 持续 goal 与并行实施安排

当前接续为 TASK-0056 显式仓库外 pytest 临时目录治理；原生 REVIEW/V2，
修正规格已冻结，独立设计复审进行中。未开始生产实现或形成验证通过结论。
准入及接口固定串行；实施阶段启用 2 名 sub-agent，分别独占目录守卫及其单测、
既有 plan/runner/verify 测试，主 agent 独占生产集成与文档。最终 Review 和
原生独立 verifier 由未参与实现者执行。TASK-0056 实际 Gate 后，串行显式修订
TASK-0055 依赖范围、重新准入、完整 V2；TASK-0057 再处理完整候选的发布和合并。
所有者已授权目标范围内必要批准及推送合并，依实际版本事实记录，不重复询问。
不修改门禁、预算或检查范围，不以临时目录迁移断言原超时原因；旧失败完整保留。

## 2026-09-30 E4.2 第五轮原生 V2 核定与停止点

E4.2 的设计准入和当前实现已在 `codex/e4-report-import` 完成，`TASK-0055`
固定源码 subject 为 `eb4c49a4ff77ca07f210fceae707495c8dece8be`，第五轮验证准入
HEAD 为 `12b8e76e195e6f13772d3d692b80fca06422d31f`。完整原生 V2 已结束为
**FAILED**，14 项必需检查中 9 项通过；下方 D/E 的历史计划不再表示实现尚未开始，
但 E 的完整验证完成条件尚未满足，不能进入发布或真实导入验收。

unit、regression、coverage XML、integration 分别实际超时 300406、900203、
1200328、600172 毫秒，四项均为 `exit_code: null`。diff coverage 因缺少
coverage XML 退出 1；总覆盖率和差异覆盖率为 `unknown`。9 项 acceptance 用例
通过、5 项 targeted mutations 全部 killed，保留各自覆盖边界，不替代完整 V2。
unit 部分日志的两项失败在限定诊断中 2 passed、12.64 秒、退出 0；原失败未复现，
原因仍为 `unknown`，不从该诊断推导正式验证通过。

源码和任务账本保留在既有忽略目录 `.claude/worktrees/e4-verification-disk`。
原始文档检出不含 `TASK-0055` 账本；失败摘要提交后，可从分支便携读取：

```text
git show codex/e4-report-import:.ai/tasks/TASK-0055/verification-failure-005.md
```

接续串行定位失败并完成全部 Policy-required checks，再取得
匹配的独立实现审查与实际 Gate。预算、质量阈值和完整检查范围保持原样。所有者已
明确授权推送、合并，授权仍有效，动作尚未执行；本次失败阻止发布，不重复请求动作
授权或提前请求代码批准。真实报告消费仍依 F 的原件、来源和目标匹配条件办理。

下方较早核定与历史计划全部保留；E4.3/E4.4、provider、I1 其余生命周期、
I2 更多目标、E5、I5 与阶段三/四不自动启动，三份用户草稿和阶段 61 旧 index 保持原样。

本轮随后完成第五次运行的私有证据包和独立字节校验：100 个显式选择文件、
23 组 producer/Git 文本映射，原件与 Git LF 文本分别保存；导出及独立校验均退出 0。
便携记录为 `git show codex/e4-report-import:.ai/tasks/TASK-0055/evidence-handoff-005.md`。
这不恢复源仓库或环境，不赋予新批准，也不改变 FAILED；当前资源观察未支持新的
完整重试，下一依赖仍是失败定位、适当验证环境及全部原定必需检查。

## 2026-09-30 最新核定与后继准入

本轮实际 CLI 确认 `TASK-0048` 为 `MERGED`、`Missing: none`；本次同仓
Windows/Linux 接入、同 SHA 双 lane、main 采用、真实 guest 重启后业务、串行恢复、
正式 V2 与治理关闭均已完成，见[任务 02 执行目录](2026-09-13-runner-infrastructure-execution.md)
和[发布关闭记录](../../../.ai/tasks/TASK-0048/publication-closeout-001.md)。不重复注册、
执行 CI 或关闭该任务；当前 guest/runner 在线状态仍须当次观察，不能沿用历史回执。

E4.1 契约与本地验收已经由 `TASK-0054` 完成，分支为
`codex/e4-external-review-contract@fd560d9`，实现 subject 为 `23793f7`。
本轮恢复该分支检出后实际 `validate` 通过，`status` 为 `APPROVED_FOR_MERGE`、
`Missing: external_merge`，批准为 `current`、证据为 `passed`，`gate` 为 PASS。
下方 A–C 及“工程实施未启动”保留 2026-09-23 的计划时点，不要求重复已完成的工作。

已提交 V1 审核包中的单元 1656 passed、全量回归与覆盖率重跑各 2294 passed、
总覆盖率 88.12% 和可统计差异覆盖率 100% 均为历史结果，本轮没有重跑。
旧忽略目录中的原始日志是否可恢复尚未确认；当前结构与治理核对不等于原始日志
已恢复，也不代表远端 CI、推送或合并已经完成。

接续从下方 D 的 E4.2 独立治理规格与设计准入开始：本轮在
`codex/e4-report-import` 准备 `TASK-0055`，先冻结原件加载、来源/目标匹配、
预检与不可变记录边界，再按当前 CLI 缺项取得准入。E4.1 的发布与合并是独立
工作线，不作为本地后继规格准备的额外前置；推送、合并及新增外部动作另需授权。
I1 其余生命周期、I2 更多目标、E5、I5 与阶段三/四仍按原条件选择；三份未跟踪
用户草稿和阶段 61 的旧 index 保留。本段只校准最新入口，下方历史计划完整保留。

状态：计划已整理，工程实施未启动。接手时以本文件和
[启动前规格](../specs/2026-09-23-zcode-report-import-preflight.md)为入口；
本文件安排顺序、职责和验收，具体契约语义仍由规格维护。

> 2026-09-27 更新：dotfiles `codex/ci-regressions-e4-preflight@3b835f1` 已通过
> [合并提交 `68ef2ec`](https://github.com/MaginaLW/ai-agent-dotfiles/commit/68ef2ecedca3e9071178dcab8b805cecdafbba53)
> 进入 `main`；[`main@6c814f1` 的完整 Validate](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/36303730680)
> 四个 job 均成功。下方 2026-09-23 的分叉基线与 dotfiles 独立集成工作包保留为历史快照，
> 不再重复集成；来源见[外仓整合记录](https://github.com/MaginaLW/ai-agent-dotfiles/blob/6c814f18e981edfa1cad7185915ed7c177857bc0/status/active/live-safety-hardening.md#L4121-L4149)。

## 1. 本次交接基线

2026-09-23 的只读核对如下；执行后续任务时重新取得当时基线。

| 对象 | 已核定事实 | 接手含义 |
| --- | --- | --- |
| harness-model 本地 | 收尾提交 `eda49f7c67d2a424884f0bea833bd0f31fc2a4dd`；tracked clean，三份用户草稿保留未跟踪 | 本计划随后独立提交；不把草稿纳入候选 |
| harness-model 远端 | main `48bf777106b9fdfef1ddf83d3abc95859fb8e580`；原分支 `codex/self-hosted-runner-inventory` 为 `a8bfdf0d00d90371baca287e8310908555dc9d66` | 本地待发布差异还包含 TASK-0053 的既有追加记录，不能按“仅这份计划”判断整个推送范围 |
| dotfiles 修复分支 | `codex/ci-regressions-e4-preflight` 为 `3b835f143616c91fff3249ba7881996ea4876cf7` | [固定 CI](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/35873759132) attempt 1、四个 job 成功、42 套件全部通过 |
| dotfiles main | `48f17e1565b4f6b95a1f904c9ebce2cda6f5484b` | 与修复分支共同祖先为 `627ef3f`，main 侧 7 个提交、修复侧 3 个提交；修复分支尚无 PR |
| E4 | E3 最小真实案例已完成；所有者已选定“将 ZCode 审查报告校验并导入既有 AI Flow 任务” | 下一项为 E4.1；不重做 E3，不把方向选择再次列为缺项 |

[上一阶段收尾记录](../../operations/e4-preflight-closeout-2026-09-23.md)绑定修补及验证事实。
私有证据集合 `E4-CI-REPAIR-20260923` 保留 README、三个 CI 回执及原始日志；
最终 CI 回执 SHA256 为 `c5d967bbe2f8987d6d89245e0ae5ddfdb512483e60f4480a2224c855883eff63`。
本次不覆盖这些回执、旧失败或既有账本。旧 `harness-env` 超时根因仍 unknown。

## 2. 推荐主线：E4.1 → E4.2

优先开始 E4.1 的治理准入。dotfiles 集成和主仓记录发布是独立工作线，不作为
E4.1 契约实现的额外前置。下表的 sub-agent 数均不含主 agent；总并发容量为两名。

| 阶段 | 工作与依赖 | sub-agent 数与职责 | 完成条件 |
| --- | --- | --- | --- |
| A：E4.1 准入 | 串行固定基线、创建独立治理 task、运行实际分类、冻结规格、设计审查，并按 `status` 的 Missing 项推进 begin | 办理步骤 0；设计审查时顺序启用 1 名独立只读 reviewer，主 agent 处理反馈 | CLI 确认实际准入；不预填 task 编号、风险等级或批准结论 |
| B：E4.1 实现 | 依赖 A；先冻结字段，再并行编写契约和安全样例 | 1；独占五份测试/fixture，主 agent 独占两份治理文件 | 独立 `external-review` 契约注册，C1–C4 定向检查通过，旧格式不放宽 |
| C：E4.1 验收 | 依赖 B；固定候选后，主 agent 执行完整必需检查 | 2；分别只读审查契约/来源边界、兼容/测试覆盖；不互写文件 | 完整测试、85% 总覆盖率、90% diff coverage、whitespace、Ruff、format、mypy；正式审查和 Gate 按实际任务要求完成 |
| D：E4.2 设计 | 依赖 E4.1 契约验收；串行冻结目标选择规则、输入契约、导入入口和合成样例，再完成治理准入 | 办理步骤 0；设计审查时顺序启用 1 名独立只读 reviewer | 目标选择/来源映射规则、预检/记录协议及不可变落盘边界可验证 |
| E：E4.2 实现 | 依赖 D 准入；模块接口冻结后并行推进，文件归属在该 task 中列出 | 2；一名负责加载/预检单元，一名负责安全测试；主 agent 负责记录/CLI 集成 | I1–I7 通过，随后完整必需检查和独立审查；旧 Review/approval/evidence/Gate 含义保持 |
| F：真实导入验收 | 依赖 E；使用与目标任务匹配、来源经核定的真实 ZCode 报告 | 1；只读核对原件、绑定和结果；主 agent 串行执行消费动作 | 原件/目标匹配，重复输入 no-op，错误或漂移零写拒绝，真实结果可追溯 |

若主线与独立工作线同时推进，最多保留两名 sub-agent；例如 B 的测试占一名，
另一名可做 dotfiles 只读集成差异审查。C、E 已占满容量，其他工作排队。
发布、合并、任务状态变更和最终集成均由主 agent 按依赖串行执行。

### E4.1 的固定最小分工

- 主 agent：新 `.ai/schemas/external-review.schema.json`，以及
  `src/aiflow/contracts.py` 的一项 registry 登记。
- 测试 sub-agent：`tests/unit/test_contracts.py`、
  `tests/fixtures/contracts/valid/external-review.json`，以及 invalid 目录中的
  `external-review.extra.json`、`external-review.invalid.json`、`external-review.missing.json`。

治理与安全单元分开走对应流程；维护模式允许的安全测试可 task-free，拆分不减少
所需批准。字段未冻结时先准备样例结构，Schema/登记就位后才串行运行集成验证。
设计冻结时确认字段/version、仓库标识的核定映射、各阶段 base/subject 规则、
未完成原因和资源上限。原件受审对象必须与目标 context 分别表达；摘要不认证身份。
E4.1 仅提供契约校验，不宣称现有 `aiflow validate TASK-ID` 已获得导入能力。

### E4.2 的实际输入和停止点

开始 D 时冻结目标选择规则、输入契约和合成样例；到 F 取得真实报告后，重新固定
当时目标 task、仓库、阶段、base/subject/context 摘要，以及原报告版本、原件 SHA
和经核定的 `source_subject`。匹配目标的真实 ZCode 报告属于 F 的验收材料，
**不是 A 的前置缺项**。已有 dotfiles/51044a55 原报告保留为错目标负例；
离线正例标明 synthetic，不修改真实报告来制造匹配。

导入按“零写预检 → 核定完整输入 → 明确记录并重新校验 → 不可变附属记录”实施。
同版本相同完整输入 no-op；同版本内容或映射冲突拒绝；新版本追加。
重复 JSON 键、原始字节上限、漂移和路径边界属于 E4.2 加载/写入层验收。
不执行报告文本，不将 F1/P1/verified 自动提升为正式 Finding、severity 或批准。
只按所选消费动作完成 guided 导入；E4.3/E4.4 另按真实关联或恢复缺口决定范围。

## 3. 独立工作线及优先级

| 顺序 | 工作包 | 分工与验收 | 与 E4 的关系 |
| --- | --- | --- | --- |
| 可与 A/B 并行 | dotfiles 修复集成 | 主 agent 在独立检出核对当时 main 与三个修补的逐项必要性；1 名 sub-agent 只读检查生产改动影响。保留适用断言，处理冲突后固定新候选，运行针对性验证和新候选完整 CI；按现有有效授权及缺项执行发布/PR/合并 | 旧 42/42 不能覆盖合并后的源码；不自动整合原仓工作，不阻塞 E4.1 |
| 需要发布记录时 | harness-model 收尾记录发布 | 先核对远端到完整候选的所有差异，识别既有 TASK-0053 追加记录；按升级清单处理发布 task。1 名 sub-agent 做候选范围/证据核对，主 agent 串行执行验证和已获授权动作 | 不复用旧固定候选的动作批准，不要求为发布记录而实施 E4 |
| 次要诊断 | harness-env 超时可观测性 | 若选定维护工作或自然复发，先保留真实两流/阶段日志并做受控超时复现；0 名 sub-agent，单写入者。以成功捕获诊断为验收，不提高预算来宣称根因解决 | 当前没有已定位的生产缺陷；不重复跑完整 CI 只为制造新样本 |

推送、PR、合并等外部动作在执行时核对当前授权覆盖；已有有效授权直接沿用，
只补实际缺项。本次计划不新增这些动作，也不请求空泛批准。
运行 dotfiles 组合树测试前，先证明 public CLI 夹具的 RepoRoot、身份与默认路径
均指向受控隔离对象；生产路径变化可能改变旧拒绝分支，不能直接在宿主沿用旧前提。
合并后另核对远端状态、提交父子关系和实际 required CI，不能以本地 `close` 替代。

## 4. 保留项与接手清单

E5、扩仓/更多平台、真实 provider、通用可信执行、阶段三/四保持条件路线。
阶段三的样本充分性与隐私/偏差规则、真实 V3 沙箱及回退案例、版本化度量须另行满足；
阶段四还依赖阶段三退出证据与真实协调需求。TASK-0028 选项 C 和历史 BLOCKED
处置保留，不因计划更新自动恢复；不把账本历史数量当作新增待办数量。

下次接手按以下顺序完成一个可验收阶段：

1. 读本计划、启动前规格和维护入口；核对 Git、当前写入者及任务状态。
2. 从 A 开始 E4.1 准入；若选择独立集成工作线，使用独立检出并固定其版本。
3. 按表中职责委派，先确定文件独占范围，再开始写入。
4. 完成该阶段检查、复核与小步提交；报告实际候选、已执行验证和未执行范围。

本次交付仅更新计划和入口：本地阶段提交，链接/历史保全/文件范围检查；
未创建 E4 task、begin、改内核、重跑 CI 或执行远端写入。
