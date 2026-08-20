# Task 1.4 精简执行计划

**目标：** 完成阶段一实施目录 Task 1.4，用四组静态输入和期望结果冻结 AUTO、ASK、REVIEW、BLOCK 的首批可比较语义。

**授权与绑定：** 用户于 2026-08-20 要求持续推进任务。本计划绑定基线提交 `350fecb237a9cc449405494438e4781f18e8e372`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a`、MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc` 及当前已验证的 Task 1.1—1.3 工作树。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: 黄金结果会约束后续路由实现，但本任务只建立静态契约与比较测试，不运行真实外部动作。
- review mode: 内联完成需求符合性和代码质量复核，不建立外置审计树。

## 允许范围

- `examples/scenarios/**`
- `tests/integration/test_golden_contracts.py`
- `.ai/schemas/decision-unit.schema.json` 中增加黄金输入所需的可选、封闭分类事实字段
- 本计划、`docs/superpowers/state/chapters/chapter-01.yaml`、`docs/superpowers/state/overall.yaml`
- 完成后同步 `README.md` 的单行状态说明

已有 Task 1.1—1.3 差异和 `.reasonix/` 不属于本任务，不删除、不改写为本任务证据。

## 实施与验证

1. 先添加场景目录、字段、规则引用、动态字段排除和 ASK 选项结构测试，确认缺少场景文件时失败。
2. 为 decision-unit Schema 增加 `scope`、`impact`、`protections`、`verification`、`impact_categories`、`business_direction_count` 等可选分类事实；原必填字段与封闭枚举不降低。
3. 创建四组 `input.yaml`、`expected.json` 和总说明；期望文件不含动态时间或绝对仓库路径。
4. 运行：

```powershell
python -m pytest tests/integration/test_golden_contracts.py -q
python -m pytest -q
python -m ruff check pyproject.toml src tests
python -m ruff format --check src tests
python -m mypy src
git diff --check
```

## 完成边界

- AUTO=`V0`、ASK/REVIEW/BLOCK=`V1`；四类 route 各出现一次。
- ASK 包含三个完整且实质不同的输出选项，推荐项不超过一个。
- REVIEW 明确需要 spec/code 批准且不执行外部动作。
- BLOCK 明确列出可验证备份和缩小目标范围两个恢复条件。
- 规则 ID 均存在于当前 Policy；不在本任务实现分类引擎或伪造运行结果。

不执行 commit、push、merge、deploy、删除、凭据操作、付费调用或其他外部高风险动作。
