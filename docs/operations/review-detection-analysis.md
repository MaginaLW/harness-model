# 记录级条件分析的合成演练

`tools/analysis/review_detection_analysis.py` 把记录级声明、机械预选、必要条件和既有区间计算串起来，供真实输入分析的接口与实现准备。当前仅接受 synthetic envelope，不接真实数据、Git／PR 回读报告或宿主，不启动评分、窗口或审核策略。详细字段与回退规则见[实现合同](../superpowers/specs/review-detection-analysis.md)。

## 运行示例

从仓库根使用项目解释器。PowerShell：

```powershell
Get-Content -Raw -Encoding UTF8 docs/operations/examples/review-detection-analysis/synthetic.json |
    .\.venv\Scripts\python.exe -B tools/analysis/review_detection_analysis.py
```

其他平台：

```sh
.venv/bin/python -B tools/analysis/review_detection_analysis.py < docs/operations/examples/review-detection-analysis/synthetic.json
```

[示例](examples/review-detection-analysis/synthetic.json)的仓库、SHA、时间、引用和结局全部虚构；不核对这些引用是否存在。两组选中项分别是已声明检出的正项及负项，七项情景假设均为 `assumed`。预期 `analysis_status=conditional_synthetic`，数学结果 `n=1,k=1`，95% 区间约为 `[0.025,1]`，精度不满足；负项不进正分母，其匹配未知是合法情形。

将任一情景假设改为 `unknown`，或把示例正项的 `closed_at` 改为 null，即得到合法的 `blocked` 报告：`synthetic_calculation=null`，仍退出 0 并保留所有声明与缺口。不得丢弃问题项后计算剩余项，也不得改选同组后续正项。

## 输入与结果的边界

顶层只含 `schema_version="1.0"`、`record_origin="synthetic"`、`declarations` 和 `scenario_assumptions`。`declarations` 完全复用[原声明接口](review-detection-input.md)；假设枚举只支持 `assumed`／`unknown`／`violated`，不支持真实准入或 `verified` 开关。程序不能证明供给输入确实合成，不能将真实声明重标后运行。

结果的 `declaration_readback` 完整保留原值、未知和来源待核事项；`selected_units` 与 `reported_selection_counts` 只是预选声明诊断。`blockers` 定位受影响条件，任何关键未知／冲突都停止整批数学结果。明确窗口外及不影响预选的未选项保留原回读，不因它们的无关缺口误阻断选中路径。

只有无阻断时才调用原[synthetic 数学模块](review-detection.md)。零正项保持空比例／区间；超过 104 个正项阻断，不截断或拆批。数学方法与数值验证域沿用原模块；本层不新增先验、聚类模型、校准、模型评分或路由。

CLI 只读取 stdin 和本脚本、三项依赖的源码，不读取时钟或原件，不访问网络、运行 Git／其他进程或写入文件、账本。输出 ASCII 转义 JSON；`input_sha256` 对实际 stdin 字节计算，PowerShell 管道的换行／编码可能与文件字节不同。脚本及依赖 hash 只支持复算，不认证来源或真实执行身份。

正常报告（含 blocked）退出 0；错误 JSON、字段、类型、编码或非 synthetic 来源退出 2，stdout 为空，stderr 只给固定错误，不回显输入或路径。构建函数无 I/O、不修改输入，返回值也不与输入共享可变对象。

## 验证与后续启用

合成反例和真实 CLI 测试可独立运行，不使用真实任务或原件：

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/unit/test_review_detection_analysis.py -q
```

所有报告都保持来源真实性、历史完整性、观察准入和统计独立性 `unknown`，真实概率 `unestimated`、评分更新 `not_implemented`、`execution_allowed=false`。假设填全与 `conditional_synthetic` 均不认证真实分析就绪。

未来真实分析需另核对应来源／方法／质量与实现准入，复用记录结构和已验证处理逻辑，不能给此入口增加一个批准布尔值就接真实数据。实际候选、独立裁定、输入与预算端点、窗口及[宿主资料](../superpowers/specs/review-detection-host-evidence.md)的缺口保持，按[观察准备流程](review-detection-preparation.md)推进；本次演练不登记真实机会或设置 `T0/T1`。
