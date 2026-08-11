# Chapter 01 Task 1.1 Python 工程与 argparse CLI 骨架 Execution Plan

> **For agentic workers:** REQUIRED EXECUTION FLOW: Use `subagent-driven-development` to execute this plan task-by-task when subagents are available. If no subagent capability is available, execute inline with the same task checklist and review checkpoints.

**Goal:** 在八个允许工程路径内建立采用 PEP 621、setuptools、`src` layout、标准库 argparse 和冻结 `uv.lock` 的最小 Python 工程与 CLI，并形成可重载、无自引用、与同一实现 manifest 绑定的验证及双审证据。

**Approach:** Task 0 由状态代理完成只读 preflight 和开始记录；Task 1 的环境、配置、红绿、pip/lock 闭环及全部验证必须由同一个 fresh implementation executor 在一个连续 PowerShell 会话内完成，内部 Phase 不换 agent。Task 2、3 分别由 fresh spec/quality reviewer 顺序执行，Task 4 再由 fresh 状态代理完成状态。

**Materials:** `AGENTS.md`、`docs/superpowers/state/README.md`、`overall.yaml`、`chapter-01.yaml`、MVP 设计（批准 SHA `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`）、原实施目录（批准 SHA `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a`）和本计划。为避免自身 SHA 循环，正文不保存最终自身摘要；主会话批准后通过派发消息提供 `$ApprovedExecutionPlanSha`，并让状态代理写入 chapter evidence，每个 agent 都重算本计划与该值比较。

**Validation:** 固定 uv 0.11.16 与外置 Python 3.13/x64 环境，通过分离的 audited native/action runners 完成同命令红绿、冻结锁、editable-install、定向/累计 pytest、Ruff、mypy、双入口逐字节比较、错误出口、clean-baseline 范围和 whitespace 检查；封存 pre-review evidence 后生成 manifest，规格与质量审查分别绑定它并 PASS。

---

## 固定治理、范围、所有权与计数

- 工程 tracked allowlist 恰为八项：`pyproject.toml`、`uv.lock`、`.gitignore`、`src/aiflow/__init__.py`、`src/aiflow/__main__.py`、`src/aiflow/cli.py`、`tests/conftest.py`、`tests/unit/test_cli.py`。
- 唯一动态权威是 `docs/superpowers/state/chapters/chapter-01.yaml` 和 `docs/superpowers/state/overall.yaml`；原实施目录和本计划保持静态。
- `DEC-T1.1-LOCK-001` 是原 Task 1.1 漏列 `uv.lock` 与固定 uv 工具链的范围+工具链升级，人工 route 为 REVIEW；主会话在用户授权其编排第一章的范围内批准此非高风险本地实现步骤。
- 下载前必须确认公共网络读取权限；资产校验并保留后，完成重验绑定 URL、archive、checksum 与 uv.exe hash，不要求重新联网。资产缺失/损坏、版本或 URL 改变时进入 `needs_revalidation` 并重新经过网络 gate。
- CLI/Policy 缺失时不创建 `.ai/tasks/TASK-*`，`subject_commit: N/A`；commit、push、merge、deploy、delete、凭据和付费调用仍须单独批准。
- 原五步精确映射：Step 1=Task 1 Phase B 配置/锁/ignore；Step 2=Phase C argparse 包；Step 3=Phase C fixture/测试红绿；Step 4=Phase D 全验证；Step 5=Task 4 完成记录。preflight、工具准备、reviews 和修复轮次不改变 `steps_total: 5`。
- Task 1 的 Phase A–D 是一个 implementation execution unit，不触发 header 的 fresh-per-task；只有会话中断时才允许替补 executor 按已批准 context 重载，禁止按 Phase 主动换 agent。
- 每次 `Invoke-AuditedNative` 或 `Invoke-AuditedAction` 都是独立的 2–10 分钟内部子步骤，单独记录、单独判断，不以同一 Phase 合并 exit 结论；失败不可被任何后续调用覆盖。
- 所有 baseline FAIL、测试红、review FAIL、修复和重验均追加保存；不覆盖旧 history、evidence index、manifest 或 review record。
- Task 1.1 只配置 coverage；不得新增或运行 `--cov`、coverage gate 或 diff-cover。

### Task 0: 状态代理只读 preflight 与开始记录

**Artifacts / Locations:**
- Modify only after successful preflight: `docs/superpowers/state/chapters/chapter-01.yaml`
- Modify only after chapter succeeds: `docs/superpowers/state/overall.yaml`
- Review: `AGENTS.md`、state README、MVP、原计划、本计划和两份状态 YAML

