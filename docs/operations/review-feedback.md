# 本仓审核结果回读

`tools/analysis/review_feedback.py` 从固定 tracked `HEAD` 的正式账本原件，汇总审核修订、Finding 状态和已有验证结果，支持追加机器审核后的事实反馈。它复用[事实快照](effect-observations.md#固定提交的事实快照)的 Git 白名单，不读 PR、会话或私密来源，不新增采集器或结果库。Task-free 来源另由[公开 PR 反馈回读](pr-feedback.md)支持，并可形成下一轮非评分核对问题；其 v2 块还可显式关联 Finding、作者处置、修复候选和复核声明，不改本工具的来源或未知字段。模型分数更新及自动审核安排尚未实现，不能称为完整评分反馈闭环。

## 使用

在仓库根目录运行：

```console
python -B tools/analysis/review_feedback.py
python -B tools/analysis/review_feedback.py --task TASK-0077 --task TASK-0078
python -B tools/analysis/review_feedback.py --task TASK-0077 --reference-input docs/operations/examples/benchmark-reference/swebench.json
```

可用位置参数指定另一个已有仓库。`--task` 只过滤报告中的任务，不缩小底层固定 `HEAD` 白名单读取与校验；不能用过滤跳过其他任务的无效原件。可选 `--reference-input` 读取[榜单工具](benchmark-reference.md)接受的 strict JSON，保留输入字节 hash，并列展示外部参考；不访问网络、重新抓取榜单或自动匹配本仓模型。

正常退出为 `0`；原件或输入读取、解析、校验失败时退出 `2`，不输出成功报告或回显原内容。JSON 输出使用 ASCII 转义，解码后保留原文字。工具不写输入、账本、审核原件、Git 状态或新存储。

## 来源与受限字段

报告用途标识为 `measurement=review_feedback_readback`。底层使用 `build_snapshot(repository, include_feedback=True)`；已有 `approval_overhead.py` 默认统计、`--snapshot` 与 `--availability` 的格式和字段不变。

来源仍是同一提交中的 `.ai/tasks/TASK-*/task.yaml`、`classification.json`、`events.jsonl`、`evidence.json`、`reviews/REV-*-r*.json` 及引用的同 task `review-contexts/<64sha>.json`。未提交材料不进入报告；未被审核引用的 tracked context 只列 blob 来源，不解析其内容。任务与事件必需原件、格式、类型、身份及 canonical hash 校验沿用快照规则。

显式反馈投影只在现有受限字段上增加 Finding 的 `finding_id`、`severity`、`status`、`resolved_at`，以及解决事件的 `finding_id`。不输出 Finding 正文、reason、reviewer、actor、自由路径或 evidence refs。原 review outcome、stage、context、事件、验证尝试和 evidence 原值继续保留；来源关系不是重新审核或验收。

可复核引用包含 `source_commit`、仓内 `path`、`git_blob` 和 `locator`。定位使用原对象 ID、修订或事件 sequence；review 与 Finding 可以沿引用回到实际读取的 Git 原件。行号不单独标识修订，hash 不认证原声明真实性。

## 如何读审核与 Finding 历史

按 `task_id + review_id` 保留每一份已观测修订；同一审核内按 `finding_id` 关联 Finding 的已观测状态，跨审核的同名 Finding 不自动合并。每个版本的原 outcome、严重度、状态、时间及来源分别保留。`observed_first_revision`、`observed_latest_revision` 只表示当前固定提交能读到的首次与末次，不证明全历史起点或完整性。

原生 `resolve` 只改变 Finding 状态并追加 review 修订，不把原 `REQUEST_CHANGES` 改成 `APPROVE`。例如 TASK-0077 的 REV-0001：r0001 的 RF-001 为 open，r0002 为 resolved，两份 outcome 均为 REQUEST_CHANGES。报告应保留两份原件，不能据 resolved 宣称审核通过、修复成功或任务解除阻断；后继 TASK-0078 的结果也不能覆盖它。固定历史来源例子见[数据合同](../superpowers/specs/readonly-confidence-data-contract.md#6-固定来源链例子task-0077--task-0078)。

`review_histories` 按审核列出 `observed_revisions` 与 `history_issues`，修订缺号、同一审核 stage/context 变化在有无 Finding 时均保留。`finding_histories` 继续列各 Finding 的状态观察及严重度变化、重开或某修订缺少已有 Finding 等异常。异常与原值一起保留，不把缺号补齐、把消失当解决、把末次结果回填到前次。没有异常也不认证全历史完整；当前 evidence 与历史尝试的对应仍按原快照保留未知。

## 原件支持的事实与未知

| 可回读内容 | 保持的边界 |
|---|---|
| 固定 task、review/context/event 引用与原结果 | 不重算 live status、批准新鲜度或 Gate，不验证账本声明真实性。 |
| Finding 的状态历史与已有解决事件引用 | 不能推作者采纳/驳回、缺陷真值、独立复核或实际修复范围；`author_disposition`、`independent_recheck` 保持 `unknown`。 |
| 已记录验证尝试及 evidence 原值 | 不补全首候选、修复入口或历史 evidence-attempt 链；失败、partial、skip 和 unknown 不被后续成功覆盖。 |
| 同 task 的保守依赖关联 | Finding、检查、修订、重试不增加独立样本；不同 task 也可能共享候选、规格或后继关系。 |
| 正式账本来源覆盖 | 本工具的 task-free 审核反馈仍为 `task_free_feedback_status=not_projected`；对应 limitation 只说明本报告不投影，并指向已有的[PR 回读](pr-feedback.md)，不表示项目尚未实现该能力。另用 PR 回读显式输入选定公开来源，不扩大 Git 白名单，也不创建虚构 TASK-ID。 |

实际模型及审核配置、任务类别、报告新增/重复对应、独立正负真值、人时和费用没有相应获准来源时保持未知；不从 actor、模型名称、自述、Finding 数或工具耗时补值。缺少实际配置不阻挡这份非评分事实报告，但不能据此归入模型层或更新模型评分。

## 与初始参考和后续判断衔接

`external_reference` 与本仓事实并列：榜单仍计算声明配置集合内的相对分，本仓状态仍是原件事实；两者不混分、不把 Finding 数、resolved、APPROVE 或最终 CI 通过换算模型胜率。`model_score_update_status=not_implemented` 明确没有根据反馈更新评分。PR 回读的 `reported_followups` 将处理关系声明与原报告分开，缺引用或候选冲突仍保留；其 `next_review_questions` 可支持下一轮非评分问题准备，但没有自动改变审核安排。

当前维持 `method_status=design_pending`、`probability_status=unestimated`、`execution_allowed=false`，无权限或账本效果；route、Gate、CI、批准和原审核流程继续按现行规则执行。只读回读属于 S0/S1 事实准备，其普通源码实施按现行维护授权完成；生产概率、真实评分 shadow 或策略接入的 3-A/S2–S4 条件不成为这份非评分摘要的额外逐次审批。

结果可帮助协调者识别尚缺哪个来源、哪些原失败仍需保留、下一份具体专项问题应核对什么。再按[专项审核流程](../superpowers/specs/supplemental-machine-review.md)引用原候选、处理与复核；未来评分更新和实际安排须有可用身份、目标/机会集或真值、相关组、质量及用途规则支持。没有这些事实时继续描述观察与缺口，不宣称额外审核降低返工、人工成本或缺陷率。
