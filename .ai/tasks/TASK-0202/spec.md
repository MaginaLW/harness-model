# Task Specification · TASK-0202

## 目标

在基线 `d991674c81b6e874007e11515336780800384cee`（分支 `codex/portable-closeout-check`）上将收尾与保留账本校验能力抽离至可安装的 `src/aiflow/closeout_check.py`，在 `src/aiflow/task_service.py` 公开所需辅助函数并保持私有别名向后兼容，将 `tools/ci/verify_closeout.py` 收敛为兼容薄包装，使仅安装 `aiflow` wheel 且无源码树/`tools/` 的外部仓库也能通过 `python -m aiflow.closeout_check` 直接使用目标仓库 `.ai/schemas` 完成收尾与保留记录校验，同时保持既有 `tools.ci.verify_closeout` 调用方与测试行为完全一致。

## 范围

仅允许修改以下 4 个文件（以及 `.ai/tasks/TASK-0202/**` 治理账本，不含 `logs/`）：
- `src/aiflow/task_service.py`：
  - 将 `_is_subject_sync_staged_patch` 与 `_require_merge_commit` 重命名/公开为 `is_subject_sync_staged_patch` 与 `require_merge_commit`（函数签名、校验逻辑与错误码保持不变），并在模块内保留 `_is_subject_sync_staged_patch = is_subject_sync_staged_patch` 与 `_require_merge_commit = require_merge_commit` 向后兼容别名（`load_task_record` 与 `close_task` 等内部调用可直接复用或通过既有名称调用）。
- `src/aiflow/closeout_check.py`（新增）：
  - 从 `tools/ci/verify_closeout.py` 迁入 `verify_closeout(root: Path, base: str, head: str, task_id: str) -> None`、`verify_retained(root: Path, base: str, head: str, task_id: str) -> None` 与 `main(argv: Sequence[str] | None = None) -> int`，并添加 `if __name__ == "__main__": raise SystemExit(main())` 入口；
  - 实现自包含只读 Git 子进程辅助函数 `_git_bytes(root: Path, *args: str) -> bytes`（`env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"}`、`timeout=20`、`check=False`，非零返回码抛出 `ValueError`），不导入 `tools.*`；
  - 仅从 `aiflow.*` 导入公共符号（`SCHEMA_RELATIVE_DIRECTORY`、`require_valid_contract`、`schema_directory_context` 来自 `aiflow.contracts`；`apply_risk_facts` 来自 `aiflow.decision_units`；`AiflowError` 来自 `aiflow.errors`；`replay_events` 来自 `aiflow.state`；`is_subject_sync_staged_patch`、`require_merge_commit` 来自 `aiflow.task_service`），严禁导入 `aiflow.node_*` 或 `aiflow.installed_*`；
  - 在 `verify_closeout` 与 `verify_retained` 执行所有契约校验前包裹 `with schema_directory_context(root / SCHEMA_RELATIVE_DIRECTORY):`，确保构建的 wheel 安装包在无源码检出的仓库中从目标 `root/.ai/schemas` 加载 Schema。
- `tools/ci/verify_closeout.py`：
  - 替换为兼容薄包装（对齐 `tools/ci/check_coverage.py` 风格），必要时将仓库 `src` 路径加入 `sys.path` 后从 `aiflow.closeout_check` 导出/转发 `verify_closeout`、`verify_retained` 与 `main`，并保留 `if __name__ == "__main__": raise SystemExit(main())` 入口。
- `tests/unit/test_verify_closeout.py`：
  - 保持全部既有 `tools.ci.verify_closeout` 测试不变并通过；
  - 新增直接调用 `aiflow.closeout_check` 与子进程执行 `python -m aiflow.closeout_check` 的测试，覆盖有效 closeout、有效 `--retained`、篡改/无效记录退出码 1，以及在脱离源码树工作目录/无相对 `.ai/schemas` 时从目标 `root/.ai/schemas` 加载 Schema 的便携性验证。

## 非目标

- 不修改 `.github/workflows/ai-quality-gate.yml`、`tools/ci/resolve_task.py`、`src/aiflow/coverage_check.py`、`src/aiflow/contracts.py`、`.ai/policy/*` 或 `.ai/schemas/*`。
- 不修改 `tests/integration/test_github_workflow.py` 与 `tests/unit/test_import_boundaries.py`。
- 不在本实施 PR 修改 `CHANGELOG.md` 或 `docs/operations/maintenance-status.md`（留待合并后的收尾 PR）。
- 不新增未请求的 CLI 参数、配置开关、缓存机制或额外的模块拆分。

