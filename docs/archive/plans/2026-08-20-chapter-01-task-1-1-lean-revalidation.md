# Task 1.1 精简重验证计划

**目标：** 依据阶段一实施目录的原始完成标准，重验证并关闭 Task 1.1“建立 Python 工程与 CLI 骨架”。

**授权与绑定：** 用户于 2026-08-20 要求读取项目文件继续任务，并明确要求避免过度审核和过度安全投入。本计划绑定基线提交 `350fecb237a9cc449405494438e4781f18e8e372` 及本计划允许的 Task 1.1 工作树差异；最终证据同时记录变更文件摘要。

## 决定

1. 保留既有 premature-green、spec FAIL、补救决定和计划失效记录，不删除或改写历史。
2. 失效的 TDD replay 计划不再作为 Task 1.1 的完成前置。其临时 AuditRoot、固定旧 HEAD、精确十二条工作树记录和多层独立审阅是该补救方案自行增加的条件，不是权威实施目录 Task 1.1 的验收标准。
3. 验证强度不降低：完整执行实施目录 Task 1.1 指定的安装、定向测试、Ruff、mypy 和 CLI 帮助验证，并补充全量 pytest、版本/错误参数检查、`git diff --check` 与范围检查。
4. 按实施目录顺序完成一次需求符合性复核和一次代码质量复核；本轮内联记录结论，不再创建多代理、多层 manifest 或外置临时审计树。

## 允许范围

- 读取并验证 `.gitignore`、`pyproject.toml`、`uv.lock`、`src/aiflow/**` 和 `tests/**`。
- 创建被 `.gitignore` 排除的本地 `.venv/` 并安装开发依赖。
- 允许修复需求复核在 Task 1.1 既有产物中发现的明确缺口；当前仅允许修改 `tests/conftest.py`，为子进程调用补充实施目录要求的显式超时。
- 在任务完成后只同步 `README.md` 的当前状态说明，使其与状态投影一致。
- 更新本计划、`docs/superpowers/state/chapters/chapter-01.yaml` 和 `docs/superpowers/state/overall.yaml`。
- 保留已有 `.reasonix/` 和状态文件修改；不把 `.reasonix/` 作为 Task 1.1 产物或证据。

## 验证清单

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest tests/unit/test_cli.py -q
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check pyproject.toml src tests
.venv\Scripts\python.exe -m mypy src
.venv\Scripts\python.exe -m aiflow --help
.venv\Scripts\python.exe -m aiflow --version
.venv\Scripts\python.exe -m aiflow --definitely-unknown
git diff --check
git status --short
```

未知参数命令预期退出码为 2；其余命令预期退出码为 0。若工程产物、规格、Policy、依赖或提交发生相关变化，本计划失效并重新评估；仅状态记录和本计划的写入不使本次验证失效。

## 执行中范围调整

需求符合性复核发现 `tests/conftest.py` 的 `subprocess.run` 缺少全局工程约定要求的显式超时。该修复属于 Task 1.1 的相邻测试范围，风险和验证等级不变；以本计划的验证清单重新验证修复后的工作树。

任务状态推进后，`README.md` 的单行当前状态说明同步为 Task 1.1 已完成、当前指针为 Task 1.2；不改变项目路线或验收标准。

## 完成条件

验证和两项复核通过后：

- 将 Task 1.1 标为 `completed`，步骤记为 `[1, 2, 3, 4, 5]`；
- 将 `SPEC-BLOCKER-001` 标为已解决，原因是其补救路径已由本次用户授权的原始标准重验证决定取代，而不是把旧 FAIL 改写为 PASS；
- Chapter 1 与总体状态转为 `in_progress`，累计完成任务加 1、步骤加 5，当前指针推进到 Task 1.2；
- 不执行 commit、push、merge、deploy、删除、凭据操作或付费调用。
