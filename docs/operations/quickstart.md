# AI Flow Quickstart

本指南从干净 `git clone` 开始，默认只在当前克隆内创建虚拟环境和演示任务记录。它不执行
commit、push、merge、deploy 或任何外部动作。项目要求 Python 3.11 或更高版本；推荐使用
仓库根目录已提交的 `uv.lock` 建立可复现环境，同时保留标准 `venv` + `pip` 回退路径。

这里安装的是 harness-model 的完整克隆，不是任意项目的一键接入流程。若要用于 ZCode
或已有业务仓库，先看[接入指南](adoption.md)，不要把本仓身份、账本和维护标记复制过去。

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
uv pip check --python .\.venv\Scripts\python.exe
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m aiflow --help
```

### macOS/Linux

```sh
git clone <REPOSITORY-URL> harness-model
cd harness-model
uv lock --check
uv sync --locked --all-extras
uv pip check --python .venv/bin/python
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

本页安装与环境命令仍从克隆根目录运行。完成安装并选中该克隆的 Python 环境后，业务
CLI 可从 Git 工作树根或内部子目录调用；内部任务、Policy、模板及默认 Schema 使用
Git 定位根，Schema 来自 `<root>/.ai/schemas`。用户显式输入、输出文件的相对路径仍以
调用目录为准，CLI 不改变工作目录。非 Git、嵌套仓库及完整外仓接入边界见
[接入指南](adoption.md#完整引擎的跨仓库边界)。

## 环境自检与常见问题

在已有克隆中，可先运行下列只读检查。`--dry-run` 只报告同步计划，不安装、删除或升级包。

```powershell
uv lock --check
uv sync --locked --all-extras --dry-run
.\.venv\Scripts\python.exe -c "import sys; print(sys.executable)"
uv pip check --python .\.venv\Scripts\python.exe
.\.venv\Scripts\python.exe -m aiflow --help
```

macOS/Linux 将最后三条命令中的 `.\.venv\Scripts\python.exe` 换成
`.venv/bin/python`。

- `No module named aiflow` 通常表示命中了系统 Python。改用项目解释器，或在项目虚拟环境中
  重新执行 editable 安装；不要用全局安装掩盖解释器选择错误。
- 能导入模块也不证明当前解释器的安装元数据与源码一致。质量检查显式使用按锁文件建立的
  项目 `.venv`；若包版本或依赖来自其他安装，先核对 `sys.executable` 与项目环境再运行检查。
- `uv sync --locked` 报告锁文件过期时，不要移除 `--locked` 或顺手重写锁文件。先运行
  `uv lock --check`，再将依赖或锁文件变更作为单独受治理任务处理。
- `pip` 或 uv 的新版本提示不代表项目依赖损坏。以当前安装前端的 `pip check` 或
  `uv pip check`、锁文件检查和项目测试结果为准，不需要仅为消除提示而升级项目环境。
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

2. 在 `freeze` 和首次 `classify` 前，用 `facts` 录入已评估的决策单元风险事实。
先将下列示例保存为本地 UTF-8 `build/local/facts.json`；`build/` 由仓库已提交的忽略规则排除，本地输入不要提交。
示例值只适用于已核实满足这些条件的本地文档工作，
不能作为未知风险的默认值。不要直接编辑 `task.yaml`。

```json
{
  "scope": {"clear": true},
  "impact": {"level": "low"},
  "protections": {"verified_backup": true, "dry_run": true},
  "verification": {"automatic": true, "tools_missing": false},
  "impact_categories": ["documentation"],
  "controlled_actions": [],
  "business_direction_count": 1,
  "change_characteristics": {
    "mechanical": false,
    "behavior_changed": false,
    "code_modified": false,
    "interaction_scope": "local",
    "regression_risk": false,
    "error_detectability": "high"
  }
}
```

这里的 `controlled_actions: []` 表示已确认本地文档示例不执行部署或生产数据删除，
不是尚未评估风险时的默认值。`start` 生成的单元为 `DU-001`；其他任务使用其真实 DU ID。
在 PowerShell 或 POSIX shell 中分别运行预览和应用：

```console
python -m aiflow facts <TASK-ID> --decision-unit DU-001 --input build/local/facts.json --actor quickstart --dry-run
python -m aiflow facts <TASK-ID> --decision-unit DU-001 --input build/local/facts.json --actor quickstart
```

预览和应用使用相同的合同与资格校验；`--dry-run` 对任务工件零写入。输入相对路径仍以调用目录为准，
因此从子目录运行时应指向该目录实际可读的 JSON 文件。字段替换和恢复限制见下节。

3. 分类并查看只读状态。

```powershell
python -m aiflow classify <TASK-ID> --actor quickstart
python -m aiflow status <TASK-ID> --format json
```

```sh
python -m aiflow classify <TASK-ID> --actor quickstart
python -m aiflow status <TASK-ID> --format json
```

对上述低影响、可逆、无外部副作用的完整事实，预期 route 为 `AUTO`。若决策单元的 `impact_scope` 触及治理面（`.github/**`、`.ai/**`、`src/aiflow/**`、`tools/ci/**`、`AGENTS.md` 等，清单见 `HARD-REVIEW-GOVERNANCE-SURFACE`），无论自报影响如何，route 至少为 `REVIEW`。两风险字段缺失时，
先处理上述零写输入错误；其他事实不足则按 Policy 分类，若得到可解释的 `BLOCK`，
应按 [恢复手册](recovery.md) 处理，不直接改写状态。

4. 运行 Gate 以观察具体缺失条件。因为示例没有实施、commit 或验证，这一步应返回非零退出码和 `passed: false`；这是正确的安全拒绝。

```powershell
python -m aiflow gate <TASK-ID> --format json
```

```sh
python -m aiflow gate <TASK-ID> --format json
```

## 分类前风险事实录入

`facts` 仅接受 `current_state=NEW`、尚无冻结规格字段、分类记录或待物化分类工件的任务。
当前仓库身份、分支和 HEAD 必须匹配任务原有 repository／branch／base／subject 绑定；
草稿文件变脏不授权更新 Git 基线。仓库没有 `DRAFT` 状态。命令仅修改一个已存在的指定 DU，
不修改目标、范围路径、身份、Git 绑定、状态、批准或验证证据，也不自动冻结、分类、派发审核或执行动作。

输入必须是一个非空的本地 UTF-8 JSON object。允许替换的 DU 顶层字段仅有：
`scope`、`impact`、`protections`、`verification`、`impact_categories`、`controlled_actions`、
`business_direction_count`、`change_characteristics`、`verification_requirements`、`reversibility`、
`external_side_effects` 和 `permission_requirements`。每个提供的顶层字段都**整体替换**原字段，
不递归合并局部嵌套对象；嵌套对象须满足既有完整 Schema。省略字段保留原来的存在性和值，
不会推断风险事实或补默认值。非法 JSON、任意深度的重复键、非有限数值、未知字段、无效类型或不满足完整结果合同的输入均被拒绝；
即使只改一个 DU，也校验全部 DU 和完整任务。录入内容是 actor 的声明，不是事实真实性的独立验证。

成功输出 JSON，包含 `task_id`、`decision_unit_id`、`dry_run`、`changed`、`applied`、`recovered`、
`before` 和 `after`；前后值是所选 DU 中实际存在的完整风险字段投影。普通应用与原值相同时，
不追加事件、不改变时间戳。有变化的应用追加一个带 DU、actor 和前后投影的 `risk_facts_recorded` 事件，
再以该事件时间物化任务。这复用仓库单写入者下的暂存／追加／替换流程，不承诺跨进程隔离或任意 I/O 失败下的原子性。

结果 JSON 使用 ASCII 转义，兼容 Windows GBK 等管道编码；解码后的中文、emoji 和字段值保持原样。新写入的任务 YAML 使用标准字符转义，避免 U+0085 被 YAML 折叠为空格；已有文件不重写，事件继续以 UTF-8 保存原文。事件正文或 actor 中合法的 U+0085、U+2028、U+2029 不作为记录边界，后续读取与重复应用保留其原值。

若事件已完整追加而任务替换中断，只有**同一 DU、actor 且产生相同完整结果的等价有效更新**可以在精确核对后续完一次替换；
必须保留原事件、时间戳及有效 `task.yaml.next`，不能手工修暂存文件。核对不绑定 JSON 排版或原始键集合；
改变更新结果的输入会被拒绝。恢复不追加第二个事件。
预览不恢复；普通加载器也不自动修复此类替换。追加结果不确定、日志部分写入／损坏、暂存文件未知／不匹配、
或缺少必要恢复材料时，保留原工件并报错，不自动重试。

严格读取遇到任意待物化 `task.yaml.next` 即拒绝；即使暂存文件丢失，已记录但未物化的风险事实也会阻断首次分类。
冻结等 `NEW` 自环事件不解除这一屏障。首次合法的 `NEW → CLASSIFIED` 记录后，
后续风险变化继续走既有 `escalate`、显式人工重评估、`resolve` 和重新 `classify` 流程；
历史 facts 事件不会永久锁住后续合法重评估，`facts` 命令自身仍只用于上述合格 `NEW` 任务。

省略 `impact_categories` 或 `controlled_actions` 不会绕过首次分类的明确评估要求；`classify` 会在路由前列出缺项，
且不写任务或分类记录。按实际事实用 `facts` 补齐后再分类，不自动转为人工审核，也不预定 `AUTO` 结果。

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

实际任务是否需要 task，以 [AGENTS.md](../../AGENTS.md) 的维护模式及升级清单为准。选择进入 AI Flow 时，先在合格 `NEW` 状态用 `facts` 补齐显式风险事实，再冻结 `spec.md` 并分类，按 route 执行 ASK/REVIEW 决定或批准，然后运行 `begin`、实施、`sync`、`verify` 和 Gate。所有命令都以 `python -m aiflow ...` 为权威入口。

具体动作的授权以 [AGENTS.md「常设授权」](../../AGENTS.md#常设授权) 为唯一权威；先核对既有批准及常设授权覆盖，不重复请求已覆盖的决定。本页演示任务显式禁止 push、merge、deploy 和 delete，继续演示仍须遵守这些任务范围。

## REVIEW 双阶段审核

`status`、`gate` 与 `review show` 的 `--format json` 在参数解析成功后遇到领域错误时，
向 stderr 输出只含 `code` 和 `message` 的 JSON，stdout 为空，退出 `1`。内部 details
和异常原因不输出；文本模式仍输出一行错误消息。非法参数沿用 argparse 的 usage 与退出 `2`；
有效但未通过的 Gate 决策仍在 stdout 输出原 JSON 并退出 `2`。读取到非法 UTF-8 任务文档时，
错误码为 `STORAGE_READ_FAILED`，原文件保持不变。

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

新生成 evidence 的命令摘要中，已知的 Python 解释器、仓库根目录和运行目录分别以 `${PYTHON}`、`${REPO_ROOT}` 和 `${RUN_DIR}` 表示；这些只是展示占位符，不改变实际执行的命令或检查。CI evidence 的复现命令使用 `${CI_RUN_DIR}` 和 `${CI_EVIDENCE}`；手动重放前须替换为已存在的运行目录及该目录下的直接子文件。既有 evidence 保持原样。

## 记录已完成的合并

外部 PR 与 required CI 核对完成后，使用完整的 40 位小写合并提交 SHA 关闭已批准任务：

```sh
python -m aiflow close <TASK-ID> --result merged --merge-commit <MERGE-SHA> --actor <INTEGRATOR>
```

`close` 要求任务处于 `APPROVED_FOR_MERGE` 且仓库身份一致。它在当前本地 Git 视图中要求该提交至少有两个父提交，并对至少一个非第一父提交验证 `base_commit → subject_commit → incoming parent`。允许相等、受审候选之后的治理提交，以及多父合并；普通提交、无关合并或仅第一父包含候选时拒绝关闭。Git 检查失败或事实不可用时返回错误，不记录合并。

该命令只核对本地必要条件并追加关闭记录，不执行 Git 合并、fetch 或网络操作，也不认证具体 PR、目标分支、远端完成状态或 required CI。发布时仍须分别核对这些外部事实；历史 `MERGED` 记录不重新裁定。

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

active Policy `2.6.0` 下，`unit_tests`、`regression_tests`、`coverage_xml` 以及 V2 的
`acceptance`、`integration` 共用同一条完整覆盖率命令
`python -m pytest --cov=aiflow --cov=tools/analysis --cov-branch --cov-report=xml:<run>/coverage.xml`，计划引擎将其合并为
一次执行；各检查 ID 仍分别出现在 evidence 中，但共享同一进程结果与日志，失败不再按子集归因。
V2 另有由单独 action approval 绑定的 targeted mutation，independent Verifier 也必须与
Implementer 使用不同的非空 task-local actor 标签。Chapter 11 的 acceptance、integration、
action-approved targeted mutation 与 independent-verifier 流程均已实现。

这次共享的完整 pytest 执行上限为 1200 秒，为 Windows 已验证运行时留出波动余量。
CI 与原生 V1/V2 随后统一调用
`python tools/ci/check_coverage.py --run-dir <run_dir> --base <base_commit>`，从同一次分支覆盖率数据
分别检查 `src/aiflow` 与 `tools/analysis`：每个目录的总覆盖率均须达到 85%，变更覆盖率均须达到
90%，不能互相补足。原生检查仍使用 `diff_coverage` 类别及既有 required 状态；strict mypy 同时
检查这两个目录。达到执行上限或任一门槛失败仍是验证失败，必须保留 run 并诊断原因，不能靠降级、
跳过 coverage 或无理由重复重试进入 Gate。

`verify` 已移除 `--pytest-temp-root`，不再接受该选项。未显式指定 pytest 的 `--basetemp` 时，
本仓测试入口在操作系统临时目录中为每次调用创建独立的短路径根，不使用或清理其他运行的编号目录。
显式 `--basetemp` 保持优先，调用者须选择自己拥有的目录；分发测试的临时根还须位于源码树外。
测试根保留供诊断，只在确认本次子进程已结束且材料不再需要后清理该精确目录。
手工质量重放仍按下文将 coverage 数据写入独立 run directory；这与 pytest fixture 临时目录是不同用途。

使用 `--check` 选择任一 pytest 检查（如 `acceptance`、`integration`）时，仍运行完整覆盖率套件；选择其他检查只运行所选检查。所得
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
先运行自动追踪和四类负向自举回归，再执行静态检查及下文的一次完整覆盖率运行。
以下命令显式使用锁文件配置的项目解释器；macOS/Linux 将 `.\.venv\Scripts\python.exe`
换成 `.venv/bin/python`。

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_acceptance_traceability.py -q
.\.venv\Scripts\python.exe -m pytest tests/acceptance/test_phase_02_self_hosting.py tests/integration/test_phase_02_self_hosting.py tests/e2e/test_phase_02_self_hosting_scenario.py tests/e2e/test_phase_02_negative_self_hosting.py -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy src tools/analysis
git diff --check
```

覆盖率命令必须把数据库和 XML 写入精确的独立 run directory，不能写入仓库根。下面的
PowerShell 示例在操作系统临时目录中为本次运行创建唯一目录；命令以 `origin/main` 的共同
祖先作为本次变更覆盖比较的 base。若任务冻结了不同的 base commit，应把 `$baseCommit`
改为该精确 SHA。完整 pytest 同时收集两个目录的分支覆盖率，再由固定检查器检查各自门槛：

```powershell
$runId = "harness-model-quality-{0}" -f ([guid]::NewGuid().ToString("N"))
$runDir = Join-Path ([System.IO.Path]::GetTempPath()) $runId
$coverageFile = Join-Path $runDir ".coverage"
$coverageXml = Join-Path $runDir "coverage.xml"
$baseCommit = (git merge-base HEAD origin/main).Trim()
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
$env:COVERAGE_FILE = $coverageFile
try {
    .\.venv\Scripts\python.exe -m pytest -q --cov=aiflow --cov=tools/analysis --cov-branch --cov-report=term-missing --cov-report="xml:$coverageXml"
    if ($LASTEXITCODE -ne 0) { throw "coverage pytest failed with exit $LASTEXITCODE" }
    .\.venv\Scripts\python.exe tools/ci/check_coverage.py --run-dir $runDir --base $baseCommit
    if ($LASTEXITCODE -ne 0) { throw "coverage checks failed with exit $LASTEXITCODE" }
}
finally {
    Remove-Item Env:COVERAGE_FILE -ErrorAction SilentlyContinue
}
```

检查器从 `$runDir/.coverage` 生成 `coverage-core.xml` 和 `coverage-analysis.xml`，每个目录均须
满足总分支覆盖率不低于 85%、相对 `$baseCommit` 的变更覆盖率不低于 90%。未执行的 Python 文件
仍计入各自分母；数据缺失、无分支数据或某个目录完全未测量均失败。合并的 `coverage.xml` 供查看，
其总数不能代替两个目录分别通过。纯文档等没有可测新增行的 diff 可为空，但有效覆盖率数据仍是前提。
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
