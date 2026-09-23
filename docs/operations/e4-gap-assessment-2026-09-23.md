# E4 进入前缺口核查：2026-09-23

## 本轮结论与范围

已完成下一步的真实案例读回、表示边界复现和后续范围筛选。当前证据仍不足以
选定 E4.1 内核修改：E3 的 F1/F2 文档修复与独立复核已完成，没有观察到该案例因
导入、映射、重放或恢复接口不足而未能交接。缺少专用导入命令本身不构成实施需要。
本轮不创建空的 E4 task，不修改 Schema、Policy、CLI 或旧任务记录。

核查本仓基线为 `18cd6b8eef79a3e6dffcc3eb5431bdcaf0e6315d`；真实 E3 对象为
`ai-agent-dotfiles` 的 `51044a55fc0dd8991e2ac25dad36fb1369a9027b`，
修复前版本为 `8f84eececf71f111a28c953f07ac2b1d490ac3fe`。两仓上一轮发布已经
记录在 [TASK-0053 回执](../../.ai/tasks/TASK-0053/publication-closeout-001.md)；
本次纯文档诊断与树外离线检查另计，不复用旧动作批准执行新推送或外仓修改。

## 实际证据与离线复现

固定版本的两份目标文档 Git blob 摘要仍分别为
`e4963cfd00bef5e7a6a0ae58999ca1873a858d5e8abfe85af04e2a593af2ddd5`、
`73031ca5566143195f5b98f9c699fbd68b557b5e1bf0e4c2ca879ddcde4dc530`。
ZCode 技术报告原件 SHA256 仍为
`80e9ebd7de1891a214075741a88abd134518195ceee6edcfd927855ac6e77ecd`。
报告与请求可沿 F1/F2 读回原问题、修复前后版本、检查输入、已验证及未审范围；
本轮没有重启 ZCode 或把旧报告当作新的独立产品执行。

已有 E3 移交包用已知 SHA256 `b1d83b67b862ef7bf22ab67032f0d46d94b25d31b92beedbc308fb2a54bd6c52`
重新校验，133 文件、4,923,046 原件字节全部匹配。工具仍明确返回
`source_authenticated: false`、`governance_effect: none`；字节一致性不认证身份或批准。
原始报告、旧 ZIP、运行原件均未重写。

本轮运行 `python -m pytest tests/unit/test_review_records.py tests/integration/test_review_command.py -q`，
**19 passed**。这覆盖既有结构化上下文、重放、事件恢复、resolution 追加及旧 evidence
拒绝等边界；测试使用隔离 fixture，不向真实任务登记新 Review，也不是新 E3 案例。
本轮未重跑全量测试、覆盖率或完整 Gate，不把这 19 项称作发布验收。

使用[现有 record 模板](../../.ai/templates/review-record.json)在内存中执行六个 Schema
探针，未调用记录服务或写账本，结果如下：

| 输入 | 实际结果 | 能说明的范围 |
| --- | --- | --- |
| 合法 `RF-001/open` fixture，以 summary/evidence_refs 引用原报告及 F1 | 接受 | 现有自由文本可保留引用；不提供类型化来源认证 |
| 顶层加入 `source` | 拒绝 unknown property | 不接受未经定义的来源字段 |
| 顶层加入 `fix_attempt` | 拒绝 unknown property | 没有正式 fix-attempt 契约 |
| `finding_id` 改为外部 `F1` | 拒绝 pattern | 外部问题编号不能直接冒充 RF 编号 |
| `status` 改为 `verified` | 拒绝 enum | 外部复核结论与 open/resolved 含义不同 |
| 严重度改为 `P1` | 拒绝 enum | 不自动猜测外部优先级映射 |

五个拒绝均符合现行契约，不能据此报告发现了五个缺陷。对照输入只是测试 fixture，
没有将真实 F1 的严重度改成 low、产生新的 RF 记录或把文本引用升级成可信 provenance。

## 现有能力与 E4 选择

[review-record Schema](../../.ai/schemas/review-record.schema.json)保留现有字段和拒绝未知字段；
[review_service](../../src/aiflow/review_service.py)已提供当前上下文绑定、不可变重放、
Finding resolution 追加及最新审核判定。[现行 CLI](../../src/aiflow/cli.py)的
`review record --input` 接收现行结构化 JSON，并非任意外部报告导入器。
[轻量交接约定](../../examples/adoption/review-fix-verify-handoff.md)允许未接引擎的原任务
保留自己的 F1/F2 与报告引用，本次自然案例已经沿该路径完成。

尚未发现真实消费者因为来源引用丢失、同一报告重复处置、错误仓库/版本关联、
重试或接手失败而需要新增内核字段。缺少机器可读专用字段是已知扩展边界；模型身份
unknown、私有鉴权限制以及已修复的本地选材路径问题也不能替代这项需求证据。

