# Task-free PR 审核反馈回读

`tools/analysis/pr_feedback.py` 从显式选定 PR 的公开 connector capture 回读反馈，并提出有来源依据的下一轮核对问题。它补充[正式账本回读](review-feedback.md)，适用于 task-free 变更；两个工具分别保留自身来源范围。本工具不访问网络、不调用模型、不保存 capture 或新结果库，只向标准输出给出受限摘要。

## 使用与来源包

先通过现有公开 connector 读取选定 PR，按下表在内存中组织来源包，再将 UTF-8 JSON 通过标准输入传入。下列 `PUBLIC_CAPTURE_JSON` 表示提供该 JSON 的既有命令或内存管道，不是仓库附带的抓取命令：

```console
PUBLIC_CAPTURE_JSON | python -B tools/analysis/pr_feedback.py
PUBLIC_CAPTURE_JSON | python -B tools/analysis/pr_feedback.py --reference-input docs/operations/examples/benchmark-reference/swebench.json
```

| 来源包字段 | 内容与限制 |
|---|---|
| `schema_version` | `"1.0"`。 |
| `repository`、`retrieved_at` | `owner/repository` 与带时区的 capture 时间；仓库名两段不能为 `.` 或 `..`，不能证明各次来源读取原子一致。 |
| `pull_request` | `get_pr_info` 返回的原 payload；从中定位真实 PR、描述、head 与状态。最终 head 不补成旧受审候选。 |
| `native_reviews` | 原 `{"reviews": [...]}` 或 null；null 为未提供，不补成空集合。 |
| `native_threads` | 原 `{"review_threads": [...]}` 或 null；null 为未提供。 |
| `workflows` | `{"requested_commit_sha": "<40hex>", "data": {"workflow_runs": [...]}}` 或 null；`data` 是 `fetch_commit_workflow_runs` 原 payload，SHA 只绑定查询请求。 |

来源包顶层必须保留表中全部字段，只接受这些字段。PR payload 必须含 `number`、`url`、`state`、`merged`、`head_sha`、`merge_commit_sha`、`body`；workflow 每行必须含 `id`、`name`、`status`、`conclusion`，原 connector 其余字段可保留在输入，但不投影。缺 key 属于错误，退出 `2`；允许的 null 专门表示未知或未捕获，不能把字段静默删掉。PR `body=null` 为 `not_captured`；有 body 但没有标记块为 `absent`，两者分开。

不为演示建立实际审核输入副本，不将会话、身份、凭据、日志或本机信息加入公开来源包。可选 `--reference-input` 接受[榜单工具](benchmark-reference.md)的原输入；外部参考与本仓反馈并列，不混分、不自动匹配实际模型。

输出 JSON 使用 ASCII 转义，解码后保留原文字；`input_sha256` 绑定实际输入字节，`executed_tool_sha256` 标识本次工具字节。它们只支持复算 supplied 内容，不认证远端原件。正常退出为 `0`，读取、解析或校验错误为 `2`，不输出部分成功报告或回显原输入。捕获时间、内容 hash 均不能认证完整历史、来源原子性或声明真实性。

## PR 描述中的可选反馈块

沿用已有 PR 收尾位置，可追加以下标记包围的结构摘要。每轮使用新的 `record_id`，保留旧块；读取器解析当前描述中全部块，不用最后一块覆盖前次结果。该约定不证明 PR 平台保存了全部旧描述或强制追加式历史。

`aiflow-review-feedback:v1` 对应块内 `schema_version="1.0"`；`v2` 对应 `"2.0"`，严格保留全部 v1 字段并增加必需的 `followups` 数组。标记与块版本须一致；没有后续处理声明时 v2 使用空数组。capture 来源包仍为 `1.0`，不因块升级而改变。

下面仅为 synthetic 格式示例：全 `1`/`2` 的 SHA 是假定候选，全部原报告链接未知，不代表实际审核、模型表现或真实修复。v1 保留原 Finding；v2 另外声明处理、修复候选与复核引用。

````markdown
<!-- aiflow-review-feedback:v1 -->
```json
{
  "schema_version": "1.0",
  "record_id": "example-round-1",
  "candidate_commit": "1111111111111111111111111111111111111111",
  "category": "coding",
  "reviews": [
    {
      "review_id": "example-review-1",
      "role": "non_author_reported",
      "outcome": "REQUEST_CHANGES",
      "original_ref": null,
      "findings": [
        {
          "finding_id": "RF-001",
          "severity": "high",
          "status": "open",
          "original_ref": null
        }
      ]
    }
  ]
}
```
<!-- /aiflow-review-feedback:v1 -->

