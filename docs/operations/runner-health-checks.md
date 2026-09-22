# Runner 只读盘点和健康检查

`tools/runner/inventory.ps1` 与 `health-check.ps1` 使用同一观察器。两者只读，不安装、注册、启停或删除任何实例，也不写配置、ACL、凭据或日志。默认脱敏；正式结果保存在仓库之外。当前真实采集器支持 Windows x64，其他平台明确返回未就绪。Linux runner 应在真实 Linux 环境独立核验，不能用本脚本的 Windows fixture 替代。

```powershell
pwsh -NoProfile -File tools/runner/inventory.ps1 -Format Json
pwsh -NoProfile -File tools/runner/health-check.ps1 -ProfilePath <private-profile.json> -Format Json
```

没有 profile 的盘点仍返回平台、实例数量、服务和进程观察状态；它返回 `NOT_READY`，退出码为 1。配置文件是操作者声明，输出放在 `declared`；CIM、进程所有者、实际当前 token、磁盘与工具版本等结果放在 `observed`。服务配置中的账号 SID、进程实际 owner SID 与当前检查身份分别核对，不能互相替代。

## 私有 profile

profile 使用 UTF-8 JSON，最多 256 KiB，只接受以下字段。真实路径、账号 SID、实例名和仓库名保存在本地，不提交到公开仓库。

| 字段 | 含义 |
| --- | --- |
| `schemaVersion` | 固定 `1.0` |
| `profileId` | 小写字母起始的短标签，允许数字和连字符 |
| `repository` | 明确的 `owner/repository` |
| `repositoryId` | GitHub 仓库稳定正整数 ID，必须与本次 API 实际观察相符 |
| `runnerId` | 远端实例正整数 ID |
| `serviceName` | 精确的 `actions.runner.…` Windows 服务名 |
| `expectedServiceSid` | 预期低权限服务身份 SID |
| `runnerRoot` | 唯一 runner 根的本机绝对路径 |
| `minimumFreeBytes` | 本机卷最低可用字节数，正整数 |
| `requiredTools` | 非空列表，每项为 `name`、`path`、`expectedVersion`；名称仅支持 `git`、`python`、`pwsh`，不重复；path 为经过操作者审核的绝对可执行路径 |
| `remoteCliPath` | 可选，经过操作者审核的 `gh` 可执行文件绝对路径，仅在显式 `-CheckRemote` 时使用 |

未知字段、profile 内的相对路径、错误类型、重解析输入文件或重复工具要求都会失败。profile / fixture JSON 文件本身可以相对于当前本地 FileSystem 目录指定。不得在 profile 中放 token 或凭据；未知字段不能充当扩展秘密容器。不要将未经信任的 profile 交给工具：profile 指定的可执行路径会实际运行固定 `--version` 参数，`remoteCliPath` 会运行固定只读 GET。工具不接受自定义命令、shell 字符串或安装参数。

## 观察和结论

服务和进程来自 `Get-CimInstance` 的限定查询，仅检查 runner 服务、RunnerService、Listener 和 Worker；不输出或收集任意进程命令行。选定服务的二进制路径及服务/Listener 的实际 ExecutablePath 必须分别与唯一根下的 `bin/RunnerService.exe`、`bin/Runner.Listener.exe` 匹配，且实际文件及祖先无 reparse。带参数或无法明确解析的服务二进制配置保留未确认。

根路径使用带异常分类的实际元数据读取；访问被拒保留 `access_denied/unknown`，不将 `Test-Path=false` 当作未安装。仅从固定 `.runner` 普通文件读取非秘密的 `agentId` 和 `gitHubUrl`，建立本地实例、仓库名称及 repository scope 的观察。缺失、错误实例、错误仓库、组织级 URL、不可读或重解析文件不能由 profile 声明补值；绝不读取 `.credentials*`。再与 API 实际 repo ID/full_name、runner ID 相连，防止把另一个在线实例和本地服务拼为健康。只有根已确认为普通本地目录时才按该盘符定向调用 `Get-PSDrive`，不枚举其他盘；工具来自明确路径的真实 `--version` 退出码和严格版本行。

profile / fixture JSON、runner 根、注册文件和可执行文件共用路径检查。Windows 在读取任何路径元数据前拒绝 UNC、设备命名空间、PowerShell provider 路径、盘符相对路径、父级跳转及含糊的设备/流别名；随后只接受 DriveType 已确认的本地固定盘、可移动盘、光盘或 RAM 盘，网络盘和未知盘保留未确认。每层元数据从盘根走向叶子，遇到 reparse 立即停止，绝不先读取其子项再向上检查。POSIX 普通路径供合成回归使用，同样逐级拒绝链接，不启用真实 Windows collector。路径检查与后续读取/执行之间仍可能发生文件系统变化；这不是抵御恶意并发替换的隔离机制，JSON 的长度预检也不是并发增长下的硬读取预算。

服务 `Auto` 只描述启动方式。`running` 只说明当前状态，不能证明重启后业务验证。远端 registered、online、busy 分别观察；服务缺失时远端仍可保持 registered，不把它显示为可用。并行活动服务、额外 Listener、任何 Worker 或远端 busy 均阻止就绪。

