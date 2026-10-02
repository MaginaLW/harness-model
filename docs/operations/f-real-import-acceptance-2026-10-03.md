# F：真实 design 报告导入验收规格

## 目标与范围

在新的 native 目标上，验证既有 external-review 导入器消费准确匹配的真实 ZCode design
审查的来源链，保存实际零写/追加/no-op/拒绝证据并按原生流程收尾。
允许交付为本文件和新目标自己的治理/审计记录；生产代码、Schema、Policy、CI、外仓不变。
规格本身是实际受审对象，不重开 E4 任务或借 design 绕过 implementation 证据要求。

主 agent 独占目标、导入和本文件；独立 reviewer 只读审核规格与来源。新目标用隔离检出，
task/branch/repository/base/context 由实际 CLI 分配，分类、验证等级及批准由 CLI 判定。
主检出用户草稿不进入目标，私有原件和日志置于任务树外，不提交机器路径或原始聊天。

## 串行协议

1. start、明确实际 decision unit、classify、freeze、生成 design context，独立审核规格；
   status 只补 Missing。冻结后不改 spec、Policy 或 classification 来凑匹配。
2. 固定 task/repository/stage/base/context、规格摘要及范围；design source/target/context
   均无 subject。内部 Git 仍核 base→subject→HEAD 及自身治理范围。合法状态仅
   WAITING_FOR_SPEC_REVIEW/READY_TO_IMPLEMENT。
3. 单独批准新付费调用后，才将固定上下文交给一次新 ZCode 只读审查；只审冻结规格和
   相关现有接口，输出来源/受审版本/内容及遗漏，不执行命令、写文件、调用其他 worker/API
   或自动重试，不替代先前取消报告。
4. 回收未改最终报告及实际来源；说明原字节是持久化文本提取还是传输原件，不能认证的
   身份保持 UNKNOWN。独立 envelope 人工核 source repository/stage/base 与 target、
   target 与当前 context、原报告哈希；用实际 UUID，需 locator mapping 时逐字独立核定。
5. 实际零写 preflight，首次创建只用 ready，重复验收可对 already_recorded 携新的
   expected-preflight-sha256 record 核 no_op；重读全部原件、目标及历史，不复用旧摘要、不覆盖。
6. 完成下表，按实际 route 完成原生批准、实施、完整验证、独立 Review 和 Gate。
   导入不产生正式 Review/Finding/批准或改变 Gate。真实合并/close 另依发布授权和远端证明。

具体新提示词在目标冻结后保存为私有材料；一次初始发送不承诺 inference 次数或费用封顶。
不改变账户、模型、权限、订阅或隐私设置。

## 验收与停止条件

| 检查 | 实际预期 |
| --- | --- |
| 首次 preflight | ready、摘要及当前目标/context；task 树前后路径/字节不变 |
| expected-hash record | create-only 新增一份 import 记录（含 envelope/可选 mapping 及原件摘要）；不复制原始 report/envelope 输入，仅写新目标 external-reviews |
| 相同完整输入重复 | already_recorded/no-op，原记录及 task 树字节不变 |
| source/version 冲突 | 同 source_key 和 report_version、不同输入的独立 envelope 拒绝；原报告不改、不覆盖，不把合法新 series 当冲突 |
| 错误目标/来源/摘要 | preflight/record 零写拒绝，原报告及真实目标不改 |
| 预检后目标漂移 | 首次 ready 后，另一独立 reviewer 按当前 design context 完成真实设计审核，经原生 review record 追加 Review/events；context 与合法状态保持，旧 token record 零写拒绝；重新 preflight 后才首次成功 record |
| 中断或 cleanup_required | 先核实际状态及本次临时材料，不盲删锁、不重试消费或删除历史 |
| 完整质量及原生收尾 | 原有完整测试/85% coverage/90% diff/whitespace/Ruff/format/mypy，Review/批准/Gate 独立 |

漂移所用真实设计审核及顺序在执行前独立核定；原件取得后先预检，再记录该审核，
旧 token 拒绝，再新预检/消费。事件内容确实参与 token，不用任意文件追加模拟。
不能安全执行的项保持未验证。
恢复采用停止消费、保留记录和追加更正，不删失败或重写导入；需要源码修复则另开治理 task。
历史 synthetic 不作为本轮实际验收。当前[准备核定](zcode-report-recovery-2026-10-03.md)已完成，
native 准入及正式冻结状态以后续 CLI 回读为准；匹配真实原件未取得，实际导入未执行。