<!-- aiflow-review-feedback:v2 -->
```json
{
  "schema_version": "2.0",
  "record_id": "example-round-2",
  "candidate_commit": "2222222222222222222222222222222222222222",
  "category": "coding",
  "reviews": [
    {
      "review_id": "example-recheck-1",
      "role": "non_author_reported",
      "outcome": "APPROVE",
      "original_ref": null,
      "findings": []
    }
  ],
  "followups": [
    {
      "finding_ref": {
        "record_id": "example-round-1",
        "review_id": "example-review-1",
        "finding_id": "RF-001"
      },
      "author_disposition": {"decision": "accepted", "original_ref": null},
      "repair": {
        "kind": "code_change",
        "candidate_commit": "2222222222222222222222222222222222222222",
        "original_ref": null
      },
      "recheck_ref": {"record_id": "example-round-2", "review_id": "example-recheck-1"}
    }
  ]
}
```
<!-- /aiflow-review-feedback:v2 -->
````

块与其中对象只接受各版本规定的全部字段。`record_id`、`review_id` 是匿名安全 ID，格式为 `[A-Za-z0-9_-]{1,64}`；`candidate_commit` 为实际受审的 40 位小写十六进制 commit SHA 或 null，不能在不知道时填最终 head。`category` 使用 `[a-z][a-z0-9_-]{0,63}`。`role` 为 `non_author_reported|author_reported|unknown`；它是协调者的角色声明，不认证非作者、统计独立性或实际模型。

`outcome` 接受 `APPROVE|APPROVE_WITH_CONDITIONS|REQUEST_CHANGES|REJECT|BLOCKED|unknown`；Finding ID 使用 `RF-` 加至少三位十进制数字、`critical|high|medium|low|unknown` 严重度与 `open|resolved|unknown` 状态。`original_ref` 为 null 或同一 PR 的公开链接加 `[A-Za-z0-9_-]+` fragment；非空引用未被工具抓取，状态仍为 `not_fetched`，null 为 `not_provided`。没有可公开原件时用 null，不将摘要自身冒充原报告。

反馈块是 `coordinator_reported` 摘要，不是原生 review、缺陷真值或新权威账本。未知字段、坏 JSON、重复 JSON key、未知版本、重复 ID、未配对或嵌套标记均拒绝，不部分投影合法块。`record_id` 在当前描述全部块中唯一；`review_id` 在一个块内唯一，`finding_id` 在一个 review 内唯一，跨轮不会靠相同 ID 自动合并。跨轮保留原失败与原候选；当前记录里的 resolved 或后续 APPROVE 不覆盖先前 REQUEST_CHANGES，也不补作者采纳、实际修复或独立复核。

## v2 后续处理声明与关联

每条 `followups` 只接受以下字段，不引入 followup ID、姓名、正文或新身份来源：

| 字段 | 内容与缺失语义 |
|---|---|
| `finding_ref` | 精确三元对象 `{record_id, review_id, finding_id}`，指向该 PR 描述内某块的原 Finding。不能按同名 RF、当前候选或相近时间猜对应。 |
| `author_disposition` | `{decision, original_ref}`；decision 为 `accepted|rejected|undecided|unknown`。它是协调者记录的处置声明，不认证作者实际采纳或独立裁定。 |
| `repair` | `{kind, candidate_commit, original_ref}`；kind 为 `code_change|documentation_change|same_candidate_retry|contract_change|unknown`，candidate 为 40 位小写十六进制 SHA 或 null。实际 diff 没有被抓取，kind 和 SHA 不证明修复内容。 |
| `recheck_ref` | null 或精确对象 `{record_id, review_id}`，指向一份已报告 review；null 为 `not_provided`。角色声明与 APPROVE 不认证独立复核。 |

处置和修复的 `original_ref` 沿用同一 PR anchor 或 null 的限制，状态分别为 `not_fetched` / `not_provided`；本工具不抓取所指原件。所有引用跨当前描述全部 v1/v2 块解析，目标出现在后面的块也可对应；只认精确 ID，不补最终 head 或原件。

含任意 v2 块时报告为 `schema_version="2.0"`，后续项仅在平铺 `reported_followups` 中输出一份，不在 `reported_feedback` 重复。来源为 `body.feedback[record_id].followups[index]`；`coverage.reported_followup_records` 只是处理声明条数，不是独立样本。仅有 v1 块或没有块的报告保持原 `1.0` 形状。

Finding/recheck 引用命中分别为 `matched_reported`，当前 capture 中未找到为 `not_in_capture`；未给 recheck 为 `not_provided`。修复与复核的已报告 candidate 均已知且相等时为 `matched_reported`，不同为 `mismatched`，任一未知则为 `unknown`。这里核对的是声明关系，不认证原件或实际修复/复核；`actual`、独立真值与真实复核仍未知。原 Finding 的 `author_disposition`、`independent_recheck` 和真值字段保持未知，不由新项回填。

所有 accepted、rejected、undecided、unknown 与原失败分别保留；上例虽已声明 accepted 并指向 APPROVE，v1 的 REQUEST_CHANGES/open 仍输出。原 open 问题精确关联后只增加 `followup_sources`，不取消原问题或宣布解决。

