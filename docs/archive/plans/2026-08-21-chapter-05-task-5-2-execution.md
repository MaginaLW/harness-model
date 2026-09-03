# Task 5.2 执行计划

**目标：** 实现无 Shell、最小环境、超时可控且日志先脱敏后落盘的验证子进程执行器。

**授权与绑定：** 用户要求按章节持续推进并逐章完成。本计划绑定基线提交 `dbe04231ca10ac4dc778748b14ace8c63b41e5af`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: 执行器会启动本地命令并保存后续证据引用的日志；需要确保 argv、环境、cwd、run_dir、超时和脱敏边界确定且失败可记录。
- allowed scope: `src/aiflow/process_runner.py`、`src/aiflow/redaction.py`、必要的验证计划邻接接口、`tests/unit/test_process_runner.py`、`tests/unit/test_redaction.py`、本计划和 Chapter 5/总体状态。
- forbidden actions: 不使用 Shell，不继承或记录完整父环境，不运行外部网络/付费命令，不把秘密原文写入日志或结果，不推送/合并。

## 完成边界

1. 结果模型记录命令 ID、脱敏摘要、时间、退出/超时、相对日志引用和解析结论，不记录父环境。
2. 仅以 argv、显式 cwd、最小环境、UTF-8 捕获和超时执行；异常形成结构化失败结果。
3. 常见密钥、Bearer/GitHub token、用户模式和任务禁止值在写日志前统一脱敏。
4. 日志只能写入已校验 run_dir，文件名由稳定检查 ID 与序号生成，命令摘要不泄露敏感参数或路径。
5. 成功、失败、超时、大输出、不可执行文件、敏感内容、路径与 COVERAGE_FILE 边界测试通过。
6. 定向测试、全量回归、ruff、format、mypy、diff check 与精简双重复核通过后本地提交。
