# Review Package

## 审核目标

对 `TASK-0196`（`codex/w4-init-render-python-policy`，`base=c98faf9d7e5a7628ef2773ca5aaf7878894c98c0`..`subject=62ba9a683dba85614c64beed1bb7dbc7b0f3e568`）的实现与证据进行独立实现审核（`REV-0002`），裁决 `aiflow init render-python-policy` 及其公开覆盖率目标校验函数、单元测试、端到端集成测试和文档是否满足冻结规格与仓库质量门禁。

## 背景

`TASK-0192` 引入了可移植 Python 覆盖率内核 `aiflow.coverage_check`，外部 Python 仓库接入时需手改四份候选 Policy 中的 `verification-levels.yaml`。本任务将其沉淀为确定性 CLI 子命令 `aiflow init render-python-policy`，从内置或显式资源包渲染仅包含合法 `--cov=<cov_target>` 与 `--source <src>` 的四份候选策略并在临时目录完成 Schema 及 V0/V1/V2 解析校验后原子输出，可直接被 `init preview`、`init apply` 与 `init migration-plan` 消费。

## 代码地图

- `src/aiflow/verification.py`：导出公共函数 `validate_coverage_target(target: str) -> str`（复用 `_COV_TARGET_PATTERN` 并显式拒绝 `".."`），并在 `_is_valid_pytest_argv` 中复用，避免跨模块导入私有符号。
- `src/aiflow/initialization.py`：抽取无标志位内部辅助 `_bundle_directory`、`_validate_python_policy`（与 `_materials` 复用同一资源包定位和 V0/V1/V2 结构校验逻辑），新增 `_render_verification_policy` 与 `render_python_policy(output_dir: Path, *, cov_target: str, sources: Sequence[str], bundle_root: Path | None = None) -> dict[str, Any]`。
- `src/aiflow/cli.py`：在 `init_commands` 注册 `render-python-policy`（`--output-dir`、`--cov-target`、`--source` 可重复且必填、`--bundle-root` 可选），在 `_dispatch_initialization` 中先于 `else:` 分派。
- `tests/unit/test_render_python_policy.py`：29 项单元测试覆盖单/多源码域与保序去重、三份非目标策略字节级保留、V0/V1/V2 校验、无效 `cov_target`/`sources`/`..` 拒绝、既有目录/文件拒绝、缺失/非目录/重解析点父目录拒绝、缺失/损坏/非文件系统资源包拒绝、暂存校验失败不创建输出、写失败处理、CLI exit 0/1 及与 `init preview`/`apply`/`migration-plan` 串联。
- `tests/integration/test_external_python_verify.py`：抽取共享初始化-验证辅助 `_initialize_and_verify_external_repo`，新增 `test_rendered_python_policy_external_repo_verify_advise_and_gate_pass` 覆盖 `render-python-policy` -> `preview` -> `apply` -> `inspect` -> V1 `verify` -> `advise` -> `gate PASS` 闭环。
- `docs/operations/initialization.md` 与 `CHANGELOG.md`：更新外部 Python 仓库便携验证操作说明及 `## Unreleased` `### Added`。

## 语义变更

- 新增公开函数 `validate_coverage_target` 与 `render_python_policy`，及只新增的子命令 `aiflow init render-python-policy`；不改变既有 `init preview`/`apply`/`inspect`/`migration-plan` 或本仓 `.ai/policy/*` 语义，不放松 `allowed_commands`、`allowed_placeholders`、`allowed_environment` 或 `85%`/`90%` 阈值。
- 抽取 `_bundle_directory` 与 `_validate_python_policy` 均满足“同业务规则、同向演进、合并不增标志位”三条件。
- 所有参数校验与文件系统防卫均置于入口及外部 I/O 边界：`cov_target`、`sources`、`..` 路径段、`os.path.lexists`、`_plain`（含父目录及资源包文件重解析点/符号链接校验）、`read_bundle` 校验、`TemporaryDirectory` 内 Schema 与 V0/V1/V2 暂存校验、`os.mkdir` 与 `open(..., "xb")` 排他创建；内部可信调用链保持契约简洁。

