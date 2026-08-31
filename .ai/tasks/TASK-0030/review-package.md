# Review Package

## 审核目标

决定是否接受 TASK-0030 在 subject `a05d2005b27f977c87248cd5e535dd52c639b2ff` 上完成的
Policy 2.2.0 验证超时加固、Phase 02 历史绑定修正，以及真实 PR 暴露的 detached-HEAD
branch binding 修复。批准范围仅是进入本地只读 Gate；PR `#2` 已存在且可按已有 push 授权
更新，merge 仍未授权。

## 背景

TASK-0029 的正式 V1 两次在 600 秒 coverage runner 上限失败；TASK-0030 因此将 active Policy
升级到 `2.2.0`。首次 Policy 2.2.0 V1 又暴露 TASK-0025 历史 Policy 绑定断言陈旧，随后按正式
扩规格流程修正 acceptance；该恢复链及旧 evidence 均保留。

旧 subject `26e57b82f6230ae3528583d7829a2270ad89acfd` 曾通过 V1、`REV-0060` 和代码批准，但 PR `#2`
run `33403951577` 在任何 required check 启动前失败：`actions/checkout` 固定 event head SHA 后
处于 detached HEAD，task 仍绑定 `codex/verification-timeout-hardening`，现有 branch equality
正确返回 `VERIFY_BRANCH_CHANGED`。该 run 未生成 CI evidence 或 Gate JSON。任务随后升级规格，
旧 evidence/review/code approval 均作为历史失效记录，不复用为当前 readiness。

当前 task 为 `REVIEW / V1`，base 是 `37dce2a61a5dc484b077ba4463cede2be04dd746`，classification
input 是 `18ebff1c2879541b88671c6c222b7ad471223709e136eb4cb72266558ea73201`，冻结规格是
`d51e34b8334247dac947ad140a1e12156d60dee4da72a3cd6e4666c7cbf98b6c`，active Policy 是
`1f684f4bf4bd2e3c28b7a04903628790f7be40f88a1dbf54587b09b90230267f`。最新独立设计审查
`REV-0061` / context `42cf08e7b8336af3d923233fdd6bb115392bb6bfa105f7b6f2a340cabc45bc4d`
为 APPROVE，findings 为空，所有者已批准该扩展规格。

## 代码地图

- `.ai/policy/{hard-rules,routing,permissions,verification-levels}.yaml`：统一为 `2.2.0`；仅将
  V1/V2 regression 与 coverage 分别调整为 900 秒和 1200 秒。
- `.github/workflows/ai-quality-gate.yml`：job 上限为 90 分钟；formal path 在 governance
  detection 后、task resolution 前把精确 event head SHA 附着到 runner-local source branch。
- `tests/unit/test_policy.py`、`tests/unit/test_verification_plan.py`：固定 raw/parsed Policy 的
  版本、命令、parser、required、环境、阈值、V2 prefix 与 timeout。
- `tests/integration/test_github_workflow.py`：固定只读 workflow、90 分钟上限、formal-only
  attachment 的条件/环境/命令/顺序，并执行 detached HEAD 正向与全部拒绝路径测试。
- `tests/acceptance/test_phase_02_self_hosting.py`：保留 TASK-0025 的历史 2.1.0 classification，
  验证其在 active Policy 2.2.0 下 fail closed；不修改任何 TASK-0025 artifact。
- `README.md`、`CHANGELOG.md` 与 operations 文档：同步版本、预算、恢复边界，以及 event SHA
  为 commit 权威、`head_ref` 仅命名 runner-local branch 的 CI 边界。
- `.ai/tasks/TASK-0030/**`：保存三次恢复链、四轮设计审查、历史/当前批准、V1 evidence 和
  implementation review 绑定。

## 语义变更

active Policy 从 `2.1.0` 升至 `2.2.0`。V1/V2 的 `regression_tests` 上限由 600 调为 900 秒，
`coverage_xml` 由 600 调为 1200 秒；检查集合、命令、parser、required、环境、85% 总覆盖率、
90% diff coverage、V2 prefix/extras 与权限不变。GitHub job 由 35 调为 90 分钟。

