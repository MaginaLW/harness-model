# ZCode 准备报告回收与独立核定：2026-10-03

## 2026-10-04 当前核定：私有 Job 候选一次 qualification 与独立私有核定完成

本轮私有修复授权仅覆盖候选与单次自有进程 qualification。实际 run 为
`harness/run-8e27688a33d945a69a57511711a84ba6`，9 passed / 10.37 秒 / rc 0；5 项真实
Windows 与 4 项 safe mock 分开记录。独立终态审计已封存，结论为
`CONFIRMED_PRIVATE_QUALIFICATION_ONLY`，无数据阻断，非 native 验收或生产批准。
详见[私有超时修复记录](windows-private-timeout-repair-2026-10-04.md)。

独立审计相对引用为 `ownaudit/import-acceptance-terminal-audit-001.json`，23171 字节，SHA256
`89a3ba3daf6b151f76372ed8d363c582c3fee829242663e86b92f169017fc8a9`；只核定本次私有
qualification 与原件/恢复边界，没有创建 native Review、event 或 approval。

私有目录以 basename `harness-model-private-repair-20261004-001` 定位。实际 helper
`candidate/windows_owned_job.py` 为 25735 字节，SHA256
`02e81bbf3878fb1ed581bf7ca14eb560a97bef4f57b514b462ea233ec211d2ef`；runner
`candidate/process_runner_private.py` 为 12799 字节，SHA256
`43456426d0083e875c0db41e0eafbab29efa7023177f7e5aac6e043e9e07903b`。
sealed bundle 为 3933 字节，SHA256 `a17bc5c1900907f2f0138f419cb3bff80dfd1ed284ebb201d71eab26497c95f1`。
原始文件留私有目录；不把含本机路径的候选 receipt、bundle 或 raw JSON 直接入库。

实际方案无 global patch/kill-on-close；两个真实 timeout 的自有 active 0、parent signaled、
drain/threads complete、handles closed 有记录。normal zero/nonzero 结果保持；normal live-child
release 的 active 2 是实际 accounting 记录，其后自然结束，不误写为超时清理失败或两条
独立存活进程证明。四项 mock 只覆盖控制流，terminate/drain 故障的 errors、retained handles
和未验证状态保留，不能被 9 项 pytest PASS 改写为全部 OS 清理成功。

outer 11.128385 秒，self-owned active 0、parent reaped、handles closed、cleanup CONFIRMED、
supervisor pass，无额外 survivor cleanup。396 个指定保护 entry（333 file、61 directory、2 absent）的实际 bytes/目录状态/identity 一致，
raw-before 留存；manifest 排除的 6 个 `__pycache__` 目录、whole main 与 host temp 完整字节证明未采集。
child 原件的 `collection_binding_preserved_function`、`original_function_preserved`、
`original_run_execution_binding_restored`、`original_test_bytes_unchanged`、
`public_result_fields_unchanged`、`public_run_execution_signature_unchanged`、`hooks_restored`
均为 true：原测试函数/字节保留，隔离 qualification 临时使用私有 runner 绑定后已恢复。
这不等于生产 runner 已修复。

qualification guard 窗口观察到 primary HEAD `1ff6e964f7f0944176c420ca55a57b885272f325`、
performance worktree HEAD `ef5943b29514ad1d13121023610bf4c2c4dcb408`。TASK-0064 仍 FAILED / REVIEW / V2、Missing `retry_reason_or_escalation`，action SPENT；
F 仍 BLOCKED，GitContext c7/source S507 保持。旧失败根因 UNKNOWN；本轮不是原生 V2、
新 Task、生产实现或旧任务恢复，没有重试旧 blocked proposal。下一依赖是具体生产治理设计
准备（尚未启动）；生产须独立治理 Task 的
实际 scope/helper 路径、规格、独立 Design Review、Missing 批准与后续新 action/完整验证。
受控位置参数、CPython 3.13.15 与 crash/orphan 限制见新记录；不扩称安全 sandbox、旧失败
已解决或有新 paid/push/merge 权限。下方所有原件和历史结论保持。

## 2026-10-04 历史窗口：TASK-0064 原生 FAILED/SPENT 原件已保留

