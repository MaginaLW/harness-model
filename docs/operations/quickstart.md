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

## 继续实际任务前

用 `spec.md` 冻结可执行规格，然后按 route 执行 ASK/REVIEW 决定或批准，再运行 `begin`、实施、`sync`、`verify` 和 Gate。所有命令都以 `python -m aiflow ...` 为权威入口；未获单独批准时不执行 push、merge、deploy、delete、凭据或付费外部调用。
