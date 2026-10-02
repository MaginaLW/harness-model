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