## 验收条件

1. 目标测试集合全部通过：
   `.\.venv\Scripts\python.exe -m pytest tests/unit/test_verify_closeout.py tests/unit/test_import_boundaries.py tests/integration/test_github_workflow.py tests/integration/test_begin_close_commands.py -q`（包含 `aiflow.closeout_check` 直接 API 与 `python -m aiflow.closeout_check` 子进程在 valid closeout、valid `--retained`、tampered/invalid exit 1 与跨目录 `root/.ai/schemas` 加载场景下的断言）。
2. 静态检查全部退出 0：
   `.\.venv\Scripts\python.exe -m ruff check .`、`.\.venv\Scripts\python.exe -m ruff format --check .`、`.\.venv\Scripts\python.exe -m mypy`（覆盖 `src` 与 `tools`）与 `git diff --check`。
3. 契约与边界保持：
   `tests/unit/test_import_boundaries.py` 确认 `aiflow.closeout_check` 仅跨模块导入 `aiflow.*` 公共符号且不触发加载 `aiflow.node_*` / `aiflow.installed_*`；`tools/ci/verify_closeout.py` 保持与现有 CI 工作流及测试完全兼容。
4. 本地原生完整 V1 验证 `.\.venv\Scripts\python.exe -m aiflow verify TASK-0202 --actor closeout-author` 10/10 项全通过（核心分支覆盖率 >= 85%，diff coverage >= 90%）。
5. 独立设计审核（`REV-0001`）与实现审核（`REV-0002`）结论均为 `APPROVE` 且无未关闭 critical/high 发现，`aiflow gate TASK-0202 --format json` 返回 `"passed": true`（exit 0）。

## 禁止动作

- 禁止修改 `src/aiflow/task_service.py`、`src/aiflow/closeout_check.py`、`tools/ci/verify_closeout.py`、`tests/unit/test_verify_closeout.py` 之外的业务/测试/文档/治理文件。
- 禁止在 `src/aiflow/closeout_check.py` 导入 `tools.*`、`aiflow.node_*`、`aiflow.installed_*` 或任何 `aiflow.*` 私有（`_` 开头）符号。
- 禁止削弱 `verify_closeout` 或 `verify_retained` 的任何校验规则、移除 `GIT_OPTIONAL_LOCKS="0"` 或破坏 `_is_subject_sync_staged_patch` / `_require_merge_commit` 向后兼容别名。
- 禁止执行 `deploy`、`delete`、`secret_export`、`paid_external_call` 或绕过独立审核/Gate 直接合并。
- 禁止提交 `.ai/tasks/TASK-0202/logs/` 或在 tracked 文件及提交记录中写入本机绝对路径、用户名或机器名。

## 错误行为

- 当 task ID 不匹配 `TASK-[A-Z0-9][A-Z0-9-]*`、Git 命令失败或超时（20s）、任务不属于当前仓库、closeout 修改了 `task.yaml`/`events.jsonl` 之外的文件、追加事件非原生 `merge_recorded`、merge commit 不在目标分支历史中或不包含候选提交时，`verify_closeout` 必须抛出 `ValueError` 或 `AiflowError`，CLI `main()` 捕获后向 stderr 打印 `Ledger verification failed: <error>` 并返回退出码 `1`。
- 当 `--retained` 目标任务不处于 `FAILED`/`BLOCKED`、改写既有文件或删除原始材料、重写 `events.jsonl` 前缀、事件回放或审批集合不一致时，`verify_retained` 必须抛出 `ValueError` 或 `AiflowError`，CLI `main()` 返回退出码 `1`。
- 缺少必填 CLI 参数或未知参数继续沿用 `argparse` usage 输出与退出码 `2`。

## 回滚

- 合入 `main` 前可在工作分支 `codex/portable-closeout-check` 回退或丢弃提交并删除分支；合入 `main` 后可通过标准反向 PR（`git revert`）完整回滚全部 4 个文件的改动，无不可逆外部状态或数据格式迁移。