分支 `codex/git-context-read-protocol` 的 TASK-0064 一次完整原生 V2 run
`run-20261003T153150710903Z` 已结束。CLI 命令 exit 0 不代表验证通过：实际 conclusion
为 failed，14 项中 11 通过、3 失败，当前 FAILED / REVIEW / V2。source subject 仍是
`50777d648765a935c265e2d12e292d325fabeb1f`，source SHA256
`c7d00dddecb8f06a8059c3a1f74b01d554bd14b6be610d3bc1db5ac0705b0755` 不变；当前 observed HEAD
`ef5943b29514ad1d13121023610bf4c2c4dcb408` 为诊断摘要治理提交。失败、消费回执及原 V2
便携摘要阶段提交 `4de35cc5af62c38619afb3a0cd7117fedcb94301` 保留，源码候选未改变。

- regression：900301ms，RUNNER_TIMEOUT，完整 pytest 计数 UNKNOWN。
- coverage：1118810ms，exit 1，3036 passed、1 skipped、1 failed；节点
  `tests/unit/test_process_runner.py::test_timeout_kills_child_process_tree` 的 child sentinel 断言失败。
- integration：600434ms，RUNNER_TIMEOUT，完整 pytest 计数 UNKNOWN。
- unit：2010 passed；同 run supplemental overall85 显示 89%，原 coverage 数据 SHA256
  `d78082f8dcd7c1cefbb0da704409c8d75f9cba416d278bc872e93222fa6b697d` 前后不变；原生 diff
  为 33 changed executable lines / 0 missing / 100%。这些通过项不覆盖三项失败。

精确 action `dd1502a97b726e3b8f8b027a146b5ae730695a625f03700378c62ac6ad91bf22`
已由真实所有者批准记录为 event 17，event 19 消费，event 20 记录验证失败。mutation run
`MUTRUN-20261003T161743Z-deb1a5e1387441f0` 的五项 canonical mutation 均 killed，action
现为 SPENT，不可复用或自动重跑。detector stdout/stderr 为 DEVNULL，保留真实 baseline/
mutant 退出码、timeout 与派生结果元数据，不能据缺失的原始流独立定位断言；
main_tree_unchanged 不等于全业务字节或每条路径清理的证明，不追加清理或补造证据。

上述分支/提交内 `.ai/tasks/TASK-0064/preparation/v2-terminal-summary-001.json` 是便携摘要，
6255 字节，SHA256 `1ce2f591cdfd68e2b9b98a9a027194648ccf1ea938232c61ce3de79b01504c96`。
原生 `evidence.json` 为 11978 字节，raw SHA256
`075d18f5cd317c3077431fb22183e4faf0893eae025dc0ed73e5a704432dd583`；它含本机解释器、
coverage 与夹具绝对路径，原字节保留本地 untracked 和私有 raw archive，不入库。
便携摘要不是替代原生 evidence；独立核查结果与原件留存引用见该摘要。

CLI classification fresh、approvals current、evidence stale，Missing 为
`retry_reason_or_escalation`。implementation Review、finalize、code approval 和 Gate 未完成；
14 项检查、预算、85%/90% 阈值保持。sentinel 记录证明写入发生，不证明 child 在 runner
返回后仍存活；原始 taskkill 返回码、流和时序未留存，失败根因为 UNKNOWN。

后续一次隔离观测诊断保持原测试、源码、断言、1/5 秒限制与 2/10/3 秒时序，原失败 node
实际 1 passed / 4.19 秒 / rc 0。taskkill 原调用 rc 0、157.7557ms，stdout 348 字节含 4 条
SUCCESS；本次 sentinel 不存在，未出现 fallback parent.kill 事件，脚本指定保护目录
实际字节前后相同。实际 pytest 调用/attempt 均为一次，retry 为零，未查询事后进程存活。
私有诊断原件 `task0064-process-timeout-controlled-diagnostic-001/run-001/diagnostic.json`
SHA256 `39bb036617d718a4917babefcb76b909d23e65d225812294e74e3869fecc32a2`。
该单次诊断 PASS 不改写旧 native FAILED/SPENT，不确定旧失败根因，也不证明完整 V2 通过。

