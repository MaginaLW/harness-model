# 任务 02：私有 Linux 执行接入记录

日期：2026-09-13。整体状态：`IN_PROGRESS`。本报告由 `TASK-0048` 记录，范围与
验收以[冻结规格](../../.ai/tasks/TASK-0048/spec.md)及
[任务 02 执行目录](../superpowers/plans/2026-09-13-runner-infrastructure-execution.md)为准。
它记录当次已取得的证据和未完成项，不替代 AI Flow 的验证、批准或 Gate。

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
| `mask-contract-independent-review-001/002` | `MASK-DIAG-001` 的首异常掩盖后续挂载问题已由完整未过滤诊断检查修复并独立验证；v2 新发现固定脚本目录不一致、二次观测遗漏传播属性，均保留为待验证修复 | 诊断候选已运行；v1/v2 均未执行容器诊断或发放 permit |
| `mask-contract-independent-review-003/004`、`guest-mask-v3-diagnostic-001` | 三项 Findings 已独立验证修复；v3 三个实际阶段完成并清理，最终因 `SecurityOpt` 不展示 mask 的表示差异而拒绝；实际完整挂载比较通过，原失败未改写 | 可以仅依赖 inspect 文字代替内核挂载证明 |
| `guest-mask-v4-source-tests-001`、`guest-mask-v4-diagnostic-001` | v4 真实 Linux 49 项测试通过；81 秒实际诊断完整通过：单 owner 正常、共享和独立 socket 的外来 owner 均被两 shell 拒绝，合成业务 PID 的四类 FD 别名可见；真实屏障无 socket FD，完整诊断内核检查通过后未获 permit，原 60 秒等待超时退出 125；三个精确实例均清理完成 | 正式 adapter 已集成、完整 fixture 或 CI 已通过；诊断始终 `acceptance=false` |
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
