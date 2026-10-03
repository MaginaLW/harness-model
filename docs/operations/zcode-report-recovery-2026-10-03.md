# ZCode 准备报告回收与独立核定：2026-10-03

## 2026-10-03 当前核定：TASK-0064 源码阶段与新的权限缺项

独立治理任务 TASK-0064 位于分支 `codex/git-context-read-protocol`，源码阶段提交
`50777d648765a935c265e2d12e292d325fabeb1f`。原冻结规格
`203bc36e9f663198b4c7b7079d0ddf1a609736f13ec5a21c7831ec0857b345a6`
已获真实人类批准并原生 begin，仍 current；实际源码14748字节，与preview003核定字节一致。
通过分支、任务及提交定位这些记录；main 尚无本任务文件，源码未合入 main 或 F 分支。

源码阶段30 passed/4.19秒，Ruff check/format、mypy44及working/staged/committed diff check
均通过，native sync与scope检查通过。synthetic002 的37项和完整traces通过；synthetic001
保留实际执行35/计划37、34通过/1失败的原结果，检查脚本还原 `__code__` 的失败不抹去。
real002 实际15场景、33对比较、390条Git命令及1170项raw记录通过；两个真实HEAD同名tag
的P2场景均核到正确branch，并走5次查询的完整回退。健康分支10对调用的中位数
112.8176→58.38445ms仅为正常路径局部结果，不证明旧600秒超时修复或整套收益。

随后原生 event 10 执行 `new_permissions → BLOCK`，TASK-0064现为BLOCKED，DU权限需求仅由 `[]` 增加到
`[action_approval]`。源码subject/HEAD仍为上述提交，pending task记录未提交；classification
stale、规格批准仍 current，实际Missing为 `block_resolution`，stable input摘要前缀 `588bbb4b`。
精确恢复提案与独立单次action草案已生成但未提交；当前仅请求 `block_resolution` 恢复授权，
action草案未请求、未批准。canonical mutation/action执行、完整V2、
85%总覆盖率、90%diff coverage、final Review及code approval/Gate均未完成。
后续按实际Missing与新鲜绑定补齐，不重复请求仍 current 的规格批准。

TASK-0063仍BLOCKED；其原来源只绑定 `070b364c`/`165c5dc2` 历史窗口，6项pending观察、
3条勘误、FAILED V2、已消费action及原始detector流未满足条件全部保持。
TASK-0064的局部结果不代替F验收，不增加付费调用、push或merge权限。
下文按原观察时点保留，历史正文的“当前”不覆盖本节。

## TASK-0063 历史诊断窗口：全量未完成，治理源码另行准备

单次observer诊断使用原 `tests/integration -q` 和600秒执行预算，实际执行600004ms、
cleanup1ms，仍TIMEOUT。991 collected、762 started、761完整三阶段结果（760 passed、
1 skipped）；最后case只有setup，229个未启动，完整最终计数与未发出的call仍UNKNOWN。
它改变pytest启动方式，不证明普通运行等价。逐case报告与模块汇总仅描述已观察部分，
支持累计预算消耗；唯一根因及observer开销未核定。

独立审计重算3047行、991个case状态和43个文件哈希，受保护源码及两个index的运行窗口
实际字节相同，owned Job active=0、parent已回收、handle已关闭。F分支提交 `166fe31`
追加 `preparation/v2-failure-recovery-001/timing-diagnostic-summary-001.json`，不改旧任务记录。

正常分支新鲜Git元数据合并的小基准30次旧调用4.869785秒/120进程，新调用2.484744秒/60进程；
真实12场景及13模拟校准仅覆盖私有原型，不认证最终候选或整套600秒收益。001夹具设置失败保留。
独立Git源码审查进一步发现unborn/dangling HEAD与同名tag的身份反例，最终候选要求HEAD字段
触发一次完整legacy回退；detached也走回退，不能直接映射DETACHED。读取顺序、回退额外查询
和错误/竞态窗口是实质协议变化，当时正独立准备治理任务，生产源码未采用。
TASK-0063仍BLOCKED、原生V2仍FAILED、旧action仍spent；原付费来源及批准不成为新源码权限。

