# 任务 02：私有 Linux 执行接入记录

日期：2026-09-13。整体状态：`IN_PROGRESS`。本报告由 `TASK-0048` 记录，范围与
验收以[冻结规格](../../.ai/tasks/TASK-0048/spec.md)及
[任务 02 执行目录](../superpowers/plans/2026-09-13-runner-infrastructure-execution.md)为准。
它记录当次已取得的证据和未完成项，不替代 AI Flow 的验证、批准或 Gate。

2026-09-21 当前入口：见文末 Stage 60D 及“正式治理关闭的当前缺口”。固定
`949fc6036a95e5c1ed55c4d5d5f96793ba42670f` 已完成 pilot 双 lane、main 采用和
main 双平台完整验证；真实 guest 重启后完整 Linux 业务验收通过。Linux 已停用且
独立确认离线、无进程/容器残留，Windows 服务已恢复并完成新的完整 Strict。
当前运维验收通过；正式治理收尾见文末阶段 61 与 TASK-0048 账本，最终结论以
当前 CLI Gate 为准。运维结果见“采用后双平台完成与运行收尾”；下方其他
“最新/当前”及 scope/V2 缺口描述均保留其历史时点含义。

2026-09-21 最新执行结果：见文末“阶段 59：完成交接、当前源码验证与独立接入候选”。
所有者已交接；固定 `39cc7ff` 的完整本地 POSIX 通过，新候选 `949fc60` 的双引擎
root 组件与修复后的回执接口实际通过。本文固定时完整候选 Strict 仍在执行，结果待核，
尚不据本地验证宣称 CI、采用或生命周期验收完成。以下阶段 58 及更早结论均为历史。

2026-09-20 最新执行结果：见文末“阶段 58：恢复实例与固定历史源码完整 POSIX”。
新 WHPX boot 上的原单项及一次未缩减完整 POSIX 已通过，覆盖固定 `cd02cb3c`，
不覆盖目标当前 HEAD 或 CI。下文阶段 55 的退出 124 和阶段 57 的启动记录保留为历史；
本任务仍未完成接入、采用和生命周期验收，不据此补写 implementation_result。

当前结论（09:32 UTC）：完整历史 POSIX 执行已结束，原生退出 `124`，最终结果文件
未生成，不能验收为通过。失败归档、两套 root 组件和执行后源码已实际回读；
收尾采集未发现额外低权限进程、容器、Pod 或待处理 Job。同步持久化 v2 已通过
Linux 154 项测试及启用生产路径检查代码的独立双文件系统 17 项测试，独立修复
核定仍在进行。目标仓保持只读，runner 注册、服务交接、完整 CI 和恢复演练未执行。
下列早期“最新核定”及各时间段记录保留其当时含义，以后续追加结果为准。

最新核定（06:51 UTC）：固定 `cd02cb3c` 的原版 root fixture 已由 v9 adapter 在
真实 Linux 中完成 Dash 与 BusyBox ash 两套执行，均为四个用例通过、退出 0、
无残留且精确清理完成。独立回读核对原五行输出、两份 FD 目标记录、内核证明和
原生命令回执。此结果只覆盖该固定源码的 root fixture；完整 POSIX gate、最终
目标提交、runner 接入与同提交双 lane 仍未完成。下文历史失败和当时待办保留，
后续结果按版本追加。

## 版本和权限

本仓通用工具固定于 `01cadafc1b5fc3c56298c79be61895737eefb6a8` 和
`44bda60199c4344220590aff30522022bf3c1064`。后者的干净检出通过 1,945 项完整测试、
105 项合同检查，总分支覆盖率 88.35%、diff coverage 95.4%，其余原质量检查通过。
该结果属于 I1/I3 软件验证，不构成服务恢复、宿主重启或 Linux 业务验收。

所有者已明确授权完成任务 02。本治理单元将既有单仓可信私有 Linux、低权限隔离、
受控串行交接及回退目标细化成可验证规格；独立设计审查未发现新增业务方向。
规格批准记录如实引用既有用户决定，没有声称用户在本轮重新逐项审核新文件，也不
预先批准最终代码或具体高风险动作。当前 task 已按 CLI 从规格审核进入实现。

目标仓的并行修改已从 `dec409c2` 推进至 `042fad44`；最近只读回读又看到 README、
状态文档和 manifest 的未提交修改。保留该并行工作，不把此 HEAD 当成已执行的
Linux pilot；当前 root fixture
基线仍固定于 `cd02cb3c`。本次保留原工作树，在独立检出中准备后续候选，接入与采用前
仍须重读版本和交接事实。公开托管 CI、生产设备、
计费设置、个人凭据及其他仓库不在本单元改动范围。I5 和既有阶段三/四准入保持原边界。

## 当前证据

下列标识均指向受限的树外原始证据包；公开文档仅保留逻辑引用和必要摘要。

| 证据 | 实际结果 | 仍不证明的事项 |
| --- | --- | --- |
| `i1-full-quality-001` | 固定检出全部原质量检查通过，结束工作树干净 | 已注册服务身份、恢复或重启后的业务 |
| `task0048-stage1-quality-001` | `ac9b8e9` 干净检出通过 1,945 项完整测试、105 项合同检查及全部原质量门；总分支覆盖率 88.35%、diff coverage 95.4% | 本任务全部实现、正式 V2 或 Gate 已完成 |
| `guest-dependency-check-v2-001` | Ubuntu 24.04 的必要依赖、实际低权限用户与 rootless Podman 检查通过 | runner 已注册或 job 已执行 |
| `guest-storage-v2-001`、`guest-storage-v2-repeat-002` | 任务专用存储连续两次 owner、容量、挂载参数和输出摘要相同 | 卸载恢复或重启持久性 |
| `guest-network-v2-001` | 四次指定 IPv4 拒绝对应计数 0→4；公开 HTTPS 探针成功 | IPv6、逐包归因或并发攻击者场景 |
| `guest-provisioning-negative-001` | 14 次真实 shell 受控检查证实修订保留前序失败 | 真实敏感数据已被读取或全面安全认证 |
| `i2-provisioning-verification-002` | 原审查者独立核对 34 项受控检查及实际回执，三项 provisioning 问题修复 | root fixture、重启或完整 CI |
| `guest-fixture-image-build-001`、`guest-fixture-image-inventory-001` | 固定输入镜像构建成功；可信盘点读取解释器、屏障与包清单 | fixture 已运行 |
| `guest-live-candidate-tests-v1-001` | 原候选在真实 Linux 上 81 项测试通过，无跳过 | 原候选不存在设计之外的实现缺陷 |
| `guest-live-preflight-v1-001` | 只读核查 155 个固定源文件和环境输入通过；未创建容器 | 容器内核证明或 payload 执行 |
| `i2-adapter-review-001`、`i2-adapter-fix-001` | 两项缺陷有独立复现和固定版本修复包 | Fixer 自报可以关闭问题 |
| `guest-live-candidate-tests-v2-001` | 修复单元在真实 Linux 上通过回归；完整结果见原始回执 | 独立复核、真实 preauth 或 fixture 已完成 |
| `i2-adapter-verification-002` | 原审查者独立验证两项 v2 修复，保留原 Finding 与失败样本 | 后续真实环境没有新问题 |
| `guest-live-preauth-v2-001`、`i2-live-preauth-diagnosis-001` | 真实启动因 UID/GID 映射错误被拒绝，未发放许可、未运行 fixture；精确实例清理完成 | 初始空 attach 日志能证明程序没有输出 |
| `guest-explicit-map-probe-002` | 可信 sleep 探针实际观察容器 root 映射到低权限 UID/GID 1001，subordinate 映射长度均为正；精确清理完成 | 完整屏障预检、fixture 或业务成功 |
| `i2-adapter-fix-002`、`guest-live-candidate-tests-v3-001` | v3 保留完整内核检查，修订映射参数与启动失败日志留存；真实 Linux 122 项测试通过，无跳过 | 独立修复关闭、真实 preauth 或 fixture 已完成 |
| `i2-adapter-verification-003` | 独立复核 v3 固定包，早退日志 Finding 已验证修复 | 真实环境已通过全部内核检查 |
| `guest-live-preauth-v3-001`、`i2-live-preauth-diagnosis-002` | 内核观察因未覆盖的运行时挂载被拒绝，未发许可；精确清理完成 | 路径相同即可允许外部挂载 |
| `i2-adapter-fix-003`、`i2-adapter-verification-004`、`guest-live-candidate-tests-v4-002` | v4 按实际设备、类型、inode、CID 和容量验证必要挂载；独立复核通过，真实 Linux 163 项测试通过，无跳过 | 模拟的 mount 样本属于真实 v4 内核证明 |
| `guest-live-preauth-v4-001`、`guest-live-preauth-v4-repeat-002` | 两次均在首次 3 秒启动查询超时；未采集内核、未发许可，精确清理完成；attach 完整性保持 unknown | 后续看见容器 running 可以追认预检成功 |
| `i2-startup-diagnosis-001`、`i2-adapter-fix-004`、`guest-live-candidate-tests-v5-001` | v5 在原 20 秒总窗口内分配查询时间并拒绝超期返回；真实 Linux 171 项测试通过，无跳过 | 独立复核、真实 preauth 或 fixture 已完成 |
| `i2-adapter-verification-005`、`guest-live-preauth-v5-001` | v5 启动期限修复经独立复核；真实 preauth 完成内核证明，未发 fixture 许可，精确清理完成 | 原业务 fixture 或完整 POSIX 成功 |
| `guest-root-fixture-v5-dash-001` | Dash 真实执行约 43 秒，三个用例通过、`success_main_entry` 失败；原生退出 1，完整输出与精确清理均有回执 | 三个负例通过能代替正常业务成功 |
| `fixture-output-observer-review-001`、`fixture-output-observer-verification-002` | 观察器的未完成发布和异常日志留存问题经独立验证修复；独立 Linux 15 项、完整绑定受控 12 项及作者 Linux 13 项通过 | 诊断器自身通过就是 fixture 通过 |
| `guest-fixture-output-observer-v2-001`、`i2-live-fixture-diagnosis-002` | 对未改字节的 Dash 再次诊断，保留已删除文件的打开句柄并取得 5,726 字节原输出；26 个失败归为 22 个 AWK、2 个进程计数、2 个 listener 绑定项 | 所有失败已有正式修复；观察器仍标记 `acceptance=false` |
| `guest-posix-tool-diagnosis-v1-001` | 真实无终端环境下 procps `ps w` 退出 1，BusyBox 对应 applet 退出 0；gawk 与 BusyBox awk 接收语法探针 | 替换工具后完整业务已通过 |
| `guest-listener-probe-v2-repeat-002` | 原 listener 函数在同一存活合成服务上完成四个对照：监督进程 dumpable=1 时两 shell 通过，dumpable=0 时均在其 FD 读取失败 | 可以取消监督进程保护或隐藏任意业务进程 |
| `guest-listener-probe-v4-001` | 仅在诊断容器额外 mask `/proc/1/fd` 后，四个单 owner 对照通过，两个其他 PID 独立 listener 对照仍退出 65；精确清理完成 | 新挂载合同、共享 socket/别名与真实屏障检查或正式 fixture 验收已经完成 |
| `guest-image-v2-source-tests-001`、`image-v2-independent-review-001` | 镜像兼容性候选经独立源码复核，真实 Linux 15 项测试通过，1 项 Windows 专属测试跳过 | 镜像构建或构建内 38 项原函数语义用例通过 |
| `guest-image-v2-build-001`、`guest-image-v3-build-001`、`image-v3-log-retention-review-001` | 两次构建均失败；v3 仅修订报告输出并保留原生退出码，经 6 个独立 shell 对照验证；实际报告为输入盘点阶段 `FileNotFoundError`，语义用例集合仍为空 | 已取得可接受的新镜像，或已确证唯一失败原因 |
| `guest-image-procps-files-v1-001`、`guest-image-procps-reconcile-v1-001` | 旧固定镜像的 procps 清单实际包含已缺失的文档/man 文件，存在文件的 MD5 一致；采集包装器在移除实例后出错，另次按原 CID 核实不存在且外部容器列表为空 | 可以跳过任意缺失包文件，或新构建的所有异常均已定位 |
| `image-v4-independent-review-001`、`guest-image-v4-source-tests-001`、`guest-image-v4-build-001` | 固定 v4 输入经独立复核，真实 Linux 45 项测试通过、1 项 Windows 专属测试跳过；保存修改前的实际 procps 文件基线后构建成功，原 38 项语义用例全部通过 | 正式 adapter、两个完整 fixture engine 或 CI 已通过 |
| `guest-image-v4-isolated-semantics-001` | 新不可变镜像在 rootless、只读根、无网络和限定资源的实际实例中再次通过 38 项原函数语义用例；精确实例已停止并清理 | 工具语义测试可以代替原业务 fixture |
| `mask-contract-independent-review-001/002` | `MASK-DIAG-001` 的首异常掩盖后续挂载问题已由完整未过滤诊断检查修复并独立验证；v2 新发现固定脚本目录不一致、二次观测遗漏传播属性，均保留为待验证修复 | 诊断候选已运行；v1/v2 均未执行容器诊断或发放 permit |
| `mask-contract-independent-review-003/004`、`guest-mask-v3-diagnostic-001` | 三项 Findings 已独立验证修复；v3 三个实际阶段完成并清理，最终因 `SecurityOpt` 不展示 mask 的表示差异而拒绝；实际完整挂载比较通过，原失败未改写 | 可以仅依赖 inspect 文字代替内核挂载证明 |
| `guest-mask-v4-source-tests-001`、`guest-mask-v4-diagnostic-001` | v4 真实 Linux 49 项测试通过；81 秒实际诊断完整通过：单 owner 正常、共享和独立 socket 的外来 owner 均被两 shell 拒绝，合成业务 PID 的四类 FD 别名可见；真实屏障无 socket FD，完整诊断内核检查通过后未获 permit，原 60 秒等待超时退出 125；三个精确实例均清理完成 | 正式 adapter 已集成、完整 fixture 或 CI 已通过；诊断始终 `acceptance=false` |
| `adapter-v6-independent-review-001`、`guest-live-candidate-tests-v6-001` | v6 固定源通过独立结构与源码核对；首轮真实 Linux 217 项通过、2 项测试失败，分别为子进程未就绪时 FD 消失、清理进程在存在性与状态读取之间消失；两项测试竞态保留为待验证修复 | 已通过完整 Linux 测试、真实 preauth 或 fixture |
| `guest-v6-independent-native-tests-001` | 固定 v6 运行时代码的三个独立实际低权限对照通过：普通子进程仅取 FD 元数据，持 socket 与 FD 受保护的子进程分别被明确拒绝 | 三个独立对照可以覆盖整套测试或替代真实屏障证明 |
| `adapter-v7-independent-review-001`、`guest-live-candidate-tests-v7-001` | v7 仅修正两处测试同步；独立确认全部运行时代码与 v6 同字节，真实 Linux 全部 219 项通过、无跳过，两项测试 Finding 验证修复 | 真实 preauth 或完整 fixture 已通过 |
| `guest-live-preauth-v7-001`、`guest-preauth-v7-readback-001/002` | 新固定镜像和 v7 源的真实低权限 preauth 通过；完整内核、空只读精确 mask、监督进程双 FD 样本均验证，未发 permit 且精确清理完成；首版回读误依赖已被清理的 cidfile，修订按原 create 回执与内核 CID 交叉核实后完成独立回读 | 无许可预检能代替两个业务 fixture 或 CI |
| `guest-root-fixture-v7-dash-001` | Dash 入口在发放 permit 前因两次 FD 证明不一致而拒绝，业务未启动；attach 退出 125，精确实例清理完成 | 业务 fixture 已运行，或可以移除跨观察的一致性检查 |
| `supervisor-fd-diagnosis-review-001/002`、`guest-supervisor-fd-diagnosis-v1-001`、`guest-supervisor-fd-diagnosis-v2-001` | 两版无许可观察器分别通过 11 和 30 项独立受控检查；实际 preauth 与原 `run_engine` 路径均取得两份相同 FD 观察并完成精确清理，v2 在许可调用前被固定诊断拦截 | 已重现原 FD 差异、确证其原因或运行业务 fixture |
| `supervisor-fd-inode-semantics-001`、`root-fixture-fd-target-design-v1` | 固定 Linux 内核源码复核指出 proc FD 链接 inode 不是跨重建的实际目标身份；已冻结保留链接和目标元数据引用的 v8 设计，通用挂载检查与原拒绝边界保持不变 | 设计已经实现、原拒绝由 inode 重建引起或真实目标证明已通过 |
| `i2-runner-storage-verification-002`、`guest-runner-storage-v2-001`、`guest-runner-storage-v2-repeat-002` | 独立复核及 29 项真实 shell 受控检查通过；专用 16 GiB runner 盘两次实际容量、owner 和挂载回读一致 | 重启持久性或 runner 已接单 |
| `guest-lifecycle-tests-v2-001`、`guest-runner-install-only-v2-001`、`guest-runner-install-repeat-v2-002` | Linux 77 项测试通过；官方包完成安装，重复调用仅检查，文件匹配且本地未注册，无 Listener/Worker | 官方程序启动、注册、服务或远端身份验证 |
| `i1-lifecycle-registration-review-001` | 固定注册 launcher 独立审查无 Finding，38 项受控检查通过，绑定 Linux 77 项结果 | 真凭据输入、实际注册或所有日志路径的保密性 |
| `guest-runner-token-free-v1-001`、`guest-low-uid-process-observer-v1-001` | 启动前进程可见性检查拒绝；root 与降权对照确认 user systemd / sd-pam 的 exe 对低权限 UID 不可读 | 注册预检通过；此项仍需实际静默窗口 |
| `guest-runner-token-free-v2-001` | root 只读确认无 Runner 进程后，低权限账号检查库依赖并实际运行官方 `--version`，退出 0 且精确返回 2.337.0 | 注册预检或日志脱敏；生产 launcher 的可见性拒绝保持不变 |
| `guest-canary-candidate-tests-v1-001`、`canary-independent-review-001` | canary 候选真实 Linux 53 项测试无跳过，独立受控 27 项通过；固定源审查无 Finding | 官方 configure 合成路径已执行或真实 token 安全已证明 |
| `runner-quiet-window-candidate/source-v1` | 专用账号停启与恢复协议、纯观测校验器及 64 项合成测试已准备 | 输入布尔值是内核事实；root 采集、实际停启或恢复已执行 |
| `guest-quiet-window-inventory-v2-001` | root 只读实查四个账号基础进程及 user manager、运行时目录、默认 socket/timer 激活源；初版输出格式解析失败记录保留 | 默认激活源已获执行认可、账号静默或恢复窗口已经建立 |
| `quiet-collector-independent-review-001`、`guest-quiet-collector-v1-source-tests-001`、`guest-quiet-collector-v1-collect-001` | 真实采集器独立 16 项受控检查和 Linux 63 项测试通过；实采在第 41 条只读查询因 timer 多条同名数组属性而拒绝，之前的原生命令回执完整保留 | 单元测试通过即可证明实际采集完整，或账号已停启 |
| `guest-user-bus-array-diagnosis-v1-001` | 固定只读 D-Bus 属性查询确认 timer 两条单调计时项、空日历数组及 dbus socket 地址；禁用自动激活与交互授权的确切 Properties.Get 对照也返回明确空数组 | 已修改定时器、允许任意 D-Bus 方法或完成静默窗口 |
| `quiet-collector-independent-review-002`、`guest-quiet-collector-v2-source-tests-001`、`guest-quiet-collector-v2-collect-001` | v2 数组修订经独立复核，真实 Linux 103 项测试通过；实采越过原 timer 失败点，在第 50 条查询因 Podman 单元的规范路径未被包数据库识别而拒绝 | 实采完整、默认激活源已获认可或账号已经静默 |
| `guest-unit-package-alias-diagnosis-v1-001` | 只读实查确认该单元的两个路径具有相同设备、inode 和摘要；包数据库仅记录经 root 所有目录别名到达的路径，原规范路径查询失败被保留 | 可以忽略未知归属，或目录别名修订已实现并通过实采 |
| `quiet-collector-independent-review-003`、`guest-quiet-collector-v3-source-tests-001`、`guest-quiet-collector-v3-collect-001` | v3 独立 17 项受控检查和 Linux 157 项测试通过；实采成功核对两个 Podman 单元的目录别名与包内容，在第 57 条查询因未实例化模板不接受运行属性查询而拒绝 | 模板可当作已停止实例、省略其来源盘点，或完整采集已通过 |
| `guest-unit-template-diagnosis-v1-001`、`guest-unit-template-source-diagnosis-v1-001`、`guest-unit-path-alias-parents-v1-001` | 只读实查取得模板定义、所有查找目录及适用 drop-in 目录的存在性、精确目录别名和包数据库内容；实际未加载该模板的实例 | 可以实例化模板或修改默认激活配置 |
| `quiet-collector-independent-review-004`、`guest-quiet-collector-v4-source-tests-001`、`guest-quiet-collector-v4-collect-001` | v4 独立 17 项受控检查和 Linux 191 项测试通过；实采完成用户单元、模板和来源盘点后，第 89 条查询返回 291 行系统单元、33,567 字节，因原 256 行表格上限拒绝；该命令退出 0，输出完整 | 全部实采已通过，或可以截断系统单元清单 |
| `root-quiet-controller-design-review-001`、`root-quiet-controller-design-verification-002` | 控制器第二版设计的三项原 Finding 经独立复核修复；另发现恢复执行器归属、服务实际启动时限绑定和审查摘要引用三项问题，均保留待修订 | 控制器已实现、服务已停启或 canary 已执行 |
| `posix-adoption-candidate/source-v1` | 完整树外 workflow 与 manifest 候选冻结，原 Windows 字节和 POSIX 检查集合保留；路径与最终提交尚未绑定 | 目标仓已采用、真实完整 POSIX 或采用后 CI |
| `guest-posix-candidate-native-v1-001`、`guest-posix-candidate-native-v2-001` | 原 v1 完整 lint 揭示 shell 函数调用诊断；v2 最小修复后真实 Linux 40 项及完整 actionlint 通过，原失败保留 | 后发现的 Git 回调问题已由 v2 修复 |
| `posix-candidate-review-001`、`posix-candidate-verification-002`、`guest-posix-candidate-native-v3-001` | v3 以不触发转换的固定 Git plumbing 与实际文件检查替代 status；独立复现并验证 fsmonitor/clean 回调修复，真实 Linux 78 项和完整 lint 通过；Windows、原检查集合及时限未变 | 最终提交已绑定、目标仓已采用或完整 CI 已运行 |

镜像、源码归档、逐文件 manifest、解释器、运行时、seccomp 与配置各自有独立摘要。
源、运行结果和模拟结果分开保管。镜像只读根、限定 tmpfs、专用存储、实际低权限映射、
私有 namespace、cgroup 与可信屏障必须在每次放行前核实，不能用配置文字或 inspect
自报替代内核事实。原业务 fixture 的 600 秒期限和精确结果契约保持不变。

## 修复与接续

`I2-ADAPTER-001` 指出伪文件系统不能只按目的路径允许写入；原实现会接受置于
特定伪文件系统路径的外部可写绑定。`I2-ADAPTER-002` 指出启动轮询耗尽原命令预算后，
同一预算会阻止清理。v2 增加真实文件系统语义与 backing 检查、单独受限清理预算及
启动查询上限。原审查者已针对 v2 固定字节独立复核两项修复，原 Finding 和失败记录
保持不变。

真实 v2 preauth 在可信屏障启动前失败：运行时生成包含零长度段的 UID/GID 映射。
同时发现 `I2-PREAUTH-003`：早退 attach 的待读日志未被完整保留，因此原始 attach
退出状态保持 unknown。v3 根据实际可信映射探针采用四个显式非零映射，并在两个
入口使用有界 drain，分别记录实际 attach 退出、日志完整性和精确实例清理；其余
内核验证函数保持不变。原审查者已完成 v3 固定包独立复核，真实 preauth 随后发现
运行时挂载的语义覆盖缺口；该失败与后续修订分别留存。

v4 针对实际出现的标准字符设备、只读 per-CID 元数据和新建只读空目录 mask，核对
对象类型、宿主对应对象、inode/device、挂载参数及容量；不按目的路径直接放行。
`tmpfs size=0` 不作为零容量证明。v4 独立复核通过，但真实预检两次在启动查询的
3 秒局部期限失败，其中一次低负载复测也重现；底层启动延迟原因尚未确定。
v5 保持原 20 秒总期限与十次查询上限，增加查询返回后的期限检查，fixture 的
600 秒期限及独立清理预算不变。上述启动阶段拒绝均未执行 fixture，与后续业务失败分开留存。

v5 的真实 preauth 随后通过；原 Dash fixture 两次真实运行仍失败。只读观察器在完整
nonce、PID/start tick、证明摘要与清理回执匹配后，从已打开的 `success.out` 取得原因。
镜像中 mawk 的语法兼容性和 procps 无终端行为需独立修复；另一个最小真实对照确认
受保护的监督进程 FD 会触发原 listener 函数拒绝。精确 PID 1 FD mask 目前只在诊断
容器试验，正式 v5 合同仍会拒绝该新增挂载。新镜像与挂载合同须保持原保护和源检查，
补齐真实语义、别名、其他 PID 及宿主观察证明后独立复核，才能再次运行正式 fixture。

新镜像构建在输入盘点阶段失败，尚未运行任何构建内语义用例。追加的报告输出修订
保留原失败退出码；旧固定镜像实查提示包数据库清单与已安装文档集合不同。后续须
在修改 `ps` 前保存实际文件存在性、类型和摘要，修改后只接受明确的 `ps` 迁移，
其余文件与该基线一致；不能把任意缺失文件直接忽略。诊断 mask 候选则须同时核对
固定脚本目录、完整挂载观测及传播属性，再取得独立复核与真实 Linux 结果。

随后 v4 镜像完成上述基线盘点修订并构建成功，镜像标识为
`sha256:f8f0a31e6de0d65b0ed44b534071c4b1f889e5a71d1600fa8464628533f5b10a`。
构建内与独立隔离实例各自通过全部 38 项原函数语义用例，原业务源、可信屏障和
fixture 结果契约保持不变。mask v4 也取得完整真实诊断结果；两者仍须集成至新的
正式 adapter，完成独立复核、真实 preauth 和两个完整业务 fixture，不能追认早期失败。

正式 adapter v7 随后完成全套 Linux 验证及真实 preauth；首次 Dash 入口在 permit 前
因 `supervisor_fds_changed_before_permit` 拒绝。当前只保留了第一份完整证明，尚不能
判定具体差异字段；下一步用无许可诊断保留原两次观测，再按证据处理，原比较保持不变。

POSIX 候选独立审查发现 `POSIX-BIND-001`：只读意图的 `git status` 仍可触发仓库配置的
fsmonitor 或 clean filter。v3 拒绝外部 include、promisor/partial clone、替代对象库等
输入，读取固定索引与树并核对真实文件，不运行 status 或内容转换；原审查者已验证
修复。该版本仍是以历史基线准备的树外候选，不能把回调修复视为新目标提交的采用。

runner 官方包安装在独立有界卷，尚未配置或接单。注册 launcher 的静态独立审查不
替代实际预检：当前低权限进程可见性检查会拒绝 user manager 的不可读身份。后续
须在精确维护窗口核对并恢复账号管理服务，保留原拒绝条件；合成 canary 的官方
二进制失败路径、日志脱敏正对照与实际注册分别验收，不向真实安装输入假 token。

新增 preauth 探针只运行可信屏障，先保存实际内核观察，再验证并清理精确实例；
它不发放 fixture 执行许可。即使探针成功，也仅能记录启动前证明和清理结果。
真实观察与预期不符时保留拒绝证据，不能为继续执行删除或放宽安全检查。

当前未取得两个真实 fixture engine、完整 POSIX gate、Linux runner 注册/服务恢复、
执行宿主重启后的业务、正式 pilot、同提交双 lane 或采用后 CI 的完整成功证据。
下一步完成工具兼容性和监督进程 FD 隔离修复的真实验证与独立复核，重新取得两个
原 fixture engine 及完整验证结果，再按当次身份、
版本和空闲交接事实办理目标仓接入。没有满足这些条件时，任务整体保持未完成。

后续两次无许可 FD 诊断均未重现原不一致；第二版调用原 `run_engine` 并在任何
`exec` 进入底层前拒绝，因此取得第二份观察仍不构成业务执行。原失败缺失的第二份
记录不能用后来的相同样本补写。v8 将 proc 链接元数据与实际目标对象身份分开，
仍须完成实现、独立审查、低权限真实目标观察及两个原 fixture engine 的验证。

静默窗口采集器已越过数组、目录别名和未实例化模板三个实际失败点，当前系统表
容量不足另行修订；原完整命令回执与每次失败均保留。控制器仍处于设计修订阶段，
尚未停止账号管理服务、改变默认激活配置或执行官方 configure 合成 canary。

## FD 目标验证与真实双引擎结果

v8 实现保留受限 proc 链接和实际目标的 `O_PATH` 引用，将可重建的 proc 链接 inode
与目标对象身份分开比较。通用挂载检查、socket 和权限拒绝、原屏障保护及 600 秒
fixture 期限均保留。独立源码复核绑定完整归档；首轮 Linux 为 304 项通过、1 项
测试失败：受保护进程在枚举 FD 时已拒绝，测试却要求后续 open 必须发生。原失败
保留。另一个独立低权限真实对照证明，没有内容读取权限的目标仍能被观察器仅按
元数据核对，且全部引用释放。

v9 只修正上述测试假设并增加枚举先拒绝的反例。独立复核确认 v8 的全部运行时
字节及 305 个测试标识保留；真实 Linux 306 项全部通过，无跳过。随后真实
preauth 完成原内核检查与两份 FD 目标比较，未发放许可，精确实例已清理。

| 证据 | 实际结果 | 验收范围 |
| --- | --- | --- |
| `adapter-v8-independent-review-001`、`guest-live-candidate-tests-v8-001` | 固定 v8 实现经源码复核；Linux 304 PASS、1 个测试假设失败 | 不追认失败为全套通过 |
| `guest-v8-independent-native-test-001` | 内容读取被拒绝的实际低权限目标通过元数据观察及引用释放检查 | 独立单项运行时对照 |
| `adapter-v9-independent-review-002`、`guest-live-candidate-tests-v9-001` | 只变测试；全部 306 项 Linux 测试通过，无跳过 | 固定候选的完整专项测试 |
| `guest-live-preauth-v9-001`、`guest-preauth-v9-readback-001` | 原内核检查、两份完整 FD 目标记录和精确清理均通过，未发 permit | 无许可预检 |
| `guest-root-fixture-v9-dash-001` | 原 Dash 四个用例全部通过，44.347 秒，退出 0，无残留，精确清理完成 | 固定 `cd02cb3c` 的 Dash root fixture |
| `guest-root-fixture-v9-busybox-001` | 原 BusyBox ash 四个用例全部通过，44.366 秒，退出 0，无残留，精确清理完成 | 同一固定源码的 BusyBox ash root fixture |
| `guest-fixture-v9-readback-001` | 两次不同 nonce 的完整证明、两份 FD 记录、原五行输出、命令流摘要和清理回执经独立回读一致 | 两套真实执行证据完整；`full_posix_gate=false` |

v7 原拒绝的具体差异原因仍为 unknown；后来的目标身份修订和成功结果不能补写
原先缺失的第二份记录。两套 fixture 也不能重标为目标仓后续提交或采用后 CI。

## 静默窗口后续盘点

采集器 v5 仅为系统单元表设置固定 512 行上限，其余输出、时间与用户单元上限
不变；Linux 212 项通过。实际采集随后因 transient 目录时间戳变化拒绝。受控
只读诊断确认，原 Podman 空列表查询会改变该目录时间戳，目录条目和摘要保持
一致。v6 将这两项原查询移至第一次激活源盘点之前，保留完整目录元数据一致性
比较；独立 28 项检查及真实 Linux 228 项通过。

`guest-quiet-collector-v6-collect-001` 首次完成全部只读采集。独立回读绑定原
428,507 字节记录和 165 条完整原生命令回执，两次激活源盘点与进程身份对一致。
结果仍为 `COLLECTED_FOR_REVIEW`：pause 的精确命令行规则尚不匹配实际表示，
默认激活源也仍待内容审查，不能进入静默窗口。固定 Podman 4.9.3 源码及一次
只读现场对照确认 pause 的进程名与单参数 argv 表示不同；其他可执行文件、
进程名、namespace 和 pidfile 绑定均保留，后续修订不得以宽泛前缀匹配替代。

控制器 revision003 的剩余三项设计 Finding 已由原审查者关闭，31 项来源和
独立算术检查完成。新的纯校验核心 v1 作者测试 131 项通过，尚待独立实现审查；
它只检查输入事件和双时钟预算，不认证输入来源，也没有服务、进程或许可执行
能力。真实 guardian、持久化、Job 生命周期、无 canary 恢复演练及原版 canary
仍待实现和验证。未停止用户管理服务、修改默认激活配置或注册 Linux runner。

## 后续核定（07:18 UTC）

`d72c82f` 的独立干净检出完成全部原质量门：1,945 项完整测试、105 项合同检查，
总分支覆盖率 88.35%、diff coverage 95.4%，锁文件、whitespace、Ruff、format、
mypy 均通过，结束时工作树干净。该结果及逐命令回执保存在
`task0048-stage7-quality-001`，不扩展真实业务或接入验收范围。

采集器 v7 仅修正 pause 的完整 argv 匹配，原采集和进程收束代码保持不变。
36 项独立检查、261 项真实 Linux 测试全部通过。新的完整只读采集及独立回读
确认四类进程身份检查均通过，两次盘点一致；剩余缺项是默认启动源审查、真实
窗口和恢复实现、当次采集交接及独立注册预检。

| 新增证据 | 实际结果 | 当前边界 |
| --- | --- | --- |
| `guest-quiet-collector-v7-collect-001`、`guest-quiet-collector-v7-readback-001` | 428,476 字节完整记录和全部命令流摘要通过回读，pause 命令身份已匹配 | 仍为 `COLLECTED_FOR_REVIEW` |
| `quiet-activation-baseline-review-001`、`guest-activation-supplement-v1-001`、`guest-activation-supplement-v1-readback-001` | 完整 56 条 unit 盘点后补齐 11 个固定只读查询、13 处端点元数据和 28 份包单元声明 | 9 个活动 socket 和 timer 均保留；未执行恢复 |
| `guest-generated-activation-sources-v1-001`、`guest-generated-activation-compare-v2-001` | 两个生成单元的 root 包 desktop 来源、生成器身份与完整已知声明一致；原字符串直接比较失败及后续格式核对分开留存 | 未执行生成器、autostart 或默认单元；待独立基线复核 |
| `guest-bus-dependencies-v1-001` | 核对 libsystemd、解释器和固定测试 payload 的 root 文件身份；两个 private socket 的实际 peer 分别匹配系统和用户 manager | 仅连接并读取 peer 凭据后关闭，未发送 bus 方法 |
| `quiet-controller-core-independent-review-001`、`quiet-controller-core-independent-verification-002` | v1 的最终恢复正断言缺失与 JSON 指数溢出两项 Finding 均由 v2 最小修复；原审查者 65 项独立探针和 163 项原套件通过，无跳过 | 纯结构检查通过，不是实际 guardian 或恢复成功 |
| `cd02-git-input-002`、`guest-cd02-git-resume-v3-001` | 真实历史 commit/tree 和浅快照完整性通过；独立 Linux checkout 的 155 文件逐字节匹配已有不可变源 | 仅供后续完整本地 POSIX 检查，未运行 gate、未修改目标仓 |

历史 Git 输入准备曾因旧浅 clone 缺少对象、原生采集器预算不匹配和低权限读取
root-owned bare 仓的所有权检查而失败。修订使用精确旧提交、原 30 秒命令上限，
由 root 仅拷入新 checkout 后核对并交给专用低权限账号；未修改全局 Git 信任设置。
原失败保留，真实 fixture 结果也没有被重复用作这次完整 POSIX 检查的执行结果。

## 后续核定（07:55 UTC）

默认激活基线的独立复核完成，14 组检查覆盖完整 56 条 unit、165 加 11 条原生
命令、9 个活动 socket、1 个 timer 与已知生成来源，无新增 Finding。包查询中
原有的非零结果及对应目录别名证据均保留；该结论只审定历史盘点，不表示恢复
实现、guardian 或静默窗口已经可用。

private-bus 诊断 v1 的独立审查发现 QBUS-001：失败 Job 的最终观察失效时，状态
保持 UNKNOWN，但暂存值会将原始 Job 结果误写为 done。v2 的单函数修复经 36 项
独立检查确认，原失败回执不改。固定 v2 在 Linux 上 149 项测试全部通过，无跳过；
实际 root 与 UID 1001 只读连接、短期 peer 绑定及固定属性查询均成功。

| 真实诊断 | 原始结果 | 独立回读与限制 |
| --- | --- | --- |
| `guest-bus-v2-selftest-active-001` | 新 nonce 的 start Job done、服务 running；stop Job done，随后单元卸载 | 原生退出 0，精确 cgroup absent；只验证专用 sleep 测试服务 |
| `guest-bus-v2-selftest-exec-fails-001` | 启动 Job done，服务以 exit-code/1/1 失败；stop Job done，但单元保留 failed | 原生退出 1；进程为 0、Job 为 0、cgroup absent，原诊断未接受为清理完成 |
| `guest-bus-v2-selftest-job-timeout-001` | 原 create 保持 UNKNOWN，后续 JobRemoved 为 failed，Service.Result 为 timeout | 原生退出 1；stop Job done 后仍保留 failed 单元，进程与 cgroup 已清空 |

