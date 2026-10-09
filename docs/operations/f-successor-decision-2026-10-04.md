# F 后继目标与历史验收承接：2026-10-04 核定

建议先完成独立的 ProcessRunner 与验证性能治理，再在实际集成后的干净基线上建立
历史 F 收尾目标。原 TASK-0063 的真实导入窗口已有完整证据，历史核定无需重新取得
付费报告；后继目标的当前质量和原生流程仍须独立完成。本文是可复核的承接方案，
尚未创建后继任务、恢复旧任务、运行新 V2、消费动作或取得新来源。

入口：[当前待办](follow-up-backlog-2026-09-22.md)、
[原 F 规格](f-real-import-acceptance-2026-10-03.md)、
[私有 Windows 修复的资格与边界](windows-private-timeout-repair-2026-10-04.md)。
本次读取了 F 隔离目标的原任务与证据；这些原件当前保留在该目标自己的任务树中，
本文不复制、改写或代替其内容。下列 task 相对路径是原目标内的证据定位。

## 原窗口的固定绑定与当前状态

| 字段 | 核定值 |
| --- | --- |
| Task / branch | TASK-0063 / `codex/f-real-import-acceptance` |
| Repository ID | `b85e5a53-4935-4436-bdbc-c26a241bfae8` |
| Allowed scope | `docs/operations/f-real-import-acceptance-2026-10-03.md`、`.ai/tasks/TASK-0063/**` |
| Base | `3d6528284bc6e867def4fc8139ef67a41544ae48` |
| 原 subject | `f59aa2544701bc4e00644fd291e16b97314c41a6` |
| 本次 observed HEAD | `166fe313b379e7a844eb9bb667cf92932d4010a8` |
| Frozen spec SHA256 | `070b364c23837dade0a91d7c8e6a7a10e2bc7bbcbfb298b296744ce59c35968d` |
| Classification input SHA256 | `da4a218c56b888f2f73571269e740e6076374d8bd6555e0c21c3705553078aa5` |
| Policy SHA256 | `d21a386779147dfad962a0fc0656bef61bc581e27f63c4789dcc06520fa10ff1` |
| Design context SHA256 | `165c5dc259714f91b575b9be295d91ca6a8d33aab411815adf273c7ce9e0e745` |
| 实际 source archive | `TASK0063-ZCODE-DESIGN-003` |
| 原报告 SHA256 / 大小 | `b29e335a03021ef6d13e5b36e1031dcdf7d8d4b20df21576b2988c97882b5355` / 15810 字节 |

本次显式使用 F 检出自己的 `src` 作为 PYTHONPATH，执行只读 `status`、`scope`、
`validate` 和 `gate`。TASK-0063 为 BLOCKED / REVIEW / V2，Missing
`block_resolution`，classification fresh、approvals current、evidence stale，工作区 clean。
`validate` 通过；`scope` 拒绝；Gate 为 REJECT，包括 blocked、scope changed、证据
stale/not passed、V2 未 finalize、检查未完成、Review/code approval 不满足等原因。
已有 current 规格批准不重复索取，但它不批准新的单次动作或不同目标。

## 已完成事实与必须保留的失败

原 context 下已执行 33 条真实验收命令，包括独立 Design Review 004 的真实追加，
旧 token 零写拒绝、首次单份 create-only 导入、重复 already_recorded/no-op，以及
10 组反例的 20 次拒绝。完整任务树路径与实际字节比较、原事件前缀及两路独立封存核对
均留存。证据位于 `acceptance/import-results-001.json`、
`acceptance/source-provenance-001.json` 和 `acceptance/independent-audits-001.json`。
这些事实仅属于上述原 spec/base/context 窗口，不覆盖后来的测试或源码候选。

原报告是保存终稿文本的 UTF-8 精确提取，不添加 BOM、换行、正规化或进度文本。
传输原字节认证、模型/provider/reviewer 身份认证、推理次数与费用上限仍 UNKNOWN。
提示词末尾单个 LF 的实际差异、原始取证失败、六项 pending 观察及独立勘误均保留。
导入没有赋予正式 Finding、人工批准、正式 implementation Review 或 Gate。

第一次完整原生 V2 `run-20261003T001416071827Z` 的结论为 FAILED：14 项中
10 项通过，unit_tests、regression_tests、coverage_xml、integration 四项失败，
integration 在原 600 秒预算超时。总覆盖率检查通过及 89.071% 的派生值不改写失败。
后来的普通维护与 timing observer 诊断也超时，缺最终 summary 的全套结果保持未知。

