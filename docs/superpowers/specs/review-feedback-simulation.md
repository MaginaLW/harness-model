# 评分更新、校准与反馈路由的合成演练合同

状态：`review-feedback-simulation-v0.1`。项目所有者明确要求先完成三部分接口、离线实现和合成验证；本合同只新增 synthetic 演练，不扩大[原有限研究](review-detection-admission.md)或启用真实评分、自动审核、宿主、provider、观察窗口。旧接口与真实状态保持原语义。

## 1. 接口与共同边界

单文件 `tools/analysis/review_feedback_simulation.py` 提供三个纯函数：`build_score_update(document)`、`build_calibration(document)`、`build_feedback_simulation(document)`。前两者分别接下述完整子包，第三者接整包并重新调用前两者，不信任供给的上游输出或旧分数。CLI `python -B tools/analysis/review_feedback_simulation.py` 只接受整包 stdin，返回 ASCII 转义 JSON。

每包顶层均恰好含 `schema_version="1.0"`、`record_origin="synthetic"` 及本节对应字段。其他来源、额外／缺字段、重复 JSON key、非法数值、类型和枚举均拒绝。合成标签不能认证实际来源，不得将真实材料改标后运行。纯函数不修改输入，返回独立副本，无文件、Git、网络、子进程、时钟、存储或执行效果。

共同 `scope` 恰好含 `profile_id`、`profile_revision`、`condition_id`，各为既有 ID 格式或 null；null 是未知并阻断依赖它的模拟，字符串相等只证明合成声明相同。目标固定为 `review_detection`：结局 1／0 分别表示已假设为正缺陷机会的预算内正确检出／未检出，不包含负真值机会。配置、角色、提示、预算、平台适用性仍只是假设，不认证模型身份。

假设枚举均仅 `assumed|unknown|violated`；未知／违反产生 `unknown|conflict` 阻断，不接 `verified` 或批准开关。时间复用既有 UTC 格式，null 保留未知；不读取当前时间。

## 2. 评分更新子包

除共同版本／来源字段外，恰好含 `profile_assignment`（上述假设枚举）、`previous`（null 或快照）、`current`（快照）。快照恰好含 `snapshot_id`（ID）、`scope`、`analysis`；analysis 为[记录级合成分析](review-detection-analysis.md)的完整输入，不接其输出。每个非空快照都实际调用原 `build_detection_analysis()`。

仅在以下条件全部成立时提供 `synthetic_score`：profile_assignment 为 assumed、scope 三项非空、两快照 scope 一致、原分析均无阻断、repository／admission_package／window／scenario_assumptions 相同，且旧候选完整保留。

旧候选按 candidate_id 比较，原字段及机会数组必须原值不变；整份候选数组重排不算修改。不得删除旧负项、失败、未知或修改其结局／引用。旧相关组的预选状态与候选／机会 ID 必须不变；新增同组后续尝试不增独立计数，新建一个更早首项也不允许覆盖旧预选。相同 snapshot_id 不得绑定不同快照内容；只重排整个候选数组可视为相同。

当前结果按完整 current 重算，绝不累加 previous 与 current 的 n/k；不使用外部榜单、先验或伪样本。`n>104`、零正项及关键未知沿用原分析。零正项可返回原空结果，但不能供路由作数值比较。多快照不提供连续监测覆盖率或真实在线更新资格。

输出 `synthetic_score_update_status=initial_snapshot|unchanged_snapshot|append_only_recomputed|blocked`、当前 scope、snapshot_id、完整 `previous_analysis`／`current_analysis`、独立副本 `synthetic_score`（原 current 条件结果或 null）、`blockers`。无 previous 时 previous_analysis 为 null。unchanged 按候选 ID 对应内容相同及其余快照条件相同判定；新的 snapshot_id 允许重放同一内容。任何旧组删改或上游不足均使 score 为 null，blocked 优先于其他状态，不用旧分数兜底。

## 3. 校准子包

除共同版本／来源字段外，恰好含 `scope`、`predictor_revision`（ID 或 null）、`fit_fixed_at`（UTC 或 null）、`bin_edges`、`scenario_assumptions`、`fit`、`heldout`。

假设恰好为 `predictions_fixed_before_outcomes`、`bins_and_split_predeclared`、`complete_independent_groups`、`same_target_and_predictor`、`no_material_drift`。predictor_revision 声明基础预测器版本，不证明预测由该程序生成。不得用同批标签算 k/n 后伪装成结局前预测。