## 原值、缺失与下一轮问题

报告的 `measurement=task_free_pr_feedback`，`source_assurance=supplied_github_records`，`source_atomicity` 与 `history_completeness` 均为 `unknown`。分开列 `reported_feedback`、原生集合和 `workflow_observations`。原生非空 reviews/threads 的 normalized 字段形状尚未实证，本轮只投影 `records_in_capture` 与 `sources` 输入 locator，`field_projection=not_projected`；`collection_status` 区分 `captured` 与 `not_captured`。空列表只表示当前 capture 未列原生记录，不证明没有机器审核。描述中无反馈块也只表示本次来源未提供结构摘要。

Workflow 来源限于 connector 首页及 PR 触发运行。原行没有可认证的 run head，`requested_commit_sha` 是 `query_reference`，不能据此认证运行原始 head、全部历史或合并提交检查。原 status/conclusion 分别保留；全部已见运行成功仍不证明 required check 集合完整，`required_checks_status=unknown`。

`next_review_questions` 是确定性的非评分准备建议：定位缺失来源与候选绑定、具体未解决的已报告 Finding、检查诊断或尚未结束的运行。每条附对应输入定位和范围；它不执行审核、为积累样本制造新一轮、把未知认作失败，或凭计数选择模型。实际是否追加及其范围继续按[专项审核流程](../superpowers/specs/supplemental-machine-review.md)和当前授权判断。

| 问题 code | 来源中满足的条件与建议范围 |
|---|---|
| `LOCATE_STRUCTURED_FEEDBACK` | body 为 null 或没有反馈块；定位已有收尾摘要来源，不要求补造一轮审核。 |
| `CHECK_CANDIDATE_REFERENCE` | 块候选为 null 或与当前报告 head 不同；核对实际受审引用，不认旧候选无效。 |
| `CHECK_REPORTED_REVIEW_CONCLUSION` | 协调者记录 REQUEST_CHANGES、REJECT 或 BLOCKED；核对该原结论及其范围。 |
| `INSPECT_REPORTED_OPEN_FINDING` | 协调者记录 Finding 为 open；核对该项，状态不是缺陷真值。 |
| `LOCATE_FOLLOWUP_FINDING` | 后续项引用的精确 Finding 未在当前 capture 找到；定位所指来源，不猜同名 RF 或补造发现。 |
| `LOCATE_FOLLOWUP_RECHECK` | 非空复核引用未命中，或 accepted 且修复候选已知但未给复核引用；定位已有复核来源，不要求制造新审核。 |
| `CHECK_REPORTED_REPAIR_CANDIDATE` | 声明同候选重试却与原 Finding 候选 SHA 不同，或 code/documentation change 却使用相同 SHA；核对声明和候选引用，未知不补成一致。 |
| `CHECK_RECHECK_CANDIDATE_REFERENCE` | 复核引用命中，但修复/复核候选未知或冲突；核对两处候选绑定，不以当前 head 补齐。 |
| `CHECK_REPORTED_RECHECK_ROLE` | 命中复核声明的角色为 author_reported 或 unknown；核对角色来源，不将角色文本认证为独立性。 |
| `CHECK_REPORTED_RECHECK_REFERENCE` | 复核指回原 Finding 所属 review；核对引用，不据此断言经过新复核。 |
| `GET_CHECK_SOURCE` | 未提供 workflows 或集合为空；定位适用检查来源，不据此断言没有检查。 |
| `CHECK_CHECK_CANDIDATE_REFERENCE` | workflow 查询 SHA 与当前 head 不同；先核绑定，不生成当前候选的失败或等待判断。 |
| `DIAGNOSE_RECORDED_CHECK_FAILURE` | 查询 SHA 与 head 相同，运行 completed 且 conclusion 为 failure、timed_out 或 startup_failure；核对所见失败。 |
| `WAIT_FOR_RECORDED_CHECK` | 查询 SHA 与 head 相同，运行尚非 completed；等待所见运行结果，不自动重跑。 |
| `CHECK_NONPASS_RESULT_SCOPE` | 查询 SHA 与 head 相同，运行 completed 且 conclusion 为其他非 success 值或 null；核对取消、skip、neutral 等原结果适用范围，不统称失败。 |

Task-free 报告的 TASK-ID 为 `not_applicable`，实际模型身份保持 `unknown`。`model_score_update_status=not_implemented`、`method_status=design_pending`、`probability_status=unestimated`、`execution_allowed=false`；权限和账本效果均为 none，Phase 3 仍为 `not_started`。当前补齐公开 PR 的声明处理链及下一轮来源核对，尚未实现反馈更新模型分数、自动安排审核或完整的评分闭环。上述问题只核对已有来源与声明，不要求制造新一轮审核。普通非评分摘要不以未来生产概率准入增加逐次审批；生产估计、真实评分 shadow 与策略接入仍满足各自 3-A/S2–S4 条件。
