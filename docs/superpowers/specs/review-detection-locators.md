# 固定文档的有界定位核对

状态：`review-detection-locators-v0.1`；由原件工具的显式 opt-in 实现。承接[固定 Git 原件](review-detection-sources.md)，为明确供给的契约、对象和实例提供可重读的精确字节位置。定位命中不是语义适用、违约真值、真实预声明或观察准入。

## 兼容接口

原声明包、`build_detection_input` 的 no-I/O、原 source CLI 默认行为及 `build_source_checks(repository, document)` 输出保持不变。仅显式调用 `build_source_checks(repository, document, resolve_locators=True)` 或：

```console
OBSERVATION_DECLARATIONS_JSON | python -B tools/analysis/review_detection_sources.py <LOCAL_REPOSITORY_ROOT> --resolve-locators
```

才输出 `schema_version="2.0"`、`measurement="review_detection_git_locator_checks"`。它在原 source 报告上增加逐项 `locator_check`；`locator_resolution` 与该项 `locator_check.status` 相同。其他字段、未知与 `VERIFY_*` 待核事项继续保留，不清除整项原件或预声明要求。

## 唯一支持的选择器

Git 引用沿用字符串 `locator`，本版本支持以下精确语法：

```text
lines-v1:L<start>-L<end>:sha256=<expected_span_sha256>
```

`start/end` 为从 1 开始、不带前导零的 ASCII 十进制整数，`start<=end`；hash 是所选原始字节的 64 位小写十六进制 SHA-256。行按字节 `LF` 划分，行内 `CR` 和行尾 `LF` 均计入原始跨度；最后一个 `LF` 不产生额外空行，空文件没有行。单个空行仍有其 `LF` 字节。不折叠空格、不做 Unicode 或换行归一化，不把 `CR`、Unicode 分隔符或渲染换行当作新行。

只有该引用已为 `matched_git_object` 后，才在同次读取且通过对象核对的字节上解析。不得另读工作树、HEAD、不同 blob、正文链接或 PR；缓存可复用相同 Git 三元组的已核字节，但同 blob 的不同 locator 必须分别核对。字节只在调用内存中使用，不进入报告或缓存文件。先验证完整 blob 是严格 UTF-8 且不含 NUL；不支持的正文不能称可读文档定位。

`lines-v1:` 前缀下格式错误、反向范围或行号超过该 blob 字节数，均为 `invalid_selector`；字节数上界只用于有界解析，不是行存在的保证。语法正确且在上界内，但结束行超过实际行数时为 `span_unavailable`。不得裁剪范围、补全缺行或退回正文子串搜索。旧 opaque locator 或其他前缀为 `not_evaluated`，不得猜锚点或 Markdown 渲染器规则。

## 逐项输出

`locator_check` 恰含 `status`、`reason`、`observed`。`observed` 恰含 `start_line`、`end_line`、`byte_start`、`byte_end`、`span_sha256`，未定位时全部 null。`byte_start/byte_end` 为原始 blob 中从 0 开始的半开区间；成功选到跨度时输出实际行号、位置和实际 hash，不输出正文。即使所供 hash 错误，也保留实际跨度与冲突，不将其修正为命中。

| status | reason | 含义 |
|---|---|---|
| `matched_span` | `MATCHED_LINE_SPAN` | 原始行跨度存在且 hash 与声明相等。 |
| `conflict` | `SPAN_HASH_MISMATCH` | 行跨度存在，但声明 hash 不等于实际字节。 |
| `invalid_selector` | `INVALID_LINE_SELECTOR` | 已识别版本的语法、顺序或解析上界不合法。 |
| `span_unavailable` | `LINE_RANGE_NOT_PRESENT` | 合法范围超过实际行数。 |
| `not_evaluated` | `UNSUPPORTED_LOCATOR` | 不是本版本选择器。 |
| `not_evaluated` | `SOURCE_NOT_MATCHED` | null、PR、范围外、对象冲突、未读或资源限制等；不绕过原 source 结果。 |
| `not_evaluated` | `DOCUMENT_ENCODING_UNSUPPORTED` | 对象核对成功，但正文不是严格 UTF-8 或含 NUL。 |

解析上界沿用原件 1 MiB 限额。新的 opt-in 报告不改变原读取路径、网络隔离、报错脱敏或 CLI 退出规则；定位缺口与冲突仍是正常报告、退出 0。非法声明或根目录仍退出 2、stdout 为空。CLI 的工具 hash 继续仅绑定入口脚本，不能作为全部依赖的证明。

## 语义与预声明证据

精确跨度只是语义核查的可读入口。协调者仍在原 PR／CLI 位置说明：先前契约在该跨度提出什么要求、为何适用于该候选、受检对象与实例边界、直接矛盾判据和排除规则。非作者按固定原件核对这些关系；行跨度或文字相似度不能自动建立契约适用、同机制匹配、完整机会集或正真值。

真实工作可在首次非作者专项审核前，按[准备流程](../../operations/review-detection-preparation.md)发布候选固定 SHA、baseline、逐件原件及定位、完整机会边界与排序、允许材料、职责和原预算来源。发布成功后回读原 PR，确认实际声明与候选，再派发新上下文审核；之后的报告和修复引用各自候选，不覆盖原声明。不得把已经审核的旧候选补称预声明。

发布／回读／派发顺序的实际动作与各自可复核来源分开记录；只有可变描述、hash 或提交时间时，历史与真实输入时序仍未知。报告完成时间不是审核开始时间。没有公开派发原件或版本历史，就明确保留该缺口；不为补证保存私密聊天或新增存储。准备声明可以是真实任务上的实际动作，但不是研究入口；`T0/T1` 继续 null，真值／匹配／独立性不由它补齐。

## 验收

- 在真实 Git 固定原件上核对跨度与 hash，包括不同版本、同 blob 多 locator、脏工作树不替代原件。
- 核 LF、CRLF、末尾有／无 LF、空文件／空行、非 ASCII、重复正文、UTF-8 错误及 NUL；按原始字节定位，不匹配渲染或归一化文本。
- 错 hash 保留冲突和实际跨度；语法错误、反向、超大行号、缺行、旧 locator 及非 Git／未核来源分别保留。
- 原默认报告兼容，输入不变、不输出正文、不额外读对象或扩大路径，不关闭来源、语义、预声明与准入缺口。
- 在本次实际公开合同候选上发布准备声明并回读，再做既有专项审核；用其真实固定原件演示定位命中和受控冲突。它不登记研究样本，不启动观察窗口。
