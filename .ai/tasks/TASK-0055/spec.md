# TASK-0055：E4.2 本地报告预检与不可变附属记录

## 目标

在 E4.1 的 external-review 1.0 契约上，实现操作者引导的本地 ZCode 报告预检与
显式记录。比较经操作者核定的来源受审对象和当前既有 AI Flow task；成功后只追加
不可变附属来源记录，完整输入重放 no-op，错配、失效、冲突或漂移拒绝并保留原记录。
报告文字始终是数据，不能产生正式 Review、Finding、approval、evidence 或 Gate。

## 范围

基线 fd560d9f12d28ef6ff155f6f46764d6c588d0f30，分支 codex/e4-report-import。
基线包含 TASK-0054 当前实现、正式本地 V1、独立审查和代码批准；本轮恢复检出并
取得其 Gate PASS。这不代替 E4.2 准入，不声称远端发布或旧原始日志当前可读。

治理实现：src/aiflow/external_review.py、src/aiflow/cli.py、src/aiflow/contracts.py
的两项登记与新契约专用安全诊断，以及 .ai/schemas/ 下的新
external-review-import.schema.json、external-review-repository-mapping.schema.json。
不修改 E4.1 envelope 或既有契约。新契约诊断不得回显未知字段名、值或输入路径。
安全测试、fixture、文档按维护模式独立实现提交，累计范围列入
tests/unit/test_external_review.py、tests/integration/test_external_review_command.py、
tests/unit/test_contracts.py、valid 目录的 external-review-*.json、invalid 目录的
external-review-*.*.json、docs/operations/external-review-import.md。
本 task 的规格/分类/审查/批准/证据仍由现有 CLI 追加维护。

### 固定 CLI 与输入

```text
python -m aiflow external-review preflight TASK-ID --envelope FILE --report FILE [--repository-mapping FILE]
python -m aiflow external-review record TASK-ID --envelope FILE --report FILE [--repository-mapping FILE] --expected-preflight-sha256 SHA256
```

TASK-ID 必须显式指定已存在任务；阶段取 envelope.target_context.review_stage。
preflight 输出安全 JSON 到 stdout，不创建 task/context/日志/缓存/目录；只用
read_task_record_strict 与 build_review_context 等只读接口，不用会恢复写回的加载器。
record 缺预检摘要由参数层拒绝。envelope 是 UTF-8 JSON，最多 256 KiB；mapping 最多
64 KiB；原报告是不解释的原始字节，非空且最多 16 MiB。读前/读中均限制长度；JSON
拒绝 BOM、无效 UTF-8、重复键、非有限数、未知字段和错误顶层；有界词法检查限制
嵌套深度 32 后再解码。原件不解码执行、不复制入 Git/task、不访问链接或加载代码。

输入须为 .ai/tasks/ 之外的本地普通文件；从根到叶拒绝符号链接、junction/reparse、
目录/设备/FIFO；Windows 元数据访问前拒绝 UNC、设备路径、ADS、网络盘、保留设备名
和尾随点/空格。相对路径先按当前目录词法展开。读取句柄与前后路径的身份、大小、
修改时间及 SHA 核对，增长/替换拒绝。本机绝对输入路径不进入 stdout 或持久记录。
受控目录前后检查不声称抵御恶意并发目录替换的 OS 沙箱。

source HTTPS 和 repository locator 只作标识；解析及百分号解码检查 userinfo/query/
fragment、控制字符、反斜杠、编码鉴权与路径逃逸，不联网或猜 UUID。finding location.path
为 POSIX 仓库相对路径，不访问目标文件；拒绝绝对/盘符/反斜杠/空段/点段/ADS/控制字符。
scope、fact/evidence refs 是便携引用或无鉴权 HTTPS 标识；可解析为路径/URL的项同样
检查，拒绝本机绝对路径、鉴权和控制字符。自由叙述作为不执行声明保留；不宣称能识别
任意正文秘密，操作者不得提供含秘密输入。诊断从不输出正文或任意用户键名。

### 当前任务与来源核对

严格只读任务物化记录/events、当前 Policy、classification、冻结规格；要求当前规格
摘要等于 frozen_spec_sha256，按共享 freshness 检查 classification fresh。当前分支
须等于 task.branch，UUID 与当前仓库相同；HEAD/base/subject 按既有 ancestry 与同 task
合法治理追加规则核对，允许 subject 后合法账本提交，拒绝未同步源码/配置或无关 dirty。
design 只接受 WAITING_FOR_SPEC_REVIEW、READY_TO_IMPLEMENT；implementation 只接受
VERIFYING、VERIFIED、WAITING_FOR_FINAL_REVIEW、APPROVED_FOR_MERGE，并要求 evidence
passed/fresh，V2 使用现有完整 snapshot 规则。其他状态拒绝，不为导入改变任务状态。

