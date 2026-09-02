# Task Specification

## 目标

让 CI 的任务解析只依据当前 PR 引入的变更来识别任务目录，使 base 分支前移并包含其他任务的记录时，仍能唯一解析到本 PR 的任务。

## 范围

- `tools/ci/resolve_task.py`：把 `_git_paths` 的变更集合从两点 `git diff base head` 改为以 merge-base 起算的三点 `git diff base...head`，其余解析规则、显式 `AI_FLOW_TASK_ID` 优先级和错误信息保持不变。
- `tests/integration/test_github_workflow.py`：增加回归测试，构造 base 与 head 各含不同任务目录的分叉历史，断言仍唯一解析到 head 引入的任务。
- `CHANGELOG.md`：在 Unreleased 记录该 CI 行为修复。

## 非目标

- 不改 `.github/workflows/ai-quality-gate.yml`、required check 名称、job 时限或任何门禁阈值。
- 不改 `aiflow` 包的任何运行期行为、Policy、证据 schema 或 Gate 语义。
- 不引入仓库变量、不改分支保护、不调整 attestation 或 scope 的判定规则。
- 不为任何既有任务重新生成或修改证据。

## 验收条件

- 当 base 含 `TASK-A` 而 head 只引入 `TASK-B` 时，`resolve_task_id` 返回 `TASK-B`，不再因两个目录出现在两点 diff 中而失败。
- head 确实引入两个任务目录时仍按原错误信息拒绝。
- 显式 `AI_FLOW_TASK_ID` 的优先级、校验和错误路径不变。
- `tests/integration/test_github_workflow.py` 全部通过。
- V1 完整回归、`ruff check`、`ruff format --check`、`mypy src` 通过，总覆盖率不低于 85%，diff coverage 不低于 90%。

## 禁止动作

push、merge、deploy、delete、secret_export、paid_external_call。本任务不执行外部动作、不访问网络、不使用凭据、不产生付费调用。

## 错误行为

- merge-base 不存在或 `git diff` 失败时，必须以原有方式抛出错误，不得回退为「解析成功」。
- head 引入零个或多于一个任务目录时必须拒绝，并保留提示设置 `AI_FLOW_TASK_ID` 的原文。
- 显式任务 ID 非法或目录不存在时必须拒绝。

## 回滚

改动全部在版本控制内且可逆：还原 `tools/ci/resolve_task.py`、`tests/integration/test_github_workflow.py` 与 `CHANGELOG.md` 即恢复原行为。本任务不写入任何任务证据，回滚不涉及审计账本。
