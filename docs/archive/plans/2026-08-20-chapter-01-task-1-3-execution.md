# Task 1.3 精简执行计划

**目标：** 完成阶段一实施目录 Task 1.3，交付统一 Policy Schema、四份阶段一 Policy、五份人类/机器模板及集成测试。

**授权与绑定：** 用户于 2026-08-20 要求持续推进任务。本计划绑定基线提交 `350fecb237a9cc449405494438e4781f18e8e372`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a`、MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`，并保留已验证但尚未提交的 Task 1.1—1.2 工作树差异。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: Policy 将成为后续分流、权限和验证的单一规则来源；本任务只建立声明式数据与结构测试，不提前实现路由或执行引擎。
- review mode: 按实施目录顺序内联完成需求符合性和代码质量复核，不建立外置审计树或重复审核层。

## 允许范围

- `.ai/schemas/policy.schema.json`
- `.ai/policy/*.yaml`
- `.ai/templates/task.yaml`
- `.ai/templates/spec.md`
- `.ai/templates/ask.md`
- `.ai/templates/review-package.md`
- `.ai/templates/evidence.json`
- `src/aiflow/contracts.py` 中登记 `policy` Schema 名称
- `tests/integration/test_templates_and_policy.py`
- 本计划、`docs/superpowers/state/chapters/chapter-01.yaml`、`docs/superpowers/state/overall.yaml`
- 完成后同步 `README.md` 的单行当前状态说明

已有 Task 1.1—1.2 差异和 `.reasonix/` 不属于本任务，不删除、不改写为本任务证据。

## 实施顺序与验证

1. 先建立覆盖 Policy 结构、全局 ID、默认 REVIEW、受限谓词/检查/命令/变量、V0/V1、权限与 Markdown 标题的集成测试。
2. 运行定向测试，确认因 Policy Schema/文件尚不存在而失败。
3. 实现统一 Draft 2020-12 Policy Schema、四份 YAML Policy 和五份模板。
4. 运行：

```powershell
python -m pytest tests/integration/test_templates_and_policy.py -q
python -m pytest -q
python -m ruff check pyproject.toml src tests
python -m mypy src
rg -n "TBD|TODO|稍后补充" .ai/templates .ai/policy
git diff --check
```

`rg` 预期退出 1 且无匹配；其余命令预期退出 0。

## 完成边界

- 未命中显式 AUTO 时默认 REVIEW；所有 BLOCK/REVIEW/ASK/AUTO 规则均具名且 ID 全局唯一。
- V0/V1 命令始终是参数数组，变量和覆盖环境严格限于实施目录列出的集合；diff-cover 阈值固定 90。
- 权限明确禁止自动 push、merge、deploy、delete、secret export 和付费外部调用。
- 模板不含空占位词；只建立结构，不提前实现 Task 3.1 的 Policy 加载器或后续执行逻辑。

不执行 commit、push、merge、deploy、删除、凭据操作、付费调用或其他外部高风险动作。
