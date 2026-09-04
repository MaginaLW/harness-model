# Task 1.1 TDD Replay Remediation Execution Plan

> **For agentic workers:** REQUIRED EXECUTION FLOW: Use `subagent-driven-development` to execute this plan task-by-task when subagents are available. If no subagent capability is available, execute inline with the same task checklist and review checkpoints.

**Goal:** 不降低 Task 1.1 原有 red-before-green gate，在既有外置 `AuditRoot` 内从当前 `HEAD` 的干净归档建立隔离 replay，以相同测试、相同 `ProjectPython`、相同 pytest 命令真实取得先 red 后 green，并重跑原计划完整 Phase D，供 fresh spec 与 fresh quality 顺序复核。

**Approach:** 主会话先对本静态补充计划做 REVIEW，并外部绑定计划 SHA、canonical runner source payload及其 expected SHA；状态代理先按 chapter→overall 只记录 `approved_for_execution`，保持三层 `needs_revalidation`，待独立 preflight 通过后再恢复执行态。唯一原 implementation executor 启动一个路径与参数固定的 Windows PowerShell 5.1 持久会话，在其中建立 attempt/fallback/index、按字节校验并内存加载 runner functions，再于 existing `AuditRoot` 完成 replay 和 exact Phase D；public dependency read 采用主会话明确批准的配置/lock/index evidence boundary，不声称 packet-level host enforcement。状态交接后由 fresh spec、fresh quality 依次把关，任何 FAIL 都保留旧记录并回原 executor，不把既有 premature-green 重命名为 red。

**Materials:** 原执行计划 `docs/superpowers/plans/2026-08-02-chapter-01-task-1-1-execution.md`（SHA-256 `dcb556a01cfa304520d84309ca1f72d8cb944a438e06c48924306bab866c5ec4`）；spec FAIL record `C:\Users\Magina\AppData\Local\Temp\aiflow-task-1-1-808bd85dd990446ab4135df0116cc55b\evidence\spec-review-task-1-1-v4\spec-review-record.json`（SHA-256 `6493635dde8561ee74bea529193bccb516e378ee60c675d5e700f7243e2838fd`）；`implementation-manifest.final-v2.json`（SHA-256 `3069aa594e16807f7ae0e58e005b1c5dae61cf1c6a0dedd1411699aa9ab66fc6`）；`context\run-context.json` revision 5（digest `7b92b229ccec59aefc33c01398692d5ab9cf2c87e89d242ff5b8d1d94d701adb`）；existing `AuditRoot=C:\Users\Magina\AppData\Local\Temp\aiflow-task-1-1-808bd85dd990446ab4135df0116cc55b`；本计划 SHA-256 由主会话批准后外部传入，本文不自引用固定值。

**Validation:** A/B 两段状态事件、精确 PowerShell process identity、runner payload-before-preflight、legacy runner 非执行、目录顺序与 public-read evidence boundary 都须 hash-bound；replay 必须证明 `HEAD=4cf6bb2b3ccf3688c87a887887cef69040a5f0a3` 的 archive/extract 基线不含八个工程路径。五个配置/测试文件复制后，同一外置 Python/cwd/pytest 命令 exit 1且三个 child 均 `No module named aiflow`；随后只复制三个当前 `src`，同一命令 exit 0/`3 passed`。当前工作树 exact Phase D 全通过，最终 NUL status 精确十二条；context rev6+、sealed index和 final-v3 绑定全部验证；fresh spec PASS 后才允许 fresh quality，二者 PASS 后才允许完成。

---

## 固定治理边界与创建时基线

- 决策固定为 `DEC-T1.1-TDD-REPLAY-001`，route 固定为 `REVIEW`；本计划只补救 `SPEC-BLOCKER-001`，不改变原计划功能范围、分流或验证等级。Phase D 所需 public dependency read 及其有限 evidence boundary 是该 decision 下的显式范围扩展，必须与本文执行批准一起单独记录。
- 创建本计划前已只读确认 Task 1.1、chapter-01、overall 都为 `needs_revalidation`，`git status --porcelain=v1 -z -uall` 精确十一条；创建后唯一新增路径是本文，精确十二条。
- 仓库内允许的写入只有：新增本文，以及批准后修改既有 `docs/superpowers/state/chapters/chapter-01.yaml` 与 `docs/superpowers/state/overall.yaml`。八个工程文件和原执行计划只能读取，其他新文件、日志、归档、review record 与 manifest 全部写在 existing `AuditRoot` 内。
- 保留所有原文件和 evidence。禁止删除、移动、stash、reset、`git worktree`、commit、push；禁止下载新工具、解释器或既有 GitHub uv 资产。依赖读取只按本计划批准的 PyPI configuration/lock/index evidence boundary判断，不得暂时改坏实现、注入错误、改测试来制造 red。
- `subject_commit` 继续为 `N/A`；replay 的只读基线单独绑定 `baseline_head=4cf6bb2b3ccf3688c87a887887cef69040a5f0a3`。HEAD、Policy、计划、spec、manifest、context、八文件或精确 status 任一变化即失效并回 `REVIEW`，不可自行放宽比较。
- 本计划执行期不并行修改状态、venv 或 evidence。主会话串行派发状态代理→唯一原 executor→状态代理→fresh spec→fresh quality→状态代理；只有纯只读审核可并行准备，结果仍按规定顺序采纳。

### 固定工程文件摘要

