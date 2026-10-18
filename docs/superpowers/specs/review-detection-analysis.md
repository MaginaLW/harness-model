# 记录级条件分析的离线实现合同

状态：`review-detection-analysis-v0.1`。本合同落实项目所有者要求的真实输入分析接口准备、离线实现及合成验证；当前只接受 synthetic 记录，不接真实数据、不启动真实评分、宿主连接或观察窗口。真实输入接口的启用、来源与方法准入仍另核，不能把真实声明改标签后送入本入口。

## 1. 范围与复用

新增纯函数 `build_detection_analysis(document)` 及 stdin/stdout CLI `python -B tools/analysis/review_detection_analysis.py`。复用[声明检查](review-detection-input.md)的 `build_detection_input()` 校验及预选，复用[数学模块](review-detection-offline.md)的 `build_detection()`；CLI 沿用 `benchmark_reference` 的严格 JSON hooks，不调用其评分。无需新增第三方依赖，不重写选择或区间算法，不改既有接口、AI Flow Schema、Policy、route、Gate 或授权。

本层补记录到条件计数的转换、选中路径的必要条件、整批不足回退及数学调用。纯函数不修改输入，无文件、Git、进程、网络、时钟或账本效果。CLI 只读 stdin、本脚本及三项依赖模块的源码字节；不解析引用、不读取原件、不采集或保存输入／结果。

## 2. 固定输入

顶层对象恰好含以下字段，所有对象按既有合同或本表严格校验；重复 JSON key、NaN／Infinity、未知字段或枚举均拒绝。

| 字段 | 要求 |
|---|---|
| `schema_version` | 字符串 `"1.0"`。 |
| `record_origin` | 字符串 `"synthetic"`；其他值拒绝，不自动改标。标签是供给声明，程序不能证明材料确为合成。 |
| `declarations` | 恰好使用既有声明输入 v1 结构，包括原 `repository`、`admission_package`、`window` 和 `candidates`，不接收该工具的输出报告或 Git／PR capture。 |
| `scenario_assumptions` | 恰好含下列七项，每项只能为 `assumed`、`unknown` 或 `violated`。它们是合成情景假设，不是认证、批准或事实字段。 |

七项假设为 `selection_fixed_before_outcomes`、`history_and_grouping_complete`、`independent_truth_and_semantic_matching`、`review_conditions_comparable`、`group_outcomes_independent`、`reports_and_budget_endpoints_complete`、`single_analysis_after_fixed_window`。含义分别为事前预选、完整来源与关联、独立真值及语义匹配、共同检出条件、组间独立、完整报告／原预算端点、固定窗口后一次分析。任一 `unknown` 或 `violated` 阻断整批条件计算，分别产生 `status=unknown` 或 `conflict` 的 `SCENARIO_ASSUMPTION`；不接收 `verified`、`independent=true` 或真实准入开关。

合成时间只描述情景，不读取当前时钟、不实际设置 `T0/T1`。同名组、不同 Agent、引用存在或条件引用相等均不认证这些假设。未来真实分析须另解决来源、自然范围、适用关系、实际输入、职责、提示、预算和方法条件，不能以这些枚举代替原件。

## 3. 选择与整批回退

完整保留声明回读，包括未选项、窗口外项、全部机械冲突及 `next_source_checks`。仅使用其 `group_selections`：

1. 窗口必须已供给且恰好 30 日。任一组选择为 `unknown` 时阻断整批；`no_in_window_candidate` 记录为窗口外，不贡献单位。首候选／首机会一经预选，不因负、争议、未知、缺报告或未关闭换入后项。
2. 对选中候选，要求入口／关闭窗口、候选绑定、全部候选引用及 `declared_at < entered_at <= report_fixed_at` 的检查均为 `consistent_reported`。旧回读将每项 `matched_at -> closed_at` 的 `EVENT_ORDER` 共用候选 `closed_at` 定位，本层不将这些共享定位检查整体视为候选条件，而按选中机会原值核对下述终端链。选中机会适用的引用、对象绑定与时序检查也须为 `consistent_reported`，未知不能当通过；负项仅豁免下述匹配未知，包含 `TRUTH_MATCH` 在内的所有已知冲突均阻断。引用存在只说明合成字段齐全，不认证语义。
3. 选中 `positive` 必须有已决 `detected` 或 `not_detected`、裁定／匹配引用及完整时间，满足 `report_fixed_at <= adjudication_fixed_at <= matched_at <= closed_at`。分别贡献假设正机会一项，只有 `detected` 贡献假设检出一项。
4. 选中 `negative` 保留原项，不贡献正分母且不换后项。它可以合法保持 `match=unknown`、`matching_ref=null`、`matched_at=null`；不将这些匹配缺失当阻断。但必须有裁定引用及完整 `report_fixed_at <= adjudication_fixed_at <= closed_at`，额外已供给的匹配时序冲突也保留并阻断。
5. 选中 `unknown`／`disputed`、正项匹配未知或任何上述必要条件缺失／冲突时，整批数学结果为 null。不得丢掉问题单位后对其余完整项计算；不假设缺失随机，不创造有效 N。
6. 不要求全包机械检查全部通过：不影响预选的未选候选、未选机会或明确窗口外项的缺口留在原回读中，不单独阻断条件计算。它们若已影响原工具的预选，则仍按选择未知阻断；负项仅豁免匹配未知，不豁免报告、裁定和关闭条件。
7. 仅在无阻断时，将假设正项和假设检出数传给原 synthetic 数学接口。`n>104` 返回整批阻断，不截断、拆批或替换；`n=0` 复用 `no_positive_units` 和空比例／区间。模型评分、审核安排和执行权限始终不变。

