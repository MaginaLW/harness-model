# 后续待完成项目：2026-09-22 核定

## 2026-10-01 Schema 读取成本已短测

20原函数/20独立分解调用实际exit0、输入前后相等、known资源已交回。
原whole median1.25015ms；分解每18项的readUTF8 median0.72270ms，JSON0.24435ms。
分解开销未知，不合计medians或外推原600；便携记录为
`.ai/tasks/TASK-0056/schema-phase-cost-diagnostic-014.md`。
下一步2名sub-agent准备及独立审查仅成功域的binary UTF8读取私有对照，执行串行。
保持全部18当前读取及JSON/Resource顺序；原型缺正式兼容守卫，未选择生产实现。
并发复制原型也未运行，readonly目录提前copystat风险阻止直接替换；原门禁保持。

## 2026-10-01 定向成本诊断已完成

两个完整原生命周期用例实际2 passed/12.30s、exit0，输入前后相等，known资源已交回。
样本内Registry1105次完整调用累计2.3318896s；YAML解码约0.084s，225 hit/27 miss，
无超限文本。观察包装开销未知，数据不外推867或原600；旧失败仍保留。
源分支便携记录为`.ai/tasks/TASK-0056/lifecycle-cost-diagnostic-013.md`。
下一步2名sub-agent并行准备和独立核对Schema原语分解微测，实际执行串行；
保持18项当前读取、JSON/Resource构造和原错误顺序，不共享mutable Registry。
尚未选择生产优化，原14项/5 mutation/85%/90%及后继55、发布进入条件保持。

## 2026-10-01 完整耗时诊断与定向成本测量

固定现有 source98b5db7 / B589 的私有完整诊断实际完成：collect867，
866 passed、1 既有 FIFO skip、639.96s，pytest/driver/launcher 实际 exit0。
输入与原断言前后相等，known-owned 资源已交回；未知历史后代仍未知。
耗时仍超过原600，不能替代原生V2；便携证据见源分支
`.ai/tasks/TASK-0056/integration-durations-diagnostic-012.md`，记录 `b024366`。
最长10.65s的真实管道超时测试及原10s要求保留，其他慢阶段分散于治理生命周期。
下一步只准备两个原生命周期用例的有包装成本诊断，私有100s；
2名sub-agent分工准备与独立审查，主agent记录和整合，实际重活串行。
观察包装的身份和开销变化须明示，不从两个用例推算完整867或600收益。
未选择singlewarm、Schema缓存或CParser；后续实现仍须明确重新准入。
action005/完整V2/独立Review/Gate及后继55/发布条件仍未完成，85%/90%保持。

## 2026-10-01 当前成本短测与诊断方向

两个串行私有短测均实际exit0、输入前后相等且known-owned资源已交回。
Schema原函数100次median1.6873ms；fixture20次真实warm全部命中，median88.7757ms，
单次source扫描median4.9492ms。类别重叠，不据此推算完整600或声明候选收益。
fixture晚期taskkill实际128不算cleanup成功；三个已知实体的实际终态支持释放。
证据见源分支`.ai/tasks/TASK-0056/current-cost-diagnostics-011.md`、记录`98f219b`。
暂不选择改变瞬态观测时机的singlewarm方案，也不实施Schema缓存。
下一步独立核对builtin pytest per-test耗时报告诊断的边界，定位实际长用例；
新增报告选项和私有诊断预算明确不替代原native600，旧失败、action005/V2/Gate缺项保留。
2名sub-agent分别负责私有运行准备与独立边界审查，主agent记录，重活串行。
后续修复仍须明确准入；原测试断言、14项检查/5项mutation及85%/90%保持。

## 2026-10-01 现有 3.14 原期限诊断失败

固定 source `98b5db7` / frozen `b5898529` 的现有 3.14.7/core 私有比较完成：
原 external188 为 187 passed/1 原 FIFO skip/145.87s、实际 exit0；原 integration
完整 collect867，但原 EXEC-012/600 秒在 600162ms 超时，没有完整 summary。
源码/原 AST/旧证据/refs/index/topology 前后相等，known-owned 终态核验已交回；
taskkill 实际255及未观察后代的限制如实保留。便携原件为源分支
`.ai/tasks/TASK-0056/runtime314-diagnostic-010.md`，记录提交 `3d2cbd1`。
不正式选择 3.14，不重复同候选600；action005/第五原生V2和Gate仍未完成。
下一步先短测真实夹具的当前读取、snapshot、copy与warm成本；任何一次完整
warm扫描候选必须明确重新准入、保留所有当前安全检查和旧用例，不声称与旧
瞬态故障观测时机严格等价。2名sub-agent并行独立边界审查与短测准备，执行串行。
Schema Registry共享尚无安全隔离证明，不实施；原期限/85%/90%及下游条件保持。

## 2026-10-01 直接入口前置结果与原期限失败

固定 source `98b5db7` / own HEAD `d0199e4` / frozen spec `b5898529…` 的独立
前置实际完成：新增窄测试12/12、完整fixture65/65（零跳过）、原external-review
187 passed/1 原POSIX FIFO跳过，分别1.82s/47.38s/142.17s，全部实际exit0。
原完整integration实际collect867，在原EXEC-012/600秒期限600183ms超时；
没有summary或原pytest退出码，不把91%部分进度记为完整通过。原件和known-owned
终态证明已保留，source/原AST/旧证据/refs/index/topology前后相等，资源已交回。
TASK-0056仍IMPLEMENTING；action005与第五完整V2未启动，313正式选择条件仍失败。
便携结果为源分支 `.ai/tasks/TASK-0056/direct-endpoint-prerequisites-009.md`，
记录提交 `3b54586`。不重跑相同失败候选、不调整预算或质量门禁。
接下来仅对已安装锁定314.7与当前已修复源做原external188私有诊断对照；当前
规格允许非formal诊断，正式314需新规格准入、设计Review及原完整前置，不能凭
旧未修复失败时长推断收益。两名sub-agent并行负责独立诊断与只读runtime/发布
准备，测试资源串行。TASK55/57、CI311和真实F匹配原件的进入条件均保持。

