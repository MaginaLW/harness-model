# 评分更新、校准与反馈路由的合成演练

`tools/analysis/review_feedback_simulation.py` 提供评分快照重算、固定分箱校准和反馈路由的离线接口。所有输入必须是虚构的 synthetic 情景；真实评分、自动审核、宿主连接与观察窗口均未启用。字段、时序和不足回退详见[接口合同](../superpowers/specs/review-feedback-simulation.md)。

## 运行示例

从仓库根使用项目解释器。PowerShell：

```powershell
Get-Content -Raw -Encoding UTF8 docs/operations/examples/review-feedback-simulation/synthetic.json |
    .\.venv\Scripts\python.exe -B tools/analysis/review_feedback_simulation.py
```

其他平台：

```sh
.venv/bin/python -B tools/analysis/review_feedback_simulation.py < docs/operations/examples/review-feedback-simulation/synthetic.json
```

[示例](examples/review-feedback-simulation/synthetic.json)中的配置、版本、仓库、引用、时间、预测与结局均虚构。预期评分由 `k=1,n=2` 重算为 `k=1,n=3`，不是累加为 `k=2,n=5`；校准两箱映射分别为 0、1，完整留出集的 raw Brier 约为 0.04、mapped Brier 为 0。显式假设和阈值下，建议为 `PREPARE_ADDITIONAL_REVIEW`。它只表示这个情景的准备建议，不派发任何审核，也不证明真实校准有效。

把阈值 `max_interval_width` 改为 0，即得到 `INSUFFICIENT_EVIDENCE`；把 `baseline_route` 改为 `ASK`，在其他检查均通过时得到 `KEEP_CURRENT_PROCESS`。三种结果都固定 `execution_allowed=false`。

## 三个纯函数

| 接口 | 输入 | 结果与限制 |
|---|---|---|
| `build_score_update(document)` | 当前完整快照、可选旧快照及配置归属假设；快照内嵌[记录级分析输入](review-detection-analysis.md)。 | 实际重算两个快照。旧候选、旧失败及组预选不可删改；同组后续尝试不增加独立计数。不给先验、外部榜单混分或累计快照的重复计数。 |
| `build_calibration(document)` | 显式分箱、固定拟合时刻、互不重叠的 fit／heldout 组、结局前预测及假设。 | 每箱拟合经验比例，在完整 heldout 上比较 raw／mapped Brier 与分箱诊断；不保证改善，不给真实接受阈值。 |
| `build_feedback_simulation(document)` | 上述两个完整输入子包及显式路由情景。 | 重新计算两子包，检查三方组隔离、版本与时序，仅输出三种模拟建议，不读写当前 route、Gate、批准或任务。 |

评分估计组、校准拟合组和留出组必须隔离；当前评分窗口结束须早于所有拟合预测。配置及版本标签相同只证明供给声明相同，不能认证实际模型、时序或统计独立性。校准目标是已声明正缺陷机会上的预算内检出结局，不是全部任务成功率。

分箱为左闭右开，最后一箱包含 1；空拟合箱保持 null，不借值或插值。留出记录落入空箱时保留全部记录与 raw 全集诊断，mapped 全集诊断为 null，路由不足。空 heldout 可以保留拟合结果，但不能通过路由。其他关键未知、组重复或时序冲突阻断整包拟合与评估，不删行后计算。

映射预测仅用于留出诊断，不改写原计数的比例或 CP 区间。Brier 变化不单独证明校准改善；同一留出集若参与选择分箱、方法或阈值，后续不能继续作为独立评估。此演练不改变[有限研究协议](../superpowers/specs/review-detection-admission.md)的一次分析约定，也不提供连续监测保证。

## 错误与复算

CLI 只读 stdin、自身和四个直接／间接依赖源码，不读原件、时钟或本机状态，不运行 Git、子进程或网络。报告包含实际 stdin 字节的 `input_sha256`、脚本 `executed_tool_sha256` 和 `dependency_sha256`；PowerShell 管道的编码／换行可能与文件字节不同。hash 支持复算，不认证真实来源。

合法报告（含不足或阻断）退出 0；非法 JSON、编码、重复 key、类型、缺／多字段或非 synthetic 来源退出 2，stdout 为空，stderr 固定为 `review-feedback-simulation: supplied synthetic scenario is invalid`。函数不修改输入，返回的可变内容也不与输入共享。

独立合成测试：

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/unit/test_review_feedback_score.py tests/unit/test_review_feedback_calibration.py -q
```

所有报告继续保留真实来源、身份、独立性与准入 `unknown`，`method_status=design_pending`、`probability_status=unestimated`、`model_score_update_status=not_implemented`，权限和账本效果为 none。新增的 `synthetic_*_status` 只描述演练结果。

## 真实启用仍缺什么

真实分析需可复核的自然候选、实际配置、独立真值、预算与关闭端点及方法适用性；校准另需真实结局前预测、固定方法和独立留出证据。真实路由需明确用途、风险参数、权限映射及兼容性验证。不能把真实材料改标 synthetic，也不能加一个批准开关就启用这套入口。

这些条件按[观察准备流程](review-detection-preparation.md#关闭后回读原值条件满足才推进评分)和[阶段进入关系](../implementation/phase-03-entry-inputs.md)核定；[宿主资料](../superpowers/specs/review-detection-host-evidence.md#8-资料获取安装版本与人工移交)仍待维护方回复。当前不设置 `T0/T1`、不启动真实评分、审核调度或连接，Phase 3 保持 `not_started`。