该分支提交 `ef5943b` 已追加 `.ai/tasks/TASK-0064/preparation/process-timeout-diagnostic-summary-001.json`，
4831 字节，SHA256 `fb26a637bcb4a74ad953977a8b647bcebe11243fa3a0b607f8b6e98613813020`。
六项私有原件的字节/哈希引用均已重算匹配；独立诊断审计为 21060 字节，SHA256
`2177f5f1f50bd475700fd0bfc0574d002db77dd06cb0f0b566c90f56f53f415c`。SUCCESS 输出不等于
独立事后存活测量，观测也可能改变时序；保护范围不包含整个主工作区业务树的字节证明。

TASK-0063 仍 BLOCKED；旧付费来源仍只绑定 `070b364c`/`165c5dc2` 原窗口，6 项 pending、
3 条勘误、旧 FAILED 原件与已消费 action 保持，不重标新 context 或复用。TASK-0064 不
代表 F 验收，也不授予新付费、push 或 merge 权限。下方未批准及 false 标志完整保留
历史准备时点，当前以真实追加 events 17–20 和失败原件为准。

## 2026-10-03 历史窗口：TASK-0064 精确恢复与独立设计复审完成

分支 `codex/git-context-read-protocol` 的 TASK-0064 已按真实所有者授权完成
`new_permissions` resolve/classify。event 11记录人类精确授权，events 12–13恢复
REVIEW/V2并要求新设计审查；实际分类input为
`588bbb4bc50aa04aa114b8cf3d290de124dd40f13f199a8e40434508958e0490`。
source subject仍为 `50777d648765a935c265e2d12e292d325fabeb1f`，base
`1fea00217533b01a7b9908f053ccaca43571f6f8` 和spec `203bc36e`保持；实际源码14748字节，
SHA256 `c7d00dddecb8f06a8059c3a1f74b01d554bd14b6be610d3bc1db5ac0705b0755` 未改变。

新design context `a4545a40c7199b9a2bae1b91a162bb91f894aa06ea887f9fcba1680e3b1e0841`
由真实独立reviewer `subagent/import_acceptance_audit` 审查，REV-0003 r1
APPROVE/findings为空，event 14原生记录。event 15沿用仍有效的原spec批准完成机械
状态转换，event 16 begin；不把它解释为新增人类规格或mutation决定。
只读核对当前原件及CLI status为 IMPLEMENTING / REVIEW / V2、classification fresh、
approvals current、Missing仅 `implementation_result`，validate/scope通过。自身恢复记录已提交
`5627d32b5298cb8161d74f2affe38b1c6769bfde`，observed HEAD为该提交；相对source subject
仅增加12个自身任务治理路径，源码c7字节不变。新记录通过上述分支、任务与提交定位。

精确单次action `dd1502a97b726e3b8f8b027a146b5ae730695a625f03700378c62ac6ad91bf22`
仍未批准、执行或消费。任务内请求 `preparation/mutation-action-request-001.md` 已由
`v2_consistency_review` 和 `cache_patch_review` 独立纯读核定PASS，下一依赖为精确单次
Action批准 → 完整原生V2。完整V2未运行，85%总覆盖率、90%diff、final Review及code
approval/Gate仍待完成，原14项检查、预算和阈值保持。恢复/设计Review/spec批准均不
授予mutation权限。原恢复提案的 `owner_recovery_authorized: false` 保存历史准备时点，
当前恢复授权由追加event 11证明；`targeted_mutation_approved: false` 仍反映当前事实。

TASK-0063仍BLOCKED；旧付费报告仍只属于 `070b364c`/`165c5dc2` 原窗口，6项pending、
3条勘误、FAILED原件及已消费action不改写、不复用。局部测量不证明旧600秒超时解决，
TASK-0064恢复不代表F完成，也不授予新付费、push或merge权限。以下BLOCKED与旧提案
false标志均保留历史，不以准备快照覆盖实际追加事件。

## 2026-10-03 历史窗口：TASK-0064 源码阶段与新的权限缺项

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