| Path | SHA-256 |
|---|---|
| `.gitignore` | `4bd504e4acdf8f2c3382143c119487c40a0543cd985b2f34d45369565d9c978f` |
| `pyproject.toml` | `b6338eb6757a1980f0dc2747d0532600aa3430d0fd2233c13d804cb2e6774613` |
| `src/aiflow/__init__.py` | `3139049109b2bd5266c6c17449ee3643b32db2c83df259567479dba0def56254` |
| `src/aiflow/__main__.py` | `dc2440528117c149f11c10e232aef355fe00689339ee082a547d596be870bb43` |
| `src/aiflow/cli.py` | `b7e7c5cf7de2547d7b9051347d14636f0b44f11343769813ebbe04f76e017db4` |
| `tests/conftest.py` | `d612594134a90aa39d9c12e93d2e65cf070ea690a773adec77a779806cc31e10` |
| `tests/unit/test_cli.py` | `83b4ce182a0ae1d2fb830ec9522fac1685f9494cb29bd8912afb8e132da367c6` |
| `uv.lock` | `d4df7f0ae76855fa32132f5cda6c3ee7b39aca7462ec435edbf66374c2992895` |

### 精确十二条 status 集合

以下按 NUL record 集合比较，不依赖显示顺序；禁止 staged、deleted、rename/copy、typechange 或额外 record：

```text
 M docs/superpowers/state/chapters/chapter-01.yaml
 M docs/superpowers/state/overall.yaml
?? .gitignore
?? docs/superpowers/plans/2026-08-02-chapter-01-task-1-1-execution.md
?? docs/superpowers/plans/2026-08-02-chapter-01-task-1-1-tdd-replay-remediation.md
?? pyproject.toml
?? src/aiflow/__init__.py
?? src/aiflow/__main__.py
?? src/aiflow/cli.py
?? tests/conftest.py
?? tests/unit/test_cli.py
?? uv.lock
```

## Task 0: 分离执行批准与恢复执行态

**Artifacts / Locations:**
- Repo state: `docs/superpowers/state/chapters/chapter-01.yaml`、`docs/superpowers/state/overall.yaml`
- Approval input: 主会话外部派发的 `ApprovedSupplementalPlanSha`、canonical `RunnerSourcePayload`/`ExpectedRunnerPayloadSha`、两份独立计划 review 的 identity/UTC/PASS、public dependency read evidence-boundary 批准
- Independent validation record: `$AuditRoot\evidence\supplemental-plan-execution-preflight-$ApprovedSupplementalPlanSha.json` 及 sidecar

- [ ] **Step 0.1（2–5 分钟）: 状态代理做零写入批准材料 preflight**

重新计算本文 SHA-256 并与外部 `ApprovedSupplementalPlanSha` 精确相等；确认 `DEC-T1.1-TDD-REPLAY-001/REVIEW` 的两份独立计划 review 都有 reviewer identity、UTC、record path/hash 与 PASS，且 review/批准 envelope 完整绑定 canonical `RunnerSourcePayload` 的 UTF-8-noBOM/LF `ExpectedRunnerPayloadSha`，Task/chapter/overall 三者仍 `needs_revalidation`。

批准材料必须明确接受当前 public-read **证据边界**：只审计 controlled env/default index `https://pypi.org/simple`、每条 uv 的 `--no-config`、pip 的 `--isolated --index-url https://pypi.org/simple`、`uv.lock` source URL，以及配置/参数/lock 中不存在显式凭据、私有源、上传或付费动作；普通 uv/pip stdout/stderr、cache delta或缺少 URL 日志都不能证明实际 egress host或阻断，当前没有独立 proxy/packet-level host evidence，官方 redirect/CDN 可能参与。工具若显式请求凭据、非 HTTPS 或 private index 必须停止；若用户或未来 executable Policy 要求 host-level enforcement，本任务为 `blocked` 而不是推断 PASS。主会话在用户已授权的编排范围内明确批准该 read evidence boundary。此步只读；任一字段缺失或不等时状态不写。

- [ ] **Step 0.2（2–5 分钟）: A 段 chapter-first 记录 approved_for_execution**

先只改 chapter，新增 `EVD-T1.1-TDD-REPLAY-APPROVED-001` 和 `EVT-T1.1-TDD-REPLAY-APPROVED-001`：decision `DEC-T1.1-TDD-REPLAY-001.status: approved_for_execution`、route `REVIEW`、`ApprovedSupplementalPlanSha`、`ExpectedRunnerPayloadSha`、两份 plan review 的 identity/UTC/PASS/path/hash、原计划/spec FAIL/final-v2/context rev5、批准 actor/UTC、`executable_policy_available: false`、`subject_commit: N/A`，以及 `scope_extension: public_dependency_read`。该 scope evidence 原样记录上一步的配置/lock/index 审核项、无独立 proxy/packet-level host proof、可能 official redirect/CDN、缺少 URL 日志不构成网络证明、显式凭据/非 HTTPS/private index 停止，以及 host-level enforcement 要求出现时 blocked；主会话 actor/UTC 明确接受此边界。Task/chapter/overall status 全部保持 `needs_revalidation`，blocker保持 `open`，`completed_steps: [1,2]`、`in_progress_step: 3`、计数不变。chapter 成功且 diff check exit 0 后才在 overall 新增 `EVT-OVERALL-T1.1-TDD-REPLAY-APPROVED-001`；它引用 chapter evidence/event并重复绑定 reviews、两 SHA 和 boundary，overall/chapter-01 仍 `needs_revalidation`，计数/指针不变。approval events 不能与恢复事件合并。