新治理任务实际分配TASK-0064，分支 `codex/git-context-read-protocol`；先提交安全测试
`1fea00217533b01a7b9908f053ccaca43571f6f8`（旧14+新16用例，30 passed/6.80秒，27原断言保留），
再以该native base创建仅允许 `src/aiflow/git_context.py` 与本任务目录的REVIEW/V2任务。
原生冻结spec `203bc36e9f663198b4c7b7079d0ddf1a609736f13ec5a21c7831ec0857b345a6`，
当时design context `24f2115a1f2cdc945d01dd6dca53cd90470648a7de960c0bcdfd8f1b120f2beb`；
非作者Design Review 001 APPROVE已原生记录，当时status为WAITING_FOR_SPEC_REVIEW，
classification fresh、Missing仅 `spec_approval`。当时没有begin、源码修改、原生新V2或新action。

## TASK-0063 后续维护：真实缓存资格通过，全量仍TIMEOUT

安全测试维护提交 `f04e8654e92d2d89284e11a39d40e8869e511eee` 限定四个精确inactive
Git键名，新增13个有意义反例；helper模块175 passed/117.73秒。新五例探针于
`2026-10-03T01:48:43Z` 开始，5 passed/9.51秒，真实资格成功、cold=1、hit依次0→4。
原始41件探针材料的manifest SHA256为
`755da076e9d9d7267d154059c237fc31f99f1539e92166c256ec0fdf39ccdca8`。
该探针不替代完整integration或原生F。

随后一次普通维护检查于 `2026-10-03T01:58:04.042580Z` 启动原完整
`tests/integration -q`，环境仅PATH/SYSTEMROOT，600秒执行预算与单次10秒cleanup grace，
无筛选、profile、观察插件或重试。实际TIMEOUT/exit124；执行599999ms，含cleanup600001ms。
stdout1073字节，SHA256 `6ef318a164110602964e53495972d15043aad31d355da9b2dbf7728ac463c6a1`；
stderr0字节。输出停于94%之后，没有完整summary、collected nodeids或最终数量；
producer的默认零值不解释为零通过、零失败或零跳过。
原始process-result SHA256 `b864887ce54e78ee590a08da3f921c6a954f29c1319959505329fa37b1aacb8a`；
terminal manifest SHA256 `618fa0f3241a8023978b80956affcbcc9090562ccc6589a904a27e99db3060c9`。

2258份受保护文件、47个目录及索引在实际内存原字节/types/modes比较中相同，
HEAD保持上述维护提交。owned Job活跃进程0、已reap/close；没有清理目录或改写原件。
末尾用例临近截止仍写入，支持累计预算耗尽的推断；首尾initial reflog相同支持缓存复用，
尚无整套永久禁用或具体deadlock证据。此运行未采集cache遥测，不回填中段hit/miss。

私有原件位于 `<RUNTIME_ROOT>/harness-model-followup-20261003-001/` 的
`task0063-cache-maintenance-integration-001/`；便携摘要追加到隔离TASK-0063自己的
`preparation/v2-failure-recovery-001/maintenance-timeout-summary-001.json`。
当前只测量私有schema解析复用原型，生产源码不变；未生成pass projection或采用新恢复规格。
原F的FAILED/BLOCKED和spent action保持，以下原始执行窗口完整保留。

## TASK-0063 首次完整 V2 与失败原件

真实来源及导入封存证据已完成两路独立核定。唯一完整原生 V2 run
`run-20261003T001416071827Z` 于 `2026-10-03T00:14:16.071827Z` 开始，
生成证据时刻为 `2026-10-03T00:54:43Z`，实际 **FAILED**：14项中10通过、4失败。
unit 1993 passed/1 failed；regression及coverage_xml各2999 passed/2 failed/7 errors/1 skip；
integration在原600秒预算后 `RUNNER_TIMEOUT`，没有完整pytest结论。原证据路径
`.ai/tasks/TASK-0063/logs/run-20261003T001416071827Z/evidence.json`；CLI退出0表示结果已记录。

原五项mutation的baseline为0、mutant为1且killed；manifest和runner绑定未改变。
action canonical digest `13812c7f836fa3d87d34268ef239c562aec5d3f0299bb7cdae71862d7b7a5124`
已真实消费。现行 `src/aiflow/mutation_runner.py` 的检测子进程stdout/stderr接入DEVNULL，
因此该批准额外要求的detector原始流未留存。此处保留未满足条件；元数据不能替代原始流，
不得复用旧动作或伪造。producer报告main_tree_unchanged；独立观察未见遗留的注册变异
worktree，原HEAD不变；这些观察不等同逐临时路径清理或整棵业务树全部原字节的独立证明。

