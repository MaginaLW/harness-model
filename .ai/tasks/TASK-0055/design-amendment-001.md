

## 2026-10-01 重入补充：已 Gate 依赖与只读 Git transport

此补充继承本文件原有目标、I1-I8、输入/来源约束、writer 提交与中断恢复、非目标、禁止动作和全部质量门；未重复执行 Windows metadata 修复。

TASK-0056 业务 source 9dca04dc18e1551dc86987eb594f84f9d37b47ad 在完整14/14 checks、5/5 mutation、实际独立 REV-0010、同 verifier finalize和代码批准后，于准确治理 HEAD `80515e6032d9e8e90193f857730f957345150457` 取得提交后 Gate exit0/passedtrue。TASK-0055 工作树从 ef92b795da729566870ff4878f100a4ffe319db5 ff-only 到该 HEAD，保持原 base fd560d9f12d28ef6ff155f6f46764d6c588d0f30；此依赖不代替本任务后续源码的完整验证。

完整原 base-to-import diff 为187路径：44件本任务账本、106件 foreign TASK-0056 账本、37件业务路径。foreign tracked Git blob 清单原始 SHA256 `bfdae40544c795f756063ea2ce6afe8361448b578b48f2581560a82b28e28585`；实际 diff 清单原始 SHA256 `8849018a3e255346a2bcc2d4c0cb29b2f6bf1f26183c160b5db8a9614bf46d73`。逐字 Git blob manifest 见本任务 dependency-task56-git-blobs-001.txt，不对 foreign ledger 使用 own-attestation 例外，不强行提交 ignored canonical evidence/logs。

允许范围保留原11模式，并纳入原始完整依赖新增20唯一业务路径和 `.ai/tasks/TASK-0056/**`，合计32模式。新增本任务治理生产修改只限 external_review.py 的只读 Git transport 与其私有 cleanup helper；不改其他 production transport、Policy、CI、Schema 或 writer中断恢复边界。安全测试和操作文档按规则8单独task-free提交，仍纳入本任务累计验证。

### 只读 Git transport 约束

保留原 Git argv、cwd、二进制 stdout、继承 stdin、每次局部 GIT_OPTIONAL_LOCKS=0、
原 communicate(10) 和安全固定错误。仅改为拥有句柄的 Popen/new group 或 new session。
spawn 失败没有子进程；成功 spawn 后的 Timeout/OSError 清理后仍固定安全拒绝。
KeyboardInterrupt/SystemExit/其他异常在拥有的清理后重抛同一个原异常，二次清理失败
不得替换它。已完成的非零命令不触发额外 cleanup/drain；部分输出不得成功返回。

Windows 仅对 retained Popen 当前仍 live 的父进程启动绝对 SystemRoot taskkill /T /F，
三个流 DEVNULL，hidden；wait(5)，必要时 kill 该 helper 后 wait(1)。父进程已退出则
跳过数值 PID taskkill。POSIX 仅对 retained direct parent 尚未 reaped 且 poll() is None
的 owned session killpg；已 reaped 则不发数值 group signal。之后只尝试 retained direct
kill 和 communicate(5)。仅 drain 成功后 close PIPE；不添加无界 wait/communicate/
context manager。计划未另加 direct wait(5)，不得照搬 Task56 helper 又保留原算术。

Windows 配置等待项之和最多 10+5+1+5=21 秒，已退出父进程/POSIX 为 10+5=15 秒，
不是整体 wall-clock 上界。process creation/OS/scheduling 仍有限制；无法证明退出的
helper、escaped session、已 orphan 且未 retained 的后代保持 UNKNOWN。无全局进程查找、
未知 PID kill、Job Object 或全树资源释放保证。

record 提交前的正常安全拒绝仍按旧规则清理本次 temp/guard/空目录，旧正式字节不变。
突然中断可留可识别 runtime 材料是原 spec 明示边界：旧记录无损、guard/坏链阻止
下一次自动恢复，不把 transport 原异常重抛误称为 writer 全零残留。

### 新 begin 后的验收补充

保留 I1-I8 和全部已有断言。两个真实继承 PIPE 用例分别通过 public preflight/live
parent 和 public record/exited parent 执行原 10 秒期限；测试掌握子进程真实 handle/
creation/终态，exited-parent 后代由 test-owned stop/finally 有界回收，不能假称 production
已杀 orphan。快例覆盖成功/非零/spawn OSError、各 cleanup 失败、原异常身份、已 reaped
不 signal，以及 token 后 identity 第 1/3/5 调用的初始/guard/temp recheck 安全拒绝。
真实其余 Git/preparation/freshness 全部执行；不 mock 原 10 秒或替换整体 prepare。
核对完整 task bytes/empty directories、index/index.lock、report/envelope/mapping 和安全诊断。

定向通过后，Task55 必须在自身实际固定 subject/HEAD 运行原完整 Policy V2：14 checks、
5 fixed mutations、原每项预算/selector/MINENV、85% overall/90% diff coverage，独立
implementation Review/finalize/current code approval/Gate。Task56 的通过不能代替它。
两个真实用例的预计附加等待不是完整原预算 PASS 保证；真实 F 原件仍缺输入，不造正例。


### 本次执行依赖与写入归属（覆盖原执行安排）

同级 spec_changed升级 → 追加本规格/DU/依赖记录并阶段commit → native sync → spec_changed resolution → native classify/freeze → 1名 author-independent设计 reviewer → status缺项与 owner delegated spec批准 → begin。全部准入步骤串行。

实现并行阶段启用2名 sub-agent：一名安全测试作者独占 tests/unit/test_external_review.py 和 tests/integration/test_external_review_command.py；另一名 author-independent reviewer只读核对生产/测试边界。root独占 external_review.py 生产与操作文档、治理账本和统一分离提交。测试作者不承担本任务正式独立review/verifier。

固定实际subject/HEAD后，完整native V2串行执行；并行准备/审查阶段最多2名sub-agent：一名未参与作者工作的verifier运行原生验证、核对真实终态和资源；一名未参与作者工作的reviewer审查规格/累计源码/真实证据。共享源码/refs/topology/import在完整native运行期间冻结。随后 implementation Review → 同verifier finalize → code批准/Gate；累计发布另行准入并绑定准确候选、远端base、required CI与既有push/merge授权。F真实原件仍缺输入，不伪造验收。
