# 第五章：验证与证据闭环

本章把“检查执行过”变成可重放、可失效、可由 Gate 消费的版本化事实。可执行定义来自 [Policy](../../.ai/policy/verification-levels.yaml)，实现入口是 `aiflow verify`；本文只说明使用和排障，不复制检查命令表或判定规则。

## V0、V1 与运行模式

V0 适合受限、机械且低影响的变更，包含契约、范围、格式和烟雾检查。V1 在完整 V0 基础上增加单元/回归、类型和覆盖率检查。最终等级来自 classification，调用方不能通过参数降低等级。

本地 full verify 会验证当前 Git 快照、执行完整等级计划、写入 `evidence.json`，并按 route 推进到合并批准或最终审核。`--check` 只生成 provisional evidence，完成后回到实现态，不能满足 Gate。CI verify 使用 `--ci --ci-run-dir ... --output ...`，只在 runner 临时目录写日志和外部 evidence，不修复或改写仓库任务记录。

## 运行目录、日志与脱敏

每次本地运行使用 `.ai/tasks/<TASK-ID>/logs/<run-id>/`，CI 使用显式 runner 临时目录。coverage 数据库和 XML 都写入该次 run 目录；仓库根不应出现 `.coverage` 或 `coverage.xml`。

执行器不经过 Shell，超时会终止进程树。stdout、stderr、命令摘要和异常先经过统一脱敏再持久化；完整脱敏日志保留，evidence 只保存相对引用和摘要。重验原子替换当前 `evidence.json`，同时把上一份有效 evidence 归档到它原先的 run 目录，旧日志不会被覆盖。

## evidence 的权威边界

一份 evidence 至少绑定任务/决策单元、稳定仓库 ID、分支、base/subject commit、冻结规格、Policy、分类输入、验证等级、工具版本和检查结果。required 检查失败、超时、缺工具、缺结果或不可解析都会形成结构化 failed evidence；optional 未验证项会显式保留。provisional、failed 或版本不完整的 evidence 不能通过 Gate。

`reproduce_command` 是可再次执行的 argv；本地记录必要 actor，CI 记录 CI 模式和临时输出参数。复现仍会重新读取当前 Policy 和版本事实，所以旧命令不会绕过新鲜度检查。

控制台中的“测试通过”、聊天回复或审核文字都不能替代 schema-valid、当前版本绑定且结论为 passed 的 evidence 文件。

## subject、attestation 与失效

`subject_commit` 是被验证的业务快照。合法业务提交通过 final verify 同步 subject，并留下审计事件；连续同步链仍回溯到原 classification。subject 之后只包含当前任务 evidence、approval、event 等治理记录时，视为 governance-only attestation，不把治理提交吸收到业务 subject。

失效与恢复遵循统一 freshness 服务：

- subject 后出现业务或其他任务路径时，旧 evidence 和 code approval 失效；重新 final verify，REVIEW 任务随后重新 code approve。
- 当前任务治理 attestation 不改变 subject；CI 必须在最新 HEAD 生成带 attestation 的外部 evidence。
- 规格变化使冻结规格、相关批准和 evidence 失效；重新完善并冻结/批准后再验证。
- Policy 或 classification 输入变化要求升级后重新 classify，并重新取得受影响的批准与证据。若已批准任务显式把新提交纳入扩展后的任务范围，先用 `aiflow sync TASK-ID --actor ...` 审计同步 subject；该命令不会自行扩大范围。
- action approval 独立于 spec/code approval，Gate 不执行动作，也不把 action approval 当作代码批准。

本地 Gate 默认读取任务内 evidence。带 `--evidence` 时，外部 CI evidence 是本次 Gate 的权威验证事实；REVIEW 的 code approval 仍绑定批准时的任务内 evidence，二者不能相互冒充。

## Gate 与退出码

`aiflow gate TASK-ID` 输出稳定文本；`--format json` 输出不含时间戳或 checkout 绝对路径的确定性对象。`--evidence PATH` 用于 CI evidence。

- `0`：所有 Gate 条件满足。
- `2`：输入有效，但状态、版本、范围、ASK、批准或 evidence 条件未满足；输出含有序 reason codes 和恢复 argv。
- `1`：任务记录、外部 evidence 或运行环境损坏/不可解析。

Gate 严格只读，不修改任务、事件、批准、evidence 或 Git。

## 失败恢复与排障

失败后先查看当前 `evidence.json` 的 `reason_code`、`unverified_scenarios` 和相对日志引用。普通验证失败进入 `FAILED`，修复后使用 `aiflow begin TASK-ID --actor ... --reason ...` 记录重试理由，再执行 full verify。范围扩大、新权限、外部副作用或不可验证条件应先升级，不能用普通重试掩盖。

常见处理：

- `RUNNER_TIMEOUT`：定位超时日志，修复阻塞或把不可验证事实升级；不要直接提高结论。
- `VERIFICATION_TOOL_MISSING`：安装/恢复 Policy 所需工具后重验；任务会保留 failed evidence，而不是卡在 VERIFYING。
- evidence 写入失败：任务进入 FAILED，修复存储后按理由重试。
- freshness/Gate reason：已批准任务先按原因 `escalate`，记录 resolution 后重新 classify；必要时 freeze、approve、verify。旧产物保留用于审计，但不再授权。

章节回归位于 [test_verification_evidence_flow.py](../../tests/integration/test_verification_evidence_flow.py)，覆盖真实 V0/V1、失败恢复、连续 subject 同步、治理 attestation、CI evidence、版本失效、超时和缺工具。
