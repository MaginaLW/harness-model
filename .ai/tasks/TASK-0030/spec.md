# Task Specification

## 目标

将 active Policy 从 `2.1.0` 升级为 `2.2.0`，为已在 Windows 实测接近或超过 600 秒的
V1/V2 regression 与 coverage 检查提供明确余量，并同步 GitHub job 总上限、contract 测试
和当前运维文档。修复真实 PR 暴露的精确 head SHA checkout 处于 detached HEAD、因而无法满足
task branch binding 的问题；修复后续真实 PR 暴露的 runner temporary root 与 Python OS
temporary root 不一致、导致 formal verify 在任何 Policy check 前 fail closed 的问题；不得减少
任何检查、降低阈值、放宽 Git 或临时目录绑定，或扩大自动权限。

## 范围

1. `.ai/policy/hard-rules.yaml`、`routing.yaml`、`permissions.yaml` 和
   `verification-levels.yaml` 的 `policy_version` 一致从 `2.1.0` 升为 `2.2.0`。
2. 只在 V1 与 V2 中将 `regression_tests.timeout_seconds` 从 `600` 调为 `900`，将
   `coverage_xml.timeout_seconds` 从 `600` 调为 `1200`；V2 继续保持完整、同序的 V1 prefix。
3. `.github/workflows/ai-quality-gate.yml` 的 job `timeout-minutes` 从 `35` 调为 `90`，使其
   高于新 V2 固定检查的 68.5 分钟最大串行预算，并保留 setup、Gate 与 runner 波动余量。
4. workflow 继续让 `actions/checkout` 固定到 `${{ github.event.pull_request.head.sha }}` 且
   `fetch-depth: 0`。只在 bootstrap detection 已确认正式治理后、`Read repository identity` 与
   `Resolve task` 之前，新增一个带相同 formal-path `if` 条件的 fail-closed 步骤。该步骤只通过
   step `env` 把 `${{ github.head_ref }}` 传为 `PR_HEAD_REF`、把 event head SHA 传为
   `PR_HEAD_SHA`，shell 中每次展开均加双引号；依次要求 source branch 非空、
   `git check-ref-format --branch "$PR_HEAD_REF"` 通过、当前 HEAD 等于 `PR_HEAD_SHA`，再以
   `git switch --force-create "$PR_HEAD_REF" "$PR_HEAD_SHA"` 将同一 SHA 附着到 runner-local
   source branch，最后同时确认 quiet symbolic branch 与 HEAD SHA。bootstrap path 不执行该
   步骤。不得改为仅按可移动 branch ref checkout，不得 fetch 新内容，也不得放宽
   `evaluate_verification_git_context` 的 branch equality。
5. 只在 formal `Verify and Gate` step 的 `env` 中将 `TMPDIR` 绑定到
   `${{ runner.temp }}`，并从 `run_dir="$TMPDIR/aiflow"` 派生 CI run directory，使 Python
   `tempfile.gettempdir()` 与 GitHub runner temporary root 一致。`run_dir` 必须继续是该 root
   的既存严格后代，evidence 与 Gate JSON 必须继续位于同一目录，diagnostics artifact 继续只
   上传 `${{ runner.temp }}/aiflow`。不得修改 Python verifier、接受任意 runner 路径、移除
   strict-descendant/output-containment 校验，或把该环境覆盖扩散到 bootstrap 或无关 step。
6. `tests/unit/test_policy.py`、`tests/unit/test_verification_plan.py` 和
   `tests/integration/test_github_workflow.py` 固定 active version、原始/解析后 timeout 和 job
   bound，并固定精确 SHA checkout、formal-path 条件、branch attachment 的环境/引用/命令/
   顺序、branch 格式检查和前后双重 SHA 检查；测试还必须固定空 branch、初始 SHA 不匹配、
   branch 格式或 switch 失败、最终 symbolic branch 不匹配及最终 SHA 漂移均 fail closed；
   workflow contract 还必须固定 formal `Verify and Gate` 独占的 `TMPDIR` step env、
   `$TMPDIR/aiflow` 与 evidence/Gate/artifact 路径一致性；verification-plan 测试必须模拟 Python
   临时根和 runner 临时根不同，证明只有绑定后的严格后代可通过，未绑定的既存 sibling root
   仍以 `CI_RUN_DIR_INVALID` 拒绝；
   `tests/acceptance/test_phase_02_self_hosting.py` 仅将 TASK-0025 的 Policy `2.1.0`
   classification 作为历史绑定，明确断言它与 active Policy `2.2.0` 不同且 verifier context
   构建 fail closed，再用已保留的 immutable context 验证复用拒绝；不复制路由或 Gate 决策表，
   不修改任何 TASK-0025 artifact。
7. `README.md`、`docs/operations/quickstart.md`、
   `docs/operations/github-branch-protection.md`、`docs/operations/recovery.md` 和
   `CHANGELOG.md` 同步当前版本、预算理由、精确 SHA/附着分支的双重 CI 绑定、失败恢复边界与
   Unreleased 记录；文档明确 source branch 只用于命名 runner-local branch，commit 权威仍是
   event head SHA，步骤不 fetch、不 push，也不改变 bootstrap path；当前运维文档与
   `CHANGELOG.md` 还要说明 formal Verify/Gate 将 Python temporary root 明确绑定到 runner
   temporary root，且不放宽 CLI 目录校验。