- [ ] **Step 1（2–5 分钟）: 任何写入前只接受唯一 clean baseline**
状态代理读取 Python 3.13 路径/版本、AMD64/64、HEAD、branch/worktree、uv/Policy 缺失，并以 `git status --porcelain=v1 -z -uall` 按 NUL 严格解析完整 status/path 集合。唯一允许项是 `?? docs/superpowers/plans/2026-08-02-chapter-01-task-1-1-execution.md`，且该文件 SHA 必须等于 `$ApprovedExecutionPlanSha`；任何其他 tracked/untracked/rename/copy 条目立即停止并请求重新审计，不写状态。随后读取并 SHA-256 哈希 `AGENTS.md`、state README、两份状态 YAML、MVP、原计划和本计划；缺失 allowlist 文件在有序 start manifest 中固定 `sha256: null`，对象 `[ordered]`、数组按路径排序。

- [ ] **Step 2（2–5 分钟）: 比对批准值与状态来源**
重算本计划 SHA 并等于主会话提供的 `$ApprovedExecutionPlanSha`。解析 `overall.source` 和 `chapter.source`，分别要求其中 MVP/原实施目录 SHA 与当前文件摘要完全一致，且两份 source 值互相一致。

- [ ] **Step 3（2–5 分钟）: 失配安全失败或按固定顺序开始**
任一批准值/source 失配时，先向 chapter history 追加原因并把 chapter/task 置 `needs_revalidation`，成功后才同步 overall，禁止进入实现。全部匹配时，chapter 写入顺序严格为：追加 history → `chapter.status: in_progress` → Task 1.1 `status: in_progress`、evidence 与 `completed_steps: []`；该写入成功后才更新 overall status/指针。

- [ ] **Step 4（2–5 分钟）: 保存开始证据**
chapter evidence 记录用户授权、actor/UTC、`$ApprovedExecutionPlanSha`、四个治理文件 hash、两份 source 比对、完整 NUL baseline 集合、完整 canonical `StartManifest`、`StartManifestSha256`、governance/source digest map、`DEC-T1.1-LOCK-001`、Python/uv/Policy、范围、失效条件与 `subject_commit: N/A`。状态代理把 `StartManifestSha256` 回报主会话，由主会话连同完整对象和 digest map 显式派发给 Task 1；`git diff --check` 必须独立 exit 0。

### Task 1: 单一 implementation executor 连续执行 Phase A–D

**Artifacts / Locations:**
- Create/modify: 八个工程 allowlist 路径
- Create external and retain: 唯一 `$AuditRoot`、uv/venv/cache/Python dirs、run context、append-only evidence、logs、manifest
- Review: 官方 uv 0.11.16 Windows x64 archive/checksum

- [ ] **Step 1（5–10 分钟）: 定义 PowerShell 5.1 公共原语**

Task 1 整个连续执行单元只能由 `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -NonInteractive` 承载；主会话审计记录 executable/arguments，子进程在任何工作前断言当前进程路径及 `$PSVersionTable.PSVersion` 为 5.1，失败立即停止。

```powershell
function Get-BytesSha256([byte[]]$Bytes) {
  $Hasher=[Security.Cryptography.SHA256]::Create()
  try { return (($Hasher.ComputeHash($Bytes)|ForEach-Object {$_.ToString('x2')}) -join '') } finally { $Hasher.Dispose() }
}
function Get-FileSha256([string]$Path) { return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant() }
$Utf8NoBom = New-Object Text.UTF8Encoding($false)
function Write-CanonicalJson([string]$Path,$Value) {
  $Json=$Value|ConvertTo-Json -Depth 10 -Compress
  [IO.File]::WriteAllText($Path,$Json,$Utf8NoBom)
  return Get-BytesSha256($Utf8NoBom.GetBytes($Json))
}
```

禁止 `[Convert]::ToHexString`、静态 `SHA256.HashData` 和 `Set-Content -Encoding utf8`。`run-context.json` 与 `.sha256` 都用 `[IO.File]::WriteAllText` 写为 UTF-8 无 BOM、无末尾换行。