封存原75份任务原件共1695658字节，私有逐份副本和便携base64档案均核对原字节；
`.ai/tasks/TASK-0063/preparation/v2-failure-recovery-001/` 保存便携档案、清单及失败摘要，
原日志、事件和单次消费回执仍在原路径。只读同run覆盖数据复算约89.07%≥85%，
diff coverage为无可覆盖行的合法结果，不能覆写coverage_xml失败或完整V2结论。

原冻结范围不含必要测试修复，已真实 `scope_expanded → BLOCK` 后单独进行维护。
测试提交 `d8af0cc377925a343fe47d32753154a7aae16f18` 仅修改三份测试文件：UUID标记
定点复制、两份临时clone-local长路径设置。必要三模块187 passed/36.66秒及静态检查通过。
首次局部检查因新临时父目录未创建而发生setup errors，原件保留；修正的是临时执行准备。
另一次仅五用例诊断5 passed/9.05秒，资格检查因四个系统配置键名禁用当次缓存，
五次原构建累计1.305秒。首次V2没有记录session cache遥测，原因及完整超时修复仍待核定，
不把当次诊断填作旧run事实。

当前BLOCKED；更大维护候选、准确新规格/分类/subject、恢复及新单次动作仍在准备。
旧来源只属于下面的原冻结context；Gate不依赖重复external-review导入，后续收尾无需新付费来源。
尚未进行新F验证、implementation Review/finalize/code approval/Gate或推送、合并、部署。
以下来源窗口完整保留。

## TASK-0063 新的匹配来源与导入边界

此前四项准备报告不作为本次匹配原件。本次面向已冻结的新隔离目标，另有真实所有者
规格批准、一次初始来源发送批准、精确恢复及本地单次变异批准；批准按类型分别记录。
分支 `codex/f-real-import-acceptance`，业务候选 `f59aa2544701bc4e00644fd291e16b97314c41a6`，
spec SHA256 `070b364c23837dade0a91d7c8e6a7a10e2bc7bbcbfb298b296744ce59c35968d`，
design context SHA256 `165c5dc259714f91b575b9be295d91ca6a8d33aab411815adf273c7ce9e0e745`。

实际来源 SID `sess_a03fad08-dee6-44dd-9c07-1de9bffa0713`；唯一完成终稿为15810 UTF-8字节，
SHA256 `b29e335a03021ef6d13e5b36e1031dcdf7d8d4b20df21576b2988c97882b5355`。
原件定义为原生保存 final text 的精确 UTF-8 提取，不添加换行、BOM、规范化或过程拼接；
独立从保存行重建后逐字节相同。实际序列0→5和 final parent 指向唯一真实请求，
八次原生 Read 全部 completed、无错误/截断；没有保存的 shell/write/worker/API工具调用。
AGENTS 会话交付仅为源报告自述，未见显式 Read，不宣称九份文件均由工具读取。
保存的会话版本 `0.16.9`、模型标签 `GLM-5.3` 仅为实际来源元数据，
provider/model/reviewer 身份认证与传输原字节均为 UNKNOWN，不将一次发送当作一次 inference 或费用封顶。

请求2263字节 SHA256 `59bcc77dd2bbd9bff1c1aac4a29743bbe13630cd3ea32ae7938ca2a9e09613ee`；
实际保存输入2262字节 SHA256 `e6c218d830153bc69cef54b3e05a2e25ad359858d7868191c87f0b135939e85d`。
唯一差异是末尾 LF 缺失，原因 UNKNOWN；首次精确字节检查因此停止。原快照/导出/失败保留，
只用已有行作一次离线完成，实际字节和原始失败分别记录，没有源快照重试或重新发送。

envelope 的 source/target repository UUID、design/base/context 与当前 native 逐字段核定，
design 不含 subject；内部另核 base→业务 subject→自身治理 HEAD。六项原观察标题及内容
逐字保留、mapping 全为 pending，不自动生成或解决正式 Finding。三条独立勘误为：
旧准备报告排除条款不适用于本次新匹配报告；DU 的本地变异 action approval 不代表付费来源批准；
重复 no_op 实际在创建 guard/temp 之前返回。原报告原文不改。
首版 envelope 的证据 fragment 引用在静态审查中被拒绝，未实际 preflight；
仅改成合法 logical reference 并另存第二版，原版保留。最终 envelope 文件 SHA256
`f1385ff40c1e1b953a3104acbdd5172d76f0f8acb51b81c53cc42bd4039116e5`，两路独立审核通过。

