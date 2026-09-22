# TASK-0048 阶段 62：实际发布与合并关闭

2026-09-21 23:55:06 UTC，[PR #39](https://github.com/MaginaLW/harness-model/pull/39)
已通过普通 merge commit 合入受保护的 main。独立复核后，CLI 已实际追加
`merge_recorded`，TASK-0048 状态为 `MERGED`、`Missing: none`。
阶段 61 的合并就绪结论保留其原观察时点，本记录追加实际发布与关闭事实。

## 发布对象与授权

所有者本轮明确批准：推送固定候选、创建 PR，并在 required CI 通过后合并。
实际发布候选为 `2dffdf0d321350dd1c40a430c5befa5d05dfd842`，来源分支为
`codex/self-hosted-runner-inventory`，基线为
`f633c036cc2a0394f7b1efb20efe4d91ba944255`。

累计范围为 117 提交、64 文件，包含 TASK-0048 base 之前的 21 提交。发布前另行
独立审查 runner 工具/测试、模型选择配置、TASK-0047 的追加历史及累计文档；
没有用 TASK-0048 的较窄 Gate 冒充全发布范围的批准。累计审查 APPROVE，原件摘要
`334d6534fa76daa707fb7981889129f14f92fac5b433409a28af3bfa436b6c89`。

本次候选未更改 AI Flow 源码、Policy、Schema、workflow 或忽略规则。当前源码、
测试、工具、依赖和质量配置与已完成 V2 的受测版本逐项 Git 对象相同，复用本机
1945 项通过、总覆盖率 88.12% 的原证据。额外覆盖新增 Python receipt 工具：
129 项通过、综合覆盖率 95.21%，对 main 的实际 diff coverage 为 95.4%，
通过原 90% 门槛；该数值不包括 PowerShell 的数值覆盖率声明。

## 远端真实质量门

[run 35668963763](https://github.com/MaginaLW/harness-model/actions/runs/35668963763)
的 required job `106560907053` / `ai-quality-gate` 已 completed/success，
检出精确候选 `2dffdf0`。原始日志与 API 均独立核验：

- 合同测试 105 passed；完整测试 1945 passed，433.52 秒。
- Linux 总覆盖率 88.04%，满足 85% 门槛；与本机 Windows 的 88.12% 分别记录。
- Ruff、438 文件格式检查、mypy 41 文件及 whitespace 全部通过。
- CI 的 aiflow diff-cover 无可统计覆盖行；新增 receipt 工具的覆盖率由上述补充
  执行独立给出，不能混称为远端测得的结果。

维护模式走原有 Bootstrap quality checks。远端 Verify and Gate 条件跳过，
不声称另执行了一次远端 V2。CI 原件摘要为
`86aec4d182634b802a2804f1ef0e0ee70b2264bf4e1e20211aade8716f717db1`。

## 合并与关闭证据

- 实际 merge：`7dad5c0be700c0ba72ed4f33f8856148e3265825`。
- Parent 1：`f633c036cc2a0394f7b1efb20efe4d91ba944255`。
- Parent 2：`2dffdf0d321350dd1c40a430c5befa5d05dfd842`。
- 远端 main、PR merged 状态、两个 parent 和合并树已独立核对；合并树与受审候选一致。
- TASK-0048 subject `968cc3c354b87671b7c3f8d60a2784ba06c90261` 和 base
  `44bda60199c4344220590aff30522022bf3c1064` 均为实际 merge 的祖先。
- 来源分支保留在原发布 head；没有 force push、squash、admin bypass 或删除分支。

独立合并复核摘要：`b45788721e3bb4e67037ae6811cf0f0b66c3a87e7f687b0652d053c9ad0f13ac`。
CLI close 本身只检查提交对象存在；上述外部状态与祖先核验已在 close 之前补齐，
没有将该实现限制误认为完整的远端验证。

## 保存边界

失败、成功、review、CI 日志和本机原始字节继续保存；不读取或搬动运行 guest 磁盘，
不导出凭据，不改变 runner 服务。三个用户原稿保留，I5 和其他仓库推广未启动。

本文件和合并后追加的 action/close 账本作为本地收尾提交保存，不属于 PR #39
的受检 head，也不声称远端 main 已包含这些后续记录。原始本机证据及 CRLF/Git
文本规范化的边界沿用阶段 61 记录，不以公开摘要替代原件。