## 2026-10-01 直接入口规格准入已完成

TASK-0056 当前为 IMPLEMENTING。冻结规格 `b5898529…` 已完成真实独立设计
审查 REV-0007/r1（APPROVE，无 Findings）、按所有者既有充分授权的 spec
批准和原生 begin；准入账本提交为 `eceb23d`。保留全部旧规格、失败与消费回执。
本阶段并行启用 2 名 sub-agent：一名仅实施三处 fixture 工具函数及追加测试，
另一名准备未参与实现的独立验收；主 agent 统一提交。固定候选后，窄用例、完整
fixture、原 external-review 和完整 integration600 串行执行；实际全部前置通过
后才进入新的完整 V2。原选择器、期限、覆盖率、CI 和发布进入条件保持。
按所有者要求的限定报告搜索已结束，未找到目标匹配的 harness-model 原件；
实际找到的 dotfiles 历史报告不能替代正向 F。未启动 provider 或 F 导入。

## 2026-10-01 直接入口候选的下一步

40次Git只读配对与2次status实际exit0、raw一致、inputs未变，配对中位收益
13.4795ms只是候选证据。194项完整模块subset全部通过；cProfile的9 entry/
49 edge有inline>total异常，函数耗时归属全unknown。资源交回、原600失败保持。

Task56最新冻结 `b5898529` 仍REVIEW/V2。先完成独立设计审查和当前批准/begin，
再仅改两个现有安全测试路径的完整mingw64资格；固定候选在新实际PATH绑定下
需真实direct warm、原完整fixture/external-review及integration600通过，随后
fresh action005/完整V2/Review/finalize/代码批准/Gate。两名sub-agent并行设计
审查与测试准备，heavy验证与下游Task55/57串行；所有门槛、原assertions保持。
源记录 `endpoint-and-profile-diagnostics-008.md`；F保持本机已搜索范围未找到。

## 2026-10-01 完整被动诊断后的待办

当前候选完整 integration 私有诊断为 854 passed / 1 原 FIFO skip / 818.91 秒，
actual exit 0；855 个 ID 逐阶段完整，新 53 项全通过，源码/旧材料/refs 未变，
资源已交回。原 600 秒失败仍有效，Task56 未获 Gate、action005 未启动。
现需测量具体残余成本、选择最小修订并完整原生重验；静态 Git 入口方案和
构建选项不等于性能收益。Task55/57 与 F 进入条件保持；便携诊断为
`integration-passive-diagnostic-007.md`，不替代 `runtime-prerequisite-failure-006.md`。

## 2026-10-01 文件身份兼容修复后的实际待办

最新 TASK-0056 source `e3790a4` / frozen spec `2cefeedd` 已完成准入和最小
Windows 创建身份修复。19 项安全测试在 3.11/3.13/3.14 均 passed、零 skip；
3.13 原完整 external-review 为 187 passed / 1 既有 skip / 177.93 秒。
同候选原 integration600 仍超时 600188ms，pytest exit unknown、无 summary，
不能确认整套结果或最终 53 项；原件保留、旧证据未变、资源已交回。
action005/完整 V2 未启动，正式 runtime 选择条件未满足，Task56 仍 IMPLEMENTING。

下一步仅用完整选择器的被动阶段计时定位当前成本，不以诊断替代 600 秒门禁。
并行 2 名 sub-agent 分别负责独立诊断与未来 Task55 transport 安全准备/性能
分析，主 agent 保存失败和统一记录。Task56 完整验证及 Gate → Task55 接入
真实获 Gate 依赖、只新增 transport 并完成自身 Gate → Task57 exact-head CI
及已授权推送合并保持串行；不重复实施已在 Task56 的 metadata 修复。
匹配报告 F 在已搜索范围仍 unknown。详见便携 `runtime-prerequisite-failure-006.md`。

## 2026-09-30 夹具候选的原期限检查后待办

源码 `097f9af` 已固定，完整守卫短测实际有二十次 warm hit，但独立原
integration 仍在 600156ms 超时。pytest exit unknown、driver exit 1，无
terminal summary；原 skip 身份及最终 53 项全集完成均 unknown。源码/HEAD
与旧证据未变，资源已交回。该检查不是第五轮 V2；action005 尚未创建。

当前先核查全套真实 session owner 使用和剩余成本，并只准备隔离 3.13 比较；
不机械重试完整 V2。正式基线仍 3.11，原断言、选择器、期限、MINENV 与全部
门禁保持；任何新修订先按原生重新准入。TASK-0056 Review/finalize/批准/Gate
→ TASK-0055 实际依赖接入和完整 Gate → TASK-0057 required CI/已授权发布
仍是串行依赖。匹配的真实报告 F 仍未在已搜索范围找到。

## 2026-09-30 夹具修订准入后的实际待办

完整 profile 分析和独立原环境初始仓库短测已结束；短测退出 0、无超时，
原创建均值 0.36051 秒，完整独立复制加三目录当前指纹均值 0.05784 秒。
完整资格成本尚未测量，原 run004 的 integration 超时及 Gate REJECT 保留。

