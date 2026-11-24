# TASK-0191 交付授权

项目所有者于 2026-11-24 明确批准（A1 公开披露授权）将软件提交 `aa231eff`、TASK-0191 最终账本和本轮六份脱敏变异 JSON 交付到公开仓库 `MaginaLW/harness-model`（分支 `codex/mutation-attribution-delivery`）。接收方为本仓公众读者和 GitHub Actions。最终账本的披露范围包括独立审核与验证身份、结果，以及 `receipt_device` 和 `receipt_inode` 等协议允许字段的实值。

六份文件位于本任务的 `logs/MUTRUN-20261124T213451Z-e6240f97221e32c5/targeted-mutation/`，包括 `evidence.json` 和 `logs/MUT-V2-001.json` 至 `logs/MUT-V2-005.json`（均经独立审核确认零凭据、零密钥、零本机隐私绝对路径）。软件 PR 当前 head 的公开 `ai-quality-gate` 必需检查通过后，以 merge commit 合入 `main`，再交付任务关闭记录并关闭被替代的 PR #186。

`TASK-0175` 原件、`codex/mutation-attribution-0526983f`、`task-0175-delivery` 工作树、密钥和其他本地运行日志继续留在本机，不纳入本交付。
