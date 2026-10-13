# 观察声明的输入检查

`tools/analysis/review_detection_input.py` 回读显式提供的候选、机会和原件引用，列出时间、版本及选择关系的机械冲突和来源缺口。它支持描述真实来源，但不会抓取或认证引用，也不计算真实检出率。[输入合同](../superpowers/specs/review-detection-input.md)给出完整字段与检查代码。

## 使用

将按合同组织的 UTF-8 JSON 从内存管道交给工具：

```console
OBSERVATION_DECLARATIONS_JSON | python -B tools/analysis/review_detection_input.py
```

`OBSERVATION_DECLARATIONS_JSON` 代表调用方已有的内存来源，不是仓库附带的采集命令。工具不读 Git、网络或引用目标，不保存输入、capture 或新结果库。原件仍留在原 CLI／PR 位置，不能把本接口的字段塞入既有 PR v2 块或 AI Flow Schema。

下面是没有供给候选的格式示例，不登记真实机会或观察窗口：

```json
{
  "schema_version": "1.0",
  "repository": "example/project",
  "admission_package": "review-detection-admission-v0.1",
  "window": {"t0": null, "t1": null},
  "candidates": []
}
```

候选的版本、声明／入口／报告／关闭时间以及职责、预算等原件引用分别保留；机会另含契约、对象、实例和裁定／匹配原值。缺事实用 `null` 或合同规定的 `unknown`，不填写猜测值。引用形状只支持本仓声明的 Git 定位或同一仓库的 GitHub PR 定位，不代表实际已读取原件。

## 如何读结果

- `reported_candidates` 保存所供给的候选和机会；`coverage` 中的数量是记录数，不能当作统计样本量。
- `condition_checks` 用 `consistent_reported`、`conflict` 或 `unknown` 表示时间、候选版本、引用及真值／匹配的包内关系。合法但矛盾的数据保留在结果中。
- `group_selections` 只按既定时间和引用排序展示首候选／首机会的声明选择。首项为负或未知也不换后项；缺组、并列、排序冲突或缺引用时保持未知。
- `next_source_checks` 列出还需要核对的原件、自然文档范围、预声明、职责与输入、独立裁定／匹配、预算／关闭及组间条件。

字段全部齐全也仍为 `observation_admission=unknown`、`probability_status=unestimated`、`execution_allowed=false`。机械一致不能证明真实来源、未提示、独立裁定、完整机会集、预算覆盖或组间独立性。

正常报告（包括未知和事实冲突）退出 `0`；非法结构、类型、引用形状、UTF-8 或 JSON 退出 `2`，不输出部分报告或回显原输入。CLI 的两个 hash 仅绑定输入字节和工具字节。

## 后续衔接

依照[真实观察准备流程](review-detection-preparation.md)在自然工作中核对实际事实；已采用范围、精度和 30 日规则不需要重新选择。工具不设置 `T0/T1`，本次实现不启动观察。已有[区间计算器](review-detection.md)继续只接受 synthetic 计数，不能把本报告的记录数或真实计数改成 synthetic 输入。

真实统计输入的准入、估计及模型评分更新仍需对应来源、方法和质量证据；这个入口完成的是可执行的声明校验与缺口汇总。
