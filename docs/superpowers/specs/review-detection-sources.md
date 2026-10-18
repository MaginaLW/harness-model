# 观察声明的固定 Git 文档原件核对

状态：`review-detection-sources-v0.1`。本合同补齐[声明输入检查](review-detection-input.md)不能读取引用目标的机械缺口，复用[已采用范围](review-detection-admission.md)内明确供给的文档原件。它不改变原声明工具的纯函数、默认 CLI、输入形状或 no-I/O 边界，不扩展账本快照白名单，不登记观察单位或启动窗口。

[有界定位合同](review-detection-locators.md)另定义显式 opt-in 的精确行跨度核对；默认 v1 的 `locator_resolution=not_evaluated` 及以下行为不变。

## 接口与读取范围

函数为 `build_source_checks(repository, document)`；显式入口为：

```console
OBSERVATION_DECLARATIONS_JSON | python -B tools/analysis/review_detection_sources.py <LOCAL_REPOSITORY_ROOT>
```

输入完全沿用 `review-detection-input-v0.1`，用现有 `build_detection_input` 校验，不接受额外字段。必须显式给出一个本地 Git 工作树根目录；不猜仓库、不读取当前 HEAD 代替引用，不读取 remote 配置认证仓库身份。输入的 `repository` 仍只是声明标签，真实身份与公开性未知。

只检查候选 `refs` 的八项引用及机会的 `contract_ref`、`object_ref`、`instance_ref`、`adjudication_ref`、`matching_ref`。每个字段分别输出；相同 Git 三元组可在本次调用中复用核对结果，不创建缓存文件或结果库。

首版只读取明确供给的 `docs/**` Git 引用；不遍历仓库、工作树或正文内链接，不读 PR、会话、身份、费用或私密来源。路径必须以 `docs/` 开始，使用 literal pathspec 精确查询；原输入的路径逃逸拒绝继续适用。引用的每个 `source_commit` 独立读取，先前契约不能被候选版本或当前 HEAD 替换。

依次核对：

1. 完整 SHA 指向本地 commit 对象；不解析分支、标签或替换对象。
2. 该 commit 的精确路径存在，且为单一 `100644` 或 `100755` 普通 blob。目录、符号链接和 submodule 不能作为普通原件读取。
3. 树中实际 blob 与声明 `git_blob` 相等；不符时不读取另一 blob 正文。
4. 读取对应 blob 的实际字节，复算 Git SHA-1 对象 ID，并输出内容 SHA-256 和字节数；不输出正文。每件 blob 的接收上限为 1 MiB，此限额仅约束本地读取资源，不是样本数、审核预算或统计门槛。先读对象大小，超限不读正文。

对象头部声明的大小不作为实际输出长度保证。正文使用无缓冲管道，最多读取声明大小加一个超量探测字节（因而每件管道读取硬上界为 1 MiB + 1 字节）；探测字节只用于拒绝多余输出，不增加可接受正文上限。超量、短读、进程失败或超时均保留 `unavailable/GIT_READ_UNAVAILABLE`，不输出部分正文；终止并回收子进程、关闭管道。原有 30 秒期限同时覆盖正文读取与等待进程退出，stderr 不捕获。默认快照、availability 及其他未指定输出上界的 Git 调用保持原路径。

复用 `approval_overhead._snapshot_git` 的隔离调用：清除继承的 `GIT_*`，禁全局／系统配置、replace objects、交互、可选锁、lazy fetch 和协议访问，每次 Git 调用上限 30 秒。命令只读，不执行 checkout、fetch、hooks、filters 或被读内容；不改变该辅助函数及既有快照范围。

## 输出与限制

独立报告使用 `schema_version="1.0"`、`measurement="review_detection_git_source_checks"`、原 `repository`、`admission_package`、`window`，以及 `source_checks` 和原声明报告的 `next_source_checks`。保留所有语义来源待核事项；机械对象命中不能关闭整项 `VERIFY_ORIGINALS`。

每条 `source_checks` 含：

