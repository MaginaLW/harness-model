# TASK-0192 · 支持跨仓 Python 验证的可移植覆盖率检查与验证计划

## 目标

在基线 `f9420c095fd9648d878717bdf7e1f12a4f65a688`（分支 `codex/d21-cross-repo-python-verify`）上交付跨仓 Python 验证支持（D2.1）：将核心覆盖率检查逻辑抽离至可安装的 `src/aiflow/coverage_check.py` 模块并保留 `tools/ci/check_coverage.py` 兼容薄包装，同时扩展 `src/aiflow/verification.py` 对 `PYTEST_CHECK_IDS` 与 `diff_coverage` 的可移植校验契约，使外部 Python Git 仓库无须内置 `tools/ci/` 或 `aiflow` 源码即可执行完整 V0/V1 验证与 Gate。

## 范围

仅允许修改以下路径（以及 `.ai/tasks/TASK-0192/**` 治理账本，不含 `logs/`）：
- `src/aiflow/coverage_check.py`（新增）：从 `tools/ci/check_coverage.py` 提取 `check_coverage(repository, run_dir, base, *, domains=DEFAULT_DOMAINS)`（`DEFAULT_DOMAINS = (("core", "src/aiflow"),)`）；在函数体内延迟导入 `from coverage import Coverage` 以避免未装 dev 依赖时导入 `aiflow` 报错；提供严格 `_validate_source_domain(source)` 校验（仅允许非空、无前后 `/`、无 `.`/`..`、无 `\`/`:`/空白/控制字符且解析路径严格位于 `repository` 内的仓内相对 POSIX 目录）；CLI `main(argv)` 接受 `--run-dir`、`--base`（40 位小写十六进制 SHA）及可选 `--source`，硬编码 `>= 85%` 总分支覆盖率与 `>= 90%` 差异覆盖率门禁且不提供降阈值开关。
- `tools/ci/check_coverage.py`（修改）：保留为向后兼容的薄包装，维持 `DOMAINS = (("core", "src/aiflow"),)`、`check_coverage(repository, run_dir, base)` 与 `main(argv)` 接口。
- `src/aiflow/verification.py`（修改）：在 `_require_output_semantics` 与 `parse_verification_plan` 中，为 `PYTEST_CHECK_IDS` 支持匹配安全包名/相对路径模式 `^[A-Za-z_][A-Za-z0-9_.]*(?:/[A-Za-z_][A-Za-z0-9_.]*)*$` 的 `--cov=<target>`，并要求同级所有 `PYTEST_CHECK_IDS` 使用完全一致的 `--cov=<target>` 以保持单次共享 pytest 执行去重；为 `diff_coverage` 接受原精确形式 `(context.python, "tools/ci/check_coverage.py", "--run-dir", run_dir.as_posix(), "--base", context.base_commit)` 或可移植模块形式 `(context.python, "-m", "aiflow.coverage_check", "--run-dir", run_dir.as_posix(), "--base", context.base_commit, ...)`（可选若干经 `_validate_source_domain` 校验的 `--source <rel_dir>` 成对参数），保持 `environment == {}`、`timeout_seconds == 120`、`required is True`、`result_parser == "exit_zero"`、`threshold == 90`。
- `tests/unit/test_coverage_check.py`（新增）：覆盖 `--source` 合法/非法路径校验、缺失 `.coverage`、非分支数据、总覆盖率与差异覆盖率通过/失败情形（`coverage_check.py` 分支覆盖率 `>= 95%`）。
- `tests/unit/test_verification_plan.py`（修改）：补充可移植 `--cov=<pkg>`（跨检查不一致与不安全路径拒绝）及 `-m aiflow.coverage_check --source ...`（不安全 `--source`、非 90 阈值拒绝、保留历史 `tools/ci/check_coverage.py` 兼容）的正反向单元测试。
- `tests/integration/test_external_python_verify.py`（新增）：构建自包含外部 Python Git 临时仓库（不含 `aiflow` 源码与 `tools/ci/`），配置可移植 `.ai/` Policy，端到端执行 `start -> facts -> classify -> freeze -> begin -> verify`（V0/V1）-> `gate` 通过。

已有能力复用与边界说明：
- 复用既有 `coverage`、`diff_cover.diff_cover_tool`、`verification.py` 与 `policy.py` 解析路径；仅在外部输入（`--source`、`--base`、Policy `--cov=`/`--source` 参数、路径解析）边界做严格校验与拒绝。

## 非目标

- 不修改 `.ai/policy/*.yaml`、`.ai/schemas/*.json`、`pyproject.toml`、`src/aiflow/cli.py`、`src/aiflow/initialization*.py`。
- 不修改 V0/V1 任何检查阈值（85% 总分支覆盖率、90% diff coverage 保持不可配置/不可降低）。
- 不修改 `smoke` 命令约束（保持 `("-m", "aiflow", "--help")`），不增加未请求的覆盖率配置文件或备用执行路径。

## 验收条件

1. `tests/unit/test_coverage_check.py`、`tests/unit/test_verification_plan.py`、`tests/unit/test_coverage_gates.py`、`tests/integration/test_external_python_verify.py`、`tests/integration/test_verify_command.py` 全部通过，`coverage_check.py` 与变更行分支覆盖率达到门禁要求。
2. `ruff check .`、`ruff format --check .` 与 `mypy`（覆盖 `src` 与 `tools`）零报错通过。
3. 正式运行 `aiflow verify TASK-0192 --actor verifier-v1`，V1 全部 10 项检查原生通过（全量测试、`core` 总分支覆盖率 >= 85%、diff coverage >= 90%、mypy、ruff）。
4. 独立设计审核与实现审核均为 `APPROVE`，`aiflow gate TASK-0192` 通过，PR 及 closeout PR 合入 `main` 且 Ubuntu `ai-quality-gate` 全绿通过。

## 禁止动作

- 禁止修改 `.ai/policy/*`、`.ai/schemas/*`、`pyproject.toml`、`src/aiflow/cli.py`、`src/aiflow/initialization*.py`。
- 禁止降低 `85%` 总分支覆盖率或 `90%` 差异覆盖率门槛，禁止提交 `.ai/tasks/TASK-0192/logs/`。
- 禁止跳过独立审核、禁止自审、禁止强推或绕过 Gate/CI。

## 错误行为

- 当 `--source` 包含 `..`、`.`、绝对路径、盘符、反斜杠、空白、控制字符或符号链接逃逸，或 `--base` 非 40 位小写十六进制 SHA，或 `--cov=` 匹配失败/同级检查目标不一致时，必须以明确 `ValueError` / `ContractError` 失败拒绝，不得回退或静默忽略。
- 若范围变化、分类非预期或 V1 验证失败，立即停止推进并按 `aiflow escalate` / `status` 规则处理。

## 回滚

所有改动均位于独立分支 `codex/d21-cross-repo-python-verify`；合入 `main` 前可直接丢弃分支，合入后可通过标准反向 PR 回滚，无需变更不可逆远端状态。