重新构造完整 review context，对比 envelope 的 task_id、UUID、阶段、base、按阶段
处理的 subject 与 context_sha256；design 不带 subject，implementation 必须带。
构造 context 不代替 freshness，不先补历史 context 文件。独立比较 source_subject 的
阶段/base/subject，缺失或不同直接拒绝；原件 SHA 必须等于 source.raw_sha256，摘要
不认证原文受审对象。source_finding_id 重复拒绝；suggested mapping 必须引用本 task
已存在 review_id、精确 revision/finding_id，只读核查历史 Review 及对应 context，
Review 的 review_stage 与 context_sha256 必须等于当前完整目标 context；历史引用即使
存在但属于旧 context 或其他阶段仍拒绝。不能用其他 review/revision 的同号 RF 替代，
不自动转换关联或执行 resolve。
completed/incomplete/tool_unavailable/timeout 均保留来源原义，不提升为正式通过。

UUID 来源必须精确等于目标 UUID，额外 mapping 输入拒绝。locator 来源必须提供封闭的
external-review-repository-mapping 1.0：kind、schema_version、mapping_record_id、
locator、repository_id、confirmation；confirmation 沿用 E4.1 checked_by_label、
checked_at、method=manual_report_git_check、fact_refs 及上限。locator/mapping ID
与来源逐字相同，UUID 与目标相同；缺失/歧义/错配拒绝，不按简称、大小写或 .git 推断。
这是操作者可追溯核定声明，不是身份认证或自动理解原报告。

### 预检 token、版本与原子追加

canonical JSON 固定 UTF-8、ensure_ascii=false、sort_keys=true、紧凑分隔符、无非有限数。
input_sha256 是完整 {envelope, repository_mapping} 的 canonical 摘要，UUID 模式的
mapping 为 null；含来源确认、所有映射、覆盖、处置和原件 SHA。空白/键序不改变语义
no-op，但会改变本次预检的原始输入字节摘要。
task 内来源系列 source_key_sha256 是 {product, source.location, resolved_repository_id,
source_subject.review_stage} 的 canonical 摘要；版本地址为 report_version 的 SHA256。
地址不得包含 raw/context/input SHA，避免同版本改内容后绕过冲突。定位符变化声明
另一个系列，不声称识别报告别名或伪造身份；版本标识不按字典顺序推测新旧。

preflight 结果只含 status/reason_codes、task_id、阶段、context_sha256、input_sha256、
source_key_sha256、拟相对记录路径与 preflight_sha256。token 绑定 envelope/mapping/
report 的原始字节摘要、完整 canonical 输入、task/events/spec/Policy/classification/
evidence、精确引用的正式 Review/context 摘要、有效 Git 事实及该来源系列完整既存
记录清单摘要。成功不写文件，不是授权或认证。record 重新读取全部输入和绑定，比较
expected token；不能复用旧预检对象。失败、漂移、冲突先于目录/guard/临时文件创建。

发布前取得来源系列的独占 guard，持有期间重读核对所有绑定；既有 task writer 不参与
该 guard，故仅承诺受控目录的 drift 检测与旧记录不覆盖，不声称任意并发原子快照。
同 token 竞争者只在既存完整输入相同且其他绑定未变时 no-op；其他漂移拒绝并清理
本次临时产物。系列记录须为唯一无分叉版本链，无共享可变 latest 文件。
最终路径：.ai/tasks/<TASK-ID>/external-reviews/<source_key_sha256>/<version_sha256>.json。
路径只用计算所得十六进制，复用 task 守卫并拒绝目标及祖先 link/reparse。

external-review-import 1.0 为封闭对象：kind、schema_version、source_key_sha256、
input_sha256、envelope、repository_mapping、可选 previous_record_sha256；嵌套对象
复用各自契约，service 校验摘要/绑定/链关系。首版本无 previous，新版本引用真实唯一
旧链头的完整 canonical 记录 SHA；不记录运行机器路径、原件正文或正式批准字段。
同系列+report_version 完整输入相同才 no-op，任一字段不同冲突；新版本才追加，
重放旧版本不改变链头。已有记录损坏/未知字段/链分叉不得作为新版本的正常基础。

