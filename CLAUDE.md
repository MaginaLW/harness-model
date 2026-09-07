# Claude Code Instructions

这是 Claude Code 的平台适配入口；开始任何工作前，必须完整阅读并遵守 [AGENTS.md](AGENTS.md)。它是所有 Agent 的唯一共同权威，本文件不复制其治理规则。

启动：先按 `AGENTS.md` 判断维护模式例外与升级清单；需要 AI Flow 时运行 `python -m aiflow --help`，创建或恢复 task 并遵循 CLI 状态。任务内的连续推进与请求人类的边界见[低干预工作方式](docs/operations/low-intervention.md)。

入口：[项目总览](README.md) · [Policy](.ai/policy/) · [模板](.ai/templates/) · [CLI](src/aiflow/cli.py) · [MVP 设计](docs/superpowers/specs/2026-08-01-ai-code-collaboration-mvp-design.md) · [实施目录](docs/superpowers/plans/2026-08-01-ai-code-collaboration-mvp-implementation-directory.md)
