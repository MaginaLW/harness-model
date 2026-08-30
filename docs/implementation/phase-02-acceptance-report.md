# 阶段二验收报告

- 状态：`completed`
- 基线日期：`2026-08-30`
- 内容基线 commit：`733962ace50e430f69cd2193a96bc797fc8a18b6`（后续提交包含 attestation 与自举收尾修订，但不得回写或冒充该历史基线证据）
- 范围：Chapters 8–13 / P2-REV-01、P2-V2-01、P2-VER-01、P2-MUT-01、P2-ESC-01、P2-HOOK-01
- Policy：`2.1.0`，SHA-256 `f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`
- 治理模式：`.ai/bootstrap-mode.yaml` 为 `active`；本报告是仓库自身的本地质量基线，不是 release、merge 或外部动作授权

## 结论

Chapter 13.1–13.6、四项 Chapter 13 exits 和阶段二五项总验收全部通过。最终投影为
13/13 chapters、77/77 tasks、408/408 steps、24/24 exits。六项输入均有实现、测试、
artifact/hash、可重放 argv、outcome 和 known limits；详细映射见
[验收矩阵](phase-02-acceptance-matrix.md)与[证据索引](phase-02-evidence-index.md)。

阶段完成由精确历史证据和当前回归基线共同证明，不改变 task-local freshness：TASK-0025
结构有效且 lifecycle 为 `MERGED`、`merge_readiness: not_applicable`；TASK-0028 结构有效，
lifecycle 为 `APPROVED_FOR_MERGE`，但 current subject
`cb1e15b547a8280ddf7b7515f45367aec14aa490` 的 approval/evidence 为 stale，
`merge_readiness: reverification_required`。本次没有编辑 ledger 使旧 evidence“变新”。

## Chapter 13 exits

| Exit | 结果 | 证据 |
|---|---|---|
| CH13-EXIT-01 | passed | TASK-0028 H1 在原 subject 完成 design/implementation 双审核、独立 local-final V2、code approval/local Gate 和隔离 CI/Gate；13.4 负向 E2E 覆盖关键拒绝路径 |
| CH13-EXIT-02 | passed | H1 local/CI 均为 14/14、five killed、zero unverified；CI-003 receipt 固定 audit head 与 Gate hash；本次又在精确 local attestation 只读复放 Gate |
| CH13-EXIT-03 | passed | Chapter 12 Hook/CLI/CI same-fact semantic parity，加上 actor、mutation、scope 和 stale review 的公开边界 E2E |
| CH13-EXIT-04 | passed | diff、task ledger、状态和命令审计未引入 V3、模型路由、资源调度或未经授权的外部动作 |

这些 exit 是产品阶段交付证据，不是把当前 TASK-0028 判为 merge-ready。历史 review、approval、
mutation artifact 和 Gate 仍只能用于其原 task/subject/spec/Policy/attestation。

## 阶段二内容基线质量

| 检查 | 结果 |
|---|---|
| Phase 1/2 traceability | `10 passed`；六项固定输入、路径、历史 SHA、完整 Chapter 12 commit 与 current TASK-0028 subject 均由 executable assertions 核对 |
| Phase 2 self-hosting | `25 passed`（acceptance、integration、正向 E2E、负向 E2E） |
| 13.4 negative E2E | `5 passed`；same/empty actor、survived mutation、scope escalation、latest stale review 与 zero-write 断言 |
| REVIEW/Gate/observation 集成回归 | `148 passed` |
| full pytest | `1581 passed, 4 skipped in 466.19s` |
| Ruff | `All checks passed!` |
| format | `332 files already formatted` |
| mypy | `Success: no issues found in 41 source files` |
| branch coverage | `87.58%`；`7151` statements、`2406` branches；`--cov-fail-under=85` passed |
| diff-cover | 基于 `e8f60dacbe1e8681ea9d8a9e299621d34ddb05fe`：`No lines with coverage information in this diff.`；sentinel passed，不是数值或 100% 声明 |
| whitespace/state | `git diff --check` passed；overall/chapter-13 YAML 可解析 |