- [ ] **Step 2（5–10 分钟）: 定义 native/action 双审计器**
`Invoke-AuditedNative` 接收 `Id/File/string[] Arguments/Cwd/int[] ExpectedExit/ExpectedPattern/ContextDigest/Cycle`。入口保存旧 `$ErrorActionPreference`，随后保持 `Stop` 并把局部 `$exit=125`；在 resolve File 前，先基于已批准 canonical `$AuditRoot` 创建与 File 无关的 `$AttemptId`、fallback sink directory、append-only JSONL 和该 attempt 的 structured exception log。该 bootstrap sink 创建/写入不可用是唯一无结构化记录路径，必须向紧急 stderr 报 `evidence-sink-failed` 并以 126 硬终止。sink 就绪后，同一个最外层 `try` 先保存 canonical `$OriginalCwd`、置 `$locationChanged=$false`，再完成 File resolve、leaf/allowlist 验证、普通 log directory/files 预建、cwd 切换（仅成功后置 changed 为 true）和 `& $ResolvedFile @Arguments`；调用后立即一次性复制 `[int]$LASTEXITCODE` 到 `$exit`，以后不再读取它。最外层 `catch` 不 rethrow，只准备内存 launch-exception record，确保 resolve/allowlist/log 预建/启动异常均可写入 fallback JSONL 与 structured exception log，`$exit` 保持 125。

`Invoke-AuditedAction` 接收同类 metadata 与 `ScriptBlock`，用于受控下载、`Expand-Archive`、hash/文件/输出比较和 NUL scope 解析；同样先建立与 ScriptBlock 无关的 `$AttemptId`/fallback sink，失败才走紧急 stderr+126。sink 就绪后，最外层 `try` 先保存 canonical `$OriginalCwd`、置 `$locationChanged=$false`，再完成普通 log directory/files 预建、分离 stream 捕获及 `& $ScriptBlock`，仅成功后设 `$exit=0`；其 catch 不 rethrow，准备可写入 fallback 的 structured exception record，`$exit` 保持 125。Action 不主动切换目录，但仍记录 cwd，并在 ScriptBlock 改变 location 时保持/恢复原 cwd。

两者离开 outer catch 后进入独立 evidence-outcome `try`，此时 preference 仍为 `Stop`：先比较 canonical current cwd 与 `$OriginalCwd` 并更新 `$locationChanged`；若为 true，恢复原 cwd并记录 restore success/not-needed，恢复失败则形成 structured sink-failure record、尽力追加 fallback JSONL 后以 126 硬终止。cwd 已恢复后，写入已准备的 exception log、保留 observed exit、检查 captured output（不匹配即把局部 `$exit` 归一为 synthetic 125）、形成/序列化 ordered outcome，并用 `[IO.File]::AppendAllText(...,$Json+[Environment]::NewLine,$Utf8NoBom)` 追加 fallback JSONL；fallback 创建或写入本身失败才允许紧急 stderr `evidence-sink-failed`+126。仅 cwd restore 成功且 evidence append 成功后才恢复旧 preference，最后只按局部 `$exit` 是否属于 `ExpectedExit` 断言/throw；前述 catch 均不得提前 throw。由此每条普通失败路径先有 structured evidence，且后续调用不能覆盖失败。记录含 AttemptId、cwd/restore result、context digest/cycle，未来 manifest 以 sealed index SHA 建立传递绑定。

- [ ] **Step 3（5–10 分钟）: 在 Phase A 前 bootstrap 外置上下文和固定 uv**
创建唯一 canonical OS temp `$AuditRoot`，其 `uv-bin/uv-cache/uv-python/project-venv/logs` 均经 containment 检查位于 `$RepoRoot` 外。紧接着、首个 Python/uv/pip 调用（含 venv）前，从当前进程清除全部继承的 `UV_*`、`PIP_*`、`PYTHON*`，只记录被清除变量名；再设置排序白名单：绝对 `UV_PROJECT_ENVIRONMENT/UV_PYTHON/UV_CACHE_DIR/UV_PYTHON_INSTALL_DIR`，`UV_NO_MANAGED_PYTHON=1`、`UV_PYTHON_DOWNLOADS=never`、`UV_NO_SYSTEM_CONFIG=1`、`UV_DEFAULT_INDEX=https://pypi.org/simple`、`UV_INDEX_STRATEGY=first-index`、`UV_KEYRING_PROVIDER=disabled`，不得设置其他匹配变量。

