# Review Package

## 审核目标

确认 TASK-0013 在 subject `290254cc70791bcfa9895feab98154b411c2ef55`
上的 Chapter 11.3 变更满足冻结规格：从固定五项 mutation manifest 建立逐项
隔离的 detached 临时 worktree，应用封闭 AST operator，仅运行对应的离线
detector，返回不可变原始执行事实，并在成功或失败后保持主工作树与 Git
worktree 注册表不变。本审核不把这些原始退出码表述为持久化 mutation evidence
或 live V2 passed。

## 背景

TASK-0012 已以 external merge commit
`e5b00f4502354ef9d18ad7d1f9f1c52e27aac604` 记录 `merge_recorded`；其 task-close
治理后继提交 `dc49293936ae8f705b7a474dc5c7b0ac0c981865` 是本任务的干净执行 base。
TASK-0013 当前绑定 REVIEW + V1、Policy
`f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`、classification
input `14b746b5cf4e5553e896c9863c7cb156133919dfbe818bb1eacd581d96b6f6bb` 与冻结规格
`949aee0bca38d4dc5977d3a3a289b463b8f27fb666f6f67d416d1fb3f5a4a281`。

最终设计审查 `REV-0003` 为 `APPROVE` 且无 findings。首次完整 V1 因 Ruff
格式与 changed-line coverage 87% 未通过；修复增加了定向 seam 测试并形成最终
subject。重新执行的完整 V1 已通过。最终独立实现审查 `REV-0004` 绑定 context
`4330ffca7b4daf9a0fbb4a662edf3c47dec7f7f5af76a4a1d1ad7491ee766edd`，给出
`APPROVE`。其中一个 medium 命名 finding 已通过追加的 task-local clarification
关闭：`full_v1_verification_rerun` 仅是 canonical `v1_verify` 的 retry-instance
标签，不是第三类事务，也不产生新授权。

## 代码地图

- `src/aiflow/mutation_runner.py`：固定 manifest 入口、五个封闭 AST operator、
  detached worktree 生命周期、最小 detector 环境、timeout/进程树终止、主树与
  worktree-registry 前后快照，以及稳定 fail-closed reason code。
- `tests/unit/test_mutation_runner.py`：覆盖五个 operator、结构锚点、路径 containment、
  subject/worktree/launch/timeout/infra/cleanup 失败、Windows readonly cleanup、
  最小环境及不可变有序返回。
- `tests/integration/test_mutation_runner_contract.py`：真实创建五个串行隔离
  worktree，证明每项 baseline exit `0`、mutant exit `1`，隔离导入生效且主树、
  注册表及临时目录恢复。
- `docs/implementation/chapter-11-acceptance-integration-mutation.md`、Chapter 11
  与 overall state：仅把 11.3 标为 completed，指针移到 11.4，并保留
  11.4/11.5、两个 exit checks、持久 mutation evidence 与 live V2 pending。
- `.ai/tasks/TASK-0013/`：冻结规格、分类/批准、single-use action/use receipts、
  失败与重试事实、V1 evidence、结构化 reviews 和事务类型澄清；这些是 task-local
  治理事实，不改变已验证 tracked subject。

## 语义变更

仓库现在可以针对当前完整 commit，从固定 Phase 02 五项 manifest 顺序执行定向
mutation probes。每项都在独立、受控系统临时根后代的 detached worktree 中先跑
未变异 detector，再应用唯一硬编码 AST 变换并重跑相同 detector。runner 不接受
自由 manifest、operator、argv、环境、路径或 timeout 输入，不使用 shell、用户
hooks 或主工作树 checkout；stdout/stderr 不持久化。

公开结果只保留 baseline/mutant 原始 exit code、timeout、duration 和 reason code。
cleanup、containment、subject 漂移、主树 bytes/status 或 Git worktree registry
变化都会保守失败。当前实现没有把 runner 接入 live V2，没有生成 killed/survived
evidence，也没有修改 approval、Gate、Policy 或 V0/V1 语义。

## 风险

- AI Flow 当前没有 action-consume CLI/schema；single-use delete approval 依赖先写
  use record 的人工审计 fallback。两次 V1 action 与 focused actions 均已消费且不可
  复用，clarification 不重新授予权限。
- Windows 防病毒或索引器若持锁超过有界重试窗口，runner 会保守报告 cleanup
  failure，并可能留下受控临时残留；后续清理仍需单独、精确授权。
- runner 限制环境且冻结 detector 保持离线，但不提供 OS 级网络沙箱。
- repository-wide Git worktree registry 若被外部并发操作改变，runner 会 fail closed
  为主树变化，不会跨临时根清理其他工作树。

## 证据

- 已验证：base `dc49293936ae8f705b7a474dc5c7b0ac0c981865`、subject
  `290254cc70791bcfa9895feab98154b411c2ef55`、冻结规格、Policy、classification
  input 与 evidence 均 current；AI Flow evidence canonical SHA-256 为
  `230ecfe761a88906923cb147f94f4735b0abeee4bb3ac299d204faf5589cfd04`。
- 已验证：完整 V1 rerun action
  `b9e57469cab7769667138fa3d46b383b446e03b099cd7c149c158b8113aad43a`
  已单次消费；10/10 required checks 全部 passed，无 timeout 或 reason code。
- 已验证：regression 与 coverage 两轮各为 `791 passed, 3 skipped`；changed-line
  coverage 为 `91.1%`（`379/416`），超过冻结门槛 90%。
- 已验证：完整 V1 中 runner 调用两次，共创建并删除 2 个受控临时 root 与 10 个
  串行 detached worktree；结束后 `aiflow-mutation-*` 残留为 0，Git worktree
  registry 前后 blob hash 均为
  `9ff1ceccb6293a90ddaf9c974cacd82174313792`。
- 已验证：独立只读代码审查未发现高/中严重度实现 finding；规格审计发现的事务
  标签歧义已由 `action-transaction-type-clarification.md` 关闭，并经两名只读审查者
  复核通过；结构化 `REV-0004` 当前可批准。
- 未验证且未实现：11.4 的 killed/survived evidence 持久化、11.5 replay 与
  approval/Gate 接线、真实 live V2、两个 Chapter 11 exit checks，以及 push、merge、
  deploy、task close、凭据/付费调用和任何新的 delete transaction。

## 审核问题

- 五个 operator 是否只触达冻结 target/symbol 中唯一预期 AST guard，并对结构漂移
  稳定拒绝？
- detector 的 argv、cwd、环境、timeout、进程树与 source import 是否始终受控且
  shell-free？
- 任意 baseline、mutant、timeout、infra、operator 或 cleanup 路径是否都保持主树
  和 worktree registry 不变，并阻止越界删除？
- task 文档与状态是否只宣称 11.3 隔离执行完成，而没有提前宣称 mutation evidence
  或 live V2 passed？
- 当前 evidence、structured review 与 governance-only dirty worktree 是否足以进入
  用户 code/document approval 门？

## 推荐结论

`APPROVE`。最终 subject 的完整 V1 evidence 与结构化实现审查均 current 且通过，
唯一治理命名 finding 已关闭，未发现阻止当前代码/文档批准的遗留问题。该结论不
授权 push、merge、deploy、task close、任何新 delete action 或 live V2。
