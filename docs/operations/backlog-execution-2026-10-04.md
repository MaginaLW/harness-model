# 当前待办执行：2026-10-04

所有者本次要求读取待办、设立持续目标并完成任务，授权必要的常规本地工作。持续目标已经
设立；本文件记录实际执行顺序、写入归属和完成条件。来源为
[当前七项待办](follow-up-backlog-2026-09-22.md#2026-10-04-收尾核定与下次待办)，
不将历史收尾窗口的“不启动”描述套用为本轮禁止准备。

本轮初读核定：主检出为 `f9deb7b`，分支 `codex/e4-followup-status`；三个用户未跟踪计划
保留。TASK-0064 在自己的工作区仍为 FAILED / REVIEW / V2，Missing
`retry_reason_or_escalation`；TASK-0063 仍为 BLOCKED / REVIEW / V2，Missing
`block_resolution`。两者 classification fresh、approvals current、evidence stale。
TASK-0064 未跟踪的原生 `evidence.json` 保留，不移动、不入库；原失败及 SPENT action 不改写。

## 执行顺序与完成条件

| 项目 | 本轮工作及完成条件 | 当前状态 |
| --- | --- | --- |
| Windows 超时处理 | 以封存候选形成精确生产 scope、支持矩阵、错误/资源语义和安全基线；另建治理 Task，真实 Design Review、Missing 所需决定后实施并完整验证 | 安全基线已提交，TASK-0065 已获真实 spec批准并 begin，实施中 |
| 完整测试预算 / TASK-0064 | 以原 run 和耗时原件定位累计成本；性能变更单独准入，实际确定候选依赖后合法承接或恢复；全部 14 检查、原预算、85%/90% 保持 | 001未测；002已完成、收益不足不采用；caller分区准备中 |
| F / TASK-0063 | 区分原历史窗口的已执行导入与原生收尾；确定真实恢复 scope 和依赖，按 native Missing 推进；新 context 如需新真实来源则独立取得 | BLOCKED，恢复方案核查中 |
| 外仓双通道 / 实际应用 | 只读刷新准确 SHA、完整 CI 和 runner；实际 POSIX 恢复或 Apply/部署须先有精确目标与独立准入 | Windows success，POSIX queued/0 steps；Linux 停用约定已定位 |
| I1 / I2 | 从实际使用缺口选择生命周期或可信目标；按幂等、权限、完整等价验证及可执行恢复条件准入 | I1 隔离冷启动具体草案已备、未批准/执行；I2 新目标未选 |
| E5 / I5 / Phase 3 / Phase 4 | 分别形成最小需求和样本/隐私/度量/真实 V3 边界材料；按独立进入门选择方向，缺失不补造 | 条件与提案核查中，实施未启动 |
| 远端发布 | 核对累计候选及本机内容，选择排除配置 `52474d9` 的干净基线；审核和准确 required CI 后按具体动作授权发布 | 发布清单核查中，未写远端 |

## 并行与串行

第一阶段启用 **6 名 sub-agent**，分别只读研究 Windows 设计、安全测试预算、F 恢复、
外仓实时证据、后续阶段进入门和累计发布清单。各 agent 输出调查结果，无共享文件写入。
主 agent 独占本文件和权威入口，核 native 状态并整合。

第二阶段使用 **2 名新增 sub-agent**，分别独立审查安全基线和准备文档；Windows 作者
独占新区唯一测试文件，其余文档作者各自独占一个新文件。schema 测量准备复用原预算
研究 agent，实际执行必须等待脚本独立核对。安全 tests/docs 与治理源码/账本分开。
每个治理 Task 的写入者唯一，禁止并发修改同一文件或版本绑定。

所有者批准规格后的实施阶段并行 **5 名 sub-agent**：一个独占两份生产源码、一个
独占三份安全测试、一个准备独立真实 Windows qualification、一个准备累计成本
offline caller 分区、一个准备非作者审查矩阵。后两者与实施无共享写入，资格产物
只在树外受控 runtime。主 agent 独占原生任务机械状态、主文档、整合和阶段提交。
源码/测试接口先对齐；固定候选 → 纯 fake/静态检查 → 独立技术审查 → 实际资格 →
新单次 action 与完整 V2 → 正式 Review/finalize/code/Gate 串行，不以准备矩阵替代审核。

设计整合 → 安全基线 → 新治理准入 → Design Review → 必需规格决定 → begin → 源码实现
→ subject sync → 具体单次 action → 完整原生验证 → Implementation Review/finalize/code
决定/Gate 串行。正式完整验证期间冻结源码与 refs；不能将局部通过写成整体通过。
F 准入、真实匹配来源、preflight、record、原生收尾也串行。

E5/I5 准备和外仓只读核查可与本地设计并行；后继实施只在进入门满足后开展。最终发布的
候选、审核、准确 CI、protected merge 与独立远端证明串行，不复用 PR #44 旧批准或 CI。

## 授权记录与保留

本次授权用于完成待办所需的常规本地准备、任务机械步骤、可恢复修复、检查和本地提交，
不改变运行时权限设置。项目规定的真实 spec/code 决定以及删除、push、merge、部署、
凭据导出、付费调用仍按具体材料和类型分别绑定；技术审核不替代人类风险决定。
请求决定前完成可审查材料并运行 native status，只请求实际缺项。

既有记录与日志追加式保留；不把旧失败、取消报告、未执行 POSIX、未选择需求或未来阶段
标为完成。实现和验收结果在发生后追加到本文件及相应原生任务，持续目标保持 active。

## 本轮已经完成的准备

- 安全基线已在独立干净工作区提交 `d4f72ac`，作者检查 20 passed / 18.52 秒，独立
  检查 20 passed / 1.40 秒；Ruff、format、whitespace 均通过。唯一新增测试模块，
  原生产源码与原测试未改，无 skip。所有 launch/timeout cleanup 均 fake，无 OS 资格结论。
- [Windows 生产设计](windows-production-design-2026-10-04.md)明确两个原候选资源保留
  缺口；TASK-0065 已在真实 base `ab07bcd` 准入为 REVIEW/V2。首轮独立 Review 的
  三项 finding 原样保留，修订经 spec_changed 升级/resolve/classify/freeze；新规格采用
  公共 Win32 backend、12 公共字段和 8 个原子 active+retained 槽位，不以 patch/build
  或未测缩小支持。新 context 独立 APPROVE 已原生记录，准备提交 `1d4731c`；
  所有者明确回复“批准”，native approve/begin 已完成，提交 `01949da`，状态
  IMPLEMENTING / REVIEW / V2、approvals current，Missing `implementation_result`。
- [F 后继决定](f-successor-decision-2026-10-04.md)核定原真实导入已发生，但当前五个
  测试路径越界且 HEAD 不等于 subject，不能直接 resolve 后吸收新源码。
- [外仓现场证据](external-follow-up-evidence-2026-10-04.md)确认 dotfiles 新 SHA 完整
  CI 成功；r3s 新 SHA 的 Windows 已 success、POSIX queued/0 steps。Linux runner
  离线符合既有主动停用约定，受控恢复接单的实际材料仍在核查。
- [后续阶段合同提案](phase-entry-proposals-2026-10-04.md)已形成，阈值/资产/保留期等
  未冻结；[干净发布包](publication-package-2026-10-04.md)静态列明历史 32 路径及排除524。
- [预算决策](verification-budget-decision-2026-10-04.md)保留 schema/deepcopy 候选
  NO_GO；新脚本两名 reviewer 静态 PASS，唯一启动因绑定 workspace 不可用失败，
  未生成 claim/result/guard，速度 UNKNOWN，无换解释器或重试。原性能业务目录已
  不存在，F 业务目录为空，原 refs 仍在；消失原因 UNKNOWN。独立资产清单确认 F
  75 文件与 TASK-0064 的 61 native 文件及审计原件均匹配；原 DEVNULL streams 不可恢复。
- 新绑定 002 唯一实测完成、独立终态复核确认24对照/4隔离/106+6+1200调用，26输入
  producer guard相等。局部paired收益不足，不采用两种表示；cold elapsed字段覆盖
  问题原样保留，既非完整预算PASS也不修旧失败。下一证据为已有raw profile caller分区。
- I1原 guest已形成具体隔离冷启动草案，新增`restrict=on`只供BOOT身份核查、保留
  服务21/22状态；冷备、image检查、实际隔离及有效新action尚未执行/批准。

以上是具体准备及安全基线的完成，七项待办的生产、原生验收和发布仍按前述条件推进。