隔离完成后才用 Native 执行 Python 3.13 `-m venv --without-pip`。网络 gate 后，预先绑定 canonical `$ArchivePath/$ChecksumPath` 到 `$AuditRoot` 下固定 leaf；两个 Action ScriptBlock 仅分别调用 `Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/astral-sh/uv/releases/download/0.11.16/uv-x86_64-pc-windows-msvc.zip' -OutFile $ArchivePath` 和 `Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/astral-sh/uv/releases/download/0.11.16/uv-x86_64-pc-windows-msvc.zip.sha256' -OutFile $ChecksumPath`，证据保存展开后的 literal URI 与 canonical absolute OutFile，禁止其他 IWR 形式。用 Action 严格读取并比较 checksum，要求 `.Trim()` 精确等于 `dd9d6d6554bfab265bfa98aa8e8a406c5c3a7b97582f93de1f4d48d9154a0395 *uv-x86_64-pc-windows-msvc.zip`，记录 checksum 文件自身 SHA；另以 Action 硬比较 archive SHA 为 `dd9d6d6554bfab265bfa98aa8e8a406c5c3a7b97582f93de1f4d48d9154a0395`，再以 Action 解压。Native 单独运行 `$Uv @('--no-config','--version')`，必须输出 `uv 0.11.16`。

- [ ] **Step 4（2–5 分钟）: 固化隔离环境并建立外部信任 context**
`run-context.json` 含整数 `revision: 1`、`previous_digest: null`、RepoRoot/Python/AuditRoot、Uv/资产 hashes、venv/ProjectPython、`LockSha: null`、清除项和完整受控 env/index；还必须嵌入 Task 0 派发的完整 canonical `StartManifest`、`StartManifestSha256` 及逐路径 governance/source digest map（`AGENTS.md`、state README、MVP、原计划、本批准计划及两份 YAML 的规范化 source 值），不得只保存路径或旁置引用。

每次创建/更新 context 都以无 BOM/无换行写 JSON 与旁置 hash，返回 `{canonical AuditRoot, revision, digest}` 给主会话；主会话让状态代理追加 chapter history，并把这三个外部 expected 值显式派发给后续 Phase、替补和 reviewers，绝不假定跨会话变量。

- [ ] **Step 5（2–5 分钟/Phase）: 每个 Phase 用外部 expected 重载**
loader 接收主会话传入的 canonical `$AuditRoot`、expected revision/digest 与 `$ApprovedExecutionPlanSha`；入口先清除当前进程全部 `UV_*`、`PIP_*`、`PYTHON*`，再读取但不盲信 context/sidecar。它重算 context digest、嵌入 `StartManifest` 的 canonical `StartManifestSha256`，从当前治理/来源文件重算逐路径 digest map 和两份规范化 source 值，并全部精确比较；同时验证 revision/digest、canonical AuditRoot、所有子路径 containment、批准计划 SHA、保留资产/checksum/uv.exe hashes/version。验证成功后才从 context 重建环境，并枚举精确比较完整白名单的所有 name/value，不容许额外匹配变量。每个 Phase 边界都递增 revision、把旧 digest 写 `previous_digest`、回报新 tuple 并由状态代理追加 history；替补只可使用最后已记录 tuple，禁止重下载、换版本或重建 context。

- [ ] **Step 6（2–10 分钟/项）: Phase A/B 基线、配置、唯一锁改写**
用 Native 运行外置 `$ProjectPython -m pytest tests/unit/test_cli.py -q`，expected exit 1 且原因含 pytest 缺失。随后创建原 PEP 621/setuptools/src 与依赖/pytest/Ruff/mypy/coverage 配置，无 contract marker；`.gitignore` 精确覆盖 caches、coverage、`.venv/`、`*.egg-info/`，不得忽略 evidence logs。唯一改写锁为 Native `$Uv @('--no-config','lock')`；记录 `LockSha` 后创建新 context revision/digest 并回报，再分别 Native 执行 `$Uv @('--no-config','lock','--check')` 和 `$Uv @('--no-config','sync','--frozen','--extra','dev','--no-install-project')`。

- [ ] **Step 7（2–10 分钟/项）: Phase C 同命令红绿**
`tests/conftest.py` 的实际使用 subprocess fixture 必须从 child env 移除任何继承的 `PYTHONPATH`，再且只添加 `PYTHONPATH=(Join-Path $RepoRoot 'src')`，不得传入未知 PYTHONPATH，并在 evidence 记录该规范化值。测试固定 description `Auditable AI code collaboration CLI`、version `aiflow 0.1.0.dev0`、unknown arg exit 2/stderr 含 `usage:`/`error:` 且无 `Traceback`。Native 审计同一 pytest 命令，no-install-project 后因 `src` 尚无包而 exit 1 红；再实现 `ArgumentParser(prog='aiflow', description='Auditable AI code collaboration CLI')`、字面量 version `aiflow 0.1.0.dev0`、`__version__` 与 `__main__`，无后续逻辑；同一命令必须 exit 0 绿。

