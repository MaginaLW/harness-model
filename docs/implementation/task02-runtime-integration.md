# 任务 02：私有 Linux 执行接入记录

日期：2026-09-13。整体状态：`IN_PROGRESS`。本报告由 `TASK-0048` 记录，范围与
验收以[冻结规格](../../.ai/tasks/TASK-0048/spec.md)及
[任务 02 执行目录](../superpowers/plans/2026-09-13-runner-infrastructure-execution.md)为准。
它记录当次已取得的证据和未完成项，不替代 AI Flow 的验证、批准或 Gate。

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