- [ ] **Step 0.3（5–10 分钟）: B 段独立验证后恢复 in_progress**

主会话派发未参与两份 plan review、也不会执行 remediation 的独立 preflight validator。其只读重算原计划、本文、spec FAIL、final-v2、`run-context.json`/sidecar、HEAD、uv/ProjectPython/lock 与八文件全部固定 hashes，验证 context `revision=5`、`previous_digest=f54fb57ec59b186ebe36382d85e12cb2add6a94d4a6d1c82b89feedfa7511424`、canonical AuditRoot、`git diff --check` exit 0，以及 raw NUL status 精确十二条；把 identity/UTC、逐项 expected/actual 与 PASS 写入上述不可覆盖 record/sidecar。该 plan-state validation 不是 audited execution loader/preflight；FAIL 时三层状态保持 `needs_revalidation`。

仅在该独立 record PASS 后，状态代理先在 chapter 新增与 approval event 分离的 `EVD-T1.1-TDD-REPLAY-START-001` 和 `EVT-T1.1-TDD-REPLAY-START-001`，设置 Task 1.1 `status: in_progress`、`completed_steps: [1,2]`、`in_progress_step: 3`、`SPEC-BLOCKER-001.status: remediation_in_progress`、chapter `status: in_progress`，计数不变；chapter 写入和 diff check 成功后，overall 新增 `EVT-OVERALL-T1.1-TDD-REPLAY-START-001` 并设置 overall/chapter-01 `in_progress`、current task `1.1`、current step `3`，计数不变。两层 start events 都绑定 validator identity/UTC/PASS/hash、approval events 和 `ApprovedSupplementalPlanSha`；最终 status 仍精确十二条。

## Task 1: 启动固定 PS5.1 会话、加载 canonical payload 并建立 HEAD replay

**Artifacts / Locations:**
- Persistent host: `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`
- Context: `$AuditRoot\context\run-context.json`、`run-context.sha256`
- Replay: `$AuditRoot\replay\$AttemptId\baseline-head.zip`、`$AuditRoot\replay\$AttemptId\worktree`
- Payload evidence: `$AuditRoot\evidence\remediation-runner-payload-$AttemptId.json`
- Historical runner only: `$AuditRoot\execute.ps1` SHA-256 `ead86a877d55e420e62705b7f224739f6ff7bdcb098be4bf844ae1f5485a1715`
- Bootstrap sinks: `$AuditRoot\fallback\remediation-$AttemptId.jsonl`、`$AuditRoot\evidence\implementation-index-tdd-replay-$AttemptId.jsonl`

- [ ] **Step 1.1（2–5 分钟）: 启动并首先断言唯一持久 PowerShell identity**

原 implementation executor 只启动一次以下 process，并通过该进程持续 stdin/session 驱动 Task 1–4；不得为 bootstrap、preflight、replay、Phase D 或 evidence sealing 新开另一个 PowerShell host：

```text
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass
```

该进程的首个 remediation ScriptBlock 在任何目录/文件/context/environment 动作前，以 `[Diagnostics.Process]::GetCurrentProcess().MainModule.FileName` 重算 canonical process path并要求精确等于上述路径，要求 `$PSVersionTable.PSEdition -eq 'Desktop'`、`$PSVersionTable.PSVersion.Major -eq 5`、`Minor -eq 1`，同时记录完整 version/build。任一不等立即 stderr 报 `powershell-host-mismatch` 并非零退出，ReplayRoot 必须不存在；不得只以“compatible”替代。后续每个 Phase 边界都在同一 `PID` 重验 path/edition/5.1，PID 变化即整轮 FAIL。允许该 host 通过 audited functions 启动 git/uv/Python/aiflow native child，但不允许嵌套 PowerShell。

- [ ] **Step 1.2（5–10 分钟）: bootstrap attempt，按字节绑定并内存加载 runner payload**

主会话向该持久会话传入 literal canonical `AuditRoot`、rev5 tuple、`ApprovedSupplementalPlanSha`、独立 preflight PASS、canonical `RunnerSourcePayload` 与 `ExpectedRunnerPayloadSha`。host identity 通过后才生成 `$AttemptId=[guid]::NewGuid().ToString('N')`，拼出 unique fallback/index/payload-evidence paths，验证全部 contained/不存在，以 `[IO.FileMode]::CreateNew` 建立 fallback JSONL 与空 remediation index。bootstrap sink 不可用是唯一无结构化证据路径，必须 emergency stderr `evidence-sink-failed` + exit 126；已创建 attempt 永久保留且不得创建 replay。

payload 必须已经是 LF-only 且不含 BOM code point；发现 CR/BOM即 FAIL，不得静默规范化。使用 `New-Object System.Text.UTF8Encoding($false)` 得到 UTF-8-noBOM bytes，以 PS5.1-compatible `[Security.Cryptography.SHA256]::Create()` 计算 lowercase SHA-256，并在加载前与 `ExpectedRunnerPayloadSha` 精确相等。随后把含**完整 payload 字符串**、computed/expected SHA、`ApprovedSupplementalPlanSha`、persistent PID/process path/edition/version、AttemptId 和 UTC 的 ordered JSON，以 `[IO.File]::WriteAllText(...,$Utf8NoBom)` 写入不可覆盖 payload-evidence；运行时外置 evidence 明确允许此 WriteAllText，用于无 BOM/无尾换行，不在 repo 写 runner 文件。相同 record append/flush 到 fallback/index。