每条 fit／heldout 记录恰好含 `unit_id`（ID）、`related_group`（ID 或 null）、`prediction`（有限数字 [0,1] 或 null，拒绝 bool）、`outcome`（整数 0／1 或 null，拒绝 bool／浮点）、`predicted_at`、`outcome_at`（UTC 或 null）。全包 unit_id 不重复，每组仅一项，fit／heldout 不共享组；重复和重叠作为语义冲突报告，不删行。未知预测、结局、组或时间阻断整体拟合与评估。

所有行须 `predicted_at < outcome_at`；fit 各 outcome_at 须 `<= fit_fixed_at`，heldout 各 predicted_at 须 `> fit_fixed_at`。heldout 的 predicted_at 是本合成情景中原预测及映射预测的固定时刻。未能证明真实时序、独立性或选择完整性的缺口始终保留。

bin_edges 显式给至少两个有限数字，严格递增，首尾恰好 0／1，无默认箱数。区间为 `[e_j,e_{j+1})`，最后一格含 1。每格拟合 `q=k_b/n_b`；空格 q 为 null，不平滑、插值、借值或 identity 回填，不强制单调。这是固定分箱平方损失的经验解；方法参考 [Guo 等 2017 §4.1](https://proceedings.mlr.press/v70/guo17a/guo17a.pdf)，本合同另固定上述端点约定。

在完整 heldout 上分别给 raw 与 mapped 的 `brier=mean((p-y)^2)` 及 reliability（按相同边界重新对相应预测归箱，每格 `count/mean_prediction/event_rate`；空格后两者 null）。Brier 同时反映多种预测性质，不独自证明校准改善；诊断依据见 [scikit-learn 官方说明](https://scikit-learn.org/stable/modules/calibration.html)。不计算 ECE、置信保证或默认通过阈值，也不保证 mapped 比 raw 好。

非空 fit 且其他输入无阻断时输出 fit_bins（每格 lower、upper、count、positives、mapped_probability）。空 fit 为 blocked、指标 null。仅 heldout 为空时可保留拟合结果，状态 fit_only、诊断 null，路由仍不足。heldout 落入任何空 fit 箱时保留逐行 mapped_predictions 的 null 和覆盖缺口，raw 全集诊断仍可给，mapped 全集诊断为 null；绝不只评估可映射子集。

输出 `synthetic_calibration_status=blocked|fit_only|incomplete_mapping|evaluated`、scope、predictor_revision、bin_edges、fit_fixed_at、fit／heldout／scenario_assumptions 的原值副本、fit_bins、mapped_predictions（按 heldout 原顺序，含 unit_id、prediction）、raw_diagnostics／mapped_diagnostics（各含 count、brier、reliability 或 null）、`blockers`。无可用拟合时 fit_bins／mapped_predictions 为 null；有拟合但无 heldout 时 mapped_predictions 为空数组。除 empty heldout／unseen fit bin 上述专列情形，任何语义阻断都不给拟合与诊断。若 heldout 用于修改箱、方法或路由阈值，该集合已参与选择，后继不能继续宣称独立留出评估。

## 4. 整包与模拟路由

整包除共同版本／来源字段外，恰好含完整 `score_update`、完整 `calibration` 和 `routing_scenario`。后者恰好含：

| 字段 | 合成含义 |
|---|---|
| `baseline_route` | `AUTO|ASK|REVIEW|BLOCK|unknown`；不读取或认证原生 route。 |
| `baseline_continuation`、`authorization_boundary_preserved`、`no_material_drift` | 三项独立假设枚举；任何非 assumed 均不足，不重试或新增批准请求。 |
| `trigger_below_lower_bound`、`max_interval_width`、`max_heldout_brier` | 显式有限 [0,1] 数字或 null，拒绝 bool；null 为未知，无生产默认值。 |

先实际重算两子包并保留完整报告，再核 scope 相同、calibration.predictor_revision 等于 current.snapshot_id。评分 previous／current 声明中的所有非空组与 fit／heldout 组必须全不交叉；合成时间还须 current.analysis.declarations.window.t1 严格早于每个 fit.predicted_at，避免用估计结局反推过去预测。组名和版本匹配只是机械检查，真实归属及独立性仍未知。

若有子包阻断／不足、空正分母、scope／版本／三方组／时间冲突、路由假设未知／违反、阈值未知或 baseline_route 未知，则 `recommendation=INSUFFICIENT_EVIDENCE`。无不足后，若当前区间 width 大于 max_interval_width、mapped heldout Brier 大于 max_heldout_brier 或劣于同集 raw Brier，也回退不足。这些是本模拟的显式筛选规则，不是统计接受、真实校准或风险通过标准。

上述检查通过后，ASK／BLOCK 仍输出 `KEEP_CURRENT_PROCESS`；其他场景仅当原更新区间 lower 严格小于 trigger_below_lower_bound 时输出 `PREPARE_ADDITIONAL_REVIEW`，相等或更高则 `KEEP_CURRENT_PROCESS`。映射只用于 heldout 预测诊断，不校准或改写 CP 区间，不将两类概率平均。高分不减少已有审核，低分也不实际追加、派发或安排审核。

输出 score_update／calibration 完整报告、routing_scenario 副本、`recommendation`、`blockers`。所有 blockers 恰好含稳定 code、status（unknown／conflict）和相对各纯函数输入的 locator；整包聚合时分别加 score_update／calibration 前缀，保留全部原因，不以成功覆盖失败。baseline_route 原值保留，不产生 native／effective route、审批或调度结果。

新增代码限定为 `PROFILE_ASSIGNMENT`、`SCOPE_UNKNOWN`、`SCOPE_MISMATCH`、`UPSTREAM_BLOCKED`、`COHORT_MISMATCH`、`HISTORY_CHANGED`、`SELECTION_CHANGED`、`SNAPSHOT_ID_REUSED`、`CALIBRATION_ASSUMPTION`、`PREDICTOR_UNKNOWN`、`REQUIRED_VALUE`、`EVENT_ORDER`、`DUPLICATE_UNIT`、`GROUP_OVERLAP`、`EMPTY_FIT`、`EMPTY_HELDOUT`、`UNSEEN_FIT_BIN`、`ROUTING_ASSUMPTION`、`ROUTING_THRESHOLD_UNKNOWN`、`BASELINE_UNKNOWN`、`NO_SCORE`、`CALIBRATION_INCOMPLETE`、`PREDICTOR_MISMATCH`、`SPLIT_GROUP_OVERLAP`、`ESTIMATION_TIME_OVERLAP`、`INTERVAL_TOO_WIDE`、`HELDOUT_LOSS_TOO_HIGH`、`HELDOUT_LOSS_WORSENED`。旧分析自身的详细 blockers 保留在其嵌套报告中，上一层以 UPSTREAM_BLOCKED 指明受影响输入。

## 5. 错误、验证与交付

三接口的所有报告均固定 `schema_version=1.0`、`record_origin=synthetic`、`target=review_detection`、`source_authenticity=unknown`、`profile_applicability=unknown`、`actual_model_identity=unknown`、`statistical_independence=unknown`、`observation_admission=unknown`、`method_status=design_pending`、`probability_status=unestimated`、`model_score_update_status=not_implemented`、`execution_allowed=false`、`permission_effect=none`、`ledger_effect=none`；measurement 分别为 `synthetic_score_update`、`synthetic_calibration`、`synthetic_feedback_simulation`。新增 synthetic 状态不回写旧接口或真实状态。

CLI 合法报告（包括阻断）exit 0；读取、解析、形状错误 exit 2，stdout 为空，stderr 固定 `review-feedback-simulation: supplied synthetic scenario is invalid`。复用 benchmark_reference 的 strict JSON hooks；只读 stdin、本脚本及 benchmark_reference.py、review_detection.py、review_detection_input.py、review_detection_analysis.py 四项源码，输出原字节 input_sha256、本脚本 executed_tool_sha256、四依赖 dependency_sha256。hash 只支持复算，不证明预测时序或身份。

验收覆盖：1/2 更新为 1/3 而非 1/5、同快照幂等、旧失败和组不变、同组重试不增 N、scope／版本／窗口冲突、104／105；手算分箱与 Brier、改善和恶化、0／边界／1、空箱与空集、未知不删行、三方组／时间防泄漏；三种路由建议、阈值相等、ASK／BLOCK 保留、旧失败／权限／漂移不足不放行；strict JSON／Unicode／固定安全错误、纯函数与 CLI 无副作用、三接口输入无别名。只用虚构原件、预测、标签和时间，不调用真实 Git／PR／宿主。

范围仅 tools/analysis、独立测试与普通文档，维护模式 task-free；不触及 src/aiflow、Policy、AI Flow Schema、依赖或治理授权。主 agent 固定合同，代码与独立测试并行，完整验证、非作者审核、required CI 与 merge commit 发布串行收口。此交付不选择真实预测方法／阈值，不启动 S3、自动审核或 Phase 3。
