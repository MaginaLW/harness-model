# Task 2.3 执行计划

**目标：** 实现 `aiflow start`，创建完整、可验证且失败后可明确恢复的初始任务目录。

**授权与绑定：** 用户于 2026-08-20 要求持续推进并在每个大块完成后提交。本计划绑定基线提交 `2a969ea4552f6ec13aed1008b0547be9f67d002e`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: 命令创建本地任务记录并涉及中断恢复，但不运行 Git 写操作或远程动作；以真实临时仓库集成测试验证。
- review mode: 定向测试、全量回归和静态检查后内联完成需求与质量复核，不增加独立审计层。

## 允许范围

- `src/aiflow/cli.py`
- `src/aiflow/storage.py`
- `src/aiflow/task_service.py`
- `tests/integration/test_start_command.py`
- 本计划、Chapter 2 与总体状态、`README.md`

## 实施边界

1. `start` 接受非空 objective、至少一个有边界 allow glob、可重复 forbid-action、detached 显式放行和 recover ID。
2. 采集 Task 2.2 Git 上下文，合并 permissions Policy 默认禁止动作，预留唯一任务 ID。
3. 原子写入契约合法的 `task.yaml`、初始 `events.jsonl`、模板 `spec.md` 和空批准集合 `approvals.json`。
4. 写入失败保留 `creation_failed.json`，其中保存完整恢复材料；恢复重写全部必需文件后再移除标记，不复用半成品为新任务。
5. 验证正常、无效参数、非 Git、detached、脏工作树、重复恢复和中途失败。

## 退出检查

```powershell
python -m pytest tests/integration/test_start_command.py -q
python -m pytest -q
python -m aiflow start --help
python -m ruff check .
python -m ruff format --check src tests
python -m mypy src
git diff --check
```

全部通过后 Task 2.3 标为完成，提交这一完整块并把指针推进到 Task 2.4。只执行用户已授权的本地 commit，不 push。