当前 token 包含 deny-only Administrators SID，或直接/组成员命中本地 Administrators 时，均归类为管理员成员；不会因 UAC 未提升而接受。必须在预期服务身份下取得 token 和本地成员关系，且服务进程及其直接 Listener 的 owner 都匹配，才能证明这一轮 preflight 的运行身份为非管理员。其他身份执行盘点时通常只能得到 `SERVICE_NON_ADMINISTRATOR_NOT_VERIFIED`；不要因此提高 runner 的权限。

默认不发网络请求。若需读取远端状态，显式使用：

```powershell
pwsh -NoProfile -File tools/runner/health-check.ps1 -ProfilePath <private-profile.json> -CheckRemote -Format Json
```

这只调用 github.com 上两个固定 GitHub API GET，确认配置指定仓库的稳定 ID/名称/私有状态及实例 ID/OS/online/busy。`gh` 使用已存在认证，不调用 `auth token`、credential export、注册 token API 或写端点；交互提示关闭，原始 stdout/stderr 不透出报告。认证不足、离线、错误响应或没有 `-CheckRemote` 时远端状态保持 unknown，退出非零。读取不会承诺随后 job 一定被调度，远端和本机观察之间仍可能发生状态变化。

固定版本命令与 API GET 的每次 native probe 使用独立 Windows Job Object。进程以挂起状态创建，先进入设置了 `KILL_ON_JOB_CLOSE` 的 job，再恢复执行；子进程只继承选定 stdin/stdout/stderr 句柄。父进程提前退出后，仍追踪 job 内全部后代。执行期限为 10 秒，精确 job 回收另有最多 2 秒观察预算；初始化/编译及主机调度开销不冒充执行时间。关闭或取消检查进程也关闭唯一 job handle，收束其后代，不按名称或全机范围杀进程。

输出以非阻塞 pipe 可读字节轮询采集，stdout/stderr 各自最多 64 KiB；超量、无效 UTF-8、原生非零退出、deadline 或无法核定精确回收都失败。正常或失败结果均要确认本次 job 活动进程数归零；没有阻塞的异步 StreamReader Dispose 路径。Job Object 只承担本次短命检查的生命周期，不是文件系统/网络沙箱，也不提供整机租约或全局调度。Windows 本地 CIM 查询仍是一次只读快照。其他 OS 不使用此 Windows native helper，返回 unavailable；合成跨平台测试保持可用。

退出码 0 表示本轮所有 preflight 条件已观察到匹配；1 表示缺失、未知、忙碌或不匹配；2 表示输入/采集结构错误。失败只输出固定错误类型，不回显异常、账号或路径。`-IncludePrivateDetails` 仅在明确需要本机调试时开启，增加有限的配置、SID、实例与进程元数据；不增加秘密读取。

`credentialIsolationVerified`、`postRestartWorkloadVerified` 与 `gatePass` 始终为 false：健康盘点无法证明禁止目录不可读、实际业务门禁或重启验收。`runtimeVerified=true` 仅表示使用了真实只读采集器，其范围由 `proofScope=read_only_preflight_only` 限定，不能据此标记 `PILOT_PASS`、`ADOPTED` 或 Gate PASS。健康检查也不能证明操作系统沙箱完整。

## 回归验证

`-FixturePath <synthetic-observations.json>` 明确切换到合成观察，不调用宿主、工具或网络。fixture 同样限长、严格字段与类型检查，不能与 `-CheckRemote` 混用。合成条件全部满足时输出 `SYNTHETIC_HEALTHY`、退出 0，但 `ready=false`、`runtimeVerified=false`；仅用于逻辑回归。

```text
python -m pytest tests/unit/test_runner_inspection.py
```

测试实际启动 PowerShell 入口，覆盖访问被拒与未安装、管理员过滤 token、注册/路径/仓库错绑、多实例/忙碌、原生命令失败、工具错版、远端未知、恶意字段脱敏和重复只读调用。内存中的 metadata / DriveType 替身验证 UNC 和网络盘零元数据访问、祖先 reparse 零子级访问及磁盘查询范围，不连接真实共享路径；注册读取测试使用临时文件并替换服务和身份采集。Windows 上还运行受控父子进程，验证父提前退出后分别持有 stdout/stderr 的后代、父超时、正常后代、输出过量、编码错误、取消检查进程和无关进程存活。PID 和文件均属于测试临时目录；这不是运行实际业务 fixture。

环境必须安装 PowerShell 7；可通过 `RUNNER_INSPECTION_PWSH` 指定其路径，缺失时测试失败，不静默 skip。Linux CI 可以用 PowerShell 执行合成回归，并验证 Windows native collector/helper 被明确拒绝；不会在 Linux 声称测到了 Windows Job Object。真实 Windows 生命周期验收来自 Windows 测试记录。

保存真实报告时使用独立时间/运行编号；保留失败和原始结果，不覆盖历史文件。两次只读结果仅证明这两个调用没有写入配置，不证明安装或重启脚本幂等。安装、服务启停和受控隔离探针需另有审核过的显式操作与实际回执。
