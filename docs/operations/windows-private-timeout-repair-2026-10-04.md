# Windows 私有超时修复候选：2026-10-04

本轮显式私有修复授权下，一次封存候选 qualification 实际 **9 passed / 10.37 秒 / rc 0**。
它完成的是私有候选执行，不是生产实现、原生 V2、旧 Task 恢复或 action 消费。独立终态审计
已封存，结论为 `CONFIRMED_PRIVATE_QUALIFICATION_ONLY`，无数据阻断；确认范围只属于本次
私有 qualification，非 native 验收或生产批准。原 native FAILED/SPENT 和旧失败根因 UNKNOWN 保持。

## 实际候选与调用范围

候选使用 fresh owned Win32 Job，CreateProcess 时 suspended，assign 后单次 resume。
通过 per-instance FunctionType 复用已绑定 CPython 的原 code/defaults/closure，并在私有
globals 中使用 `_winapi` 代理；不修改共享 Popen、原函数/code 或全局 `_winapi`。
实际候选不设置 kill-on-close，正常完成时释放 owned handles，保留合法 live child 的自然完成。
早期设计文字不是当前机制的替代依据；以封存候选、bundle 和实际结果为准。

本次只覆盖 CPython 3.13.15 的已绑定 Windows `_execute_child` / 九个 CreateProcess 位置参数
协议。受控调用仅把 argv 作为 Popen 位置参数，其余参数按固定关键字提供；泛用 Popen 的
其他位置参数形式未取得安全资格。单次、隔离调用的结果不证明一般并发兼容或其他解释器版本。

原测试源码、collected 函数及 1 秒 timeout、5 秒总 cleanup、2/10/3 秒测试时序不变。
qualification 在自己的隔离 Python 进程中临时把测试 `run_execution` 绑定到私有 candidate，
结束后恢复；不修改生产文件。child 原件中以下字段为 true：
`collection_binding_preserved_function`、`original_function_preserved`、
`original_run_execution_binding_restored`、`original_test_bytes_unchanged`、
`public_result_fields_unchanged`、`public_run_execution_signature_unchanged`、`hooks_restored`。
这只说明本次指定绑定与公共字段检查通过，不把私有机制包装成已部署的生产修复。

## 一次 qualification 的实际结果

| 案例 | 证据类型 | 实际结论与边界 |
|---|---|---|
| 原 timeout 测试 | 真实 Windows | 原断言通过；自有 active 0、parent signaled、drain/threads complete、handles closed |
| parent 先退出、child 保留继承 pipe 的 timeout | 真实 Windows | RUNNER_TIMEOUT 保持；自有 active 0、parent signaled、drain/threads complete、handles closed |
| normal zero / nonzero | 两项真实 Windows | returncode 0 为 passed；returncode 3 为 failed/VERIFICATION_COMMAND_FAILED，保持原结果语义 |
| normal live child | 真实 Windows | release accounting active 2，后续 child 自然完成，未请求 kill；不把 accounting 2 当成两条独立活进程证明 |
| assignment / resume 故障 | 两项 safe mock | 检查控制流、错误与模拟 cleanup；没有真实 native 故障或 OS 清理证明 |
| terminate / drain 故障 | 两项 safe mock | errors、cleanup false、retained handles/未验证状态保持；PASS 仅表示预期失败路径断言成立 |

pytest 的五项真实案例加四项 mock 均通过，原始 stdout 为 9 passed in 10.37s。outer controller
实际 11.128385 秒，其 fresh own Job active 0、parent reaped、owned handles closed，cleanup
CONFIRMED、supervisor pass，无额外 survivor cleanup，也没有自动重跑。outer 的完整 raw capture
不替代 inner drain 失败案例缺失或 UNKNOWN 的输出/清理证据。

脚本指定保护集合为 396 个 entry：333 file、61 directory、2 absent；before/after 实际文件
字节、目录/absent 状态与身份一致，原 raw-before cache 已保存。
证明范围以 guard 的精确清单为准；manifest 的 `skipped_cache_entries` 实际列出 6 个
`__pycache__` 目录。这些目录、整个 main 业务树和 whole host temp 没有完整字节证明，不能把
这些未采集范围写为 unchanged PASS；其他未列的 Git admin/config/objects/reflogs 和路径也在
保护清单之外。

## 原件定位与入库边界

私有目录以 basename `harness-model-private-repair-20261004-001` 定位，以下为该目录相对引用。
run 相对目录为 `harness/run-8e27688a33d945a69a57511711a84ba6`；表中 run 文件位于此目录。

