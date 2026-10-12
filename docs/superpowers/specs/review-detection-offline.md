# 检出区间首个离线数学实现合同

状态：`review-detection-offline-v0.1`。项目所有者已采用[有限研究范围](review-detection-admission.md)；本合同串行固定首个 S2 模块的接口与验收。它仅实现已选等尾双侧精确二项区间的 synthetic 数值计算，不接入真实原件、纳入裁定、总体推断、评分更新或 30 日观察窗口。

## 1. 范围与准入核对

现有 `review_feedback` / `pr_feedback` 仍不能自动认证独立真值、语义匹配、未提示条件与关闭端点；来源事实计数不能转作统计 N。本模块先接受纯数学的 synthetic 计数，与原件读取模块分开；不读取 Git／PR／文件作为样本，不将来源声明、布尔许可或当前 HEAD 解释成真实研究准入。

已核定数值方法、95% 覆盖、总宽 0.20 及 [1..104 的规划边界](review-detection-protocol.md#51-条件性精度规划与复算)；最小实现只承诺 `n=0..104` 的已验证数值域，104 是本模块能力边界，不是自然观察、任务或样本的上限。更大计数明确拒绝，扩数值域须有新边界验证，不能截断输入。

实现只改 `tools/analysis/**`、独立测试和普通用法文档，属于维护模式 task-free 范围；不改 `src/aiflow`、Policy／Schema、CI、依赖或授权。沿用 required CI 全部门槛，纯构建函数无文件／进程／网络／账本／权限效果。合格数值实现不使 3-A、S3 或 Phase 3 自动准入。

## 2. 固定输入与接口

纯函数为 `build_detection(document)`，入口为 `python -B tools/analysis/review_detection.py`，只从标准输入读 UTF-8 JSON。顶层**恰好**含四个字段：

| 字段 | 固定要求 |
|---|---|
| `schema_version` | 字符串 `"1.0"`。 |
| `record_origin` | 字符串 `"synthetic"`；真实、历史或供给声明输入一律拒绝，不能静默改标签。 |
| `n` | Python／JSON 整数，`0 <= n <= 104`；不接受布尔值、浮点或字符串。含义为数学假设中独立正缺陷机会数，不是原件计数。 |
| `k` | 同类型整数，`0 <= k <= n`；假定的预算内正确检出数。 |

缺字段、额外字段、重复 JSON key、NaN／Infinity、类型或范围错误均拒绝，不输出部分报告。CLI 不建副本、不保存输入／输出；正常退出 0，读取／解析／校验错误退出 2，错误不得回显原输入。调用本工具不核验输入是否真的 synthetic，标签和计数均为供给声明。

## 3. 数值与输出

固定 `alpha=0.05`，每尾 `0.025`。`0<n` 时按二项 CDF 反演：`k=0` 的下界为 0，`k=n` 的上界为 1，其余下界解 `F(k-1;n,L)=0.975`，上界解 `F(k;n,U)=0.025`。使用 Python 标准库 `comb`、`fsum` 和有界二分，不新增依赖。区间方法的“精确”指二项构造，浮点求根是数值近似；不将四舍五入端点用于精度判断。

输出 `schema_version="1.0"`、`measurement="synthetic_review_detection"`、`record_origin="synthetic"`、`source_assurance="synthetic_supplied_counts"`，固定 `method="clopper_pearson_equal_tailed"`、`coverage=0.95`、`target_width=0.20`、`verified_n_max=104`。

`conditional_result` 恰好列 `n`、`k`、`proportion`、`lower`、`upper`、`width`、`precision_met`。`n>0` 时 `calculation_status="calculated"`，比例为 `k/n`，宽度为 `upper-lower`，精度为未舍入宽度 `<=0.20`。`n=0,k=0` 时 `calculation_status="no_positive_units"`，上述五个结果字段全部 null，不补 0、默认区间或精度通过。

固定保留 `method_status="design_pending"`、`probability_status="unestimated"`、`model_score_update_status="not_implemented"`、`actual_model_identity="unknown"`、`execution_allowed=false`、`permission_effect="none"`、`ledger_effect="none"`；它们描述真实研究尚未准入，数值结果只是假设输入下的条件计算，不是本仓概率或实际模型评分。CLI 另给实际输入字节 `input_sha256` 和执行脚本字节 `executed_tool_sha256`，只支持复算，不认证来源。

## 4. 独立验收

- 空样本、全检出、零检出和中心情况；用独立解析端点／精确有理数 CDF 校核上下尾及数值容差，而不只抄实现求根。
- `103,k=51/52` 的宽度大于 0.20，`104,k=52` 小于 0.20；独立全 k 枚举确认规划边界，不假设中心最大。
- 真实输入标签、越界计数、布尔／浮点、缺／额外字段、重复 key、非法 JSON 常数均失败；原输入不被回显。
- 纯函数及 CLI 的无网络／子进程／写入效果；不从审核、Finding、CI 条数推 N，不给执行权限或模型评分。

通过上述验收与独立非作者审核、required CI 后，只报告此有界离线模块交付。真实观察仍需原件、机会选择与独立真值、条件／提示、相关组、预算／端点及 `T0/T1` 的核定；采用范围不认证这些事实。历史回放、synthetic 输出与数学检查均不计自然正缺陷机会。
