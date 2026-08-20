# Task 1.5 与 Chapter 1 退出计划

**目标：** 建立一键契约测试集合和 Chapter 1 基线说明，完成工程基线与可执行契约章节的退出验证。

**授权与绑定：** 用户于 2026-08-20 要求持续推进任务。本计划绑定基线提交 `350fecb237a9cc449405494438e4781f18e8e372`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a`、MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc` 和 Task 1.1—1.4 当前已验证产物。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: 本任务本身主要是测试分组和说明文档，但结论决定是否跨章，必须执行 Chapter 1 完整退出检查。
- review mode: 退出命令通过后，依次内联完成需求符合性与代码质量复核；不增加独立审计层。

## 允许范围

- `docs/implementation/chapter-01-contract-baseline.md`
- `pyproject.toml` 的 pytest `contract` marker 注册
- `tests/unit/test_contracts.py`
- `tests/integration/test_templates_and_policy.py`
- `tests/integration/test_golden_contracts.py`
- 本计划、`docs/superpowers/state/chapters/chapter-01.yaml`、`docs/superpowers/state/overall.yaml`
- 完成后同步 `README.md` 的单行状态说明

已有 Task 1.1—1.4 差异和 `.reasonix/` 不属于本任务，不删除、不改写为本任务证据。

## 实施与退出检查

1. 先运行 `pytest -m contract`，确认当前尚无 marker 选择结果。
2. 注册 marker，并在 Schema、Policy/模板、黄金场景三个测试模块设置模块级 `contract` 标记。
3. 编写基线说明，固定 Schema 版本、Policy 变更、目录职责、场景目的和摘要参与字段。
4. 运行：

```powershell
python -m pytest -m contract -q
python -m pytest -q
python -m ruff check .
python -m ruff format --check src tests
python -m mypy src
python -m aiflow --help
rg -n "TBD|TODO|稍后补充" .ai/templates .ai/policy
git diff --check
```

`rg` 预期退出 1 且无匹配；其余命令预期退出 0。

## 完成边界

- `contract` 集合覆盖 Schema、模板、Policy 和黄金场景，且不访问网络、用户主目录或当前时间。
- 基线说明明确 `schema_version: "1.0"` 不得无迁移改变语义。
- 需求复核逐项覆盖 Task 1.1—1.5 及设计说明第 4—9 节；质量复核确认 Schema 引用一致、Policy 无代码副本、错误可定位。
- 全部通过后，Task 1.5 与 Chapter 1 标为完成，总体指针推进到 Task 2.1；不提前实现 Chapter 2。

不执行 commit、push、merge、deploy、删除、凭据操作、付费调用或其他外部高风险动作。