基线后的收尾审计发现，原 GitHub Actions job 的 15 分钟总时限小于仓库内保留的真实 V2
检查耗时，且 bootstrap 路径没有消费锁文件或执行 coverage/diff coverage。提交
`8e82e3c32061b428bb11952d83cbd31bb45c0b61` 已将
job 时限改为 35 分钟，改用固定 uv/locked sync，并在 bootstrap 路径执行一次完整 branch
coverage pytest、85% 总覆盖率、90% diff coverage、PR 范围 whitespace、Ruff、format 与
mypy。该修订不改变上述历史 evidence 的 subject/attestation，也不能代替一次真实远端 PR
运行或平台 branch-protection 配置；外部门禁在取得这两项证据前仍不得声明为已启用。

四项 skip 均为已知 Windows symlink capability 限制：verification Git scope、mutation evidence、
scope 和 verification plan 各一项。它们不证明 Linux/macOS live Hook 或符号链接行为。

## 历史 Gate 只读复放

成功复放固定 TASK-0028 code-approval attestation
`f35d3094a8385806abff2996691e5224bedb00e2`，结果为：

```json
{"passed": true, "reason_codes": [], "recovery_argv": [], "route": "REVIEW", "task_id": "TASK-0028", "verification_level": "V2"}
```

复放没有重新执行 mutation，而是附带当前仍保存的原 ignored artifact：

`.ai/tasks/TASK-0028/logs/MUTRUN-20260829T140929Z-1ceeb5a57d70bcd9/targeted-mutation/`

Windows clone 必须在 checkout 前设置
`core.autocrlf=false`、`core.eol=lf`，使 manifest SHA
`1dac9624e5a221784d56dc189e5bb225662334b550238b13ecf7587c96d277c0` 和 runner SHA
`0e22fced34cfee5bcd8eab7d03bcddbbf68eaa560208e371b37f3ff518989145` 与 artifact 一致。

两次未采用的诊断结果也保留在本报告中：detached TASK-0025 checkout 因 branch 不再是
`main` 且缺少原 artifact，返回 `GATE_REPOSITORY_CHANGED` / `GATE_V2_MUTATION_NOT_KILLED`；
TASK-0028 的 CRLF checkout 因 manifest/runner raw SHA 不匹配而返回
`GATE_V2_MUTATION_NOT_KILLED`。它们证明 Gate 对环境漂移 fail closed，不能算失败的产品基线，
也不能被改写成 successful clean-clone replay。clean clone 不包含 ignored runtime artifact。

最初的 detached 临时 worktree 已由 Git 精确移除，可从其 commit 重新创建；随后三个精确
Gate clone 和两个 coverage 临时文件均已移入回收站，可从回收站恢复。主仓库、refs 和 task
records 未被这些清理动作修改。

## 失败、限制与非目标

- 历史 REQUEST_CHANGES、失败 verification/CI receipt、stale evidence/approval、survived/missing
  mutation 和平台 skips 继续追加式保留；后续成功没有覆盖它们。
- actor 只是 task-local 审计标签，不是人员、模型或外部身份认证。13.4 survived fixture 隔离
  public consumer/Gate 语义；binding、manifest/source digest 与 review freshness 的组合边界由
  integration/self-hosting suite 证明。
- Hook/CLI/CI parity 只覆盖列出的结构化 facts 与 semantic fields；不证明 Linux/macOS live
  Hook、未安装客户端、IDE/GUI/remote Git、自由 shell、通用命令拦截或 OS sandbox。
- package 版本保持 `0.1.0`。未创建 tag，未发布 registry，未移除 bootstrap 标记。
- Phase 3 保持 `not_started`/blocked；内部记录充分性口径、真实 V3 用例与统一 telemetry
  contract 尚未满足。未实现或授权 V3、模型路由、信任度、成本优化或资源调度。
- 除历史 single-use action 批准和本轮范围明确的精确 task-owned worktree/OS-temp cleanup 外，
  未删除仓库或业务数据；未执行或授权 push、merge、deploy、凭据导出、付费调用或其他外部
  系统动作。
