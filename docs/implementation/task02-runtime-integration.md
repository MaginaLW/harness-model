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
