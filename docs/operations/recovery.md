# AI Flow 故障恢复手册

先运行 `python -m aiflow status <TASK-ID> --format json` 和 `git status --short --branch`。保留 `.ai/tasks/<TASK-ID>/events.jsonl`、失败 marker、evidence 和 logs；不通过直接改写 `current_state`、删除事件或伪造批准来“修复”任务。

## REC-01 半创建任务

- 诊断：检查 `.ai/tasks/<TASK-ID>/creation_failed.json`，并运行 `python -m aiflow status <TASK-ID> --format json`。
- 可恢复操作：在同一仓库运行 `python -m aiflow start --recover <TASK-ID>`；CLI 会核对 repository ID 并原子完成缺失文件。
- 禁止操作：不复制其他仓库的 marker，不手工预占或重用 task ID，不删除 marker 后假定创建成功。

## REC-02 损坏 JSON/YAML

- 诊断：运行 `python -m aiflow validate <TASK-ID>`，记录 `STORAGE_PARSE_FAILED` 或 `CONTRACT_VALIDATION_FAILED` 及精确文件。
- 可恢复操作：从当前 task 的已提交版本或可验证备份恢复单一损坏文件，重跑 `validate` 并确认事件重放一致。
- 禁止操作：不猜测 hash、commit、approval 或 evidence 字段，不用空 JSON/YAML 覆盖损坏文件。

## REC-03 事件与物化状态不一致

- 诊断：`python -m aiflow validate <TASK-ID>` 报告物化 `task.yaml` 与 `events.jsonl` 终态不一致；保留两者和 `task.yaml.next`。
- 可恢复操作：重运原 CLI 命令触发内建原子恢复；若仍失败，停止实施并以保留的事件和 marker 建立修复任务。
- 禁止操作：不直接编辑 `current_state`，不删除或重排 JSONL 事件，不跳过重放检查。

## REC-04 FAILED 重试

- 诊断：用 `status` 查看 `missing_conditions` 和最后失败事件，并读取对应 run 的 stderr/stdout logs。
- 可恢复操作：修复具体失败原因后运行 `python -m aiflow begin <TASK-ID> --actor <ACTOR> --reason "<FIX>"`，再执行全量 `verify`。
- 禁止操作：不在没有 retry reason 时重试，不删除失败 run，不将定向 provisional 证据当作 final evidence。

## REC-05 BLOCK 解除

- 诊断：读取 classification 中的 BLOCK rule、恢复条件、Policy hash 和当前 classification input hash。
- 可恢复操作：每个恢复条件都用 `python -m aiflow resolve <TASK-ID> --condition <CONDITION> --evidence-ref <TASK-LOCAL-FILE> --reason <REASON> --actor <ACTOR>` 留痕；降级还需明确 `--authorize-downgrade`，然后重新 `classify`。
- 禁止操作：不用工作树外或无法读取的 evidence ref，不自行降级，不在条件未满足时直接改状态。

## REC-06 stale evidence

- 诊断：运行 `python -m aiflow gate <TASK-ID> --format json`，根据 `GATE_EVIDENCE_STALE`、`GATE_REPOSITORY_CHANGED` 或其他 reason code 核对 subject、attestation、spec 和 Policy hash。
- 可恢复操作：对当前 commit 重跑 `sync`、全量 `verify`；CI 必须在 PR 最新 HEAD 用新临时目录重验。REVIEW 证据变化后重新获取 code approval。
- 禁止操作：不改 evidence JSON 内的 commit/hash，不复用旧 CI 输出，不在主 HEAD 伪装旧 attestation。

## REC-07 Policy 变化

- 诊断：`status`、`validate` 或 `verify` 显示 Policy hash 不匹配；用 `git diff -- .ai/policy` 定位实际变化。
- 可恢复操作：用 `escalate --reason-code policy_changed` 记录影响和下一步，重新 `classify`、`freeze`、必需批准和全量 `verify`。
- 禁止操作：不恢复旧 Policy hash 来保留批准，不降低 route/V 等级，不复制 Policy 规则到脚本绕过重分类。

## REC-08 无法唯一解析任务

- 诊断：CI 或差异解析报告零个/多个 task ID；用 `git diff --name-only <BASE>...<HEAD>` 查看变更包含的 `.ai/tasks/<TASK-ID>/` 路径。
- 可恢复操作：核对 repository ID 后，向 CI 传入唯一的显式 task ID；若变更实际混合了多任务，建立新的有界任务/分支并重新验证。
- 禁止操作：不按字典序或最新时间猜选 task ID，不忽略 repository ID，不将多个任务的证据合并成一个 Gate 输入。

## REC-09 stale 或不可批准的结构化审核

- 诊断：运行 `python -m aiflow review show <TASK-ID> --stage <design|implementation> --format json`；再生成当前 context，核对 `context_sha256`、阶段、结论和 high/critical finding 状态。
- 可恢复操作：事实变化后基于新 context 记录新的 review；现有 finding 已修复时，用 `python -m aiflow review resolve <TASK-ID> --review <REV-ID> --finding <RF-ID> --reason <REASON> --actor <ACTOR>` 追加 revision，然后重新取得对应 spec/code approval。
- 禁止操作：不改写旧 context/record，不把 design record 用作 implementation approval，不复用 subject/evidence 变化前的 implementation review，不以自然语言或旧 Markdown 包替代结构化 record。

## 恢复后共同检查

1. `python -m aiflow validate <TASK-ID>` 通过。
2. `python -m aiflow status <TASK-ID> --format json` 的 next event 与预期一致。
3. `python -m aiflow scope <TASK-ID>` 通过。
4. 从当前 subject/attestation 重跑必需验证和 Gate；保留失败证据以供审计。