8. `.ai/tasks/TASK-0030/**` 仅由本任务正式生命周期维护。历史 state、task、evidence、
   approval 和 acceptance 文档中的 `2.1.0` 保持形成时事实，不得改写；当前 acceptance
   contract 可按第 6 项显式验证这些历史事实已相对 active Policy 失效。

## 非目标

1. 不修改检查集合、命令、parser、required 标记、85% 总覆盖率要求、90% diff coverage、
   V2 targeted mutation/independent verifier 语义或 GitHub required check 名称。
2. 不修改 Python 运行时代码、Git context 判定、Schema、模板、Hook、依赖、锁文件、package
   version 或 Release。
3. 不优化测试性能，不引入并行测试、自动重试、缓存复用或平台特例，也不把失败降级为 warning。
4. 不修改、重验证或关闭 `TASK-0029`；它在本修复合并后另按 current Policy 恢复。
5. 不启动 Phase 3/4，不发布 package，不创建 tag 或 Release。
6. 不修改其他 acceptance、integration 或 E2E 测试，不刷新 TASK-0025 的 classification、
   verifier context、evidence、approval、review 或 Gate 结论。

## 验收条件

1. 四份 active Policy 均报告 `2.2.0`，Policy bundle 可重复加载且新 digest 与 `2.1.0`
   不同；历史记录保持不变。
2. V1/V2 原始及解析后的 `regression_tests` 都精确为 `900` 秒，`coverage_xml` 都精确为
   `1200` 秒；其命令、环境、parser、required 与覆盖率阈值不变，V2 prefix 仍严格一致。
3. workflow job 上限精确为 `90` 分钟，触发器、只读权限、required check 名称、锁定安装、
   bootstrap transition 与 formal resolve/verify/gate 命令均不变。checkout 仍固定 event head
   SHA；branch attachment 只在 formal path、bootstrap detection 之后且 task resolution 之前
   运行，将同一 SHA 附着到 `${{ github.head_ref }}`。空 branch、非法 branch、初始 SHA 不匹配、
   switch 失败、最终 branch 不匹配或最终 SHA 漂移均立即失败；formal `Verify and Gate` step
   独占 `TMPDIR: ${{ runner.temp }}`，使用 `$TMPDIR/aiflow`，diagnostics 仍读取同一 runner
   temporary path。测试固定全部拒绝路径、步骤顺序和临时根/运行目录/产物路径一致性。
4. Phase 02 self-hosting acceptance 明确保留 TASK-0025 classification 的历史 Policy SHA
   `f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`，断言它不等于 active
   digest；`build_verifier_context` 返回 `VERIFIER_CONTEXT_CLASSIFICATION_STALE`，已保存的
   immutable context 仍可作为负向复用校验输入且不能形成 current readiness。
5. focused Policy/plan/workflow/acceptance tests、task contract、scope、Ruff、format、mypy、
   完整 pytest、coverage XML 与 90% diff coverage 均通过，且只读 Gate 返回 passed。
6. 真实 PR 最终 head 的 required `ai-quality-gate` 成功；日志证明 checkout 的精确 event SHA
   在附着 source branch 前后不变，并执行 formal `Resolve task`、`Verify and Gate` 与
   diagnostics upload；formal verify 不再因 runner/Python temporary root 不一致而启动前失败。
   push/PR 使用当前用户单独授权，merge 仍未授权。
7. 最终业务 diff 是本规格列出的文件子集，其余 tracked diff 仅限 TASK-0030 治理产物。

## 禁止动作

任务实现、审查和验证不得 push、merge、deploy、delete、发布 package、导出凭据、发起付费
调用或改变 GitHub 配置。Gate 通过后，外部 actor 只能依据当前用户授权推送本修复分支并创建
PR；不得合并、删除分支、修改保护规则、发布 tag/Release 或执行其他外部动作。

## 错误行为

Policy 文件版本不一致、V2 prefix 漂移、检查/阈值/权限被弱化、job bound 小于合法预算、把
历史 TASK-0025 classification 当作 active binding、仅按可移动 branch ref checkout、branch
attachment 未保持精确 event SHA、formal step 的 Python temporary root 与 runner temporary
root 未显式对齐、run directory 不是严格后代或 output 逃逸、范围扩展、绑定失效、审查或批准
陈旧、验证失败或 Gate 拒绝时必须停止并按 CLI 指引恢复；不得通过降为 V0、跳过 coverage、
手改 evidence、放宽 branch equality/临时目录校验、重复碰运气或恢复 bootstrap 来放行。

## 回滚

未合并时关闭 PR 或前向撤销业务提交；已合并后以新的 AI Flow task 将当前 Policy、job bound
与 branch attachment 前向修订。历史 TASK-0029/TASK-0030 事件、失败 evidence、review、
approval 和 GitHub Actions runs `33403951577`、`33410732408` 均保持追加式，不得删除、重排
或改写为通过。
