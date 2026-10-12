# 检出区间的离线数学计算

`tools/analysis/review_detection.py` 按[固定接口合同](../superpowers/specs/review-detection-offline.md)计算 synthetic 计数下的条件检出比例及区间。它交付首个有界 S2 数学模块；[已采用的起步范围](../superpowers/specs/review-detection-admission.md)仍须完成真实来源、方法与质量准入，30 日观察窗口的 `T0` 尚未启动。

后续自然工作的候选、机会、输入、职责和预算端点按[真实观察准备流程](review-detection-preparation.md)核对。该流程提供可复制的说明模板；实际事实未核定时只保留来源与缺口，不把真实计数改标 synthetic 输入本工具。

## 使用

在仓库根目录把 UTF-8 JSON 直接送入标准输入。以下 ASCII 示例假定 `n=104` 个独立正缺陷机会，其中 `k=52` 个在预算内正确检出；它们只演示数值计算，不代表已有真实机会或审核结果。

PowerShell：

```powershell
Write-Output '{"schema_version":"1.0","record_origin":"synthetic","n":104,"k":52}' | python -B tools/analysis/review_detection.py
```

POSIX shell：

```bash
printf '%s\n' '{"schema_version":"1.0","record_origin":"synthetic","n":104,"k":52}' | python -B tools/analysis/review_detection.py
```

两者都输出 JSON 到标准输出。此例的 `proportion` 为 `0.5`，区间约为 `0.40034` 至 `0.59966`，总宽约为 `0.19932`，所以 `precision_met=true`。显示值仅便于阅读，精度判断使用未舍入的总宽。

没有正缺陷机会的数学输入：

```powershell
Write-Output '{"schema_version":"1.0","record_origin":"synthetic","n":0,"k":0}' | python -B tools/analysis/review_detection.py
```

此时 `calculation_status="no_positive_units"`，`conditional_result` 中的 `proportion`、`lower`、`upper`、`width` 和 `precision_met` 全部为 null；没有机会不能补成零检出率或精度通过。

## 输入与数值域

顶层恰好接受以下四个字段，纯函数入口为 `build_detection(document)`：

| 字段 | 要求 |
|---|---|
| `schema_version` | 字符串 `"1.0"`。 |
| `record_origin` | 字符串 `"synthetic"`。`real`、`historical` 和其他标签均拒绝。 |
| `n` | 整数，`0 <= n <= 104`，表示数学假设中的独立正缺陷机会数。 |
| `k` | 整数，`0 <= k <= n`，表示假定的预算内正确检出数。 |

布尔值、浮点数或字符串不能代替整数。缺字段、额外字段、重复 JSON key、NaN／Infinity、非法 JSON 以及越界计数均失败；错误退出码为 `2`，不输出部分报告，也不回显原输入。正常退出码为 `0`。

104 是当前实现已验证的数值域上界，也是[协议中条件性精度规划](../superpowers/specs/review-detection-protocol.md#51-条件性精度规划与复算)的最小最坏宽度规划值。它不限制自然观察数量，不是已有合格样本数、任务配额或补样本目标。更大输入明确拒绝；不能截断或拆分真实计数以绕过能力边界。扩展计算域须先完成相应边界验证。

标签与计数均由供给者声明，工具不能核验它们确实来自 synthetic 输入。真实或历史审核计数不能换成 `synthetic` 标签以获得本仓估计；[反馈回读](review-feedback.md)及[公开 PR 回读](pr-feedback.md)中的来源条数、Finding、APPROVE 或 CI 成功也不能直接作为 `n` 或 `k`。

## 输出怎样解释

固定方法为 `clopper_pearson_equal_tailed`，`coverage=0.95`，每尾 `0.025`，`target_width=0.20`。正数输入返回 `calculation_status="calculated"` 及 `conditional_result` 的 `n`、`k`、比例、上下界、总宽和精度判断。95% 是区间构造的覆盖要求；区间数值只在供给的独立二项机会假设下成立，不能解释为模型有 95% 可靠性。方法的“精确”指二项区间构造，浮点求根仍是数值近似。

输出明确标识 `measurement="synthetic_review_detection"`、`source_assurance="synthetic_supplied_counts"` 和 `verified_n_max=104`。即使条件区间满足总宽目标，真实研究状态仍保持 `method_status="design_pending"`、`probability_status="unestimated"`、`model_score_update_status="not_implemented"`、`actual_model_identity="unknown"`、`execution_allowed=false`，权限与账本效果均为 `none`。

CLI 的 `input_sha256` 绑定实际输入字节，`executed_tool_sha256` 绑定执行脚本字节，仅支持复算，不认证真实来源。工具不读取 Git／PR 原件作为样本，不保存输入或输出副本，不写账本或结果库，不访问网络或调用模型。

[公开榜单参考](benchmark-reference.md)描述外部配置在声明候选集合中的相对参考分；本模块描述 synthetic 假设计数下的条件区间。两者不混分，均不更新本仓实际模型评分。真实检出率仍需按采用范围核定原件、独立真值、机会选择、提示条件、相关组、预算与关闭端点。此模块不完成真实评分闭环，也不启动观察窗口、3-A 真实评分／shadow 或 Phase 3。
