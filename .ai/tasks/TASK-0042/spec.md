# Task Specification

## 目标

在 `.gitattributes` 中把 `.ai/tasks/**` 整体钉为 `text eol=lf`（并把 6 个二进制 `.coverage` 显式标记为 `binary`），使
`tests/integration/test_acceptance_traceability.py::test_phase_two_historical_hashes_and_current_subject_match_records`
在 `core.autocrlf=true` 的 Windows 检出上通过，且不改写任何已提交 blob。

## 背景与根因

`.gitattributes` 当前只有一条规则：

    .ai/tasks/*/historical-snapshots/** text eol=lf

该规则是为 `tests/e2e/test_phase_02_self_hosting_scenario.py` 按字节校验
`.ai/tasks/TASK-0025/historical-snapshots/h1-fe30565` 下的 bundle 而加的，但它没有覆盖 `.ai/tasks/` 下其余任务证据文件。
`test_acceptance_traceability.py:237` 对该 glob 之外的两个路径做 `read_bytes()` 摘要：

- `.ai/tasks/TASK-0028/evidence-h1-b7c7fb4a.json`
- `.ai/tasks/TASK-0028/action-use-5a3071cd2e446dea89d5b8acb5c6c26399cf69a4ba141da0f3995706bfa28020.md`

在 `core.autocrlf=true` 的 Windows 上这两个文件以 CRLF 检出，工作副本摘要与测试钉住的 LF 摘要不符。已实测：

| 路径 | blob (`git cat-file blob HEAD:…`) | 工作副本 |
| --- | --- | --- |
| `evidence-h1-b7c7fb4a.json` | `4fc5729e…823662`（= 测试期望值） | `476ac2e1…843b2516` |
| `action-use-5a3071cd…8020.md` | `3d420bb8…6eff94`（= 测试期望值） | `970fbe2b…079b52` |

**测试钉住的摘要是正确的**（等于 blob 摘要），错的是检出规则不完整。Linux/LF 的 CI 因此通过。

现状实测（`git ls-files --eol .ai`，共 1027 个跟踪文件）：

- 940 个 `i/lf w/crlf attr/`（无属性、被 autocrlf 转成 CRLF）— 缺口所在
- 21 个 `i/lf w/lf attr/text`（已被现有 historical-snapshots 规则覆盖）
- 60 个 `i/none w/none`（空文件）
- 6 个 `i/-text w/-text`（Git 自动判定为二进制）

## 范围

只修改 `.gitattributes`，新增两条规则：

1. `.ai/tasks/** text eol=lf` — 覆盖全部任务账本与证据文件。
2. `.ai/tasks/**/.coverage binary` — 6 个 coverage SQLite 文件必须保持二进制，排在其后以覆盖前一条。

不修改任何测试、任何期望摘要、任何 `.ai/tasks/` 下的内容。

## 关键安全依据：不会改写任何已提交 blob

已逐个校验 `.ai` 下全部 1027 个索引 blob 的字节：**只有 6 个 blob 含 CR，且全部是 `.coverage`**：

    .ai/tasks/TASK-0001/logs/run-20260821T113252388253Z/.coverage
    .ai/tasks/TASK-0002/logs/run-20260821T114956613507Z/.coverage
    .ai/tasks/TASK-0002/logs/run-20260821T120144843557Z/.coverage
    .ai/tasks/TASK-0003/logs/run-20260821T122553379824Z/.coverage
    .ai/tasks/TASK-0004/logs/run-20260822T121808322845Z/.coverage
    .ai/tasks/TASK-0004/logs/run-20260822T123218334873Z/.coverage

其余 987 个 blob 已经是纯 LF。`text eol=lf` 只规定「索引 LF、工作区 LF」，因此对这 987 个 blob，
`git add --renormalize` 是恒等操作，不可能产生新的 blob。6 个 `.coverage` 由第 2 条规则钉为 `binary`
（= `-text -diff -merge`），与它们当前被自动判定的 `-text` 行为一致，同样不被重写。

这满足任务账本「追加式、不得重写」的治理要求。

## 非目标

- 不覆盖 `.ai/tasks/` 之外的 `.ai/**`（`.ai/policy/**`、`.ai/schemas/**`、`.ai/templates/**`、
  `.ai/mutations/**`、`.ai/repository-id`，共 34 个文件）。已核查：没有任何测试对它们钉住跨平台字节摘要——
  `test_mutation_runner_contract.py`、`test_gate_parity.py`、`test_observation_parity.py` 都是
  「同一次运行内 before == after」的自洽校验，与行尾无关；`test_contracts.py` 对 `.ai/repository-id`
  用 `splitlines()`，CRLF 下同样成立。且 `.ai/policy/**` 与 `.ai/schemas/**` 本身在升级清单上，
  纳入会无谓扩大本决策单元的风险面（AGENTS.md 规则 8）。
- 不改动 `core.autocrlf`、不改动仓库或用户的 Git 配置。
- 不修改任何测试代码或期望摘要。
- 不为 `.ai/tasks/` 之外的其他目录（`docs/`、`tests/`、`src/`）新增行尾规则。

## 验收条件

1. `git check-attr text eol -- .ai/tasks/TASK-0028/evidence-h1-b7c7fb4a.json` 报告 `text: set`、`eol: lf`；
   对上述两个被摘要的路径均如此。
2. `git check-attr text -- <6 个 .coverage>` 全部报告 `text: unset`。
3. 先提交 `.gitattributes` 与本任务账本，再执行 `git add --renormalize .`，其后
   `git diff --cached --stat` **完全为空**——没有任何 blob 被改写。（先提交是为了让这条检查无歧义：
   否则本任务自身的改动也会出现在 staged diff 里。）
4. 用 `git rm --cached -r . && git reset --hard` 按新规则重新检出后，
   `git ls-files --eol .ai/tasks` 中不再出现 `w/crlf`。
   注意：`--renormalize` 只修索引，不会刷新工作区，必须重新检出才能让 Windows 上的既有工作副本生效。
5. 在 Windows（`core.autocrlf=true`）上
   `uv run --locked python -m pytest tests/integration/test_acceptance_traceability.py -q` 全部通过，
   特别是 `test_phase_two_historical_hashes_and_current_subject_match_records`。
6. 在 Windows 上 `uv run --locked python -m pytest -q` 全量通过，且与改动前相比不新增任何失败。
7. `git status --porcelain` 中不出现 `.coverage` 被修改。
8. 最终 diff 只含 `.gitattributes`。

## 禁止动作

`push`、`merge`、`deploy`、`delete`、`secret_export`、`paid_external_call`。
另：不得修改测试期望摘要，不得重写任何已提交 blob，不得改动 `.ai/tasks/` 下的任何文件内容。

## 错误行为

- 若 `git add --renormalize .` 产生任何 staged 改动，说明存在含 CR 的文本 blob 会被重写：立即
  `git reset` 撤销暂存，停止并升级，不得提交。
- 若任何 `.coverage` 在检出或 renormalize 后发生变化，说明二进制豁免未生效：停止并升级。
- 若全量测试在改动后出现改动前不存在的失败：停止并升级，不得通过修改测试掩盖。

## 回滚

改动完全可逆：还原 `.gitattributes` 的新增行，再用 `git rm --cached -r . && git reset --hard`
重新检出即可恢复原有行尾。因为全程不产生任何 blob 改写，回滚不涉及历史重写，也不触及任务账本内容。
