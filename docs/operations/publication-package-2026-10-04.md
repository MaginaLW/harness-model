# 本地记录的干净发布工作包：2026-10-04

## 2026-10-08 发布 A 的固定文档内容核定（准备）

所有者已选择 A：整合私有账本及必要源码。新整合目标 TASK-0069 已实际创建，规格和独立 Design 记录提交为 `c9e0132933f894ed5c684af08952fd535e863fc5`；当前原生 status 为 WAITING_FOR_SPEC_REVIEW，仅缺 `spec_approval`。这不构成 publisher 准入、完整验证或远端动作授权。

本次内容审查只绑定文档候选 `81e664809cd052486db878f68dbf00791a42d50b` 相对固定公开基线 `db3efabab562971aef1a6eb1317b679d42eeadb9` 的 15 份文档。主工作区后继 `0e663791a724d19a75e1b0c0b5876a9d0984bb4d` 的变化不在该次准入范围；上述基线也不是本次重新查询的远端最新 HEAD。

三组独立内容审查覆盖全部 15 项：13 份为 `ADMIT_AS_FIXED_HISTORICAL_DOCUMENT`，只准入固定历史文字，不将旧“当前”摘要用作现在的 native、CI 或验收结论。两份原件因精确私有会话定位符和截短 preflight locator 保持暂不公开：

- `docs/operations/zcode-next-stage-assignments-2026-10-02.md`：四个会话定位符，共八处。
- `docs/operations/zcode-report-recovery-2026-10-03.md`：五处会话定位符及两处八位十六进制 preflight 片段。片段未被认定为完整凭据。

两份普通文档已有 runtime 公开派生稿，原件不变。派生稿明确标注源提交、原 Git OID/SHA 和非原字节性质，以一致的逻辑来源占位符替换 13 处会话定位符、两处 token 片段，三个表头说明占位符；其余正文及 FAILED、SPENT、取消、未验收与权限限制保留。派生稿不是 Task63/65 evidence 等暂不公开原件的同路径变换替代，也不是 F 真实报告。

| 派生稿逻辑文件 | 实际字节数 / SHA256 | 当前身份 |
| --- | --- | --- |
| `doc-12.public.draft.md` | 10899 / `b8da64189403212baea5580b8aa1ed8c46d9f6469f44122adfef2e744e475bb6` | 普通文档派生准备稿，尚无 stored Git OID。 |
| `doc-13.public.draft.md` | 35559 / `0900014dc6b87881ef0e32fa62481aed1090736eaf8a2f79406feec5ebf1ae09` | 普通文档派生准备稿，尚无 stored Git OID。 |

原 15 文档输入包为 `${RUNTIME_ROOT}/publication-A-frozen15docs-admission-input-001`，manifest SHA `2ecf8669763b2bc46e078362d3f4144bd5175d599b4814e68c80fcd5bef294ed`。三组审查包 `publication-A-frozen15docs-admission-group-a-001`、`publication-A-frozen15docs-admission-group-b-001`、`publication-A-frozen15docs-admission-group-c-001` 的 manifest 分别为 `e062b2aed75d4e617b4d7efa33335f2858d4868236dbdad9a40e85238f1f367f`、`8b2666304f273cd35c5d7fbe211f36e39ce76073c2a374e1b51cd5bc684657b4`、`c7d237a3e3d3006756da9b9a10848431fd6c0f63358ad6d839266bf55f412da0`；Root 核对全部成员、SHA、长度及 stored Git blob OID，15 项没有重复或缺项。完整字节扫描与实际语义阅读覆盖在各报告分开记录，不声明绝对无秘密或全部行均人工阅读。

派生准备包为 `${RUNTIME_ROOT}/publication-A-frozen15docs-public-derived-proposal-002`，manifest SHA `7deeb0b63c461042c915ba3609172c29b02a2b84dedaf074d7c3cf40d3fd39f9`；首次表头数量准备错误及空输出原件在 `publication-A-frozen15docs-public-derived-proposal-001` 保留，不是业务验证重试。两路独审分别核对事实语义与最小字节变换，均为 `ADMIT_DERIVED_DOCUMENT_CONTENT_PREPARATION_ONLY`，发现项为零。Root 已核对输入、派生包、两个回执的完整成员、SHA 和长度；派生内容准入不改变两份原件的暂不公开结论。