只有 hash/evidence 全成功后才执行 `$RunnerBlock=[ScriptBlock]::Create($RunnerSourcePayload)` 并在当前持久 session 内存作用域加载其函数，核对 `Invoke-AuditedNative`、`Invoke-AuditedAction` 的 command type/source。每个新 attempt 都必须重新比较 externally expected payload SHA；不得从磁盘创建、读取或 dot-source remediation runner 文件。legacy `execute.ps1` 仅重算上述 historical SHA并记录 `historical_only=true`，禁止执行、dot-source、复制或复用。

- [ ] **Step 1.3（5–10 分钟）: 验证内存 payload 完整实现批准 runner 契约**

主会话绑定的 canonical payload 必须实现并由 self-test 证明：

- `Invoke-AuditedNative` 接收 `Id/File/string[] Arguments/Cwd/int[] ExpectedExit/ExpectedPattern/ContextDigest/Cycle`；`Invoke-AuditedAction` 接收同类 metadata 与 `ScriptBlock`。每次调用在固定 remediation AttemptId 下生成独立 `CallAttemptId`，使用已建立 fallback/index。
- Cwd allowlist 精确为 canonical `{RepoRoot, ReplayWorktree}`，初始 loader/preflight 只能用 RepoRoot；Native executable allowlist精确为 resolved `git.exe`、current `uv.exe`、`ProjectPython` 和 venv `aiflow.exe`。Action 不主动切换目录；所有 path 在使用前做 leaf/existence/containment检查，尚未创建的 ReplayWorktree 只作为 allowlist literal。
- 两函数保存旧 `$ErrorActionPreference`，设 `Stop` 和局部 `$exit=125`；在 resolve/ScriptBlock 前为 CallAttemptId 确定与 File 无关的 exception/stdout/stderr paths。在同一个 outer try 保存 canonical `$OriginalCwd`/`$locationChanged=$false`，完成 resolve/allowlist/log预建、分离双流捕获、必要 cwd 切换和调用。Native 返回后立即且仅一次复制 `[int]$LASTEXITCODE`，此后绝不再读；陈旧 LASTEXITCODE 不得成为结果。Action 仅在 ScriptBlock完整成功后设 exit 0。
- outer catch 不 rethrow，保留 exit 125并准备 structured exception；独立 evidence-outcome try先比较/恢复 cwd，记录 restore result。恢复或 fallback append失败时尽力写 structured sink-failure，emergency stderr + exit 126。只有 cwd恢复且 evidence append成功后才恢复 preference并断言 expected exit/pattern；输出不匹配归一为 synthetic 125，任何失败先留 immutable record。
- loader 读取但不信任 external context/sidecar，重算 digest、paths、environment whitelist和全部绑定后才重建环境。JSON/hash用 UTF8-noBOM/LF；禁用 PowerShell 7-only API、`[Convert]::ToHexString`、静态 `SHA256.HashData` 与 `Set-Content -Encoding utf8`。

self-test 在同一 PID 内覆盖 success、synthetic 125、陈旧 LASTEXITCODE隔离、cwd restore和 structured fallback；不得触碰 repo/replay。self-test PASS 后将 payload SHA、contract/self-test records、persistent session identity、Cwd/executable allowlists纳入 index；后续 context rev6/final-v3 绑定 payload SHA而非 runner file/path。

- [ ] **Step 1.4（5–10 分钟）: 用内存 functions 严格重载并做 audited preflight**

通过内存 `Invoke-AuditedAction` 执行 loader：清除当前进程全部 `UV_*`、`PIP_*`、`PYTHON*`，读取但不盲信 rev5 context/sidecar，重算 raw digest、canonical containment、原计划/本文/StartManifest/治理 source map、uv 0.11.16、`uv.exe` SHA `c5a583d5f1f6d055fc1c32c87d8eceee90edc69a5b9af5da70811befdfc04880`、existing assets、ProjectPython、lock、spec/final-v2、A/B state events、public-read boundary、payload expected/computed SHA和八文件。重建 rev5环境后枚举 name/value；再确认 persistent PID、HEAD、status十二条、`git diff --check` exit 0、final-v3/replay targets尚不存在。任一失败记录到当前 attempt/index并停止；**ReplayRoot、archive、ReplayWorktree 必须不存在**。

- [ ] **Step 1.5（2–5 分钟）: 只创建 contained ReplayRoot**

由 AttemptId 拼出 `$ReplayRoot=$AuditRoot\replay\$AttemptId`、`$ArchivePath=$ReplayRoot\baseline-head.zip`、`$ReplayWorktree=$ReplayRoot\worktree`。先断言三者 contained且全不存在，再以 audited Action只创建 ReplayRoot；动作后它为空，ArchivePath/ReplayWorktree仍不存在。禁止预创建 zip/worktree或复用旧 attempt。

- [ ] **Step 1.6（5–10 分钟）: 由 git archive 和 Expand-Archive 顺序创建剩余路径**

在 repo cwd 用 audited Native 单独运行：

```powershell
git archive --format=zip -o $ArchivePath HEAD
```

