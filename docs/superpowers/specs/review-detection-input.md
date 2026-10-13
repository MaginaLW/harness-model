# 真实观察来源声明的离线输入合同

状态：`review-detection-input-v0.1`。本合同承接[已采用的有限研究范围](review-detection-admission.md)与[准备流程](../../operations/review-detection-preparation.md)，定义来源声明的机械校验、原值回读和缺口汇总。它允许描述真实来源，但不认证原件、登记合格单位、启动观察或计算真实评分；[数学工具](review-detection-offline.md)仍仅接受 synthetic 计数。

## 1. 接口与固定边界

纯函数为 `build_detection_input(document)`，CLI 为 `python -B tools/analysis/review_detection_input.py`，从标准输入读取 UTF-8 JSON、向标准输出返回 JSON。纯函数无 I/O 且不修改输入；CLI 只读 stdin 和自身脚本字节，不运行 Git、子进程、网络、其他资源读取或文件写入。它不抓取引用、生成候选、建立新存储或保存原输入、capture、身份、会话及结果副本。

这个独立入口不改变现有 Git 白名单、PR capture/v2 块、AI Flow Schema、权限或账本。正式 Git 回读仍使用 `review_feedback.py` 的 repository/`--task` 接口；PR capture 仍交给 `pr_feedback.py`。不得把本声明包伪装成原生 Git snapshot、既有 PR capture 或 synthetic 计数。

已采用的 30 日窗口、95% 覆盖和 20 个百分点总宽保持不变。本工具只检查供给时间之间的关系；不读取当前时钟，不填 `T0/T1`，不启动或延长窗口，不触发审核、补样本或付费调用。填写完整、时间顺序一致或来源形状合法均不产生真实准入。

## 2. 最小输入

所有对象恰好包含下述字段；数组可空。缺字段、额外字段、错误类型、未知枚举值、重复 JSON key、非有限常量和不可解析的时间均为输入错误。正常的事实缺失显式使用 `null`，判断缺失使用枚举 `unknown`，不得补默认事实。

| 顶层字段 | 取值 |
|---|---|
| `schema_version` | 字符串 `"1.0"`。 |
| `repository` | `owner/repository`，两段各匹配 `[A-Za-z0-9_.-]+` 且不能是 `.` 或 `..`；仅定位供给声明，不证明仓库身份或公开可见性。 |
| `admission_package` | 字符串 `"review-detection-admission-v0.1"`。 |
| `window` | 恰好 `{ "t0": <UTC 时间或 null>, "t1": <UTC 时间或 null> }`；两项都给出时检查差值恰好 30 日，单项缺失仍保留。 |
| `candidates` | 候选声明对象数组；空数组表示没有供给候选，不证明来源没有候选。 |

UTC 时间使用 RFC 3339 的 `YYYY-MM-DDTHH:MM:SS[.ffffff]Z` 或同形式 `+00:00`；小数可为 1–6 位。拒绝无时区、非 UTC、非法日期及闰秒。比较按实际 UTC 瞬时进行，不比较时间字符串。标识符匹配 `[A-Za-z0-9][A-Za-z0-9._-]*`；候选 ID 在包内唯一，机会 ID 在所属候选内唯一，重复 ID 是输入错误。SHA 为 40 位小写十六进制字符串。

每个候选恰好包含：

| 字段 | 取值与含义 |
|---|---|
| `candidate_id` | 候选声明标识符。 |
| `related_group` | 相关组标识符或 `null`；跨 TASK/PR 的关联仍须原件判断，字符串相同不证明关联完整。 |
| `candidate_commit` | 候选 SHA 或 `null`；不得补当前 HEAD。 |
| `declared_at` | 机会与选择声明固定时间，UTC 或 `null`。 |
| `entered_at` | 被测首次审核入口时间，UTC 或 `null`。 |
| `report_fixed_at` | 被测完整原报告固定时间，UTC 或 `null`。 |
| `closed_at` | 本观察结局关闭时间，UTC 或 `null`；不是脚本执行时间。 |
| `refs` | 恰好含 `candidate`、`declaration`、`related_group`、`conditions`、`roles`、`budget`、`report`、`closure`；每项为第 3 节的引用或 `null`。 |
| `opportunities` | 该候选完整预声明机会列表的供给投影，元素如下；数组是否完整、是否事前固定仍未知。 |

每个机会恰好包含：

| 字段 | 取值与含义 |
|---|---|
| `opportunity_id` | 此候选内的机会声明标识符。 |
| `contract_ref`、`object_ref`、`instance_ref` | 分别为先前适用契约、受检对象与唯一实例的引用或 `null`；实例引用帮助消歧，不新增排序优先级。 |
| `defect_class` | 字符串 `"direct_contradiction"`；不由这个标签确认实际存在直接矛盾。 |
| `truth` | `positive`、`negative`、`disputed` 或 `unknown`，只回读供给裁定。 |
| `adjudication_ref` | 该机会的原裁定及理由引用或 `null`。 |
| `adjudication_fixed_at` | 原裁定固定时间，UTC 或 `null`。 |
| `match` | `detected`、`not_detected` 或 `unknown`，只回读供给匹配结论。 |
| `matching_ref` | 该机会的语义匹配依据引用或 `null`。 |
| `matched_at` | 匹配固定时间，UTC 或 `null`。 |