再次进入 [E4 准入](../superpowers/specs/2026-09-13-cross-agent-review-fix-loop.md#7-e2-退出与-e3e4-分批推进)
时，先确定一个实际消费动作，保留其固定 repo/head/input、预期和实际失败，说明现有
引用或记录机制为何不足，再选择最小字段、兼容与退出条件。必要时先做 E4.1 契约，
不同时拉入全部 E4.2–E4.4；治理代码独立 task，文档/样例与之分开。无须为此制造
新的 E3 样本、虚构耗时收益或接入 provider。

## 新完成的 dotfiles CI：独立后续事项

本轮实时读取 [Validate run 35733693990](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/35733693990)
的最终 run/jobs/check-runs 及原始日志。它对应 `51044a55`、attempt 1、push，
在 2026-09-22T14:31:57Z 已更新为 completed/failure；4 个 job/check 均匹配
GitHub Actions app 15368 和该 head。本轮是读取已经结束的运行，没有重跑 CI。

| 作业 | 最终状态 | 原日志套件计数 |
| --- | --- | --- |
| repository gates / `106765389013` | success | 元数据确认，不混入套件计数 |
| shard 1 / `106765388999` | success | 7 discovered / 7 passed / 0 failed / 0 timed-out |
| shard 2 / `106765389119` | failure | 8 discovered / 7 passed / 1 failed / 0 timed-out |
| shard 3 / `106765388805` | failure | 27 discovered / 26 passed / 1 failed / 0 timed-out |

合计 **42 discovered / 40 passed / 2 failed / 0 suite timed-out**。两项实际失败为：

1. `root-claims-registry.tests.ps1`：`Invoke-TestRegistryScriptStreams` 的
   `WaitForExit(15000)` 未成立，在第 7301 行尝试终止子进程并抛错；原始 job 日志
   第 1519–1524 行点名 `recover-canonical-transaction.ps1`。最后 PASS 对应第 7375 行，
   后续第 7378 行释放持有锁、第 7380–7386 行执行 `routeContentionReleased` 的
   `recover -Action abandon -Apply -PlanPath`。将失败归到该调用是固定源码顺序与日志
   的推断，非栈直接打印；第 7390 行的成功断言尚未到达。子进程尚未返回 helper 的
   stdout/stderr。不能据此认定为负载抖动、锁泄漏或直接放宽期限；它不是 suite timeout。
2. `sync.tests.ps1`：异常第 59 行是通用 Assert，具体调用在第 203 行、断言在第 211 行。
   released-policy 下的无 internal capability `DryRun + PlanPath`，要求
   `$result.Code -ne 0`，该谓词未成立；根据固定条件推断 Code 为 0，不能把这个推断
   写成已捕获完整子进程回执。第 216 行的无 plan 文件断言没有执行，文件是否生成未知。
   原始 job 日志第 2952–2956 行保留失败；底层原因仍需定向复现。

日志内其他预期负例提示不能冒充上述失败；本次也不重新解释历史 run `34851206631`。
这两项 CI 失败没有证明 E3 文档归因错误或 E4 桥接缺陷。后续应在目标项目固定候选中
分别复现子进程期限及 dry-run 断言，保留实际 exit/stdout/stderr 与清理结果，再决定
最小修复；本轮没有接管外仓写入、修改测试阈值或宣称修复完成。

## 证据保管与本轮并发

树外证据集为 `E4-GAP-REVIEW-20260923`。正式文档只保留版本、可移交摘要及必要引用；
私有原始日志、机器路径、会话原文和临时测试输出不进入 Git。主要回执 SHA256：

- `offline-boundary-001/receipt.json`：`1ccdd83cd08cdcbe86decca6ba62e5e4b883f45eb171ffa5eb8fe5ff5348528e`。
- `schema-boundary-001/receipt.json`：`d403e7eb7e943fefd6c653613f89145ce0f5f932f0afce9b9b31e3c9c7c0feae`。
- `dotfiles-ci-final-001/final-receipt-001.json`：`3f7f0dfaf78f51d547c498571e27a652952639e96c72b79ebab86ec53de10f70`。
- `dotfiles-ci-final-001/source-context-001.json`：`ecd1f92e55c775fc6df4ebfb1c1c14e8bd631e6b0d59678756b2243130f08e20`。

本阶段两名 sub-agent 分别只读核对 E3/接口边界与固定 CI 原件；协调者同时运行离线
核查，随后串行整理本文、检查新增链接/差异和提交。全部旧任务、原始证据与三个
用户草稿保留；本轮没有外部动作、真实 provider 调用或后续阶段验收结论。