原 action `13812c7f836fa3d87d34268ef239c562aec5d3f0299bb7cdae71862d7b7a5124`
已单次消费且过期，保持 SPENT。五项变异 baseline 0、mutant 1/killed 的 metadata
存在，但 detector stdout/stderr 因原 runner 接入 DEVNULL 未留存，原批准中的 streams
条件未满足。不得补造流、复用旧 action 或将后继成功回填旧 run。失败与保留核定位于
`preparation/v2-failure-recovery-001/failure-summary-001.json`、
`independent-retention-review-001.json` 及两份后续 timeout summary。

## 旧目标当前不能直接恢复

最近的 escalation 为 sequence 25：`scope_expanded`，BLOCK，
`preserve_and_reassess`，required_conditions 为 `[scope_expanded]`。
因此 status 的 `block_resolution` 只是状态前置概括；真实 CLI resolution condition
必须使用 `scope_expanded`，并以当前有效的 evidence SHA 和版本绑定记录处理决定。
BLOCK 向原 REVIEW 恢复还要求真实人工的版本绑定授权，不能把广义权限写成这种记录。

当前 base 到 HEAD 的净差异包含原 scope 外的五个测试路径：

- `tests/unit/test_contracts.py`
- `tests/e2e/test_clean_checkout.py`
- `tests/e2e/test_phase_02_self_hosting_scenario.py`
- `tests/integration/repository_fixture.py`
- `tests/integration/test_repository_fixture.py`

[分类服务](../../src/aiflow/classification_service.py)在恢复时要求 actual HEAD 与 task
subject 精确相等；目前 HEAD `166fe313...` 与 subject `f59aa254...` 不同。
[Git 验证](../../src/aiflow/git_context.py)及
[subject 同步](../../src/aiflow/task_service.py)同时累计核 base 到新 subject/HEAD 的 scope。
即使先记录 resolution，以上 Git/scope 前置仍未满足；直接 sync 也不能接纳五个测试路径。
引入 ProcessRunner、contracts/schema 解析或其他性能源码会继续扩大累计差异，
不能因它们来自独立任务就排除这些路径，更不能改旧 base 来隐藏它们。

此前七路径恢复草案未采用。把它真正采用会改变原冻结范围，需真实重新准入与适用批准，
不能作为“保持旧 scope”的历史收尾。旧 base、原 spec/context、FAILED/SPENT 和源报告
继续保留；本文不实施该范围扩展，也不重开已关闭的历史 E4 任务。

## 两个后继选项与验收

| 选项 | 来源与范围 | 完成条件 |
| --- | --- | --- |
| A：历史 F 核定与当前质量收尾，推荐 | 独立修复完成后，从真实集成的新干净基线建立新 native 目标。规格明确只核定原窗口和完成当前质量；旧报告不作为新 context 的导入输入，不新发付费获取 | 原证据逐项保留并独立核定；真实依赖、base/subject/scope 明确；新目标实际分类与准入、原生必需质量检查、适用完整 V2、新具体 action、独立 verifier/Review、finalize/批准/Gate 均完成。旧 TASK-0063 保持历史状态，不由后继成功自动标成完成 |
| B：新基线上的新真实导入验收 | 独立修复完成后建立另一个真实目标，冻结新 task/base/spec/context，再取得准确匹配的新原件；原报告只作历史参考 | 新来源单独取得授权并核来源/字节/匹配；实际零写 preflight、expected-hash record、create-only/no-op/拒绝/真实 Review 漂移逐项留证；新目标自己的原生质量、完整 V2 与独立审核/Gate 完成 |

顺序为：独立 ProcessRunner 治理准入与实施 → 独立性能测量/候选和完整预算核定 →
实际集成依赖与固定新干净基线 → 选项 A 或 B 的新目标准入和执行。
每个阶段保留自己的失败、审批及 evidence，私有 qualification 不替代生产治理或完整质量。
后继目标 base 由当时实际 CLI 创建，不能在旧 TASK-0063 上手写新 base。