TASK-0056 初始测试仓库复用修订已原生重新分类、冻结为 REVIEW/V2，实际
独立 REV-0005/r1 APPROVE、spec approval/begin 完成；准入账本 `c999985`。
当前由一个 sub-agent 实施四个测试文件，另一个独立准备审查与验证，主 agent
整合。原 builder 失败残留、当前输入资格、独立物理 Git、全部原断言、真实
后续治理及原期限均保持。待完成有效专项、原 integration 600 秒检查、新
single-use action005、全部原生 V2、正式 Review/finalize/代码批准/Gate。
专项/微基准不能替代完整验证。TASK-0055 → TASK-0057 的串行进入条件仍然
有效；F 原件条件在已搜索范围内未满足，未执行 provider 或远端写入。

## 2026-09-30 第四轮 FAILED 后的实际待办

完整私有 integration profile 已完成 801 passed / 1 原 skip，851.34 秒、exit 0，
固定源码前后不变。当前分析函数成本，再选修复；该较长诊断不替代原生预算检查。

TASK-0056 run004 终态为 13 PASS / 1 FAIL；唯一 integration 在原 600 秒
期限超时、exit null、600140ms。原生 Gate 1、REJECT。完整 regression
2707 passed / 1 skip、857.61 秒，完整覆盖率 88.9574%、diff 97%，五项
mutation 全 killed；局部通过不补齐失败必需检查。失败记录及 action004
消费回执保留，源码 subject `38648440f5a862edd5a7dccfb55a60aae4f6757e` 不变。

当前先量出完整原 integration 的 setup/call/teardown 成本；两个 sub-agent
分别负责实际测量和只读 fixture 方案，主 agent 整理可追溯状态。不得根据
末尾进度判根因，不缓存 production freshness/Git/Schema 验证结论，不缩减
选择器或增加 Policy 预算。修复后需新批准回执及全部原生 V2/Gate。
TASK-0055 依赖接入与两项候选修正仍待 TASK-0056 实际 Gate；随后才进行
TASK-0057 固定候选 CI/已授权发布。F 仍缺本地搜索范围内匹配的真实原件。

## 2026-09-30 11:21Z 第四轮启动时待办记录

纯解码复用已完成准入、实现和分阶段提交；源码 subject `38648440f5a862edd5a7dccfb55a60aae4f6757e`。
70 项相关 unit 测试通过；完整原模块对照为 187 passed / 1 既有 FIFO skip，
187.05 秒，退出 0。safe YAML 调用从 3586 降到 87，契约和 Git 调用数保持。
这是单次非同时的诊断观察，不替代完整 V2 或预测原期限检查通过。

fresh action004 和独立最终 preflight 完成，默认全部原生 V2 已启动：
`run-20260930T112131331525Z`。启动时等待实际完整结果，再完成独立 Review、
finalize、代码批准/Gate；旧三轮 FAILED 和回执保留。TASK-0055 依赖接入及
候选修正仅只读准备，实际 TASK-0056 Gate 后才重新准入。F 原件条件仍未满足，
最终 TASK-0057 发布仍须固定候选 required CI 与独立远端核验。

## 2026-09-30 诊断后的实际待办

完整 Python 3.11 external-review 诊断结束为 187 passed / 1 既有 FIFO skip，
200.15 秒；重复 safe YAML 解析的累积时间为 36.92 秒，不证明原超时原因。
隔离 Python 3.14 完整比较实际失败，继续保留原 3.11 正式基线。
TASK-0056 纯解码复用已原生重新分类和冻结为 REVIEW/V2，独立设计审查中；
实现、模块对照、新 action004、完整 V2、正式 Review、finalize/批准/Gate 待完成。
每次当前读取及全部验证保持，旧三次失败与已消耗动作不复用。

所有者要求自行搜索报告。当前已搜索仓库、pilot artifacts、只读 ZCode 索引和
常用文档目录；找到另一仓库的真实 dotfiles 报告，未找到当前 F 的匹配原件。
不能将错目标报告或历史 UI 观察当作正向真实导入；F 条件仍未满足。
后续依赖仍是 TASK-0056 Gate → TASK-0055 重新准入/Gate → TASK-0057
required CI、已授权推送合并及独立远端核验。当前未执行远端写入。

## 2026-09-30 第三轮 V2 后的实际待办

TASK-0056 第三轮完整原生 V2 为 FAILED（12/14 通过）；regression 900 秒、
integration 600 秒均实际超时。完整 coverage 为 2676 passed / 1 原有 FIFO skip，
合并覆盖率 88.8278%、diff coverage 95%，unit 1838 passed，acceptance 9 passed。
质量阈值通过不注销两项超时；Gate REJECT，action003 已消费，旧记录完整保留。

当前待办为定位完整集合的耗时热点、基于事实修正或选择合适的隔离验证运行时，
然后新 preflight/单次动作、完整原生 V2、独立 Review、finalize、代码批准和 Gate。
启用 2 名 sub-agent，分别承担诊断与独立审计；资源密集测试串行，源树运行时冻结。
随后才重新准入 TASK-0055，再由 TASK-0057 完成累积候选 required CI 与已授权
推送合并。F 仍须匹配真实报告输入。便携依据：`verification-failure-003.md`。

## 2026-09-30 TASK-0056 修复后的实际待办

第二轮完整 V2 仍 FAILED（10/14 通过）：unit 1838 passed，三项完整集合
超时，diff coverage 缺少 XML，覆盖率 unknown。action002 已消费、Gate REJECT，
原始失败与账本不覆盖。长路径测试 I/O 和 Git 超时后的管道清理已诊断并在
修正规格下重新准入；初始 Git 超时原因仍 unknown。