`guest-bus-v2-selftest-readback-v1-001` 绑定三次完整原始流、原生退出及实际终态。
Job 结果、服务结果、资源清理和保留的失败单元是不同事实；后续候选须分别记录，
不能将旧 UNKNOWN 或失败执行改标通过。未发送既有服务修改、ResetFailed、取消
Job 或注册方法。生产连接、guardian 和恢复演练仍未实现。

历史 `cd02cb3c` 的完整本地 POSIX 候选已冻结：保留原 gate 的全部检查及期限，
主机 127 项通过、8 项 Linux 专属测试待运行；原 gate 的六处变换可逐字节撤回。
专用传输包装已独立复核，完整本地 gate、实际启动脚本审查及 Linux 验证仍待完成。
证据卷的只读盘点确认约 52.6 MB 可用，无扩容；盘点包装首轮 JSON 序列化失败
和修正后的真实结果分别留存。目标仓保持只读，尚未选择最终 CI 提交或接入。

## POSIX 原生准备核定（08:08 UTC）

历史 POSIX v1 的独立审查完成：52 项独立检查通过，40 文件归档与 8 文件运行时
清单一致，原 gate 与预装工具步骤的逐字节保留得到确认。随后真实 Linux 135 项
全部通过，无跳过，五个 Bash 文件的语法检查通过。

实际 `--prepare-contract` 在工具读取阶段以 `file_bound` 拒绝，未安装合同、
未启动完整 gate。只读定位确认固定 root-owned ShellCheck 为 19,420,144 字节，
超过复用的默认 16 MiB 源文件读取上限；单硬链接、祖先权限与实际完整摘要均经
独立核对。QPOSIX-001 要求只修正该固定工具角色的读取边界，源码、配置、回执
和 adapter 的原限制保持不变。v1 及本次拒绝记录保留，修订尚待独立复验。

服务诊断的 QBUS-002、QBUS-003 分别记录保留 failed 单元的清理判定，以及
JobRemoved failed 与 Service timeout 的区别。修订只可对固定的两个负例分别
记录资源清理和失败单元保留，原 JobTracker 终态与原始执行不得改写。三次服务
诊断及合同失败的完整原始流已精确归档并回读摘要，后续成功必须来自新的执行。

## 修复原生复验（08:28 UTC）

private-bus v3 的独立复核以原始 v2 记录验证两个负例的精确条件，38 项检查通过；
bus、身份与 JobTracker 实现保持不变。真实 Linux 227 项测试通过，无跳过。
三个新 nonce 的实际诊断均退出 0，随后 root 独立回读完整流、原生退出、服务属性
和精确 cgroup；原有 v2 失败记录未改。

| 新诊断 | 保留的原始观察 | 新执行的独立回读 |
| --- | --- | --- |
| `guest-bus-v3-selftest-active-001` | create DONE、stop DONE_ABSENT | 单元 not-found，MainPID 为 0，cgroup absent |
| `guest-bus-v3-selftest-exec-fails-001` | create FAILED、stop FAILED；两个 Job 的结果均为 done | exit-code/1/1 的 failed 单元保留，Job 和进程清空，cgroup absent |
| `guest-bus-v3-selftest-job-timeout-001` | create UNKNOWN、stop FAILED；后续启动 Job 为 failed，服务结果为 timeout | timeout/2/15 的 failed 单元保留，Job 和进程清空，cgroup absent |

QBUS-002、QBUS-003 的修复已由新的真实执行验证。负例的诊断通过表示观察与资源
清理符合预期，并未将失败 Job 或 UNKNOWN 改成成功；没有 ResetFailed、既有服务
操作或许可发放。生产 guardian、静默窗口及恢复演练仍待实施。

历史 POSIX v2 仅为固定 ShellCheck 角色设置 19,420,144 字节读取上限，其余默认
16 MiB 读取器与原 gate 检查、时限均保持不变。36 项独立检查和 Linux 163 项测试
全部通过。`guest-local-posix-v2-contract-001` 实际完成工具摘要核验与合同准备，
合同摘要为 `b089fcafb5e00d18530bff901bd0e3ab0f1c684b5b56dbadf41cb3abd9ed8c65`；
低权限 `guest-local-posix-v2-source-check-001` 随后验证固定历史源码成功。
QPOSIX-001 的修复由上述新执行验证；完整 gate 尚未执行。

上述新诊断和 POSIX 准备的 31 份完整原始文件已精确归档、传回并逐项复核：
`stage9-native-diagnostics-002.tar` 为 399,360 字节，摘要
`c96f6f14593143fe0d052aad40a0dce931ad5c7f51ffe2d7eff2535f45ba65da`。
独立结论保存在 `stage9-native-verification-001`。目标仓继续只读，未注册 runner。

## 后续候选与执行边界（08:53 UTC）

完整历史 POSIX 启动脚本已绑定上述实际合同及八个运行时文件，独立 15 项检查
通过；长传输包装只变更运行编号与脚本路径，原 gate 与全部期限不变。
`guest-local-posix-v2-run-001` 已实际启动，完整终态及回读尚未核定。最终验收
清单、14 个有序输出标记和回读脚本的 27 项独立检查保存在
`local-posix-run-acceptance-001`。

原候选 README 对九项 Windows 用例的措辞不准确：原 gate 按冻结 manifest 的
`platform=windows` 排除它们，不输出九条 `BEHAVIOR_SKIP`，也不把它们计为 Linux
通过。实际行为跳过按原始日志逐项保留；不得由平台排除数量补造日志或验收结果。
启动包首份格式检查误记已由追加的 `delivery-v2.json` 更正，受审运行文件字节
保持不变，原误记和失败 JUnit 均保留。

持久化设计 v1 的独立审查发现 QPERSIST-DESIGN-001：已确认 guardian 死亡但旧
文件 writer 卡住时，接口会连同有效 capsule 的恢复读取一起拒绝。设计 v2 将
接管恢复与新建主卷 writer 分开；只有已独立绑定为纯文件 I/O 的旧 writer 才可
使用此分支，且不读取卡住的主卷，主卷写入、新窗口和主动动作仍禁止。命令或
服务 helper、Job、operations 的原恢复检查保持不变。

原审查者已独立核对 22 项来源摘要、五文件归档和全部可逆修改，将该 Finding
核定为设计层修复。同步存储模块尚在实施；异步接线、真实 guardian、静默窗口
和恢复演练仍未完成，没有真实 lease、服务操作或 runner 注册。

## 完整历史运行失败与收尾（09:32 UTC）

`guest-local-posix-v2-run-001` 从 08:32:53 至 09:06:37 UTC 运行 2,024.281 秒，
实际退出 `124`；宿主传输没有超时。步骤 02、03、04 为原生退出 0，步骤 05 为
原生退出 124，`result.json` 不存在，完整 PowerShell 与最终成功标记均不存在。
原 gate 的检查、fixture 600 秒上限及总预算保持不变。本轮没有重复运行完整 gate。

失败归档独立于成功验收路径：`guest-local-posix-v2-failure-readback-002` 重新核对
当次两套新 nonce 的 root 组件、四用例五行输出、内核与 FD 证明、精确清理回执，
以及 Python 两文件共 27 项实际通过、无跳过。它同时明确要求原步骤 05 为 124、
最终结果文件缺失，不能产生完整 PASS。归档 `local-posix-v2-failed-002.tar` 为
378,880 字节，摘要 `e8f47237dc7d9d84cd403fba72737709a939636c87038f2630ad959ddeb7af1f`。
`local-posix-failed-independent-verification-001` 随后独立复核全部 112 个归档文件、
原 receipt 校验器及四个拒绝反例、当次各子结果和执行后完整采集；结论仍为完整
gate 失败。核定记录摘要为
`22cfbc6fe2951eff2c946b0b27ef318e96f7609fe8aeaa680714335a465c0f87`。

首次失败归档的 source-after 调用漏传本次运行目录，原检查程序实际报 `KeyError`。
首次诊断又因读取了错误的流文件后缀而失败；两份失败回执保留。新版本仅补齐
固定运行目录参数并使用新输出编号，原源码、合同与验收断言不变。修订后的
低权限源码及运行目录检查原生退出 0，两个流完整读至 EOF、子进程已回收。
该结果不把之前的包装失败改成成功。未执行的旧成功回读脚本也有此调用缺项；
其标记清单另漏列两条合法 root 组件输出，后续使用前必须另作版本修正和独立复核。

原始组合日志可确认五个 portable PowerShell fixture 的成功标记，后续三个尚未
完成。`secret-scan-fixture` 的原输出另明确标记 Git-index/reparse 子项为 POSIX
排除、`non_git_rg_ignore=dependency-missing`；这些实际限制与九项 Windows 平台
排除分别保留，不能统一宣称所有行为无跳过。只读临时目录盘点发现 current-state
fixture 的 55 个直接成员；从首项到最后一个新生成的无效用例相隔约 593 秒。
这说明临近期限仍在推进用例，但文件存在不证明该用例断言通过，也未确定唯一
超时原因。临时文件继续保留，没有修改源 fixture 或放宽期限。

`guest-quiet-collector-v7-post-posix-001` 及其 root 回读在失败执行结束后完成，
完整采集为 429,121 字节，摘要
`19eb58015e486a436d3a72d8328ba5582c656c04ce5f86a9e1c4f47751a6a48b`。
两次身份观察一致，仅有原 manager、sd-pam、pause、D-Bus 四个角色；container、
pod、系统 Job 与用户 Job 列表均空。165 项原查询及其非零包缺项记录完整保留。
这支持本次执行结束后的无额外工作负载结论，不能替代 SSH 丢失、SIGKILL、服务
恢复或重启演练，也没有解除 collector 的生产就绪阻断项。

## 同步持久化修订的文件验证（09:32 UTC）

v1 的独立审查保存三项 P2：QPERSIST-001 的主卷目录检查阻断独立 capsule 恢复；
QPERSIST-002 的取消异常没有锁定后续写入；QPERSIST-003 在已启动后缺少 started
capsule 时仍接受追加。11 个实际方法受控反例和原 v1 字节保留。v2 仅拆分必要的
run/主卷检查、补齐取消失败锁定，以及收紧已启动 capsule 要求；固定 core 和
原 96 项测试不变。v2 冻结摘要为
`0da189eb056acfd92b39b66f1f65c37377d9713ec1213468689e470fc2c9051a`，尚待原审查者
独立核定，作者修复声明本身不关闭 Finding。

`guest-persistence-v2-source-tests-001` 在 Linux 上 154 项通过、无跳过。另一次
独立测试实际使用 tmpfs 与 ext4 两个新测试根，经既有私有入口启用生产祖先、
owner、mode、mount-type 和 FD 检查；17 项全部通过。覆盖双卷追加与回读、错挂载、
链接和权限负例、主卷目录替换、run/锁身份损坏、缺 capsule、部分写入取消，以及
合成 capsule-only 接管不访问主卷。首次包装因申请超过原采集器 30 秒上限而在
测试开始前被拒绝；新编号在原 30 秒限制内通过，失败记录保留。

两套 JUnit、原生命令流、实际 mountinfo、测试文件内容与目录身份已回读并保存在
`persistence-v2-native-files-001.tar`，256,000 字节，摘要
`0c8c41ea18d4d29194274a5fe6408b41c526001062c72129f786070c93d21078`。
这些是同步文件模块与受控故障分支的验证；测试 lease 与接管观察是合成输入，
未调用生产目录构造器，未创建真实窗口，也未实证坏盘、D-state、断电恢复或
guardian 的异步时限。异步 I/O 接线仍在设计，服务与注册边界保持不变。

## 持久化独立验修与后续候选（09:45 UTC）

`quiet-persistence-independent-verification-002` 已将 QPERSIST-001、QPERSIST-002、
QPERSIST-003 核定为独立验证修复，无新增 Finding。它复核 47 个冻结源文件、
原方法差异及 11 个原独立反例，并重新核对 Linux 154 项、双文件系统 17 项，
以及 109 个原始归档文件、173 条文件元数据和固定 core 下的实际日志。
两个部分写入取消样本保留原 13 字节残片；没有以完整日志替换失败证据。
验修记录摘要为
`f1b85e9e3e3a1b1ea9db77fc3bd35faaccb60ff3fb3b00f0663d9409391860a6`。
这关闭的是同步文件模块的三项问题，尚不证明异步 guardian、真实 lease 或恢复。

非阻塞 I/O 接线设计已冻结在 `runner-quiet-persistence-io-design-v1-candidate`，
冻结摘要 `6c9c8de3f7e0e3013861b70176a5cd471de6daeaef04f88554e50ccbbb6da898`，
正接受独立设计审查。它明确旧 Handle 不能直接交给 fork 子进程；主卷 worker、
run worker 与父进程的可信链头各自承担不同检查，只有两份完整文件结果与进程
结算均符合原请求后，父进程才可能接受新链头。MAIN 出生留证须先于唯一文件请求。
候选提出额外两个 4 KiB pending 文件，总 run payload 从 204,800 到 212,992 字节；
这是待审查的设计增量，原冻结合同、同步实现与核心预算均未修改。

实施顺序为：先准备已有子进程的非阻塞推进模块，再实现固定协议与出生/FD 分配，
然后接入父 lease、链头与两阶段确认，最后处理真实 guardian。第一块候选已开始
准备；当前没有新 worker 出生、生产执行入口、服务操作或静默窗口结果。

另一次 `local-posix-timeout-diagnosis-001` 只读复查保留的合成输入：正常对照约
13.525 秒以 0 返回，最后一个无效 TCP 输入约 10.252 秒以原预期 3 拒绝，输出
逐字相符。辅助包装随后因读取后的完整 stat 比较失败而退出 1，此失败保留；
比较包含可因读取而更新的 atime，但前一份内存 stat 未单独落盘，故 atime 定因
只作为推断。新的回读没有重跑 validator，而是核对原始流、输入摘要与稳定身份，
并完成新的低权限源码检查；mtime/ctime 与之前的临时目录盘点一致。
这些观察支持累计耗时线索，不证明原运行中该子用例已经完成，也不改变完整
gate 的 124。诊断记录摘要为
`c89b09bb88b66778f1e783cdaea195c82ebbc6df1c5772be9882c9c53cfda8be`。

## 接线设计审定与只读版本快照（09:49 UTC）

`quiet-persistence-io-design-independent-review-001` 已完成上述接线设计的独立
审查，无新增 Finding；记录摘要为
`3b523dd5f309f93d6f3372f454a43753ce6c264f26307348d93491a1e4ecf48a`。
新增 8 KiB 留证预算仅在设计层审定。完整合法 schema 的实际 4 KiB 编码、64 KiB
数据运输、固定来源与 FD 分配、异步出生及真实循环时延仍是后续实现的验证义务。
主卷 writer 未决时的独立 run emergency 属于明确的恢复特例，不能据此启动第二个
主卷 writer；run writer 未决时同样禁止第二个 run writer。没有据此执行真实恢复。

09:46:40 UTC 的目标仓只读快照显示 `main` 为
`f0a9e118312cc298e213aea37f8321c4a46611ff`，当时工作树干净，两次 HEAD 相同；
查询关闭 Git 可选锁。快照 `task0048-stage11-target-readonly-001` 摘要为
`82db155fb0e216ec385de52b5a30089831e45c43d1a4eca14e44fdd4d693a959`。
这不表示并行写者已完成交接，也不采用该提交作为已验证的 Linux subject。
此前实际执行仍只绑定历史 `cd02cb3c`，目标仓继续保持只读。

## 成功验收模板修正（10:06 UTC）

`local-posix-success-acceptance-fix-candidate-002` 修订了之前未执行的成功验收工具：
补齐固定 run 环境参数，并将两条绑定实际 engine/nonce 的 root 组件输出纳入
完整 16 条有序标记；标记核对在两套原组件校验全部完成后进行。其余原业务、
来源、子结果和跳过判据保持不变。旧工具与本次失败执行均未改写。

主任务独立核对 12 个冻结文件及归档、可逆 AST 差异、一个正例与 25 个拒绝例，
并核对作者 48 项受控测试无失败、无跳过。实际失败归档和仅补造最终标记的日志
仍被拒绝为成功。独立记录摘要为
`050cc4c545926bd01a79cd7f410a07b4f6ff4b01ef3aa98ac235e6f258489fe0`。
首次独立校验器只还原一条语句，未计入四条相关语句搬移和完整标记返回值，因此
自身断言失败；原校验器与失败记录保留，第二版按真实最小差异完成核验。

本结论只验证修复候选。guest 模板开头保持无条件退出，主机入口也保持无条件
拒绝，脚本摘要明确未绑定；未对旧失败 run 执行成功验收。将来须在新的实际
运行、固定来源和回读编号确定后，另作可执行版本并独立复核，不能直接启用旧模板。

## 非阻塞管道推进模块完成验修（10:35 UTC）

`runner-quiet-native-pump-v1-candidate` 已冻结并完成本层独立验修。运行时摘要为
`b04025864343588bd0722d7ab449ad5889995193322d6192548ee36f37c6df11`，交付摘要为
`2ac77b4043f7c9a28d78cbae141878f1120d3c804e53999f4c672e49342e6dbe`。它只推进一个
已出生、由当前测试父进程独占等待的子进程及三个非阻塞管道；没有生产出生、
任意命令接管、文件事务、ACK 接受、服务或 guardian 接口。私有测试构造器仍明确
返回未认证身份，Python 私有名称本身不构成权限边界。

原草稿的两项 P2 为 QPUMP-CANCEL-001（入口时钟取消没有永久锁定失败）与
QPUMP-CANCEL-002（关闭取消丢失未决 FD 记录）；另有主任务发现的收尾时钟过期
问题。固定源补齐整个 step 的取消保护、关闭与 signal/reap 的未知结果留证，
并在所有收尾动作结束后重新观察原绝对时限。不会重试可能已经释放或复用的
数字 FD/PID，也不以新的截止替换旧截止。独立审查重做 50 个实际方法受控检查，
将两项 Finding 及原收尾时钟反例核定为已修复，无新增运行时 Finding。正式记录
`native-pump-independent-verification-002` 摘要为
`7924aae6207acfc70fd863d0a61dd0c775959e9cf0336ade79f19b60066102d3`。

Linux 上 95 项全部通过、无跳过：82 项仍为受控端点测试，13 项实际使用匿名管道
和测试出生的子进程。真实用例覆盖 0/1/16 KiB/64 KiB 传输、EOF、非零退出、stderr、
65537 字节拒绝、提前关闭输入、精确组取消、独立旁观者存活，以及错误或复用 FD
拒绝。原采集器在 30 秒上限内以低权限身份启动测试，实际约 4.374 秒、退出 0，
两流 EOF 与回收记录齐备。原始流、JUnit、96 个安装源文件身份保存在
`pump-v1-native-files-001.tar`，71,680 字节、10 个文件，摘要
`3054e7bf160997bf1dbb1681e06c19112465b34f3905dd061b678ecba61ecffd`。

前两次包装失败均保留：首次因不存在的目录属主方法在启动测试前失败；第二次
使用相对测试路径，且低权限 JUnit 路径位于不可遍历的诊断祖先内，导致收集失败，
没有业务用例结果。第三个编号修正为绝对测试路径和本次专用低权限临时目录，
固定候选源与原截止均未改。第一次失败回读误以为 JUnit 必定存在，同样保留其
非零记录；修订回读明确记录缺失。没有以这些包装结果替代业务验证。

另一次独立补充包装完成 7 组 Linux 实际观察，保留每个已知测试子进程的身份、
管道元数据、完整 step 耗时与收尾记录。持管道后代用例中，leader 的原退出码为 0，
传输仍正确保留 `execution_deadline` 失败；精确组信号后，测试自身通过局部
subreaper 核对并回收该已知后代，退出码为 -9，随后恢复原 subreaper 值。本次最长
完整 step 约 2.304268 毫秒，只是本次样本，不证明硬实时或 guardian 一秒循环。
归档 `pump-v1-native-observations-001.tar` 为 40,960 字节、5 个文件，摘要
`ba3199a4af5c8fffe8359bd45f7aaee26facfbd647210055f496cc230ba45254`。

补充包装的两个未执行旧版本也经独立反例修订：逐个收束已知 child/FD、保留原异常、
始终尝试恢复 subreaper；未观察到后代身份时保持 unknown，不能记为尚未出生或
清理完成。最终包装经 7 个受控反例复验后才执行，其真实归档亦由独立审查者核对。
本层仅证明这些已知测试对象的收束，不宣称一般进程树缺席、生产身份、存储提交、
ACK 接受或服务恢复已经成立。

10:32:32 UTC 的目标仓只读快照仍为 `main` 的
`f0a9e118312cc298e213aea37f8321c4a46611ff`，当时工作树干净，两次 HEAD 一致。
`task0048-stage12-target-readonly-001` 摘要为
`76775809d78b3aceb3d785acf2a6709c3fda6958af4fd4c71b5ad2a0926043b6`。
没有建立写者交接或采用新提交。完整 POSIX gate 仍保留原 124；成功验收模板仍
不可执行。下一步继续独立审查纯协议候选，并准备固定出生与文件检查映射；
实际 MAIN/RUN worker、父方两阶段确认及 guardian 接线尚未完成。

## 纯协议候选完成独立审查（10:45 UTC）

`runner-quiet-io-protocol-v1-candidate` 完成纯数据协议及独立审查，无新增 Finding。
交付摘要为 `c324a850d8cf8b6c044a078806fb2b211f6cca7c5b127ff1f5cf1c48eb8d9c9e`，
运行时摘要为 `8d048c0b8eeab91c3720ea9d27647aa4c1d363dce9461e765500365858350109`。
本版仅定义 `main_append_event` 和 `run_replace_head` 两种待核对的文件事务值。
父方保留的 before/after 与数据被固定为字节；ACK 只与这些原始预期比较，不能
反向构建可信链头。返回值始终未认证，不接受 checkpoint，不产生 permit。

Windows 与 Linux 均为 149 项纯数据测试通过、无跳过；在 Linux 上运行并不将其
变成真实管道或文件事务测试。独立审查另作 245 个实际方法检查，包括固定 core
认可的 36 条合成事件链和 72 次 MAIN/RUN exchange，并验证严格 canonical、
重复键/非有限数/bool、长度与 EOF 状态、错误 ACK、跨窗口/事务重放及可变引用。
独立报告 `quiet-io-protocol-independent-review-001` 摘要为
`4c4bdcd1459426f8985ec324081043038ad5d650d83ba9fe81e5f59a7d2a6c89`。

实际最大完整请求对象为 1813 字节，连同固定 flag 和两个 NUL 的控制参数为
1836 字节；完整 ACK 连同 LF 为 917 字节，均未放宽 4 KiB 限制。独立数据 framing
保留 65536/65537 边界；65536 字节填充对象仅通过运输形状检查，仍被业务 schema
拒绝。完整最大事件形状与真实 core 合法事件另列，不将填充对象称为合法事件。
既有 core 与同步存储源未改变。

Linux 原始流、149 项 JUnit、交付与 28 个源文件身份已保存于
`io-protocol-v1-linux-tests-001.tar`，51,200 字节、7 个文件，摘要
`c4b8b3f57fc91fa8b99da2099618e6b6ed11b79faf1285fdd2773a9fabd8d9ec`。
该归档也已独立核对。固定进程创建、父方来源观察、实际 FD 分配、MAIN 请求屏障、
pending、其余存储事务与真实耐久性均不在此版实现内。后续 worker 设计仍须解决
这些具体接口，再经独立审查；两种纯协议通过不表示完整 worker 可执行。

## Worker 设计审查与运行环境变化（11:23 UTC）

`runner-quiet-io-worker-birth-design-v1-candidate` 已完成独立设计审查，无新增设计
Finding。交付摘要为 `a5878a098916615970037662ca0693cdbe94e6ce9c547f02e91d65f11752a598`；
9 文件归档为 112,640 字节，摘要
`364d062a1df307a9323d8b08d3f51616e55835d9c2c780ed34f86bbca685a988`。
审查核对 16 个固定输入、原存储全部 51 个方法、149 条检查索引与 26 项设计约束，
并执行原 takeover 纯值的 3 个正例和 15 个拒绝反例。审查报告摘要为
`1df25a6115187812a88635ea594f961ad3614ff68dab9fe63ffb967d2e690ce9`。

新设计将 fork 后的实际身份观察、固定解释器与 sealed source、exec 后完整 FD
复核、RUN pending 完成后唯一一次释放 MAIN 数据分开。原 RUN capsule/head/temp
检查并入 pending 前置检查，MAIN 完成后的 RUN mirror 再次读取检查。MAIN 仍完整
读取并重放 journal，父方提供完整 canonical+LF 历史字节的长度与 SHA；这项密码学
承诺与 RUN 先建无动作存储的 bootstrap 顺序均作为显式设计差异审查。设计列出
14 种固定事务，未实现出生、文件事务、父协调器或真实 guardian。

`runner-quiet-io-reply-bounds-v1-candidate` 的完整 armed/started 单对象回复分别为
3016/2433 字节，独立测量及 24 个拒绝反例通过；没有截断对象或增加结果管道。
原文将 ACK 字段数量误写为 18，实际为 17，加 `object` 后共 18。该 P3
`QREPLY-DOC-001` 以单独文档更正候选保存，未覆盖冻结源或改变算法、测试结果。
更正后 README 摘要为
`aae3bda904cdded6df412a19ff84824ab8cf2a2c7aa0576d9d53db2b77d1f447`。
此测量只覆盖两个 capsule 回复，全部新 kind 的完整 argv、pending 和 ACK 最大值
仍须在单元 A 的实际编码器中验证；原 4 KiB/64 KiB 和时间预算均未放宽。

10:55:13 UTC 的宿主只读核查发现旧 QEMU PID、QEMU 进程名与本地 SSH 监听均
不存在，停止原因未知。`task02-guest-unavailable-001` 摘要为
`de4d1eced39abf832d1ebf8518743899a236a062ba1b329bd52ba308eb459f1a`。
旧 Linux 测试保留为各自运行时刻的有效历史证据；旧 boot、进程和服务基线不能
继续作为当前在线事实。未重启 VM、操作服务或尝试使用旧身份执行 guest 命令。