运行前再次断言 ArchivePath/ReplayWorktree 不存在；`git archive` 自身创建 zip，expected exit 0。命令前后 `git rev-parse HEAD` 都必须输出 `4cf6bb2b3ccf3688c87a887887cef69040a5f0a3`；`git ls-tree -r --name-only HEAD --` 加八路径必须 exit 0 且 stdout 为空。记录 archive SHA-256/size；确认 ReplayWorktree 仍不存在后，以 audited Action `Expand-Archive -LiteralPath $ArchivePath -DestinationPath $ReplayWorktree` 让 Expand-Archive 自身创建 worktree，expected exit 0。抽取后逐一断言八路径、`tests`、`tests/unit`、`src`、`src/aiflow` 和 `.git` 都不存在，记录 inventory digest；repo status 仍十二条。不得预创建 archive/worktree，任一顺序或 absence 不符即 FAIL。

## Task 2: 在 replay 中完成不可伪造的同命令 red→green

**Artifacts / Locations:**
- Replay files: `$ReplayWorktree`
- External Python: `C:\Users\Magina\AppData\Local\Temp\aiflow-task-1-1-808bd85dd990446ab4135df0116cc55b\project-venv\Scripts\python.exe`
- Remediation index: `$AuditRoot\evidence\implementation-index-tdd-replay-$AttemptId.jsonl`
- Session invariant: Task 2 每个 audited Action/Native 都由 Task 1 已验证的同一 persistent PowerShell PID 和内存 payload functions 承载

- [ ] **Step 2.1（5–10 分钟）: 只复制五个配置/测试文件并消除旧 editable 泄漏**

先以 audited Action 在 existing ReplayWorktree 内顺序创建 `tests`、再创建 `tests/unit`，每次要求父目录存在、目标原先不存在且 canonical contained；`src`/`src/aiflow` 此时仍必须不存在。然后从当前 worktree 逐个 `Copy-Item -LiteralPath` 到 replay 同相对路径，只复制 `.gitignore`、`pyproject.toml`、`uv.lock`、`tests/conftest.py`、`tests/unit/test_cli.py`；每次复制前断言 destination parent 已存在且 leaf 不存在，复制后记录 source/destination SHA并与固定表相等。禁止 Copy 到不存在的父目录；再次断言三个 `src` leaf/parent 均不存在，测试与当前/v2 byte-identical。

为防 existing ProjectPython 的旧 editable 安装把当前 `src` 泄漏到 replay，使用现有 `$Uv`、existing cache 与同一受控 venv，在 replay cwd 单独运行：

```powershell
$Uv @('--no-config','--offline','sync','--frozen','--extra','dev','--no-install-project')
```

expected exit 0；`--offline` 缓存缺失即 FAIL，禁止改为联网。随后同一 `ProjectPython` 在 replay cwd 执行 `-c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('aiflow') is None else 11)"`，expected exit 0，证明 venv 中无可回退的 installed `aiflow`。记录 sync 前后解释器/venv identity、`find_spec`、五文件 hashes 和 `src_absent=true`。

- [ ] **Step 2.2（2–5 分钟）: 用固定命令取得真实 red**

只构造一次并封存 command identity：

```powershell
$ReplayPytestFile = $ProjectPython
$ReplayPytestArguments = @('-m','pytest','tests/unit/test_cli.py','-q')
$ReplayPytestCwd = $ReplayWorktree
```

用 Native runner 执行，expected exit **1**。stdout/stderr 结构化证据必须同时证明 `3 failed`、三个测试 node id 均失败、每个 child 失败归因包含 `No module named aiflow`，且不是 collection/config/pytest 缺失；不得出现 `3 passed`。记录 command File SHA、arguments JSON、cwd canonical、受控 env digest、五文件 hashes、三个 `src` absence、raw stdout/stderr bytes/hash、exit、开始/结束 UTC 和 index 序号。任何原因不同都不是合格 red，立即停止。

- [ ] **Step 2.3（2–5 分钟）: 只复制三个 source 文件**

合格 red record append/flush/read-back 成功后，先生成不可覆盖的 `red-checkpoint-$AttemptId.json`/sidecar，绑定 red record digest、当时 index byte length 与该 prefix SHA；后续 sealed index 的相同 prefix 必须仍匹配。checkpoint 成功前不得创建 `src`。随后 audited Action 在 ReplayWorktree 内顺序创建 `src`、再创建 `src/aiflow`，要求父存在、目标原先不存在且 contained；再依次机械复制当前 `src/aiflow/__init__.py`、`__main__.py`、`cli.py`，每次先确认 destination parent 存在/leaf 不存在，不编辑任何源或测试。每个 source/destination hash 必须与固定表和 final-v2 相等；目录创建/复制的 index 序号与 UTC 严格晚于 red checkpoint、早于 green。再次验证五个配置/测试文件 hash 未变。

- [ ] **Step 2.4（2–5 分钟）: 同一命令取得 green 并核对 chronology**

不重建、不增删任何参数，复用 Step 2.2 的三个变量运行同一 Native command，expected exit **0**，输出必须含 `3 passed` 且无 failed/error。Action 比较 red/green 的 File SHA、arguments JSON、canonical cwd、受控 env digest 与两份测试 hashes完全相同；唯一准许的工程输入差异是三个固定 `src` 从 absent 变为对应 hash。最终 replay 八文件逐项等于当前/v2，index 顺序必须是 baseline→tests/unit directories→五文件 copy→no-install-project→red→red checkpoint→src/aiflow directories→三 source copy→green。任一比较失败则整轮 FAIL；不得补写、重排或覆盖旧 record。

