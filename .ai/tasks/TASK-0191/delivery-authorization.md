# TASK-0191 交付授权

项目所有者于 2026-11-24 明确批准（A1 公开披露授权）并于 2026-11-25 明确批准增补项（`A02` 选项 1），授权将软件提交 `aa231eff`、TASK-0191 最终账本、本轮六份脱敏变异 JSON 及第七份行动启动声明 JSON 一并交付到公开仓库 `MaginaLW/harness-model`（分支 `codex/mutation-attribution-delivery`）。接收方为本仓公众读者和 GitHub Actions。最终账本与公开附件的披露范围包括独立审核与验证身份、结果，以及 `receipt_device` 和 `receipt_inode` 等协议允许字段的实值。

七份授权公开的 `logs/` 文件为：
- `logs/MUTRUN-20261124T213451Z-e6240f97221e32c5/targeted-mutation/evidence.json` 与 `logs/MUT-V2-001.json` 至 `logs/MUT-V2-005.json`（六份变异 JSON，均经独立审核确认零凭据、零密钥、零本机隐私绝对路径）；
- `.ai/tasks/TASK-0191/logs/action-launch-11ad4f13061f8f8503445e4c954ebe0644d10b95ba638c56eee1c342d09df4c1.json`（第七份行动启动声明 JSON，由项目所有者 2026-11-25 `A02` 选项 1 明确授权公开披露，仅含 `action_sha256`、`claimed_at`、`receipt_device`、`receipt_inode`、`receipt_ref`、`schema_version`、`single_use`、`subject_commit`、`task_id`，零凭据、零密钥、零本机隐私绝对路径，满足 schema `2.0` `_verify_recorded_action` 与 `aiflow gate` / 公开 `ai-quality-gate` 校验要求）。

软件 PR 当前 head 的公开 `ai-quality-gate` 必需检查通过后，以 merge commit 合入 `main`，再交付任务关闭记录并关闭被替代的 PR #186。

`TASK-0175` 原件、`codex/mutation-attribution-0526983f`、`task-0175-delivery` 工作树、密钥和其他本地运行日志继续留在本机，不纳入本交付。
