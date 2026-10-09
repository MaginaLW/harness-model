# Runner 只读盘点和健康检查（已移除）

本文描述的 `tools/runner/RunnerInspection.psm1`、`tools/runner/inventory.ps1`、`tools/runner/health-check.ps1` 已在 2026-10-10 的架构精简中删除：CI 与 `src/aiflow` 均不调用它们，最后一次使用属于 2026-09 的历史任务。历史任务记录中的引用保持原样。

需要时可从删除前的提交恢复：`git show 5693ad2:docs/operations/runner-health-checks.md` 查看原文，`git show 5693ad2:<工具路径>` 取回工具。