| 独审包（位于 `${RUNTIME_ROOT}`） | `review.json` SHA256 | manifest SHA256 |
| --- | --- | --- |
| `publication-A-frozen15docs-derived-semantics-independent-review-001` | `c27d1019dfc1234ce64fb3aaecb0343661d55532b8e1f76edb75515a0b9b1ceb` | `d5e16cb16735850752c8904b3681188d4d548262a6668978e431120731aea975` |
| `publication-A-frozen15docs-derived-bytes-independent-review-001` | `b3f10e941bb3b8bea4e04f464771bf42bccbb931c0b4ba728600f85aab9dadd6` | `5a7a7b28b66b17201c1d0a104ab57f96192f36e947a7097d61e9ba0ba1ee84ae` |

静态链接盘点仅覆盖 320 个 Markdown 内联引用：116 个目标存在于固定公开基线，129 个仅存在于固定文档候选，75 个外部 locator 未获取。片段正确性、代码/纯文本引用、私有 archive、新投影及新 catalog 的实际可得性未由此证明。原报告、会话、token 与私有 recipe 不随文档内容准入导出。

后续仍须完成 TASK-0069 所需的实际批准与实现，逐值审查实际 NONnative catalog，绑定后继普通文档版本，以及固定累计候选的完整规定检查、85% 总覆盖率和原生/公开累计 base 各自的 90% diff coverage。Action005 已消费且整体 FAILED；既有 CI、局部通过及本次文档准入不替代这些门。publisher、具体 push/merge 授权及远端证明尚未完成。

以下 2026-10-04 文本保留为早期仅文档发布路径的历史材料，其范围与远端查询窗口不作为方案 A 的当前准入或授权。

