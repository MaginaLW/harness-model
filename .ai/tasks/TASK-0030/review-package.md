# Review Package

## 审核目标

决定是否接受 TASK-0030 在 subject `26e57b82f6230ae3528583d7829a2270ad89acfd` 上完成的
Policy 2.2.0 验证超时加固，以及为保持 Phase 02 历史绑定语义而追加的最小 acceptance
修正。批准范围仅是进入本地只读 Gate；push 与创建 PR 使用所有者已有单独授权，merge 未授权。

## 背景

TASK-0029 的正式 V1 两次在 600 秒 coverage runner 上限失败；隔离 coverage 曾在 579.8 秒
通过，regression 也曾接近该边界。TASK-0030 由 `REVIEW / V1` 管理，base 为
`37dce2a61a5dc484b077ba4463cede2be04dd746`，classification input 为
`fcb29d35ec212dfcd9c75dafa0345141e9a35bc5d805ca285506ca79f09e5656`，冻结规格为
`8e74f113766f452509bfc9453e2b20c18705388dd28fc4b2dd4a5f881cbc9c66`，active Policy 为
`1f684f4bf4bd2e3c28b7a04903628790f7be40f88a1dbf54587b09b90230267f`。最新独立设计审核
`REV-0059` / context `30b38db82707d2e5a3792c48e6bc2bc250cebf046afba567dbe883addbff0528`
为 APPROVE，findings 为空，所有者随后批准该扩展规格。

首次 Policy 2.2.0 V1 保留为失败链：regression 621.97 秒、coverage 735.31 秒，均未 runner
timeout，但同一 acceptance 文件仍把 TASK-0025 的历史 Policy 2.1.0 classification 当作
current。扩规格后只修正该测试的 stale-binding 断言，并格式化已在原范围内的 plan 测试；
TASK-0025 的 classification、context、evidence、review、approval、event 与 Gate 均未改写。

## 代码地图

- `.ai/policy/{hard-rules,routing,permissions,verification-levels}.yaml`：统一版本 `2.2.0`；仅
  V1/V2 regression 与 coverage 分别改为 900 秒和 1200 秒。
- `.github/workflows/ai-quality-gate.yml`：job 上限 90 分钟，高于 V2 固定检查 68.5 分钟
  最大串行预算。
- `tests/unit/test_policy.py`、`tests/unit/test_verification_plan.py`：固定 raw/parsed Policy
  版本、命令、parser、required、环境、阈值与两个新 timeout。
- `tests/integration/test_github_workflow.py`：固定只读 workflow 与 90 分钟上限。
- `tests/acceptance/test_phase_02_self_hosting.py`：把 TASK-0025 作为历史 2.1.0 绑定，验证其
  相对 active Policy fail closed，并只读取 immutable context 做负向复用校验。
- `README.md`、`CHANGELOG.md` 与三份 operations 文档：同步当前版本、预算理由和恢复边界。
- `.ai/tasks/TASK-0030/**`：保存冻结规格、三轮设计审核、批准、失败/恢复链、V1 evidence 与
  implementation review 绑定。

## 语义变更

active Policy 从 `2.1.0` 升至 `2.2.0`。V1/V2 的 `regression_tests` 上限由 600 调为 900 秒，
`coverage_xml` 由 600 调为 1200 秒；检查集合、命令、parser、required、环境、85% 总覆盖率、
90% diff coverage、V2 prefix/extras 与权限保持不变。GitHub job 由 35 调为 90 分钟，不改变
required check 名称、触发器、只读权限、bootstrap transition 或 formal resolve/verify/gate 路径。

Phase 02 acceptance 不再把 TASK-0025 的历史 classification 与 active bundle 强行判等；它
固定历史 digest、断言与 active digest 不同，并要求 current verifier context 构建返回
`VERIFIER_CONTEXT_CLASSIFICATION_STALE`。已保存 context 只用于证明跨 task 复用被拒绝，不能
形成 current readiness。

## 风险

- 放宽时间预算可能延长真实失败反馈，因此只调整两项已实测接近旧上限的检查，并用精确断言
  防止其他 timeout、命令或 required 状态漂移。
- 90 分钟 job 上限必须高于 68.5 分钟合法串行预算；若平台资源异常，检查仍以失败或 timeout
  结束，不降级为 warning。
- 历史绑定测试若读取或改写 TASK-0025 current artifact，可能伪造 readiness；本实现只读取
  digest-addressed immutable context，并明确断言 classification stale。
- Windows 的四项 symlink capability skip 仍存在，不证明其他平台或 live Hook 行为。
- 未执行或授权 merge、deploy、发布、凭据、付费调用、远端分支删除或保护规则变更。

## 证据

- 已验证：current V1 evidence 结论 `passed`，10/10 required checks 全部 passed，evidence
  SHA-256 为 `0aceba3d520bceebb1de2ce4a29fd3004d73aebd34a0eb5bcacba545e7bd85db`。
- 已验证：unit tests 为 `1084 passed, 3 skipped`；完整 regression 为
  `1589 passed, 4 skipped`，耗时 619.87 秒；coverage collection 为
  `1589 passed, 4 skipped`，耗时 612.29 秒并生成 XML。
- 已验证：contract、scope、Ruff、336-file format check、mypy 与 smoke 均 passed；diff-cover
  对本次仅 Policy/workflow/test/doc 变更报告 no executable coverage lines sentinel，并通过
  90% 门禁语义；`unverified_scenarios: []`。
- 已验证：implementation context SHA-256 为
  `bab67b8606f36e1e5bb7aace37e893d1e880a3a06ceabfcb02931ebacc57f607`，绑定 current subject、
  spec、Policy、classification 与上述 evidence。
- 未验证：真实 GitHub PR 的 Linux `ai-quality-gate` 尚未运行；push/PR、merge、deploy、发布、
  分支删除及其他远程或破坏性动作均不由本地 V1 证明。

## 审核问题

- 四份 Policy 是否只包含一致版本升级与四个预定 timeout 修改，V2 prefix 是否保持严格一致？
- workflow 的 90 分钟上限是否足以覆盖 68.5 分钟固定预算，同时没有扩大权限或改名 required check？
- raw/parsed/workflow contract 测试是否足以阻止命令、parser、required、环境和阈值弱化？
- acceptance 修正是否只证明 TASK-0025 历史绑定 stale，且没有改写或复用其 artifact 形成 readiness？
- 是否存在范围外差异、未关闭 high/critical finding 或未披露的外部动作？

## 推荐结论

若独立 implementation reviewer 确认当前 diff、V1 evidence 与冻结规格一致且无未关闭的
high/critical finding，建议 `APPROVE`，随后请求所有者对 current subject 与 evidence 的代码批准。
