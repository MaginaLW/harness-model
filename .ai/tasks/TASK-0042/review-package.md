# Review Package — TASK-0042

## 审核目标

裁决是否给予 code 批准：`.gitattributes` 新增两行检出规则，使
`tests/integration/test_acceptance_traceability.py::test_phase_two_historical_hashes_and_current_subject_match_records`
在 `core.autocrlf=true` 的 Windows 上通过，且不改写任何已提交 blob。

## 背景

`.gitattributes` 原先只有一条规则 `.ai/tasks/*/historical-snapshots/** text eol=lf`，它是为
`tests/e2e/test_phase_02_self_hosting_scenario.py` 的 bundle 字节校验而加的，未覆盖 `.ai/tasks/` 下其余
任务证据文件。`test_acceptance_traceability.py:237` 对该 glob 之外的两个 TASK-0028 文件做 `read_bytes()`
摘要，它们在 Windows 上以 CRLF 检出，摘要因此与测试钉住的值不符。Linux/LF 的 CI 不受影响。

## 代码地图

- `.gitattributes`（唯一的非账本改动，subject `91563b1`）
- 依赖此规则的测试：`tests/integration/test_acceptance_traceability.py:237`、
  `tests/e2e/test_phase_02_self_hosting_scenario.py:76/142/153`
- 被钉住的数据：`.ai/tasks/TASK-0028/evidence-h1-b7c7fb4a.json`、
  `.ai/tasks/TASK-0028/action-use-5a3071cd…8020.md`
- 二进制豁免对象：`.ai/tasks/*/logs/run-*/.coverage`（6 个 SQLite）

## 语义变更

新增：

    .ai/tasks/** text eol=lf
    .ai/tasks/**/.coverage binary -eol

前者把整个任务账本的检出行尾钉为 LF（原先仅 `historical-snapshots`）；后者把 6 个 coverage SQLite
显式标记为二进制并清除 `eol`，排在后面以覆盖前一条。索引内容语义不变——987 个文本 blob 本来就是纯 LF。
工作区语义改变：Windows 上 934 个文件由 CRLF 检出变为 LF 检出。

## 风险

| 风险 | 影响 | 缓解 | 状态 |
| --- | --- | --- | --- |
| 误把二进制当文本导致 blob 被改写或文件损坏 | 高 | 第 2 条规则 `binary -eol`；`git check-attr` 实测 6 个 `.coverage` 为 `text: unset` / `eol: unset` | 已缓解并实测 |
| renormalize 改写既有 blob，破坏账本追加式要求 | 高 | 只读预检遍历 `.ai` 全部 1027 个索引 blob，仅 6 个含 CR 且已豁免；提交后 `git add --renormalize .` 的 staged diff 完全为空 | 已缓解并实测 |
| 既有 Windows 工作副本不自动生效 | 中 | 需 `git add --renormalize .` 或重新检出；本工作树已用 `git rm --cached -r . && git reset --hard` 刷新 | 已知，需告知其他贡献者 |
| 范围过宽波及治理面文件 | 中 | 范围限定 `.ai/tasks/**`，不含 `.ai/policy/**`、`.ai/schemas/**` 等 34 个文件 | 已缓解 |

## 证据

**已验证：**

- 改动前 Windows 基线：`1 failed, 1613 passed, 4 skipped`，唯一失败即本缺陷。
- 改动后：`1614 passed, 4 skipped`，无新增失败，跳过项仍为原有 4 个 symlink 相关。
- 两个被摘要文件的工作副本摘要现等于测试钉住的 blob 摘要
  （`4fc5729e…823662`、`3d420bb8…6eff94`）。
- 提交后 `git add --renormalize .` 的 `git diff --cached --stat` 完全为空：**零 blob 改写**。
- 重新检出后 `git ls-files --eol .ai/tasks`：934 `i/lf w/lf attr/text`、60 空文件、
  6 `i/-text w/-text attr/-text`，**无 `w/crlf`**。
- 6 个 `.coverage` 仍以 `SQLite format 3\x00` 开头，`git status` 中未被修改。
- V2 验证 14/14 全部通过（`local` 模式，subject `91563b1`，快照
  `9a8fc38202d20cbb361f2ba0f9dc2b15088057077927bef001a3c386fb839eb9`）。
- `targeted_mutation`：`MUT-V2-001`..`MUT-V2-005` 全部 `killed`；变异源码已全部还原，
  `git status` 无 `src/` 改动；action 已消费并生成 receipt
  `action-use-60936520…d4b5.md`。
- `unverified_scenarios: []`；`aiflow scope` 通过，最终 diff 只含 `.gitattributes` 与本任务账本。

**复现命令：**

    git check-attr text eol -- .ai/tasks/TASK-0028/evidence-h1-b7c7fb4a.json
    git add --renormalize . && git diff --cached --stat   # 期望为空
    git ls-files --eol .ai/tasks | grep w/crlf            # 期望无输出
    uv sync --locked --all-extras && uv run --locked python -m pytest -q

**仍未验证：**

- 未在 `core.autocrlf=input` 或 macOS 上实机验证。规则为显式 `eol=lf`，不依赖 `autocrlf`，
  预期一致，但本任务未实测，不作已确认表述。
- 未验证其他贡献者既有 Windows 工作副本的迁移体验（需各自 renormalize 或重新检出）。

## 审核问题

1. 范围限定 `.ai/tasks/**`、不纳入 `.ai/policy/**` 与 `.ai/schemas/**`（依据 AGENTS.md 规则 8
   避免扩大决策单元风险面），是否接受？
2. 用 `binary -eol` 而非仅 `binary` 豁免 6 个 `.coverage`（显式清除 `eol`，不依赖属性优先级细节），
   是否接受？
3. 「零 blob 改写」的证据链（只读全量 CR 预检 + 提交后 renormalize 空 diff）是否足以满足任务账本
   追加式、不得重写的治理要求？
4. 是否接受把「既有 Windows 工作副本需 renormalize 或重新检出」的操作说明留到单独的低风险文档任务，
   而不并入本治理面单元？

## 推荐结论

**APPROVE。** 缺陷根因明确且已消除，测试钉住的摘要未被修改（它们本就正确），零 blob 改写已由只读预检与
提交后 renormalize 空 diff 双重证实，V2 十四项检查全部通过，最终 diff 只含 `.gitattributes` 与本任务账本。