实际首次 ready 检查点后，另一真实设计审查形成 REV-0004 r0001，由原生 record 追加。
context 和合法状态保持，旧 token `7ef6aef2` 以 `EXTERNAL_REVIEW_PREFLIGHT_STALE` 零写拒绝；
新 ready token `d555dccb` 才首次创建唯一 import，重复 `already_recorded/no_op` 零写。
十组 repository/stage/base/context/task/raw hash/同来源同版本冲突反例各执行两操作，
实际原因码匹配，共20次全树零写拒绝。33条命令于 `2026-10-03T00:04:12.547535Z` 封存完成；
比较覆盖完整任务树目录和缓存原字节，事件原前缀保存，未以任意文件追加模拟漂移。

私有材料继续位于 `<RUNTIME_ROOT>/harness-model-followup-20261003-001/`，
本次 archive ID 为 `TASK0063-ZCODE-DESIGN-003` 与 `TASK0063-REAL-IMPORT-RUN-001`；
完整采集、失败、离线派生、原件、envelope、whole-tree byte cache 和回执不入库。
封存证据正独立复核，完整 V2、五项动作消费、implementation Review/finalize/code approval/Gate
尚未完成。下面是既有准备报告核定，不能覆盖本次实际执行窗口。

## 既有四项准备报告核定

四个指定会话已完成回收核查。ZN-01/03/04 有完整终稿，主体接受并附勘误；ZN-02
消息实际取消、无最终报告。独立审查补齐条件门评估，不冒充 ZN-02 交付。F 仍需新目标
及其后取得的匹配真实报告。本仓核查基线为 `ed4b3e7a57d785b57670eed47170944e3532a832`。
3 名原生 sub-agent 分别只读审核 F、两个外仓、条件门；主 agent 独占取证、记录和提交。

## 来源与回收

仅查询[任务安排](zcode-next-stage-assignments-2026-10-02.md)中的四个 ID。索引 DB/WAL
复制前后源与副本哈希相同。会话 DB 的前两次全窗口检查因并发 WAL 更新拒绝，未查询，
失败原件保留；第三次分开取证：数据库在 WAL 取得前后完整哈希相同，WAL 自己的
before/copy/after 哈希相同。SQLite 仅以只读连接查询副本的指定 session/message/part。
不声明整个源库停止活动或复制绝对原子性，未连接、修复或改写源 SQLite。

回收时刻 `2026-10-03T00:27:53.767471+08:00`。私有材料位于
`<RUNTIME_ROOT>/harness-model-followup-20261003-001/`：失败/成功副本、来源哈希、四份
持久化行、终稿提取、清单和 GET 回执，不入库。没有查询账户配置、凭据或费用表。
UTF-8 提取绑定数据库保存文本，不认证 provider 传输原始字节或真实身份。
`assistant.txt` 是过程及终稿的聚合；正式终稿按最后 `finish=stop` 消息定位。

| 工作包 | 既有会话 ID | 终态 / Singapore 完成时刻 | 终稿字节数及 SHA256 |
| --- | --- | --- | --- |
| ZN-01 | `sess_a4f8e128-e510-4a96-94f9-2ededcc717d7` | stop / 10-02 16:21:48.009 | 15316 / `949567c532501f984dc7dfa58d223afdaee24ab9dc3c00e2efba66cf7cd7d84d` |
| ZN-02 | `sess_2db709cb-d466-4881-b09e-33beaf1bf9ea` | cancelled / 10-02 16:23:03.279 | 无终稿，不把空文件当报告 |
| ZN-03 | `sess_6a7aad63-be2c-4aa2-8004-fd8b69836c70` | stop / 10-02 16:37:29.139 | 10249 / `966e1ca2e45df2460d226bb47a59f3f717507ad50f1aade7f9008cb48c3890f0` |
| ZN-04 | `sess_bff4e119-950a-4508-9138-05479d3a6f4e` | stop / 10-02 16:44:23.555 | 10507 / `166e821578778b313776b5edb8119a40bf29f31462a18afaa3236aa9cf066922` |

ZN-02 只有 user 1/assistant 1；assistant 无 text/tool，错误为 model_request_cancelled、
turnResult=cancelled、retryable=false。取消者和根因 UNKNOWN；索引仍 completed，不能推导
报告完成，reasoning 不作报告。其他三份保存的工具均为 Read（13/18/23 次），分别有
2/1/1 次错路径或读取上限错误，随后更正或分段。未见保存的 shell/edit/write/API/worker
调用；这只证明记录范围内的工具边界。03/04 的第二条 user 是 synthetic Todo 提醒，
timeline 为系统 model_change，不能算第二次人工提示词或新批次。应用元数据记载
GLM-5.3、GLM-5.3-Flash、GLM-5.3-Flash；真实 provider/model 身份未认证。