## Task 3: 当前工作树重跑原计划完整 Phase D

**Artifacts / Locations:**
- Current worktree: `D:\repos\harness-model`
- Mutable context: `$AuditRoot\context\run-context.json`；immutable rev5 snapshot: `run-context.r5-7b92b229ccec59aefc33c01398692d5ab9cf2c87e89d242ff5b8d1d94d701adb.json`
- Phase D logs/index: existing `AuditRoot` 下本 remediation attempt；继续使用同一 persistent PowerShell PID 和已验 payload SHA

- [ ] **Step 3.1（2–5 分钟）: 保存 rev5 并推进 rev6**

先把当前 raw rev5 与 sidecar 机械复制为上述 immutable snapshot/sidecar，hash 仍为 `7b92...1adb`，目标必须原先不存在；再生成 canonical context revision 6，`previous_digest` 精确为 rev5 digest，保留原全部字段并新增 `ApprovedSupplementalPlanSha`、decision/spec/final-v2 digests、A/B events与独立 preflight、public-read evidence-boundary approval、`AttemptId`、persistent process path/args/PID/edition/version、runner payload expected/computed SHA及payload-evidence pointer、Cwd/executable allowlists、legacy runner historical hash、replay/archive/inventory/red/checkpoint/green pointers和 remediation index。无 BOM/无尾换行写入 mutable context/sidecar，重算 digest并由主会话记录新 tuple。若推进 rev7+，每次先保存上一 revision并精确串联 `previous_digest`；禁止覆盖 rev5、v2、payload evidence或旧 index。

- [ ] **Step 3.2（2–5 分钟）: 验证已批准的 public-read evidence boundary**

内存 loader 用 latest tuple 验证 A approval 已由主会话 actor/UTC 接受该 evidence boundary：controlled `UV_DEFAULT_INDEX=https://pypi.org/simple`、`UV_KEYRING_PROVIDER=disabled`，每条 uv exact arguments含 `--no-config`，pip exact arguments含 `--isolated --index-url https://pypi.org/simple`，`uv.lock` source均为 HTTPS public PyPI index/files references，且这些配置/参数/lock没有显式 userinfo/token/private index、上传或付费动作。existing GitHub uv archive/checksum/exe hashes必须相等，禁止重新请求 GitHub；先做 uv cache/venv inventory以优先复用 cache。

boundary record 必须同时声明：当前无独立 proxy/firewall/packet capture，不能据普通 uv/pip输出、cache delta或缺少 URL 行证明实际 egress host或 host阻断；官方 redirect/CDN可能参与。执行中若工具**显式**请求凭据、非 HTTPS或 private index，立即停止；若用户或 executable Policy 要求 host-level enforcement，则 status `blocked`，不得用本 boundary替代。满足配置审计只证明批准输入边界，不证明 packet-level route。

- [ ] **Step 3.3（2–10 分钟/项）: 用同一内存 functions 逐项重跑 exact Phase D**

同一 persistent host 在每行前重验 process path/PSEdition/5.1/PID、payload SHA、context、assets、八文件和 status，在当前 repo cwd逐行调用内存 audited functions；每行失败立即停止，后行不能覆盖：

| ID | File + exact arguments | Expected |
|---|---|---|
| SYNC-INEXACT | `$Uv @('--no-config','sync','--frozen','--extra','dev','--inexact')` | exit 0 |
| ENSUREPIP | `$ProjectPython -m ensurepip --upgrade` | exit 0 |
| PIP-EDITABLE | `$ProjectPython -m pip install --isolated --index-url https://pypi.org/simple --disable-pip-version-check --no-input -e .[dev]` | exit 0；existing venv |
| SYNC-EXACT | `$Uv @('--no-config','sync','--frozen','--extra','dev')` | exit 0；此后禁止 pip |
| LOCK-CHECK | `$Uv @('--no-config','lock','--check')` | exit 0 |
| LOCK-HASH | Action 重算 `uv.lock` | exit 0；等于 `d4df...2895` |
| PYTEST-DIRECT | `$ProjectPython -m pytest tests/unit/test_cli.py -q` | exit 0；`3 passed` |
| PYTEST-ALL | `$ProjectPython -m pytest -q` | exit 0 |
| RUFF | `$ProjectPython -m ruff check pyproject.toml src tests` | exit 0 |
| MYPY | `$ProjectPython -m mypy src` | exit 0 |
| MODULE-HELP | `$ProjectPython -m aiflow --help` | exit 0；固定 description |
| MODULE-VERSION | `$ProjectPython -m aiflow --version` | exit 0；固定 version |
| EXE-HELP | existing `project-venv\Scripts\aiflow.exe --help` | exit 0 |
| EXE-VERSION | existing exe `--version` | exit 0 |
| MODULE-BAD | `$ProjectPython -m aiflow --definitely-unknown` | exit 2；usage/error，无 Traceback |
| EXE-BAD | existing exe 同一坏参数 | exit 2；usage/error，无 Traceback |
| DIFF-CHECK | `git diff --check` | exit 0 |
| STATUS | `git status --porcelain=v1 -z -uall` | exit 0；精确十二条 |
| STREAM-COMPARE | Action 分别逐字节比较 module/exe help、version、bad 的 stdout 与 stderr | exit 0 |

