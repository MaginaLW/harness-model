# 公开榜单的初始参考评分

项目所有者已允许最初评分参考各排名网站。`tools/analysis/benchmark_reference.py` 提供离线、可复算的候选配置相对参考分，用于准备追加机器专项审核；本仓真实审核、处理与复核结果仍按[专项审核反馈流程](../superpowers/specs/supplemental-machine-review.md)积累。它不估计本仓成功率、检出率或误报率，不接入自动审核、route、Gate 或批准。

## 使用

在仓库根目录运行，读取 UTF-8 JSON，输出 JSON 到标准输出。输出使用 ASCII 转义以兼容 Windows 管道编码，JSON 解码后的文字保持原值。不写输入、账本或结果库，不访问网络、调用模型或读取本地会话。正常退出为 0，文件或数据错误为 2；错误时 stdout 为空，stderr 只输出固定说明 `Invalid reference input.`，不回显文件路径、输入原文或底层异常。

```console
python tools/analysis/benchmark_reference.py --input docs/operations/examples/benchmark-reference/swebench.json
python tools/analysis/benchmark_reference.py --input docs/operations/examples/benchmark-reference/aider.json
python tools/analysis/benchmark_reference.py --input docs/operations/examples/benchmark-reference/arena-webdev.json
```

示例只是来源核对及算法演示的少量公开事实，分别使用不同候选集合，不能把三份输出再次平均。保留原样可复算；刷新时从对应官方来源重新核对日期、指标和完整配置，生成新的输入和 hash，不用抓取日期冒充测量日期，也不称这些示例是最新模型榜。

## 输入与身份

输入采用 strict JSON：对象只接受下表字段；重复 key、重复来源/候选、非有限数字或 bool 分数、无时区日期、未知字段均拒绝。

| 对象 | 必须字段与语义 |
|---|---|
| 顶层 | `schema_version="1.0"`；非空 `task_category`；至少两个唯一配置 ID 的 `models`；非空 `sources`。候选集合在比较前声明，不按结果逐模型增删来源。 |
| source | `source_id`、`family`、`category`、`url`、`retrieved_at`、`as_of`、`revision`、`metric`、`direction`、`protocol`、`observations`。URL 为无用户凭据的 HTTPS；`retrieved_at` 带时区；`as_of` 为上游日期标签（YYYY-MM-DD）或 null，具体是页面日期还是源提交日期在 protocol 说明；`revision` 为来源版本或 null，其余描述字段为非空字符串。 |
| observation | `model_id` 必须属于声明集合且在该源中唯一；`label` 保留上游原名；`configuration` 保留模型版本、推理档位、harness、尝试/预算条件和未知；`score` 保留原指标数值或 null。来源未列该配置时可缺行。 |

一个 ID 表示**完整受测配置**，不是模型系列。不同推理档位、harness 或版本应有不同 ID；只有有来源证明是同一配置才可在不同 source 中复用。不存在自动别名匹配，不把 GPT 5 的分数赋给 GPT 6，也不把榜单标签当成本会话实际运行身份。身份不能对应时保留缺行或 null。

`family` 用于避免同一基准、镜像、过滤视图或重叠组合重复计权；每个 family 只接受一个 source。字段由整理者声明，工具不能证明不同 family 独立、来源真实或配置可比。整理前核对任务和协议，已知共享样本的多个榜单选择一个代表来源或保持分开展示，不能靠改 family 名绕过去重。`category` 的精确匹配也只是声明过滤，不证明能迁移到本仓审核。

## 计分与缺失

1. 每个匹配 category 的 source 必须覆盖整个声明集合。缺一行或任一分数为 null，标为 `incomplete_panel`；保留原数值和未知，不在缩小后的集合中重排。
2. 完整来源按 `direction=higher|lower` 排名。并列取平均名次 `r`，集合大小 `N`，参考分为 `100 × (N-r)/(N-1)`；全部并列为 50。
3. 每个配置的总参考分为各匹配来源参考分的中位数，每个声明 family 一次。先用未舍入分数汇总，显示保留两位小数；不直接平均百分比、Arena 分数等不同量纲。
4. 任一匹配来源不完整，**整个集合的总分为空**，完整来源的组件仍显示；全部来源类别不匹配时为 `out_of_scope`。避免不同配置用不同来源集合得到不可比较的总分。

这是一条透明的启发式排序规则，未验证最优性或跨基准迁移；它丢弃分数间距，也不使用统计显著性。0/100 仅表示该集合相对末位/首位，不是无能力/必然成功，也不是全榜百分位。候选或来源集合改变，分数含义随之改变；小集合和区间重叠尤其要连同原数值及配置一起看。不会输出可接受阈值、先验样本量或冷启动成功概率。

输出保留所有 source 原字段、各来源状态、组件、总分和原输入 bytes 的 `input_sha256`。该 hash 绑定整理后的输入，不能认证远端原件。恒定输出 `score_kind=external_rank_reference`、`probability_status=unestimated`、`runtime_identity_status=not_evaluated`、`execution_allowed=false`，权限和账本效果均为 none。结构有效不表示模型适用于专项问题，也不触发执行。