两选项都保留全部适用必需检查、原预算、85% 总覆盖率、90% diff coverage、
whitespace、Ruff、format、mypy。若实际分类触发完整 V2，新 targeted mutation action
绑定该候选 subject、DU、classification、参数、有效期及 single_use；当前批准前先回读
status，只补真实 Missing。新动作若改变 streams 条件，必须在具体提案中明确核定；
原 streams 缺失不被后继方案消除。push、merge、部署及付费取得仍各自按具体动作办理。
原生 close 仅记录已经真实完成且有远端证明的 merge，不作为本地收尾开关。

## 后续机械步骤与批准边界

Agent 可继续准备真实依赖清单、后继规格/DU、独立 Review、准确 scope/base/subject、
具体 action 文件与原证据保留核定，并按准入完成已授权的常规本地阶段。需要决定的是
选项 A 或 B；实施前的原生 Missing 与具体 action 必须对应实际目标，不能由本文预授。

旧任务恢复命令仅作条件草案，当前不得直接执行：

```powershell
# 在目标自己的检出中显式绑定当前源码。
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python -m aiflow status TASK-0063
python -m aiflow scope TASK-0063
python -m aiflow gate TASK-0063

# 仅当真实 scope/Git 前置合法、处理决定与版本绑定授权均已具备。
python -m aiflow resolve TASK-0063 --condition scope_expanded `
  --evidence-ref preparation/<new-resolution-evidence>.json `
  --reason '<真实处理决定与准确版本绑定>' --actor human --authorize-downgrade
python -m aiflow classify TASK-0063 --actor codex
python -m aiflow status TASK-0063
```

推荐路径的后继创建必须在真实集成的新基线上执行；先让 CLI 分配实际身份，再补该身份
的 own task scope 和精确 DU/spec，随后 classify、freeze、独立 design Review、status。
不得预造任务 ID、classification 或人工批准。

```powershell
python -m aiflow start --objective '<所选后继的准确目标>' `
  --allow docs/operations/<successor-document>.md
python -m aiflow classify <NEW_TASK> --actor codex
python -m aiflow freeze <NEW_TASK> --actor codex
python -m aiflow review context <NEW_TASK> --stage design --output <private-context>
python -m aiflow review record <NEW_TASK> --input <independent-review> --actor <reviewer>
python -m aiflow status <NEW_TASK>
```

以上命令没有执行。本文交付只增加本承接记录，不更改旧 task/source，不声称后继准入、
新来源、动作消费、验证、Gate 或远端发布已经完成。

## 本轮后续资产核对

随后只读检查发现原 F 业务目录为空、原性能业务目录不存在，两者不再位于 Git worktree
注册清单；原 refs `166fe31` / `ef5943b` 和提交内容仍在。消失原因 UNKNOWN，不推断
具体删除者、工具或时间因果。上文 native 状态为本轮初读窗口，不能借空目录再次执行。

独立资产核查确认 F 私有 `task0063-v2-terminal-audit-001/task-tree` 的全部 75 文件、
15 目录、1,695,658 字节匹配 sealed manifest；原 evidence
`4c9f45061e9e38880923970ad676042f8c59adcdc706efa97872ddbcec87b6e9`、mutation
`3d04806e5418fd7ad986c97569adcae4381ac9919ba3e86053aa40f76f63523e`、报告及 envelope
仍有原字节。私有 snapshot 截止 event 24 / FAILED，Git 分支保留 event 25 / BLOCKED；
恢复时不能用旧 snapshot 覆盖最新 task/events。

TASK-0064 的两份 raw JSONL 仅在内存解码，组合全部 61 个 native 文件并匹配 sealed
manifest；18 个 runtime 引用、6 个终态审计及6个诊断引用也匹配。原 evidence
`075d18f5cd317c3077431fb22183e4faf0893eae025dc0ed73e5a704432dd583` 与日志/coverage/
mutation 原字节可恢复。原 DEVNULL detector streams 仍不可恢复，FAILED/SPENT 不变。

唯一新增私有清单为 `${RUNTIME_ROOT}/harness-model-backlog-20261004-001/asset-inventory-001.json`，
54,438 字节，raw SHA256
`9f24f3b97cdf57f4f0066ca8285ad99ba106e5e18eb3de177bbcc4785ee49afc`。本次没有恢复或
新建旧工作区、执行测试、改写原件。后继恢复须选择真实 workspace/ref、核目的地冲突、
精确写回缺失原件并重核 hashes/事件前缀；venv、ignored 缓存、Git admin、ACL/模式的
恢复能力超出该清单，仍未知。资产核查不代替后继验收。
