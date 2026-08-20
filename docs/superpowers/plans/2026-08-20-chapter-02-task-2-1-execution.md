# Task 2.1 执行计划

**目标：** 实现稳定领域错误、任务 ID 预留、安全任务路径和原子 YAML/JSON 存储，为后续任务状态命令提供最小持久化核心。

**授权与绑定：** 用户于 2026-08-20 要求继续推进下一章节。本计划绑定基线提交 `519601e93a00de3eb41cb8737461d8adacae91aa`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: 本任务改变本地持久化行为，但不执行外部写入或高风险动作；以定向单元测试、全量回归和静态检查验证。
- review mode: 完成后内联核对实施目录六步要求与代码质量，不增加独立审计层。

## 允许范围

- `src/aiflow/errors.py`
- `src/aiflow/storage.py`
- `src/aiflow/contracts.py`（仅接入统一领域错误）
- `src/aiflow/cli.py`（仅建立领域错误的无 traceback 顶层边界）
- `tests/unit/test_storage.py`
- 本计划、`docs/superpowers/state/chapters/chapter-02.yaml`、`docs/superpowers/state/overall.yaml`
- 完成后同步 `README.md` 的当前任务说明

## 实施步骤

1. 定义具有稳定 `code`、人类可读 `message` 和机器可读 `details` 的领域错误，并让 CLI 顶层默认只输出人类消息。
2. 先写单元测试，覆盖 ID 分配、竞争重试、无效目录、路径逃逸、原子替换中断、损坏文档和未知 Schema 版本。
3. 实现 `.ai/tasks` 下的严格任务 ID、安全相对路径解析和基于原子建目录的 ID 预留。
4. 实现同目录临时文件、flush/fsync、`os.replace` 的 YAML/JSON 原子写入；失败仅清理本次临时文件并保留旧目标。
5. 读取 YAML/JSON 后可选执行现有机器契约校验，并把解析或契约失败转换为稳定领域错误。
6. 运行退出检查并记录结果。

## 退出检查

```powershell
python -m pytest tests/unit/test_storage.py -q
python -m pytest -q
python -m ruff check src/aiflow/errors.py src/aiflow/storage.py src/aiflow/contracts.py src/aiflow/cli.py tests/unit/test_storage.py
python -m ruff format --check src/aiflow/errors.py src/aiflow/storage.py src/aiflow/contracts.py src/aiflow/cli.py tests/unit/test_storage.py
python -m mypy src/aiflow/errors.py src/aiflow/storage.py src/aiflow/contracts.py src/aiflow/cli.py
git diff --check
```

全部通过后 Task 2.1 标为完成，总体指针推进到 Task 2.2。不得提前实现 Git 上下文、状态机或 CLI 子命令。

不执行 commit、push、merge、deploy、删除用户数据、凭据操作、付费调用或其他外部高风险动作。
