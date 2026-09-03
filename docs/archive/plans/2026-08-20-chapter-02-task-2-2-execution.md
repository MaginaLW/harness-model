# Task 2.2 执行计划

**目标：** 通过受限、限时的只读 Git 命令采集稳定仓库身份、诊断路径、分支、HEAD 和工作树脏路径。

**授权与绑定：** 用户于 2026-08-20 要求持续推进下一章节。本计划绑定基线提交 `519601e93a00de3eb41cb8737461d8adacae91aa`、Task 2.1 已验证工作树产物、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: 只读采集不修改仓库，但其结果将成为后续任务身份和版本判断输入，因此用真实临时仓库覆盖成功与失败边界。
- review mode: 定向测试、全量回归和静态检查后内联完成需求与质量复核，不增加独立审计层。

## 允许范围

- `src/aiflow/git_context.py`
- `tests/unit/test_git_context.py`
- `.ai/schemas/task.schema.json`（增加可选的规范化脏路径字段）
- 本计划、`docs/superpowers/state/chapters/chapter-02.yaml`、`docs/superpowers/state/overall.yaml`
- 完成后同步 `README.md` 当前任务说明

## 实施步骤

1. 只以参数数组运行四类 Git 命令，固定十秒超时，UTF-8 严格解码且不记录 stderr 或环境变量。
2. 校验 checkout 根目录的 `.ai/repository-id`，返回规范化诊断路径、分支或 `DETACHED`、40 位 HEAD、脏状态和排序后的仓库相对路径。
3. 用稳定错误码处理非 Git 目录、空仓库、命令超时、无效 HEAD 和无效 repository ID。
4. 用命令级提交身份建立真实临时仓库，覆盖清洁、脏文件、分支、detached HEAD 和复制到不同路径后身份不变。
5. 运行退出检查并记录结果。

## 退出检查

```powershell
python -m pytest tests/unit/test_git_context.py -q
python -m pytest -q
python -m ruff check src/aiflow/git_context.py tests/unit/test_git_context.py
python -m ruff format --check src/aiflow/git_context.py tests/unit/test_git_context.py
python -m mypy src/aiflow/git_context.py
git diff --check
```

全部通过后 Task 2.2 标为完成，总体指针推进到 Task 2.3。不得提前实现 `start` 或任何写操作。

不执行当前仓库 commit、push、merge、deploy、删除用户数据、凭据操作、付费调用或远程动作。测试仅在 pytest 临时目录创建并提交隔离仓库。
