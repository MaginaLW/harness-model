# 受控环境中的工具发现

`tools/diagnostics/tool_discovery.py` 收敛了实际验证中最小 PATH 无法发现 PowerShell
的问题。它是可选的只读诊断入口，与现有 runner 健康观察器共用 Windows native probe；
不会修改 AI Flow 的进程环境、wrapper、Policy 或 Gate。

使用操作者已经核对的 Python 绝对路径启动，逐个指定可信安装目录：

```powershell
& '<trusted-python-dir>\python.exe' tools/diagnostics/tool_discovery.py `
  --trusted-directory '<trusted-python-dir>' `
  --trusted-directory '<trusted-git-dir>' `
  --trusted-directory '<trusted-powershell-dir>' `
  --expect python=3.11.9 --expect git=2.55.0.windows.3 --expect pwsh=7.6.6
```

路径和版本是使用形式示例，不是当前主机事实或版本推荐。多个工具在同一目录时只传一次。
版本由部署清单决定；省略某个 `--expect` 时只观察该工具的严格版本行，不判断版本策略。
入口本身依赖已经选定的 Python，不承担 Python 安装或引导发现。

搜索只检查这些目录直接子级中的固定 `python.exe`、`git.exe` 和 `pwsh.exe`，不递归、
不读取当前目录、注册表、用户配置或 PATH，不运行 `where`、`Get-Command`、别名、脚本、
shim 或自定义命令。Windows 路径先做纯字符串检查，只接受盘符开头的绝对路径；UNC、
设备命名空间、盘符相对及根相对路径在任何文件元数据读取之前拒绝。随后仅查询盘根的
`GetDriveTypeW` 类型，拒绝网络映射盘、未知或不存在的盘；仅接受本地固定、可移动、
CD-ROM 和 RAM 盘后才读取元数据，不因“指定了可信目录”而探测 SMB 共享。
目录必须为已存在的绝对普通目录；元数据按盘根到叶的顺序逐级检查，在接触后代前拒绝
符号链接或 reparse 祖先，目录及可执行文件本身同样拒绝。重复目录、歧义候选、缺失、
访问失败都不选择替代来源。
操作者指定目录是信任输入，不是 OS 签名认证、ACL 核验或依赖隔离证明；请只选用已审核、
不受待审代码写入控制的安装目录。工具不能防止受信任安装在观察期间被其他进程替换。

PowerShell 缺失时，Python 入口仍列出全部三个工具的定位结果，并明确版本探测不可用。
它不会尝试 ambient PATH。可信 PowerShell 可用时，固定桥接脚本通过现有
`RunnerInspection.psm1` 的 module scope 调用 `Invoke-InspectionNative`，仅执行
固定 `--version`，复用每项 10 秒、每流 64 KiB、Job Object 后代收束和严格输出校验。
PowerShell 桥接进程使用空 PATH、指定安装目录的 Modules 及必要的 SystemRoot；版本
子进程保持既有观察器的最小环境。桥接有 45 秒总等待上限，不接受任意 argv 或脚本。
这不是文件系统或网络沙箱；可信二进制的加载器和运行时仍可能读取其正常安装依赖。

当前真实版本采集仅支持 Windows。其他系统可以运行输入与发现逻辑，但返回
`LIVE_VERSION_PROBE_WINDOWS_ONLY` 和非零退出码，不声称完成 Linux 版本验收。
现有 Linux CI 执行的纯逻辑回归不代替真实 Windows 受控环境验证。

输出为 JSON，默认只含工具名、状态、版本、所选版本要求及固定原因码。只有显式
`--include-private-details` 才包含已找到的绝对路径；这样的报告保存在树外私有证据目录，
不要提交。工具不会输出版本命令的原始 stdout/stderr、异常内容或环境变量。

退出码 0 / `TOOLS_OBSERVED` 表示三个工具均取得严格版本行，且所有显式版本要求匹配；
1 / `NOT_READY` 表示工具缺失、歧义、版本不匹配、探测失败或平台不支持；
2 / `INPUT_INVALID` 表示目录或版本要求输入无效。`runner_ready`、`gate_pass` 始终
为 false。本工具不安装、不注册、不改 PATH/ACL、不读凭据、不联网、不启停服务，
也不会因此完成 I1 的安装、更新、日志保留、恢复或其他生命周期验收。

回归命令：

```text
python -m pytest tests/unit/test_tool_discovery.py
```

Windows 真实检查应从空/最小 PATH 启动上述明确 Python 入口，分别验证三个可信目录
齐备、缺少 PowerShell 目录、错版三种结果，并保留每次原始报告。测试不修改机器 PATH。
