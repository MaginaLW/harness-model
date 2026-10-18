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

## 本地 Git 原件核对

需要实际核对明确供给的 Git 文档引用时，使用[独立原件合同](../superpowers/specs/review-detection-sources.md)定义的显式入口：

```console
OBSERVATION_DECLARATIONS_JSON | python -B tools/analysis/review_detection_sources.py <LOCAL_REPOSITORY_ROOT>
```

输入仍是上面的声明包；必须显式指定本地 Git 工作树根。原声明工具及其 `build_detection_input` 保持 no-I/O，独立入口不改变默认输出或账本白名单。

独立报告逐项核对显式 `docs/**` 引用自己的 commit、精确 literal path、普通文件 mode、声明 blob 及实际字节。每件最多读取 1 MiB，不读工作树、PR 或正文里的链接，不输出正文。`matched_git_object` 只表示上述对象绑定与字节匹配；错误 blob 为 `conflict`，缺对象、路径或读取失败为 `unavailable`，PR、null、范围外、非普通文件及超限为 `not_checked`，具体原因分列。

每项的 `locator_resolution=not_evaluated`，原 `VERIFY_*` 待核事项继续保留。实际公开性、仓库身份、语义定位、先前契约适用、自然变更范围、预声明、职责、真值、预算及关闭均需对应证据；本地对象命中不将它们认证为成立。工具不补 HEAD 或 baseline，也不登记合格观察单位。

正常报告含冲突和缺口，退出 `0`；非法声明或仓库根退出 `2`，不回显输入与底层异常。CLI hash 只绑定 stdin 和工具字节。报告继续固定未知准入、未估计概率、无评分更新及 `execution_allowed=false`。

## 后续衔接

依照[真实观察准备流程](review-detection-preparation.md)在自然工作中核对实际事实；已采用范围、精度和 30 日规则不需要重新选择。工具不设置 `T0/T1`，本次实现不启动观察。已有[区间计算器](review-detection.md)继续只接受 synthetic 计数，不能把本报告的记录数或真实计数改成 synthetic 输入。

真实统计输入的准入、估计及模型评分更新仍需对应来源、方法和质量证据；这个入口完成的是可执行的声明校验与缺口汇总。
