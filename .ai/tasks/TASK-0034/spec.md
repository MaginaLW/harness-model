# Task Specification

## 目标

为停在 `VERIFYING` 且没有记录任何验证结果的任务提供一个确定性 CLI 入口，把那轮被中断的运行如实记录为失败并迁移到 `FAILED`，使其能够继续走既有 `begin --reason` 重试路径，不再需要人工编辑状态或以升级方式绕开。

## 范围

- `src/aiflow/cli.py`：为 `verify` 增加互斥的 `--abandon` 入口，要求同时提供 `--actor` 与非空 `--reason`。
- `src/aiflow/verification_service.py`：实现作废逻辑。仅当任务处于 `VERIFYING`、且在最近一次 `verification_started` 或 `verification_restarted` 之后不存在任何验证结果事件时才接受；追加 `verification_failed` 事件迁移到 `FAILED`，payload 记录中断结论与操作者给出的理由。
- `tests/integration/test_verify_command.py`：覆盖成功作废、状态不符被拒、缺少 reason 被拒，以及作废后可由 `begin --reason` 继续重试。
- `docs/operations/recovery.md`：新增「验证运行被中断」恢复条目，写明诊断、可恢复操作与禁止操作。
- `CHANGELOG.md`：在 Unreleased 记录该行为新增。

行为边界：作废只改变任务状态与事件账本，不写入、不修改、不删除任何 evidence，也不触碰被中断运行已经落盘的 run 日志。

## 非目标

- 不实现续跑，不复用被中断运行中已完成的检查结果，不合成跨时间点的证据（对应已被否决的 OPT-02）。
- 不让 `verify` 在无显式 `--abandon` 时隐式接受 `VERIFYING`（对应已被否决的 OPT-03）。
- 不引入运行存活性、进程归属或并发锁判定。
- 不改变 V0/V1/V2 检查集合、Policy、证据 schema、Gate 语义或 CI 行为。
- 不修改既有 `verification_failed` 在 `begin` 重试路径中的判定规则。

## 验收条件

- 对一个停在 `VERIFYING` 且无结果事件的任务执行 `aiflow verify TASK-ID --abandon --actor A --reason R`，退出码为 0，任务迁移到 `FAILED`，事件账本追加一条 `verification_failed`，且 `aiflow validate TASK-ID` 通过。
- 作废后 `aiflow begin TASK-ID --actor A --reason R` 成功迁移到 `IMPLEMENTING`，随后 `aiflow verify` 可正常开启新一轮完整验证。
- 作废前后 `evidence.json` 字节不变；被中断运行的 run 日志目录及其文件保持不变。
- `tests/integration/test_verify_command.py` 全部通过。
- V1 完整回归（`pytest -q`）、`ruff check`、`ruff format --check`、`mypy src` 均通过，总覆盖率不低于 85%，diff coverage 不低于 90%。

## 禁止动作

push、merge、deploy、delete、secret_export、paid_external_call。本任务不执行任何外部动作，不访问网络，不使用凭据，不产生付费调用。

## 错误行为

- 任务不处于 `VERIFYING` 时必须以非零退出码拒绝，并给出明确的状态错误码，不得回退为开启新一轮验证。
- 最近一次 `verification_started` 或 `verification_restarted` 之后已存在验证结果事件时必须拒绝，避免把一次真实的通过或失败结论覆盖为作废。
- `--reason` 缺失或为空白时必须拒绝。
- `--abandon` 与 `--check`、`--finalize`、`--ci` 等既有模式组合时必须拒绝。
- 上述任一拒绝路径都不得写入事件、状态或证据。

## 回滚

本任务的改动全部在版本控制内且可逆：还原 `src/aiflow/cli.py`、`src/aiflow/verification_service.py`、`tests/integration/test_verify_command.py`、`docs/operations/recovery.md` 与 `CHANGELOG.md` 即可恢复原行为。已经由该入口写入的 `verification_failed` 事件属于 append-only 审计记录，按 REC-03 不得删除或重排；回滚代码不回溯改写既有账本。

## 已冻结决策

### DU-001

- 已选择：`OPT-01`
- 操作者：project-owner
- 回答时间：2026-09-01T22:44:40Z
- 理由：项目所有者选择显式作废重试：优先保证证据始终绑定单一 subject 与单次运行，复用已被测试覆盖的 FAILED 重试路径，不引入跨时间点合成证据或隐式丢弃活跃运行的风险