## 来源目录与可比性

| 来源 | 本轮核对的指标和条件 | 初始参考用途与限制 |
|---|---|---|
| [SWE-bench Verified](https://www.swebench.com/verified.html) | 人工筛选的 500 个修复任务；示例取 mini-SWE-agent 2.0.0、一次尝试的 resolved 百分比，行日期为 2026-02-17/19。 | 修复配置的外部参考；Bash Only 是 Verified 的过滤视图，不另计一份。官方指出 1.x 与 2.x setup 未必可比；修复通过不提供审核缺陷真值。 |
| [Aider Polyglot](https://aider.chat/docs/leaderboards/) | 225 道题；示例用 `pass_rate_2`（至多两次尝试的累计通过率，失败测试反馈后可修复），行日期在 2025-05～08；页面标记更新 2025-11-20。 | 编程/编辑配置的历史参考。`pass_rate_1` 才是首次通过；示例各行 harness/编辑格式不同，分数包含这些条件，不宣称裸模型能力或独立重复试验。 |
| [Arena WebDev](https://arena.ai/leaderboard/code/webdev) | 页面日期 2026-10-08；保留完整标签、原 score、显示区间及 votes；区间置信水平未知。 | 运行网站的用户偏好参考；不提供本仓代码审核概率。Text 与 WebDev 分开展示；旧 WebDev 与重建后的 [Code Arena](https://arena.ai/blog/code-arena) 方法不混合。 |
| [Artificial Analysis](https://artificialanalysis.ai/methodology/coding-agents-benchmarking) | 核对了 Coding Agents Index 方法（页面列 v1.5 / September 2026）；实际分数页面本轮不可读，未获得原件。 | 作为可补来源，当前无分数输入。API 文档示例不是实测分数；不为补分申请账户/key或调用付费服务。综合指数与单项可能重叠，补入前核对。 |

两份固定数据来源：

- [SWE-bench JSON，commit 193160a](https://raw.githubusercontent.com/SWE-bench/swe-bench.github.io/193160a463a435d05cf44a1fa9dc5eac832113c3/data/leaderboards.json)，源文件 SHA256 `83cd949a9582f4dd68b0a07148cd86ff0eae6a05b0f2d2298a8f3717baf89d2d`。源提交日期 2026-09-01，不是各行测量日期；仅摘录四行事实，未复制全部数据或轨迹。[网站源许可](https://github.com/SWE-bench/swe-bench.github.io/blob/master/LICENSE)单列，不借主 benchmark 的 MIT 推定整个网站数据许可。
- [Aider YAML，commit cb6a152](https://raw.githubusercontent.com/Aider-AI/aider/cb6a152e5ee27fbc77ac499d5e628ccd74a5fa2a/aider/website/_data/polyglot_leaderboard.yml)，源文件 SHA256 `85a50b25953512d18ba4bb0c23c0b8e626fcf9a5b52d287644b8a0b44b9535de`。源提交日期 2025-10-04；[benchmark 协议](https://github.com/Aider-AI/aider/blob/main/benchmark/README.md)说明两次尝试与反馈，不能把抓取日期当成新测量。

Arena 没有本轮取得的不可变来源 revision，示例为带抓取时间的少量转录，原件可信度和后续漂移仍须核对。原区间和 votes 保留在 configuration，工具不把它们转换成本仓样本量、误差或质量门。

## 本仓反馈怎样积累

先依据具体专项问题、可用配置身份、既有授权和预算准备机器审核候选；外部参考是附带信息，不单独决定是否追加审核。每轮仍引用固定受审版本、原报告、新增/重复/未裁定问题、作者处理、修复版本与受影响处非作者复核。沿用现有审核记录和 PR 收尾，不新增会话采集或第二结果库。

[审核结果回读工具](review-feedback.md)已可从固定 tracked `HEAD` 的正式账本生成受限反馈摘要，并用 `--reference-input` 将本工具的输入并列展示为 `external_reference`。它保留审核修订、Finding 状态和已有验证原值；task-free 来源另用[公开 PR 回读](pr-feedback.md)，支持同一外部参考输入与下一轮问题准备。两种回读均不认证本仓实际模型配置。

初期并列展示“外部参考”和“本仓可复核事实/未知”。不把 Finding 数、APPROVE、采纳或最终 CI 通过当模型胜率，不将本仓计数与榜单分数直接平均。`model_score_update_status=not_implemented` 明确反馈尚不更新分数；下一轮问题只是来源支持的非评分准备，不自动安排审核。真实反馈满足[方法协议](../superpowers/specs/readonly-confidence-method.md)的身份、目标、机会集/真值、独立组、精度与用途条件后，才评审本仓估计及外部参考的迁移/更新方式。当前概率准入、S2/S3 和 Phase 3 状态保持原结论。