## 4. 输出与错误

输出固定 `schema_version="1.0"`、`measurement="synthetic_review_detection_analysis"`、`record_origin="synthetic"`、`source_assurance="synthetic_supplied_declarations"`，并含：

- `declaration_readback`：原声明工具的完整报告，原检查定位相对于 `declarations` 包；不改写其 unknown 或原值。
- `scenario_assumptions`：输入假设的独立副本。
- `selected_units`：每个预选项的 `related_group`、`candidate_id`、`opportunity_id` 及 `reported_outcome`。后者为 `positive_detected`、`positive_not_detected`、`negative` 或 `unresolved`，只表示供给分类，不证明合格。
- `reported_selection_counts`：上述四类计数及 `outside_window_groups`、`unresolved_groups`；只是预选声明诊断，不是统计分母。窗口外和选择未知的组仍可在原回读定位。
- `blockers`：稳定 `code`、`status=unknown|conflict` 和相对整个 envelope 的 `locator`，保留所有受影响缺口；原机械代码复用，另用 `SCENARIO_ASSUMPTION`、`SELECTION_UNRESOLVED`、`OUTCOME_UNRESOLVED`、`REQUIRED_TIME`、`VERIFIED_DOMAIN_EXCEEDED`。
- `analysis_status`：无阻断时为 `conditional_synthetic`，否则为 `blocked`。
- `synthetic_calculation`：无阻断时为原数学函数完整返回报告，否则为 null；不额外给真实 n/k、比例、模型分数或准入结论。

所有输出始终固定 `source_authenticity="unknown"`、`history_completeness="unknown"`、`observation_admission="unknown"`、`statistical_independence="unknown"`、`actual_model_identity="unknown"`、`method_status="design_pending"`、`probability_status="unestimated"`、`model_score_update_status="not_implemented"`、`execution_allowed=false`、`permission_effect="none"`、`ledger_effect="none"`。`conditional_synthetic` 只指本合成情景可计算，不表示真实分析已就绪。

CLI 成功输出报告退出 0，包括合法的 blocked 报告；读取／解析／形状错误退出 2、stdout 为空，stderr 固定 `review-detection-analysis: supplied synthetic records are invalid`，不回显输入、路径或底层异常。JSON 用 ASCII 转义保持文字原值。CLI 追加原始 stdin 字节 `input_sha256`、本脚本 `executed_tool_sha256` 和按文件名列出的三依赖 `dependency_sha256`（`benchmark_reference.py`、`review_detection_input.py`、`review_detection.py`），只支持代码与输入复算，不认证来源。

## 5. 独立验收

验证多组正项计数与既有数学结果一致、零正项、104／105 边界、首负／未知不替补、共享组不重复计、数组置换与等价 UTC、选择并列、排序引用缺失、影响主声明的未知整批阻断。专门验证负项无匹配合法、裁定在关闭后则阻断；无关未选／窗口外缺口保留但不冒充受影响阻断。

验证七项假设的未知／违反、畸形／真实来源输入拒绝、重复字段、坏编码、纯函数无副作用和无别名、真实 CLI 的字节 hash／依赖 hash、固定安全错误、Unicode 与受限输出编码。正常与 blocked CLI 都覆盖实际入口；fixture 只用虚构仓库、时间和引用，不读真实 Git／PR／宿主。

实现仅位于 `tools/analysis/**`、独立测试与普通文档，按维护模式 task-free 准入；通过完整测试、两域覆盖率、静态检查、独立非作者审核与 required CI 后，只交付记录级合成分析。真实数据启用、真实评分、S3、Phase 3 与宿主连接继续未启动。