新修复候选 `4f0288b4afb608412f984fa9078b7b0692fa0e6f` 已提交、同步。
共享夹具、验证命令、外部审查和 E2E 完整专项分别 34、81、187、28 项通过；
外部审查另有 1 项原有 POSIX FIFO skip。原业务断言和全部门禁保持现值。
当前待完成第三轮完整原生 V2、独立实现 Review、finalize、代码批准与 Gate。
两名 sub-agent 分别承担独立 verifier 与审查，主 agent 统一账本与交付。

串行依赖保持 TASK-0056 Gate → TASK-0055 依赖重新准入与完整 V2/Gate →
TASK-0057 累积候选审查、required CI 和已获授权的推送合并。真实导入 F 仍缺
匹配的原件与来源/目标绑定，不能以 synthetic 或错目标报告代替。
便携依据见源分支 `verification-failure-002.md`、`verification-retry-002.md`。
下方历史窗口保留，专项结果不注销原完整失败或提前形成发布通过结论。

## 2026-09-30 TASK-0056 固定候选的实际待办

设计复审、spec approval、begin 及实现提交已完成，当前候选为
`659f61cb4245112d75b119b103821bb06bae69ce`。78 项守卫专项、3 项 runner/默认
兼容用例和静态检查通过，独立预审没有剩余阻塞；这些不是完整 V2 或 Gate。
当前由独立 sub-agent 执行完整原生 V2，随后取得匹配的正式实现 Review、finalize、
code approval 及 Gate。TASK-0055 的依赖接入准备保持只读，尚未变更其范围或
原 FAILED 状态；实际 Gate 后才依原生流程重新准入。旧失败、批准和证据完整保留。

## 2026-09-30 持续 goal 的当前接续

所有者授权持续完成当前进入条件满足的待办、必要批准与推送合并。当前先推进
独立 TASK-0056 的显式仓库外 pytest 临时目录，原生 REVIEW/V2、规格已冻结，
设计复审进行中。原设计审查提出的裸仓库及执行期失败记录问题已进入修正规格；
不声称实现完成或解决既有超时。TASK-0055 原失败和证据保留，待 TASK-0056
实际 Gate 后显式修订依赖范围并完成完整 V2。随后 TASK-0057 绑定实际完整候选
和 required CI 发布合并。各阶段使用独立 sub-agent；不降低门禁或重复索取授权。

## 2026-09-30 E4.2 第五轮原生 V2 后的实际待办

E4.2 当前实现已在 `codex/e4-report-import`，`TASK-0055` 固定源码 subject 为
`eb4c49a4ff77ca07f210fceae707495c8dece8be`，验证准入 HEAD 为
`12b8e76e195e6f13772d3d692b80fca06422d31f`。第五轮完整原生 V2 已结束为
**FAILED**，14 项必需检查中 9 项通过，当前待办为完成失败定位与完整必需验证。

unit、regression、coverage XML、integration 分别实际超时 300406、900203、
1200328、600172 毫秒，四项 `exit_code` 均为 `null`。diff coverage 因缺少
coverage XML 退出 1；总覆盖率及差异覆盖率为 `unknown`。9 项 acceptance 用例
通过、5 项 targeted mutations 全部 killed，均不能代替完整 V2 的通过结论。
unit 部分日志的两项失败在限定诊断中 2 passed、12.64 秒、退出 0，未复现原失败；
原因仍为 `unknown`，不以限定诊断注销原失败或补作正式通过证据。

源码及任务账本保留在既有忽略目录 `.claude/worktrees/e4-verification-disk`。
原始文档检出没有 `TASK-0055` 账本；失败摘要提交后，便携读取入口为：

```text
git show codex/e4-report-import:.ai/tasks/TASK-0055/verification-failure-005.md
```

所有者的推送、合并授权已给出且仍有效，动作尚未执行。失败的 V2 阻止发布；后续
依次完成完整验证、匹配的独立实现审查与实际 Gate，不重复请求动作授权，也不提前
请求代码批准。不降低 Policy 预算、质量阈值或检查范围，原失败原因仍待定位。
E4.3/E4.4、provider、I1 其余生命周期、I2 更多目标、E5、I5 和阶段三/四
保持原条件；三份用户草稿、阶段 61 旧 index 及下方所有历史窗口保持原样。

证据可迁移性的进入条件因本次换检出已满足，本轮第五次运行的私有移交现已完成：
100 个显式选定文件经导出及独立 ZIP 校验，全部条目的大小与 SHA-256 匹配；
23 组 producer/Git 文本映射一致，原始 CRLF 与 Git LF 分别保存。通用工具未扩展，
旧日志缺失仍保持 unknown。详见便携记录
`git show codex/e4-report-import:.ai/tasks/TASK-0055/evidence-handoff-005.md`。
该移交不补作 V2 PASS；当前资源观察没有支持新一轮重试，原因定位与完整验证仍待完成。

## 2026-09-30 最新核定与实际待办

本轮实际 CLI 确认 `TASK-0048` 为 `MERGED`、`Missing: none`。同仓 Windows/Linux
接入、同 SHA 双 lane、main 采用、真实 guest 重启后业务、串行恢复、正式 V2 与
治理关闭均已完成；见[任务 02 执行目录](../superpowers/plans/2026-09-13-runner-infrastructure-execution.md)
和[发布关闭记录](../../.ai/tasks/TASK-0048/publication-closeout-001.md)。注册、CI 和
关闭不重新列为待办，历史运行回执不证明当前 guest 或 runner 在线。

E4.1 `TASK-0054` 已完成契约实现和本地治理验收，保存于
`codex/e4-external-review-contract@fd560d9`，实现 subject 为 `23793f7`。
本轮恢复该分支检出后实际 `validate` 通过，`status` 为 `APPROVED_FOR_MERGE`、
`Missing: external_merge`，批准为 `current`、证据为 `passed`，`gate` 为 PASS。
下方“E4 未启动”和“下一项为 E4.1”均为历史快照，不重复其准入与实现。