使用同目录临时文件、flush/fsync 与 OS 原子 create-only 发布；禁止 exists→os.replace
的覆盖窗口。不支持 guard/create-only 时拒绝，不降级。竞争既存文件只读比较。
原子 create-only 成功是提交点，之后不删除/撤销新不可变记录。提交前的正常失败清理
本次创建的 temp/guard/空目录，task 全目录清单和字节不变。成功只新增一份 import，
不写 task/events/context/formal review/approval/evidence/Git index。
提交后的 temp/guard 清理失败报告 recorded 与 committed_cleanup_required；不得标成
普通零写拒绝。stdout 交付失败可导致操作者尚不知结果，须通过重新预检查明已提交
记录；预检仍零写，并能区别完整已提交记录与遗留 guard，给出明确清理需求。
提交前突然中断可留可识别临时材料，旧正式记录无损；遗留 guard/坏链禁止下一次
record 自动恢复或覆盖。恢复说明只核对并处理本次临时材料，永不删除成功 record。

## 验收条件

positive/negative fixtures 全部明确 synthetic；不修改真实报告制造正例。

| 编号 | 必须观察到的结果 |
| --- | --- |
| I1 | UUID/显式 locator mapping、design/implementation 合法预检给 token；task 全目录/字节不变，坏物化账本不恢复、不补 context |
| I2 | 显式 record 首次一个 import，重新预检重放 no-op；JSON 空白变化语义 no-op，旧字节与链引用不变 |
| I3 | 同版本 raw/mapping/覆盖/来源确认/context 变化、错 repo/base/subject/context、stale spec/classification/evidence、源码漂移及预检后各输入变化在写前拒绝，task 字节不变 |
| I4 | 已有真实 dotfiles/51044a55 原件若当前可核验，保留真实 source_subject 指向 harness TASK-0053 后拒绝错配；不可读则标未验证并以同结构 synthetic 负例验证算法，不伪称真实验收 |
| I5 | incomplete/timeout 保留原义；注入不执行；鉴权URL、encoded逃逸、输入/输出路径逃逸、links/reparse、拒绝状态、未知字段安全拒绝；两流无合成secret/未知键名/正文/本机路径 |
| I6 | 前后 task/events/formal review/approval/evidence 字节相同；相同受控Git事实下 status/Gate/formal review选择结果相同，不隐藏新增文件引起的实际Git dirty |
| I7 | 重复键、BOM、深度/字节超限、读时增长/替换、SHA错配、缺/错来源核定/mapping、重复问题ID、错复合finding引用、旧context或跨阶段Finding映射安全零写拒绝 |
| I8 | 同版本并发相同/不同输入不覆盖；不同版本guard下链无分叉；旧版no-op不改链头；提交前写失败/create-only不支持零残留，中断不损旧record；提交后cleanup/输出失败保留新record，重新预检识别已提交及清理需求 |

固定候选后运行全部 Policy-required checks，完整测试、总覆盖率至少 85%、diff coverage
至少 90%、whitespace、Ruff、format、mypy。实际分类决定 route/V；本任务要求 acceptance、
integration、独立 verifier，按现有 Policy 办理 V2，不用定向测试代替。设计/实现独立
审查、正式证据、code approval 和 Gate 按 CLI 真实结果完成。
匹配目标 task 的真实 ZCode 报告留作后续单独明确记录动作的验收输入；本实现 task
不调用 provider、不造真实会话、不写其他历史 task。无原件/授权保持未验证，不妨碍
离线合成验收，也不宣称真实导入已完成。

## 非目标

不实现任意 Markdown 解析、来源/模型/独立性认证、联网、付费调用、外仓写入、fix
编排、自动 resolve/severity/outcome 转换、自动批准、E4.3/E4.4、runner/provider/可信
执行、阶段三四；不修改旧任务/记录、Policy/CI质量门。

## 禁止动作

不执行 push、merge、deploy、delete、secret_export、paid_external_call；不改 Git
index、不删除历史账本/证据，不执行报告内容。旧批准不扩展为 E4.2 或外部动作批准。
设计审查及当前 spec approval 完成前不得 begin 或修改上述治理实现。

## 错误行为

拒绝用固定可区分 reason_codes，不插值用户输入或异常正文；不自动恢复 task、补
context、忽略 mapping、放宽路径/预算，不伪造批准，不降级 route/V 或质量门。
preflight 零写和 record 提交前拒绝零写分别做全 task 快照断言，不能只比较几份正式文件。
提交后的清理/输出失败保留已提交事实，不伪装为失败零写，不删除新不可变记录。

## 回滚

