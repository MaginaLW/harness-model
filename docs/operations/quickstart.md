# AI Flow Quickstart

本指南从干净 `git clone` 开始，默认只在当前克隆内创建虚拟环境和演示任务记录。它不执行
commit、push、merge、deploy 或任何外部动作。项目要求 Python 3.11 或更高版本；推荐使用
仓库根目录已提交的 `uv.lock` 建立可复现环境，同时保留标准 `venv` + `pip` 回退路径。

<!-- required-path: pyproject.toml -->
<!-- required-path: .ai/policy/routing.yaml -->
<!-- required-path: tests/unit/test_specification.py -->
<!-- verify-command: python -m aiflow --help -->
<!-- verify-command: python -m pytest tests/unit/test_specification.py -q -->

## 推荐：使用锁文件安装

先运行 `uv --version` 确认工具可用；未安装时按
[uv 官方安装说明](https://docs.astral.sh/uv/getting-started/installation/)选择适合本机的方式，
本项目不要求全局 Python 包安装。

`uv sync --locked --all-extras` 会在仓库内创建或更新 `.venv`，安装项目及开发依赖，并在
`pyproject.toml` 与 `uv.lock` 不一致时直接失败。后续命令显式调用项目解释器，不依赖环境
是否已激活，也不会误用系统 Python。`uv sync` 默认执行精确同步，可能移除 `.venv` 中未被
锁文件声明的额外包，因此应为本项目使用仓库自己的 `.venv`，不要指向共享环境。

### PowerShell

```powershell
git clone <REPOSITORY-URL> harness-model
Set-Location harness-model
uv lock --check
uv sync --locked --all-extras
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m aiflow --help
```

### macOS/Linux

```sh
git clone <REPOSITORY-URL> harness-model
cd harness-model
uv lock --check
uv sync --locked --all-extras
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q
.venv/bin/python -m aiflow --help
```

## 无 uv 时的标准安装

若本机没有 `uv`，可使用 Python 自带的 `venv`。editable 安装会让仓库中的 `src/aiflow`
直接成为当前虚拟环境的命令实现；它不会把 `aiflow` 安装到系统 Python。

### PowerShell

```powershell
git clone <REPOSITORY-URL> harness-model
Set-Location harness-model
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m aiflow --help
```

### macOS/Linux

```sh
git clone <REPOSITORY-URL> harness-model
cd harness-model
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q
.venv/bin/python -m aiflow --help
```

如需使用后文较短的 `python -m ...` 命令，可在 PowerShell 运行
`.\.venv\Scripts\Activate.ps1`，或在 macOS/Linux 运行 `. .venv/bin/activate`。激活失败不影响
使用上面的显式项目解释器入口；尤其在 PowerShell 中，无需为了本项目修改系统 execution
policy。

## 环境自检与常见问题

在已有克隆中，可先运行下列只读检查。`--dry-run` 只报告同步计划，不安装、删除或升级包。

```powershell
uv lock --check
uv sync --locked --all-extras --dry-run
.\.venv\Scripts\python.exe -c "import sys; print(sys.executable)"
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m aiflow --help
```

macOS/Linux 将最后三条命令中的 `.\.venv\Scripts\python.exe` 换成
`.venv/bin/python`。

- `No module named aiflow` 通常表示命中了系统 Python。改用项目解释器，或在项目虚拟环境中
  重新执行 editable 安装；不要用全局安装掩盖解释器选择错误。
- `uv sync --locked` 报告锁文件过期时，不要移除 `--locked` 或顺手重写锁文件。先运行
  `uv lock --check`，再将依赖或锁文件变更作为单独受治理任务处理。
- `pip` 的新版本提示不代表项目依赖损坏。以 `pip check`、锁文件检查和项目测试结果为准，
  不需要仅为消除提示而升级项目环境。
- 若 `uv sync --locked --all-extras --dry-run` 计划修改环境，先检查是否使用了仓库根目录的
  `.venv` 和当前 `uv.lock`；确认后再运行不带 `--dry-run` 的同步命令。

## 运行无外部动作示例

1. 创建一个仅允许修改本地演示文档的任务，并保存命令输出的 `TASK-ID`。

```powershell
python -m aiflow start `
  --objective "演示受控的本地文档变更" `
  --allow "docs/quickstart-demo.md" `
  --forbid-action push `
  --forbid-action merge `
  --forbid-action deploy `
  --forbid-action delete
```

```sh
python -m aiflow start \
  --objective "演示受控的本地文档变更" \
  --allow "docs/quickstart-demo.md" \
  --forbid-action push \
  --forbid-action merge \
  --forbid-action deploy \
  --forbid-action delete
```

2. 在首次分类前，编辑 `.ai/tasks/<TASK-ID>/task.yaml` 的决策单元，补齐下列明确事实。当前 CLI 还没有专用的事实录入子命令；缺失任一必需事实时，Policy 会安全地转为 BLOCK。

```yaml
scope: {clear: true}
impact: {level: low}
protections: {verified_backup: true, dry_run: true}
verification: {automatic: true, tools_missing: false}
impact_categories: [documentation]
business_direction_count: 1
change_characteristics:
  mechanical: false
  behavior_changed: false
  code_modified: false
  interaction_scope: local
  regression_risk: false
  error_detectability: high
```

3. 分类并查看只读状态。

```powershell
python -m aiflow classify <TASK-ID> --actor quickstart
python -m aiflow status <TASK-ID> --format json
```

```sh
python -m aiflow classify <TASK-ID> --actor quickstart
python -m aiflow status <TASK-ID> --format json
```

对上述低影响、可逆、无外部副作用的事实，预期 route 为 `AUTO`。若未补齐事实，预期为可解释的 `BLOCK`，应按 [恢复手册](recovery.md) 处理，不直接改写状态。

4. 运行 Gate 以观察具体缺失条件。因为示例没有实施、commit 或验证，这一步应返回非零退出码和 `passed: false`；这是正确的安全拒绝。

```powershell
python -m aiflow gate <TASK-ID> --format json
```

```sh
python -m aiflow gate <TASK-ID> --format json
```

## 只读 observation 示例

`observe` 的输入必须是已经绑定到当前 task、base、subject 与 Policy 的事实；只读 evaluator
还会核对当前 repository/branch/HEAD/ancestry、classification freshness、route/V 与 task state，
因此该输入必须与当前版本一致。新建的空演示任务不能被伪装为可成功观察的输入。已有完整绑定的
任务可用本地 UTF-8 JSON object 和 `dry-run` 重放只读决策：

```sh
python -m aiflow observe <TASK-ID> --input <CURRENT-OBSERVATION.json> --mode dry-run
```

`dry-run` 只接受 `source: "cli"` 的输入且不接受 `--actor`，对完整 task 目录零写。有效的
observation 仍会以 exit 2 返回 `execution_allowed: false`：这是有效、可审计但**非授权**的
结论，不会执行或允许所描述的动作。输入、contract 或 binding 错误返回 exit 1，必须先修复
当前事实，不能借 exit code 或新建空任务绕过它。

## 继续实际任务前

用 `spec.md` 冻结可执行规格，然后按 route 执行 ASK/REVIEW 决定或批准，再运行 `begin`、实施、`sync`、`verify` 和 Gate。所有命令都以 `python -m aiflow ...` 为权威入口；未获单独批准时不执行 push、merge、deploy、delete、凭据或付费外部调用。

## REVIEW 双阶段审核

`REVIEW` 任务的规格批准前，先生成只含规格、Policy、base、分类和决策单元的 design context，由审核者提交结构化结论：

```sh
python -m aiflow review context <TASK-ID> --stage design --output design-context.json
python -m aiflow review record <TASK-ID> --input design-review.json --actor <REVIEWER>
python -m aiflow approve <TASK-ID> --type spec --actor <APPROVER> --reason "design approved"
```

实现、commit、`sync` 和 `verify` 通过后，implementation context 会额外绑定当前 subject、evidence digest、committed numstat 摘要和验证摘要。它不会复制完整 patch、日志或实现对话：

```sh
python -m aiflow review context <TASK-ID> --stage implementation --output implementation-context.json
python -m aiflow review record <TASK-ID> --input implementation-review.json --actor <REVIEWER>
python -m aiflow review show <TASK-ID> --stage implementation --format json
python -m aiflow approve <TASK-ID> --type code --actor <APPROVER> --reason "implementation approved"
```

`review record` 不覆盖历史；需关闭发现时使用 `review resolve` 追加 revision。code approval 仍同时要求现有八节 `review-package.md` 和通过的本地 evidence。

## V2 独立 Verifier 与已完成的 Chapter 11

V2 的 `--actor` 是 task-local 文本标签：会先 trim，再按精确字符串比较。它不代表人员、模型或外部身份认证。当前实现周期的 Implementer 取最近一次 `implementation_started` 或 `implementation_retried` 事件；V2 Verifier 必须提供非空且不同的标签。

V2 采用以下 current-version 绑定顺序：Verifier context → action-approved targeted mutation
artifact 与 pre evidence → implementation review → `verify --finalize` → local code approval →
Gate。context 只携带冻结规格、允许范围、diff 路径/numstat 摘要、验收条件、限制和复现 argv，
不携带实现对话、内部推理、完整 patch、原始日志或凭据。每一项都绑定当前 task、subject、规格、
Policy 与 classification；任一绑定变化后必须从当前版本重建，不能借用其他 task 的 artifact。

```sh
python -m aiflow verify <TASK-ID> --actor <VERIFIER>
python -m aiflow review context <TASK-ID> --stage implementation --output implementation-context.json
python -m aiflow review record <TASK-ID> --input implementation-review.json --actor <REVIEWER>
python -m aiflow verify <TASK-ID> --actor <VERIFIER> --finalize
python -m aiflow approve <TASK-ID> --type code --actor <APPROVER> --reason "local V2 evidence reviewed"
```

active Policy `2.1.0` 下，默认 live V2 在完整 V1 prefix 后，依次执行确定性、离线的
`pytest tests/acceptance -q`、`pytest tests/integration -q`，以及由单独 action approval 绑定的
targeted mutation；三项各自保留真实进程结果、日志与工具版本，independent Verifier 也必须与
Implementer 使用不同的非空 task-local actor 标签。Chapter 11 的 acceptance、integration、
action-approved targeted mutation 与 independent-verifier 流程均已实现。

使用 `--check acceptance`、`--check integration` 或其他局部检查时，只执行所选检查，所得
evidence 是 partial/provisional，不能形成 final evidence 或进入 Gate。`--finalize`、code
approval 和 CI 输出也不能把 missing、stale、tampered、non-killed 或 unverified 的当前 V2
事实变成 passed。CI evidence 只提供 Gate attestation；它不替代当前本地 evidence、
implementation review 或 local code approval。Gate 仍逐项核对这些 current-version 绑定，
不因 Chapter 11 已完成而自动放行任一后续 task。

`begin` 的治理提交兼容仅允许 `subject_commit..HEAD` 中的当前任务路径 `.ai/tasks/<TASK-ID>/**`；业务路径、其他任务路径、仓库/分支不符和超出创建时 dirty baseline 的工作树变化仍会拒绝。

## 阶段二基线重放

阶段二的入口不是某个历史 task 在当前 `HEAD` 上继续显示 merge-ready，而是
[阶段二验收矩阵](../implementation/phase-02-acceptance-matrix.md)和
[阶段二证据索引](../implementation/phase-02-evidence-index.md)中明确区分的两类事实：

- historical/immutable：绑定原 subject 或 attestation 的 review、evidence、mutation artifact、
  receipt 和 Gate 结论；
- current projection：当前 Chapter/overall 状态、当前测试集合和本次基线质量检查。

历史 `APPROVED_FOR_MERGE` task 在后续业务 `HEAD` 上可能正确显示
`merge_readiness: reverification_required`；这不会抹去其历史 evidence，也不能被改写成当前通过。
先运行自动追踪和四类负向自举回归，再运行完整质量命令：

```powershell
python -m pytest tests/integration/test_acceptance_traceability.py -q
python -m pytest tests/acceptance/test_phase_02_self_hosting.py tests/integration/test_phase_02_self_hosting.py tests/e2e/test_phase_02_self_hosting_scenario.py tests/e2e/test_phase_02_negative_self_hosting.py -q
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy src
git diff --check
```

覆盖率命令必须把数据库和 XML 写入精确的独立 run directory，不能写入仓库根。下面的
PowerShell 示例在操作系统临时目录中为本次运行创建唯一目录；命令以 `origin/main` 的共同
祖先作为本次变更覆盖比较的 base。若任务冻结了不同的 base commit，应把 `$baseCommit`
改为该精确 SHA。先前的完整质量命令可继续运行，再单独运行以下覆盖率与 diff-cover 门槛：

```powershell
$runId = "harness-model-quality-{0}" -f ([guid]::NewGuid().ToString("N"))
$runDir = Join-Path ([System.IO.Path]::GetTempPath()) $runId
$coverageFile = Join-Path $runDir ".coverage"
$coverageXml = Join-Path $runDir "coverage.xml"
$baseCommit = (git merge-base HEAD origin/main).Trim()
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
$env:COVERAGE_FILE = $coverageFile
try {
    python -m pytest -q --cov=aiflow --cov-branch --cov-report=term-missing --cov-report="xml:$coverageXml" --cov-fail-under=85
    if ($LASTEXITCODE -ne 0) { throw "coverage pytest failed with exit $LASTEXITCODE" }
    .\.venv\Scripts\diff-cover.exe $coverageXml --compare-branch=$baseCommit --fail-under=90
    if ($LASTEXITCODE -ne 0) { throw "diff-cover failed with exit $LASTEXITCODE" }
}
finally {
    Remove-Item Env:COVERAGE_FILE -ErrorAction SilentlyContinue
}
```

这两项阈值分别要求总分支覆盖率不低于 85%、相对 `$baseCommit` 的变更覆盖率不低于 90%。
成功或失败后先保留 run directory 以便定位结果；若要把它绑定为 task evidence，应按正式
`aiflow verify` 流程生成 task-local run，而不是把这个临时目录当作权威 evidence。只有在确认
无需保留诊断信息后，才可用精确路径 `Remove-Item -LiteralPath $runDir -Recurse` 删除本次
临时运行；不要对临时目录的父目录执行递归清理，也不要删除任何 task 运行记录。

需要重放某个 attestation 的 Gate 时，应在该精确提交的隔离只读 checkout/worktree 中使用
索引记录的 argv 和原 task-local artifact；Windows 必须在 checkout 前按索引固定 LF。ignored
runtime artifact 不在 clean clone 中，缺失时应报告不可复放，不能重新制造或修改 evidence/hash。
不要在新 `HEAD` 上编辑旧 evidence 的 commit/hash 使其“变新”。
失败输出、Windows symlink capability skips、Hook/actor/platform 限制和 TASK-0028 当前
reverification requirement 都是基线的一部分。重放本身不执行 push、merge、deploy、仓库/
业务数据删除、外部模型或付费调用；若创建临时 checkout，只清理经过精确路径校验的本地
task-owned 临时目标。它也不把 V2 扩大解释为 V3、模型路由或资源调度。
