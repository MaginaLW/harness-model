# Task Specification

## 目标

将任务 02 的可信私有 Linux 接入、隔离运行、Windows/Linux 串行窗口及当次证据纳入
独立治理记录；按原必要检查验证真实行为，保持公开托管 CI、维护模式与原 Gate。
I1/I3 通用工具已在之前的独立提交固定，本 task 不把它们重新归入治理实现范围。

## 范围

本仓交付范围为 `docs/implementation/task02-runtime-integration.md` 及本任务生成的账本。
树外材料只使用明确归属本任务的 guest、受限盘、源码快照、镜像、配置及运行证据；
目标仓的 workflow 改造遵循该仓完整 Strict、manifest 与独立审查规则，使用独立候选
工作区，保留其他写者的修改。实际目标和机器路径只保存在树外私有配置。

所有者已授权完成任务 02。该任务保留独立 spec/code/action 记录；计划与安装产物
不能替代真实准入或自动授权未核定的命令。Linux runner 注册、服务窗口和 CI 触发前
重新核对确定实例、当前 busy/Worker、仓库与 source。没有实时交接证据时仅推进候选。

## 非目标

不操作 R3S/VPS 生产设备，不导出个人凭据，不改变 Billing、费用 fallback 或仓库可见性。
不迁移公开或不可信 PR，不推广第二个仓库，不自动启动模型或 Agent，不实现 I5 调度器。
不替代既有 Phase 3/4 准入，不改变现有 Schema、Policy、质量阈值或分支保护。

## 验收条件

1. 固定提交与 manifest/源码字节一致；发现其他写者或版本漂移时保存历史并重新核定。
2. 专用 guest 真实运行 Linux；运行账号无 sudo/管理员组，必要依赖版本与原检查一致。
3. 运行前核验实际 namespace、UID、进程、挂载、cgroup、默认 seccomp、无附加 hooks
   与可信启动屏障；未知或冲突时 fixture 不启动。容器根只读、写入与日志具有确定容量。
4. root fixture 的 dash 与 BusyBox ash 路径在原 600 秒预算内实际执行，真实退出 0 且
   精确四用例/五行结果通过；超时、SKIP、输出溢出、进程残留或回收未知均失败。
5. 保留每次失败、修复、独立复核和执行回执；source 类别或自报 PASS 不产生 Gate。
6. 接单实例受控串行；GitHub API 指向实际 runner、job、attempt、完整步骤与 checkout。
   smoke、完整 pilot、main 采用与采用后验证分别记录，缺少任一项不能混称完成。
7. 真实服务恢复和执行宿主重启后业务需独立回执；开机自动启动配置不充当此项证明。
8. 本仓按当前 85% 总覆盖率、90% diff coverage、完整测试、合同、whitespace、Ruff、
   format、mypy 验证。新工具关闭时原 CLI/证据/Gate 行为与历史完整保留。

## 禁止动作

默认禁止动作保留；执行具体外部动作前只根据当前 CLI 状态和已存在的明确授权办理其
记录，不从技术审查、Gate 或旧 task 推导权限。生产、付费、秘密导出、覆盖其他工作树、
批量删除、降低质量检查和未受控并发始终不在本任务范围。

## 错误行为

注册或进程身份未知、管理员接单、环境漂移、路径/挂载/配额不匹配、native 前序失败、
输出不完整、屏障前运行、时限失效、清理不确定、远端零步骤失败均保持非成功。
禁止把工具安装、合成用例、初始模拟控制器或历史 Windows 成功作为当前 Linux 验收。

## 回滚

回退只针对精确核验的本次对象：空闲时恢复原 Windows 服务、停止本次 Linux 实例，
恢复本次 workflow 路由差异。guest、失败日志、源快照与镜像摘要保留诊断；未知内容不
清理。托管额度不足时不保证回退后 job 能执行。中止 Linux 接入不影响旧引擎使用。


## 2026-09-21 治理收尾规格补充

本节通过 `spec_changed` 同级升级重新核定，补充原“范围”中唯一报告路径的集成
审查范围；原规格文字、base、已完成运维证据及既有提交归属保留。所有者在接入
验收与正式治理缺口报告后明确继续，沿用其项目状态/ZCode 复盘与完整执行委托。

以下八份既有文档增量纳入本次累计版本的独立集成审查，不追认其最初属于
TASK-0048 实施，不改变其原 task-free 来源，也不允许改动额外业务或治理源码：
独立审查发现的必要文档纠正可在这些精确路径内完成，并保留发现及修复复核记录。

- `README.md`
- `docs/operations/adoption.md`
- `docs/operations/feedback-loop.md`
- `docs/operations/maintenance-status.md`
- `docs/operations/zcode-retrospective-2026-09-20.md`
- `examples/adoption/project-rules.md`
- `examples/adoption/zcode-feedback-loop-prompt.md`
- `examples/adoption/zcode-pilot-prompt.md`

精确十个既有提交、当前字节摘要及原规格摘要见
[补充范围记录](closeout-amendment-001.json)。审查完整 base→subject 增量，
对历史事实保留其当时版本限定；不得将历史待验收记为当前失败，或从方法采用
推导业务/生产验收。文档中的按需反馈决定保留，普通完成不触发回灌或新外部动作。

原验收第 8 项补充明确：按当前 V2 执行固定五项 harness 治理防线 mutation，
验证必需检查集、独立 verifier、code approval、Gate 和 snapshot 防篡改。
这些 mutation 必须真实运行并取得 killed 结果，只证明本仓治理回归，不证明
Linux 隔离、服务恢复或目标业务；后者沿用各自实际原件，不能相互替代。

本次保持 REVIEW/V2、全部原质量阈值、原 base 与追加式账本。新规格必须重新
冻结、独立设计审查、办理已有委托的当前版本 spec 批准，再推进固定 subject 的
完整验证、独立实现审查和 finalize。不得借此降级、跳过门禁、重写旧批准或
启动 I5/生产/新外部操作。三个用户未跟踪计划不纳入范围，在原工作区保持不动。


### READY/begin 版本顺序补充

实际拒绝及对应源码位置见 `closeout-begin-binding-001.json`：当前 `begin` 对
spec 批准额外比较 subject，而 READY 状态不允许补录 spec 批准。此次收尾先固定
业务提交，再完成规格冻结、独立设计审查、既有委托的规格批准及 `begin`，这四步
之间不再推进 subject。进入 IMPLEMENTING 后的账本提交按正常 sync/验证绑定推进。
这是当前 CLI 行为下的执行顺序约束，不宣称 spec 新鲜度定义已经改变；不修改
Policy/CLI 或旧批准。该一致性缺陷另作后续代码问题，本任务不扩治理源码范围。