## ZN-01 勘误与 F

11 次成功 Read 的完整内容与 `cfec0779f52a267f6bfe0fdfee71344ab7d68aa4` 对应文件
规范化文本逐一相等，证明内容版本对应，不证明当时 HEAD。8 份源码/契约/接口仍与本轮
基线相等，3 份状态/安排文档已有追加。Read 保存时段为 10-02 08:19:39.776–08:20:08.033 UTC。
报告列 AGENTS.md 为来源但清单无该 Read；可能来自已加载上下文，证据不足，保持 UNKNOWN。

状态、design 无 subject、implementation fresh passed evidence、context 匹配、expected-hash
消费及“不将准备报告当 F 原件”与源码一致。执行方案采用以下勘误，原件不改：

- Git 关系为 **base→subject→HEAD**，不是只分别检查两者为 HEAD 祖先。
- source_key 仅含 product/location/resolved repository/stage；report_version 派生 version_key，
  acquisition_method 不进入 source_key。
- 工具使用严格 JSON 且不执行内容；绝对路径及认证样式拒绝施于规定引用/路径字段，
  不声明扫描所有自由文本或拒绝一切“反序列化”。

最小单元是新 design-stage 目标：冻结[真实导入验收规格](f-real-import-acceptance-2026-10-03.md)，
经实际 CLI 准入及当前 context 后再取得匹配审查。不能向已 MERGED 或失败历史任务导入。

## 外仓证据与报告勘误

本地 Git 在 10-03 00:27:06 +08 核定两仓 main、净树和 cached upstream 相等。
主 agent 于 00:30:04–00:30:30 +08 仅 GET main/ref、准确 head runs/checks、attempt 1 jobs；
8 份 JSON 实际 exit 0/stderr 空，独立 reviewer 重算字节和 SHA256 与回执一致。
以下依据 API 结果及 step 状态，未复读 job 原始日志，未重跑 workflow。

