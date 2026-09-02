# Review Package

## 审核目标

裁决 subject `344faf9fc1024fc469daa774a6d6511646a13798` 是否可以获得 code approval：把 CI 任务解析的变更集合从两点 `git diff base head` 改为以 merge-base 起算的三点 `git diff base...head`。

## 背景

正式 CI 的 `Resolve task` 步骤用 base→head 的变更集合推断本次 PR 属于哪个 AI Flow 任务，要求恰好命中一个 `.ai/tasks/TASK-*` 目录。两点 diff 比较的是两棵树，而不是该 PR 引入的变更。当 base 分支合入了另一个任务的记录后，那个任务目录会作为 head 侧变更出现，解析随即失败。

实际发生的故障：PR #4 在 head `7719796` 上，run `33571530225` 通过；main 合入 TASK-0034 后，同一个 head 的 run `33621586978` 以 `base-to-head diff must identify exactly one .ai/tasks/TASK-* directory` 失败。head 未发生任何变化，唯一变量是 base 前移。

## 代码地图

- `tools/ci/resolve_task.py` — `_git_paths` 调用 git 得到变更路径；`resolve_task_id` 在其上做显式 `AI_FLOW_TASK_ID` 优先、否则要求唯一命中的判定。
- `.github/workflows/ai-quality-gate.yml` — `Resolve task` 步骤以 `github.event.pull_request.base.sha` 与 `head.sha` 调用该工具，输出 `task_id` 供后续 `verify --ci` 与 `gate` 使用。本任务不修改该文件。
- `tests/integration/test_github_workflow.py` — 既有 `test_diff_task_resolution_requires_exactly_one` 覆盖 0/1/2 个目录；本任务新增两个分叉历史的回归测试。

## 语义变更

`_git_paths` 由 `git diff --name-only -z <base> <head>` 改为 `git diff --name-only -z <base>...<head>`。变更集合的起点从 base 提交本身改为 base 与 head 的 merge-base，因此结果只包含 head 侧引入的变更，不再包含仅存在于 base 的内容。

不变部分：显式 `AI_FLOW_TASK_ID` 的优先级、格式校验与目录存在性检查；零个或多于一个任务目录时的拒绝路径与原错误文案；subprocess 超时与非零返回码的处理；`TASK_PATTERN` 匹配规则。

## 风险

- **merge-base 缺失或不可达**：`git diff` 返回非零，沿用既有 `ValueError` 路径失败关闭，不会退化为「解析成功」。
- **判定被放宽**：三点形式严格收窄路径集合，不会新增候选，因此不会把本应拒绝的多任务 PR 放行；新增的第二个回归测试专门锁定这一点。
- **遗漏 head 侧删除**：若某 PR 的唯一变更是删除一个任务目录，两种形式都会命中该目录，行为不变。
- **对既有通过记录的影响**：本改动不触及任何任务的证据、Policy 或 Gate 语义，不会使既有 evidence 失效。

## 证据

已验证：

- V1 完整验证在 subject `344faf9` 通过，十项必需检查全部 `passed`，含完整回归、85% 总覆盖率与 90% diff coverage。
- `aiflow scope TASK-0035` 通过，改动仅限 `tools/ci/resolve_task.py`、`tests/integration/test_github_workflow.py`、`CHANGELOG.md`。
- 真实故障场景直接复核：`git diff --name-only 5e49a28 7719796` 给出 `TASK-0032` 与 `TASK-0034`；`git diff --name-only 5e49a28...7719796` 只给出 `TASK-0032`。
- 独立实现审核 REV-0071 无 finding。

复现命令：`python -m aiflow verify TASK-0035 --actor <ACTOR>`。

仍未验证：本地未在 GitHub Actions runner 上重放 `Resolve task` 步骤；该步骤在真实 PR 上的表现需由合并后的下一次 CI 运行确认。

## 审核问题

1. 三点 diff 是否正确表达了「本 PR 引入的变更」这一既有契约，而非改变契约？——是。工具文档与 workflow 意图均为按 PR 变更定位任务，两点形式是实现偏差。
2. 该改动是否可能放行本应被拒绝的 PR？——否。路径集合严格收窄，多任务拒绝路径由新增回归测试锁定。
3. 是否触及门禁强度、required check、阈值或运行期行为？——否，均未修改。

## 推荐结论

APPROVE。缺陷有真实 CI 证据支撑，修复与既有契约一致且严格收窄判定，范围受控、可逆，V1 十项检查全部通过，独立审核无 finding。