10:57:32 UTC 的只读 `WHvGetCapability` 查询成功，报告 Windows hypervisor
present；记录 `task02-whp-capability-001` 摘要为
`0192b6ab288f48adf34bafc00dc72ee4dd83967e68c798f32189a3d91d35f449`。
该 API 的能力查询语义见 [Microsoft 原始文档](https://learn.microsoft.com/en-us/virtualization/api/hypervisor-platform/funcs/whvgetcapability)。
未创建 partition、启动 VM 或修改系统 feature，尚不证明 QEMU WHPX 可用或完整
gate 性能。完整 POSIX gate 仍保留 124 失败，目标仓仍只读且无写者交接。
后续先完成树外纯协议与文件 primitive；任何 Linux 实测需重新建立当前环境、
boot、来源、挂载和适用执行边界，不能沿用旧在线快照。

## 文件 leaf 第二版完成独立复验（11:53 UTC）

`runner-quiet-file-primitives-v2-candidate` 实现仅持有 FD 的稳定读取、独占创建、
固定 head/pending 替换、journal/emergency 追加及事务 FD 收尾。交付摘要为
`d563fb0fa4c393c3cc1bb2ea11799e2c4e1659d985f4c0aa2c71cb84259d5087`；
17 文件、235,520 字节归档摘要为
`a12a98262a40ac03c6f3b6b64dd9c746e710ab3252c905baf8e0135bf6442c85`。
公开构造器仍拒绝，测试入口不发行生产 grant，也没有 worker、ACK、服务或 guest
接口。根目录/窗口、锁路径、lease/capsule、14 kind 组合及父协调器仍未接入本层。

独立审查与根审查先后发现三个 P2，旧源码、反例和失败状态均已保存：

- `QFILE-001`：open 结果未知或已知 FD 登记被取消，收尾未跟踪该资源。
- `QFILE-002`：目录 FD 释放后，号码复用到同一 inode 仍可继续写入。
- `QFILE-003`：已知 FD 移出集合后、close helper 尚未进入时取消，可能误报全部关闭。

第二版在打开前记录获取中状态，未知结果保持 unknown；已知结果登记失败时仅尝试
关闭一次。关闭前先记录关闭中状态，再移出集合；所有 cleanup 失败均 latch，
主异常不被次生异常替换，未决号码不重试。每次 leaf 操作先核目录 FD 当前所有权。
这些记录保留可观察的不确定性，不宣称消除了 Python 或内核的任意取消时间窗口。

作者固定源码的 62 项宿主受控测试通过，6 项 Linux 原生测试跳过。独立复验核对
JUnit、17 文件及旧版完整 29 文件归档，执行 32 项新源受控检查，并保留旧版 6 项
close 入口失败复现；三项 Finding 全部独立关闭，无新 Finding。独立报告
`file-primitives-independent-verification-003` 摘要为
`23230bb566171d369e148cde536a497ea0c441b636dbc4dc9fc26727b444e5c0`。
没有 Linux 原生执行，也不把这些测试当作真实 tmpfs/ext4 耐久性或 guardian 验收。

第一版冻结加入历史源码副本后，原全目录 Ruff 命令将失败 draft 和原存储旧格式也
纳入了检查；两项失败日志已保留。独立核对后的更正文档使用 `--exclude reference`，
仍检查全部新增运行时、测试和工具，不改变规则或阈值，也不重格式化历史源码。
更正回执摘要为
`0d86dc5cd8cae7889d3522a74e937e2c77c88a808debeec75b95031cf03d0f82`。
第二版以原归档保管这些历史字节。原保守 128 次写循环行为未放宽：最后一次写完仍
可能被拒绝并保留文件；未将完整残留认作已接受结果。

新事务纯协议已进入源码实现与审查。预审发现部分主动写缺少 guardian 与 lease 的
跨字段绑定，`QTX-001` 的旧源独立检查 42 项，其中 12 项实际错误匹配已保留；
其修复及全部新编码最大值尚待固定源码独立复验。根目录/窗口检查层继续树外准备。
当前 guest 不可用、完整 POSIX gate 为 124、目标仓只读且未交接的边界均保持。

## 14 kind 纯事务协议完成独立复验（12:20 UTC）

`runner-quiet-io-transaction-values-v1-candidate` 已固定请求、ACK、pending 与父侧
保留上下文的纯值协议。交付摘要为
`9dcf38b0b7b48fe013072f5aa71c22634102e5c34370f90f4876d63726a13d2e`；
103 文件、2,252,800 字节归档摘要为
`c19c56ecdb5030713c77594626a54e9a7b5afe353d3c17937886c0f553dd0104`。
原 core 和 event shape 字节保持不变；本层不执行文件、进程、时钟或 guest 操作。

根独立审查保留三个问题的旧源与实际错误匹配，并复验修复：

- `QTX-001`：主动写的 guardian PID/start tick 必须与 lease 绑定；恢复读取与
  emergency 保留新 holder 的纯值表达，仍不证明实际接管身份。
- `QTX-002`：已接受 contract 的 started 读取不能通过矛盾的未绑定标志接受缺失。
- `QTX-003`：MAIN prepare 必须从完整 lease 数据直接核对 armed 摘要，不能依赖
  可省略的重复上下文才执行该检查。

独立重跑固定源码的 335 项宿主纯测试全部通过，另执行 208 项独立检查；三项
Finding 均独立关闭，无新 Finding。核对了全部 103 文件与归档、一次性比较状态、
不可变父上下文、请求与 ACK 绑定、pending FD 值以及原 core 的 128 event 重放。
最终独立报告摘要为
`fc3c7076eabdc67b7bbfb59c86416c45614be3146a4cc947f7d7c36a7d9d7e28`。

14 kind 在当前闭合字段域内的最大完整 argv 为 2,834 字节，ACK 含 LF 为
3,016 字节，pending 含 LF 为 2,125 字节。已独立核对实际编码器、最长合法字段与
定长摘要；这些是协议值域上界，不证明最大 4 MiB journal 可达或真实内核身份。
原 4 KiB、64 KiB、4 MiB、128 event 及时间预算不变。经原存储逻辑复核的
`DESIGN-AMENDMENT-001` 保留未 start 时 RUN emergency 的空 contract，以及
部分 start 的恢复表达；不产生执行权限。单次 Exchange 的终结不能替代全局重放
防护，父侧单调发行及有界保留仍待实现。

冻结工具的两项 Ruff 风格问题另包修正，原协议交付未重写；独立验证精确差分、
归一化 AST、上下文退出顺序及 Ruff/format。更正交付摘要为
`966a4590c8fe2d6de522be8af91c0a1009c835f7c3ba7e8e5918c3489b059101`。
修正后的冻结工具未执行，不将脚本审查当作重新生成交付的证据。

根目录/窗口检查层已交作者候选，独立审查仍在进行。14 kind 文件事务组合、实际
worker birth、父协调器及原生集成尚未完成；本次没有 Linux 原生执行，协议输出
的身份认证、operation readiness、checkpoint 接受和 permit 均为 false。
完整 POSIX gate 的 124 失败、guest 不可用与目标仓只读未交接状态保持。

## 根目录与窗口检查层完成宿主独立复验（12:36 UTC）

`runner-quiet-root-window-guards-v2-candidate` 固定交付摘要为
`163cffff376375ffb3efcccee26c0f1eead1a0d2c77b8d1107df68ab55d779c9`；
26 文件、706,560 字节归档摘要为
`bc368d615ef0b04a4d7fabb50417512f29828f4e74731834b705976737b9ddfb`。
本层实现完整根目录祖先、固定挂载类型/设备、窗口目录、父保留 tuple5、RUN 锁路径、
独立 holder 锁 FD 与固定临时文件检查。复用 B1 第二版的 FD 台账与 private open
context；全部文件系统操作仅可放在固定 worker 或循环前准备阶段。

第一版独立重跑 118 项宿主测试及 28 项补充运行时检查，无运行时 Finding；
138 个建模调用位置的三类异常注入合计 414 次，包含在宿主测试中，不另加测试数。
根审查与独立复现发现 `B2-TEST-001`：Linux 测试 fixture 尚未完整核验挂载与祖先，
锁测试就先创建文件。实际 fixture/test 函数的内存模型调用序列证实错误设备下先
CREATE、后 mount_type 拒绝；未执行真实 Linux。原失败探针摘要为
`058e70235be8f47ea414b1bfad9d6f3c6b80b7757b0ce1963d022922dfeba828`。

第二版仅将 native fixture 的 yield 包在已准入的 checked_root 内，并补宿主回归。
运行时、B1 依赖及原宿主测试字节不变；原第一版完整交付、归档和 Finding 保留。
固定第二版独立重跑 126 项宿主测试通过，6 项 Linux 测试跳过；28 项补充运行时
检查和 13 项实际 fixture/test 函数的受控检查通过。错误设备、文件系统、祖先、
根替换均在创建前拒绝；有效入口仍先准入再写，退出替换及三类取消异常按原要求
拒绝或传播。该测试基础设施 Finding 已在固定第二版独立关闭，Ruff/format 通过。
最终独立报告摘要为
`ce740e91c47e686705095296ff0395ec488f96b3304144a81588eaed62a92e95`。

本层不签发生产 grant、不验证实际 holder/boot/source，不实现 flock 获取、完整
文件事务、worker birth 或 guardian。新打开的稳定 W 不等于父原先保留的 W；
上层仍须将经核定的父身份明确传入比较，不能由当前 fstat 重建旧事实。
原生内核、挂载、取消、时限及服务行为仍待当前 Linux 环境验证。

14 kind 组合设计另发现输入闭合缺口。根对固定纯协议执行 32 项实际纯调用：
14 个完整父上下文基线通过；11 kind 缺少保留上下文时拒绝；MAIN append/read 的
root/W 新字段、bootstrap/prepare 的新 W ACK 对象均不在旧闭集内，pending 又要求
完整 MAIN request。探针摘要为
`28d7f802f2dfe8286b66fb5c941ba99035d2b42825d9ca23ebe4c654c3da0887`。
这说明固定 worker 传输仍需明确的新版设计，不重开纯值协议已修复的问题，也不
将本层复验算作接线完成。目标仓继续只读；本轮未启动 guest 或执行原生测试。

## 14 kind 文件组合设计与传输修订完成独立审查（13:16 UTC）

`runner-quiet-file-transactions-design-v1-candidate` 已固定 14 类事务的输入来源、
原检查对应、读写顺序、失败残留与最后 ACK 条件。交付摘要为
`56b82facaa4ecfe1782c4141e799a1cf602a42a3e2e233ab2a40944bf05de274`；
35 文件、4,587,520 字节归档摘要为
`69e7d2941baa7bd32036a8c495ffb6474684c3dbab71a2de404a48f3bcf0e038`。
这是已审设计及纯测量模型，不是已实现的文件事务或生产 codec。

修订采用 request/v3、transport/v1、pending/v2、写 ACK/v3 与读 ACK/v2。现有单 FD3
承载完整 payload 与必需父上下文，整个 envelope 共用 64 KiB；payload 自身、完整
transport、context 的长度或摘要分别绑定。MAIN append/read 补齐父 root/W 身份；
pending 携带完整 MAIN request，并要求 FD5 的 dev/ino 值与该 MAIN root 一致，实际
内核 FD 来源仍由 C 验证。仅 bootstrap/prepare 的成功 ACK 返回文件效果摘要与实际
新 W tuple5 的完整对象；父在实核来源与完整结算后一次接收，失败不能更新 W。

RUN mirror 保持原 2b 的 fresh capsules/head/temp 检查；完整 pending、MAIN request
与实际结算的关联由父发行前核定，worker 不从摘要展开缺失的 birth/gate 事实。
emergency 明确保留原仅依赖 RUN、父 lease/armed 与完整 emergency 链的能力，不因
新加 capsule/head/MAIN 读取而堵死故障记录。允许的 started absence 只来自初始固定
nofollow stat 的明确 ENOENT；B1 读取已 latch 后不能转换成正常 absence。

独立审查核对全部 35 文件与归档，逐字节复现两份最终报告，执行 20 组正向检查、
213 个拒绝反例与 39 个 event 分支；作者及独立审查工具 Ruff/format 通过。草稿的
stale failure-after、outer/nested 新字段漏检、FD5 与 MAIN root 缺关联均保留旧反例，
并在固定设计模型上关闭。独立报告摘要为
`4987e60f0ca228be4539b789596e6a97ab3ac95cbaec8bc5e98b4274d0716600`。

闭合字段域内最大完整 transport 为 10,587 字节，argv 含 NUL 为 3,215 字节，ACK
含 LF 为 3,016 字节，pending 含 LF 为 2,125 字节。最大 event 为 3,132 字节，
来自 39 个合法 shape 分支的完整枚举；不声称该组合可由真实 core history 或内核
产生。MAIN/RUN 并存仍共享每 step 的 16 KiB/100 ms，等待期间不刷新原 30+1 秒及
绝对 deadline。这些字节计算没有证明实际调度或一秒 guardian 循环。

CHECK-MAP 的旧报告引用另包单处更正，原 35 文件未改。根核对精确差分与最终报告
入口，更正独立回执摘要为
`5d6073398f2bccafa78625e0faf85ce95e1243ae59bd3a3c47d2aca03f0fa20b`。
51 个原方法与 162 个选定 AST 节点仅表示机械对应，不是行为覆盖率。

后续实现先补完整新版 codec，并独立准备不依赖该 codec 的固定文件 helper；再验证
14 kind 组合及 C 的实际 birth/FD/source/EOF/reap、单调发行和共享时限。新 holder
仅有 capsule/pending 摘要时，MAIN root/W 的只读恢复准入另待核定；原 Store 并未
要求跨 guardian 保留旧 inode，不能伪造这项历史要求。Linux 原生仍未执行，完整
POSIX gate 仍为 124；目标仓保持只读，实际接单、服务与 CI 阶段均未推进。

## 完整新版事务 codec 完成宿主独立复验（13:41 UTC）

`runner-quiet-io-transaction-values-v2-candidate` 已实现 request/v3、transport/v1、
pending/v2、写 ACK/v3 与读 ACK/v2 的完整严格编解码。交付摘要为
`8434a3102d00c4ee9803f253c9f99a2045927bd3e3f9480dbe541dd6fc66b874`；
67 文件、4,280,320 字节归档摘要为
`9820315381f9658ced299d0c07ceeae478f7dbd8804c55afeb15d96cdb17df9a`。
运行时摘要为
`55216c71fb9b94a9c34e7b5861ce63f52b1932dbfb220cfada116c25d3d3cc4e`，
原 quiet_core、storage_values、event_shape 三个依赖逐字节不变。

完整 FD3 envelope 的 payload、context、transport 各自承诺与请求共同核对；新版外层及
嵌套 MAIN request 不投影为旧 schema 后跳过字段。Exchange 保留四段不可变原始字节，
先终结再验证；直接构造、组件错配、失败 ACK 与取消均不能重用该次 Exchange。
`eof_complete=True` 仅是调用者的完整 EOF 声明，codec 本身没有观察内核 EOF。

根独立核对全部交付文件与归档，重跑 665 项宿主测试，Ruff/format 通过；另执行
455 项运行时检查与 177 项完整 pending/最大值检查。覆盖四个 pending 阶段、FD5 与
MAIN root 的 dev/ino 关联、全重绑后的 nested 新字段类型及 FD alias、创建效果/设备
与关闭状态、原三项 QTX 回归、39 个 event 分支和完整 128 event core 重放。
独立报告摘要为
`02910aa32dee608b63b0c8058ff8748abe53a4f370262aec9939b8d5f6198a6c`。

实际新 codec 的最大值报告逐字节复现，摘要为
`2623dc19dae8070ba9bbe7524ea1ab63e5a5883b105225d79a7f3b44ed82c0e9`。
完整 transport/argv 含 NUL/ACK 含 LF/pending 含 LF 为 10,587/3,215/3,016/2,125 字节，
最大 event 为 3,132 字节；这是闭合 wire 字段域，不证明实际内核身份或该最大历史
可由 core 产生。所有身份认证、operation、checkpoint、permit、全局 replay 标记仍 false。

固定文件 helper 已修复作者候选中的创建身份缺口，独立审查尚在进行；四类只读文件
事务进入树外实现准备。完整 14 kind 文件组合、实际 worker/C、单调发行、恢复准入
与原生集成仍未完成。本阶段未启动 guest、未接触目标仓，完整 POSIX gate 的 124
失败与目标仓只读交接边界保持；不据纯 codec 结果填报 implementation_result。

## 固定文件 helper 完成独立复验（13:54 UTC）

`runner-quiet-file-transaction-helpers-v1-candidate` 实现初次 pending 提交及可选 started
读取，交付摘要为
`c096321dd1a936b10a12a0d1ec79e2bf242ba345a0603d36312aa042a60fcb0f`；
80 文件、1,505,280 字节归档摘要为
`9addea4217c5abe6caa79b2030d629ed464ccbfd6b8e1604541e29cdc01fd014`。
原 B1/B2 运行时字节不变；本层只处理固定文件与原始字节，不验证业务 capsule 或授权。

根预审实证 `B3-HELPER-001`：创建并同步 next 后再认领路径当前 inode，会把同字节
替换的新 inode 当作已经同步的文件。旧反例保留实际 fsync inode 113、错误回执 inode
114，摘要为
`30c79d52636748f7c1b289c7d0d062230d53c6f384046360a81be2cea9a74163`。
修复从仍打开且归本事务所有的创建 FD 捕获完整九字段身份；B1 原 close/dirsync 后
再核路径必须一致。后续替换、捕获取消、未知关闭均保留残留并拒绝成功回执。

独立审查重跑 109 项宿主测试及 41 项补充控制通过，核对全部候选文件与归档不变，
Ruff/format 通过，Finding 在固定源码上闭合。395 个建模调用位置的三类异常注入共
1,185 次，包含在九项 pytest 中，不另计测试数。独立报告摘要为
`138a7c153b2cf47bb72b3b8235da7b1b8afd0d87117fea5105ccff79bd1cc5ff`。

初次 pending 保持 target/next 均不存在、固定 next 创建同步、目标缺失复核、rename、
目录同步与最终稳定读取；普通 rename 的检查与替换不具备 NOREPLACE 原子语义，仍
要求受信任的单写者。started 只有初始固定 stat 的允许缺失可返回 absence，读取中
消失、早期 root/lock 错误、损坏内容和已失败台账不能转换为正常缺失或清除 latch。
所有本事务已知 FD 结束后才返回文件观察；未知关闭不重试。

四类只读事务与单 RUN emergency 事务继续树外实现。完整 14 kind 组合、worker/C、
Linux 内核行为、时间预算与目标仓交接仍未完成；当前通过的 helper 不扩展这些边界。

## 单 RUN emergency 事务 v2 完成独立复验（14:24 UTC）

`runner-quiet-emergency-transaction-v2-candidate` 完成固定 `run_emergency_append`
组合，交付摘要为
`7029266abb212a27384f8127c67043122532adeaaf5746079c415b76e261aabc`；
92 文件、3,553,280 字节归档摘要为
`ee9eae325e99c24f3ecc1f1bde4094073520ae56662d707e3c54cb1c9d38ade1`。
运行时摘要为
`26e786dfadcb09b93ca7567c6ef9251a75bd615799f6664e0a280a19e7052150`。

事务复用固定 B1/B2、完整 codec 和原 emergency 历史校验，核对 RUN root/W/lock、
完整旧链及 expected sequence/previous SHA；追加后同步文件和 W 目录，再核身份，
所有已知事务 FD 结束后才生成并比较 ACK。不读取 capsule、head 或 MAIN，不由
metadata 成功清除 guardian 失败 latch；部分写入及关闭不确定状态保留，失败不重试。

独立审查发现并闭合两项问题。`B3-EMERGENCY-001` 将文件结束后的 ACK 处理异常
纳入整次尝试的失败及终结状态。`B3-EMERGENCY-002` 证明 v1 可在未登记输入 FD
的情况下返回关闭完成，部分反例还遗留实际打开的 FD；v2 在纯解码前新增固定 root
FD 5 和已登记 FD 3/4/5 两项检查，只清理已知归属，不认领或关闭未登记 FD。
v1 的早期通过结论已被后续审查取代，原 64 文件、归档和七项反例完整保留。

固定 v2 独立重跑 85 项宿主测试与 67 项补充控制通过（既有 53 项及新增 14 项），
11 项主体质量命令及新审查脚本 Ruff/format 通过；全部候选、历史包与审查包逐项
核验不变，无新增 Finding。最终独立报告摘要为
`fed41bcf3d721688e7cfb23761278312993723e843b4429651fbeda244429a1c`。
137 个建模调用位置的三类异常共 411 次注入已包含在 pytest 中，不另计测试数。

这仅闭合 test-bound 单项宿主组合。输入台账不证明真实 FD 类型或 source 身份，
EOF 仍为调用者值；实际 worker/C、原生文件系统、共享时限与单调发行尚未验证。
其余写事务、新 holder MAIN 恢复准入和完整 14 kind 组合仍待完成。未启动 VM、
未接触目标仓，完整 POSIX gate 仍为 124，implementation_result 仍未具备。

## 四项只读文件事务完成独立复验（14:33 UTC）

`runner-quiet-read-transactions-v1-candidate` 已实现 MAIN history、RUN armed capsule、
started capsule 与 head 四种读取。交付摘要为
`c5d62373ea13ad8681e1e5da48c5e0d5832515d0ded99799acb96785d15b232e`；
79 文件、2,467,840 字节归档摘要为
`63b2c94c9810302198021eae038d232a2092cad2eb80aa53acffa2db2ce25ea4`。
运行时摘要为
`70af8d7040e9e90eceb9673d485224f6159cae4c9cd9f3de0e50e0784cdd2719`。

MAIN 读取实际 current、lease、contract、完整 journal 与 head，并调用原 core 重放
历史；再与保留的 parent head/prefix 核对。RUN 三项读取只访问 RUN，核对保留的
root/W/lock 和新鲜 capsule，不访问 MAIN。允许的 started 缺失仅限显式未开始状态；
读取中的缺失、身份变化、失败台账与业务校验错误均不能转换为正常 absence。
读取完成及所有已知 FD 结束后才编码和比较完整 ACK，不宣称文件或目录发生同步。

独立运行的 169 项宿主测试通过，Ruff/format 通过；根额外完成 86 项控制，另一
审查完成 35 项尾部控制。根实际观察原 core 校验完整 128 个 event、378,943 字节
历史，并拒绝实际文件、parent 承诺和语义历史错误。原 Store 的四个方法仅核对
AST/文本映射，未执行原 Store，不将映射数量当作行为覆盖率。

`B3-READ-001` 的旧反例在文件结束后的 ACK 异常中遗留未失败、未终结状态；固定
版本将整次公开调用纳入失败处理，保留原异常并阻止重用。独立旧/新成对反例以及
helper FINISH 后业务取消、成功后零文件 I/O 检查均通过。最终根审查摘要为
`da1aa6144029c793e446ee6280696bf912f51e12a79d246b9c8bc2141da31394`；
独立尾部审查摘要为
`b486aad12ea53b8c22baf82cb68a94227b141e0dfc017f02a40b15ba62660c43`。

根核验早期 60 秒超时、contract 夹具字段错误及核验工具风格/导入分组错误均保留；
后续仅重跑受影响的补充控制或封存，完整测试日志与 XML 按原固定候选复用，不累计
重试次数作为新增测试。最终封存 41 文件、7,895,040 字节审查归档，候选及独立尾部
包逐项核验不变。上述核验工具错误没有导致候选源码变更。

目前 14 kind 中四项读取和单项 emergency 完成宿主候选验证；其余九项写事务仍待
组合实现。实际 FD/source/EOF、worker/C、跨事务恢复准入、全局 replay 与 Linux
原生集成均未验证，recovery/operation/production 标记保持 false。目标仓只读及
完整 POSIX gate 124 的既有边界不变，不能据本阶段填报完整 implementation_result。

## RUN started 与初始 head 完成独立复验（14:57 UTC）

剩余九写审计核对 22 份固定输入及 85 处源码位置，划为 RUN 初始化、MAIN 初始化、
两卷创建、pending、append/mirror 五批；根核对 47 文件及归档不变，回执摘要为
`078618cbb1cd6ebc34dae4bdf0bdeec95845106b9160d24363e54fe041777aa8`。
这是静态顺序与缺口核定，不表示源码已执行。原实际启动顺序和 MAIN 数据屏障保持。

首批 `runner-quiet-run-initialization-v1-candidate` 实现 `run_start_capsule` 及
`run_initialize_head`，交付摘要为
`80b2cff40c1f585ab2dfe15d470967e4fd24e6893c30b269d662747ef7d75119`；
66 文件、1,720,320 字节归档摘要为
`19cb8fb3936e32c66bfb9caefeb709732feba514974dcf42a9ab40e31c82e3e5`。
运行时摘要为
`665bb00617302fc7477b4a1f0f6f980e0456f3efb7edb8603af396cec3353c6a`。

两项均核完整上下文、RUN root/W/lock 与 fresh armed；写 started 时要求 started/head/
next 不存在，写 H0 时要求完整已接受 started 且 head/next 不存在。固定 B1 O_EXCL
创建后完成文件与 W 同步、根/W/锁复核和全已知 FD 收尾，再比较完整 ACK。整个调用
的尾部异常也终结 Exchange；不访问 MAIN，不由单项成功认定完整 start 或父 checkpoint。

独立重跑 129 项宿主测试及 25 项补充控制通过，Ruff/format 通过，无新增 Finding。
补充实测移除整个 MAIN 模型目录仍可成功、FINISH 后零文件 I/O、完整实际 armed、
mandatory started、占用/next 与锁前后变化，以及 ACK 尾部取消和不可复用。
独立报告摘要为
`3768ea25012f847d84e95f25036ccbd48a713498789f45354c0fc5c7e52cb508`。
290 个模型调用位置的三类异常共 870 次注入包含在六项 pytest 内，不另计测试数。

作者首次完整运行的四项断言错误保留：独占 open 失败按冻结 B1 保持 open_unknown，
坏业务对象按 storage_values 原异常传播。根观察器最初误要求 ACK 仅编码一次，忽略
解码器的规范重编码；修正为所有编码观察均位于相同最终 I/O 计数，只复跑补充控制，
原 129 项完整测试记录复用。上述修正均未改运行时或冻结依赖。

MAIN contract/H0 两项的作者候选已通过 87 项宿主测试，独立审查尚未完成。有限状态
防重放和新 holder MAIN 身份来源仍需设计；C、Linux 原生、实际目标交接与完整 Gate
均未完成。当前仅七项 kind 完成独立宿主验证，不升级 production 或 implementation_result。

## MAIN contract 与初始 journal/head 完成独立复验（15:04 UTC）

`runner-quiet-main-initialization-v1-candidate` 完成 `main_bind_contract` 与
`main_initialize`，交付摘要为
`e7a84b9de0ca6467491e4ab414d8e1597074c6de5c220983697362c87b1ef2ed`；
56 文件、1,392,640 字节归档摘要为
`d508bae7368e75a69441f7a800f040a97fc9da233d63490c711021202927cb70`。
运行时摘要为
`68f25df0effef5260fa453b2a2a5b0d7f7771f5779cbe5d1ef3ae35698ed7db3`，
完整 codec、B1/B2、core/storage/event、模型及参考材料共 13 份输入逐字节固定。

MAIN 实读 current/lease，初始化另实读完整 contract，与保留的上下文及 MAIN root/W
身份严格核对。contract 拟值仍在 payload，context.contract 为 null；要求目标不存在
后 O_EXCL 创建 0400 文件。H0 全字段绑定 sequence=bytes=0 和 contract chain，要求
journal/head/next 全 absent，先空 journal600 后 head600。部分创建保留，不自动重试。
所有文件和目录 scope 及已知 FD 完成后才生成、比较完整 ACK；整次调用覆盖尾部异常。

独立审查在固定副本完整重跑 87 项宿主测试及 82 项补充控制通过，无新增 Finding。
补充覆盖完整但不同的实读对象、同字节 inode 替换、读中消失、祖先/mount/子挂载、
O_EXCL 竞争、128 次保守短写边界、产生效果后的取消、主次异常、FD 关闭后复用、
尾部失败和未登记 root5 的已知清理。源与审查工具 Ruff/format 通过，原候选、依赖
及归档前后不变。独立报告摘要为
`dad294d1d074f91e302ce0124542d99eb1ef604e03628bbc02522863977ccfbd`。
211 个模型调用位置的 633 次异常注入已包含在六项 pytest 内，不另计测试数。

原 Store 的三个方法只核对 AST/文本。测试模型的确定结果不代替 B1 台账中的
open_unknown，也不把已关闭 FD 数字重新认领为旧资源。受信任独写根仍是前提；
本地 MAIN 成功不证明父 pending、真实来源、C 屏障、完整 start 或 operation permit。

现在 14 kind 中九项完成独立宿主验证；两卷初次创建、pending、append/mirror 五项
继续树外准备。防重放提案已提交独立设计审查，未据域内 reserve 单调关闭跨 holder
强序或 G3。实际 worker/C、Linux 原生、服务窗口和目标仓交接仍未完成；原完整
POSIX gate 的 124 失败、目标只读及 implementation_result 缺失保持如实记录。

## 两卷创建完成独立复验，防重放阶段歧义修正（15:27 UTC）

`runner-quiet-window-creation-v1-candidate` 实现 `run_bootstrap` / `main_prepare`，
交付摘要为
`94d68ce58779deaad620131a7bd2cd42bcc4edbf8ead9db1b7d11378f8f59ae3`；
68 文件、1,761,280 字节归档摘要为
`e5ad66018b0a545a01e0ee320b97b2934a9b6879c8d81c50043a9180cdfda031`。
运行时摘要为
`55473d28fdfd51b407973cd52385d4d0cd77c480aa634b71ace63945f17740d4`，
21 份固定输入与原来源逐字节复核，codec、B1/B2 和业务值源均不变。

两项分别只访问 RUN 或 MAIN。创建 W 后、root fsync 前即保留目录身份，持续持有
W FD 并在后续开目录和全部写入后复核；每个 B1 创建文件在原 FD 仍归台账时捕获
九字段身份，跨目录同步和第二文件创建核对，拒绝以同内容新 inode 冒认已同步对象。
RUN 创建 armed400 与空 emergency600；MAIN 要求 current 不存在，创建 current600
与 W 内 lease400。全部 scope 与已知 FD 收尾后才返回含实际创建 W 身份的完整 ACK。
任何异常终结整个尝试，保留部分状态，不自动删除、重试或认定父 ARMED。

独立重跑 119 项宿主测试及 54 项补充控制通过，源与审查工具 Ruff/format 通过，
无新增 Finding。补充覆盖隔离另一卷、FINISH 后零 I/O、同步/写入/关闭已产生效果后
三类异常、同字节 inode 替换、实际子挂载替换、根变化、ACK 尾部取消及 128 次短写
边界。独立报告摘要为
`141217bb7f92ffb78b45b2778946679efa46f8c243c86da8eb7ced655a7000bc`。
325 个模型调用位置的 975 次异常注入包含在六项 pytest 内，不另计测试数。作者首次
完整运行有两项 fixture 误把 window_id 赋回原值，旧源与日志保留；修正只改测试。
mkdir 至首次 stat 仍依赖可信独写根，以上结果不证明恶意特权并发下的创建身份。

`transaction-replay-design-002` 冻结有限状态域内 reserve-and-burn 提案；manifest
摘要为 `40db400a5a690fdba671bd84fc1a772285024b149ea0ab253d8ce80fe3b3c580`。
所有 kind 共用不回绕的 128 位发行序列，失败消耗编号，耗尽停止；最多两个 live slot
和一个 compound，未知 child/close/reap 不释放槽。MAIN M 与 RUN R=M+1 的预留允许
RUN 先完成，不能用最大已完成编号拒绝仍被保留的 M。这是未实现的父协调约定。

独立审查发现旧 v1 的 BORN→BOUND 混淆了请求形成前的观察与 READY 后的来源/FD
核验。v2 明确 REQUEST_FIXED→CONTROL_SENT→POSTEXEC_BOUND：固定请求后发送
唯一 control，完成 exec-error/READY EOF 和实际来源、最终 FD 核验后才构造 pending；
MAIN 仍须等待 RUN 全收尾及自身 fresh 复核才释放 DATA。精确差分和旧证据全部保留，
独立回执 `120ae47a1b107c90a9ede0bbe03defa7f37a9bc1a3afd51d9f9c14a8b10b8d4a`
仅关闭 `G2-DESIGN-001` P3，没有运行时测试或整体 G2 验收。审查工具首轮格式失败
及修正记录也保留；没有改业务来源或协议。

现在 14 kind 中十一项完成独立宿主验证；pending 与 append/mirror 三项继续树外
实现。跨 holder 永久数字总序、真实 worker/C、G3 新 holder MAIN 准入、Linux 原生、
服务窗口、目标仓交接和完整 Gate 仍未完成。原 POSIX 124、目标只读与缺失
implementation_result 不变，未将候选和设计审查升级为执行或生产验收。

## pending 与 append/mirror 完成独立复验（15:44 UTC）

`runner-quiet-pending-transaction-v1-candidate` 的交付摘要为
`e6d0c4d62c7359948179cf7c9cdf8c1196f2c11f3cb02323b67b126c032e4499`；
70 文件、2,713,600 字节归档摘要为
`a722e5b05d4eacc24330c859a1cd81ca221ae0be8ff130ea251597ae5331f35b`。
运行时摘要为
`081fcfbee12ee363066f0064225cac31a982ec1c5aec09292c5b6337b8ea0aec`。
`run_commit_pending` 核四阶段的 fresh armed、按阶段要求的 started/head、next absent
和 RUN root/W/lock；首次提交前退出所有预检 scope，再调用会 FINISH 全台账的固定
helper，返回后只做纯结果及 ACK。替换保留旧 pending StableRead 九字段，旧对象单独
decode 并核父旧 SHA/域，不误用新 MAIN request；next 的实际创建 FD 身份跨同步和
rename 核对。旧 MAIN 完整结算及新 MAIN 的数据释放仍由尚未实现的父 C 负责。

独立重跑 188 项宿主测试及 51 项补充控制通过。四阶段 × 初次/替换共八条路径，
1,892 个模型调用位置的 5,676 次异常注入包含在 24 项 pytest 内。独立报告摘要为
`fdf4f8c917829540d851d9e13f4c37fe7def2e3c506c1f13eae10086d9274477`。
23 份候选固定输入和另行核对的原 Store 共 24 份来源不变；原 Store 没有 pending
方法，新增协调行为归本轮 B3。根补充控制最初将已经取上界的 start_tick 再加一，
触发纯 codec 范围拒绝；保留该审查脚本/回执，改用域内不同值后只重跑补充控制，
复用已绑定源码的 188 项全量结果。没有由此修改候选或删除失败记录。

`runner-quiet-append-mirror-v1-candidate` 的交付摘要为
`839cec0840f65bf645f635b074cc4c9aa984d73e3021119023610b0777d57642`；
85 文件、2,078,720 字节归档摘要为
`f839667452c37012edba543dcc0361f578275ec991b4b471e18421df564b5825`。
运行时摘要为
`2bad76f0b5102b7d51183d4f3e8e63ec81b2585c22e11b50ffbdbf1c51b6095f`。
MAIN 实读 current/lease/contract、完整 journal/head，保留原读基线，实际重跑原
`q.check` / `q.check_dispatch` 并核父 H/P、H0/T0 和完整 after，再 append 与替换 head。
RUN mirror 重新核 armed/started/head/next，只访问 RUN。两项都保留旧 head 九字段和
next 原创建 FD 身份，拒绝同步及 rename 前后同内容的新 inode；全 FD 收尾后才比较
完整 ACK，尾部失败同样终结整个 Exchange。局部成功不更新父 accepted checkpoint。

独立重跑 191 项宿主测试及 50 项补充控制通过；24 份固定输入逐字节复核，独立报告
摘要为 `994cdb561f8f04a451791f65bc6c6710bc4307e99b6c6facc384c8690f2e2006`。
330 个模型调用位置的 990 次异常注入包含在六项 pytest 内；作者新增的 51 项产生
效果后取消控制已包含在 191 项中。作者首轮导入风格失败、后续 smoke/full 与新增
控制记录均保留，运行时从 smoke 起未改。两批源及独立工具 Ruff/format 均通过，
没有新增产品 Finding，未知 open/close 和部分文件仍保留，不做删除或自动重试。

至此 14 kind 全部完成各自的独立宿主验证；同一模型文件系统上的完整阶段衔接另行
核查，不能把单项通过相加当成真实父协调完成。G3 初次目录准入设计继续准备，G2
发行器、真实 birth/FD/EOF/reap、双路共享预算、Linux 原生与旧 POSIX 124 的完整复验、
服务窗口、目标仓交接及 implementation_result 仍未完成。目标只读和所有权限边界不变。

## 十四类事务串联与 G3 设计独立审查（16:14 UTC）

`fourteen-transactions-integration-001` 在每个场景的一份持久 MemoryFS 上实际调用
七个冻结事务模块；manifest 摘要为
`4fa2d6387fd5395c2ef4598387a66f9c245f7285aed259fb48f819a6ec1e6553`，
77 文件、21,022,720 字节归档摘要为
`1f7845eb9134661e8ec07fa0da0bad5ee522fc58c69c2351b04f9b81d86bccbf`。
七份原包及其完整归档、20 份选定源码逐字节复核，共享六个业务依赖保持同一实例。
read 阶段由模型 hook 拒绝修改；测试脚手架选择 creation 的可写 MemoryFS，原 read
脚手架仍保留，没有声称两者相同。每次调用前固定唯一 synthetic parent Exchange，
调用后只比较该实例；3/4/5 是模型 grant，实际传输和 EOF 来源未由此认证。

独立重跑复现了与作者逐字节相同的两场景报告：成功 17 次调用覆盖 14 kind，失败
场景第八次 MAIN initialize 在空 journal 已创建后停止，保留 open_unknown、无 ACK
及未消费的父 Exchange，阻止后续 grant。两场景分别记录 2,869 与 1,342 次模型调用。
另加六项独立控制：MAIN append 的 write 已产生效果、RUN mirror 的 rename 已产生
效果后分别注入三类异常，均保留文件效果、终结 child Exchange 并停止推进。后者
即使两卷 head 字节已相等也没有 ACK 或 accepted checkpoint，不能据磁盘相等补签成功。
独立报告摘要为
`631b85500475ff92a8ec6e6c860af57ebaa3fa689b2fca540a792fdef8fb98c8`；
17 文件、22,108,160 字节复验归档摘要为
`49367676e7b5e4f85598627ede47af2cfe708fef4428999cb8454f58573d7640`。
运行、源码映射及独立工具 Ruff/format 五项通过；作者脚手架失败和根工具初稿闭包
lint 失败另行保留。没有修改任何冻结业务源，也没有新增产品 Finding。

G3 新 holder MAIN 初次目录准入提案的 DESIGN 摘要为
`65dfac2dd03e6c488a1b6dbc44b0d338e1522120840fb8afef8a0306a0c2208b`；
36 文件设计归档摘要为
`bfa62f86b0f7aec9b96334f438932e9434f4bbd77a2b55087eebc34fd64d04d0`。
独立核对 16 份原来源、七份归档、41 处源码/文段与 12 项要求，报告摘要为
`ebfaf787b0f575d0a7a90289e0fe84a2bac6430666af5db2f6ac87dbc70e2d8c`。
本次只认可继续独立 schema/宿主候选准备的设计方向，G3 仍 STOP：新目录 helper 的
FD5 为 IPC，需要单独闭域 grant/schema；两个 SCM_RIGHTS 目录引用必须先隔离，再经
真实来源、完整帧、EOF/exit/reap 与原 deadline 一次接收。父循环不执行 MAIN 探针或
关闭来替代 helper；原子 native 接收登记、有限 unknown 台账和最坏延迟尚未证明。

当前恢复域的首次目录身份不证明上一个 holder 的 inode 延续，活父的已有 tuple
不得刷新。old_writer=None 也不证明从未发行 MAIN；真实 takeover、全部旧 MAIN 收尾
与完整 RUN 事实缺失时仍禁止目录 helper 出生。新步骤共用原计数器、共享预算和
原逻辑 deadline，不能在 helper 完成后重新获得 30 秒。A1–A8 实际机制/证据及 A9
新增接线均未完成；Linux API 文档仅支持接口语义，不构成 native 验收。

G2 纯编号与有限槽候选已交独立复验。真实 C/birth/source/FD/EOF/reap、跨 holder
永久总序、Linux 原生、原 POSIX 124 的完整复验、服务窗口和目标仓交接仍未完成。
TASK-0048 仍 IMPLEMENTING，classification fresh、approvals current，缺失
implementation_result；本次没有补造该结果或推进账本。目标只读边界不变。

## G2 编号与有限槽完成独立模型复验（16:21 UTC）

`runner-quiet-domain-reservations-v1-candidate` 交付摘要为
`4da2d720615d99d37802169fe4713753742971ab243e8c04c15970bfc9e409e9`；
35 文件、604,160 字节归档摘要为
`355f0c46cce917524fcd7fc2b249929525868844c57329d31df176346c354abf`。
运行时摘要为
`925acbd0de6d24f49a62916004e7b66a925fce9460b9f71e6513b823c9ef0069`。
纯测试域使用一个 128 位计数器，0 为未发行哨兵；不可变状态一次发布 burned 与槽。
MAIN 一次预留 M/R，R=M+1、gate=R；R 可以先退休，不能因此丢弃仍 live 的 M。
最多两个 live 槽及一个 compound；原槽全退后可顺序发行新 RUN followup，原对象身份
仍保留。剩一个号却申请双槽时整次停止，不部分发行、不退号或绕回。

独立重跑 77 项模型测试及 33 项补充控制通过，含原 171 个实际源码行位置的 513 次
异常注入；注入数不是额外 pytest 数，也不证明指令级原子性。补充控制涵盖完整 18 种
synthetic 收尾组合、真 128 位边界、R 先退、followup、有界结构及同号对象重建拒绝。
未知 child/FD/stream 保留槽并永久 halt，后来原槽得到完整模拟收尾也不能解除 halt。
独立报告摘要为
`42bb1c7d61170e2071f0de240bfa834d23efbb4149ec2c8785de16c58c8b91b3`；
59 文件、1,372,160 字节复验归档摘要为
`056c2b4bef0805119e9a898de4ad78a34422b4d5b263b885bef4dc1c1f0a3eeb`。
根回读七份固定来源、三份来源归档、16 处文段、原包与独立包全部文件及测试日志通过；
回执摘要为 `7afbad1245decf7f43b2926c7b462c252d00c3b2ebb81e9f105676ab97d1a4bb`。
作者测试准备错误、独立准备工具归档字段错误均保留，运行时未由此修改，无新 Finding。

这只是编号与原实例槽模型。SyntheticSettlement 全由测试调用者填写，既不观察 OS，
也不认证真实域、来源或 EOF/reap；MAIN 与 followup 的业务对应、真实通道、完整
Exchange/compound 事实及父 accepted 发布均未实现。公开构造器继续拒绝，全部权限
属性 false；G2 整体、跨 holder 永久总序、C 与 G3 仍未完成。

后续沿用原 C→D→E→F 顺序。C 是固定来源、出生和数据屏障，E 才是父协调：下一最小
准备单元 C1 固定依赖闭包、确定性 source bundle 和入口接线设计；私有 test 工厂或
stub dispatcher 不能成为生产入口。seal/fd-exec/真实 grant 仍须在重新核定的 Linux
上验证。G3 独立闭集 codec/最大编码与 receiver 测试源码可以并行准备；这些树外工作
不依赖目标仓交接。D 原生文件组合、E 双卷一次接受、F 真实 guardian/恢复、最终目标
采用和采用后 CI、真实服务恢复及宿主重启后业务仍分别保留为待办。

后续稳定指针已封存为 `remaining-c-through-f-plan-001/PLAN.md`，摘要
`f8f25c72ba861bea5551602994c2b7a8c927355d73600bb8c61caed0a3482d04`；
manifest 摘要为
`fa9d145613828b9b4987af933a9fa71e5438b276112bd46f17ab41807c4e4fe1`。
根回读 29 份文档/manifest 来源、14 处文段、12 项候选索引及 47 文件归档通过；
报告来源固定为 `5e9776932a8dae2c29c380f762a1877d356a4749` 的实际 Git blob，
不要求当前追加后的报告仍等于历史字节。首预检漂移及工具 lint 失败均保留。
该清单明确 C1、后续 C/D、E/F 与 G3 的依赖和停止条件，只是准备指针；没有新增
运行时实现、执行旧业务源、恢复 guest 或授权目标写入，也不构成 implementation_result。

## C1 源码库完成独立构建与隔离复验（17:00 UTC）

`runner-quiet-source-bundle-v1-candidate` 固定上述串联包的 15 份应用模块，合计
212,371 字节；其交付摘要为
`b0417060bd5a3c88c514858c3ec54627f83d7025479e138e921ce90cf9208610`。
排除测试脚手架和测量文件，保留空 vendor 包标记；原模块字节没有修改。活跃产物为
`artifacts/build-002/source_library.py`，293,459 字节，摘要
`60d5cff951ebb52fd320d0aed81491af4c53c179d80fbd2243c7647edf86f2d5`。
独立核对原串联包 77 文件、候选 48 文件及两份完整归档，并以正序和逆序输入重新
构建，结果逐字节相同。七项独立负例覆盖缺失、重复、混入测试、源码/loader 漂移、
文本替代 bytes 和空包标记变化，均拒绝。外置 build manifest 绑定 builder、loader、
输入表与产物；包内摘要不是自身来源认证，14 行目标表仍只是描述。

32 项宿主测试独立重跑通过，候选与根复验工具的 Ruff/format 均通过。此前五个隔离
子进程探针与直接执行拒绝记录已核对为同一最终包字节，未冒充为第二轮执行：15 个
模块从单文件加载、17 组真实纯 codec 输入与原串联结果一致，包及延迟 event import
使用同一实例；预先占名拒绝，开始装载后 compile/exec 中断保留部分实例并禁止重建。
公开事务构造器仍拒绝，直接执行库文件非零退出，没有调用任何文件事务。

独立复验报告摘要为
`64ebc645790951a149ab75446d165319b0036d42703fbcc42f2e3cc774965caf`；
31 文件、4,055,040 字节复验归档摘要为
`0ec6bfb219273cb2f17f482d9ccca067bae64448a33e6945b463785e11ef4f22`。
原调用者传 records 的 loader 草稿、旧 build 和检查失败均保留，不能选旧产物替代
build-002。独立来源审计定位 86 处 import AST、11 个直接 stdlib 根及一个函数内
event import；这些数量不覆盖 stdlib/extension 的完整依赖。被替换的宿主文件 API
调用为零也不证明 importlib/native 完全无 I/O，当前结果仅属于 Windows CPython
3.11.9，不替代目标 Linux 3.12、sealed source、fd-exec、READY 或真实 FD/EOF 认证。

16:44 UTC 的新宿主元数据回读未发现 QEMU 进程或原端口监听，原因仍未知；没有联系
guest、启动 VM 或沿用旧 boot 身份。C1 后续生产绑定设计另行独立审查；可发行 child、
C/D/E/F、G2/G3、原 POSIX 124 的完整复验与目标采用仍未完成。TASK-0048 仍缺
implementation_result，目标仓继续只读。

## C1 生产绑定设计完成独立方向审查

`production-file-binding-design-001` 的 manifest 摘要为
`97d7c102f27003d56be20a331caca43c0b17580958d3c18d9e9764a909bd0f79`，
DESIGN 摘要为 `8dfea06f54d10805160fea6b46ae730463b82c077b3b561ef51655ec99b90e2d`。
独立审查核对设计及四个上游包的全部文件/归档、23 份来源副本，并从 15 份原源码
重算函数、导入、14 路目标与 19 处内部测试工厂。审查方向可接受，无新 Finding；
这次只读 bytes/AST/text，没有运行原业务或作者工具，未来工厂行为仍未验证。

具体差分为七事务及 B1/B2/helper 共十个模块另版，新增 binding types、admission、
child 三个库模块，并另加最早内联 prelude。拟 18 个库节点不代表完整来源闭包，
builder/loader/bootstrap、解释器及 stdlib/native profile 均须另行固定。真实 C
来源缺失时生产构造仍拒绝，不能调用或改名旧 test 工厂形成可发行入口。

设计把 SourceImage 与单 role AnchorGrant 分开，固定源码不授予 MAIN 准入。第一条
Python 语句前的失败由父按实际 EOF/exit/reap/unknown 收束；最早 raw owner 先于
loader/stdlib，随后把原 3/4/5 一次移交同一 B1 ledger，READY6 另行收尾。只有原 FD3
读到真实 EOF 并完成全部验证后，精确工厂才唯一 FRESH→TAKEN，再允许 B2 fstat5。
dispatcher 只查表，TAKEN 也拒绝第二次工厂调用，保留同一 child Exchange/ledger；
父 Exchange 是父进程原实例，不与 child 混同。所有已知事务 FD 完成 FINISH 后才
形成 claim/ACK，stdout/stderr EOF 与退出、reap 仍由 C 另观察，E 才能一次接受业务状态。

实施时 helper 必须从同一 invocation 建立自己的新 lexical scope，不能复用已经
退出的预检 W scope；started/initial pending helper 提前 FINISH 整个 ledger 的
原顺序保留。十九处生产工厂替换仍须逐项保留原身份、文件顺序与异常边界，不能只
搜索并替换方法名。目标 3.12 预载、真实 FD 观察、原 deadline 与共享预算仍未证明。

独立 REVIEW 摘要为
`be9ee9f12a1b0d1e16aa4340145e9d8657987543370571fc55323e7f36f9ebb8`；
receipt 摘要为 `31a20530561d99c5615cfc5279fb0e3df2a9b4645af8120072b062ef668fd07c`，
29 文件、4,229,120 字节归档摘要为
`bfee81665e514f93ab65b6519f163c405503038c9346d7ea2e84cafbf0d63981`。
最终静态、Ruff/format 通过，历史工具失败与行号订正记录保留。后续按 DIFF-SCOPE
先做另版封闭绑定类型与拒绝接口，再做十模块工厂保真回归及固定入口/实际 C 观察；
C1-BIND-01 至 08、C/D/E/F、G2/G3 和 native 仍开放，未产生 implementation_result。

源码库另由非作者完成代码审查及 11 项非业务装载控制，无新 Finding；回执摘要为
`05d7093a1f2efd63feab88487a9d4677a18b8643476ef92ddc18af104b31f196`，
56 文件审查归档摘要为
`2c418e2ffdba610f33256d10a56b4eaf51ff770f01e81d8aeaddc0a04bf36722`。
控制覆盖包/缓存原实例、装载前后碰撞及三类 compile 异常；最终 Ruff/format 通过。
prepare_library 再次返回失败的原库不代表健康或 READY，其后 import/preload 仍拒绝。
固定源码加载器不提供同进程反射沙箱或多线程原子性，只接受用于源码库准备。

## 绑定引用与本地 claim 生命周期的首批实现

`runner-quiet-binding-types-v1-candidate` 已实现独立的 `io_binding_types.py`，运行时
摘要为 `f5c2a3442f67e3fbdfca57d70a27eae7397c3a2520d71bdd2712b593594f700c`；
交付摘要为 `5ad5dd479bf4072452978d1c03534068097214620b636ce07add606dba623e09`，
50 文件、1,566,720 字节归档摘要为
`ec297df08242e4a9c2a62796c4bf02f383ca7fbf4f0a05006565a681a9478e89`。
生产 ChildEntryState、CompleteDataRead、BoundFileInvocation 和 BoundDirectoryScope
的构造、复制、反序列化及消费继续拒绝；正向行为限于明确独立的 SyntheticDomain。
原 15 模块未改，新模块尚未纳入生产源码包，也没有重新创建最早 raw owner。

一个测试域保存五个原对象引用，只有精确 kind、原 invocation 和全部相同实例才可
FRESH→TAKEN 一次；14 行路由仍是固定目标描述，不是实际类注册或 dispatcher。
当前 root/window 各最多一个 lexical scope，退出后不保留历史 scope/generation。
同 FD 再开得到新的原 scope，旧句柄不能复活；失败或 unknown 保留当前有限槽，只
允许原 scope 退出。模型 ledger FINISH 后禁止再开 scope，compare_started 先记
模型 Exchange 终态，最后 FINISHED 仅表示本地纯 claim 形成，不能证明输出或父接受。

根衔接实际使用冻结 codec.Exchange 和 B1.TransactionFDs 原实例，17 组原输入覆盖
14 kind，另三类失败全部通过：close 未知、全部关闭但 ledger.failed、ACK 比较失败
且 Exchange 已终态，均不能成功收尾。正向路径两次使用同一窗口 FD、撤销旧 scope、
结束 B1 台账后才比较 ACK。模型不读写所引用对象的属性；检查由测试在外部执行，
B1 close 被明确替换为模型记录，没有真实 FD 关闭、EOF、文件事务或生产绑定认证。
根报告摘要为 `fb28555bd371b45513778ae710d1d6863d92706ae1eca4d6a74e3487724fb4bd`；
19 文件、624,640 字节衔接归档摘要为
`aba19881d63c0ccbcfc0508fef7030174d4df974b41daa5d2bea21d084407a75`。

最终运行时与首稿仅折行不同，独立 AST 比较相同，17＋3 控制按最终字节重新执行。
作者 89 项宿主测试包含 133 个已执行保护区源码行的 399 次异常注入；这不是额外
399 个 pytest，也不证明任意字节码位置或 native 原子性。最终 Ruff/format/来源
检查通过，23 份来源、三份输入归档和旧测试工具/格式失败均保留。

域内单次规则不提供跨真实域注册：新建两个测试域仍可引用同一组外部对象。外部
close 后重用同 FD 若未撤销旧 scope，本模型也不会自动发现；真实 B2/B1 consumer
必须保留实际 active/owns、目录身份和 lexical 撤销检查。FINISHED 后的 ACK 输出
失败由后续 Entry/C 单独记录，不能重新执行事务或据本地终态补签 parent accepted。

独立审查按最终字节重跑原 89 项测试及额外 55 项消费者控制，全部通过，无新 Finding；
其中覆盖五个值相等但不同的原引用、跨域/同 slots 重建、十四路重复 take、旧 scope
与 FD 复用、错序及永久终态，并实际验证新测试域可复用同组引用这一范围限制。
独立回执摘要为
`aa328fae231c6451a1eae7fc0c7cb454bf851857da56a012a7cd06f067c080d9`；
108 文件、6,031,360 字节审查归档摘要为
`199c22fda71f8107b2173fb47cae4a656ad875ff062e393f4966be940b9c66eb`。
原候选清单、归档和最终运行时逐字节回读，Ruff/format 通过；旧草稿控制与封存工具
格式失败保留。下一批仍须另版实现十模块生产工厂、十九处内部构造及真实 scope
接线，保留全部原检查；实际 producer、C/EOF/source、D/E/F、G2/G3 和 native 未完成。
本仓此次仅追加记录并检查 diff；没有重跑或冒称新的全仓 Gate，没有目标采用、VM
或服务动作，TASK-0048 仍缺 implementation_result。

## 十模块文件消费者接线与异常收尾的另版验证

`runner-quiet-file-binding-v1-candidate` 已完成七事务与 B1/B2/helper 共十模块的消费
接线，新增 file context 接口另受审。运行库共 16 节点；原 codec/core/storage/event
及空 package marker 五份字节不变，旧 source-library 的 15 节点包没有被替换。
交付摘要为 `a5df0a0649c69475fb47c9a532d76abc997e19df253ce1e15cece821551084a1`；
1,368 文件、30,146,560 字节归档摘要为
`39f5fa69acfebb60d054586d68512209892aab27a4e698a19bb0e28d18d4a470`。

七类保留旧测试接口，新增明确的 `_from_model` 消费同一 fresh Exchange；生产
`_from_bound` 仍先在真实 producer 缺失处拒绝。共享初始化核固定十四路、精确预载类、
原 guard/ledger/Exchange、MAIN/RUN、root 5、owned 3/4/5 与完整缓存字节；生产路径
不调用测试工厂，不重建 Exchange，没有注册回调或允许开关。B2 生产 gate 位于字段
读取及 fstat5 之前；后续代码保留父原 expected tuple，不以当前 stat 刷新授权基准。

原十九处内部 `_for_test` 调用已替换为 lexical scope 消费。继承 root 5 与原
checked_root 打开的内部 root FD 明确区分；root/window 当前登记在底层关闭前撤销。
B1 保留原 active/owns/目录身份、九字段 StableRead 和创建 FD 捕获，四种固定 creator
消费同一 scope。helper 在预检 scope 退出后另开自己的 scope，提前 FINISH 后仅做
纯值及 ACK 工作。同号 FD 复用不复活已退出 scope；任意外部 close/regrant 与任意
Python 私有字段修改不在该模型保证内，精确模块对象检查不构成来源认证或反射沙箱。

独立实际反例修复包括：B3-BIND-001 的撤销异常覆盖主因、B3-BIND-002 的 helper
构造漏 failed latch，以及 B3-BIND-003 的新 claim 入口异常未结束已接管 FD。
公共 catch 现保留主因并用原 ledger.finish 收尾全部已知 FD，不重试 unknown。
原回归另发现重复调用错误族被 BindingError 提前替换，已恢复原 ledger.active 顺序。
三项 P2 均 fixed_verified；原反例、兼容失败、修订源码和工具失败全部保留。

最终十组选定原测试 1,257 项通过，其中根执行的四包为 87/129/169/85，共 470 项；
作者新增 90 项通过，源码行异常注入和 42 项入口异常控制包含在该数量内。
原 17 成功、8 失败及六项部分写入后异常场景，在旧入口和新模型入口两路均通过；
业务字段及 31 组模型调用记录与原基线完全相同。新模型工厂的 94 次调用均保留原
Exchange，工厂内没有执行 prepare_exchange 本体。这些都是宿主模型记录，不是
真实 syscall/FD、Linux 时限或父 accepted 的证明。
根回归报告摘要为 `ed0d04979f8b6ccd5f3d11ac07ed83bb40bc38999103250ca60c8b531003acb0`；
720 文件、27,299,840 字节归档摘要为
`29dbe2419decf7631641b85dc41d8541ef8fd3e7ab67c668487bede6ef3a8baf`。

清单补查发现另八项 MemoryFS 测试仍调用旧 native fixture 私有入口，原样执行均
TypeError，不能把上述 1,257 项称作全部宿主测试。另版纯测试适配保持原八项断言
字节及旧 B1 acquisition 函数体，限定精确 CreateFS、两条路径与 flags；八项及额外
23 项控制通过，原真实 native fixture 没有迁移或执行。测试 helper 的全局后端仅
用于顺序模型，不支持并发切换不同 FS。三个生成源的导入排序问题由独立质量续件
修正生成步骤；旧主包保持冻结，不能宣称其所有历史生成文件都通过格式检查。
`runner-quiet-host-fixture-v1-candidate` 交付摘要为
`a3999aa3255b6fec8f8a93b8758760aebd4df090a5e593b4bf3b986d7a8792c8`；
112 文件归档摘要为 `b5d4dd7602c7ea9bd528f701c44aed94c325fcc53c0aed22043593c5aff1f019`。
续件三生成源与生成器在固定 cwd 的显式隔离 Ruff/format 下通过，16 份运行库源码字节不变。

非作者审查完成 82 项消费者控制、90 项作者用例重跑、原/适配八场景完整调用比较、
八项独立 acquisition 控制及续件 31 项重跑；各数量分列，不累加重复执行。原十五
模块的直接 os 调用 AST 保留；根协作编写的四事务由该审查者独立复读，原业务调用
顺序与全部原 p.need 谓词保序保留。根回归不冒充这四源的非作者代码审查。
独立回执摘要为 `c8cfe083b65be60ef669ca02c280345835c2161c88930959e9f562546639ef59`；
356 文件、37,918,720 字节归档摘要为
`2c56b7ce4d7a6df27745d102d578dd7ea9c6a91849fed3eb8f8245393cf2dc29`。

本批只读复查私有试点 HEAD 为 `aa283bde5e1b0aa99cd5ca1b1c817a069488099c`，有两项
未提交改动，未建立交接；本机未见 QEMU 或预期端口监听，未联系 guest 或沿用旧 boot。
只读记录摘要为 `1d6dcab01de6c37777119e034fdcd2234484966f3848c06bfa5fcf681351bfd0`。
目标仓保持只读。本仓仅追加本记录，不重跑或宣称新的全仓 Gate；原质量阈值不变。
真实 producer、raw owner/EOF/source/preload、可发行 child、C/D/E/F、G2/G3、原 Linux
600 秒验收、目标采用及服务/重启回执仍未完成，TASK-0048 仍缺 implementation_result。

## 十六模块源码库的重建与文件模型复验

`runner-quiet-source-bundle-v2-candidate` 将上一批 16 份运行源码的全部 256,579 字节
纳入另版固定库；builder 与 v1 字节相同，loader 的完整 AST 差分只有增加 binding
模块名和直接 stdlib `types` 两个闭集项。源字节、事务算法及生产拒绝入口均未修改。
交付摘要为 `008a4900283b1358f71265175a4b74df39d0c979d685ac07ca53658eada9489f`；
63 文件、4,853,760 字节归档摘要为
`eb0038de7865b3b1c008d8591677ced62e4f577b30005fae766ed89263dcf0a1`。
活跃 build-003 的单文件库为 352,581 字节，摘要
`a73181a7be2b21cbacac60c275a4650af8209409efc05a93660da4963a8cf098`。

作者 32 项原装载测试适配加六项新增控制，共 38 项通过，Ruff/format 及来源检查通过。
根独立回读三个来源包全部文件与归档，正反输入重建字节相同；七项坏构建输入均拒绝。
另六个隔离进程核对 binding/B2/B1 占名及缓存替换拒绝，没有重建实例或回落到磁盘。
原 107 处 import 保留，B1 两处反向查找仍依赖预载的原 B2；部分装载不代表 READY。

根在仅有单文件应用库及原测试夹具的隔离进程中，经旧/模型两路分别运行原 17 成功、
八失败及六项部分写入后异常场景。完整报告、singleton 源摘要及 31 组调用记录均与
固定未打包版本完全相同；模型 94 次工厂调用保留原 Exchange，内部 prepare 本体调用为零。
仅将夹具的源码身份读取改用库内原 bytes，并保留已审的一个模型工厂适配点；没有改业务
算法。加载与十四个生产拒绝入口期间所拦截的宿主文件 API 调用为零，不代表完整原生追踪。
根独立审查只覆盖本次打包差分和组合行为，不冒充先前协作编写四事务的非作者源码审查。
审查回执摘要为 `cbfaf40a997942520b03f9ac4a6911a984d1cc746f20a559e2102ea4e5c3e614`；
104 文件、5,509,120 字节归档摘要为
`c80e61560c3665fe8d86739e60d53a82cb21170bb2def5e9f2f5572cf1d6e4b5`。

build-002 与 build-003 库字节相同；生成工具 import 排序修订只更新外置来源清单。
原 I001、根审查工具格式失败及对应源码均保留，不重复计入已经通过的行为执行次数。
最早 raw-owner 片段正另行实现和独立审查，本库尚未接入它。真实 producer/admission/
child、source4/真实 EOF/预载 profile、C/D/E/F、G2/G3 和 Linux 验收仍未完成。
目标仓继续只读，本批未运行 guest、VM、服务、CI 或新的全仓 Gate，未填 implementation_result。

## 最早继承 FD 所有权片段的实现与异常复验

`runner-quiet-entry-prelude-v1-candidate` 新增实际可内联的 Python 源片段，以
`io_entry_prelude.py.txt` 保存原 bytes，避免当作独立 child 运行或普通库导入。
当前已复验源为 9,345 字节，摘要
`b7dcb9781ef8746d76a7a6b22b18cbf58e0d24ceeca09266a0a30b49c221086b`。
候选交付摘要为 `cf84ee14eec1296475fef1449531a1cf9cdaa9bc4b2cdbd82a3ff708ad42226d`；
58 文件、788,480 字节归档摘要为
`18ff3f1483e8f398eae8ba873af3daa428059676c84fb7f48e5db2146564adfc`，已逐项回读。
片段仅依赖后续受核的内建 sys/posix，保存固定 3/4/5/6 单例 owner；不接受调用者 FD
列表、class、callback 或启用布尔，不写 READY/ACK，不读取、打开或 stat 卷路径。
真实解释器、内建模块与受信预载来源仍是未实现的外部前提，名称和类型检查不认证来源。

移交在内部新建精确原 B1 的 fresh 空账本，按 3→4→5 先登记 TRANSFERRING，再 own，
成功后 TRANSFERRED；6 独立保留。own 前后中断时核原账本归属，判定不明的槽不猜 close。
每个 known 槽独立尝试收尾，先标关闭进度，unknown 不重试，也不因同号 FD 复用而重关。
失败收尾不调用可能遍历归属不明槽的 bulk FINISH；原账本置 failed，正常事务的 FINISH
仍由原 B1 生命周期完成。raw 关闭结果不能代替 stdout/stderr EOF、进程退出或父接受。

独立反例证实并修复两个 P2：ENTRY-PRELUDE-001 的 posix 可用后初始化异常跳过清理，
以及 ENTRY-PRELUDE-002 的终态登记中断阻断独立关闭、最终退出路径丢失最早主因。
现有固定槽表可用时，class/owner 初始化失败有有限清理后固定非零退出；首受控状态或
posix 尚不可用、清理无法推进等情形仍由真实父 C 保留 unknown，不宣称无限中断下必完成。
追加定点检查还发现 B1.failed 单次登记中断后可保持 false；末尾只补内存登记，实际原
B1.active 现拒绝失败账本，不重试任何 FD 关闭。

作者 179 项宿主测试通过。非作者 77 项控制通过，另以定点观察核 failed/active 和单次
关闭；不将重复执行相加。原 B1 own/close 算法与片段精确字节运行于显式 fake sys/posix
模型，未调用真实 posix.close 或执行 Linux。完整 Ruff/format 通过，独立检查另以 Python
源码 stdin 文件名解析 .txt 原字节；早期 E501 忽略记录不算最终完整质量通过。
两个 P2 的最终独立状态均为 fixed_verified；回执摘要为
`28910e965ec5bec0e94dc972167b50ab7132077e82ea292d5c4e241fd24a6f49`。
独立审查 57 文件、798,720 字节归档摘要为
`8e6e32999b79a570af8d867f985fb0dbf492b3308a1ceaa5c4a57e88b12580e0`，已逐项回读。
最早两源、latch 反例及工具字符串/AST 检查误报均保留；最终源码未因工具修订而重跑冒计。
下一依赖审计 `c1-next-implementation-review-001` 固定 19 文件，manifest 摘要为
`47639d1bacfd798280887fec8f1d49e847dade934d509beadfb3559169fb60e2`，不以本片段代替
真实 producer；后续生产 context/scope 必须另版实现，不能仅打开 require 门或借用 Synthetic。
源码仍未内联入可发行镜像，admission、生产 registry/scope、DATA 真 EOF、父 birth/pump、
C/D/E/F、G2/G3 与原 Linux 验收继续待完成。目标仓、guest、VM、服务与 CI 均未操作。

## 冻结入口与模块库的宿主组合检查

`entry-library-composition-root-001` 将上一阶段的精确 b7dc 入口和 a731 模块库放进同一
显式测试 namespace，未改两个运行时源。每项使用新的 Windows Python 3.11.9 隔离进程，
prelude 读取 fake sys/posix 与合成 3.12 profile；预载使用真实冻结的 16 模块，并核原
owner、原 B1 class 和固定 3/4/5 移交。仅将该 B1 模块的本地 os 绑定到 fake provider，
没有修改真实 os 或关闭宿主 FD。正常模型顺序为 close 6，再由原 B1 FINISH 关闭 3/4/5。

16 项不同控制通过：正常移交 1 项、原库 SOURCE_LIBRARY_ONLY 拒绝 1 项、binding/B2
预占碰撞 2 项，以及 stdlib import、quiet_core compile/exec、原 B1 constructor 四处
分别注入 OSError/KeyboardInterrupt/SystemExit 的 12 项。异常保留同一首 primary，
已知槽逐一清理且不重复关闭；库编译/执行失败保留原 partial module，禁止重试预载。
第二 agent 只读检查后补强两项碰撞的精确首错误和原占位对象 identity，定点复验通过；
原执行保留，复验不相加计数。两个审查工具的完整 Ruff/format 通过。

这里在库失败后调用原 owner.fail_and_exit 的接线仍由测试提供，尚未写入生产入口；
普通库测试 namespace 和合成平台也不能认证实际 argv、内建模块或源 FD。
该结果只核既有片段的组合兼容性，不代表实现了 assembler、child 或新的生产发行者。
57 文件、481,280 字节归档已逐项回读，manifest 摘要为
`1501b17044d0d040e21ff274d3a2039104af569954dd5c20cbe1edc4f9f3e6bb`，归档摘要为
`1c37baf38422961e16075fc9bd305eb16bf68550e3085e869118fbf9a7b5965c`。
DATA reader 正另行实现；time 新预载依赖、真实 EOF、admission、生产 scope、父 birth/pump
及原 Linux 验收仍未完成。本批没有目标仓写入、guest/VM/服务/CI 操作或新的全仓 Gate。

## 固定 FD3 DATA reader 的实现与失败路径复验

`runner-quiet-data-reader-v1-candidate` 新增同原入口 namespace 的实际源码片段
`io_data_reader.py.txt`，11,021 字节，摘要为
`f2ab255a9a7138752e4b75ba9491d96066a03fa5d6634fb66f3ea4f5b6a9b421`。
begin 先消耗一次尝试，再严格解码 request/v3，并保留原 owner/ledger 与完整 transport
承诺。固定 argv 是组件输入；格式正确不证明真实进程 argv、启动 flags 或控制来源。
借用只认原 transferred 3/4/5 和本地已关闭的 READY6，不补造 READY 或父接受。

step 每次至多一次 read(3)，上限 min(16KiB, N+1-used)，N 为完整 transport_bytes，
并非 payload 的 data_bytes。EAGAIN 保留同一 buffer 和期限；读满 N 后仍须由原 read
返回空 bytes，下一读最多探一字节。短 EOF、多余字节、错误类型、摘要或完整 codec
检查失败均永久终结；成功也只允许一次取出普通 bytes，不发行 CompleteDataRead/Exchange。
get_blocking(3) 拒绝阻塞模式，不改 flags、不触 FD5；瞬时 flags 和数字所有权仍不能
证明原 OFD 的连续身份。原两种绝对截止时间在读取/EAGAIN、摘要/解析及 take 后复核，
不新建 100ms 或 30s 预算。time 为新增的未来预载依赖，缺失即失败，无导入回落；
既有 16 模块库预载通过不代表目标 time/解释器已核。

独立 DATA-READER-001/P2 发现故障处理入口的一次中断会留下可读状态；进一步复现原
owner.abort 调用点中断会留下 active 账本。修复在 begin/step/take 的调用边界增加
有限后备失败登记和原 owner 清理，保留首 primary，不重复 unknown FD，不调用 B1 FINISH。
原 d5c、首修 de36、作者 run-002 的 9 失败/93 通过及独立反例均保留；这些失败和复验
不相加计数，也不宣称清理在无限重复中断下仍能完成。

固定 f2ab 源的作者 102 项宿主控制通过。独立 72 项不同控制通过：51 项流/EOF/时钟
控制，加 18 项三调用边界、两清理入口、三异常的组合，以及 3 项 unknown close 控制。
65536/65537 字节边界样本只用于有界拒绝，未作为合法业务 transport 成功。
完整 Ruff/format 通过，另以 .py stdin 文件名解析原 .txt 字节。全部运行于 Windows
Python 3.11.9 与显式 fake sys/posix/time，实际使用原冻结 prelude、16 模块库及 codec；
没有真实 FD3 EOF、Linux syscall/时钟或卷访问的验收结论。

作者交付摘要 `6d33d5111301d2039b684f7ab4acfa5f3a92ab427c36244cb1865fe08e952c08`，
49 文件、5,109,760 字节归档摘要
`0fa3d6beccb87e84889cb5a05b7e65ef4d0bab8ba0147e6d9a27195cec706ef7`，已逐项回读。
独立 `data-reader-entry-contract-review-001` 回执摘要为
`34ac7f8f081e2f7cc4ab29181668a5c9e306ad9a533e32ab3e5ef85ffd479763`，
DATA-READER-001 的两处反例均为 fixed_verified，无新增未解决 Finding。
67 文件、2,201,600 字节归档已逐项回读；manifest 摘要为
`b03c4fc04937b99556534a06e0705064d6d7229a1b3cee3e904ef092101baf6d`，归档摘要为
`40923aa319cb96429d9638f28a9a28ff0047f9ddc6197133402a71e221ff29c0`。
固定镜像 assembler、实际 admission、生产 registry/scope、父 birth/pump 和原 Linux
验收仍待完成；本批未操作目标仓、guest、VM、服务或 CI，未填 implementation_result。

## 固定入口前缀组装与首次退出前清理

`runner-quiet-entry-assembler-v1-candidate` 实现纯字节 build_entry_prefix：只接受固定
b7dc/a731/f2ab 三个原组件，不接受路径、role、callback 或生产启用参数。实际输出
`entry-prefix.py.txt` 为 618,355 字节，摘要
`992e1a3ca3af6cc6522d6a936c6fb43d04c172cc9608d941ca0802d740076d5d`。
原 prelude 是 byte-zero 前缀；库和 reader 作为精确 bytes literal 嵌入并执行，解码
字节不变。库装载到固定私有 ModuleType，入口自身 __name__ 不改；原库作为脚本运行
的 SOURCE_LIBRARY_ONLY 拒绝保持，正常内部库装载不开放其生产门。

准备行为实际预载 16 模块、核原私有模块实例、装载所需 time 接口，并在原入口
namespace 安装 reader。成功仍为原 owner RAW3/4/5/6、没有 B1 ledger、reader NEW；
不自动 transfer、不关闭6、不读 DATA，不输出 READY/ACK。完整未来模块图及目标
stdlib/profile 尚未到位，按原设计应在这些前提满足后才移交。该前缀是后续完整
child 组装可复用的部件，尚非可发行 child、PreparedSourceImage 或业务准入。

独立 ENTRY-ASSEMBLY-001/P2 证明初稿仅在 fake_exit 抛出后才补做清理，首次 _exit
调用时仍是 RAW3456；修复先对原 abort 做有限后备尝试，再走原 fail_and_exit。
检查绑定第一次退出调用之前的 known 槽状态，不用模拟退出后的补救冒充真实收尾。
ENTRY-ASSEMBLY-002/P2 证明首修未拒绝缺失或不可调用的 time 时钟接口及模块引用
不一致；当前同一原模块/所需接口不匹配即失败。接口结构通过仍不认证真实时钟。
原 b7dc 不改，早期两版及反例保留；两个缺陷均在组装层修复。

当前 build-002 的作者 50 项宿主控制、非作者 44 项控制通过；后者为 38 项准备、碰撞、
替换、编译/执行/导入、时钟接口及未知关闭控制，加 6 项首次退出清理入口控制。
原失败与复验不相加；审查工具 SIM102 修订后的同源复跑也不加计数。完整 Ruff/format
通过，生成前缀另以 .py stdin 文件名按原字节检查。宿主仍为 Windows Python 3.11.9，
sys/posix/time 的实际运行控制使用明确模型，未验证 Linux、真实 FD 或目标 stdlib。

根独立重建两种输入顺序，prefix 和 index 均逐字节相同；六段连续覆盖全部输出，
原三个组件、16 模块的 256,579 字节和 107 处导入位置均一致，七类非法输入拒绝。
旁置 artifact-index 为 19,687 字节，摘要
`3569f315891507f61c0706b9ca5acc29b7a835f112a1b1161aa6d9074683e2e2`；另明确绑定
原库 builder/loader/input table/preparation tool/build manifest 五层构建来源。
index 含输出 SHA 和段范围，不嵌入 prefix；外置 receipt 再绑定 index、prefix 和
构建工具，因此无自哈希环。它不是最终生产 source_manifest，也不能回写自身摘要
到 prefix 后继续使用旧 index 或拿片段清单替代完整来源链。

作者交付摘要 `9d13f4c946f4362aa49d1cb30015dc0f35af5ee589024981ea056d0e5aba1fb0`，
78 文件、4,034,560 字节归档摘要
`030ec9a2dbbce36fdd7672ef063780d8b77ee934557e8a772de035f644ad1928`，已逐项回读。
独立审查回执摘要为
`aecdaab61a05e1b7eb5c0d95dd1f124062878d25ee013cf2c4b9315c23895ef4`；两项 Finding
均为 fixed_verified。245 文件、3,676,160 字节归档已逐项回读，manifest 摘要为
`3a04d1b73a71f9cf0a55bd30c0d5d399cfe634b712f6021385864003176692f4`，归档摘要为
`0ef99323e062db5e383fc5ec856445c4ec406ae5a0f05dbd98e55fc7c827ee92`。
根重建审查另封存 40 文件、1,198,080 字节归档，manifest 摘要为
`b3d80ba9a97af3f93f2a456dbfd7b4f1c5700d49a7f156a3150d2e276b55d051`，归档摘要为
`6f190d0afc9f51e5880cb6cadcbc6f855a9e62a844e32131c67536d2c7bd5762`；文件与归档回读通过。
该审查同时绑定先行 contract 的 34 文件封存包，manifest 摘要为
`3d4b255cfef6f9a08bc48d59e5958593209f2ab428d85d3530194baec055d224`。

完整镜像和实际来源准入、生产 registry/dispatcher、READY/ACK、父 birth/pump 与
Linux/目标采用仍未完成。本批继续只读候选准备，未运行新的全仓 Gate 或记录实现完成。

## 固定继承输入观察器与原实例校验

`runner-quiet-entry-observer-v1-candidate` 新增同入口片段 `io_entry_observer.py.txt`。
最终片段为 14,847 字节，摘要
`cbd8fe30c1d56d1c2fe39266fc3037fa0a22d746b21810a8d18f775a26ca8929`。
唯一 `_ENTRY_OBSERVER.observe_once()` 无外部参数，从解释器 orig_argv 取固定七项，
先核类型、ASCII 和含 NUL 的 4KiB 总预算，再与实际三项 script argv 对照并交原 codec。
它使用 request 中已有的两种绝对截止时间，不另起 30 秒或 100ms 窗口。

实际算法检查四项 UID/GID 为 root，PID/PPID/PGID 与原请求对应；只对 FD3/4 做 fstat
和 fcntl。FD3 为 FIFO、status=2048，FD4 为 regular、status=32768，二者 F_GETFD=0，
source4 的 seal 精确为 15，dev/ino 不同。成功前再读身份和两 FD 的同组属性，变化即拒绝。
正常返回的观察调用前后核原配对时钟，倒退、错误编号、等于或越过截止均失败；异常
则立即保留首因并清理已知原始资源，不把错误清理时延或 guardian 预算写成已验证。

首次观察前不可逆进入 OBSERVING，成功仅返回普通观察值并进入 OBSERVED；再次调用
拒绝。成功仍为同一个 owner RAW3/4/5/6、无 B1 ledger、reader NEW，没有 DATA 读取、
READY/ACK、事务、transfer 或 FD5 元数据访问。其失败路径复用原 owner 的有限清理，
未知 close 不重试数字；非原始 receiver 的拒绝不能取得原 owner 的清理资格。

独立 ENTRY-OBSERVER-001/P2 证明首稿接纳同类型模块替换，甚至替换 codec 后可放行
错误解释器参数；错误 CLOCK_BOOTTIME 编号 0/1 也被真正传给模型调用并返回成功。
修订绑定原库、codec、B2/B1、B2 持有的 fcntl 和原 time 引用，在观察期间反复核对，
固定时钟编号 7。ENTRY-OBSERVER-002/P2 证明空伪造 receiver 遮蔽原异常，而复制字段的
伪造 receiver 能关闭真正 RAW 资源；修订只允许原单例在公开操作失败时调用清理。
首稿、实际反例和各次质量失败均保留，旧 prelude/library/reader/prefix 字节不改。

最终同源作者 119 项测试和非作者 125 项控制通过，涵盖固定原请求、参数/元数据/身份
拒绝、逐调用到期、模块替换、非原 receiver、清理入口取消及未知 close。失败初稿和
修订复跑不相加；B904 修订只增加 `raise first from None`，保留首因并抑制次生异常链，
最终片段仍重新验证。宿主为 Windows Python 3.11.9，实际 syscall 使用明确模型；
生成片段另以 .py stdin 文件名接受完整 Ruff/format 检查，py312 解析不等于 Linux 执行。

作者交付摘要 `4332149023db971ffb558fbcfa031af0d01836c92e6799be9500c393b2ead295`，
67 文件、2,058,240 字节归档摘要
`e7655540d64d6fa73595a5493238a090c1622edcb2ff99293bf2c8af012a1198`，已逐项回读。
最终全部 10 份作者工具/测试源、6 份独立审查工具与根审查工具均通过完整 Ruff/format。
独立审查回执摘要为
`0b6a4aa78a3e66890d884ef47f2e60a3a8a9635970ba0d6ae5bffcd1aefd860b`，两项 P2 均为
fixed_verified，无未解决 Finding。77 文件、1,781,760 字节审查归档已逐项回读，manifest
摘要为 `e54c7be49f376d8a5e32cafc2f1c84e675ed82989bcfb494c120b3d4e48a81da`，归档摘要为
`022bd5110f5c33f13337d3233ddd9ca56c1fa828eb84ec8fbb41909075eeb36a`。
根审查另封存首稿与最终源码映射、接口核查和包绑定，12 文件、71,680 字节归档均回读
通过；manifest 摘要为 `f0be85a34205bfeedf912ecf3feddc4c96669bf6febe2ec498eddfe30b143c94`，
归档摘要为 `a00855c09c45064aae12a9631ab4205164a4b0c026051d87b80ad39891003281`。

这里的严格 status/seal 值只是待目标核定的固定候选 profile，额外 seal 也会被拒绝，
并非所有合法 Linux memfd 的通用规则。两次属性相同不证明原子观察或持续 OFD 身份；
尚未读取进程 start tick、boot、namespace/cgroup、完整 FD 表或 source4 内容，也未核定
source4 的文件 ownership/profile、完整来源清单和解释器/stdlib。控制帧本来不含完整
镜像 SHA 等事实，stage35 输出 index 不能填补这项缺口。ChildEntryState、完整来源准入、
生产 registry/dispatcher、父 birth/pump、真实 Linux 与目标采用继续未完成。
本批未写目标仓或运行 guest、VM、服务、CI、新的全仓 Gate，未填 implementation_result。

## 进程与 namespace 观察及 FD 表容量扫描

`runner-quiet-proc-observer-v1-candidate` 新增同入口片段 `io_proc_observer.py.txt`。
最终片段为 28,458 字节，摘要
`d7ed0e5990340fa01dac4351dbbc8665a642afd494de588c3f735276f3441ac4`。
唯一 `_ENTRY_PROC_OBSERVER.begin()/step()` 无调用者参数，只接续原 cbd8 观察器的
OBSERVED 状态、原 request、两种绝对截止时间和最后配对时钟；不重启观察器或刷新预算。

算法两轮读取自身与 guardian 的 stat/status/cgroup，以及 boot_id，核 PID、PPID、
进程组、start tick、单线程、四项 UID/GID、固定 guardian unit 和 boot。guardian 控制
只给 PID/tick，其 PPID/进程组只作跨轮稳定比较，不虚构额外控制字段。stat 的 comm
可含空格、括号和换行，选定字段从末尾 comm 边界定位。文件上限分别为 stat/cgroup
4096、status 8192、boot 37 字节，N+1 探测且必须取得真实 EOF；短读沿同一 FD 分段，
EAGAIN 与其他读取异常立即失败，不继承 DATA pipe 的等待重试规则。

十种固定 namespace 各比较自身与 guardian 的 dev/ino，并作第二轮复核，共 40 次
固定 namespace stat。缺项即拒绝，不动态缩短清单。临时 proc 文件使用独立原 B1
账本和 read 角色，FD0 是合法且正常的首次 open 结果，1..6 不得登记为临时资源。
临时文件前后 fstat 和关闭均在该原账本中完成；原 RAW3456 仍无 ledger，reader NEW，
没有 DATA/source4 内容读取、fstat5、业务事务、READY/ACK 或 transfer。

每轮临时文件全关后，按自身 status 的 FDSize 逐槽 F_GETFD。FDSize 是已分配的表
容量，不是当前打开数或 RLIMIT；每 step 至多一次 proc/FD 观察或临时 close，另有
原配对时钟检查。扫描只保留递增索引和继承资源位图，不设静态容量捷径，不枚举目录或
修改资源限制。只允许 1..6 存在且 descriptor flags 为 0；其余槽只有 EBADF 表示不存在。
第二轮扫描后再固定读取一次自身 status、核身份和容量、取 EOF 并关闭，才完成临时
账本并返回普通观察值。正常路径共 15 次临时打开与对应关闭，不增加第三轮扫描。

PROC-OBSERVER-001/P2 的实际反例在第二轮扫描末将容量 64 改为 128 并添加 FD100，
首稿仍按 64 返回 DONE；最终 status 回读修复该遗漏。PROC-OBSERVER-002/P2 的实际
反例在 open 返回时替换临时账本引用，虽被后续身份检查拒绝，已知 FD0 却留在替代
账本且未关闭；修订让获取、登记、读取和清理始终使用原账本。

PROC-OBSERVER-003/P2 涵盖两个已执行的取消窗口：旧组合在原 B1 close 入口取消后
可留下 finished 但仍 owned 的 FD0；中间修订在 closing 标记后、try 之前取消，又被
后续 finish 关闭该数字。最终组合将标记与原 close 放在同一保护范围，清理前后均
隔离 closing/owned 交集，保留首因并独立处理临时与 RAW 资源。未知关闭不重试；
实际模型可能仍有 FD0、零次 close 和 closing 未知记录，这属于失败，不能称成功释放。
原 B1、旧 prefix/library/entry observer/reader 字节均不改，初稿与失败记录继续保留。

最终同源作者 120 项 pytest 与非作者 98 项独立控制通过。作者三项测试中的 36 次
逐调用位置注入包含在 120 内；独立 98 为 85 项主控制加 13 项关闭/入口控制，旧反例和
复跑不重复计数。三项 P2 均为 fixed_verified，无未解决 Finding。宿主为 Windows
Python 3.11.9，实际调用使用明确 syscall 模型；py312 解析与质量检查不等于 Linux 执行。
最终作者 10 份工具/测试、独立审查 10 份工具和根审查工具通过完整 Ruff/format；实际
片段另以 .py stdin 文件名接受完整检查，未降低规则或忽略 E501。早期质量失败保留。

作者 delivery 摘要为
`4c866fbf6097608c30668a7562f8a263d63e448fc5be277bb41c75fa93ce8f52`，108 文件及
3,174,400 字节归档已逐项回读；归档摘要为
`606300b04ea758b45fc4873d4e4c3880c59ef3c66b19a2108f21fb67ae9f60df`。
独立审查回执摘要为
`6db2e54f8c795647957527833203f8de766b2c2d08a43fbe9567ad1e063260ed`；135 文件、
1,986,560 字节归档均回读通过，manifest 摘要为
`f54c587e1a6ec7304e008bd784d674603f3c68e8c02c0c5a95f9e63d0f566a54`，归档摘要为
`fb91d18be06e66c2b3325fd31696e3074bcc72eca75ac6e945755ad71a9c4546`。
根审查固定三版源码映射、来源核查、最终两包绑定及本阶段快照工具，25 文件、
184,320 字节归档均回读通过，manifest 摘要为
`d24708f9d337f1e2e6b8ae13af8703f6f3f925b1539965c96542fa6550d8f943`，归档摘要为
`7442bcba4e0daddab84b04f8b540f28ce8cd3b3aae6e1673c7d8980be74fa199`。

这些实际算法与宿主控制不认证 procfs、源镜像或目标 namespace/profile，也不证明
多次观察的原子性、线程期间不变或持续 OFD 身份。最终 status 不能发现同容量内已扫
位置的新 FD，或最终采样之后的变化。source4 内容/hash、完整镜像及解释器/stdlib
来源、生产 ChildEntryState/registry/dispatcher、父 birth/pump、真实 Linux 与采用
仍未完成。本批只读候选边界不变，未运行 guest、VM、服务、CI 或新的全仓 Gate，
未写目标仓、未填 implementation_result；TASK-0048 继续 IMPLEMENTING。

## 固定 FD4 流式摘要观察

`runner-quiet-source-observer-v1-candidate` 新增同入口 `io_source_observer.py.txt`，
最终 15,092 字节，摘要
`a0b329f5e8e700f9d2c2a736a4a2905b06702c75436bd2a475194ea5fb66a1d8`。
唯一 `_ENTRY_SOURCE_OBSERVER.begin()/step()` 无参，要求原 d7ed 观察器 DONE、其原临时
账本已完成且无失败/未知，原 RAW3456 无 ledger、reader NEW。它保留原 request、两种
绝对截止时间和 d7ed 的最后时钟值，另续时钟链；不重启或调用已终态观察器的 helper。

本次实际 fstat4 取得 regular、正数且在候选 signed 64-bit off_t 范围内的 size。
F_GETFL、F_GETFD、seals 分别要求 32768、0、15；读前和读后同组属性必须相等。
固定 `pread(4, min(16384, S+1-used), used)` 从偏移 0 分块，用原 codec 已预载的
hashlib.sha256 流式更新，不缓存完整镜像，也不把 DATA 的 64KiB 限额当作镜像上限。
每步最多一次 Python pread，另有摘要更新和时钟检查。短读按实际返回长度推进，
精确 S 字节之后仍须真实 EOF；短 EOF、额外字节、坏返回值或摘要/读取异常均失败。

成功只借用 FD4，不调用 open/dup/lseek/read 或接管/关闭它，也不复用已终结的临时账本。
原 hash 模块、构造器、哈希对象和其他入口引用在配对时钟前后复核；末次 metadata、
hexdigest、结果构造和时钟都在首因失败边界内。即使本观察器的 owner 别名被替换，
失败仍清理捕获的原 RAW owner；foreign receiver 无清理资格，未知 close 不重试数字。

这里的无重试指片段不会再次调用已抛出异常的 Python pread。CPython 3.12 的包装层
可能在 Python 信号检查不抛异常时内部重试 kernel EINTR，并释放 GIL；hashlib 的较大
更新也可能释放 GIL。因此模型中的一次 Python 调用不能证明一次内核调用、硬时限或
无异步变化；Python 可见 EINTR/EAGAIN 仍立即保留首因失败。

当前 request/v3 只有 source_manifest_sha256，完整 source_image_sha256 位于后续
pending.birth；stage35 detached index 只标识未完成的 prefix。新组件不接受 expected
SHA、不拿这些字段当作独立镜像预期，也不消费调用者保存的 cbd8 source4 结果字典。
输出只是本轮 size/SHA/metadata 普通观察值，未把 FD4 认证为实际执行中的完整程序。

作者最终 `run-002` 117 项测试通过，其中 3 项测试包含的 36 个异常注入位置不另加总。
独立审查在最终源码上 93/93 通过，覆盖短读/EOF、超过 64KiB 的镜像、偏移不变、
前后 metadata、原引用、构造/更新/摘要异常、末次时钟、foreign receiver 与未知关闭。
模型实际顺序执行 992e+cbd8+d7ed 前缀，FD4 内容刻意使用不同的合成字节；真实 hashlib
核对这些字节的摘要，不据此宣称它们就是执行镜像。d7ed 的 census 仍是 hash 之前的
观察，未补齐 READY 前所需的新鲜核查。

本轮未发现新的源码 Finding。独立初跑的 3 个失败来自审查断言误把单次 FD3 close
失败后的所有 FD 都要求为 UNKNOWN；修正后分别保留 FD3 UNKNOWN 和 FD4/5/6 CLOSED。
旧失败保留，后续同一矩阵的重复运行不累加。根保存初次可审源码 4ec9 与最终 a0b329，
确认两者只格式变化、AST 相同；该静态复核不代替行为矩阵。审查者未作者新观察器，
但曾作者旧冻结 library 依赖；本轮独立结论限于新组件，不是整个 prefix 的重新验收。

作者最终 10 个工具、独立审查 8 个工具及实际 `.txt` 源码通过完整 Ruff/format 检查；
根复核与快照工具也通过相应检查。实际运行仍是 Windows Python 3.11.9 和 syscall
模型，py312 质量检查不构成 Linux Python 3.12 执行。未复跑行为未变的旧矩阵或全仓 Gate。

作者 delivery 摘要为
`1ac9e755f1a8f07ef12138477a74768447217b897dbecb2566ff8b46b767a804`，60 文件及
2,324,480 字节归档逐项回读通过；归档摘要为
`5213fdc2bcd3d1f8ec17e7408ffbee092c36d6181cdf29fd82a7fa2ebb1eab74`。
独立审查回执摘要为
`c6a20bc2a6973cbb2d64a7eb3ed5abde0305a1fefa161f91c79819aee82576e0`；111 文件、
1,925,120 字节归档均回读通过，manifest 摘要为
`09d28d8506f193831e8333711f02552f46c0894e9635ce6006480b1f31e03560`，归档摘要为
`6d17faee7d0b24ae1a1571d498c559f02cc9a057efd95b156c60086bcbd4eebd`。
根复核固定两版源码映射、格式比较、两包绑定和本阶段快照工具，19 文件及
92,160 字节归档均回读通过，manifest 摘要为
`e9fce16b0e6a746139aa6dc42864db62c3a1202d21d92e76bcf64e51257f65de`，归档摘要为
`f40047a7afbe4130f43a1b6b40a75df932bee22dda1394801d4c75982386817d`。

独立完整镜像摘要的生产与核对、解释器/stdlib 来源、新鲜入口核查、生产 registry/
dispatcher、父 birth/pump、真实 Linux、runner/CI 采用及服务恢复/重启仍待完成。
本轮未发 READY、未读 DATA、未转移 RAW 所有权、未创建生产权限；目标仓保持只读。
未填 implementation_result；CLI 仍为 IMPLEMENTING，classification fresh、approvals
current、evidence not_available，不能将该观察组件的通过当作任务 02 完成或全仓 Gate。

## 父侧固定源码 seal 与读回准备

原 production binding 及 birth 设计要求父 C prepare 保留独立完整镜像摘要与只读 OFD，
在 READY 后结合实际 post-exec 来源比对子进程的观察。该职责不能倒置为 child 自证，
也不能用 pending.birth 的后续字段给当前 request/v3 补一个 expected SHA。

`runner-quiet-source-image-prepare-v1-candidate` 以固定 992e、618,355 字节的入口 prefix
实现这条资源链的候选算法。生成器核对原 assembler delivery、prefix、detached index
与 build receipt，再将字节嵌入运行源码；这些原产物明确为不完整入口，本轮不执行其中
程序。准备器不接 caller bytes、路径、FD、expected SHA 或认证开关；唯一预算输入为
`(monotonic_ns, boottime_ns)` 顺序的原绝对截止时间，不自行生成新 TTL。参数形状正确
不认证它来自实际 parent/holder 的原预算。

算法创建本次唯一 memfd，按实际短写长度分段写全，加入四项 seal，再只通过本次原 FD
的固定 proc 路径重新只读打开。新旧身份、size、status/descriptor flags、seals 与
完整 positional 读回、真实 EOF 和固定摘要均须核对；原写 FD 确认关闭后才保留只读 FD。
只读 FD 仍由原准备器持有并负责关闭，没有 child grant、exec 或所有权交接。

独立审查复现 P2 `SOURCE-PREPARE-001`：首稿在 begin 核完原字节后，后续仍信任可变
SIZE/SHA；把二者改为前 16,384 字节及其实际摘要，会只写入这个短文件，seal/只读 flags
均正确、原写 FD 已关闭，却错误进入 PREPARED。该主反例没有伪造 readback；另一个
对照显示错误 readback 在原 SHA 下被拒，但改变 SHA 后被接受。修复只在每次 `_borrow`
校验固定长度和摘要的精确类型与字面值，未新增 expected 参数或放松 profile。

最终运行源码 1,350,769 字节，摘要为
`16ba414ce15339879f0dea5da1321688f739ee556e45f778b1e0495d6eef9e34`；其中嵌入的 prefix
是数据。15,670 字节模板摘要为
`9df1f7a25c39bcd3655c1ff4152650b508bfd62e17924a6e087c193fc8c068bf`，生成器摘要为
`0e5db7c9090f7d00ace24ca6e2368175f230ce67ef5dddcc12cda5faa76eddc9`。根独立解码唯一
bytes.fromhex 赋值，核得原 618,355 字节/992e；删除该赋值后其余 AST 与模板完全一致。
实际运行源码接受完整 Ruff/format；模板的插入占位不被冒称为独立可执行或单独 lint
通过。初稿到格式稿的模板、生成器及运行源码均确认 AST 不变，修复另保留版本。

最终作者 `run-006` 122 项测试通过，3 项 pytest 内遍历的 276 个 I/O 异常位置已包含
在总数中；独立 122 项为 114 项主控制加 8 项尾部/FD/关闭控制，分别记录，不累加复跑。
两边均使用实际生成源码和真实 hashlib，文件及 FD 操作由各自隔离模型执行。
唯一 P2 已 fixed_verified，无新增 Finding；原失败与修复前后源码继续保留。
作者曾执行的 2 项失败回归、独立错误读回/真实截断反例、早期工具质量失败不被抹去。

注册中断疑点的实际 trace 仅触发首个位置，此时新 FD0 被关闭；没有把未触发的第二次
中断宣称为覆盖或缺陷。独立最终关闭控制另核到先标 CLOSING 后被取消时零次实际 close、
保留 UNKNOWN 且不重试数字。这个结果不等于资源已释放，也不承诺任意连续中断可恢复。
正常与失败调用的预算是 Python 层检查，不证明内核调用次数、硬时限或原生关闭延迟。

最终作者 10 个工具、独立审查 9 个工具、实际运行源码及根复核/快照工具的完整
Ruff/format 检查通过。作者 delivery 摘要为
`d5dbfe9121ce568d7249ee472356f9d7b8bb6ec55b6a8c37695e5e040493838a`，108 文件及
17,612,800 字节归档逐项回读通过，归档摘要为
`f4bc93e11e5aceecce1a878b399c1a00f475ec12498fe6f65331a67edfb30aa5`。
独立回执摘要为
`a3b51c74a359b80c4a3033ececf86961e77cc79ee89a6592b05ac79d51d44cee`；183 文件及
13,537,280 字节归档回读通过，manifest 摘要为
`f602e43b1947c627823d63e6fb147507a7a5e7ee85a5b13725af0693a75dbe5e`，归档摘要为
`26e8a507d7c004b3f9618008c74a7d07db4a2e0c9053aecfe254971a6ce1160b`。
根复核封存三版模板/生成器/运行源码、格式与字面量比较、两包绑定及快照工具；29 文件、
4,249,600 字节归档回读通过，manifest 摘要为
`18e4a86f47dec907321442ccc831a24a5184859dc5f5817ee294073e9dec0970`，归档摘要为
`fd69e19448a90ba9126e5a2d07f5d59e7745b41c0da64c48352ee11d44c0c8a8`。

实际宿主仍为 Windows Python 3.11.9；模型与 py312 静态检查不认证 Linux memfd、
procfs、解释器/stdlib 或真实父来源。完整 child 构建、PreparedSourceImage、父 birth/
post-exec/READY 与 DATA 绑定均未完成。后续 admission 还须解决旧 f2ab reader 从 argv
重新解码 request、另建 deadline tuple 且未续接入口最后时钟的接线缺口；本轮未改旧库。
未运行 native、guest、服务、CI 或新的全仓 Gate，目标仓仍只读，未填 implementation_result；
TASK-0048 继续 IMPLEMENTING，本批不构成任务 02、C/E/G3 或生产来源的完整验收。

## DATA 读取与原入口上下文接线

`runner-quiet-data-reader-v2-candidate` 补齐上一阶段指出的接线缺口：`begin()` 不接 argv，
不再次调用 decode_control_argv，也不重新生成 deadline。它继承原 entry/proc/source
观察器共同持有的 request、deadline 对象与 source 最后时钟，使用自己的借用及配对时钟
检查，不重新调用已经结束的观察器。固定 CLOCK_BOOTTIME 为精确整数 7；读取前后继续
核对原对象、模块、工厂、账本类型及资源所有权。

新 `runner-quiet-entry-assembler-v2-candidate` 从原 RAW prelude 的第零字节开始，顺序
安装固定 library、新 reader 及原 cbd8/d7ed/a0b329 三个观察器。三个观察器安装后、任何
观察开始前，固定无参调用 `_bind_loaded_observers_once()`，保存原实例与类引用。
所有安装和绑定仍处于原有限清理 wrapper 内。安装结束时 RAW 未转移、观察器均为 NEW，
没有发 READY 或读 DATA；它不是先执行旧 prefix 再替换旧 reader。

读取保留 16 KiB 单次上限、64 KiB transport 上限、N+1 溢出检查、真实 EOF、原摘要及
transport 解码。EAGAIN 11 返回 WAIT，其余可见异常失败；首因、有限清理、UNKNOWN 不按
数字重试的边界保持。成功只返回普通 bytes，不生产 CompleteDataRead 或其他 registry
权限。绑定 hook 只建立固定安装顺序下的引用边界，不认证安装前来源，也不证明任意可信
root 私有状态改写下的防护。

独立审查在新组装首稿 698994 上实际跑通正向链，并复现 P2 `DATA-V2-001`：7c26 在 DATA
开始前仅将 owner ledger 与其 class 相互核对，没有再绑定原 B1 class；替代类及账本映射
仍可返回完整 transport。作者自查补上原 class 引用比较，形成 4480，随后仅格式为 956f。
独立代理之后被平台内容检查中止，材料按 PARTIAL 封存。最终 reader、新 prefix、该修复
及独立工具完整质量检查尚未获得最终独立复验，不标作 fixed_verified。

当前运行源码 21,744 字节，摘要为
`956fe95a1af4186e4c47519067b1ca433f41f9f32cdda0bbb5c9c028e1f51504`。
新完整组装 prefix 为 735,690 字节，摘要为
`eb3ff1cb04b29e5fbf518586bfec21858d392ec5046c10d03ad118729bca1272`；这里的“完整组装”
仅表示本次六个固定输入已接线，不表示完整 child。每次 build 独立保留六个原输入、
builder 源码、detached index 与 receipt；初稿、失败和最终清单分别固定，不覆盖历史。

作者 `run-004` 共 115 项通过：98 项接口与流控制，加 17 项直接执行新完整 prefix 的
合法 transport 链；最终 14 个工具/测试文件及实际 reader 的完整 Ruff/format 通过。根的
32 项构建契约测试检查闭输入、原字节、顺序与安装边界，工具及实际 prefix 的完整
Ruff/format 通过。根另复用已保存的审查模型运行 17 种正向链，均返回原 transport，
保持原 request/deadline 与已关闭的临时账本，DATA 阶段未重新解码控制请求。这 17 项
是根执行审查者模型，不能替代独立审查；与作者测试分别记录，不累加成独立验收数量。

原始独立包保留 74 文件、7,270,400 字节归档；manifest 摘要为
`d768ca63c67170e07a8e46e97128235519ab0fc949f1fe15cb5d76c7355ab196`，归档摘要为
`c5131077bf1d59017872f8886a2f48f9444f481e0fa673d96be2d37d7ca0149b`。
根初次误录 reader 长度被闭输入检查拒绝，未产生 build；初次 wrapper 长行/F821 与工具
格式失败、作者 fixture 错误、独立早期模型适配错误均保留。安装 alias 疑点未完成实验，
不列为已复现 Finding。阶段 40 快照绑定最终候选包、PARTIAL 审查、根复核及本节提交。

最终 reader delivery 为
`365d887edbc10aef9a546cb465129e9196320b88f18cfc1c5382fa69ff302287`，90 文件；assembler
delivery 为 `cc1da1178b767a9fe550eb1d7199d35c0642ec9f8d94aa0b1dcc763bb6a5b323`，134 文件。
assembler `build-003` 固定全部六份最终输入 delivery，prefix 字节与已执行的 build-002
相同；`run-003` 的 32 项及 8 文件工具质量、实际 prefix 质量均通过。其 index 把 reader
实际 NEW 状态与已绑定观察器的布尔事实分开记录。根包 38 文件，manifest 为
`a81039d9e5284e93f0380771ab1cbe0e68e0db2a624393988ba65c37243fda6d`；四包本地文件与
归档逐项回读通过。根另核得 7c26 到 4480 只新增上述一项比较，4480 到 956f 的 AST
完全一致；该静态比较不替代行为复验。

模型显式调用原 owner 的 transfer_inputs/close_ready 后才开始 DATA。这不是实际 READY
frame 或父准入；原两方法没有配对时钟，source 末时钟到 DATA 首时钟只提供前后观察，
不证明 READY 期间逐操作预算或原生 FD 新鲜性。宿主仍为 Windows Python 3.11.9，使用
真实 hashlib 与隔离 I/O 模型；py312 是静态检查目标。旧 source-image preparer 仍嵌入
旧不完整 prefix，本轮没有将它静默改为新镜像。

最终独立复验、完整 child/来源准入、PreparedSourceImage、CompleteDataRead、父 birth/
READY/pump、真实 Linux 与 runner/CI、服务恢复及重启均未完成。目标仓保持只读，未运行
native 或新的全仓 Gate，未填写 implementation_result；TASK-0048 继续 IMPLEMENTING。

## READY 闭集帧与普通分块组装

原 birth/binding 设计规定 FD6 唯一 READY、完整帧不超过 4096 字节、父观察真实 EOF 后
再核 post-exec 来源，但没有给出 READY 的 schema 或字段表；旧 codec 的 operation_ready
是状态属性，不是出生帧。因此本批新增明确版本的纯协议，不把新字段说成旧合同已有。

`runner-quiet-ready-protocol-v1-candidate` 定义 `task02-quiet-io-ready/v1` 五个闭集字段：
schema、request_sha256、worker、source_image_sha256、source_image_bytes。worker 沿原
`identity(worker=True)`：PID/PGID 至少 2、start_tick 至少 1、PGID=PID，上界均为原
MAX_NS；源码字节数为精确整数 1..MAX_NS。请求摘要字段约定引用完整 canonical request，
codec 只核摘要形状；请求、源码摘要及长度的实际比较留给父侧。不新增 request/v3 字段，
也不自行核定真实进程或源码身份。

完整编码为 canonical JSON 加唯一 LF，4096 上限包含 LF。重复/额外键、坏类型、
非规范编码、坏 UTF-8、尾随对象或内容均拒绝。最大合法编码实测 349 字节：四个整数
取原 MAX_NS，两个摘要保持固定 64 字符，PGID=PID；没有为新帧增加预算。模块 1263 字节，
摘要为 `179dabf661537d248342d810559510f468cd8d9da547dcb69bf45beaee3ef5d7`。

`runner-quiet-ready-buffer-v1-candidate` 提供普通 `append(bytes)` / `finish_claim()`：
每个非空精确 bytes 片段先核剩余容量再复制，累计不超过 4096；收到末尾 LF 仍只处于
COLLECTING，显式完成后才一次返回普通 dict。非法输入、重复完成或解码失败保留首因。
它不收 EOF 布尔，不读管道、不看时钟，也不产生权限；调用 finish_claim 不证明实际
EOF。未来 collector 必须从原管道独立观察 EOF，并遵守原共享 16 KiB/100 ms、绝对
截止及关闭记录。缓冲模块 2010 字节，摘要为
`e86877a6d6550bcf21de0e3495ba125e1b22e406f872837bd10ae31ab242965b`。

codec 作者 83 项普通序列化测试通过，17 组原合法 fixture 的 READY 可编码，原 request
argv、transport、ACK 与 pending 编码前后逐字节相同；10 个新源码文件完整质量检查
通过。根缓冲组件 89 项通过，覆盖 17 组请求的四种分块、单帧所有双段切分位置、类型、
预算、截断/额外内容及一次完成；切分循环包含在测试数内，不另加总。6 个工具/测试
文件与实际缓冲源码完整 Ruff/format 通过。根初次把 scenario.rows 误读为顶层 rows 的
收集错误、初次风格失败与作者初次工具风格失败均保留；两个运行模块未因这些问题改写。

独立工作仅核对原合同、新 schema 与两组件静态接口，不执行新组件，也不替代行为或
Linux 验收。源码依赖仍为固定原 codec/core/storage/event 四份纯文件；没有加载 B1/B2
或调用文件事务。旧 source bundle、入口 prefix 与 source-image preparer 没有重新接线。

codec delivery 为 `41378002c35f9795a792420b2a608d87d33ea223235c5bdf0f6acf6d454e9ae7`，
40 文件、1,423,360 字节归档；buffer delivery 为
`8b1193392fb2f35a0f94f81b3c7cc571b6405260fc1fc035d6b9e3075fa5c454`，77 文件、
1,105,920 字节归档。独立静态审查 manifest 为
`c6b5aa24bae01bde6366efa7ae2ab54eeae2cc018372b5513b22a1976458fd9c`，63 文件、296,960
字节归档；其 4 个自有工具质量检查通过。三包本地与归档逐项回读通过，阶段 41 快照
绑定三包、本节提交、当前 CLI 状态与前一阶段快照，不将这些字节证明转成原生验收。

实际 READY writer、原管道 collector/EOF、FD6 关闭、父 post-exec 比对和 DATA 放行仍待
完成。阶段 40 的独立复验缺口继续保留。本轮未运行 native、guest、服务、runner/CI 或
新的全仓 Gate；目标仓仍只读，未填 implementation_result，TASK-0048 继续 IMPLEMENTING。

## READY 写出、关闭与 DATA 时钟接续

本批补齐树外 READY sender 候选、DATA reader v3 和八输入 assembler v3。新完整前缀
在宿主模型中依次执行原 entry/proc/source 观察，再由 sender 调用原 owner 的
transfer_inputs，经固定 posix.write(6, ...) 写出 READY，再调用原 owner 的 close_ready，
最后由 reader 读取 DATA；不再由模型代办转移和关闭。成功仅说明候选的普通 IPC 链
跑通，不表示完整 child 或父侧准入。

sender 固定原观察器、reader、library、codec、B1 与 READY module 引用。begin/step
均无参；由原 source hasher 的摘要、实际长度、同一 request 的 canonical 摘要和 worker
形成五字段 READY。转移后保留原方法返回的唯一账本；FD6 写前、写后核 FIFO 的
mode/dev/ino、状态 flags 2049 与 descriptor flags 0。它不要求管道 st_size=0，也不从
uid/gid/nlink 推导管道身份。完整帧仍最多 4096 字节，单次 write 最多 16 KiB；短写
推进、EAGAIN 11 等待，其余可见错误和非法计数失败。已知关闭 6 后进入 SENT_CLOSED，
原账本保留 3/4/5；关闭异常保持 UNKNOWN，不按数字重试或算作释放成功。

sender 从 source 的原末时钟继续，在成功返回的观察、写入及原 transfer/close 调用
前后检查原绝对截止和配对时钟；EAGAIN 等待前也检查，其余可见异常立即保留首因清理。
reader v3 在固定安装时绑定原 sender，开始 DATA 时要求它已达
SENT_CLOSED、同一 request/deadline、同一 transfer 返回账本，并继承 READY 最后时钟。
原 source→READY→DATA 引用链分别核对，不复用终态观察器或 sender 的时钟方法。
八处精确替换从冻结 v2 重建出实际 v3 字节；仅四个上下文方法改变，原时钟、DATA 循环、
transport 提取及清理方法 AST 不变。公共 API、16 KiB/64 KiB、摘要和 EOF 条件不变。

assembler 从 byte zero 安装 RAW prelude 和原 16 模块库，再安装新增私有 READY module、
reader、三观察器、sender，最后一次绑定 reader。READY module 明确列入新 detached index，
只依赖原预加载 codec；没有静默改写旧 library manifest。全部仍在原有限清理 wrapper
内，安装结束保持 RAW、观察器及 sender 为 NEW，未观察、转移、写 READY 或读 DATA。
三个 build 的执行前缀字节相同；build-003 固定全部八份最终输入 delivery。

sender 源码为 18,019 字节，摘要
`141caf3b421504a0feb7fafe559c4c45034a04e03b663f55fef19c8626d79c17`；reader 为 22,602 字节，
摘要 `0ed86e82ff27db06136d1a192dd793e9d1b294289e0224ec693d3d41591c59a1`；新前缀为
770,814 字节，摘要 `5ae8197f786e7a1af5d10e8ba7a41214e0556d207f4ea90a94b13da476ec65d2`。
build-003 index 为 24,844 字节，摘要
`d3d43a62339d5534e3c9477628601fda9e7ce52771800b65b458a4810a51f7bd`。

作者 57 项普通 sender 测试通过；48 个固定调用前后异常场景已包含在其中六项内，不
另加总。构建器 40 项契约测试通过。独立常规集成 42 项通过：17 个原 transport 请求，
加 25 个短写、EAGAIN、非法返回、可见异常、截止、时钟与 DATA 边界。正常模型将
实际输出与独立组装的 canonical JSON+LF 比较，17 帧均为 294 字节；核实际整前缀的
SHA/长度、原 request/worker、仅关闭 6、保留原 3/4/5 账本及 15 次临时获取均已关闭。
DATA 未重新解码控制请求，未调用终态 sender 时钟；后续模型销毁的关闭单独记录。

独立时钟用例 source=(5,8)、READY=(20,30)、DATA=(21,31) 成功；DATA=(10,15) 虽晚于
source，仍因早于 READY 而以 clock_reversed 拒绝。该用例补充普通时钟接续证据，不
证明原生阻塞、调度、EINTR 重试或实际清理的硬时限。独立审查者未实现这三个新组件，
但曾实现部分旧 library 依赖，因此本次只声明普通 IPC 集成审查，不声明整个历史前缀
重新独立验收，也不补回或关闭阶段 40 的 PARTIAL 审查。

作者 13 个新工具、reader 4 个工具、assembler 8 个工具/测试、独立审查 10 个工具均通过
完整 Ruff/format；实际 reader/sender/prefix 以 py312 静态目标检查通过。根 3 个汇总工具
及实际快照工具通过相同完整规则。根只回读和核对既有测试证据，没有再计一次行为测试。
作者曾把两个时钟分开推进，独立首轮曾误以 348 字节分块必然短写 294 字节帧；这些
fixture 错误、初次工具质量失败及其修正均保留，未列为运行源码 Finding。根对格式调整
核得 AST 等价；最终清单固定实际执行源码和检查源码之间的关系。

| 交付包 | 最终 manifest/delivery SHA256 | 文件数 / 归档字节数 |
| --- | --- | --- |
| READY sender v1 | `23bf536ffb874a6e39ebf5f88b797fc44b5cfc9faccec845a098af17fe1435df` | 74 / 2,938,880 |
| DATA reader v3 | `cdd61417a3f9dba4cd3f8fcb0000c44ac70faa695c82852d1fadfe7e92e07474` | 51 / 460,800 |
| Entry assembler v3 | `26be0e3af1a92eb9fb76141f4d511859181abec40fdf0821c80a3dcbdbbce74f` | 150 / 6,727,680 |
| 独立普通集成审查 | `34ffa6bd96cade9ff7613afa9f6799d3c22d53d267be673cf0162798f5bbae9d` | 182 / 2,682,880 |
| 根证据汇总 | `33297c12e9e63836d4b238139e3130e51fbcbafe18d73c5b61aeb4038ce65357` | 52 / 409,600 |

五包本地文件及归档成员、全部八份输入包逐项回读通过。阶段 42 快照绑定这些交付、
本节提交、当前 CLI 状态与阶段 41 快照。宿主仍为 Windows Python 3.11.9，使用真实
hashlib 与隔离 I/O/进程/时钟模型。旧 source-image preparer 仍嵌入旧不完整前缀。

真实 READY collector/EOF、父 post-exec 比对、来源准入与 DATA 放行、完整 child、ACK/
退出收束、PreparedSourceImage、CompleteDataRead、实际 Linux、runner/CI、服务恢复及
重启仍待完成。未运行新的全仓 Gate，目标仓仍只读，未填 implementation_result；
TASK-0048 继续 IMPLEMENTING。

## 父步骤共享预算与 READY 接收候选

本批新增树外 ParentStepBudget v1 与 READY collector v1，并用阶段 42 实际 sender
输出完成一次独立普通模型组合。预算对象与接收算法已实现；父侧实际 pipe issuer、
完整调度器和旧 pump 接线仍缺失。宿主模型结果不证明实际父 EOF 或来源准入。

ParentStepBudget 保留原 deadline、前一步 tail 的 tuple 引用及原时钟函数。父同一步的
所有组件共用 16,384 字节和 100 ms；实际返回字节先 charge，超额仍保留实际计数。
monotonic 的 100 ms 边界可达，两项原绝对截止不可达；boottime 不改成新的 TTL。
父最后调用一次 finish_step，即使步骤已失败也取末时钟，并保留此前组件首因。
后一步必须接续原 tail 和同一 deadline；普通输入 tuple 本身不证明截止来源。

collector 公共构造拒绝，只有明确的 _for_model 接受模型已拥有的父读端、原 FIFO
dev/ino、预期五字段 claim 和 child deadline。它使用固定 os/fcntl/time 模型执行实际
检查与读取算法；没有可选择的生产适配器。父读端 FD 独立持有，不固定为 child FD6；
读取 flags 2048、descriptor flags 1 是本候选 profile，其中父 CLOEXEC=1 是新增假设，
尚非 birth 事实。
模型工厂接收已拥有 FD 后的参数失败清理属于模型 setup 边界，未冒充父步骤内操作。

advance 单次最多一次正长度 read，长度受共享剩余额度及 4097 减累计字节限制。零
额度返回 NEED_BUDGET，绝不以 read(0) 判 EOF；短读、LF、EAGAIN 均不能完成帧。
返回字节先计费，再核延迟、超长及缓冲。仅模型 read 返回空、原读端已知关闭、原
buffer 完成 canonical 解码和预期比对、child 时钟检查通过后，才等父共享步骤结束。
take_claim 只在成功父 tail 后一次转移已准备的普通字典，不再解析、复制或执行 I/O。
FIFO 身份不符或关闭异常保持 UNKNOWN，不按数字重试关闭。实际身份来源仍未认证。

普通生命周期复核发现 READY-COLLECTOR-001/P2：草稿 fd58ed6b 在接收已结束预算时，
advance 和 abort 仍会于父 tail 后 close(7)。独立修复前两项均复现，报告摘要为
`ca82b184c920508820187b9751d1884b09317c6824fa3a4b83c1b87bfea5d5b5`。
最终 422c9f2c 对这种调用只记录失败、保留 OWNED、无 I/O；合法新步骤可以仅清理，
关闭一次并实际调用新 finish_step，保持首因。第三项覆盖前一步 FAILED 且 finished
后的同类清理；三项均记录新 tail=(21,31)、FAILED/finished。最终报告摘要为
`cdd0d45e78120e3d9b5357b032256ab994404d3a7b4b846914d397b6bc4d7ae0`。
此 Finding 已在普通模型范围修复并独立复验，不关闭阶段 40 的 PARTIAL 审查。

预算源码 5,867 字节，摘要
`edbc23b8db030d31701b4a6ac13394f9b39e6f741b939b399aa369a31e2f0a57`；collector 为
9,532 字节，摘要 `422c9f2ce197534ed163cae6c3bd9e44973d3829b2a5f491de4d898b00d59b36`。
作者 41 项预算、91 项 collector 测试分别通过；独立普通检查 39 项通过，分为 9 项
预算、26 项接收组合、3 项上述生命周期和 1 项实际 sender 组合。最终 binding 摘要
`3fe4492a7ca04dcbb67324e6cc7d9cbefb2a8b271dbba1605d8a6d066aa5d1c5` 固定这四组；
trace、export 准备、重复质量复验、旧轮次和作者测试不叠加到独立计数。

实际 sender 组合在单独模型进程运行固定 5ae8197f 前缀、三原观察器和 141caf3b sender，
写出 294 字节并关闭 child 6。另一模型域把原输出交给 parent 7，仅在 writer 已关且
缓冲耗尽后返回空。预期 request 摘要/worker 来自独立保留的原请求，预期源码 SHA/
长度来自本地固定前缀，未从接收帧反填。根重新计算 canonical 帧并核得实际输出一致；
帧摘要为 `8a2324498faa14db503bd882d9211db2d954c44ab698fd65f45cd2449cd8622e`。
这只是一次完整普通组合，未重跑旧 17 种请求矩阵，也未证明真实 child、管道或 EOF。

预算最终 5 个工具/测试及 runtime、collector 最终 10 份 Python 源、独立 11 个工具
均通过完整 Ruff/format；实际接收源码以 py312 静态目标检查通过。根 3 个汇总工具
和实际快照工具通过完整规则；根核作者 JUnit、四组实际报告及执行/最终工具 AST，
没有新增行为测试。旧失败、未选中的中间报告和原工具快照均保留。

| 交付包 | 最终 manifest/delivery SHA256 | 文件数 / 归档字节数 |
| --- | --- | --- |
| Parent step budget v1 | `36b8a56257c0889ba8002cf68303a0dfaf5632045ac8b861ee1567d754a24f23` | 47 / 235,520 |
| READY collector v1 | `3a081e712148e8ad43b57463a7607f48f8cb31c14518ed898210576d80000f49` | 62 / 1,382,400 |
| 独立普通集成审查 | `6c4afb206478e1d40a03b0e17bf1ac8d790970354657f320e5e84af2179cead3` | 168 / 1,546,240 |
| 根证据汇总 | `53e0e419a1a38513cdd10b10bfb507503a70c28762ef95280b8c7435b2602e61` | 44 / 358,400 |

四包文件与归档成员均逐项回读。collector 冻结包独立指针路径误多了 evidence/；根
pointer-correction.json 将原 720 字节指针绑定到正确的审查目录根 binding，原摘要
3fe4492a 不变。作者归档保留四份既有 Ruff cache，它们不计为运行源码或测试。
未改写任何冻结包。阶段 43 快照绑定本节提交、四份清单、阶段 42 快照和新 CLI 状态；
要求 tracked 文件与 HEAD 一致，既有三份未跟踪计划文件仅如实记录。

当前 Windows Python 3.11.9 使用固定 fake OS/fcntl/time 与真实 hashlib。接收器尚未
接入实际 ParentBirthSlot 或旧 pump；父 post-exec/source 比对、DATA 放行、完整 child、
ACK/退出收束、PreparedSourceImage、CompleteDataRead、Linux/runner/CI、服务恢复和
重启仍未完成。独立审查者未实现本批两份 runtime，但曾实现部分旧依赖；没有重验
全部历史内核或恢复阶段 40 实验。目标仓仍只读，未运行新的全仓 Gate，未填
implementation_result；TASK-0048 继续 IMPLEMENTING。

## 共享 pump v2 与 Linux fixture 源码准备

阶段 44 新增树外 shared pump v2，接入阶段 43 原 ParentStepBudget；原 pump、预算与
READY collector 冻结包不变。新 pump 为 22,964 字节，摘要
`4f3b08cfc2c7742d83df5b88bbbd8c67545ed3c683b6d3104cf3bfb2f5eeca20`。
输入初始 WAITING，保持输入管道；父用同一未结束预算明确 release 一次，保留原 bytes
引用，不在步骤外复制 64 KiB。明确 release 空 bytes 与尚未 release 分开；这不改变
业务 DATA 必须为 1..65536 字节的约束。模型 fixture setup 仍不证明生产 birth。

两个 pump 与原 READY collector 在同一普通步骤合计传输 16,384 字节，共用一次父
finish_step；共享时间超额控制使公共预算失败。零余额不 read(0)，实际读写返回先
charge。原 child execution/complete 截止仍独立检查，不以更宽父截止延长。组件不
自行结束预算。输出在父 tail 前固定为 immutable bytes，成功 tail 后只返回原引用，
并继续核原 child/settle 截止；这是 opaque transport，未提供 ACK 接受或 DATA 准入。

当前 FAILED 步骤只做有限的已知管道关闭。随后合法 OPEN 步骤可推进原失败任务的
收束，必须接续上一实际 tail 与同一父 deadline 引用。首次接入合法预算的异常（包括
abort/release 失败）立即以原预算 last_clock 固定保守的最多一秒 settle 截止，并受原
complete 截止限制；后续步骤不续期。此结论限定为 _record 异常路径；根汇总 REVIEW.md
中的 first legal failure 按此限定，普通 _fail(reason) 仍在随后的 _enter_settle 取时。
owner、close、signal 或 reap 不明仍保留不明，不靠数字句柄重试冒充已清理。

本批四项普通模型 Finding 均保留修复前实际报告，并完成独立修复复验：

- SHARED-PUMP-001/P2：草稿 512e 允许超过 child execution 截止后 release，及前一次
  read 跨截止后继续写 4 字节。最终迟到 release 保持 WAITING，跨截止后不写，只计已
  实际读到的 13 字节。
- SHARED-PUMP-002/P3：同一草稿首次迟到 tail snapshot 暂报空 failure，内部已记录
  settle_deadline；输出原已拒绝。最终首个 snapshot 字段一致，tail 后取值无 I/O。
- SHARED-PUMP-003/P2：c0c 将首次 settle 初始化推迟到下一步骤。最终 abort/release
  在 (10,20) 失败即固定 (1000000010,1000000020)，后一步及实际 tail=(200,300) 不续期。
- SHARED-PUMP-004/P2：作者控制发现 2e97 可能用 owner 观察的 KeyboardInterrupt
  覆盖父已有 OSError。最终 abort/step、budget 和 tail 均保留原首因；owner 不明时
  三个管道角色仍未关闭，没有用强制关闭伪造成功。

作者 run-005 的 86 项模型测试通过；独立 32 项分为 25 项普通组合、3 项原 child 截止/
snapshot、2 项首次 settle、2 项父首因控制。最初两项 smoke 已包含在 25 项内，旧轮次、
trace、源码映射和质量复验不累加。最终独立 binding 为 6,137 字节，摘要
`21c686936da26b40889fcafa7da7ce0ae2e394120f311673ee1417f279c5d1b5`。
作者最终 10 份 Python 源、独立 11 个工具、根 3 个工具及快照 helper 均通过完整
Ruff E,F,I,UP,B,SIM 与 format；实际 runtime 以 py312 静态目标检查。根逐项核实际
JUnit、四组前后报告和来源绑定，未新增行为测试。原 pump 的前置类/函数 AST 不变，
新 Pump AST 与提交模板一致；这些检查不构成整个历史内核的重新独立验收。

另准备 15 项 Linux fixture 源码：适配原 13 项，新增等待后 release 与两个 pump 共用
父预算两项。源码 16,122 字节，摘要
`4a7d6e4f4b05a312b873286bab9a058806ad98763b33d10569991cdd593f7298`。
七个原 helper/test 定义 AST 保持一致；stdin-closed 负例明确保留 BrokenPipeError 与
失败 tail，再用合法 OPEN 步骤和原 settle tuple 等待 pump 自身证明 reap。wrapper
清理本身不能使该断言通过。该接口修正仅经源码复核，没有 native 行为结果。

15 项由 AST 中的 literal 参数表计数，未 import、collect 或执行，也未把 Windows
SKIP 计为通过。最终四个准备工具与实际 fixture 完整质量检查通过。三成员 native
bundle 仅包含上述新 pump、原 edbc 预算和 fixture；归档 51,200 字节，摘要
`d5edb433aa88c35698e262d5ff3d7452dcae31824eead49cba445a525cb11eb5`，已逐成员回读。
原 dummy READY 行只是测试 setup，未验证新的 native collector 或生产 birth。

| 交付包 | 最终 manifest/delivery SHA256 | 文件数 / 归档字节数 |
| --- | --- | --- |
| Shared pump v2 | `2376cf390d452f8a8aebac03bb9736173a7290f2f6914b476ab584a4fbde2bbd` | 77 / 1,228,800 |
| Native fixture v2 准备 | `77a44a046bd1cc9c7f46641db2b1e37b22f366aeaaaa9a3edf7e11a2ce077674` | 111 / 542,720 |
| 独立普通集成审查 | `9762d79466b2355b6856478f51db08aa9d757544df3d917b61c6963ef743601e` | 232 / 2,058,240 |
| 根证据汇总 | `606e4b02b3144bf24388ae5c98ea85359e6110892f6536b8f066a1722b8855fd` | 39 / 399,360 |

四包列项文件与归档成员均完整回读，失败尝试及原源码快照保留。自动审批曾拒绝删除
本轮 pump 的 Ruff cache，仅返回 blocked by policy；未换工具重试，三份缓存留在
本地并明确排除于交付文件和归档，未读取内容。未读取或哈希旧 host-tests-001.xml。
阶段 44 快照绑定本节实际提交、四份清单、阶段 43 快照与新 CLI 状态；要求 tracked
文件与 HEAD 一致，既有三份未跟踪计划仅如实记录。

本批仍在 Windows Python 3.11.9 的固定 fake I/O/时钟模型内，未触及目标仓或 Linux。
实际 ParentBirthSlot、完整父调度器、post-exec/source 比对、pending/DATA 准入、完整
child、PreparedSourceImage、CompleteDataRead、Linux 门禁、runner/CI、服务恢复与
重启均未完成。旧 source-image preparer 未改指新前缀，阶段 40 PARTIAL 未关闭。
未运行新的全仓 Gate，未填 implementation_result；TASK-0048 继续 IMPLEMENTING。

## Bootstrap-control 与 exec-error 父管道候选

阶段 45 新增树外 ControlSender 与 ExecErrorCollector 实际算法，继续使用原 edbc 父
预算、55216 事务协议、422 READY collector 与 4f3 shared pump。新源码 12,168 字节，
摘要 `6f145ceaefe3867884a6037392a7939674c2685c353dedc04c4b744db473067e`。
两条新管道仍只有明确模型入口，没有 fork/exec、管道发行器或 ParentBirthSlot。

首次 control advance 在同一父步骤检查前后完成原 encode_control_argv、decode 和
request deadline 比对；完整固定七项 argv 含各 NUL 不得超过 4096。仅发送最后一项
原 canonical request bytes，无 LF/NUL、不新增 schema 或可选 argv/env/path。短写接续
同一帧，零余额不 write；有效正返回先登记 bytes_sent，再 charge 与后置时钟检查。
写全并已知关闭本父写端后等待父成功 tail，才一次取结果；这不证明 bootstrap 已读 EOF。

exec-error 每次最多一次正长度 read，长度为 min(共享余额,4097)。实际返回先 charge，
诊断最多留 4096 字节；非空数据立即永久失败，不解析为成功或等待后续 EOF 清错。
4097 字节超限仍记录实际收费。只有正长度 read 返回空、原读端已知关闭及父 tail 成功，
才提供普通 empty-EOF 结果；EAGAIN、LF、read(0) 均非 EOF，空 EOF 也不认证 exec。

两类均保留原 child 截止及跨步原 tail/deadline 引用；已结束、错型或断链预算不执行
组件 I/O。当前尚未结束的 FAILED 预算只允许保留首因后的有限已知关闭；合法后续
cleanup 不恢复业务传输。close 异常保留
UNKNOWN，不按数字重试。候选父 profile 为精确 FIFO dev/ino、读 2048/写 2049、
CLOEXEC=1，尚非真实 birth 观察。model factory 参数失败尚未接纳 FD，原调用者继续
拥有它；一般 fstat 异常不等于已观察到身份替换，明确身份错值才标 UNKNOWN。

BIRTH-CHANNEL-001/P3 已在普通范围修复并独立复验。根静态发现、作者实际复现草稿
8b46 的正 write 返回后，后置时钟失败会使 bytes_sent 保留旧值。独立修复前实际写
1224、budget 计 1224、bytes_sent 却为 0；最终三者均为 1224。两版原本均 FAILED、
已知 FD 关闭一次、保留原首因和 FAILED tail=(40,60)，没有成功结果。修订只补实际
传输证据，不称旧版少计父预算或错误接受。作者原 1258 字节反例另保留，不混写数值。

作者最终 run-003 为 103 项普通测试通过；独立 46 项通过，最初三项 smoke 与单点
counter probe 已包含其中，不重复累加。独立 binding 为 2352 字节，摘要
`cd8829c99d3808658560798408793455e9e08e8f098ead8872847437fea10c48`。
五组件组合将 control 1240 字节、READY 285 字节与两个 pump 合计收费 16,384，共用
一个成功父 tail；共同时间控制在 100000001 ns 失败。该组合的 control 与 READY
request SHA 不同，只证明共享传输/预算，不证明同次出生身份与来源闭环。阶段 42/43
的实际 sender 294 字节组合未重跑，不加到本批计数。

根从原 67 文件 values 包和完整归档回读后，取四份未变纯源码及原最大值见证，用实际
codec 复核 14 kind：完整 argv 与旧保存字节一致，并实际 encode/decode 往返。最大
原始控制帧 3147 字节，完整 argv 3215 字节；固定前六项含 NUL 为 67，最后项另计一个
NUL。这是原见证的传输形状核对，不是新的闭域最大值证明、真实 EOF 或 core replay。

另准备 9 项 Linux 真实 pipe 测试源码：完整控制及 EOF、共享余量下的短写、背压、
已结束预算与合法清理、空 error EOF、1/4096 非空 error、零预算不消费及 EAGAIN。
源码未 import、collect 或执行；无 fork/exec，即使未来成功也不证明 exec 时 CLOEXEC
或真实 birth。组件作者仅按实际 API 和失败 tail 做文本复核。八成员 native bundle
固定新 channel、原 budget、四纯依赖、fixture 与原 control frame；163,840 字节，摘要
`81eea7340902b7e1c9518b9e558ce757464e0c7dcaa498c22571db1e1a2c9336`，已逐成员回读。

作者 9 份 Python 源、独立 9 个工具、native 准备工具与 fixture、根 5 个工具及实际
快照 helper 均通过完整 Ruff E,F,I,UP,B,SIM/format；实际 channel/fixture 等当前源码
按 py312 静态目标检查。原失败源、计数反例及质量失败保留。根首次 B007 和 helper
长行修正后重新聚合，通过 quality-002；最终选择 aggregation-final 与 helper-v2，
原聚合和 helper 仍保留。根未新增 channel 行为测试，14 个 codec 往返与 native 准备分列。

| 交付包 | 最终 manifest/delivery SHA256 | 文件数 / 归档字节数 |
| --- | --- | --- |
| Birth channels v1 | `5a0d9073a0b74be8bab7e8af7001f55f26ef0e511aa7bc4b56cf3626d62b42f5` | 56 / 1,669,120 |
| Native pipe fixture 准备 | `205c8df32c806a7deeeee6e237dcd7b20e5640bbdbf227117cbd9d03e599eac5` | 35 / 409,600 |
| 独立普通集成审查 | `f5b1f60b4e4c70aa0096ba4b86b46da95b50cd99777ac3fe1dfc5ee84fb52a70` | 149 / 1,945,600 |
| 根证据汇总 | `19e91b314c877026c5309172c07c112602db3fc47b04fed4c419478e29ae274b` | 89 / 1,781,760 |

四包列项文件与归档均完整回读；本轮无缓存删除。阶段 45 快照绑定本节实际提交、
四清单、阶段 44 快照及新 CLI，要求 tracked 与 HEAD 一致并保留三份既有未跟踪计划。
本轮仍在 Windows 固定 fake OS/时钟模型内，没有目标仓、guest/native、runner、服务
或重启动作。独立审查者未实现本批新 channel，但曾实现部分旧依赖，不重新签发全部
历史内核接受。固定 bootstrap reader、完整父出生/调度/post-exec/source、pending/DATA
准入、完整 child、PreparedSourceImage、CompleteDataRead、G3、Linux 门禁及实际交接
仍未完成。阶段 40 PARTIAL 不变；未运行新的全仓 Gate，未填 implementation_result，
TASK-0048 继续 IMPLEMENTING。

## 固定 bootstrap 控制接收与同请求 READY 字节桥

阶段 46 新增树外固定 FD8 bootstrap 接收算法，源码 7,807 字节，摘要
`e7c306a0ba855715077f6d6ad1f6bc0e4790a5d18f66e2246c84c13ddb905af0`。
它只有明确普通模型入口，成功构造时接纳 FD8 是模型假设，不是真实 pipe/birth 发行。
形状检查失败前未移交描述符；原调用方仍拥有它。候选不提供 argv/env/path 回调，
不调用 fork/exec，也未接上完整 bootstrap 的描述符安排与解释器执行。

每次 advance 最多一次正长度 read，申请量为 4096 减实际累计接收字节。实际正返回
先登记 received_bytes，再做后置时钟检查。固定前六项 argv 含 NUL 为 67 字节，
最后一项另计一个 NUL，因此合法原始控制帧最多 4028 字节；不加 LF/NUL 或 4097
哨兵。读到 4028 后仍有 68 字节容量用于实际空返回 EOF；超限立即失败。EAGAIN
为 WAIT，短读或已有合法 JSON 都不产生 EOF，其他可见错误不内循环重试。

空返回后已知关闭 FD8，再由原 55216 codec 严格解码固定七项 argv；重复键、额外
空白、尾随数据及非 canonical JSON 均由原解码器拒绝。请求 deadline 必须仍等于
原窗口；候选保留原 fork 前 born 与原 deadline 引用，每次双轴时钟不回退、严格
早于原截止，且各轴相对 born 均小于 30 秒。宽窗口和 MAX 值不被改写为新 TTL，
1 秒收尾余量不用于准备或取用 argv。子接收器没有复制父预算；父侧写入仍由原
16 KiB/100 ms 预算独立收费。本批时钟与 born 都是明确模型输入。

BOOTSTRAP-CONTROL-001/P2 已在普通范围修复并独立复验。根静态发现准备后至
take_argv 期间缺少进程值重核；独立在原 eae76 源分别改变 getpid/getppid/getpgid
普通返回值，三项均仍取到原 argv。最终 take 再用原请求核对三个实际模型调用，
与最初观察值比对，并做最新双轴时钟检查后才一次移交。三项修订后均拒绝，FD8
保持此前已关闭一次，不重复关闭。旧/新反例报告摘要分别为
`741561eaf3435ab464e03fc9c3f983a0977e929db611fe2747b1eb8c8168b637` 与
`4d04ddef7ed789045401e06301b6fcf0fd57d9f10e3d3d19e17ff5eae909673b`。
该结果不证明实际 exec、start_tick/boot/source 或完整进程身份认证。

作者最终 run-003 为 92 项普通测试通过；独立最终 50 项由 47 项普通控制与 3 项
take 值变化组成，smoke、旧失败和重跑不累加。独立 binding 为 2910 字节，摘要
`56bb07c3384b3cea2faab58760205b3f1dba04de7b1343b794be391d38f44c92`。
原未执行的窄 deadline 草稿、执行过的旧源和反例均保留，未重开阶段 40 实验。

根另执行 1 条同请求普通字节链路：实际 6f ControlSender → 新 e7c bootstrap reader
→ 原 5ae 固定入口及 141caf READY sender → 原 422 READY collector。原请求来自
冻结 fixture；父侧实际写出的 1258 字节按片读回，重组完整 argv 1326 字节，入口的
orig_argv 直接来自该接收结果。独立保存的原请求与进程/proc 期望保持不变，完整
770,814 字节前缀执行普通 entry/proc/source 观察后实际生成 294 字节 READY。
父期望由原请求和固定源码摘要/长度构造，没有从收到的 READY 反填期望。

原控制及各组件 request SHA 均为
`0be311d1508765306d73dac4b87c53c1bc84129b39b152bdfa8d143d046a6dd9`；
实际 READY SHA 为 `8a2324498faa14db503bd882d9211db2d954c44ab698fd65f45cd2449cd8622e`。
同一 ParentWorld 内两个父步骤分别计 1258 与 294 字节；第二步骤的原 deadline 与
上一 tail 使用对象同一性断言。Windows 模型子进程位于第一个模型步骤结束后、
第二个开始前；不把宿主编排计作生产调度器，也不称一个步骤覆盖 child 执行。
两个模型 elapsed 均为 0，不证明真实耗时。READY 后只有 FD6 已关闭，345 ledger
仍保留，DATA 为 NEW/0 字节；显式测试 disposal 单独记录，不当作生产完成。

独立审查者只读核对根六份实际执行工具及控制、argv、入口、READY、disposal 和
最终报告，没有重跑或增加行为测试。此桥关闭阶段 45 的不同请求普通字节关联缺口，
不补 exec-error、真实 EOF、出生、exec 或授权。根报告 62,209 字节，摘要
`cf8a28d678aec7bc164cb15f161a3d14d6df2059218838a4037d9efccdc23306`。
作者 9 份 Python、独立 8 个工具及根 7 个工具与实际快照 helper 完整 Ruff/format
通过；实际新 reader 另按 py312 静态目标检查。作者封存工具首次 E501 日志与源码
保留；根预检查长行在首次桥运行前格式化，最终八源码 quality-001 全部通过。

| 交付包 | 最终 manifest/delivery SHA256 | 文件数 / 归档字节数 |
| --- | --- | --- |
| Bootstrap control reader v1 | `2eec2e307a19e922629cdc6641a6370c3b3c293558d554ce0ce1d5ac609aa181` | 55 / 1,351,680 |
| 独立普通集成审查 | `18f5fac5a29fe7625cf8250169456f69b6f961b3654cd45680a1d89b103c17fe` | 119 / 2,519,040 |
| 根同请求字节桥与证据汇总 | `d8d9556a278593e5badeb4bafad17cbf5903ec67d8e9562f738db8e5b12e06d1` | 71 / 1,669,120 |

三包全部文件及闭合归档逐成员回读通过，无排除项；原六个桥输入包也已完整回读。
阶段 46 快照绑定本节实际提交、三包清单、阶段 45 快照与新 CLI，要求 tracked 与
HEAD 一致，保留三份既有未跟踪计划。并发目标仓继续只读，未操作 guest/native、
runner/CI、服务或重启。固定 reader 候选已补齐；实际 pipe/birth 发行、完整父调度、
post-exec/source、pending/DATA 准入、完整 child、PreparedSourceImage、CompleteDataRead、
G3 与 Linux 实际验收仍未完成。旧 source-image preparer 未改指新前缀，阶段 40
PARTIAL 未关闭。未运行新的全仓 Gate、未填 implementation_result；TASK-0048
继续 IMPLEMENTING，不能据本批普通模型结果认定任务 02 完成。

## 当前入口的源码准备器对齐与 FD8 native 测试准备

阶段 47 另建 source-image preparer v2，封装阶段 42/46 已固定的 770,814 字节入口
prefix，摘要仍为 `5ae8197f786e7a1af5d10e8ba7a41214e0556d207f4ea90a94b13da476ec65d2`。
旧 v1 及其 992e 前缀不变。新生成源码 1,679,942 字节，摘要
`0fcb173aca2a4c013888c4b0a421450a0932be80294c6e8b90b41c6a9b38f948`。
嵌入入口只作为固定数据写入/读回普通模型文件，本轮不执行其中程序。

根完整回读旧 preparer 的 108 文件/归档和当前 assembler 的 150 文件/归档，选取
六份输入。新模板仅改变 globals、_borrow、begin 三处固定 size 和三处固定 SHA；
旧 SOURCE-PREPARE-001 的字面量重核仍保留。生成器在每次构建重新核两份 delivery
固定摘要、选中文件、prefix/index/build receipt 及旧模板/运行源码的固定摘要。
独立解码唯一 bytes.fromhex 赋值，核原/新嵌入字节，再移除该赋值并归一六个常量，
旧/新模板及旧/新生成源码四份算法 AST 完全相同。两次构建字节一致；最终加强输入
绑定的生成器再次双构建，输出仍与原新源码相同，不更改接口或资源移交流程。

首次准备工具误以为各有两处 size/SHA，严格断言失败；实际还有 begin 中第三处。
原工具及失败记录保留，未生成或执行运行源码。随后构建因 inputs.json 尚未产生
而失败，也明确记录。修正要求精确三处替换；已复制 reference 只在字节相同时复用，
没有覆盖旧候选。该准备工具修正不被记作运行算法缺陷。

新源码的七项普通控制通过：完整准备/关闭、997 字节短写与 1009 字节 positional
读回、最后字节变化、提前 EOF、额外一字节、EOF 后原截止已到、只读关闭可见错误。
完整模型观察保留新长度/完整 SHA、四 seal、只读独立 OFD/offset0、原写端已关与
原 readonly slot 保管；负例分别拒绝并保留首因。最后关闭错误仍为 UNKNOWN，
不重试数字、不称释放。根报告 1850 字节，摘要
`76b4b627c92560a223e0edbbd09d98341691b6ae90cafe7ce324dfe6b4df42d7`。
旧模型只改两处 fixture 路径；普通错误/读值/时钟通过原固定模型输入控制，未重跑
旧对象/类/模块替换实验，旧作者或独立 122 项均不加入本批七项计数。

另准备固定 e7c FD8 reader 的九项真实 Linux pipe 测试源码：完整 canonical 控制
及 EOF、七字节分段且完整帧仍等 EOF、开放空 pipe EAGAIN 后 abort、截断 JSON、
尾 LF、空 EOF、4028 非法 raw 待 EOF 后 codec 拒绝、4029/4096 运输超限。4028
样本明确是非法 JSON，不声称存在该长度的合法请求；全组未使用第 4097 接收字节。
未来 fixture 要求独立单线程且 PID=PGID、原 FD8 不存在；read 端原本为 8 时保留，
writer 为 8 时先移至已知新 FD，再用 F_DUPFD_CLOEXEC 取得空闲 8，不覆盖既有 FD。

请求的实际 PID/PPID/PGID与 setup 双钟仅属于未来 fixture 的输入来源，其他 tick/
source 字段仍是声明。一次 40 秒绝对窗口保持不变，reader 独立遵守原 born 双轴
小于 30 秒；不称真实 fork 前时钟或生产预算。wrapper 只清理本次已知资源，不能把
UNKNOWN 按数字重试或把兜底关闭写成 reader 自身的成功关闭。七成员 bundle 含
reader、四纯依赖、原控制模板及 fixture，不含执行入口；九项均未 import、collect
或执行。根普通模型也没有真实 memfd、pipe、seal、procfs、fork/exec 操作。

根六个 Python 工具/模型加实际阶段快照 helper、实际生成源码 stdin py312 完整
Ruff/format 通过。native 准备工具及 exact fixture/reader 的六项质量命令通过；
首轮工具 format 失败保留，fixture 首轮已通过。交叉审查由不同实现者完成：根编写
v2 对齐，worker_birth_design 独立只读核六常量/字节/AST/七项原报告；后者编写
native fixture，根独立核固定 FD8/所有权/窗口和九项源码。无必须修订项，未增加
独立行为测试，不重新签发全部旧依赖接受。原先较广的 C 缺口审查未形成最终回执，
已取消且未计入完成；本批回执明确记录实际交叉审查者与静态范围。

| 交付包 | 最终 manifest/delivery SHA256 | 文件数 / 归档字节数 |
| --- | --- | --- |
| 固定入口 source preparer v2 | `b248a895d80943c8c1d02727a68d5dfdd994880df757fad8fd4e018964dfb26c` | 59 / 9,349,120 |
| FD8 native fixture 准备 | `19c5f21ffb68226e1a431175555e84a7c8f761540640748cda0e473bb8c1c836` | 42 / 430,080 |
| 交叉静态审查记录 | `0c4bfaf4112ddcbeb6d71684208cc485dbe99171060d6bc25088baf07d035822` | 31 / 317,440 |

三包所有列项与闭合归档逐成员回读通过，无排除项；审查封存工具亦通过完整质量
检查。阶段 47 快照绑定本节实际提交、三包清单、阶段 46 快照及新 CLI，tracked 与
HEAD 一致，三份原未跟踪计划保持原状。最终源码仅提供原 begin/step/close；PREPARED
观察不移交 FD。后续 C 仍需明确真实 source FD 与解释器的取得、保管和移交来源，
不能从普通观察签发 grant。真实 pipe/birth、固定 bootstrap FD 布局及 fd-exec、
post-exec/source/完整 FD 表、DATA 准入、完整 child、PreparedSourceImage、CompleteDataRead、
G3 与 Linux/runner/CI/服务恢复/重启均未完成。目标仓仍只读，阶段 40 PARTIAL 不变，
未运行新的全仓 Gate、未填 implementation_result；TASK-0048 继续 IMPLEMENTING。

## 最小执行路径核对与 Linux native 准备收束

阶段 48 对照原任务 02 建议稿、实施计划、TASK-0048 spec、阶段 47 记录及后续 C–F
计划，重新核对剩余范围。原目标仍是一个可信私有试点；完整 Linux 隔离、原 dash/ash
600 秒四用例/五行、真实 runner/job/checkout、采用与采用后 CI、服务恢复及重启业务
证据均未完成。后续 C/E/F/G3 是已选实现路径的义务，不能据其设计文件将所有大型模块
完成推成小规模平台实测的前置条件，也不能删去原准入要求。下一有限步骤收束为确定
专用 guest 的当前身份及已有 native 测试，不再为累计模型 PASS 扩展新的框架候选。

本仓固定提交 `e7fbe4d67bc4220d2eec54d7ea28a36c719699fd` 的独立干净 Windows
检出完成九项质量命令：锁文件、锁定安装、105 项合同检查、1,945 项完整测试、diff
coverage、whitespace、Ruff、format、mypy 全部退出 0，测试无失败或跳过。总覆盖率
88.12%，保留 branch 测量与 85% 阈值。diff-cover 保持 90% 阈值，对固定 base
`f633c036cc2a0394f7b1efb20efe4d91ba944255` 报告无可计量变更行，不声称数值达到
90%。最终 HEAD 未变且检出干净；根逐命令日志摘要及 JUnit 计数读回通过。完整测试
815.78 秒，未延长原 1200 秒命令限额。该结果属于此次文档提交之前的固定源码和
Windows 环境，不是托管 Ubuntu CI、Linux fixture、正式 AI Flow Gate 或实现完成。

新的只读采样显示私有目标当前 main 的 Windows job 七步骤成功，POSIX job 仍为
零步骤失败；返回的原 Windows runner 在线且空闲。主机没有原 QEMU 或预期 SSH
监听，原 PID 已不存在；Windows runner 服务运行，其进程路径本地不可读，身份仍
unknown。分页、瞬时采样不证明所有实例状态、持续空闲或并行写者交接。首次 Windows
PowerShell 5.1 采集被执行策略拒绝，失败保留；改用已配置的 PowerShell 7 完成采集，
没有改变或绕过执行策略。未读取目标工作树、启动 VM、连接 guest 或改变服务。

另封存固定 source preparer v2 的四项 Linux native 测试源码：完整 memfd 准备、
只读写入拒绝、开始前已过期、取得 writer 后再次 begin 拒绝并关闭。实际读回、EOF、
SHA、offset、metadata/seals 和已知关闭是未来测试的断言；只读写入 EBADF 只证明
访问方向，不能独立证明 F_SEAL_WRITE。root 控制面 fixture 的真实/有效 UID/GID
要求均为 0，不能作为低权限 runner 验收。嵌入的固定 prefix 只作数据，不执行。
fixture 清理和组件自身关闭分开，UNKNOWN 不按数字重试；setup 截止不是原生产预算。

新包 43 文件，delivery 摘要
`ba52ed97f812d4ee42ef7030f8ff9b08c345bd88291cc84d201e761f95f8a340`；归档
5,079,040 字节，摘要 `1704a5df585d6a024a9605852170efe8ba04907056ef065041416e0e98dfe3d3`。
根完整回读新包和阶段 47 的 FD8 包全部文件/归档；三成员 memfd bundle 与七成员
FD8 bundle 分别固定，合计 13 项仅准备，0 import/collect/execute。新 fixture 与
实际 runtime 静态质量通过，首次工具 format 失败保留；这些不是 native 行为证据。

树外 `completion-path-audit-001/NEXT-NATIVE-ENTRY.md` 与数据型入口请求固定下一
阶段：使用专用 guest、现有严格 SSH 身份策略和全新日志/PID/回执路径，先启动后做
只读身份核查；启动本身会写 guest 盘，明确不称只读动作。旧盘摘要和新 boot 身份
仍 unknown，执行前须重核输入、占用和现场条件。该提案未包含 native 执行、目标写入、
runner 注册、CI 触发、服务切换或宿主重启，也没有从当前空闲采样推导权限。

本轮独立审查发现质量工具最终 HEAD/clean 原先未参与成功条件，及采集工具超时可能
漏存部分输出/其他 GET。已修订未来工具并保存旧执行源码；本轮原质量报告的实际
HEAD/clean 另经读回确认，未重跑或改写原结果。两项缺陷的四个反例经合成控制复现，修订后
14 项控制通过，不接触网络或 guest。阶段 48 快照绑定本节实际提交、审计清单、
阶段 47 快照及新 CLI；三份既有未跟踪计划保持原状。阶段 40 PARTIAL、Linux 实际
准入及任务 02 剩余验收未关闭，
未填 implementation_result，TASK-0048 继续 IMPLEMENTING。目标仍按用户要求只读候选。

## 专用 Linux guest 获准启动与当前身份核查

阶段 49 在用户明确回复“允许启动”后执行阶段 48 提案的第一步：启动既有专用
guest，并只读核查当前身份。该回复未扩展为 native 测试、目标写入、runner 注册、
CI、服务切换或宿主重启；原私有目标继续只读。启动本身写 guest 盘，已如实记录。

启动器绑定原封存请求、QEMU/kernel/initrd/seed 摘要及新日志/PID 路径。实际 qcow2
元数据揭示该增量盘仍依赖原基础镜像，故补核真实 backing 路径、原下载 SHA256 与
无更深 backing。两盘以独占读句柄取得当次摘要，增量盘原 size/mtime 未变；这只是
启动前占用采样，不称持久所有权。qemu-img check 未请求 repair，返回 0 且 check-errors
为 0。不同实现者只读审查启动器和 host preflight 后未发现本限定动作需修订的问题。

第二次核查确认无 QEMU/端口冲突、可用内存满足预备值，按原参数隐藏启动。初次 SSH
探测在 guest 启动中发生 banner 超时，失败保留且未重启；第二次严格 host-key 探测
退出 0。随后核对当前 QEMU PID/创建时间/路径及回环端口归属，通过既有专用 SSH 身份
运行固定摘要的只读 inventory。Python 使用 -I -S -B；未读取或显示私钥内容。

实际 inventory 退出 0、stderr 空、采集 errors 为空，耗时约 0.487 秒。新 boot 身份、
Ubuntu 24.04.5 LTS、Python 3.12.3、dash 0.5.12、BusyBox 1.36.1、Podman 4.9.3 和
crun 1.14.1 均已采样。ci-runner 本地 UID/GID 为 1001，只列 users/ci-runner 组；
未检查 sudoers/NSS 或以该身份验证有效权限，不能认定低权限 runner 已验收。

采集进程实际为 root、单线程，FD8 前后不存在；PID 不等于 PGID，且与 PID1 共用
所列 namespace，根挂载为 rw ext4，NoNewPrivs/Seccomp 为 0，session cgroup 限额
为 max。这是 guest 管理环境的观察；Python isolated 模式不等于 OS 沙箱，也不能
将此次采样代入未来要求 PID=PGID 的 FD8 fixture。查询范围内仅见既有 network guard
服务 active/exited，未返回已加载的 Linux runner unit；未核定全部注册和 activation。

前后 Windows runner 服务字段一致，最后观察 VM 与回环监听仍存活。新增工具完成
完整静态质量检查；inventory 作者只读核对实际输出与 SSH 回执，确认上述边界，未
重跑采集或新增行为测试。树外 guest-start-identity-001 复制有限执行证据并封存；
仍会变化的 serial/stdout/stderr/PID 仅保存当次样本，不把活动进程日志伪装成最终日志。
阶段 49 快照绑定实际文档提交、封存包及阶段 48 快照；旧文件与三份未跟踪计划保留。
13 项 native 仍为准备完成、执行 0；完整隔离、原 root fixture、runner/CI、服务恢复、
宿主重启业务及其他原验收项尚未关闭，未填 implementation_result，任务 02 未完成。

## Linux native 测试入口准备与封存

阶段 50 延续已获准的只读核查，实际 profile 退出 0：guest 仍为阶段 49 的同次启动，
kernel 为 6.8.0-139-generic、Python 为 3.12.3，发行版元数据显示 pytest 7.4.4；
拟用的新输入和证据目录当时均不存在。该请求只读取身份、目录及文件元数据，未导入
pytest。五个发行版文件摘要仅固定这些文件，不认证整个 pytest 安装，也不保证未来
目录仍空闲。本阶段没有上传文件或写入 guest，原目标、runner 服务和 CI 继续只读。

为原有九项 pipe/FD8 和四项 memfd 诊断准备固定入口。入口要求 root UID/GID、
单线程、PID=PGID、指定 boot 身份与 FD8 空闲，并在 collection 和各 test setup
重新检查；使用隔离 Python、干净的三个环境变量、固定参数及受限 pytest 插件。
关闭默认捕获、缓存、logging、faulthandler 和 JUnit，避免入口额外占用 FD8。
只有精确收集全部 13 项、13 项 call 均通过、所有报告阶段通过且退出 0 才能记录通过；
skip、缺项、失败和超时均不能折算为通过。上述均是待执行入口的检查逻辑。

诊断 supervisor 为子进程建立独立 session，限制日志并设置 120 秒软件预算；在回收
直接子进程前完成原进程组操作。保留 zombie 的组存在观察不证明后代已全部清零，
也未增加完整 cgroup/resource 隔离或生产 parent 预算。未来判定必须同时核对实际
supervisor 退出 0、其通过回执以及全部 pytest 结果；该入口不是生产 guardian 验收。

本地重新完整校验两份原 delivery，十个原测试输入未改变。新包为 2,631,680 字节，
摘要 `7ec308e056d6b4fbc2eba706cc21ab8a626d875dbfce96603682e9f6506f5120`；
清单摘要 `36b08222241d477b23e5b6a58a9acb132b38f7f6dfe53d024eb8e13e19bd2bed`
必须由 host 独立传入，不能从 guest 清单自行推导预期值。清单固定 12 文件闭集，
归档另含清单共 13 个普通成员；成员数量不作为测试运行数量。独立审查确认此前发现的
外部摘要绑定与 pytest 环境问题已落实，且所有归档成员和最终入口逐字节一致。

树外 native-entry-preparation-001 封存 52 文件，manifest 摘要
`2970f6676c28301894ce00639dd02a6ab33daa638a70c6b2ebf25f9160cfea70`；
归档 5,355,520 字节，摘要
`f084aa7aa30b0c2269e646714033da10920c922cf315e67d98a40fdb6b09759c`。
五个新增工具的十项最终静态检查通过，封存内容与归档完整回读通过；初始格式/静态
问题及修订记录保留。真实 profile 的原始请求和结果单独保存，未改写为后续源码。
本仓只追加本文档，沿用阶段 48 完整质量基线，不将文档静态检查称为新的完整测试。
阶段 50 快照绑定实际提交、封存包、阶段 49 快照和 CLI 状态，三份既有未跟踪计划保留。

执行这 13 项测试的授权问题仍待用户答复；“允许启动”未扩展为 native 执行。
本阶段 native import/collect/execute 均为 0，尚未实现或执行传输安装步骤，未来须先
重新核对身份和目录占用。未填 implementation_result，TASK-0048 继续 IMPLEMENTING，
原隔离、root fixture、runner/CI、服务恢复与宿主重启等剩余验收继续未关闭。

## 固定 native 输入的传输与结果回收准备

阶段 51 补齐阶段 50 尚缺的 host 编排与 guest 传输工具，只作本地准备。原固定归档、
清单和 13 项测试源码未变。拟执行的四个显式模式为 probe、stage、run、collect；
各使用独占的单次证据目录，无自动串行执行、重试、删除或覆盖。host 每次派发前核对
原 QEMU PID、精确创建时间、程序摘要和回环监听归属，并保持原严格 SSH 身份策略。

guest helper 在内存中核对固定归档及全部 13 成员后，才手工创建两个新 attempt
目录和文件，不使用 tar 自动解包。原父目录须满足 root 所有、非组/全局可写、无链接；
文件独占创建并读回摘要，最终输入文件为 0444、目录为 0555，证据目录为 0700 且空。
失败保留部分结果。run 入口拟重新检查 boot、输入文件与空证据目录，再执行已读回的
原 supervisor；该逻辑尚未在 guest 运行，也不构成对抗并发 root 写者的完整保证。

collect 仅回收固定的两份日志及两份 JSON，检查大小、实际 EOF、摘要和前后元数据。
文件缺失与读取错误分别保留，其他有效文件仍可回收；收集成功不证明测试通过或进程
结束。SSH 观察超时不证明 guest 已终止，不得据此重启。原 supervisor 后代生命周期、
生产 parent 预算与隔离限制均未改变，原目标、runner 服务及 CI 继续只读。

独立审查发现的本地预检超时证据丢失已修复；模拟超时确认原始部分输出和失败回执
保留。离线控制还验证四种请求的源码编译、shell/base64 往返、Windows 命令长度，
以及部分文件回收和额外路径拒绝。含额外余量的最大长度为 24,215 UTF-16 单位，实际
派发另核对完整命令不超过 32,767。四个工具的八项最终静态检查通过，最终独立只读
复核未报告封存缺陷；这些都不是 SSH、Linux 文件系统或 native 行为的验证。

树外 native-transport-preparation-001 封存 31 文件，manifest 摘要
`88d45ffec794c98cd620874c6c4b92a1476562dc2da9b2966ae00372291d8040`；
归档 92,160 字节，摘要
`2c44ce3f2ea6ee481862e0e8224554fa35c046406d404a9df633eb89ffc3b2d4`，完整回读通过。
阶段 51 快照绑定本次文档提交、封存包和阶段 50 快照，三份既有未跟踪计划保留。
本阶段 guest 操作 0，native import/collect/execute 仍为 0。执行授权问题尚待答复，
TASK-0048 继续 IMPLEMENTING；任务 02 原有剩余验收及 implementation_result 未关闭。

## 获准传输并完成 13 项 Linux native 诊断

阶段 52 在用户明确回复“批准传输与执行”后，执行前述固定的九项 pipe/FD8 与四项
memfd 诊断。该授权解除本次测试的等待；原目标仓、runner 服务和 CI 继续只读，未
据此启动注册、服务切换、工作流采用/触发、推送或宿主重启。先并行核对准备包与验收
条件，再串行 probe、stage、run、collect，最后由两名 sub-agent 分别复核执行证据链
和精确测试结果，主会话完成综合核验及封存。

第一次真实 probe 的 SSH 退出 0，但原证据 parent 为非 root 所有，路径状态 unknown，
因此没有在该路径 stage 或运行测试。另一次只读 inspection 确认该 parent 的 UID/GID
为 1001，候选新路径不存在且父目录为 root 所有。保留旧目录、所有权和内容，改用
本次独立的 root 诊断目录；两份 entry 只替换固定输入/输出路径，十个原测试输入
逐字节不变。独立审查确认 case、断言、清理、计时与结果判定均未改变。

适配后的输入归档为 2,631,680 字节，摘要
`770e0ee5773939add837860150609c106056e82bcf00c650a0b1e7d817683718`；
清单为 3,174 字节，摘要
`aadd58647c0cab8bf1b8521676531c627997baf2983b76bb6bc1c690052e701e`。
新 probe 确认同次 boot 与两个新路径均满足条件。stage 实际验证归档及全部成员后
独占创建输入/证据目录，完成 13 文件写入和完整回读；原封存包不改写。

实际 run 的 SSH 退出 0，无观察超时或失败；pytest 输出 **13 passed in 1.39s**，
supervisor 耗时约 2.723 秒，记录子进程退出 0、已 reap、原进程组已核对，errors
和 signals 均为空。回收四个固定文件全部成功，stdout 165 字节、stderr 0 字节，
与 supervisor 的 observed/saved 长度和真实 EOF 一致，无 overflow。

主核验及独立原始证据复核确认精确 9+4 项，无遗漏、重复或额外项；每个 nodeid
各有 setup/call/teardown 一条 passed，共 39 条。15 条过程样本及 initial 均满足
指定 boot、root、单线程、PID=PGID、有效 PPID 与 FD8 空闲。最终进程检查未另写入
样本数组，未把它算成第 16 条过程样本。四文件的传输字节、base64、长度、SHA 一致；
11,996 字节 pytest-result 的摘要
`c8082f5c74cdcace45b70f0293fe9a6287df89ba2461a1ef2687b22ae3fb08db`
也与 stdout 中打印的结果摘要一致。

组存在观察仍包含可能的保留 zombie，仅确认直接子进程回收，不证明全部后代归零。
本次通过限定于实际 root/Linux/Python 3.12 下这 13 项平台诊断；4028 字节用例仍是
畸形帧，只读写入 EBADF 仍不能独立证明 F_SEAL_WRITE，prefix 仍作为数据而非 child
代码执行。完整 birth/exec/READY、生产 source grant、低权限隔离、原 dash/ash root
fixture、runner/CI、服务恢复与宿主重启等验收尚未完成。

树外 native-platform-tests-001 封存 143 文件，manifest 摘要
`af4c5b55d4b2c1c4018919bbf2a40f0227f181c02ebc38ae9cb4c7c4749b420f`；
归档 5,908,480 字节，摘要
`ce06118e5ef404edad4e135d79582354a2232ef5f6e43921eee029b84bd6b4ce`，完整回读通过。
九份工具/入口的十八项最终静态检查通过；构建器初始 E501 的实际源码与检查输出保留，
后续仅修正格式，未重建或重跑已成功的输入。阶段 52 快照绑定实际文档提交、封存包、
阶段 51 快照和 CLI 状态；三份既有未跟踪计划保留。TASK-0048 继续 IMPLEMENTING，
未填 implementation_result，任务 02 未宣称完成。

## 当前 v9 低权限复核、Dash 通过及 BusyBox 启动前拒绝

阶段 53 重新对照 TASK-0048 原规格与最终 v9 入口。原八项验收继续有效；完整
C/E/F/G3 是选择 quiet 路线时的实现义务，不是原规格要求所有路线先完成的新引擎。
本阶段复用既有固定 v9，未扩大到调度器或新的 quiet 实现。并行阶段启用两名
sub-agent，分别准备只读采集/回收及独立审查，主会话核当前环境与执行入口；实际
guest 捕获、preauth、Dash、BusyBox、回收严格串行，再并行复核结果和最小修复方案。
原目标仓、runner 服务、CI 继续只读，没有注册、服务切换、推送、采用或触发。

当前 boot 的只读捕获完成 178 项观察，无错误、缺项或截断。固定源码树另有
178 个条目，其中 155 个文件与原 `cd02cb3c` 清单闭集、摘要一致；六个 v9 runtime、
配置、manifest、运行时二进制及固定 seccomp 策略摘要匹配，hooks 为空；
containers.conf 记录实际摘要，未在采集器中声明 expected SHA。三个卷归 UID 1001，
为独立设备，容量分别为 4,143,677,440、67,108,864、58,675,200 字节，满足原上限。
这仍是固定候选的当前环境观察，不代表目标仓 main 已采用，也不是低权限内核准入。

首次执行前置检查取得有效 UID/EUID/GID/EGID 均 1001、附加组仅 100/1001，但账号
自己的非交互 sudo 查询只返回需要密码，不能证明无 sudo 权限。入口据此停止，
没有进入 adapter 或创建容器。保留 preauth-001 失败；随后 root 只读策略查询明确
确认该账号不允许 sudo。修正前置检查，要求该确定拒绝句及有效身份均匹配，再使用
新 preauth-002。原六个 runtime 与 shell entry 字节、原检查和预算不变。

| 当前执行 | 实际结果 | 原范围内的结论 |
| --- | --- | --- |
| preauth-002 | PREAUTH_PROOF_COMPLETE；内核及两次 FD 证明通过；attach 125、完整 drain、精确清理 | 未发 permit、未运行业务 fixture |
| Dash-001 | PASS；29.130 秒；fixture/attach/wait/inspect 均退出 0；无超时、溢出、残留 | 原四用例、205 字节五行输出与 600 秒预算通过 |
| BusyBox-001 | REJECTED：`supervisor_fds_changed_before_permit`；attach 125、完整 drain、精确清理 | 在发 permit 前拒绝，不能计作 BusyBox fixture 已执行或通过 |

BusyBox 两份完整 FD 记录属于同一 PID/start_tick：第一次只有 0/1/2，第二次新增
FD 3；原 0/1/2 完全一致。新增目标为只读普通文件，8,273 字节，其链接目标文本
摘要为 `132dad19278946c72a2a409208b5aa0f356fbba4789ec7536de5b49007c339aa`，
与固定屏障脚本路径的摘要一致。这是路径文本摘要，不是内容摘要；记录支持本次
FD 集合变化及保守拒绝，尚不能单凭它确证完整启动时序原因。现有 Running 观察
不能证明 Python 屏障初始化已完成，后续最小修复聚焦可信就绪握手；不忽略 FD 3，
不删除两次比较，不通过延长原预算或重复运行来替代修复。

三次回收分别为 43/47/40 文件，共 130 文件、401,695 字节。主核验及独立回读确认
完整 base64/长度/SHA/真实 EOF/stable、命令 stdout/stderr 摘要、nonce 绑定和清理
链一致；Dash 原输出、结果 envelope、proof 与 tick 一致。每次保存一份完整内核
观察和两份 FD 记录，未将两次内核采样宣称为两份已持久化完整内核文件。失败结果
从原完整 stdout 最后 JSON 行提取，保留提取来源；未重跑或改写旧失败。

宿主只读 WHP API 查询返回成功、HypervisorPresent 为真；未创建 partition、改变
Windows 功能或重启 VM。该查询可说明 API 报告的能力，不能替代 QEMU 加速启动或
性能验证；参见 [Microsoft WHvGetCapability](https://learn.microsoft.com/en-us/virtualization/api/hypervisor-platform/funcs/whvgetcapability)。
原完整 POSIX 超时、BusyBox 当前拒绝、runner/CI、服务恢复及宿主重启验收仍未关闭。

七份本阶段工具的最终完整 Ruff/format 检查通过；原已执行源码副本、初次格式问题
和失败输出均保留，后续格式修正未重跑业务。树外 v9-current-reentry-001 封存实际
证据、工具、独立回读和后续最小修复方案，共 239 文件；manifest 摘要
`caa9f4649587c3e702cbad59ae48279d9d4d8d4e07ea8ed365b60c194a0f14fb`，
归档 1,556,480 字节，摘要
`3d62b13f6d70f80c7db4c337ef0f7d37071c52964911f4dd194390122a394402`，完整回读通过。
阶段 53 快照绑定本次文档提交、封存包及阶段 52 快照。三份既有未跟踪计划保留，
TASK-0048 继续 IMPLEMENTING，未填
implementation_result；任务 02 未完成。

## v10 就绪握手、Linux 全测试及两条 root fixture 实际通过

阶段 54 按已批准的传输与执行范围，完成最小可信 READY 握手。并行准备使用两名
sub-agent，分别负责发布端与接收端实现、测试和交叉审查；主会话负责固定交付包、
运输、镜像及配置。固定来源后，安装、Linux 测试、镜像构建、配置、工具语义、
preauth、Dash、BusyBox 及各自回收严格串行；最终再并行独立回读与下一入口差异定位。
目标仓、runner 服务和 CI 继续只读，未注册、切换、推送或触发。

发布端在初始化后，以 0600 独占临时文件完成写入和已知关闭，再原子发布六字段
`ready.json`。接收端通过固定 procroot 路径读取，核单链接普通文件、UID/GID、
大小、完整 EOF、稳定身份、engine/nonce/start_tick，并先关闭自己的临时 FD。
只有 READY 完成后才进入原两次内核/FD 观察；tick 与两次观察相同，原 guard 关闭、
同一 READY 再核后才可 permit。preauth 仍不发 permit。原 20 秒启动窗口、屏障
60 秒及 fixture 600 秒预算不重置、不提高；FD 变化仍拒绝。新增 READY 不替代原
source/interpreter、namespace、mount、cgroup、seccomp 或清理证明。

本机完整 suite 为 358 PASS、16 项 Linux 专用 SKIP。最后一处测试输入路径改为
包内固定旧源，仅复核受影响的 AST 单项；此前全套记录仍绑定当时字节。最终冻结包
23 文件、317,440 字节，归档摘要
`87b36caa95aa650a7e73d8b3cec3a6f441783a40e54332eeab3bc985dc2be1ee`。
guest 安装全量核对后，以 UID/GID 1001 实际运行全部 374 项，11.62 秒，零失败、
零错误、零跳过。完整 XML 57,350 字节，摘要
`c4f557d960f1d3bdc592078d6e84d11ba72f62e186ba26fe06b8934d71eebdb1`；
独立核对测试 nodeid 无缺项、重复或额外项。本机跳过未被算作 Linux 成功。

首次构建前的 image inspect 因继承 SSH 的不可访问工作目录而被拒绝，尚未启动
build。保留该失败及已写的新 context；第二次使用独占新 context，固定所有相关
子进程 cwd，实际构建成功。镜像仅从固定 v4 增加新 barrier COPY，无 RUN、安装、
联网拉取或入口改变。新 image ID 为
`sha256:552f8d5d1af5f07bf08f64e6d7770441f2cbdb8ade489893222d0c198da5cd50`；
新屏障摘要为 `1305cf24f8cdbb057c14716739553188cfc5f25ef6361c9a65ee5a3b52a0a36e`。
新配置只改变 image_id/barrier_sha256，摘要
`106f1023101837d9d1d881141c5742ea89aeb373560545bb9072018d7955f22c`。
原 source、v9、配置和失败回执均保留。

镜像内实读 barrier 为 root 所有、普通文件、0444、10,525 字节，内容摘要匹配。
原工具语义脚本仅迁移唯一旧 barrier 输入摘要，规范化 AST 与原全部检查相同；
执行源码摘要为 `a679be45c2711cad148d7b1ebd1dd83c6ec442115af6de95edc428ce8f58cf69`。
原 38 项由 UID/GID 1001 的 rootless Podman 启动，在容器 UID 0、无网、只读 root、
默认 seccomp 和空 hooks 条件下全部 MATCH；
总 120 秒、单项 10 秒、attach 145 秒保持，330 秒运输外围容纳既有准备及精确清理。
这项是工具语义检查，不计为业务 fixture 或完整 POSIX Gate。

| 当前 v10 执行 | 实际结果 | 输出与清理 |
| --- | --- | --- |
| preauth-001 | PREAUTH_PROOF_COMPLETE；两次 FD/内核准入通过 | 无 permit、无 fixture；attach 125、drain 完成、精确 CID 清理 |
| Dash-001 | PASS；27.626 秒；fixture/attach 退出 0 | 原四用例、205 字节五行；无超时、溢出、残留，清理完成 |
| BusyBox-001 | PASS；28.240 秒；fixture/attach 退出 0 | 原四用例、205 字节五行；无超时、溢出、残留，清理完成 |

三次 READY 分别为 159/159/166 字节，0600、UID/GID 1001；每次 nonce/start_tick
与当次内核及两份 FD 记录绑定。两次 FD 集合均为 0/1/2，原比较通过；未忽略旧 FD 3，
未覆盖阶段 53 BusyBox 拒绝，也未把此次成功当作完整启动竞态的唯一因果证明。
每次仍只保存一份完整内核观察及两份 FD 记录，另加原 READY 和读取元数据。
语义、preauth、Dash、BusyBox 分别回收 22/45/49/46 文件，共 162 文件、471,369
字节。完整集合、长度/SHA、真实 EOF/stable、各命令两流、结果和清理链已由主核验
复核；主核验结果摘要
`37b500d6314bb9c0852ca227289c891f7573b732b7c064c73fc7163165116a89`。

17 份运输、准备及核验 Python 工具及新增封存修订完整 Ruff/format 通过；运行源码 suite 和
新增握手反例在上述 Linux 374 项中验证。未为文档追加重跑本仓全部质量矩阵，也不
将树外 suite 当成本仓覆盖率或完整 POSIX Gate。下一步是将原完整本地入口绑定到
固定 v10，再按原检查和预算取得新完整回执。原完整 POSIX 超时、受控 runner/job/
attempt、目标采用及后续 CI、真实服务恢复和执行宿主重启业务仍未关闭；TASK-0048
保持 IMPLEMENTING、Missing implementation_result，任务 02 未完成。

独立实际复核无新增阻断，报告摘要
`5a1600882af8cfeb0a70b8c5480f2b187e16c4348ddd1ad0920888334248e799`。
首次封存遇到 pytest scratch 的 current 目录链接而停止，未生成 manifest；保留
部分目录和失败说明。新封存仅排除三个明确的 pytest tmp 目录，源码、测试定义、
原版本输入、源快照、JUnit、两流、审查和全部实际 guest 证据保留，未跟随链接。
v10-barrier-ready-002 共 407 文件；manifest 摘要
`a14cfbafcaf12f005ede18b41d67e887277e1aefaa46613f20fd3cea44fba954`，
归档 5,048,320 字节，摘要
`5257df329eb4adca2d7f769904cd620f4746dae2a792b7c53c367216e1c12be1`，完整回读通过。
阶段 54 快照绑定该封存包、本次文档提交及阶段 53 快照；三份既有未跟踪计划保持。

## v3 完整历史 POSIX 入口接续

阶段 55 将原完整本地入口绑定到已核定的 v10 READY 运行时。并行准备启用两名
sub-agent，分别负责最小候选迁移及运输/审查；主会话核对固定源码、交付包和实际
环境。安装、Linux 测试、新合同生成、源码核验及完整门禁按依赖串行执行；运行期间
两名 sub-agent 分别准备完整回收及独立核验。目标仓、runner 服务和 CI 继续只读。

候选仅改变三个运行文件中的必要固定路径、版本及摘要，八文件运行集合不变；
原 receipt 校验器、三个前置步骤及 binding fragment 保持字节一致。原 gate 的
检查集合、45 个 shell 文件、17 个 shell fixture、五个 Python 文件、两份 Python
测试、八个便携 PowerShell fixture 和平台声明保留。每 fixture 600 秒、步骤
02/03/04/05 的 600/300/300/10800 秒、总任务 21600 秒及 kill-after 30 秒均未提高。
旧完整 POSIX 的退出 124 和当时限制保持为独立历史记录。

候选交付闭集 151 文件，归档 2,785,280 字节，摘要
`e11f4a1023b7c2fffcca552b94b8f85b6bd99dddb6d4de91af643242fe2e9107`。
主会话及独立审查逐项核候选、归档与交付清单；另固定实际运输的 27 文件输入，
其中八个运行文件。运输归档 798,720 字节，摘要
`651536eefc031366e1d829d9e86f1bd314134fc58039095ed839e3ade4fbce96`；
manifest 摘要 `26fe6642d01627292de86d3557f8caf2295074faf39dab24df0e1c0fbbdeddfc`。
安装使用独立 v3 目录，源码与运行文件均完整回读，root 所有、0444，目录 0555。

本机原 163 项测试保留，155 PASS、八项仅非 Linux 条件的 SKIP。实际 guest 以
UID/GID 1001、附加组 100/1001 运行全部 163 项，零失败、错误或跳过；XML 时长
18.603 秒。完整 XML 22,159 字节，摘要
`787ae8152b29eed15e1f3f1375be4512cd46554dc357d47ccac8bf3d672b5e26`，
与运输原 stdout 中的 base64、测试计数及原 163 个唯一 nodeid 完全一致。
这组验证属于本地入口源码测试，不能代替下面的完整业务执行。

新合同由实际 guest 准备并独占写入，4,882 字节，摘要
`1e97193c07fcb324d24c6e9bae7221c68a57c2457322d11603b4ba9a2ffbde15`。
独立复原原 4,876 字节 `b089fcaf` 合同后逐字段核对：23 个键全部保留，恰好七个
必要字段更新，21 项原 tool_files 摘要不变且实际逐项回读匹配。新合同绑定原
`cd02cb3c` 的 155 文件来源、同一 checkout、固定 v10 adapter、READY barrier 与
新镜像。执行前低权限源码核验退出 0，明确 `executed=false`。

本次完整运行原生退出 **124**，运输未超时，用时 1,878.422 秒；步骤 02/03/04
均退出 0，步骤 05 的原生文件及 JSON 均记录 124。最终 `result.json` 未生成，
完整历史 POSIX Gate 仍为失败。组合日志确认 45 文件静态检查、17 个 shell fixture
的双 engine、两份 Python 共 27 项及前五个便携 PowerShell fixture 通过；业务
Python 零跳过。依据原固定执行顺序与最后的 secret-scan 成功行，停止位置指向第六个
current-state fixture；本次没有单独的 PowerShell 进程或用例时点采样，不能确证
具体超时用例、唯一原因，也不能把后续两个 fixture 计为已执行。

| 本次完整运行内的新 root 组件 | 实际结果 | 证据范围 |
| --- | --- | --- |
| Dash | PASS，28.499 秒，fixture/attach 退出 0 | 新 nonce，原四用例/205 字节五行，精确 CID 清理完成 |
| BusyBox ash | PASS，27.948 秒，fixture/attach 退出 0 | 另一新 nonce，原四用例/205 字节五行，精确 CID 清理完成 |

两个组件均无超时、溢出、取消、剩余 PID 或残留路径。各自 READY 的六字段、0600
单链接元数据、nonce/start_tick、两份仅 0/1/2 的 FD 观察与当次完整内核记录一致；
每个组件 13 条原生命令及其两流、attach drain、终态 inspect 和精确 rm/不存在
回读均匹配。仍只保存一份完整内核和一份初始 READY 原文，不宣称第二份完整内核或
末次 READY 原文已独立落盘。两组件通过不能代替失败的完整门禁。

实际行为限制另行保留：原清单仍声明九个 Windows 专用 fixture 排除；因本次没有
最终结果文件，未把这些声明写成已完成的最终结果。secret-scan 原输出明确
Git-index/reparse 部分为 `skipped-posix-lane`，非 Git 的 rg-ignore 用例为
`dependency-missing`；两条 AWS hardening 行保留 `signal=skipped-host-signal`。
runner-health fixture 标记 `synthetic=true isolation_verified=false`。这些限制不被
各自 PASS 标记覆盖，也不计为真实 runner 隔离、服务恢复或全行为零跳过。

执行后以相同固定请求及原预算再次进行低权限源码核验，退出 0，1,124 字节 stdout
与执行前完全相同。独立只读回收保存本次 run 的 24 文件及两个组件各 49 文件，
共 **122 文件、324,282 字节**；727,406 字节原始回收响应摘要为
`50ebf12d2d84479bc9ffe6521bfff8eec22081d43875f03f816f647d3327c27f`。
逐文件 base64、长度/SHA、真实 EOF/stable、闭集、14 个可信输入及末次整 run 回读
全部核对。原 receipt 校验器重新验证两个组件；材料核验因缺 `result.json` 保持
失败，回收成功不翻转原生 124。

主会话另用专门的失败核验入口联结固定收集器、实际请求、boot、合同、manifest、
原运行运输记录、完整回收和源码 after；未调用原成功专用核验入口。主核验结果
17,797 字节，摘要
`dfdf7821beb67705bd5e5267f49b5c72e7c26cd7e958aa5b245971c6353e1a8c`。
两组件的精确清理已核，本收集器没有做 whole-guest 进程/Job 空闲盘点，不将其
表述为完整 guest 已无剩余工作负载。

最终 20 份本阶段 Python 工具及实际绑定的收集请求，完整 Ruff/format 均通过；
初次 17 文件结果及新增失败核验前的源码快照保留。本次文档追加未重跑本仓完整
质量矩阵，树外 Linux 163 项不替代本仓覆盖率或正式 V2。TASK-0048 继续
IMPLEMENTING，Missing implementation_result；任务 02 未完成。

后续先核对执行结束后的实际空闲状态，再做最小有界环境诊断。当前 QEMU 二进制
只读 `-accel help` 退出 0，列出 TCG 与 WHPX；它仅证明编译支持。阶段 53 的 WHP
能力查询也不能证明实际加速器初始化或 guest 性能。保留原 600 秒预算，先取得
真实初始化证据再决定受控环境调整；本阶段未启动新加速器、重启 guest/宿主、修改
目标仓或触发 CI，不以再次执行相同入口替代问题定位。

独立执行复核确认上述失败和有限通过结果，报告摘要
`a1c1b19f1c4edffaa2f0c3df7f46240531d1311226aa9fdab77157dd80db0ea2`；
下一步最小诊断文件摘要
`e9bccb2bd5c03fada412db5e76323211c49ba9fb829b9fc86b394717abc557c1`。
树外 `local-posix-v3-001` 封存 386 文件，manifest 摘要
`a9efac52b32429d978186abe74fcd9478561283c86f955a72d805ce5d10d3c14`；
归档 8,345,600 字节，摘要
`1ff35baef2242e9426843a90d68abe6bac7a72558044ef54a175ee5df664bfe6`，完整回读通过。
阶段 55 快照绑定本次文档提交、该封存包及阶段 54 快照；三份既有未跟踪计划保留。

## 退出后的有限观察与 WHPX 初始化

阶段 56 延续已授权的传输与执行。两名 sub-agent 并行准备结束状态观察和无磁盘
WHPX 探针，并交叉审查；主会话复核固定输入，按“guest 观察 → host 探针 → 原始
证据回读”的依赖串行执行。原 guest 未停止或重启，目标仓、runner 服务及 CI 继续只读。

guest 请求固定为 18,343 字节，摘要
`8083f0bf91f06674760d96b314838111b8c5413a04372ff1eda59774d8227a05`。
当前 boot、原 Python/timeout、v10 adapter/合同和 Podman 依赖均匹配。请求只采集
UID1001 的进程元数据、既有 system/user bus 的 ListJobs，以及固定 store/runroot
的容器、Pod 和两个阶段 55 CID 状态。未读进程参数或环境；Podman 的逻辑查询可能
更新运行时记账，不宣称 guest 零字节写入。观察逻辑 108 秒，每查询 8 秒、kill-after
1 秒、捕获 10 秒及有限收尾；外围 120/10 秒、SSH 145 秒，host 前置另有 30 秒。
这些是新诊断预算，原 fixture 600 秒与完整门禁预算保持不变。

实际观察退出 0，无运输错误，含 host 前置用时 10.235 秒。stdout 14,262 字节，摘要
`a5074396695bdd7832cbd7630b2adba6bd43b0fde17af2f20caa4342ad40d2a6`，stderr 空。
两次各盘点 121 个 PID，均仅发现四个 UID1001 进程，身份配对一致、样本稳定、无
unknown；可执行文件、comm 与 cgroup 符合用户 systemd、PAM、Podman pause 和
用户 D-Bus 基础设施的特征。这是元数据解释，不是完整角色认证；两个采样点未发现
该 UID 的 fixture 进程，也不能排除其他 UID 或采样间的活动。

六个查询均完整回收双流，无超时、截断或收尾错误。system/user Jobs 均原生退出 0，
返回精确空列表；容器及 Pod 列表为空。两个固定 CID 的 exists 均原生退出 1、两流
为空，确认其不存在。原报告的 whole_guest_idle 仍为 null，不将有限观察升级为
整台 guest 空闲证明，也不停止被观察到的基础设施进程。

WHPX 最终探针 14,069 字节，摘要
`00e344216e491632de3fee4b86b638c2eec348abeb47ef5d05f574f7260d8972`。
它使用同一固定 QEMU、独占输出、干净环境及 no-user-config，明确选择 WHPX；
没有磁盘、seed、网络转发或 TCG 回退，单 vCPU、256 MiB，CPU 保持暂停。总探针
预算 20 秒、两流各 256 KiB，并为仅本次原 process handle 的有限收尾预留 2 秒。
交叉审查修正了 reader 启动失败的记录及身份登记顺序，实际使用修正后的固定源码。

实际探针 **退出 0、0.203 秒**，另计 host 前置 1.047 秒。原始 QMP 输入 198 字节，
依次为 capabilities、status、cpus-fast 和 quit；返回 running=false/prelaunch，
只有一个 cpu-index 0，模型为默认 qemu64。随后收到 host-qmp-quit 事件及 quit
回复，完整双流 EOF，未使用 terminate，无 primary/secondary 失败。stdout 649
字节；stderr 129 字节保留 `Ignoring request for interrupt vector 0` 警告。
这证明无盘、暂停 CPU 的 WHPX 初始化和正常退出，不证明 Linux 指令执行、启动、
性能或该默认 CPU 适合最终 guest；后续 CPU 选择仍需核定。

主会话及另行回读复核原始输入、两流长度/SHA、六项查询、QMP 回复与真实退出。
主核验还在探针后重新确认原 QEMU 身份和 SSH listener；结果 5,015 字节，摘要
`0df5beb5b4ef36c6ed6327a6a779398890f20487ef89ffc93adede38fd12cff2`。
结束状态另行回读者也是该观察器作者，WHPX 的交叉审查者不是探针作者；两者职责
如实记录。五份本阶段 Python 工具的完整 Ruff/format 均通过，未重跑本仓完整测试。

树外 `whpx-init-001` 封存 80 文件，manifest 摘要
`8067c14088d13c836047f89a869301c87127c6a625dda653292da078d4bf1081`；
归档 327,680 字节，摘要
`4eb437fd39b1ab90f787029243ebcbe290d7bccfb61d976c62d8632713935ca7`，完整回读通过。
阶段 56 快照绑定本次文档提交及阶段 55 快照，三份未跟踪计划保留。阶段 55 完整
POSIX 的退出 124 不变；TASK-0048 仍为 IMPLEMENTING、Missing implementation_result。
下一步先核 CPU 兼容与停机前材料保留，再准备受控 guest 切换；未完成这些前置前，
不把初始化成功当作新 Linux 环境或任务 02 验收完成。

## WHPX 实际启动与阶段 57 收尾

阶段 57 在既有传输与执行授权内推进：两名 sub-agent 分别准备 CPU/保留材料与
冷启动方案并交叉审查；主会话依赖前置结果，串行完成有限保留、正常关机、冷备份、
镜像检查和新启动。随后用户要求在最近节点收尾，本轮停在新 guest 启动及首次严格
SSH 身份确认，不再启动后续 fixture。收尾由一名 sub-agent 封存材料，主会话记录
待办和提交；这些工作相互独立，提交快照依赖封存和文档提交完成。

使用 `-cpu host` 的无盘 WHPX 探针退出 0、0.187 秒，QMP 确认 host CPU 模型、
暂停状态和正常 quit；stderr 保留同一 interrupt vector 0 警告。随后旧 guest 的
观察确认 store/evidence 是持久 ext4 loop 卷，其 backing 位于系统盘；runtime
为 64 MiB tmpfs。有限树共 17 项，其中 9 个常规文件总计 66 字节，均完整保留并
回读，另 8 项是目录。两次元数据一致，但不证明整个 guest 或内核状态已保存，
也不将锁文件字节视为锁状态。新 boot 不自动恢复旧 PID、锁或运行目录内容。

在固定原 host/boot、重新观察原四个低 UID 基础设施进程及六项查询，并核定
systemctl 字节后，仅发送一次正常 poweroff。SSH 与 systemctl 均退出 0；最终
观察原 QEMU 与 listener 消失，串口到达 Power down，未强制终止。旧 QEMU 原生
退出码仍为 null，未将进程消失改写为退出 0。关机终端记录摘要
`3e57faa10db2afeb470d2df0cd22d82f85615249c8494b9b689679c6980882d0`。

停机后以独占源句柄复制恢复磁盘，目标 CreateNew，源元数据前后稳定，目标完整
回读与另行独立复核一致：4,783,931,392 字节，摘要
`8e57f62e82a936e004175b85b7ecd6a4f4a428ae1d62c24a98644af1f301a62d`。
恢复副本位于树外 `vm/recovery/stage57-before-whpx/`，没有执行恢复。原磁盘的
两层 backing chain 与无修复参数的 qemu-img check 均退出 0，无已报错误、损坏
或泄漏；固定基础盘、QEMU、kernel/initrd/seed 的摘要核验通过。独占冷读取句柄
释放后到 QEMU 打开之间不宣称原子交接。启动后不再读取或 hash 运行中的原磁盘。

新启动明确选择 q35、WHPX、cpu host、2 vCPU、4096 MiB，保留原 kernel/initrd、
seed、系统盘和 noapic 参数，无 TCG 回退，未重启 host 或更改 Windows 功能。
启动记录摘要 `e7e4295b2a7f52444cea657a842c6658377cd042688d1b20df1227d7df0d551e`。
初始三秒日志为空不能解释为启动停滞；后续串口到达 cloud-init 完成和登录提示。
首次严格 SSH **退出 0、0.656 秒**，stdout 242 字节，确认新 boot、原 Linux
6.8.0-139-generic、x86_64 和两个在线 CPU；stdout 摘要
`3d0c24ae64122d9bd1bf58f4697d8f88ebc8cf429e9213b0752efc9bf2aae405`。
该查询使用 provisioning UID1000，不能替代 UID1001、sudo、挂载、源码或完整运行
合同准入。收尾仅复核新 QEMU 原身份仍在，guest 保持运行，未再发起测试或重启。

保留本轮过程缺陷：runtime 保留运输初次 Ruff E501/format 未通过，但后续命令仍
执行了只读观察；实际源码留存，随后仅格式化并通过检查，前后 AST 一致。不得称
该次执行前格式检查通过，也未重跑以替换原记录。冷启动独立复核曾把多 JSON
观察记录误按单 JSON 解析，修正解析后核验通过；这不是原生执行失败。树外启动
目录中名为 `%SystemDrive%` 的未知目录保留，未遍历或判定成因；封存排除它。
运行中的 QEMU 日志只保存当时有限字节，不声称 EOF 或最终状态。旧禁止读取的
XML 未读，三份既有未跟踪计划保留；目标仓、runner 服务和 CI 仍只读。

### 后续待办与恢复顺序

树外 `tools/stage57-handoff/NEXT-STEP.md` 是本节点恢复入口，记录新 PID/创建时间/
boot、实际证据位置、恢复副本与原工具摘要。恢复时先重查身份，不能沿用旧 host
guard，也不能直接重放本轮关机或冷启动脚本。按以下依赖继续：

1. 串行重核 Git、最新阶段快照和 TASK-0048，再核当前 host/SSH/boot，最小派生
   新绑定的 guard，保留全部身份断言。未知或变化先核定，不以历史状态代替当前值。
2. 串行核新 boot 的 UID1001、组、sudo 禁止策略及三个独立挂载合同。fresh tmpfs
   如缺已知 runroot/tmp 子目录，只在合同成立后按原所有权/权限创建；不恢复旧锁。
3. 此时可用一名 sub-agent 并行只读审查请求与固定 source/runtime/v10/image/policy
   摘要，主会话处理 readiness；执行仍串行。通过后先运行原 v3 verify-source，
   再运行原 current-state fixture 单项，保留 **600 秒、kill-after 30 秒**、全部
   原断言、原始双流、真实退出和完成 marker。若仍超时，按阶段 55 NEXT-STEP 准备
   非验收的最小逐 case 观测副本，不延时、不删检查。
4. 只有原单项通过，才开始一次未缩减完整 POSIX gate：fresh root 组件、所有检查
   和 source-before/after，保留原 step/job 预算，不拼接历史 PASS。随后补齐必要
   本仓质量验证及真实实施结果，按 CLI 当前输出推进账本。
5. r3s-VPS 的并发处理交接仍待完成；目标仓继续只读候选。runner 注册、服务切换、
   CI 触发、push 和采纳尚未执行，实际接入及任务 02 最终验收仍在后续范围。

本轮未重跑本仓完整测试。阶段 55 完整 POSIX **退出 124** 不变，TASK-0048 仍为
**IMPLEMENTING、Missing implementation_result**；用户要求的预算收尾不代表任务
完成或技术阻塞，不补写成功结果，也不创建自动续跑。

树外 `whpx-boot-001` 封存 200 文件，manifest 摘要
`f917615c0d835efff4bdf1a8e5c1ac82ecb2da9ca65d82533c11f9f03f9a642a`；
归档 819,200 字节，摘要
`dde290db2228f684f6ade79fc57810d4f8fda41cf867cc490138b7aff31a16b8`，完整回读通过。
恢复入口 NEXT-STEP 摘要
`347bbe4cd341f8e0e1bad4aa54b25dadb49a53ce5dd16e8adfbfe12c715b5fbd`。
阶段 57 快照绑定本次文档提交、封存包和阶段 56 快照；本轮只有该文档追加入库。


## 阶段 58：恢复实例与固定历史源码完整 POSIX

2026-09-20 所有者明确要求执行下一步。本轮沿阶段 57 接续本地恢复、readiness、原单项
与完整 POSIX；外仓、runner 服务、CI 仍只读。恢复准备由一名 sub-agent 只读审查，
随后并行准备 readiness 与证据回读；主会话串行启动、修复两个已知运行目录并执行。
后续按需反馈文档工作单独提交，不混入本治理单元或其运行时范围。

### 恢复与准入

现场未发现 QEMU 或原 SSH listener；阶段 57 实例的退出方式与原生退出码未知。
本轮没有重放旧关机/冷启动脚本，建立全新的 stage58 工具、输出与恢复副本。
确认空间和内存后，以独占源句柄冷拷当前磁盘，源/目标摘要与元数据核对一致；
保留旧 stage57 副本，不恢复旧盘、不覆盖历史输出。新副本 4,788,387,840 字节，
原 base、QEMU、kernel/initrd/seed 摘要仍匹配。双层 qcow2 链及无修复参数的
qemu-img check 通过；独占句柄释放到启动仍不宣称原子交接。

新启动保持 q35/WHPX/host CPU、2 vCPU、4096 MiB、noapic、原 loopback SSH，
无 TCG fallback。原始进程句柄绑定 PID/创建时间/EXE，严格 SSH 取得新的 boot，
Linux 6.8.0-139-generic、x86_64、两个在线 CPU。启动回执摘要
`3ba251a5c7d3f3cbe5ad56899cda5c78ff6027b81e3f6992ac238e208449e011`。

首次 readiness 只因新 tmpfs 中缺少 runroot/tmp 两目录而拒绝；身份、组、sudo
禁止策略及三卷合同均通过。重核同一新 boot 与完整前置后，降为 UID/GID1001，
使用 nofollow 目录句柄仅创建两个 0700 目录，未恢复旧 PID/锁/socket/运行内容。
独立第二次 readiness 退出 0；原 v3 verify-source 仅替换 BOOT，在原低权限路径
执行退出 0，源、runtime、合同和 adapter 准入通过。

### 原单项与完整执行

原 current-state fixture 四项输入摘要不变，命令仍为 timeout 600 秒、kill-after
30 秒的原 PowerShell fixture。新封装保留完整 root source_checks、降 UID/组、
关闭附加 FD 和干净环境，执行前后调用原 verify-source。审查发现初版用完整
stat_result 比较会受访问时间影响，执行前改为稳定元数据元组；旧候选未执行且保留。
最终单项 **54.484 秒、原生退出 0**，原唯一 PASS marker 存在；原日志记载
invalid_cases=70、hardlink=tested-pass、ps51=skip-non-windows。源码前后相同，
无该进程组或新增 fixture 临时目录残留；12 份原件已回读核对。

随后一次完整运行的实际 run_id 为 `95909287c8904ceda8bbb57d7edcc827`，
完整 SSH 传输 **246.968 秒、退出 0**。这包含启动与运输开销，不冒充单 fixture
耗时。Step 02/03/04/05 均原生退出 0；原内部预算 600/300/300/10800 秒和
job 21600 秒、kill-after 30 秒保持，未拼接旧 PASS：

- 清单保持 shell=45、shell fixtures=17、Python=5、Python tests=2、portable PowerShell=8。
- 两套本次新 root fixture 各执行四用例，Dash 4.857 秒、BusyBox ash 4.640 秒，
  原五行输出逐字节匹配；不同 nonce、内核与 FD 证明、真实退出和精确清理均核定。
- Python 原两组 18/9 项均通过、零 skip；8 个 portable PowerShell fixture 全部走完。
- 原最终 marker、四份 step 原生退出和结果文件一致；explicit_behavior_skips 为空。
  原 fixture 内的平台限定说明保留，不升级为 Windows 专属路径已经验证。

终态 collector 回读 run 25 文件/53,156 字节、Dash 49 文件/141,792 字节、
BusyBox ash 49 文件/142,075 字节；原文件/目录上限、摘要、稳定读取、最终重读及
原组件校验器均保留。随后重新执行原低 UID verify-source，前后双流逐字节一致。
本地核验器连接实际 run、传输、原件、root 组件、markers、source-after 和新 boot，
核定 **historical_cd02_local_only PASS**，不是正式任务 Gate。

完整运行传输回执摘要
`1f8f588f32aa70b150500e93588ba5738a004b961d4d70f52bb1baf397d2e41b`；
source-after 回执摘要
`1c620bb1bd533fd0819946a6616e75dce355a1ec7834920baa8d120d3baeea7f`；
组合核验结果摘要
`83db3db6044a55099ea10369d5a012c4e66d91dd59c8b2981fbeaa0208ebf666`。
树外原件位于 stage58 各独占 evidence、stage58-single-fixture 与 stage58-collection
工具目录；实际实例信息留树外，不将机器或密钥路径写入本仓。

### 结论与下一边界

阶段 55 的旧失败 124 不变，本次证明在新 WHPX boot 下固定历史 `cd02cb3c` 的
完整本地 POSIX 能通过，不能仅据此认定旧失败只有一个原因，或量化性能/可靠度改善。
执行未读运行磁盘、私钥正文或禁止的旧 host-tests-001.xml；准备 collector 的一次
宽范围搜索意外匹配另一份 package/host-test-result.xml，未使用其结论，后续收窄
文件清单。准备期格式检查失败已在执行前修正，不写成首次即通过。

guest 保持运行供后续接手；原始运行日志只按有限时点保存，不把进程存活当生命周期
验收。没有注册 runner、切换服务、触发 CI、push、修改目标工作树或启动生产操作。
目标当前提交的重绑与验证、同 SHA 双 lane、main 采用、真实服务恢复/重启验收和外仓
持有者交接仍缺失；TASK-0048 仍 IMPLEMENTING / Missing implementation_result。
本轮执行记录先固定为候选提交，再在其干净检出运行原完整本仓质量门，结果保留树外
阶段 58 质量回执；该软件验证不补签外仓 CI、任务 Gate 或阶段三/四。

## 阶段 59：完成交接、当前源码验证与独立接入候选

2026-09-21 所有者明确说明原任务已结束并由本会话接手，目标仓的写者交接阻塞解除。
目标原工作树的状态文档及 manifest 两份既有修改保留；本次 workflow 改造使用独立
候选分支。准备阶段启用两名 sub-agent，分别负责绑定材料和独立审查；主会话串行
处理实例恢复、安装及运行，并并行推进目标仓完整 Strict 与本仓记录。

### 新实例与当前源码

首次沿旧实例发起的身份请求在打开原进程句柄时失败，尚未进入 SSH；现场随后确认
旧 QEMU 和 listener 已消失。原因及原生退出码仍未知。新恢复先独占冷拷，保存
4,839,964,672 字节的新副本并核对摘要、磁盘链及只检查模式结果，不覆盖旧副本。
审查在执行前发现辅助脚本仍引用上一阶段路径，修正后才启动；失败候选保留。
新实例继续使用 WHPX、原受限卷和严格连接身份；readiness 仅补建新 tmpfs 中两个
缺失目录，随后独立检查通过，未恢复旧 PID、锁或运行内容。

本轮从目标已提交的 `39cc7ff1622740cf1d28f1ce3022cf4701df90a1` 直接导出 166 个
Git 文件，165 项业务 manifest 全部匹配，不包含原工作树未提交字节。源码包摘要
`a32f1404311a4c07d93c896d3be2129349def2f2bd94251f5e86cb072cb10696`。
新路径重绑 source、合同、runtime 和 adapter；adapter 仅替换三个源码常量。
低权限完整运行的 run_id 为 `2246970fd54e4c28b8f86faca263765c`，完整传输
**279.906 秒、原生退出 0**，Step 02/03/04/05 全部退出 0，原时限不变。

- 本次运行清单为 shell=48、shell fixtures=17、Python=7、Python tests=2、portable
  PowerShell=8；两组 Python 共 27 项通过，无 skip，8 个 portable fixture 全部走完。
- Dash 与 BusyBox ash 各执行四个 root 用例，分别 4.585 秒和 4.239 秒；各自五行
  205 字节日志精确匹配，nonce、内核与 FD 证明、真实退出和清理结果通过。
- 终态回读 run 25 文件/52,846 字节、Dash 49 文件/141,793 字节、BusyBox ash
  46 文件/126,206 字节。文件数差异来自实际观测次数，不复用上一轮计数或 PASS。
  运行前后源码双流一致；组合核验摘要
  `2833315a0c6837869895deb25f03194994f07f980d314543c4cd6a55f542778c`。

该结论是 **fixed_39cc_local_only PASS**。阶段 58 历史源码、当前 39cc 源码及下面
的新接入提交分别绑定，不将其中一项升级为另一项的通过证据。

### 接入候选与实际接口问题

独立候选提交为 `949fc6036a95e5c1ed55c4d5d5f96793ba42670f`：增加可信私有
Linux lane 的固定合同、工具与源码检查，保留 Windows 路径及原检查标准；同步
actionlint 标签、使用说明和三个 manifest 摘要。checkout 前只核验私有仓所有者与
低权限身份，源码与提交绑定在 checkout 后执行，不声称 checkout 前已经核验源码。
本文固定时该提交的完整本地 Windows Strict 正独立执行，尚未取得最终退出回执；
终态结果待核并留存树外，不能用已有 39cc Linux 结果代替。

安装前主会话发现 generic CI checker 仍读取旧版 fixture 的 `result` 和
`observed_exit_code` 字段，而 v10 实际回执使用 `fixture_exit`。独立审查复现
两个真实回执均被旧 checker 拒绝；此前包完整性审查未覆盖这一接口缺口，已追加
纠正记录并暂缓旧包安装。新候选仅修回执兼容与严格字段检查，通过实际 39cc 双引擎
回执回放及失败变异测试后重新绑定合同；旧候选与失败证据均保留。

修复共 53 项专项测试通过，仅改变 `check_receipt`；独立审查通过后新安装请求
`install-ci-002` 实际退出 0。新合同摘要
`675eb603c65076635798ab940ea07e2c266c9b792b0dfaff72a5ff02c202502c`，
checker 摘要 `abf11dbc6bf2f72a280492a2f18316433c25d19f4ab09f7ce8504520097a1371`。
新提交的实际低权限 source/runtime/adapter preflight 退出 0，随后两个新的 root
fixture 各四用例通过，Dash 4.265 秒、BusyBox ash 4.207 秒；修复后的 generic
checker 实际读取新回执通过，执行前后源码仍匹配。该次双引擎外层总预算为 1500 秒，
adapter 各引擎内部 600 秒不变；这只验证新提交的 root 组件和回执接口，不冒充原
workflow 的外层预算、完整 POSIX 或真实 GitHub event。没有伪造 event/run 环境。

### 尚未取得的结果

官方 runner 2.337.0 的已安装文件匹配，现场本地检查为 UNREGISTERED_LOCAL，
无 Listener/Worker。只读 GitHub 观测仍只有原 Windows runner；这些是当次状态，
不构成之后服务窗口的持续授权或空闲证明。本轮未注册 runner、切换服务、push、
触发 CI 或修改生产设备。新候选的真实 GitHub event、同 SHA 双 lane、main 采用、
服务恢复与重启验收仍需后续真实证据。

TASK-0048 仍为 IMPLEMENTING / REVIEW V2 / Missing implementation_result；
分类 fresh、批准 current 不代表实现完成。本阶段文档提交固定后执行本仓原完整质量门，
其结果仅证明本仓软件检查，不补签目标 CI、生命周期验收或任务 Gate。


## 阶段 60A：真实 CI 启动与注册前恢复机制实证

2026-09-21 所有者进一步明确“充分授权，你来完成”。具体外部动作仍按当次实例、
源码和请求摘要分别记录 action；此授权不替代技术验收。阶段 59 的独立候选
`949fc6036a95e5c1ed55c4d5d5f96793ba42670f` 完整本地 Windows Strict 已实际退出 0，
耗时 2225.828 秒；本仓 `49d45d7cee9ecf76a5d59c8ff27ebcddf2e56690` 干净检出
105 合同测试、1945 完整测试及全部质量检查通过，总覆盖率 88.12%。这些回执绑定各自
原提交，不冒充后续提交或真实 CI 结果。

本次只推送已审候选分支，目标 main 保持原提交。真实
[CI run 35547201811](https://github.com/MaginaLW/r3s-VPS/actions/runs/35547201811)
已由 push 触发并绑定同一候选 SHA；本段固定时 Windows 完整门禁仍执行中，Linux
job 排队。Linux 尚未注册或启动 Listener；未因 Linux 准备工作停止忙碌的 Windows。

### 实际失败与恢复

原低权限注册检查仍保留。新的无令牌静默窗口先使用独立 PID1 服务与定时器验证恢复
机制。首次惰性演练因同时停止 worker 与 recovery、退出钩子重启 recovery 而失败；
修复为串行停止和真实 PID/Job/cgroup 回读后，定时器及 SIGKILL 两案例均通过。
实际结果摘要 `94505ffd2150aada7a7b5d916ff5ded6304b3353ee53f26f2a30746a0b62712c`。

静默窗口候选的首次只读预检发现固定 32 MiB 读取上限小于已固定 Podman 二进制，
因此在任何服务动作前拒绝。新包只将两处上限改为 64 MiB，保持文件身份和摘要检查，
实际只读预检随后通过。正常窗口之后实际停止用户管理器，但恢复过程暴露三个接口
问题，均保留原失败并使用新审查补丁，不覆盖已安装版本：

- 停止后 logind 的动态 User 对象消失，持久 linger 文件仍存在。恢复先严格核验停止
  状态，再启动管理器并经官方接口重申既有 true 状态；实际确认管理器和 logind
  进程身份未变、Linger=yes、Sessions 为空。
- 独立临时卷仍保留 Podman alive 状态，但用户运行时目录被重建，缺少 pause 的 tmp
  父目录。仅由原 UID 经固定父目录 FD 创建缺失的 tmp/0700，不改数据库或整树权限。
- 恢复后的 pause transient scope 名称自然变化。仅将原 v7 身份检查认证的唯一新
  pause scope 映射到原基线名称；其余 unit-file、服务状态、依赖、源码检查全部保留。

最终实际四角色、配置及启动清单通过，原窗口锁释放、定时器 inactive/dead 且无 Job。
完整恢复耗时 **806.023 秒**，在原 1200 秒上限内；终态回读摘要
`5eba9317f541882ba2d0babbfda1d1be824ae3dcc65074471899bb721d53d0bb`。
该窗口仍记为失败后恢复：原 process visibility 尚未执行，不能据恢复成功记成正常
演练通过。原失败记录、补丁源码、动作授权及各次回读均保存在树外 stage60 独占目录。

### 本次检查点边界

已安装原版合成验证程序但尚未执行；没有获取注册令牌、注册 Linux runner、切换
Windows/Linux 接单服务或操作生产设备。正常及异常静默演练、真实合成验证、注册、
同 SHA 双 lane、main 采用及生命周期验收仍待完成。TASK-0048 保持 IMPLEMENTING，
Missing implementation_result；此检查点不生成 Gate 或阶段三/四通过结论。

## Stage 60B：真实 Windows CI 与静默恢复演练

同一外仓提交 `949fc6036a95e5c1ed55c4d5d5f96793ba42670f` 的 Actions run
`35547201811` 中，`windows-strict` job `106175121183` 已实际完成且 success；
`posix-shells` job `106175121387` 仍待 Linux runner。该事实不是双 lane 全部通过。

v3 normal003 的低权限原 helper 进程可见性检查通过，但两次原恢复在
`activation_changed` 退出。独立应急恢复采集到具体差异：已退出的 Podman 命令留下
短暂的 `podman-69087.scope transient -` unit-file 行；原服务、socket、timer 状态
没有改变。保留原 activation hash，待该行自然消失后连续两次完整严格检查通过，
659.705 秒内恢复并释放原窗口。v3 normal003 仍记录为失败后恢复，不计正常演练成功。
终态回读摘要：`c51cff29c117cad27e913d5dd8a5b6d5ec826fa5a044c138f9127ab63fba9f30`。

v4 仅增加实际差异记录及恢复末尾的有界稳定观察：只允许 `activation_changed`
重试，接受窗口 15 秒、间隔 1 秒；需连续两次完整 activation 与四角色观察一致。
其余错误直接失败，不忽略未知 scope，不改原基线、900/1200 秒预算或独立恢复机制。
21 项主机测试及独立源码/包审查通过后，完成以下真实 guest 演练：

| 演练 | 实际结果 | 从 arm 到 restored | 原始回读 SHA256 |
| --- | --- | --- | --- |
| normal004 | 原 helper 可见性 PASS，自动恢复四角色，lease 释放 | 7.90 秒 | `c80f78d0af353286684627997518ae4f510942fc40128440f4dbb64c4f75ef0c` |
| fault002 | quiet 后控制器 SIGKILL，独立 PID1 自动恢复，lease 释放 | 7.16 秒 | `a030d63e040958e0f838fb569408a65eeb69a96d0ac3886eabe85147d40795e8` |

fault002 另以实际 `Result=signal / ExecMainCode=2 / ExecMainStatus=9` 确认 SIGKILL，
并重新执行严格 activation 与四角色检查；证据摘要
`9b14f227ff147c829845421c58c6e7f3b38eaf6ce226a9aa9890ed9d5c3807a5`。
两次恢复服务及独立定时器均 inactive/dead、无 Job；故障 work 的 failed 状态保留。

仓库提交 `958e75964e3d73e8ca013b8caa33f786fc7efaeb` 的 clean-checkout 检查完成：
105 项 contract 检查、1945 项完整测试通过，总覆盖率 88.12%；lock/sync、Ruff、
format、mypy、90% diff coverage、whitespace 及工作树检查通过。此质量证据只绑定
该提交，不推定之后的新提交已经完整复验。

本检查点未申请真实注册令牌，未注册或启动 Linux runner，未切换 Windows 服务。
真实官方合成检查、注册及同 SHA 双 lane、采用与生命周期验证继续进行；
TASK-0048 保持 IMPLEMENTING，不据静默演练成功产生任务完成或 Gate PASS。

## Stage 60C：合成验证通过与真实离线注册

原版官方合成 canary 已实际执行，run ID `c27f67e883bc4862800bdcf4a6655126`。
结果 `SYNTHETIC_FAILURE_PATH_MASKING_OBSERVED`：隔离配置 native exit 1 符合预期，
version native exit 0；扫描 1 个文件、27127 字节，所有受检表示匹配数为 0，
masking、环境移除和网络失败上下文均实际出现。原 helper/child native exit 0，
清理完成，实际安装 manifest/tree 不变。完整窗口 34.710 秒内自动恢复并释放 lease。
该测试只证明实际执行的合成失败路径，不扩展为对所有成功路径的泄漏保证。

- 原始净化 canary receipt：`3971691bd4fd51847b16f2d7a27f831d42b88c30614a868b4cdc86998c7f94d0`。
- 包含独立恢复的回读：`380096aa54d46b24a693121a8c23636203ea832faea7d99041687267371b4ec3`。

真实注册准备的第一次操作 `835562d1420140a6b149e08d8786d638` 在获取 token 前失败。
producer 明确记录 token_requested=false、registration_dispatched=false；控制器
记录 BrokenPipeError，26.407 秒内恢复并释放 lease。现场 Unix socket 探针证实，
正常 connect 更新 atime；旧的完整 stat 相等检查因此误拒绝。没有创建 `.runner`、
凭据文件、原 helper slot 或 journal。过期 intent 经独立动作核验后在同目录 rename，
保留原内容和 inode，不删除第一次尝试。失败回读摘要：
`01146bbd3008e1376a1df74d1b32cda681a6edef8631abff99ce15ed20323b7d`。

新不可变候选只将 socket 身份比较中的 atime 排除；dev/inode/owner/mode/link count、
size、纳秒 mtime/ctime 及 SO_PEERCRED、argv、exe、cgroup、进程身份复查全部保留。
另增固定诊断枚举，不导出原始日志。9 项协议测试、6 项构造器测试和最终 12 文件
独立回读通过，原注册 helper 保持不变。

新操作 `a87440b69320403badb1f22bc8a7d4cf` 使用新鲜仓库观测，通过认证 READY 后
申请一次性注册令牌，并经匿名 stdin 调用原 helper。实际返回
`CONFIGURED_LOCAL_PENDING_REMOTE_CONFIRMATION`、native exit 0、清理完成。
GitHub 随后回查确认私有仓库 `MaginaLW/r3s-VPS` 的 runner **22**：
`r3s-vps-linux-pilot-01`，Linux/X64/self-hosted/trusted-linux，offline、busy=false。
没有启动 Listener。完整注册窗口 31.626 秒内自动恢复并释放 lease；work/recover/watch
均 inactive。注册成功与恢复成功分别核验。

- 最终包：`81a2109e536bb36ffd7c80df2ea2a558ac864238638dec1d678544d3fde1aa3a`。
- 注册及恢复回读：`28627a5835ed05ca00a6dda56c107fc3a45cad27d743e727c43b44b27602f22f`。
- GitHub runner 22 回查：`b4f3b93218eb7e80dc32f6dbe19e4dfa4f22943ec04fe6617a69c2989e0223dc`。

此检查点完成离线注册；Windows/Linux 串行接单切换、Linux CI、main 采用、重启与
恢复后的业务 job 尚未据此通过，继续执行。Windows 服务操作采用正常 OS UAC 提权，
不将项目授权解释为已取得管理员 token。TASK-0048 继续保持 IMPLEMENTING。

### Windows 切换的 OS 提权结果

正常 UAC 提权尝试返回“操作已被用户取消”，未得到进程 PID，也未产生服务操作
脚本的执行 receipt。随后只读回查确认：Windows 原服务仍 Running/Auto、原进程
未变，runner 21 online/idle；Linux runner 22 offline/idle。没有重复提权或绕过
管理员边界。现场结果保存在树外 `stage60-windows-elevation-cancelled-001/receipt.json`。
用户的项目授权仍有效；继续切换需要一次实际成功的 OS 管理员提权，随后重新核验
空闲与两端状态。Linux CI 和后续生命周期仍未执行，不能将离线注册当作采用完成。

### 注册检查点质量复验

提交 `9f5686f52f2eb8c5189ac337142930bdbb2b0fce` 的独立 clean checkout 完成全部
10 项检查：105 项 contract 检查与 1945 项完整测试通过，总覆盖率 88.12%，完整
测试耗时 579.08 秒；Ruff、format、mypy、diff coverage、whitespace 及 clean status
均通过。质量 receipt 摘要：
`966a64a9b038da7a9e2f7c66011643422cdb0d5333d72ee93c12403f237a1fb2`。
独立证据审查也确认 Stage60B/C 全部 10 个引用摘要与现场原件匹配，且未扩大完成
声明；审查摘要 `628aa501514a975e65ae00ae8c77f326a95c70d65949e9c3ef670f7cf929a859`。
本小节及 UAC 结果仅追加状态文档；完整测试绑定上述提交，不冒充 Linux job 验收。

### 再次授权后的下一阶段预检

所有者再次授权后，重新核验 runner 22 的本地注册身份、无 Listener/Worker、
空容器及四角色基线，结果通过。服务 install/start/stop 源码复核通过；外仓候选
仍为 `949fc6036a95e5c1ed55c4d5d5f96793ba42670f` 且工作树干净，远端 pilot 未漂移，
main 仍为 `39cc7ff1622740cf1d28f1ce3022cf4701df90a1`。同 SHA 的 Windows job 成功、
POSIX job 仍排队；原外仓两处用户改动保留，没有执行采用或推送。

第二次正常 UAC 提权再次返回“操作已被用户取消”，未启动管理员脚本。紧接着的
只读回查仍为 Windows Running/Auto、runner 21 online/idle，runner 22 offline/idle。
结果保存于树外 `stage60-windows-elevation-cancelled-002/receipt.json`，下一阶段
仍阻塞于本机交互式管理员提权；没有把再次项目授权写成服务切换或 CI 完成。

### Stage60D：真实串行切换与首次 Linux CI

所有者在桌面准备好后，正常 UAC 启动了管理员进程。初次进程未留下回执；添加
仅记录预检失败的诊断派生脚本后，确认 PowerShell 自动将 JSON ISO 到期时间转换为
DateTime，后续文化相关解析失败，且 Mutations 为空。固定使用 `-DateKind String`
保留原 ISO 字符串，重新绑定脚本与单次 action；初始及每次服务命令前的到期检查
均保留。独立复核确认该修复不改变授权时限。原失败尝试均保留。

Windows 精确服务随后实际停止、禁用自启，无 Listener/Worker 残留，原恢复设置
逐字保持；GitHub 确认 runner 21 offline/idle 后才安装并启动 Linux 固定服务单元。
runner 22 实际 online，Listener 为 UID 1001、预期路径及精确 unit cgroup，用户
manager 未更换。安装、启动回执摘要分别为
`8d6add00ea3350a608bb2c2eabbd9003e77e9082cd959190c76eb0c057c51b38`、
`6b7a425d4fbcf165be5256aa73123d769fffaf91b55f21ce158fd076568dac6f`；
Windows 停止回执摘要为
`83ecc1e6191676b44fd5d19ff2ba9da6bc09f6ca7c8318dbeee3801513a07e7c`。

原排队 POSIX job `106175121387` 实际由 runner 22 接取，checkout 固定 S 后在工具
预检失败：`POSIX_BINDING_REJECTED reason=unsupported_git_metadata`，尚未执行完整
POSIX gate。只读现场确认拒绝项为普通非链接 `.git/config.worktree`；其余禁止元数据
不存在，已安装 checker 摘要与固定合同一致。Git 本地配置键未启用 extensions。
首轮 job 原始 API 摘要为
`79b479c0660d2e05acf46221c0b7a16537d9277c1304ac6987bf94704862501b`。
本阶段证明真实串行接单，不能据此宣告双 lane 通过、main 采用或生命周期验收。

#### Checkout 惰性元数据修复与单 job 重跑

固定 checkout 会留下未启用的 `config.worktree`。最小修复只将该普通文件纳入可选
字节快照，区分缺失与空文件，并沿用前后快照一致性检查；所有 `extensions.*`、
include、partial-clone、链接和其他禁止元数据规则保持不变。真实 Git 的六项回归
全部通过、零跳过；独立审查再次执行通过。合同仅变更 `binding_sha256`。

修复前 runner 22 已实际 stopped/disabled、无 Runner/Worker、空容器及四角色基线
通过，两端 API 均 offline/idle。受控安装先将精确两份旧字节归档至任务专用 root
只读目录，再逐一比较替换并回读；未更改 checkout、服务单元、工具版本或候选 S。
新 helper 摘要 `e322ce27aaf713b703b758bdb9052a083bb4579a818f436dd9c9998fa98e9136`，
新合同摘要 `e9246d396b0fe557d11d2808a2a9ce337494578868e07502115b682382f84c0b`，
安装实际结果摘要 `3891305d0ea40eaf3c478709fcb0803615f862b325e3fe28d49f0a5c278e0baf`。

随后 runner 22 重新启动，Listener PID 从 75240 变为 76230，仍为精确 UID/路径/unit
cgroup。仅调用失败 POSIX job 的 rerun API；attempt 2 新 job `106358427430` 实际由
runner 22 接取，工具预检、yq、actionlint 均成功，已进入完整 POSIX gate。Windows
成功结果由 GitHub 沿用（新显示 job ID `106358430073`，步骤仍为原执行时间），
没有声称再次执行 Windows。此记录时完整 POSIX 结果、重启后业务及 main 采用仍待验收。

#### 完整双 lane、服务恢复与 main 采用

attempt 2 的 POSIX job `106358427430` 已成功，九个步骤全部成功；实际日志包含
48 shell 静态检查、17 fixtures 双 shell、两个 Python 文件共 27 cases、八项
PowerShell fixture 及最终精确快照复查。两项 root 组件实际 nonce 分别为
`2904c249ae1347c087a75f62e3e02372`（dash）和
`a2454ab30c6e4a408e87cc28caae179c`（BusyBox ash）。独立只读收集 98 份原件，
双读、哈希、schema、启动/FD/内核授权、精确四用例日志和清理检查均通过；结果摘要
`1a4816b3639ee51eb9428a7e4dd0ac78f3213d8be7a21875624b35b81ba35a64`。
workflow 未公开 adapter 原始 JSON，兼容验证投影来自收回的真实 receipt；相等检查
不冒充独立 stdout 佐证。bootstrap controlled-path marker 未公开，按固定源码和
实际 inventory/最终 controlled-path 检查区分间接依据与直接日志。

独立恢复复核确认真实 stop/start、Listener 身份变化及随后固定 S 的完整业务 job，
服务恢复项通过；结果摘要
`3e1d8a0be99a182697219260274bce63938e5e83a77058a7e2a9b57acc551c53`。
该结论不代表 guest 重启。实际 QEMU 启动参数含 `-no-reboot`，且无 monitor/QMP，
因此先准备受控退出后的冷启动入口，不能使用“原进程保持运行”的重连假设。

同 SHA 双 lane 与原件验收后，重新核对远端 main/pilot 和干净候选；仅以非 force
push 将远端 main 从 `39cc7ff1622740cf1d28f1ce3022cf4701df90a1` 快速前移到 S。
原外仓工作区两处用户改动保留。实际 push 验证 run `35608851034` 已触发，Linux
job `106362618755` 正在运行，Windows job `106362618978` 按串行窗口排队；采用后
双 lane、重启后业务与最终 Windows 恢复尚未据此宣告完成。

#### main Linux 验收与受控冷重启

main Linux job `106362618755` 已完整成功。独立收回本轮实际 92 份原件（不固定复用
前轮 98 的数量），两个实际 nonce 的所有文件名/字节双读、必要证明、完整 markers
和原 component 校验通过；最终结果摘要
`d0c5ad5be09f86f4b33b4a496bd7b5724f5ce4159e15c593f6208601dee7fde0`。
首份派生标签不准确的本地结果保留，由 corrected `recovered-002` 明确替代；未重跑
业务或重采原件。Windows 仍排队，尚不声称采用后整体 workflow 成功。

冷重启 v2 入口经独立复核，先持有旧 QEMU 原 handle，再要求本次精确请求 hash、
window、armed 后的 dispatcher 启动及唯一旧 BOOT intent；不将任意正常退出当作
本次重启。真实 guest reboot 已提交，旧 handle 退出 0 后，完成两次全 QEMU/SSH
端口 absence、独占冷态备份、同字节读回、固定不可变输入/backing 校验和只读镜像
检查，再单次启动。原件与备份保留，不自动回滚或重试；运行中的磁盘未被读取。
实际 argv 仅移除 `-no-reboot` 并改用新日志/pidfile，原输入与同一 guest 磁盘不变。

新 QEMU PID `32316`、launch 摘要
`698abba5e23ac70df96b804d417b046643abbf95355f22f69e6fd60eec86ff2a`；
新 BOOT `3a61e674-1061-4621-b5f0-47c3ed08804c` 与旧 BOOT 不同。新只读 transport
只重绑 launch 路径和摘要，原 SSH host-key、进程出生身份和端口 owner guard 保留。
runner 22 自动恢复，MainPID 714、Listener 909、user manager 798；原 unit enabled、
精确 UID/路径/cgroup、注册及包字节匹配，无 Worker。linger、runtime-dir 和 bus
socket 元数据也通过；不以 socket 存在宣告业务通过。独立实际重启审查结果摘要
`d71a8e78d05c7c81eb1a0addea8a098e0a07aab87a97af02b8b5ee71db020db2`。
重启后单独重跑已完成的 pilot POSIX job，attempt 3 新 job `106367257688` 正在
runner 22 执行；main 的 Windows 排队作业保留，等待 Linux 完全停用后串行恢复。

本仓 `78df470cf233e626e0e008a6ebd3b8efe88bfc11` 干净检出的完整质量检查均通过：
105 合同、1945 全量测试、总覆盖率 88.12%、90% diff coverage 阈值及 Ruff、format、
mypy、whitespace；完整测试 729.88 秒，最终工作树干净。质量回执摘要
`b69cf848c3b8b98c24e00a299114f36cd6d02b2ec175e0015fb55961c2e22cc7`。
该完整测试绑定指定提交；后续追加的运行事实不伪称重新执行过相同测试。

#### 重启后真实业务验收与最终串行交接

新 BOOT 的 pilot attempt 3 Linux job `106367257688` 九个步骤全部成功，实际执行
runner 22。独立收回本轮 98 份原件，两项实际 nonce 为
`bbf52abfcf674681a638f83acb092eab`（dash）和
`9c58904ad80141608c305c3e6c642e51`（BusyBox ash）；双读、哈希、schema、完整业务
markers 与原 component 检查全部通过。结果摘要
`fdf1befe2c1d35231c5ac0bcff8dbe79c51e79345822bc903ed12a4295329c1f`。
该结果绑定新 BOOT、QEMU 出生身份、launch 与严格 SSH transport，构成实际重启后的
业务验收；Windows 展示的沿用结果不算重启后 Windows 新执行。

采集结束后以新 BOOT 绑定的受控动作停用 Linux 服务，实际 `inactive/dead`、
`disabled`、MainPID/ControlPID 为零且无 Runner 残留，原 user manager 保持运行。
main 的 Windows job `106362618978` 已由恢复后的 runner 21 接取，低权限、
checkout 和工具检查成功，完整 Strict 仍在执行。

最终独立只读核验确认 Linux unit `inactive/dead/disabled`，无 Listener/Worker，
rootless containers/pods 为空，注册保留，user manager 798 未变；随后 GitHub 21/22
均 offline/idle。独立回执摘要
`17d3d77af45b6d88af90241b89f9f204b7b171d08e2d01ab80b178d8a1fdd001`。
Windows Restore 通过真实系统提权执行，服务恢复 Running/Auto，原 delayed-auto
启动设置已还原；服务 PID 25804 与 Listener 43600 的路径、SID 和父子关系通过，
故障恢复配置前后完全一致。恢复回执摘要
`f4f0873f4ac75a02c7cd6d16b8fab15dd9aaa8269308f6182c7067ec8d6689d6`；
本地恢复与远端接单已确认，新 Windows Strict 终态另行核实。

#### 正式治理关闭的当前缺口

只读 CLI 审查确认 `implementation_result` 是状态提示，不是可手工补写的 schema
字段。TASK-0048 仍为 IMPLEMENTING / REVIEW / V2；当前 scope 与 gate 不通过：
原 base 到当前提交还包含其他工作的业务路径，不能归入本任务唯一报告范围。
另有三个用户未跟踪计划文件，保持原状。CLI `sync` 只同步 subject，不提供迁移
base/branch 的入口；不以扩大 allowed_scope 或重写历史消除差异。

DU-001 的 targeted mutation 声明为 false，与 V2 当前必需的 mutation 合同不一致。
即便后续正确执行，其固定五项 mutation 验证的是 harness 治理防线，不是 runner
业务行为。当前没有伪造 mutation、最终 review/code approval 或 V2 finalize；
也没有以历史完整质量结果冒充最终 subject 的正式验证。运维验收与此治理缺口分别
记录，不能由真实 CI 成功推导 TASK-0048 Gate PASS。I5、其他仓推广和生产操作未启动。

#### 本轮试验复盘与最终运行约定

- 首次真实 Linux CI 在 checkout 绑定处失败。修复只接受未启用且字节稳定的普通
  `config.worktree`，保留危险元数据拒绝规则；六项真实 Git 回归、后续 pilot/main
  与重启后业务共同支持修复结论，不从本地测试直接推导 CI 成功。
- 原 QEMU `-no-reboot` 使 guest reboot 对应宿主进程退出。实际流程先关联本次
  请求与原 handle，再冷态备份和单次重启；新 BOOT 的完整业务证明恢复能力。
  退出、启动、服务上线及业务成功是四个不同证据点。
- Windows UAC 是系统交互；早期未完成尝试和日期反序列化失败均保留。修正 ISO 日期
  保留方式后真实 stop/restore 成功，不通过放宽到期、身份或串行检查取得成功。
- 最终默认由 Windows 接单。Linux 注册及 guest 保留，runner 服务禁用且离线；
  已证明的开机恢复来自禁用之前那次真实重启，不声称禁用后仍自动接单。再次切换
  必须重核 busy/Worker 与两端状态，沿用受控串行交接。

本轮只读审查、公开作业日志和原件按独立尝试保留；失败结果、冷态备份及其他写者
内容未删除。正式任务的 scope/V2 缺口单独保留，不以运维成功自动解除治理门禁。

#### 恢复检查点完整质量复验

`aaf4eb26e0db359d8e4116341763f1d8000b6455` 的独立干净检出通过全部原质量检查：
105 项合同、1945 项测试，总覆盖率 88.12%（门槛 85%），Ruff、format、mypy、
whitespace、依赖锁定及最终工作树检查通过。pytest 报告 839.86 秒，全量 pytest
子进程实测 840.86 秒。diff coverage 保留 90% 阈值、比较基线
`9f5686f52f2eb8c5189ac337142930bdbb2b0fce`，实际输出为本次 diff 无可统计覆盖行，
命令退出 0；不将其表述为测得 90% 或 100%。质量回执摘要
`55f19b6123ffa77ba69bd9456f46519ddae8ff56e2a93603d1a65ddb4045c0e4`。
这是指定提交的独立质量复验，不代替尚未建立的 TASK-0048 正式 V2 证据。


#### 采用后双平台完成与运行收尾

2026-09-21 15:08:25 UTC，main Windows job `106362618978` 实际完成，runner 21、
固定 S、全部步骤 success；本次从 14:23:01 UTC 开始，历时 45 分 24 秒。
公开完整日志核对 17 项 PowerShell fixture 全部执行且零跳过、58 份 Markdown、
27 项 Python cases、源码 SHA256 快照复查、secret-scan assurance 及
`PROJECT_VERIFICATION=PASS mode=offline strict=true` 完整结论。Windows 的
BusyBox 行为 fixture 依平台合同跳过，未误记为执行；其真实双 engine 行为由已验
Linux lane 证明。

main run `35608851034` attempt 1 实际 completed/success：Linux job
`106362618755` 与本次 Windows job 都对应
`949fc6036a95e5c1ed55c4d5d5f96793ba42670f`。这次 Windows 是恢复后的新执行，
不是 pilot rerun 显示的历史复用结果。CI 独立回执摘要
`4ef668c7921e943b0952ea5f4a6d309caad200d4736271849269d008480b48c6`。

最终重新读取远端 main 仍为 S，runner 21 online/idle、runner 22 offline/idle；
Windows 原 delayed-auto 与故障恢复配置已恢复，Linux 注册及 guest 保留但 runner
禁用，原件与失败历史保留。综合最终回执摘要
`983fbdd60fb5f0121fe4a109f1adb5b72919cc6b1c72ccc3df5536ca5c8a6e2b`。
本次主机/guest 运维验收、main 采用后双平台 CI 和串行恢复闭环已完成，监控进程
已结束。TASK-0048 正式 Gate 仍受上述 scope/V2 缺口阻断，不宣告任务治理关闭，
也不据此启动 I5、其他仓推广或生产操作。


## 阶段 61：补充集成范围与正式 V2 收尾

所有者在运维验收和治理缺口报告后明确继续。进一步核对现有 CLI 后，使用
REVIEW→REVIEW 的 `spec_changed` 升级，而不是修改 base、历史或 Policy。
八份已提交 ZCode 文档增量按精确路径纳入补充集成审查，十个原提交保留原始
归属；记录见 TASK-0048 的 `closeout-amendment-001.json`。三个用户未跟踪计划
保留原处，验证工作区不含这些原稿。

独立审查发现一项 P2：方法文档中“退出码或断言输出”可能允许成功文本掩盖
非零退出。已明确要求立即保存并检查门禁自身退出码，文本断言仅作附加检查。
首次发现与修复复核分别保存在 `closeout-integration-review-001.json`、
`closeout-integration-review-002.json`，前者未覆盖。规格和修复固定于
`37beda8ce0f0d6decdcd5f84ab52b7f8f45cacf6`。

CLI 已实际完成 scope-valid、升级条件 resolve、重新 classify 和 freeze，保持
REVIEW/V2。原验收第 8 项现在明确执行固定五项 harness 治理防线 mutation，
DU 声明同步补正为 required；mutation 只证明本仓防线，不替代先前真实 runner
和业务原件。此段记录的是正式验证前的冻结点，不预报 V2/Gate 成功。

后续验证结果须绑定新的最终 subject，依次保存完整 pre evidence、独立实现
review、finalize 及当前版本批准。正式结论由任务账本和 CLI Gate 读取，不因
补写本段而重跑外部 CI、服务切换、注册或反馈回灌；I5 和生产范围不变。