| 项目 | 本地及远端 main | 本轮准确 SHA 的 CI |
| --- | --- | --- |
| ai-agent-dotfiles | `e93d5b65e9f8089337f0c146a724468870e40566` | [run 36944593176](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/36944593176) attempt 1 SUCCESS；repository gates + 3 shards 的 check/job 集合一致，全部实际 steps SUCCESS |
| r3s-VPS | `513a3d09afda748da053e5ddb7170dd6f33624a6` | [run 36748860600](https://github.com/MaginaLW/r3s-VPS/actions/runs/36748860600) attempt 1 CANCELLED；Windows job 110001982989/runner 21 的 7 步 SUCCESS；POSIX job 110001983313/runner 0/0 步/CANCELLED |

ZN-03 当前 head CI UNKNOWN 由本轮补证解决，不回写为原会话已验证。“实读三层一致”
证据过强：原工具没有读 schema/emitter/registry。独立 reviewer 另核当前 schema 3 的生产、
注册、正负 fixture 和 CI orchestrator 消费一致，历史漂移已修复。
c18-09 原始 completion/route/summary 绑定代码候选
`3897dc4fbe22487b80e30ed6212ffce4779368aa`，11 门/43 套件 PASS；full-validation
8445150 ms（8445.15 秒），8158 秒属于 c17。#181 红样本及 #182 后继收口保留，
不接受“#176–#184 全绿”概括。项目记载真实 Apply/部署尚未执行；S5 setup DryRun
三次 FAIL/零写的原记载保留，本轮未复验。

ZN-04 两笔历史双绿及 c35 Strict 只有项目记载，原会话未读树外原件，不能认证为原始结果
PROVEN。本轮重算四项入口/workflow manifest 哈希一致，它不替代 Strict。
现在 Windows 成功已实证，POSIX 缺执行；恢复 runner 后仍须准确 SHA 的实际完整结果。
本轮不改外仓业务、不操作主机或触发 CI。

第六项统一映射[接入方法](adoption.md#真实任务的执行与收尾)的实现前方案/实现后 diff 评审，
不是 R1-W06、终审或定向复审。I2 按[启动条件](next-stage-start-conditions-2026-10-02.md)
分别核需求、单一可信目标、权限/平台、等价检查、准确 CI、回退和准入。现有收尾不表示
扩仓完成；无新增实质方法缺口，回灌保持 no-op。

## 条件门的本轮独立核定

| 单元 | 结论及下一条件 |
| --- | --- |
| I1 | 已有同仓双 lane/main/guest 重启业务、恢复及原生收尾保留；其他生命周期无选定真实新需求 |
| I2 | 既有试点分别核定，新增可信目标/准入未选；POSIX 恢复不直接等于扩仓完成 |
| E5 引擎采用 | wheel 等基础存在；完整资源分发、非覆盖初始化、身份/Policy/存储/目标 CI 适配需实际目标及设计 |
| E5 provider | 缺实际 adapter、身份/费用/数据、超时/取消/分页/重复结果边界和授权 |
| E5 可信执行 | 缺身份根、服务授权、固定参数、过期/原子消费、凭据托管、不可变审计/恢复 |
| I5 / Phase 3 | 样本充分性/分层/隐私偏差、真实 V3 沙箱损失/回滚、版本化度量合同未冻结，仍 not_started |
| Phase 4 | 缺 Phase 3 退出、稳定接口、量化协调/暂停恢复/集中审批需求，仍 not_started |

来源：[task02 验收](../implementation/task02-runtime-integration.md)、[阶段三输入](../implementation/phase-03-entry-inputs.md)、
[启动条件](next-stage-start-conditions-2026-10-02.md)、[Hooks](hooks.md)。overall.yaml 的旧
Sol/max 与 Sol/high 漂移保留历史；[当前型号规则](model-selection.md#历史记录)明确不恢复
任一固定值，其余门不因此解除。可并行准备样本/V3/度量提案，方向决定、冻结和准入串行。
未定阈值、身份和费用保留未知，不补造充分性或改善结论。历史任务、失败、批准、配置及
三份用户草稿保留，本轮记录仅本地。

## 本地验证与新目标准备

文档候选 `3d6528284bc6e867def4fc8139ef67a41544ae48`、比较基线 `ed4b3e7`：
完整 pytest+branch coverage 在 2026-10-03 00:41:37–01:00:44 +08 实际 exit 0，
3008 passed、1 skipped（Windows 无 POSIX FIFO），89.05% 总覆盖率达到 85%。
`diff-cover --fail-under=90` exit 0、差异无可覆盖行；whitespace exit 0。
前置 contracts 185 passed，lock check、Ruff、format（615 files）、mypy（44 source files）通过。
私有 stdout/stderr、coverage XML、命令/真实退出/时间回执保存在同一运行材料目录，
测试未改本地已有 coverage 文件。本节及最新交接只是结果追加，不再变更执行代码。
这些是本地主检出验证，不替代新任务原生 V2 或远端 required CI。

新隔离分支 `codex/f-real-import-acceptance` 从该候选创建，native start 分配 TASK-0063。
准入先修正本任务自身记录范围，native classify 为 REVIEW/V2；独立技术设计审查 APPROVE，
当前 WAITING_FOR_SPEC_REVIEW，Missing 只有 spec_approval。复制规格的一个相对链接
修正后重新 freeze；先前冻结字节保存为 `preparation/spec-frozen-001.md`，旧 context/Review
保留，新 context 保存为 `preparation/design-context-002.json`。一次重新 classify 因
Git baseline 不同拒绝；decision unit 未改变，既有 classification 仍 fresh，freeze/status
成功，不改 baseline 或降低路由。当前 spec SHA256：
`070b364c23837dade0a91d7c8e6a7a10e2bc7bbcbfb298b296744ce59c35968d`；context：
`2bfa873bda2125336b48b7181ba2a7de1ca568aac435b21af0d1ec4a67fcd605`。

具体新 ZCode 提示词与独立付费获取方案的 revision 002 已保存为私有材料，绑定该目标，
只读、最多一次初始发送、无自动重试/其他 worker/账户模型权限变更；提示词 SHA256：
`c2f846d3913ce80fccb61801a5b160ff1a112ce10a0007a632025ac921fdf640`。
原生规格批准不是该外部动作批准，两项均尚未取得，未发送新会话或执行 F preflight/record。
原生 V2/Review/Gate 和真实发布/close 仍是后续步骤。

补充只读 runners GET 窗口 2026-10-03 00:50:53.235389–00:50:54.632693 +08：
r3s-VPS Linux runner 22 offline、Windows runner 21 online，两者 busy=false。
626 bytes、SHA256 `ec141fe40d976726083d5ce3c2e600018dc185ba083d898620f6fada34541a37`，
实际 exit 0，独立重算与回执一致。在线窗口不证明取消原因，也不替代准确 SHA 的完整 CI；
未恢复主机、重跑 CI 或新增远端发布。
