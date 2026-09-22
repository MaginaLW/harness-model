# TASK-0049：PR #40 实际发布与关闭

2026-09-22 06:11:51 UTC，[PR #40](https://github.com/MaginaLW/harness-model/pull/40)
已通过普通 merge commit 合入受保护的 main。合并提交为
`4399352e5d13f062cc7dc864767cb5c5e4ae666e`。CLI 已在实际合并与祖先核验后追加
`merge_recorded`；TASK-0049 为 MERGED、Missing: none。

## 对象与授权

所有者明确批准受检 subject `d05beb274290c90aad67f986efdaac49a4e0967b` 的代码结果，
并授权发布 `f421084` 候选及本次批准记录、创建 PR、required CI 成功后普通合并。
代码批准已记录，干净验证目录中的本地 Gate 为 passed=true、reason_codes=[]。
审核包补齐校验器要求的“已验证/未验证”标签后成功记录批准，未改规格或源码。

实际发布 head：`9ab3ca44597f8c1345fd9daa57291e54f20db04e`。
发布 base：`7dad5c0be700c0ba72ed4f33f8856148e3265825`。
累计 31 文件、1531 增行、8 删行，含已授权的旧 TASK-0048 关闭记录与后续文档。
`f421084` 后仅增加本任务批准/授权记录及审核包标签；为满足 strict 更新要求合入
main 的已有合并节点，该次本地 merge 的树与第一父提交完全相同，没有新增业务差异。
三个用户原稿未入库，Policy、Schema、workflow、依赖和质量阈值未改变。

push 与 exact-head merge 分别记录当前 action；其本地记录是授权留痕，仍不冒称
通用执行器或可信身份验证。未强推、未绕过保护、未删除分支。

## 本次远端检查

[run 35693038600](https://github.com/MaginaLW/harness-model/actions/runs/35693038600)
与 required job `106633896767`（ai-quality-gate，app 15368）均 completed/success。
原日志确认 checkout 的精确 SHA 为上述发布 head；独立复核与 main 的 required check
配置一致，merge 前 PR 为 CLEAN/MERGEABLE，strict 和 enforce_admins 均保持启用。

- 契约测试：105 passed。
- Linux 全量：1958 passed，432.26 秒。
- Linux 总覆盖率：88.03%，原始日志明确确认 85% 门槛通过；与本地 Windows 的
  88.12% 分别记录，不混用。
- Diff coverage：100%，保留 90% 门槛。
- whitespace、Ruff、444 文件格式检查、mypy 41 文件全部通过。

本次远端执行的是维护模式 Bootstrap quality checks；workflow 的正式 Verify and
Gate 步骤按既有模式跳过。本地正式 V1/Gate 与远端 required CI 是两份不同证据。

## 实际合并核验

GitHub API 确认 PR MERGED，远端 main 指向 `4399352`。该提交父节点依次为
`7dad5c0` 与 `9ab3ca4`，合并树与受检 head 相同。受检源码 `d05beb2`、完整发布
head 及 TASK-0048 的真实关闭记录 `7eec053` 均为合并提交祖先。TASK-0048 不重复 close。

合并后本地账本：48 项，40 MERGED、7 BLOCKED、1 APPROVED_FOR_MERGE。
最后一项仍为既有处置的 TASK-0028；条件性试点/阶段边界不因本次合并改变。

## 保管和发布边界

完整 CI 日志、run/jobs、保护配置、合并前后 PR/main 回执保存在
`<ARTIFACT_ROOT>/TASK-0049/`。原件哈希与验证日志继续保留，不将本机路径或凭据入库。
合并后 PR 回执 SHA256：`cc9682d80c183b6fedd501c1db709ab0209ce916298eba06c60e28f8b863632a`；
main 回执 SHA256：`acb8ab0b2df68a99f9ad62dc5b97bb177184bd581d96d8e7aa8eece56d71ecef`。

本文件、merge action、CLI 关闭记录及之后的待办入口更新在 PR #40 合并后追加，
仅本地保存，不属于已发布受检 head。远端已包含 TASK-0048 的关闭；远端 TASK-0049
保留 APPROVED_FOR_MERGE 的受检快照，实际 MERGED 事实由上述 PR/提交和本地追加记录
证明。不为发布后一条记录递归创建新发布，后续有真实交付时再按其范围纳入。