| 相对引用 | 字节 | SHA256 |
|---|---:|---|
| `candidate/windows_owned_job.py` | 25735 | `02e81bbf3878fb1ed581bf7ca14eb560a97bef4f57b514b462ea233ec211d2ef` |
| `candidate/process_runner_private.py` | 12799 | `43456426d0083e875c0db41e0eafbab29efa7023177f7e5aac6e043e9e07903b` |
| `harness/qualification-bundle-001.json` | 3933 | `a17bc5c1900907f2f0138f419cb3bff80dfd1ed284ebb201d71eab26497c95f1` |
| run `process-result.json` | 3148 | `a680057f2ac691fda9f0d5884f4a63acece405408c4abc1b0b70753b29cddabd` |
| run `child-summary.json` | 37649 | `b1955d1ccfbc557304676b1a3e0da03f28519bcd9797aa37eca8e9df8f13f0f6` |
| run `raw-artifact-manifest.json` | 1990 | `d2fc7c18d51fc041ebeff9fa24876a3e970a429fb8d15d8d82c5dfe16a5a4419` |
| run `protected-byte-comparison.json` | 266 | `de2cead406b958c48a1da8d9824bb90461e67b2e8fdeb16e44d0603182ca22c8` |
| run `protected-before.raw.jsonl` | 6021754 | `bef2df6e4f94ac4c72b9225762d1e21a25cbb7aaaff42020345970d4bc2e4a2c` |
| `ownaudit/import-acceptance-terminal-audit-001.json` | 23171 | `89a3ba3daf6b151f76372ed8d363c582c3fee829242663e86b92f169017fc8a9` |

raw manifest 的自身 digest 不包含在它自己的 files 列表中；本表为独立 raw-byte hash 引用。
bundle 的 AUTHOR_PREPARATION 标志保留封存时点，不改写为新的执行或批准记录；实际执行以
不可变 run 原件为准。私有 candidate、receipt、bundle、raw JSON/streams 含本机状态和路径，
不直接入库、不改原字节；本页只提供可移植定位和边界，不替代原件。

独立 terminal audit 已重算候选/bundle/runtime、11 项 raw manifest 引用、333 个原文件、目录
集合及 396 个 entry 身份，确认单次封存执行和恢复边界。其 `CONFIRMED_PRIVATE_QUALIFICATION_ONLY`
不创建正式 native Review、event 或 approval，也不消除下一节限制。

## 尚未取得的资格

- 不设置 kill-on-close，且 CreateProcess→assign 不是 crash-atomic；外部解释器崩溃或被终止
  时可能留下 orphan。本轮没有测得这种故障的原子保护。
- 只证明本次受控关联 Job/进程；不能覆盖逃逸、未关联、其他创建通道或所有系统进程，不是
  security sandbox，也不代表一般 nested-job/并发/跨版本兼容性已完成。
- 故障 mock 不能替代 native assignment/resume/terminate/drain 的真实失败行为资格；retained
  handles 与未知状态不是成功清理。公共结果字段保持不自动证明所有新增错误路径的产品契约。
- 单次私有 PASS 不复原旧 coverage 失败缺失的 taskkill telemetry，不证明旧失败根因已解决，
  也不证明 regression/integration 的完整预算检查通过。

## 后续生产治理提纲

当前没有新 Task、生产源码改动、旧 Task 恢复、V2 retry 或新 action；本轮没有重试旧 blocked
proposal。下一依赖为具体生产治理设计准备（尚未启动），用已封存候选和独立私有审计形成
可审阅提案；现有资格不代表生产采纳。

1. 从明确选择的干净基线建立工作区；能独立验证的测试安全改动先按维护例外单独提交，
   不用 skip 或降低断言制造 baseline-safe。若测试依赖未来实现，先解决真实拆分和基线设计。
2. 新治理 Task 的 scope 逐项列出 `src/aiflow/process_runner.py`、最终采用的 helper 精确路径
   和自身账本，不能用旧 TASK-0064 scope 或宽泛 `src/aiflow/**` 代替。helper 生产路径尚未冻结。
3. 按实际 DU 风险与 action 需求完成 classify/freeze、独立 Design Review；先看 status 的 Missing，
   取得真实规格决定后才能 begin。原 approval、私有候选授权和技术审查不能跨 Task 复用。
4. 正式实现后的实际 subject 用 native sync 绑定；正式完整 V2 仍保留全部 14 项、原预算、
   85%/90%，为该候选另备具体单次 action 并获得真实批准，由独立 verifier 执行与收尾。

qualification guard 窗口观察到 primary HEAD `1ff6e964f7f0944176c420ca55a57b885272f325`、
performance worktree HEAD `ef5943b29514ad1d13121023610bf4c2c4dcb408`；这是本次 guard 窗口的
版本记录，GitContext source c7 与 S507 保持。
TASK-0064 为 FAILED / REVIEW / V2，Missing `retry_reason_or_escalation`，action SPENT；
TASK-0063 为 BLOCKED，旧 paid source/action 不可复用。没有新付费、push、merge 或部署权限。
旧原生失败和新私有结果分别见[当前维护状态](maintenance-status.md)及[原件回收记录](zcode-report-recovery-2026-10-03.md)。