职责、输入、预算、适用关系、完整报告范围、争议及失败原值均由原件引用承载，不复制正文，也不扩成 `independent=true`、`complete=true` 或 `ready=true` 自证字段。取消、timeout、partial、工具/权限失败及未关闭原记录应继续留在原位置；本包用引用和未知表示待核，不替换原记录或把它们转换成零。

## 3. 引用形状和来源限制

引用为以下 tagged union 或 `null`，不允许其他字段：

- Git：`{ "kind": "git", "source_commit": <SHA>, "path": <仓内相对路径>, "git_blob": <SHA>, "locator": <非空字符串> }`。
- PR：`{ "kind": "pr", "url": <本 repository 的 GitHub PR URL，可带锚点>, "locator": <非空字符串> }`。

Git 复用[既有四字段定位](readonly-confidence-data-contract.md#1-固定输入与引用)。路径采用 `/`，不能绝对定位、包含反斜杠、空段、`.`、`..` 或控制字符。PR URL 恰好为 `https://github.com/{repository}/pull/{正整数}`，可附 `#[A-Za-z0-9_-]+`，不得带查询参数、凭据或其他域/仓库。无锚点 URL 加 locator 只能描述所供给位置；不由此补成原报告公开锚点。原件位置不存在或不能定位时用 `null`。

本工具只核形状和包内相等关系，不解析 locator、不读取目标，也不验证 Git mode、blob 对应、提交可达性、PR 原子性、追加历史或公开可见性。引用中 SHA 与输入 bytes hash 不能认证原件、事前冻结、职责独立性、信息暴露或完整历史。当前 Git 自动投影白名单未因此扩大；`docs/**` 引用即使合法，也没有被该白名单读取或认证。

## 4. 机械检查与保守选择

输入形状错误拒绝整个包，不输出部分报告；可解析的事实冲突、缺失或顺序错误则返回报告，保留供给原值和定位明确的缺口。不得为了输出一个选择结果而过滤掉不利记录。

固定机械检查包括：

1. 两个窗口端点是否齐全、是否恰好相隔 30 日；入口是否在 `[t0,t1)`、结局是否在 `t1` 前关闭。端点或时间未知时检查为 `unknown`；已知范围外值为 `conflict`，不自动调整日期。
2. 已知时间应满足 `declared_at < entered_at <= report_fixed_at <= adjudication_fixed_at <= matched_at <= closed_at`；任一相邻端点已知且颠倒则报冲突，未给出的端点保留未知。通过只说明供给时间一致，不证明真实时序、未提示或独立裁定。
3. `candidate_commit` 与 Git `refs.candidate.source_commit`、Git `object_ref.source_commit` 是否一致；其他用途的引用使用其真实版本，不要求旧契约 SHA 等于候选。缺引用或版本为未知，已知不等为冲突。PR 引用无法据 URL/locator 认证候选绑定。
4. 所需原件引用是否提供；正/负裁定是否有裁定引用；已声明匹配是否有匹配引用。`truth` 不是 `positive` 而 `match` 已声明检出/未检出时保留双方值并报冲突，不将负真值转换成未检出。

相关组选择只回读本包已供给的先后与列表关系，不认证完整机会集、完整相关组、组间独立或共同检出概率：

- 任一候选缺 `related_group`，其未知关联可能影响其他组，因此本包组选择均保留 `unknown`；不得把缺组项当独立的新组。
- 对每个已声明组，先判断入口窗口。窗口不完整、组内任何候选入口时间未知，或窗口内候选声明时间未知/不早于入口时，组选择为 `unknown`。明确窗口外候选保留原值与范围标记，不据其结局换入窗口内候选。
- 对窗口内候选分别按 `declared_at` 与 `entered_at` 排序；任一顺序存在并列，或两种顺序不一致，则保留组选择 `unknown`。两者顺序一致且唯一时，仅取第一候选。后来裁负、未知、报告缺失或关闭失败都不转选后项。
- 第一候选的所有机会均有契约/对象/实例引用时，按 `(contract_ref, object_ref, defect_class)` 取第一项。引用比较键为 Git 的 `(kind, source_commit, path, git_blob, locator)` 或 PR 的 `(kind, url, locator)`，按字段字符串的 Unicode 码点顺序比较；它只定义供给引用的确定性排序，不能证明这是原声明的完整排序。
- 同排序键有多项、实例引用重复、缺任何排序/实例引用或机会数组为空时，机会选择为 `unknown`。不能用输入数组位置、机会 ID、实例字符串或真值作为额外排序项。保留所有机会及待核消歧依据。
- 选择确定时只输出 `selected_reported` 的候选/机会 ID。该项真值为负、争议或未知也保持选择，不替换正例；它不是合格统计单位。

候选是自然工作、改动仅含普通 `docs/**` 且含契约内容、契约先前适用、原件完整、预算实际覆盖、裁定者不是作者或被测审核者、允许输入与提示暴露、真值判据、语义匹配及跨组条件均不能由本声明包证明。每个候选都保留这些来源核对待办，即使上述机械检查全部通过。

## 5. 输出与错误

输出包含 `schema_version="1.0"`、`measurement="review_detection_input_readback"`、原 `repository`、`admission_package`、`window`、`reported_candidates`、`group_selections`、`condition_checks`、`next_source_checks` 和 `coverage`。`reported_candidates` 保留已校验形状的候选/机会及引用原值；不覆盖冲突的时间、真值或匹配。`coverage` 恰好列 `reported_candidates`、`reported_groups`、`reported_opportunities` 三个供给记录数；组数只计不同的非空组 ID。它们不命名为样本量，不输出 `n/k`、真实比例、区间、精度通过或模型分数。

`group_selections` 每项恰好为 `{ "related_group": <ID 或 null>, "status": "selected_reported" | "unknown" | "no_in_window_candidate", "candidate_id": <ID 或 null>, "opportunity_id": <ID 或 null> }`。选择未知时 ID 均为 null；明确无窗口内候选才使用 `no_in_window_candidate`。`condition_checks` 每项恰好为 `{ "code": <稳定代码>, "status": "consistent_reported" | "conflict" | "unknown", "locator": <输入字段路径> }`，代码为 `WINDOW_DURATION`、`ENTRY_WINDOW`、`CLOSURE_WINDOW`、`EVENT_ORDER`、`CANDIDATE_BINDING`、`REQUIRED_REFERENCE`、`TRUTH_MATCH`、`GROUP_SELECTION` 或 `OPPORTUNITY_SELECTION`。检查仅解释第 4 节的机械关系，不把机械通过命名为准入通过。

`next_source_checks` 每项恰好为 `{ "code": <稳定代码>, "locator": <输入字段路径> }`。每个候选保留 `VERIFY_ORIGINALS`、`VERIFY_NATURAL_DOCS_SCOPE`、`VERIFY_PRIOR_DECLARATION`、`VERIFY_ROLES_AND_INPUTS`、`VERIFY_TRUTH_AND_MATCH`、`VERIFY_BUDGET_AND_CLOSURE`、`VERIFY_GROUP_CONDITIONS`；空候选包保留 `LOCATE_NATURAL_CANDIDATE`。这些是待核事项，不执行或授权核对、创建候选或追加审核。

所有输入固定输出 `source_assurance="supplied_observation_declarations"`、`source_authenticity="unknown"`、`history_completeness="unknown"`、`observation_admission="unknown"`、`statistical_independence="unknown"`、`method_status="design_pending"`、`probability_status="unestimated"`、`model_score_update_status="not_implemented"`、`actual_model_identity="unknown"`、`execution_allowed=false`、`permission_effect="none"`、`ledger_effect="none"`。完整声明也不改变这些值，不返回 `ready`。

CLI 附 `input_sha256` 与 `executed_tool_sha256`，分别绑定实际 stdin bytes 与脚本 bytes，仅供复算；不认证任何供给来源。复用已有 strict JSON 的重复 key/非有限常量拒绝逻辑，不新增通用框架。正常报告（含未知或事实冲突）退出 0；读取、解析或形状校验失败退出 2，stderr 使用不回显输入的固定安全错误，stdout 为空。

## 6. 必需验收

- 空声明、未知窗口、单边窗口、缺组与缺来源均能回读；不存在隐式 `T0`、默认预算、合格单位或 n/k。
- UTC 等价写法、30 日窗口、端点 `[t0,t1)`、严格 `closed_at<t1` 和时间倒序分别验证；事实冲突保留，非法时间拒绝。
- 组内两种时间排序冲突/并列/缺失、未知组、缺机会和排序键冲突均不能偷偷选择后项；候选数组和机会数组置换不改变可确定的选择。
- 第一候选/机会为负、争议、未知或不利结局时保留原选择；后项即使正真值并已检出也不能替补。重复实例或同排序键不能通过换 ID 消歧。
- 候选 SHA 冲突、真值与匹配冲突、缺原件、可变 PR 位置均保留限制；全字段完整且机械一致的包仍输出固定未知准入和未估计状态。
- 严格字段/枚举/类型、重复 ID、重复 JSON key、非有限常量、非法 UTF-8、越域/带凭据 PR URL 和路径逃逸均拒绝；错误不泄露输入。
- 纯函数不修改输入；CLI 不联网、不读 Git/任意引用资源、不写文件、不创建子进程、不启动观察。synthetic 数学接口的现有接受域和结果保持不变。

来源核定和真实研究准入仍按[采用范围第 6 节](review-detection-admission.md#6-一项采用决定与后续准入)执行。这里交付的是可复用的离线缺口检查；所需机械事实由 Agent 补齐，不重复询问已采用的用途、精度、窗口规则或风险包。真实来源、范围或风险变化才集中处理相应决定。
