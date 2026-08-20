# Chapter 2：任务记录与状态核心

Chapter 2 在仓库的 `.ai/tasks/TASK-xxxx/` 中保存任务。`task.yaml` 是当前物化状态，`events.jsonl` 是不可省略的追加历史；`spec.md`、`classification.json`、`approvals.json` 和 `evidence.json` 分别保存后续治理输入。仓库身份来自版本化的 `.ai/repository-id`，绝对 checkout 路径只用于诊断。

## 写入与恢复

YAML、JSON 和文本先写同目录随机临时文件，flush/fsync 后用 `os.replace`。任务 ID 通过原子创建下一个合法目录预留，竞争时重新扫描，最多十次。

状态变化先生成新事件和新任务，在 `task.yaml.next` 暂存任务，再追加并 fsync 事件，最后替换 `task.yaml`。如果最后一步中断，staged task 会保留；下次可写读取以事件重放确认 staged 终态，修复物化状态并追加 `state_recovered`。没有合法 staged task 的状态不一致视为直接篡改并拒绝，不自动修复。

`start` 创建前先写 `creation_failed.json`，四个必需文件全部完成后才移除。失败目录不会被新任务复用；使用 `aiflow start --recover TASK-xxxx` 重写完整记录。

## 状态主路径

```text
NEW → CLASSIFIED
CLASSIFIED → WAITING_FOR_ASK | WAITING_FOR_SPEC_REVIEW | READY_TO_IMPLEMENT | BLOCKED
WAITING_* → READY_TO_IMPLEMENT → IMPLEMENTING → VERIFYING
VERIFYING → VERIFIED | FAILED | ESCALATED | BLOCKED
VERIFIED → APPROVED_FOR_MERGE | WAITING_FOR_FINAL_REVIEW
WAITING_FOR_FINAL_REVIEW → APPROVED_FOR_MERGE → MERGED
FAILED → IMPLEMENTING
ESCALATED | BLOCKED → CLASSIFIED
```

允许边、事件类型和前置条件类别只有 `src/aiflow/state.py` 一份生产来源。`task_created`、`spec_frozen`、`approval_recorded`、`evidence_generated` 和 `state_recovered` 是封闭的非状态事件，自循环但不能伪装成普通转换。

## 命令示例

```powershell
aiflow start --objective "实现一个有边界的变更" --allow "src/**"
aiflow start --recover TASK-0001
aiflow begin TASK-0001 --actor agent-id
aiflow begin TASK-0001 --actor agent-id --reason "修复失败检查"
aiflow status TASK-0001
aiflow status TASK-0001 --format json
aiflow close TASK-0001 --result merged --merge-commit <sha> --actor operator-id
```

`begin` 验证冻结规格、当前分类、所需规格批准及 Git 基线。风险性失败必须先升级。`close` 只确认 commit 对象存在并记录已经发生的外部合并，不运行 merge、push 或远程 API。`status` 严格只读；route、批准或证据不存在时显示 `not_available`，不会显示为通过。

## 失败排查

- `START_CREATION_FAILED`：检查保留的 `creation_failed.json`，使用提示的 recover 命令。
- `STATE_EVENT_*`：检查 JSONL 语法、连续 sequence、前态链和事件 Schema。
- `STATE_MATERIALIZATION_MISMATCH`：若没有 `task.yaml.next`，视为直接修改或不完整复制，不要手工覆盖事件。
- `BEGIN_*`：补齐冻结、分类、批准或处理 Git 漂移；需要升级的失败不能直接重试。
- `CLOSE_COMMIT_*`：确认 SHA 是当前仓库中已存在的 commit 对象。

Policy 规则及优先级仍以 `.ai/policy/` 为准，本说明不复制规则表。
