# Task Specification

## 目标

在 `docs/operations/github-branch-protection.md` 中定义首个 bootstrap 退出后正式 AI Flow
Pull Request 的证据保留和验收方法，使维护者能够确认 GitHub 实际执行了 task resolution、
CI verification 与 Gate，同时不通过向受治理文件回写运行 URL 制造 subject/evidence 循环失效。

## 范围

1. 唯一业务文件为 `docs/operations/github-branch-protection.md`。
2. 说明 PR body 应保留 task ID、最终 head SHA 和对应 CI run URL；GitHub required check 与
   诊断 artifact 分别作为平台结果和限期诊断材料。
3. 说明验收时必须在真实 PR run 中观察正式路径的 `Resolve task`、`Verify and Gate` 和
   `Upload AI Flow diagnostics`，且不得执行 `Bootstrap quality checks`。
4. `.ai/tasks/TASK-0029/**` 仅由当前 AI Flow 生命周期维护，不扩展业务范围。

## 非目标

1. 不修改 workflow、Policy、Schema、CLI、Hook、测试、README、CHANGELOG 或分支保护配置。
2. 不把 CI run URL 写回本次受治理文件，也不创建无业务内容的 no-op PR。
3. 不增加 `main`/tag 构建、发布附件、registry publish 或 Actions SHA pinning。
4. 不重验证或关闭历史 `TASK-0028`，不启动 Phase 3 或 Phase 4。

## 验收条件

1. 文档清楚区分 PR/required-check 的长期平台证据与保留 14 天的诊断 artifact，并要求 PR
   body 绑定 task ID、最终 head SHA 和 CI run URL。
2. 文档明确同一 PR 的 run URL 不回写受治理文件，避免新 commit 使旧 CI evidence 失效。
3. `python -m aiflow validate TASK-0029`、`python -m aiflow scope TASK-0029`、Policy 定义的
   V1 verification 以及只读 Gate 全部通过。
4. 真实 GitHub PR 的 required `ai-quality-gate` 成功，日志显示正式路径三个步骤执行、
   bootstrap quality step 跳过，且 `ai-flow-TASK-0029` diagnostics artifact 可见。
5. 最终业务 diff 仅包含目标 operations 文档；其余 tracked diff 仅限当前 task artifacts。

## 禁止动作

任务实现与验证不得 merge、deploy、delete、发布 package、导出凭据、发起付费调用或更改
GitHub 配置。AI Flow Gate 不执行 push 或创建 PR；只有在 Gate 通过后，才可依据当前用户对
本 canary 的单独授权由外部 actor 推送本分支并创建 PR。合并仍需新的明确授权。

## 错误行为

出现范围扩展、workflow/Policy/行为变化、主分支漂移、task binding 失效、验证失败、Gate
拒绝或正式 CI 未执行预期步骤时必须停止并按 CLI 指引升级、同步或修复；不得改写 task
状态、伪造证据、切回 bootstrap、绕过 required check，或以历史 TASK-0028 的证据替代本任务。

## 回滚

在未合并前撤销目标文档的新增段落或关闭 PR；已产生的 task、event、verification 与平台
记录保持追加式，不删除或改写。若合并后需要修订，通过新的 AI Flow task 前向更正。