已提交 V1 审核包记录单元 1656 passed、全量回归与覆盖率重跑各 2294 passed、
总覆盖率 88.12%、可统计差异覆盖率 100%；本轮仅恢复检出并核对 CLI，没有重跑
这些检查。旧忽略目录中的原始日志是否可恢复尚未确认，不从本次 CLI 结论推导
完整原件已恢复或远端 CI 已通过。

当前主线为 E4.2 的独立治理规格与设计准入：本轮在 `codex/e4-report-import`
准备 `TASK-0055`，按[后续工作计划](../superpowers/plans/2026-09-23-e4-follow-up-work-plan.md)
固定加载、来源/目标核对与不可变记录边界；实际实现须满足该任务的 CLI 准入。
E4.1 推送、合并及新增外部动作另需授权。I1 其余生命周期、I2 更多目标、E5、I5
和阶段三/四保持原条件，不自动扩仓或进入下一阶段。
三份未跟踪用户草稿和阶段 61 的旧 index 保留；下方历史记录不改写或删除。

## 2026-09-27 dotfiles 修复线集成核定

`codex/ci-regressions-e4-preflight@3b835f1` 已通过[合并提交 `68ef2ec`](https://github.com/MaginaLW/ai-agent-dotfiles/commit/68ef2ecedca3e9071178dcab8b805cecdafbba53)
进入 dotfiles `main`。[`main@6c814f1` 的完整 Validate](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/36303730680)
四个 job 均成功；[外仓整合记录](https://github.com/MaginaLW/ai-agent-dotfiles/blob/6c814f18e981edfa1cad7185915ed7c177857bc0/status/active/live-safety-hardening.md#L4121-L4149)
保留了分支来源。下方 2026-09-23 的“分叉、待集成”与独立工作线是历史快照，不再重复集成。

## 2026-09-23 后续计划与统一接手入口

收尾已完成，[后续工作计划](../superpowers/plans/2026-09-23-e4-follow-up-work-plan.md)
明确 E4.1 准入、契约实现、验收及后继 E4.2 的依赖和 sub-agent 文件分工。
dotfiles 修复分支与新 main 已分叉，尚无该分支 PR；集成及主仓记录发布作为独立工作线，
不把旧候选 CI 外推为组合树验收。本次只更新计划和入口，E4 仍未启动。
下方窗口保留原时点，实际接手顺序以上述计划为准。

## 2026-09-23 CI 修复收尾，E4 启动前材料就绪

dotfiles 修复已推送到 `codex/ci-regressions-e4-preflight`，固定 `3b835f1` 的
[CI run 35873759132](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/35873759132)
四个 job 全部 success，42 套件全部通过，无失败或套件超时。
详细修补、失败历史及证据摘要见[收尾记录](e4-preflight-closeout-2026-09-23.md)。
已完成[启动前规格](../superpowers/specs/2026-09-23-zcode-report-import-preflight.md)；
下一阶段才固定基线、建立 E4.1 治理 task、分类/冻结/设计审查并按 CLI 准入 begin。
本轮 E4 未启动；主仓准备与关闭文档仅本地提交。下方各窗口作为历史保留。

## 2026-09-23 消费动作已选定，E4 停在启动前

所有者选择“将 ZCode 审查报告校验并导入既有 AI Flow 任务”。
[启动前规格](../superpowers/specs/2026-09-23-zcode-report-import-preflight.md)已将首批范围
收敛为 E4.1 独立外部报告契约及兼容检查；实际预检/写入留给后继 E4.2。
来源受审对象与目标任务分开绑定，原件摘要不认证身份，也不形成正式 Review 或 Gate。
本轮继续收尾 dotfiles 两项 CI 修复；E4 task 分类、冻结、设计审查和 begin 均未启动。
下方“尚无选定范围”是选择之前的核查快照，按本窗口及规格的实际验收状态推进。

## 2026-09-23 E4 进入前核查

E3 最小真实双产品案例及两仓推送已完成，发布范围见
[TASK-0053 回执](../../.ai/tasks/TASK-0053/publication-closeout-001.md)。本轮只读原件、
离线表示边界复现和 19 项现有 review 回归通过；未找到该案例被内核接口阻断的证据，
因此尚不选定 E4.1 的代码范围。详见[核查与后续入口](e4-gap-assessment-2026-09-23.md)。

dotfiles 固定 `51044a55` 的自然 CI run `35733693990` 已结束为 failure：42 套件中
40 passed、2 failed、0 suite timeout。两项实际失败分别是 root-claims-registry 内部
子进程 15 秒期限和 sync 的 released-policy dry-run 断言，底层原因仍待复现；它们不
构成 E4 缺口。新窗口不改写下方历史，也不把已完成 E3 再列为待造样本。

## 2026-09-22 dotfiles 归因修订已应用

dotfiles 两处 CI 规则冲突及既有更正记录中的提交归因已修正，本地提交为
`51044a55fc0dd8991e2ac25dad36fb1369a9027b`。目标文档检查和独立原始证据复核通过；
没有推送、重跑历史 CI 或修改生产行为。详见[实际应用记录](pilot-evidence-review-2026-09-22.md#2026-09-22-后续修订已应用)。
该具体 E1 修订及 E3 最小 guided 双产品文档归因案例已完成：Codex 修复后，真实独立
ZCode 会话逐项复核 F1/F2，原始证据、002 检查输入及受审版本均已核对。实际运行模型
为 `unknown`；不以同产品 sub-agent 或模型标签替代产品来源。无需为补样本制造新任务。
r3s 写入交接、I1 其他生命周期及后续条件阶段保留；E4 仍待具体接口缺口和明确选定范围。
以下历史窗口中的 E3 待办按本段更新，不重新打开已闭环案例。

## 2026-09-22 PR #43 后续工具交付

[PR #43](https://github.com/MaginaLW/harness-model/pull/43) 已于 2026-09-22T11:08:56Z 普通合入 main
（`48bf777`）。本轮完成 runner 本机路径与 PSDrive 绑定检查，
以及显式证据选材预检；缺失日志、缺失原件和实质字节冲突均保留可见诊断。

固定源码 `2393c67`：本地 **2238 passed**，含 Python 工具总覆盖 **88.86%**、
累计差异覆盖 **99%**，七组质量检查通过。TASK-0052 正式 V1、独立实施审查、
代码批准和本地 Gate 均通过；精确发布 head `45a220f` 的 required CI
为 Linux **2236 passed / 2 Windows-only skips**、核心覆盖 **88.03%**。
维护模式远端 Verify and Gate 跳过，本地正式验证单独保留，不混用覆盖范围。

核对远端父提交、树与源码祖先后已关闭 TASK-0052：MERGED、Missing: none。
账本共 **51 项：42 MERGED / 8 BLOCKED / 1 APPROVED_FOR_MERGE**。详细版本与动作依据见
[TASK-0052 关闭记录](../../.ai/tasks/TASK-0052/publication-closeout-001.md)。
本轮关闭记录仅本地追加，不递归发布；三个用户草稿及旧历史保留。

E3 自然双产品案例、外仓安全交接、I1 其他生命周期及 E4/E5/I2–I5/阶段三四继续按
既有条件推进；TASK-0028 保持选项 C，七项更早 BLOCKED 不自动恢复；新增 TASK-0051 为已被本任务接续的 CI 失败历史。
本次首次 Linux CI 的 3 个失败来自合成 Windows 测试的宿主盘查询，保留为 TASK-0051
失败记录；`7b940bf` 的 6 行 fixture 修复保持所有原断言，Task52 重新完成验证后发布。
以下 PR #42 及更早段落是对应历史窗口，不作为当前待重复实施的队列。

## 2026-09-22 PR #42 合并与本轮关闭

[PR #42](https://github.com/MaginaLW/harness-model/pull/42) 已于 08:06:49 UTC 合入 main
（`ae0e3d3`）。最终 head `1d76edd` 的 required CI 通过：Linux 2102 passed、
1 Windows-only skip、核心覆盖率 88.03%；本地含工具测试 2103 passed、总覆盖
88.58%、累计差异覆盖 96%。TASK-0050 正式 V1、独立审查和本地 Gate 均通过，
核对远端父提交、树及源码祖先后已关闭 MERGED、Missing: none。

账本现为 49 项：41 MERGED / 7 BLOCKED / 1 APPROVED_FOR_MERGE。工具与本轮 E1
诊断已发布；条件阶段、外仓交接和 TASK-0028 选项 C 保留。动作及关闭回执仅追加
本地，不递归再发布；详见 [TASK-0050 关闭记录](../../.ai/tasks/TASK-0050/publication-closeout-001.md)。
下文关于最终发布尚待执行的文字属于此前观察窗口，原文保留。


## 2026-09-22 最终源码与发布治理追加核定

证据导出边界补充修复后，固定源码 `5ecde71` 在干净检出重新通过 **2103 项测试**，
含新工具总覆盖率 **88.58%**、差异覆盖率 **96%**，七组质量检查全部通过。
工具实施维持 task-free；外部发布另由 [TASK-0050](../../.ai/tasks/TASK-0050/spec.md)
按 REVIEW / V1 前瞻执行。先前只保存授权回执的发布流程遗漏如实保留，不倒签。
PR #42 的旧候选 CI 不能覆盖最终源码；实际发布状态以后续真实回执为准。
详见[最终验证和流程纠正](local-tools-closeout-2026-09-22.md#最终源码补充核验与发布流程纠正)。
此前 2100 项、88.57% 是第一次源码检查的历史结果，以下原文保持。


## 2026-09-22 工具交付与 E1 复核追加核定

[PR #41](https://github.com/MaginaLW/harness-model/pull/41) 已于 06:27:32 UTC 通过
required CI 合入 main（`aeaed58`），TASK-0049 关闭记录已经发布。

旧表中两项顺序 3 的具体交付已完成实现和本地核验：
[证据移交](evidence-handoff.md)支持显式选择和原始字节校验；
[受控工具发现](controlled-tool-discovery.md)完成 Windows 空 PATH、缺项和错版诊断。
干净检出 2100 项测试通过，总覆盖率 88.57%、差异覆盖率 96%；完整范围和实际案例见
[实施与验证记录](local-tools-closeout-2026-09-22.md)。这不等于 I1 所有运维生命周期完成。

E1 本次固定窗口已产出[登记试点证据诊断](pilot-evidence-review-2026-09-22.md)：
更新过时状态，定位尚存的规则正文冲突，并提供目标接手者可执行的最小建议。
目标写入权未接管，实际回灌尚未完成；E3 双产品及独立会话链仍未补齐。
后续 E4/E5/I2–I5/阶段三四、TASK-0028 选项 C 和七项 BLOCKED 沿用既有条件。
以下表格中旧的“方案待选”“本次未复核”按本段更新，原历史观察保留。

## 2026-09-22 PR #40 合并后追加核定

[PR #40](https://github.com/MaginaLW/harness-model/pull/40) 已通过 required CI，
于 2026-09-22 06:11:51 UTC 合入 main；精确受检 head 为 `9ab3ca4`，普通 merge
提交为 `4399352`。以下历史表格中的旧待办 **1、2 均已完成**：TASK-0048 的
关闭记录与后续文档已经发布，`begin` 批准新鲜度缺陷已由 TASK-0049 修复并发布。
本次全量测试 1958 项通过，Linux 总覆盖率 88.03%、差异覆盖率 100%。

TASK-0049 在真实合并核验后已由 CLI 关闭为 `MERGED`、`Missing: none`；本地
账本共 **48 项：40 MERGED / 7 BLOCKED / 1 APPROVED_FOR_MERGE**。
TASK-0048 不重复关闭。发布范围、CI 和合并依据见
[TASK-0049 发布与关闭记录](../../.ai/tasks/TASK-0049/publication-closeout-001.md)。
本轮 TASK-0049 关闭账本及这些入口更新仅在本地保存，未纳入 PR #40 受检 head，
不把它们列为必须再发布的新待办，不递归生成发布与回执。

下一步仍仅按真实需要开展证据移交、E1 复核或自然 E3 双产品案例；E4 / I1–I5 /
E5 / 阶段三四的既有条件不变，TASK-0028 继续选项 C，七项 BLOCKED 保留历史处置。
以下正文、表格及接续顺序是 PR #40 之前的历史快照，原文保留；其中旧待办 1、2
和“未修复”“尚未发布”的说法以本段完成事实为准，不重新启动相同工作。

本记录整理后续候选、依赖与完成条件，不启动实施或发布。沿用既有 E1–E5、I1–I5
编号，不另建任务体系。优先级是建议顺序；有条件事项可以长期保持未启动。

## 当前基线与已完成项

- 核定时本地 head 为 `7eec053bbfca6d3fb33a09b2622b99bf1becfabd`，远端 main 为
  `7dad5c0be700c0ba72ed4f33f8856148e3265825`。
- [PR #39](https://github.com/MaginaLW/harness-model/pull/39) 已通过 required CI，
  以普通 merge commit 合入 main。发布候选是 `2dffdf0`；其后的 `7eec053` 是本地
  TASK-0048 关闭记录，尚未发布，不属于 PR #39 的受检 head。
- 本地账本共 **47 项：39 MERGED / 7 BLOCKED / 1 APPROVED_FOR_MERGE**。
  TASK-0048 已 `MERGED`、`Missing: none`；远端 main 尚保留其关闭前状态。
- TASK-0048 的真实 Windows/Linux 私有 CI、同源版本采用、Linux guest 重启及串行
  恢复验证、正式 V2、独立审查、Gate 和实际合并均已完成。注册、双 lane 验证和
  再次关闭该任务不列入待办。详见[实际发布与关闭记录](../../.ai/tasks/TASK-0048/publication-closeout-001.md)。
- E2 最小 guided 设计与示例已经随 PR #39 发布；I3 已有独立 Profile/Receipt 契约
  及纯校验器。二者均不等于通用跨产品执行能力已完成。

## 近期候选与完成条件

| 建议顺序 | 项目及当前状态 | 下一项可交付成果 | 依赖与完成条件 |
| --- | --- | --- | --- |
| 1 | 本地收尾记录发布：待安排 | 将 `7eec053` 的四个关闭文件及拟一并发布的后续文档组成明确候选 | 冻结实际 head/base、核对累计差异与范围，按项目要求取得对应发布授权、通过 required CI，并记录真实合并；不重复关闭 TASK-0048，也不复用旧候选的批准和 CI 覆盖新范围 |
| 2 | `begin` 与 spec approval 新鲜度不一致：已复现、未修复 | 独立治理 task 中统一实现与权威新鲜度规则，补充状态转换回归验证 | `status` 的 spec 判断使用 base/policy/spec，而 `begin` 额外比较 subject；READY 状态又可能拒绝补 spec 批准。修复须保留其他批准的版本绑定及质量门，不能以放宽控制解决 |
| 3 | 证据可迁移性：已有保存边界，通用移交方案待选 | 明确原件、Git 文本、摘要、运行环境及重现步骤的移交清单 | 仅在需要换环境复核或交付时实施；验证原始字节与摘要，保留 CRLF 原件和 Git LF 文本的区别，不改旧摘要，不提交私密路径或凭据 |
| 3 | 受控环境依赖发现：本次已解决，复用方案待选 | 纳入 I1 的可信工具定位、版本检查与缺项诊断 | 本次最小 PATH 下的 PowerShell 发现问题已有成功处理，不能报作当前阻塞；如泛化，须验证干净受控环境及缺项失败行为，不扩大不可信 PATH |
| 按需 | E1：登记试点当前证据复核 | 对实际问题或明确请求形成版本化诊断及必要反馈 | 先重读目标当前 head、CI、Policy 和证据；仅覆盖选定窗口。无问题且无请求直接 no-op，不因版本变化或普通完成递归生成回执 |
| 下一项自然案例 | E3：真实双产品 Review–Fix–Verify 闭环尚未完成 | 一项自然、低风险案例的完整交接与逐项复核材料 | 依赖已完成 E2 及案例自身安全收尾；记录两种产品、独立会话、受审版本、问题来源、修复版本和独立验证结果。同产品 sub-agent 不算双产品；零 Findings 不能单独证明完整 Fix–Verify |

`begin` 缺陷的原始拒绝与本次处理顺序见
[绑定差异记录](../../.ai/tasks/TASK-0048/closeout-begin-binding-001.json)及
[关闭摘要](../../.ai/tasks/TASK-0048/closeout-summary-001.md)。TASK-0048 使用同一固定
subject 的正确顺序完成，并没有修复该源码问题。未来修改 `src/aiflow/**` 必须独立
走 AI Flow；普通文档整理仍适用维护模式。

本次没有重新检查两个外仓的最新运行状态。旧复盘中的目标 Policy 差异只能作为
下一次核对线索，不能直接宣布为当前缺陷。已补齐的历史日志或已成功的双 lane 窗口
也不能再次写成“缺失”；新窗口与旧业务批次各自保留证据边界。触发约定见
[反馈闭环](feedback-loop.md)。不为凑 E3 样本制造业务修改或启动付费调用。

## 条件性实施与扩展

| 既有项目 | 已有基础 / 尚缺部分 | 启动条件与完成边界 |
| --- | --- | --- |
| I1：运维复用 | 只读工具与本次范围的实际生命周期验证已有；通用安装、更新、冲突检测、依赖发现、日志保留和精确回退仍可收敛 | 选择真实运维需要后分批实施；再次运行不得重复注册、覆盖凭据或扩大 ACL，并验证选定生命周期。已有恢复验证不为新增证据重复执行 |
| I2：更多目标接入 | 同一私有仓库的 Windows/Linux 本阶段已完成；更多仓库或平台未启动 | 每次选择一个有实际需求的可信目标，独立验证权限、平台、安全、检查等价性、完整 CI 与回退；不自动扩仓 |
| I3 / I4：回执与跨产品接续 | v1 契约、纯校验器和本次独立修复/复核事实已有；可信来源认证、产物正文验证及通用正式服务映射并未因此完成 | 先由 E3 找出真实接口缺口，再与 E4 共用最小适配。现有 receipt 校验器不执行 runner、不联网、不验证日志正文或身份、不修改正式 task、不计算 Gate，不另造第二套状态机 |
| E4：内核桥接 | 未启动 | E2 + E3 证明实际接口缺口，且明确选定范围后，串行推进“契约与兼容 → guided 导入导出 → fix/verification/Gate 关联 → 中断恢复与兼容验证”。治理变更独立建 task，与安全文档分开 |
| E5：外部引擎、provider 与可信执行扩展 | 未启动 | 完整外仓引擎采用、真实 provider、可信执行分别判断需求、授权与准入；runner 采用不能代替这些条件 |
| I5 / 阶段三 | 未启动；现有试点不等于入口齐备 | 补足冻结的样本充分性、分层、隐私与偏差规则；真实 V3 高风险用例及沙箱、损失和回退边界；统一版本化成本、返工、审查缺陷、工具失败度量。actor 标签不是可信身份或模型身份证明 |
| 阶段四：独立编排器 | 未启动 | 阶段一至三接口稳定，并有可度量的多仓、多平台、多模型协作成本，以及真实暂停/恢复和集中审批需求后再决定，不由计划存在推导实施必要性 |

详细接口和入口继续以原文件为准：
[E2–E4 设计](../superpowers/specs/2026-09-13-cross-agent-review-fix-loop.md)、
[runner receipt 边界](runner-receipts.md)、
[基础设施执行目录](../superpowers/plans/2026-09-13-runner-infrastructure-execution.md)、
[阶段三输入](../implementation/phase-03-entry-inputs.md)、
[总实施目录](../superpowers/plans/2026-08-01-ai-code-collaboration-mvp-implementation-directory.md)。

## 保留边界与历史挂起

- **TASK-0028**：名义状态仍是 `APPROVED_FOR_MERGE`，当前 readiness 为
  `reverification_required`、`Missing: reverification`；继续既有选项 C。
  不因本次整理自动重验、改状态或关闭。
- **七项 BLOCKED**：TASK-0008、0029、0032、0033、0040、0041、0043 属于既有
  替代、拒绝或保留处置，不当作七项待开发功能。治理提案 B0–B2 已停止、B3 已解决、
  B4 延后；不自动复活。见[历史任务收敛目录](../superpowers/plans/2026-09-03-approval-overhead-and-open-task-consolidation-directory.md)。
- **可信外部执行**：普通 push/merge 强制授权、可信身份根、服务端授权、原子消费、
  凭据、审计及恢复仍是条件性架构方向。本地 approval 文件不是可信执行授权。
  CLI `close` 当前只核验 commit 对象存在，不能代替真实 PR/远端祖先核验；PR #39
  已独立完成这些核验，故这不是本次关闭缺项。不重启被拒绝的 TASK-0043 方案。
- **效果度量**：尚无足以宣称成本、耗时或缺陷改善的可比基线、人工分钟、因果归属
  及成熟缺陷观察窗口。后续在自然任务中按选定的版本化、隐私约定采集真实事实，
  不补造评分，也不为统计制造工作。
- 历史证据、失败记录与三个用户原稿保持原样；本清单不授权分支清理、删除或外仓修改。

## 建议接续顺序与并发关系

1. 先处理本地收尾记录的候选发布安排；若开始工程实施，优先选择已复现的 `begin`
   一致性缺陷。二者各自冻结范围与验证对象，发布与合并按依赖串行。
2. 自然案例出现时推进 E1 的必要复核和 E3；无需等待扩仓。不同目标的只读核对可并行，
   但同一业务目录只保留一个活跃写入者。具体实施计划再确定 sub-agent 数量与归属。
3. E3 形成真实缺口后才决定 E4 / I3 / I4 适配；I1 复用及 I2 扩展按实际需要另选。
4. I5、E5、阶段三/四继续保留条件，未满足不启动。

本次记录阶段采用主 agent 核对事实、1 名 sub-agent 并行检查遗漏；随后由主 agent
串行编辑、验证与提交。未创建新实施 task，未改变既有批准、Policy、质量阈值或运行服务。
