# Windows 超时处理生产设计提案：2026-10-04

本提案承接[私有候选及其限制](windows-private-timeout-repair-2026-10-04.md)。原封存两份
candidate SHA256 已重新核对一致。本轮设计与安全测试基线已完成，所有者批准冻结规格后
已原生 begin，生产实现正在独立治理工作区推进，尚未完成完整验收。
既有 TASK-0064 仅覆盖 GitContext，不能容纳 ProcessRunner/helper。

## 精确范围与先行安全基线

TASK-0065 的累计范围为 `src/aiflow/process_runner.py`、`src/aiflow/windows_owned_job.py`、
`tests/unit/test_windows_owned_job.py`、`tests/unit/test_process_runner_safe_contract.py`、
`tests/unit/test_process_runner.py` 和自身目录。治理源码与安全测试分别归属、分别提交。
先行安全维护只新增
`tests/unit/test_process_runner_safe_contract.py`，全 fake Popen，不启动真实子进程；
以当前未修改源码锁定公共签名/字段、argv/固定关键字、正常零/非零退出、启动错误、
超时原因优先级、日志错误、去重和独立解析、最小环境及脱敏、preflight 零启动。
该基线已提交 `d4f72ac`，在治理工作区承接为 `ab07bcd`；20 项作者与独立检查均通过。
测试作者与独立 reviewer 分开，主 agent 统一检查和提交。helper mock 与真实 OS
资格另行设计，不能以 fake baseline 或原 4 项故障 mock 代替。

## 所有权与受控启动

只服务 ProcessRunner 固定受控调用，不暴露泛用 Popen 包装器。argv 是唯一位置参数，
其余固定关键字；拒绝 shell、额外位置参数、调用者 suspend/breakaway 和未知 flags。
采用 ctypes 调用稳定公共 `CreateProcessW` / `STARTUPINFOEXW`，不采用 CPython 私有
`_execute_child`、FunctionType 或 stdlib hash 白名单。每实例创建 fresh unnamed、
不可继承的自有 Job；创建时 suspended，先 assign，再启动本 owner 的两路 reader，
仅一次 resume，核其原 suspend count 为 1。helper 自持 raw parent/thread handles，
不需要 Popen adoption 或复制 parent handle。
不修改共享 Popen、`_winapi` 或任何原函数/code/global binding。

不使用 breakaway，不终止父级或他人 Job，不因 assign 失败改走 taskkill。
正常返回允许合法 live child 自然完成，不启用 kill-on-close。嵌套 Job 不兼容时保留
明确启动失败和控制资源，不把该失败说成 timeout cleanup 成功。

生产方案采用实例锁和 registry 锁协调并发句柄归属，无主线程或 `active_count == 1`
准入门槛；真实并发/线程/nested Job 案例仍须取得本次资格。HANDLE_LIST 只列 stdout/
stderr child write ends 和 stdin duplicate，parent read ends 不继承。stdin 保留默认
STD_INPUT_HANDLE 行为，不存在时使用 fresh EOF pipe。CreateProcess 返回后及时关闭
parent 持有的 child-only handles，避免自身阻止 EOF。

保留 argv resolution、官方 MS CRT quotation、`lpApplicationName=None` 搜索行为、
最小 Unicode 环境和原 `subprocess.Popen` audit event。reader 捕获 bytes，确认 EOF 后
UTF-8 replacement 解码并统一换行；不新增输出截断。只在 parent signaled 后取退出码，
259 可为实际退出码，不能仅据 STILL_ACTIVE 值判定仍在运行。

## 终态与错误

| 终态 | 必需事实与处理 |
| --- | --- |
| NORMAL_RELEASE | parent signaled、drain/reader threads 完成、owned handles 已关闭；active count 大于零可表示合法 live child，不能由此称完整树已清空 |
| TIMEOUT | 保持公共 RUNNER_TIMEOUT 与返回码合同；单一 5 秒 monotonic cleanup deadline 覆盖 terminate Job、parent wait、accounting active 0 与 bounded drain；禁止第二次无期限 communicate 或自动 retry |
| LAUNCH_FAILED | assign 失败绝不 resume；只尝试终止本次自有 suspended parent；若 terminate/wait 未确认，保留 raw parent/thread 控制句柄及明确状态 |
| INCOMPLETE / UNKNOWN | 任一 wait/accounting/drain/close 未确认即保留错误、输出已知程度和资源归属；未知输出不能写成已知空或 cleanup PASS；不能同步关闭可能阻塞的 pipe |

