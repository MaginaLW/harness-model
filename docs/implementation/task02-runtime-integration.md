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