## 风险

- **TOCTOU 或并发目录创建冲突**：在暂存校验后、`os.mkdir` 前复核 `_plain(output_abs.parent, directory=True)`，使用原子 `os.mkdir` 与 `open(..., "xb")` 排他写入，将并发撞车映射为 `INITIALIZATION_OUTPUT_EXISTS` 或 `INITIALIZATION_WRITE_FAILED`。
- **可编辑安装无内置资源包**：与 `init preview`/`apply` 一致，未传 `--bundle-root` 且非 wheel 安装时按缺失资源路径（`INITIALIZATION_PATH_UNAVAILABLE`）清晰拒绝，不隐式读取源码仓 `.ai`。
- **文档与测试范围偏移**：已通过 `aiflow scope TASK-0196` 与差异检查确认仅触及规格允许的 7 个软件与文档文件及任务账本目录。

## 证据

- **已验证结果**：本地原生 V1 完整验证（`aiflow verify TASK-0196 --actor verifier-v1`，记录于 `.ai/tasks/TASK-0196/evidence.json`）10/10 项全数 `passed`（`contract`、`scope`、`ruff_check`、`ruff_format_check`、`smoke`、`unit_tests`、`regression_tests`、`mypy`、`coverage_xml`、`diff_coverage`）。
- **测试与覆盖率实测**：`5361 passed, 9 skipped`（仅跨平台 POSIX/Windows 及外置 Node 材料用例按环境条件跳过），核心分支覆盖率 `91%`（门槛 >= 85%），diff coverage `95%`（109/114 行；`cli.py` 100%、`verification.py` 100%、`initialization.py` 94.9%；门槛 >= 90%）。
- **静态检查与导入边界**：`ruff check .`、`ruff format --check .`、`mypy`（64 个源文件无错误）、`tests/unit/test_import_boundaries.py`、`git diff --check` 均通过。
- **复现命令**：`python -m aiflow verify TASK-0196 --actor verifier-v1`。
- **仍未验证的场景**：GitHub Actions Ubuntu `ai-quality-gate` 远端 CI（将在推送 PR 后执行并验证）。

## 审核问题

请独立审核者明确裁决以下问题：
1. `render_python_policy` 的输入校验、非覆盖创建（`lexists` + `os.mkdir` + `open("xb")`）、暂存 V0/V1/V2 验证及 3 份未改策略原字节保留是否完整满足 `spec.md`？
2. `verification.py`、`initialization.py`、`cli.py` 的改动与跨模块导入边界、核心/差异覆盖率及 V1 证据是否一致且无未声明副作用？

交付边界五项自检结论：
1. **目标与关键假设是否清楚**：清楚；目标为向外部 Python 仓库提供非覆盖、经 V0/V1/V2 校验的候选 Policy 渲染命令，不修改既有安装或源仓策略。
2. **是否已核实语言标准库与代码库既有复用机会**：已核实；复用 `pathlib.Path`、`os.mkdir`、`open("xb")`、`tempfile.TemporaryDirectory`、`validate_source_domain`、`PYTEST_CHECK_IDS`、`_plain`、`read_bundle`、`load_policy_bundle`、`parse_verification_plan` 并抽取 `_bundle_directory` 与 `_validate_python_policy`。
3. **各修改模块是否存在更简单的直接实现**：当前实现已直接复用既有原语，无多余包装类、配置开关或冗余分支。
4. **新增抽象、分支或配置项是否均有当前明确依据**：所有新增函数、参数与分支均直接对应规格中的渲染、校验、非覆盖和 CLI 分派要求。
5. **是否只触及了任务范围边界内的文件**：是；仅修改/新增任务 `allow` 清单内的 7 个文件及 `.ai/tasks/TASK-0196/` 账本记录，无无关改动。

## 推荐结论

`APPROVE` — 实现严格控制在规格范围内，边界防卫与错误码清晰，本地原生 V1 全套 10/10 门禁、91% 核心分支覆盖率与 95% diff coverage 全部通过。