- [ ] **Step 8（2–10 分钟/项）: Phase D pip/lock 闭环和独立验证**
每行均为单独 `Invoke-AuditedNative` 或 `Invoke-AuditedAction`、独立 expected exit/输出，任何异常立即停止：

| ID | File + arguments | Expected |
|---|---|---|
| SYNC-INEXACT | `$Uv @('--no-config','sync','--frozen','--extra','dev','--inexact')` | 0 |
| ENSUREPIP | `$ProjectPython -m ensurepip --upgrade` | 0 |
| PIP-EDITABLE | `$ProjectPython -m pip install --isolated --index-url https://pypi.org/simple --disable-pip-version-check --no-input -e .[dev]` | 0；仅外置 venv |
| SYNC-EXACT | `$Uv @('--no-config','sync','--frozen','--extra','dev')` | 0；此后禁止 pip |
| LOCK-CHECK | `$Uv @('--no-config','lock','--check')` | 0 |
| LOCK-HASH | Action 重算并比较 `LockSha` | 0；hash 不变 |
| PYTEST-DIRECT | `$ProjectPython -m pytest tests/unit/test_cli.py -q` | 0 |
| PYTEST-ALL | `$ProjectPython -m pytest -q` | 0；本章累计回归 |
| RUFF | `$ProjectPython -m ruff check pyproject.toml src tests` | 0 |
| MYPY | `$ProjectPython -m mypy src` | 0 |
| MODULE-HELP | `$ProjectPython -m aiflow --help` | 0；固定 description |
| MODULE-VERSION | `$ProjectPython -m aiflow --version` | 0；固定版本 |
| EXE-HELP | 外置 `Scripts/aiflow.exe --help` | 0；等于 module help |
| EXE-VERSION | 外置 `Scripts/aiflow.exe --version` | 0；等于 module version |
| MODULE-BAD | `$ProjectPython -m aiflow --definitely-unknown` | 2；usage/error，无 Traceback |
| EXE-BAD | 外置 exe 同一坏参数 | 2；输出等于 module bad |
| DIFF-CHECK | `git diff --check` | 0 |
| STATUS | `git status --porcelain=v1 -z -uall` | 0；NUL 集合可解析 |
| STREAM-COMPARE | Action 对 module/exe help、version、bad 的 stdout 与 stderr 日志分别逐字节比较 | 0；每对完全相等 |

Action 对 `$Allowed` 八文件逐一扫描行尾空白，并把完整 `git status --porcelain=v1 -z -uall` NUL records 与以下恰好 11 条精确集合比较：`?? docs/superpowers/plans/2026-08-02-chapter-01-task-1-1-execution.md`；` M docs/superpowers/state/chapters/chapter-01.yaml`；` M docs/superpowers/state/overall.yaml`；`?? pyproject.toml`；`?? uv.lock`；`?? .gitignore`；`?? src/aiflow/__init__.py`；`?? src/aiflow/__main__.py`；`?? src/aiflow/cli.py`；`?? tests/conftest.py`；`?? tests/unit/test_cli.py`。计划 SHA 仍须等于批准值；禁止 staged、deleted、rename/copy（包括其第二 path）、typechange 和任何其他 record。正常工具生成物若被既有 ignore 规则排除，另由 Native `git check-ignore -v` 验证且不得进入 records；若有 egg-info，`git ls-files '*.egg-info/*'` 必须为空。Python 3.13 仅证明满足 `>=3.11`，明确记录未在 Python 3.11 运行。

- [ ] **Step 9（5–10 分钟）: 封存 evidence 并生成无循环 implementation manifest**
把基线失败、严格 checksum、下载/解压、lock、红绿、pip、双流比较和全部验证写入本轮 append-only index，封存并旁置 SHA；修复轮新建 index。manifest 保留既有全部字段，并明确加入 context revision/digest/previous_digest、完整 canonical `StartManifest`、`StartManifestSha256`、governance/source digest map、checksum 文件自身 SHA、清除的环境变量名、完整受控 env/index 配置和完整 NUL baseline/final records；不含 reviews。manifest/旁置 hash 使用无 BOM/无换行；executor 回报 manifest 路径/digest 和最后 context tuple，index 内命令证据由 index SHA 传递绑定 manifest。

