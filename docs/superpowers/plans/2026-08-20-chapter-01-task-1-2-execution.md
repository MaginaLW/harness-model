# Task 1.2 精简执行计划

**目标：** 完成阶段一实施目录 Task 1.2，交付七个核心机器契约 Schema、统一 Python 验证接口、正反例夹具和稳定仓库 ID。

**授权与绑定：** 用户于 2026-08-20 要求持续推进任务。本计划绑定基线提交 `350fecb237a9cc449405494438e4781f18e8e372`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a`、MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`，并保留 Task 1.1 尚未提交的已验证工作树差异。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: 新增机器契约和校验行为，但不新增依赖、不访问外部系统、不执行高风险动作。
- review mode: 按实施目录顺序在本轮内联完成需求符合性和代码质量复核，不建立外置审计树或重复多层审核。

## 允许范围

- `.ai/schemas/*.schema.json`
- `.ai/repository-id`
- `src/aiflow/contracts.py`
- `tests/unit/test_contracts.py`
- `tests/fixtures/contracts/valid/*.json`
- `tests/fixtures/contracts/invalid/*.json`
- 本计划、`docs/superpowers/state/chapters/chapter-01.yaml`、`docs/superpowers/state/overall.yaml`
- 完成后同步 `README.md` 的单行当前状态说明

已有 Task 1.1 差异和 `.reasonix/` 目录不属于本任务范围，不修改、不删除，也不作为本任务证据。

## 实施顺序

1. 先添加覆盖公共枚举、七类契约、稳定错误、交叉字段规则和 repository ID 的测试及正反例夹具。
2. 运行 `tests/unit/test_contracts.py`，确认因契约实现尚不存在而失败。
3. 实现七个 Draft 2020-12 JSON Schema 和 `contracts.py` 的加载、稳定错误列表、异常接口及交叉字段校验。
4. 生成一次 UUIDv4 写入 `.ai/repository-id`。
5. 运行定向测试、全量 pytest、Ruff、mypy、`git diff --check`，再完成两项复核。

## 完成条件

- 每个 Schema 至少一个有效夹具和三个无效夹具，分别覆盖缺字段、非法枚举或 ID、未知字段。
- CI evidence 缺 `attestation_head`、passed evidence 含失败检查、code approval 缺 `subject_commit`、任务状态与末事件状态不一致均被拒绝。
- 错误按 JSON Pointer 稳定排序，且不回显实例中的敏感值。
- repository ID 是单行 UUIDv4，复制到不同绝对路径后值不变。
- Task 1.2 七步完成，Chapter 1 和总体累计推进到 Task 1.3。

不执行 commit、push、merge、deploy、删除、凭据操作、付费调用或其他外部高风险动作。