SYNC/PIP/SYNC-EXACT 等 File/arguments 必须逐字保持原批准 Phase D，不追加 `--offline`、`--no-index` 或其他参数。每个 uv/pip record 保存 raw stdout/stderr、cache inventory delta及工具明确输出的 `Using cached`/`Downloading`/URL/artifact path/size/SHA；这些只标注为 `tool_emitted_network_hints`，不是实际连接或 egress-host证明，空 URL 集合也只表示“日志未显示”。工具若显式请求 credential、non-HTTPS或 private index即停止；官方 redirect/CDN 不能由本证据排除，仍受主会话批准 boundary约束。再 Action 扫描八文件行尾空白、重算 hashes，验证 ignore、egg-info tracking、module/exe raw streams。记录 Python 3.13满足 `>=3.11`，Python 3.11未验证。

- [ ] **Step 3.4（2–5 分钟）: 最终 scope 与 chronology 校验**

独立 `git diff --check` expected exit 0；读取原始 NUL status 并与十二条集合完全相等；本文 SHA 与外部批准值相等；八文件、原计划、spec、final-v2 均未变化。Action 同时确认 replay/evidence 均位于 retained `AuditRoot`，没有 repo 内新路径、staged/deleted/rename/copy/typechange。输出结构化 `phase_d_complete=true` 与全部 log hashes。

## Task 4: 封存 remediation evidence、final-v3 与状态交接

**Artifacts / Locations:**
- Sealed index: `$AuditRoot\evidence\implementation-index-tdd-replay-$AttemptId.jsonl` 及 sidecar
- Manifest: `$AuditRoot\evidence\implementation-manifest.final-v3.json` 及 sidecar
- State handoff: 两个既有 state YAML

- [ ] **Step 4.1（5–10 分钟）: 封存新 index，保留全部旧证据**

append-only remediation index 收录 exact persistent PowerShell path/args/PID/edition/5.1 assertions、完整 runner payload evidence及expected/computed SHA/contract self-test、legacy runner historical hash、每个 preflight、archive/extract、目录创建/hash/copy、offline no-install、真实 red/red checkpoint/green、context revision、public-read配置边界/局限声明/tool-emitted network hints、Phase D、diff/status/raw-stream 的命令、expected/actual exit、stdout/stderr/action hashes、UTC、actor 和 invalidation result。封存前再断言仍是同一 PID/payload SHA并验证 red checkpoint prefix，随后写无 BOM/无换行 SHA sidecar并停止追加。显式引用且不改写：

- premature initial index `implementation-index.jsonl` SHA `9e4b2e9cd6b3482217e34b1b153d9306486c049a2259f8275f8032e222c61903`；
- sensitivity repair index `implementation-index-repair-1.jsonl` SHA `880328943a135d2df65c40ac0388e6a6f8331a0194be370fd0be20cd24f433ed`；
- integrity index `implementation-index-integrity-repair.jsonl` SHA `8ca3541ac92336f0bc899150e70ae56dea39b6f0fb6cf6fc118188d7094380e8`；
- prior final-v2 与 spec FAIL 的固定 path/hash。

旧 premature/sensitivity records 的语义保持不变，新 replay 是 decision 授权的补充 chronology，不是历史改名或覆盖。

- [ ] **Step 4.2（5–10 分钟）: 生成 final-v3 manifest**

`implementation-manifest.final-v3.json` 目标必须不存在；manifest 至少绑定：原计划与本文外部批准 SHA；`DEC-T1.1-TDD-REPLAY-001`；reviews、A/B events和独立 preflight；public-read配置/lock/index evidence、工具日志 hints及“无 packet-level host证明”局限；spec FAIL/final-v2/prior indexes；context rev6+ chain；AuditRoot/AttemptId；exact persistent PowerShell path/args/PID/edition/5.1；完整 runner payload evidence、expected/computed SHA/contract、legacy runner historical hash；replay paths；baseline HEAD/archive/inventory；五文件/red/checkpoint/三 source/green hashes与 chronology；ProjectPython/uv/venv/cache；Phase D；当前八文件；十二条 NUL records；Python 3.11未验证；`subject_commit: N/A`；retention/high-risk禁令。manifest 不纳入尚未发生的 fresh reviews；写 sidecar后不改写。若 final-v3 已存在或本轮需修复，新建 final-v4+，不可覆盖。

- [ ] **Step 4.3（2–5 分钟）: chapter-first 记录 implementation handoff**

原 executor只回报 `{AuditRoot, latest context revision/digest, sealed index path/hash, final-v3 path/hash, AttemptId}`，不写 state。状态代理 loader 验证后先更新 chapter：Task 保持 `in_progress`，`completed_steps: [1,2,3,4]`、`in_progress_step: 5`，blocker 转 `remediation_pending_fresh_spec`，计数不变；追加绑定 manifest/index/context/计划 SHA 的 handoff evidence/history。chapter 成功后才同步 overall `in_progress`、current step 5，计数不变。独立 diff/status 仍应 exit 0/精确十二条。

## Task 5: fresh spec→fresh quality→完成状态