### Task 2: Fresh spec reviewer 绑定实现 manifest

**Artifacts / Locations:**
- Review: 主会话显式传入的 `{canonical AuditRoot, expected revision, expected digest}`、sealed index、manifest 和八文件

- [ ] **Step 1（5–10 分钟）: 重载并审规格**
先用主会话显式提供的 canonical AuditRoot 与 expected revision/digest 调 loader，禁止仅信 context/sidecar；再用同一审计命令契约但写入独立 review logs（不得追加 sealed index），验证 `$ApprovedExecutionPlanSha`、context/资产/manifest/index hashes 和 manifest 全字段，再核对 argparse、八路径、conftest 实际使用、红绿、锁/pip、命令期望、原五步映射和非目标。以无 BOM/无换行 JSON 写 review record，包含 identity、role=`spec`、UTC、manifest digest、PASS/FAIL、发现和证据引用，并返回 record hash。

- [ ] **Step 2（2–10 分钟/轮）: FAIL 回原 executor**
FAIL 由状态代理追加 history，主会话把 `$AuditRoot` 交回原 implementation executor；其 loader 校验后修复、重跑受影响红绿和全部 Phase D、封存新 index/manifest，再由 fresh spec reviewer 重审。原 executor 不可用仅属中断恢复，替补必须加载原 context/资产。

### Task 3: Fresh quality reviewer 绑定同一 manifest

**Artifacts / Locations:**
- Review: spec PASS record、同一 implementation manifest/context/index 和全部代码配置

- [ ] **Step 1（5–10 分钟）: 仅在 spec PASS 后审质量**
不同 fresh reviewer 先以主会话显式提供的最新 canonical AuditRoot 与 expected revision/digest 调 loader，再用同一审计命令契约和独立 review logs 验证 spec record hash，检查 PS5.1、命令逐项 exit、上下文可恢复、锁复现、测试隔离、argparse 错误契约、范围/ignore 和证据无循环；写 role=`quality`、同一 manifest digest、identity/UTC/PASS-FAIL 的 review record并返回 hash。

- [ ] **Step 2（2–10 分钟/轮）: FAIL 完整回环**
任何 quality FAIL 同样追加 history并回原 executor；修复后必须重跑全部 Phase D、生成新 index/manifest，并按 fresh spec→fresh quality 顺序重审，旧 FAIL/records 保留。

### Task 4: Fresh 状态代理完成并交接

**Artifacts / Locations:**
- Modify first: `docs/superpowers/state/chapters/chapter-01.yaml`
- Modify only after chapter succeeds: `docs/superpowers/state/overall.yaml`
- Review: context、sealed index、manifest 与两份 PASS review records

- [ ] **Step 1（5–10 分钟）: 完成前逐项重算**
由主会话传入最新 `{canonical AuditRoot, expected revision, expected digest}` 和 `$ApprovedExecutionPlanSha`，状态代理先按外部 expected 调 loader；再重算 context、保留资产、index、manifest、两份 review record、四个治理文件、三份规格/计划来源、overall/chapter source、HEAD/status、八文件、Policy/Python/uv/env/LockSha。除 review records 不在 manifest 内外，所有 manifest 字段必须精确复现；任一工具/代码/来源失配先进入 `needs_revalidation`，不得完成。

- [ ] **Step 2（2–5 分钟）: 先完成 chapter**
严格按 history → evidence → Task 1.1 fields 写入：记录 manifest/index/context/两份 review record hashes、identity/role/UTC/PASS、命令 exits、外置路径、Python 3.11 未运行限制与 `subject_commit: N/A`；`completed_steps` 设 `[1,2,3,4,5]`、task `completed`，chapter 仍 `in_progress`。

- [ ] **Step 3（2–5 分钟）: 成功后才汇总 overall**
仅在 chapter 写入成功后把 overall tasks_completed 增至 1、steps_completed 增至 5，overall/chapter-01 保持 `in_progress`，指针移到 Task 1.2。用同一审计命令契约和 completion record sink 独立运行 `git diff --check` 与 status/allowlist 检查；保留 `$AuditRoot`，不 commit/push 或执行任何高风险动作。

---

Plan complete and saved to `docs/superpowers/plans/2026-08-02-chapter-01-task-1-1-execution.md`. Recommended next step: use `subagent-driven-development` so each task gets a fresh executor plus review. If this environment has no subagent capability, I can execute inline using the same checklist and review checkpoints.
