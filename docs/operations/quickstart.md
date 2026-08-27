# AI Flow Quickstart

本指南从干净 `git clone` 开始，默认只在当前克隆内创建演示任务记录。它不执行 commit、push、merge、deploy 或任何外部动作。

<!-- required-path: pyproject.toml -->
<!-- required-path: .ai/policy/routing.yaml -->
<!-- required-path: tests/unit/test_specification.py -->
<!-- verify-command: python -m aiflow --help -->
<!-- verify-command: python -m pytest tests/unit/test_specification.py -q -->

## PowerShell

```powershell
git clone <REPOSITORY-URL> harness-model
Set-Location harness-model
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
python -m aiflow --help
```

## 平台中立 Python 入口

Windows 可将 `python3` 换成 `py -3.11`；macOS/Linux 通常直接使用 `python3`。激活命令是唯一的平台差异，后续统一使用 `python -m ...` 以确保命中当前虚拟环境。

```sh
git clone <REPOSITORY-URL> harness-model
cd harness-model
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
python -m aiflow --help
```

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