**Artifacts / Locations:**
- Fresh review records: `$AuditRoot\evidence\spec-review-task-1-1-tdd-replay-$AttemptId\` 与 `quality-review-task-1-1-tdd-replay-$AttemptId\`
- Completion state: 两个既有 state YAML

- [ ] **Step 5.1（5–10 分钟）: fresh spec 独立复核补救 gate**

主会话派发从未参与实现的新 spec reviewer；只给批准计划/decision、latest context tuple、final-v3/index 和固定材料，不给口头豁免。reviewer 重算 hashes/status，确认 A/B分离；主会话明确批准 public-read evidence boundary且 records没有把 uv/pip普通日志冒充 egress证明；host-level enforcement要求不存在，否则已 blocked。确认所有 remediation动作由 exact PowerShell path/args的同一 PID、Desktop 5.1承载，canonical runner payload在 preflight前按 UTF8-noBOM/LF重算并匹配 expected SHA、完整写 evidence且仅内存加载，legacy runner从未执行/dot-source。再确认 replay来自授权 HEAD archive、目录顺序正确、测试/config byte-identical、red前 `src`/installed aiflow absence、checkpoint先于 src目录、red/green command identity相同、red exit1/三个 child `No module named aiflow`、source hashes、green exit0/`3 passed`、Phase D、旧 FAIL与scope全通过。record给明确 PASS/FAIL、逐项 pointer和SHA。

FAIL 时状态代理追加 immutable FAIL/history，Task/chapter/overall 回 `needs_revalidation`，`SPEC-BLOCKER-001` 保持 open，计数不变，quality 不得开始；主会话把 latest tuple/FAIL 交回同一原 executor。范围未变时新 attempt、新 index、新 manifest 版本、重跑受影响 replay 与完整 Phase D 后再 fresh spec；Policy/规格/计划/HEAD/允许范围变化则先回 REVIEW 重新批准。

- [ ] **Step 5.2（5–10 分钟）: 仅在 spec PASS 后 fresh quality**

状态代理先 chapter→overall 记录 fresh spec PASS 和 record hash，blocker 转 `remediation_pending_fresh_quality`，Task 仍 in_progress/step 5、计数不变。主会话再派发另一名 fresh quality reviewer；其独立验证当前八文件与 manifest/index hashes、pytest/Ruff/mypy、CLI module/exe help/version/bad raw streams、lock、line endings、ignore、diff/status、最小实现、可维护性与无多余行为，输出明确 PASS/FAIL record/hash。quality reviewer 不得重判或降低 spec gate。

quality FAIL 同样 chapter→overall 记录，Task/chapter/overall `needs_revalidation`、计数不变，回原 executor；修复后必须新 context revision/index/manifest、重跑完整 Phase D，并严格重新走 fresh spec→fresh quality，旧 PASS/FAIL 全保留。

- [ ] **Step 5.3（2–5 分钟）: 双 PASS 后完成 Task 1.1**

仅当 latest fresh spec 与 fresh quality 都 PASS，状态代理 loader 验证两份 record、final manifest、context、计划 SHA、八文件和十二条 status。先 chapter：解决 `SPEC-BLOCKER-001`，Task 1.1 `completed_steps: [1,2,3,4,5]`、`in_progress_step: null`、`status: completed`；chapter 保持 `in_progress`，chapter counters tasks +1/steps +5，指针移到 Task 1.2。chapter 成功后才 overall：tasks_completed +1、steps_completed +5，chapter-01/overall 保持 `in_progress`，current task `1.2`、current step null。最后独立 `git diff --check` exit 0、NUL status 精确十二条；保留整个 `AuditRoot`，不 commit/push/merge/deploy。

## 全局失效与回报规则

- 每个 Native/Action 调用都是独立 2–10 分钟以内步骤，expected exit/pattern 与实际结果都写结构化 record；launch/resolve/log 异常沿用原 runner exit 125，evidence sink 不可用 exit 126，均立即停止。
- exact `powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass` 的 path/Desktop/5.1断言先于所有 remediation 动作；随后 `AttemptId`、fallback/index、完整 payload evidence及 expected SHA比较必须先于任何 audited loader/preflight。payload只在同一 persistent session内存加载，不创建 runner文件；preflight FAIL 保留 attempt/index/payload evidence且 ReplayRoot不存在，legacy `execute.ps1` 永远只作 historical evidence。
- 同一 attempt 内任何 hash、path containment、context chain、HEAD、status、command identity、chronology、输出语义或 review 前置不相等都使该 attempt 失效；后续成功不能覆盖先前失败。
- replay 的 no-install-project 保持 `--offline`；Phase D 保持 exact arguments并使用主会话批准的 configuration/lock/index read evidence boundary。显式 credential、non-HTTPS、private index、upload/pay、GitHub uv重下载立即停止；需要 proxy/packet-level host enforcement 时 blocked，工具缺失或 Python 3.11要求变化回 REVIEW。
- 原 executor 不可用属于中断恢复；替补必须由主会话明确批准并加载 latest recorded context/资产，不能重建 AuditRoot 或抛弃历史。
- 最终 executor/reviewer/state agent 只向主会话回报路径、SHA、tuple、PASS/FAIL 和精确 status；主会话审核后再驱动下一代理，不在主会话内代执行工程步骤。

Plan complete and saved to `docs/superpowers/plans/2026-08-02-chapter-01-task-1-1-tdd-replay-remediation.md`. Recommended next step: use `subagent-driven-development` so approval, state transitions, the single original executor, fresh spec, and fresh quality each receive an explicitly scoped agent handoff.