formal PR checkout 继续固定 `${{ github.event.pull_request.head.sha }}`。bootstrap detection 确认
非 bootstrap 后，workflow 只通过 step env 取得 `github.head_ref` 与 event SHA，要求 branch
非空且通过 `git check-ref-format`，检查 switch 前 HEAD 精确等于 event SHA，再以该 SHA 为显式
start point 创建或覆盖 runner-local branch，最后同时复核 symbolic branch 与 SHA。步骤不 fetch、
不 push、不按可移动 branch ref 选择 commit；bootstrap path 与 runtime branch equality 不变。

Phase 02 acceptance 固定 TASK-0025 历史 Policy digest，要求 current verifier context 构建返回
`VERIFIER_CONTEXT_CLASSIFICATION_STALE`；已保存 immutable context 仅用于负向复用校验，不能
形成 current readiness。

## 风险

- 增大 timeout 会延长真实失败反馈；精确 Policy/plan tests 限定只调整两项已实测接近旧上限的检查。
- `github.head_ref` 属于 PR 输入；它只经 env 和双引号展开，先做 nonempty/ref-format 校验，且只
  用作本地 branch 名称。event SHA 才是 start point 与 commit 权威，避免移动 ref race。
- branch attachment 若错误地作用于 bootstrap、fetch 新内容或弱化 branch equality，会改变治理
  边界；workflow 条件、顺序、无 fetch/push 断言和现有 Git evaluator 共同 fail closed。
- 历史绑定测试若改写 TASK-0025 可能伪造 readiness；本实现只读取 digest-addressed immutable
  context，TASK-0025 diff 为空。
- Windows 的四项 symlink capability skip 仍存在，不证明其他平台或 live Hook 行为。
- 未执行或授权 merge、deploy、发布、凭据、付费调用、远端分支删除或保护规则变更。

## 证据

- 已验证：current V1 evidence 结论 `passed`，10/10 required checks 全部 passed，evidence SHA-256
  是 `7e54b88c63767ed9fe49d8c257ce266173075ac41b9d44d1cd71b7c647a267ca`，
  `unverified_scenarios: []`。
- 已验证：unit 为 `1084 passed, 3 skipped`（27.48 秒）；完整 regression 为
  `1597 passed, 4 skipped`（566.02 秒）；coverage 为 `1597 passed, 4 skipped`（625.45 秒）并
  生成 XML。四项 skip 均为既有 Windows symlink capability。
- 已验证：contract、scope、Ruff、338-file format check、mypy 与 smoke 均 passed；diff-cover
  对当前 Policy/workflow/test/doc diff 报告 no executable coverage lines sentinel，并通过既有
  90% 门禁语义。扩展 focused suite 为 `173 passed, 1 skipped`，workflow 文件单独为 21 passed。
- 已验证：implementation context SHA-256 是
  `3a0d8782b28d70e2702ba99d8f77a6c9d0180377f00791d94f9750cf729df338`，绑定 current subject、
  spec、Policy、classification 与上述 evidence。
- 未验证：新 head 的真实 GitHub `ai-quality-gate` 尚未运行；旧 run `33403951577` 仅证明修复前
  detached-HEAD 拒绝。当前本地 Gate 将在新 implementation review 与代码批准后执行。

## 审核问题

- 四份 Policy 是否只包含一致版本升级和预定 timeout 修改，所有检查语义与阈值是否保持不变？
- 90 分钟 job 是否覆盖 68.5 分钟固定 V2 预算，同时没有扩大权限或改名 required check？
- attachment 是否始终固定 event SHA、仅 formal path 创建 runner-local branch，并对 branch/SHA
  所有不一致 fail closed？
- workflow tests 是否同时固定结构和真实 Git detached/attach 行为，包括 switch 与 post-check 失败？
- acceptance 是否只证明 TASK-0025 历史绑定 stale，且 TASK-0025 artifact 完全未改写？
- 是否存在范围外差异、未关闭 high/critical finding、未验证场景或未披露外部动作？

## 推荐结论

若独立 implementation reviewer 确认 current diff、V1 evidence 与冻结规格一致且无未关闭的
high/critical finding，建议 `APPROVE`，随后请求所有者对 current subject 与 evidence 重新批准代码。