| 字段 | 含义 |
|---|---|
| `input_locator` | 引用所在的输入字段路径，区分重复供给的记录。 |
| `reported_reference` | 原引用或 null，不替换错误 blob 或旧候选。 |
| `status` | `matched_git_object`、`conflict`、`unavailable` 或 `not_checked`。 |
| `reason` | 下表稳定代码。 |
| `observed` | 恰含 `git_blob`、`mode`、`bytes_read`、`content_sha256`；未读取或不可知字段为 null。 |
| `locator_resolution` | 固定 `not_evaluated`。semantic locator 不因对象存在、正文匹配或 hash 正确而成立。 |

| reason | status 与语义 |
|---|---|
| `MATCHED_GIT_OBJECT` | `matched_git_object`；固定 commit/path/blob 与实际读取字节一致。 |
| `GIT_BLOB_MISMATCH`、`GIT_OBJECT_HASH_MISMATCH`、`COMMIT_TYPE_MISMATCH` | `conflict`；保留声明和实际可得的冲突，不改写引用。 |
| `GIT_READ_UNAVAILABLE` | `unavailable`；对象缺失、Git 命令失败或读取期间不可用，不能断言原件不存在。 |
| `PATH_NOT_IN_TREE` | `unavailable`；成功读取的该 commit 精确路径查询为空。 |
| `REFERENCE_NOT_PROVIDED`、`PR_REFERENCE_NOT_READ`、`PATH_OUTSIDE_DOCS_SCOPE`、`NON_REGULAR_GIT_ENTRY`、`BLOB_SIZE_LIMIT` | `not_checked`；分别保留未供给、PR 未读取、范围外、非普通文件或读取资源限额。 |

报告固定 `source_assurance="local_git_object_checks"`、`repository_identity="unknown"`、`source_atomicity="unknown"`。`source_authenticity`、`history_completeness`、`observation_admission`、`statistical_independence`、`actual_model_identity` 继续 `unknown`；`method_status=design_pending`、`probability_status=unestimated`、`model_score_update_status=not_implemented`、`execution_allowed=false`、`permission_effect=none`、`ledger_effect=none`。

对象匹配只说明此刻读到对应 Git 字节，不认证公开来源、语义定位、适用契约、自然纯文档范围、真实预声明或提示暴露时序、机会完整性、职责、独立真值、预算及关闭端点。输入未给 baseline，因此不计算变更范围，也不猜父提交。输出不计样本、不产生 n/k、真实比例、ready 或评分。

CLI 增加 `input_sha256` 与 `executed_tool_sha256`，仅绑定实际 stdin 和本工具字节。正常报告包括冲突与缺口，退出 0；非法输入、无效仓库根或根检查失败退出 2，stdout 为空，stderr 固定为 `review-detection-sources: supplied declarations or repository are invalid`，不回显内容、路径或底层异常。单件引用读取失败留在报告，不转成全包成功认证，不自动重试。

## 验收

- 在真实 Git 夹具上核正确绑定、不同版本的候选／契约、错误 blob、缺对象／路径及 commit 类型冲突；工作树内容不能替代 Git 原件。
- literal 文件名中的 `*`、`[`、pathspec magic 不扩大读取；目录、symlink、submodule 和范围外引用均不能按普通文档通过。
- PR／null 保留未核；错误 blob 不读其他正文，声明超限不读正文，字节 hash 与长度不符不能命中。真实损坏 loose object 的声明大小为 0、1 或 1 MiB 而正文更大时，实际读取仍受声明大小加一个探测字节约束，默认与定位模式均不认证部分正文。
- 继承 `GIT_DIR` 等、replace refs 不能改变对象；缺本地对象不触发联网。固定仓库失败为安全错误，引用级故障与原值保留。
- 不修改输入、Git refs、工作树或输入来源，不回显正文；现有声明工具的 no-I/O 和 synthetic 数学接口原样通过。
- 在本仓明确的真实文档引用上做一次非评分核对，给出真实匹配和受控错误引用的冲突；它是来源能力验证，不是自然审核单位、独立缺陷真值或研究样本。
