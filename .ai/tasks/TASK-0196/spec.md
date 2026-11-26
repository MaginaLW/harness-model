# Task Specification

## 目标

为外部 Python 仓库新增非覆盖命令 `aiflow init render-python-policy`，从内置或指定资源包渲染面向目标包与源码域的 4 份候选 Policy 文件并完成 V0/V1/V2 结构验证，供 `init preview` / `init apply` / `init migration-plan` 消费。

## 范围

仅允许修改与新增以下文件：
- `src/aiflow/verification.py`：导出公共函数 `validate_coverage_target(target: str) -> str`（复用 `_COV_TARGET_PATTERN`），并在 `_is_valid_pytest_argv` 中复用，避免跨模块导入私有符号。
- `src/aiflow/initialization.py`：新增 `render_python_policy(output_dir: Path, *, cov_target: str, sources: Sequence[str], bundle_root: Path | None = None) -> dict[str, Any]`，复核既有 `read_bundle`、`_plain`、`load_policy_bundle`、`parse_verification_plan`、`validate_source_domain` 等内部路径，在参数及外部 I/O 边界校验输入与文件状态，在临时目录完成 schema 与 V0/V1/V2 校验后再原子非覆盖创建输出目录与 4 份规范化 UTF-8/LF Policy 文件。
- `src/aiflow/cli.py`：在 `init_commands` 注册 `render-python-policy`（`--output-dir`、`--cov-target`、`--source` 重复传入、`--bundle-root` 可选）并在 `_dispatch_initialization` 中分派（先于 `else:` 分支）。
- `tests/unit/test_render_python_policy.py`：新增单元测试覆盖核心函数、校验拒绝路径、非覆盖拒绝、符号链接/重解析点拒绝、损坏/缺失资源包、CLI 退出码及与 `init preview`/`apply`/`migration-plan` 串联，保证新增/修改行分支覆盖率 >= 95%。
- `tests/integration/test_external_python_verify.py`：新增集成测试覆盖 `aiflow init render-python-policy` -> `init preview` -> `init apply` -> V1 `verify` -> `advise` -> `gate PASS`。
- `docs/operations/initialization.md` 与 `CHANGELOG.md`：补充 `aiflow init render-python-policy` 操作文档及 `## Unreleased` `### Added` 条目。

## 非目标

- 不修改本仓 `.ai/policy/*` 既有策略文件、阈值（85% 总分支覆盖率与 90% diff coverage）或 `policy_version`。
- 不实现自动执行 `init preview`/`init apply`、不修改已有 `.ai` 安装目录、不跳过外部审核直接写入目标仓库 `.ai`。
- 不引入未请求的额外 CLI 参数、配置文件格式、策略模板变量或顺手重构无关初始化函数。

## 验收条件

1. `.\.venv\Scripts\python.exe -m pytest tests/unit/test_render_python_policy.py tests/unit/test_import_boundaries.py tests/unit/test_cli.py tests/unit/test_cli_error_output.py tests/integration/test_external_python_verify.py` 全部通过，且新增/修改行分支覆盖率达标。
2. `.\.venv\Scripts\python.exe -m ruff check .`、`.\.venv\Scripts\python.exe -m ruff format --check .`、`.\.venv\Scripts\python.exe -m mypy` 与 `git diff --check` 全部退出 0。
3. 完整本地原生 V1 `.\.venv\Scripts\python.exe -m aiflow verify TASK-0196 --actor verifier-v1` 10/10 全项通过，核心分支覆盖率 >= 85%，diff coverage >= 90%。
4. 独立设计审核（`REV-0001`）与实现审核（`REV-0002`）均为 `APPROVE` 且无未关闭 critical/high 发现，`aiflow gate TASK-0196 --format json` 退出 0（`"passed": true`）。

## 禁止动作

- 不得覆盖已存在的 `output_dir` 或其中的文件；不得跟随符号链接或 Windows 重解析点写入。
- 不得修改 `hard-rules.yaml`、`routing.yaml`、`permissions.yaml` 的内容，亦不得放松 `verification-levels.yaml` 的 `allowed_commands`、`allowed_placeholders`、`allowed_environment` 或覆盖率门槛。
- 不得提交 `.ai/tasks/TASK-0196/logs/`、本机绝对路径、用户名或机器名；不得绕过独立审核或 Gate 直接推送/合并。

## 错误行为

- 当 `cov_target` 不满足 `validate_coverage_target` 时，抛出 `INITIALIZATION_PYTHON_COV_TARGET_INVALID`。
- 当 `sources` 为空或任一项不满足 `validate_source_domain` 时，抛出 `INITIALIZATION_PYTHON_SOURCE_INVALID`。
- 当 `output_dir` 含 `..` 路径遍历、已存在（`os.path.lexists`）或其父目录不是普通真实目录（如符号链接/重解析点或非目录）时，拒绝并不创建任何目录或文件。
- 当资源包缺失、损坏、非文件系统路径或阶段化后的 4 份策略在临时目录未通过 schema / V0 / V1 / V2 解析校验时，在创建 `output_dir` 前失败退出，不遗留半成品目录。

## 回滚

- 本任务尚未合入 `main` 前，在工作分支上执行 `git switch main && git branch -D codex/w4-init-render-python-policy` 即可完整丢弃变更；若已创建提交但未合并，可用 `git revert` 撤销对应提交。
- `render-python-policy` 仅在校验通过后创建全新输出目录；运行期失败不会产生目标目录或修改既有目标仓库。