必须修正原私有候选的两个具体缺口：`_reclaim_unadopted_launch` 在 terminate/wait
失败后仍关闭 raw parent/thread handles，可能丢失未 assign 进程的唯一控制句柄；
CloseHandle 失败后的 owner 保留路径不完整。不能原样复制该候选上线。
registry 在任何 Job/Process 创建前原子预留最多 **8 个 active+retained owner 槽位**。
unknown 沿用原预留；只在未创建资源或所有 owned handles 确认 closed 后释放槽位。
第 9 个 launch 必须零创建拒绝，不能为腾出容量关闭或终止未知旧 owner。只读诊断和
后续处置边界须可审计。公共 ProcessResult 保持 **12 字段**，新 cleanup 事实通过
receipt/脱敏日志表达，timeout reason/returncode 合同不变。

单一五秒 deadline 覆盖所有合作 wait/drain，不重置；同步 kernel API 不能被 Python
合作 deadline 抢占，因此实际超界或未知不能报告及时清理确认。

没有 kill-on-close，且 create → assign 非 crash-atomic；外部解释器崩溃/被终止仍可能
留下 orphan。本次最小修复不承诺 crash containment，不引入 JOB_LIST 或 security sandbox。

## 支持矩阵与准入缺项

项目 Python >=3.11 和现有 CI 不变。生产采用公共 Win32 API，不按 Python patch、
stdlib hash、Windows build 或“未测”人为拒绝原本可运行的环境。实际缺必要 API/ABI
才在创建前 OSError → RUNNER_EXECUTION_FAILED。封存私有候选只绑定 CPython 3.13.15
Windows 的私有协议；这不证明新版生产方案或其他平台兼容。
本轮尚未核定封存执行窗口的 Windows OS/build/architecture/ABI；解释器版本不足以
证明 OS 资格。实际矩阵须列这些平台事实，不能借当前宿主版本回填封存窗口。
当前 CPython 3.11.9、私有 3.13.15 与 AMD64 / build 26300 只作为本次实际可用资格
输入，不是唯一放行表，也未自动取得新 backend 的资格。

实际可用的 3.11/3.12/3.13/3.14、Windows 10/11/Server、x86/x64/ARM64 分别记录测过或
缺失。保留原 timeout 节点的 source/AST 和 1/5/2/10/3 秒时序；真实案例还包括
exited-parent/pipe、normal 0/3/live-child、thread/concurrent/nested、Unicode/quotation/
stdin/large output。fake 注入须同时禁止真实 native factory/WinDLL/reader，避免旧
Popen monkeypatch 被新路径绕过。未测与不兼容分开记录。

设计依据为 [Python 的公开 Windows 启动接口](https://docs.python.org/3/library/subprocess.html#subprocess.STARTUPINFO.lpAttributeList)、
[参数引用规则](https://docs.python.org/3/library/subprocess.html#converting-an-argument-sequence-to-a-string-on-windows)
和 [Win32 属性列表契约](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute)。
公共 Popen 不提供 primary-thread handle，直接 backend 避免先执行后 assign 的竞态。

## 原生准入进展

TASK-0065 真实 base/subject 为 `ab07bcd`，继承现有 GitContext 候选不等于 TASK-0064
验证被接受。首轮独立 Design Review REQUEST_CHANGES 指出字段数、并发预留和支持合同
三项问题，原报告保留。修改规格经 native spec_changed 升级、resolve、classify、freeze；
规格审核窗口为 WAITING_FOR_SPEC_REVIEW / REVIEW / V2，Missing `spec_approval`。
新 context 003 已获独立 APPROVE，并原生记录为 REV-0002 r0001；
原 REV-0001 三 finding 的解决追加为 r0002–r0004，原 REQUEST_CHANGES 保留。完整
准备提交为 `1d4731c`，工作区干净，validate/scope 通过，classification fresh。
规格 SHA256 为 `418642e6cf7ab36edcc2ff575924dd0038235dbbcf75bb353eaa634c3d2914fa`，
位于生产治理分支 `.ai/tasks/TASK-0065/spec.md`。所有者随后明确回复“批准”，native
spec approve/begin 已完成，事件16/17和提交 `01949da` 保留真实决定；当前 IMPLEMENTING /
REVIEW / V2，classification fresh、approvals current，Missing `implementation_result`。
原预算和完整验收门不变，具体单次 mutation action 尚未请求或执行。

## 串行验收

安全 baseline 实际 PASS并提交 → 明确真实干净基线与上列支持/错误决定 → 新治理
Task classify/freeze/context → 独立 Design Review → native status 的实际规格决定
→ begin → 实施与 subject sync → 新具体单次 mutation action → 全部 14 项原生 V2
→ 独立 Implementation Review/finalize/code 决定/Gate。保持原 selectors/预算、85%
总覆盖率、90% diff coverage、whitespace/Ruff/format/mypy及 main 保护。

原失败和 SPENT action 不重写或复用。局部 OS qualification 只证明本次案例，真实
OS 故障未出现的范围仍 UNKNOWN；完整测试预算问题另见
[预算决策](verification-budget-decision-2026-10-04.md)。