实现用限范围前向提交撤回；历史 task/events/审查/批准/证据不重写。测试使用隔离
synthetic 仓库，仅清理本次临时产物。成功不可变 import 不覆盖删除，需更正按新版本
追加；未来发布/真实记录另核定精确候选和授权。

## 执行依赖与文件归属

准入串行：事实完善、分类、冻结、1 名独立只读设计 reviewer、处理反馈，按 status
Missing 取得实际 spec 决定，再 begin。未准入只准备规格/合成验收设计。
实现并行 2 名 sub-agent：一名独占 external_review.py 加载/绑定/预检，先冻结接口，
原子记录由主 agent 待其完成后串行接入；另一名独占两份专用安全测试、fixture 及
test_contracts.py。主 agent 独占新 Schema、registry/CLI 与文档。集成后固定候选，
主 agent 串行正式 V2；2 名只读 reviewer 分别审边界/存储、兼容/测试；独立 verifier
按 V2 context 办理，最后由主 agent 统一账本和阶段提交。


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


## 2026-10-01 additional platform API lookup admission

# TASK-0055 platform API lookup amendment (2026-10-01)

This is an additional same-route spec_changed admission, not a reduction of REVIEW/V2. Previous frozen specification 3c014d67a353f93c22377aff85584532a397cc41fd5cbb0cec4ff6e6b75d7e88 is preserved byte-exact as spec-snapshots/spec-003.md. All earlier specifications, failures, approvals, reviews and dependency evidence remain unchanged.

The importer transport stage e03bfb1 and separately committed maintenance safety tests/documentation 72294c1 were verified with the complete two importer test modules: 305 passed, one pre-existing FIFO skip, actual exit 0. Source SHA256 was 0a77f2b9ace59cc92acd0b38f30820b401d7e2d219b94735a7e44c5e87165209. Independent raw-capture checks matched all 13 handback entries. This is focused Windows evidence only, not current whole V2 or Linux execution. The failed initial run is retained.

Additional full Linux-platform mypy diagnosis failed with four attribute errors across 44 source files; stdout SHA256 2df2bcb83f2846553d5d93c0922bbf537ed1dc87259ba59a52748c719ea2041f. Windows file mypy and Ruff/format passed. This diagnosis is a real remaining issue, not waived by earlier TASK-0056 or focused test passes.

## Exact newly admitted production work

In src/aiflow/external_review.py, change only three Windows-specific attribute access expressions: ctypes.windll in _lexical_path and subprocess.CREATE_NO_WINDOW / subprocess.CREATE_NEW_PROCESS_GROUP in the newly admitted transport. In src/aiflow/verification_temporary.py, change only ctypes.windll in _drive_type. Use getattr(module, literal_name) without a default. Preserve the same underlying Win32 API, arguments, flags, integer conversion, platform guards and allowed drive types. No fallback, replacement signal, cast that hides a changed value, default zero flag on Windows, exception remapping, path acceptance change, PID/session ownership change or deadline change is admitted. The previous importer-only production-purpose restriction is broadened solely by these two existing drive-guard lookup expressions; the original 32 allowed patterns remain identical.

The TASK-0056 control checkout, source 9dca04dc18e1551dc86987eb594f84f9d37b47ad and its 106 imported tracked ledger blobs remain immutable. The new derived verification_temporary.py expression is TASK-0055 work with its own validation, not a re-opening or substitution of the dependency pass.

All I1-I8, source/report matching, zero-write refusal, original writer interruption/recovery boundaries, transport waits/retained-process limitations, quality thresholds, 14 required checks, five fixed mutations and every original budget/selector/MINENV remain required. Real report acceptance F remains missing authentic input; no provider or paid call is introduced.

## Validation and role plan

Admission is serial: append DU/spec and stage commit, native sync, spec_changed resolution, classify/freeze, actual author-independent design Review, status-directed owner-delegated spec approval under the existing human authorization, then begin. Only after begin may root perform the four substitutions.

Parallel preparation uses two sub-agents: one actual independent design/implementation reviewer, one actual independent native verifier preparing capture only. Root owns specification, four production expressions, governance and unified commits. Existing safety test author is not a formal independent reviewer/verifier. No agent modifies shared source/refs during native verification.

After implementation, run Ruff/format and full mypy on Windows plus additional --platform linux static analysis, and meaningful existing importer/temp-root unit tests. Full native TASK-0055 V2 on its own fixed source/HEAD remains serial and mandatory; Linux real integration execution is verified by exact publication-head CI. Then actual independent implementation Review, same verifier finalize, current code approval, Gate and exact post-commit Gate. Publication remains separately admitted, with fresh exact-candidate/base/head approvals and unchanged branch protection.