本页落实[待办第 7 项](follow-up-backlog-2026-09-22.md#2026-10-04-收尾核定与下次待办)的静态发布清单。
只读核验和材料准备已完成；尚未创建 publisher Task、工作区或发布候选，未 cherry-pick、
更新 refs、推送、写入 PR 或合并。实际候选及其新批准、完整验证和远端证明仍待执行。

## 准确基线与当前远端事实

本次只读 GitHub API 核验确认 `main` 为
`db3efabab562971aef1a6eb1317b679d42eeadb9`；本地 `origin/main` 与之相同。
新干净候选应从该准确提交创建，创建和外部动作前仍须重读远端事实。
本地 `main@48bf777106b9fdfef1ddf83d3abc95859fb8e580` 已落后，不能代替此基线。

[PR #44](https://github.com/MaginaLW/harness-model/pull/44) 为 MERGED：
原准确 head 为 `f5707ff178b760bb0215c7d5cb773cc4d06c75d6`，
merge commit 为上述 `db3efab`，merged_at 为 `2026-10-01T23:36:09Z`。
该 head 的 `ai-quality-gate` 为 COMPLETED / SUCCESS，
见[原 required CI](https://github.com/MaginaLW/harness-model/actions/runs/36939643115)。
旧 CI 只覆盖原候选，不覆盖本页的新工作包。

实时 main 保护仍要求 strict `ai-quality-gate`，app ID `15368`；
enforce admins、conversation resolution 开启，force push 和 deletion 禁止。
本次未改变保护设置。

核验时主检出为 `codex/e4-followup-status@f9deb7b10983084cf58df78c23ac2b1dafb263f5`，
相对 `origin/main` 领先 25、落后 0。不能直接发布该分支，因为其历史包含本地配置提交 524。
三份既有未跟踪用户计划保持原状；本轮新的执行文件另见[本轮执行入口](backlog-execution-2026-10-04.md)。

## 必须排除的提交与文件

以下五项不进入新候选，主检出的原历史继续保留：

| 提交 | 排除原因 |
| --- | --- |
| `52474d93101d387ccca853debbe6fdcc7f565c8d` | 本地并发配置及关联说明；`.codex/config.toml` 和 `docs/operations/model-selection.md` 均保持新远端基线的原值。 |
| `ab1a0880f8c1e1ae87586d2ba955e8797ea14873` | 此文档 patch 的内容已经存在于当前远端文档，不重复引入。 |
| `9c089a87fa22214aaafcf80dbe5945449f9c5d0e` | 此文档 patch 的内容已经存在于当前远端文档，不重复引入。 |
| `17196c28423b0fce234c9955663953dbc594293b` | 此文档 patch 的内容已经存在于当前远端文档，不重复引入。 |
| `df3bfd19616159d789e0d7e137f5e21df87553e2` | 主检出的本地整合 merge 会带入配置 524 祖先，不用于发布。 |

不从 `codex/f-real-import-acceptance` 或 `codex/git-context-read-protocol` 合并生产、测试、
Task 准入或失败恢复改动；私有 Windows 修复源码也不在本包。
完整本机 candidate、bundle、native evidence、raw streams、运行时 receipt、私有日志和缓存均不入库。
三份既有用户计划、旧分支及原件不移动、不删除。

## 最小完整累计范围：8 份文档与 24 个历史路径

这是相对准确新基线的 32 个原路径；后续新 publisher 自身治理记录须另列实际精确 scope。
它排除本轮七份准备文档、本轮权威入口追加和新区安全测试。若新发布决定纳入这些后继
成果，必须重列实际累计 scope/base/head，完成相应 classify/freeze、独立 Review 和
准确候选验证，不能沿用本页静态 32 路径或旧候选批准。
不包含生产源码、测试、配置、workflow、Policy 或 schema 改动。
文档和历史记录共同组成包，避免文档指向未发布的 Task62 closeout 或 Task47 dispatch。
只发布原有历史事实，不新增付费调用或重复闭账。

八份文档：

```text
docs/operations/f-real-import-acceptance-2026-10-03.md
docs/operations/follow-up-backlog-2026-09-22.md
docs/operations/maintenance-status.md
docs/operations/next-stage-start-conditions-2026-10-02.md
docs/operations/windows-private-timeout-repair-2026-10-04.md
docs/operations/zcode-next-stage-assignments-2026-10-02.md
docs/operations/zcode-report-recovery-2026-10-03.md
docs/superpowers/plans/2026-09-23-e4-follow-up-work-plan.md
```

24 个既有历史路径：

```text
.ai/tasks/TASK-0047/action-paid-zcode-next-stage-preparation-2026-10-02.json
.ai/tasks/TASK-0047/approvals.json
.ai/tasks/TASK-0047/events.jsonl
.ai/tasks/TASK-0047/task.yaml
.ai/tasks/TASK-0047/zcode-next-stage-dispatch-2026-10-02.md
.ai/tasks/TASK-0054/events.jsonl
.ai/tasks/TASK-0054/task.yaml
.ai/tasks/TASK-0055/events.jsonl
.ai/tasks/TASK-0055/task.yaml
.ai/tasks/TASK-0056/events.jsonl
.ai/tasks/TASK-0056/task.yaml
.ai/tasks/TASK-0057/events.jsonl
.ai/tasks/TASK-0057/task.yaml
.ai/tasks/TASK-0062/actions/merge-001.json
.ai/tasks/TASK-0062/actions/pr-update-001.json
.ai/tasks/TASK-0062/actions/push-001.json
.ai/tasks/TASK-0062/approvals.json
.ai/tasks/TASK-0062/closeout-001.md
.ai/tasks/TASK-0062/events.jsonl
.ai/tasks/TASK-0062/operator-receipts/merge-001.json
.ai/tasks/TASK-0062/operator-receipts/pr-update-001.json
.ai/tasks/TASK-0062/operator-receipts/push-001.json
.ai/tasks/TASK-0062/publication-actions-001.md
.ai/tasks/TASK-0062/task.yaml
```

这些历史文件只复制来源已封存的 Git blobs，不重新生成 approvals、events、task materialization
或 action receipt，不改旧批准、时间、subject/base、spec 或失败结论。
新基线到既有记录的差异表示发布原先仅本地追加的事实；不执行任何旧 Task 状态迁移。
TASK-0047 的付费动作历史是已发生事实，不成为本次或后续新付费动作授权。

## 20 个按顺序选取的静态提交建议

从准确新基线构造时，建议依次选取下列原提交；本次未运行 cherry-pick，
不宣称无冲突或最终树已通过验证。第一项的 docs 树与当前 `origin/main` 相同，
其变化为原闭账记录，后续链条承接文档和分配历史。

```text
84029ccabf6ea607c748c233615e6f0b8d53f407
a402d660666c3d8e2a7baf71c4dad82f6ed1f513
cfec0779f52a267f6bfe0fdfee71344ab7d68aa4
8ba37b6037d4da5721cdc8e0d79589df24c7ac39
6e1ba4a0cb8d66810295ba824b79e19ddfc1993f
ed4b3e7a57d785b57670eed47170944e3532a832
3d6528284bc6e867def4fc8139ef67a41544ae48
f5421a2ff048b5090504b9f5452fffa555e1ec75
96d51c0277518a46753a1631ade22812b563757a
fc7494b67221e71ad4e110e5d89c91adfe305b04
82a59e1341ddb717b2151c5030d39091915b5222
ef48db3b76a532935e10251771d31f4b7d946b3a
574fb806611e1ab9c1e54e603cc1cc0303988504
97b0c85726536b3aa265eb1bcb20f04485e598f5
123b7b3037396deb042e5d0e36910d508a89913d
9585c64fc359fe1bc93dcd4ba0171176a64b042f
13e8424ecc93df7a01311237636820c409daa77b
1ff6e964f7f0944176c420ca55a57b885272f325
bf7ae55faa3efc0e4f6364927bdd257afc72c273
f9deb7b10983084cf58df78c23ac2b1dafb263f5
```

整合后须逐路径核对原 blobs、累计 diff 和文档链接。若需解决冲突，只按已核对的来源原字节
恢复该路径，不编辑失败/批准记录来使检查通过；未知或冲突停止相应步骤并留存原件。
旧主检出和分支始终提供原来源恢复路径；本次不清理它们。
候选须明确证明配置 524 非祖先，配置及 model-selection 的 blobs 与准确新基线一致，
而选中的便携记录符合上述累计清单；禁止整分支 merge 或强制推送来绕过范围核验。

## 新 publisher 的准入与完成条件

外部发布和任务账本属于 [AGENTS.md](../../AGENTS.md) 的 AI Flow 升级清单。
后续真实分配新 publisher Task，固定准确 source/base/head 与上述累计 scope，
另列其自身治理路径、实际外部动作和禁入项。按当前 CLI/Policy classify、freeze，
完成真实独立审核及所选完整原生检查；请求人类决定前先读 status，只补实际 `Missing:`。
不以旧 publisher 或失败目标代替新准入，不重复索取系统判为 current 的既有批准。

候选构造、统一提交及 native 验证串行；准备与只读审核可启用 2 名 sub-agent，
分别承担候选累计范围/便携性审核与独立远端动作/保护事实核验，均不改旧 Task。
实际 exact-head Gate、push、PR 写入、完整 CI、保护 merge 和远端证明按依赖串行。

每项实际高风险动作须绑定具体候选和最新远端事实，并核对覆盖该动作的真实批准：

1. Push：准确 repository、feature ref、expected predecessor、head、唯一有效 push URL
   和普通 non-force 参数；确认 524 排除，禁止隐式 tags 或额外 ref。
2. PR 创建或更新：准确 base/head、标题和正文内容；对本工作包取得对应动作批准并保留真实回读。
3. Merge：仅在新准确 head 的 required CI 完整成功、当前批准/Gate 有效且保护未降低后，
   执行普通保护合并；merge 动作独立绑定具体 PR/head/base，不复用 PR #44 旧动作。

本轮用户的整体推进授权应先按实际动作参数核对适用范围；笼统权限不改写旧一次性 action。
部署、删除、凭据导出、付费调用及 provider 执行不在本发布包。
CI 保持完整测试、85% 总覆盖率、90% 累计 diff coverage、whitespace、Ruff、format、mypy，
不调整原选择器、预算或阈值。新准确 head 的完整 required CI 和真实远端证明是完成条件；
本地 Gate、旧 CI 或文档记录不能代替。

合并后独立核对 PR merged、准确 merge parents、树、来源/候选祖先、远端 main 和 524 排除。
只能对成功的新 publisher 按真实结果做自身 native close，不重复 close 旧任务。
后续动作和关闭回执作为本地追加，不递归派生下一轮发布。

## 保留的终态与证据边界

主检出原账本核验 TASK-0054/0055/0056/0057/0062 均已 MERGED，五项不重新闭账。
TASK-0053 保持 push-only；0058/0059/0060 的三个准确 head CI 失败、0061 的原生 FAILED
保留，不因新成功变为 MERGED。
TASK-0063 的 BLOCKED、TASK-0064 的 FAILED / SPENT 和 TASK-0028 Option C 依据各自原记录
保留，不能借本发布包或新 CI 验收生产修复、完整预算或 F。
状态和动作解释见[当前维护状态](maintenance-status.md)、
[原件回收记录](zcode-report-recovery-2026-10-03.md)及
[私有 qualification 限制](windows-private-timeout-repair-2026-10-04.md)。

八份文档使用占位符、basename、相对引用和摘要；针对所选文档与历史路径的
本机绝对路径/用户名扫描未发现命中。该检查仅覆盖列明文件，不认证全部私有材料。
便携摘要不替代原 native evidence；私有原字节继续保留，不能由发布、格式化或
Git 换行规范化重写。文档中的线上历史窗口按原时间解释，外仓业务不属于本次发布验收。
