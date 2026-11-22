# TASK-0183 实施审核包

## 审核目标

裁决普通 CI 工作流标记在软件提交 `0aa35d273538b95eff66da74f7eb5904d7f7f8b9` 上是否符合冻结规格，核对本次私有 Ubuntu 本地 V2 快照 `f9ff7c435bc79421c08c4ebb0b3be648d4385c52a57e251c3662888eab952d6d`。决策单元为 `DU-001`。

## 背景

原 TASK-0171 的标记对齐到公开 main `fa58164d`。所有者批准一个独占槽、一次正式收集及至多一次固定变异动作，90 分钟含清理。单次动作经独立审核后以 CLI 绑定到当前软件提交，准入 head 为 `eb38906c`。[确认单](pre-v2.md) · [所有者决定](owner-decision-v2-01.md)

## 代码地图

`.github/workflows/ai-quality-gate.yml` 增加一个先于 checkout 的步骤。`tests/integration/test_github_workflow.py` 使用既有工作流测试检查步骤的位置、展示名、唯一性、空操作命令及随后检出的 PR head。

## 语义变更

标记把事件提交和工作流来源提交写入展示名，checkout 按 PR head 绑定。软件增量仅有上述两文件。去掉两行标记，工作流原始字节与基线相同。没有新增依赖、权限或配置项。

## 风险

受保护验签器要求普通工作流在受保护 base 与待验证 head 上的 blob 相同，标记改动自身会触发 `Ordinary workflow changed`。真实 GitHub run/attempt 来源需由平台记录核实。#186 的公开必需检查、后续切换、TASK-0173 和 G 另有准入条件。

## 证据

原独立验证者 `ubuntu-independent-verifier-183` 在已准入的无外网、无宿主挂载 Ubuntu 槽运行 `python -m aiflow verify TASK-0183 --actor ubuntu-independent-verifier-183`。仅一次收集，零重启，单次动作消费一次。2026-11-22 04:38:35 至 04:46:59 UTC 完成收集与监督进程清理。软件提交之后仅新增本任务的治理记录。

预结果 `83527dfd` 绑定本次运行 `run-20261122T043835858993Z`。14 项逻辑检查通过；共享 pytest 报告 4,779 项通过、77 项跳过，核心行与分支覆盖合计 17,417/19,389，即 89.83%（报表显示 90%）。diff coverage 检查通过，本次改动在核心覆盖域无可映射行。mypy 检查 51 个源码文件。固定 5 个变异全部检出，五对均为 baseline 退出 0、mutant 退出 1；变异证据规范摘要为 `f48ecb4cb7664ec959ad50ddad943fea6de8eec9600196140a84f2728a46b7f9`。原件留存在 Ubuntu 同一检出，原验证者核实 28 个原件的内容与 inode。[执行证据](evidence.json)

## 审核问题

- 版本与范围是否正确？冻结规格、分类、Policy、软件及独立验证上下文绑定同一任务及 DU。
- 是否复用了既有能力，是否有更简单的实现？新增两行步骤并扩展原测试，无新增抽象；原工作流、验签器及质量门保留各自约束。
- 证据是否覆盖声明的行为？定向标记正反例与本地全量门禁覆盖准备和本地验证，真实运行元数据、公开 CI 和 #186 合并另行验收。

## 推荐结论

APPROVE。独立审核人 `independent-marker-design-183` 已复算实施审核上下文、验证者上下文和本次快照，确认单次消费与验收结果。未关闭发现为 0。
