# 主线同步后的治理交付

## 目标

在已包含 #173 接入文档的目标 main 5ad71cf845e1253a0ca821f6d68790f4cc4116c4 上，交付 35 个已审核的治理及 POSIX 受控验证文件。新候选须在其实际分支、基线和实现提交上重新取得独立审核、原生完整验证与 Gate。

## 范围

- 复用 1ed54255c1894485aad63926a953a4f83ea05182 中 TASK-0161 的 35 个业务文件，规格冻结摘要为 53ba378d3c2772e37a3ee543d49c4dea4a07f9240a7dc5639752b35c67c6ca29，仅引入本任务 task.yaml 列明的路径。核心与 CI 的 33 个文件来自 4ccd9a0f，另两项为 process_runner.py 和相邻测试。
- 上游 README.md、docs/operations/adoption.md、examples/adoption/project-rules.md 以本任务创建时 main 的版本为准。原 #174 已发布 head 9dec02ee、#172 的 Linux 失败 run 44325839473、原任务和其证据均留在原 ref。当前候选只生成自己的账本。
- 特性边界为审批来源与兼容重试、两个 Hook 的真实 Git 根/任务选择与观察绑定、基于 schema 实际内容的有界编译复用、既有共享接口及 SDK 的只读访问、required check PR 路由/收尾/失败记录与范围验证，以及只对 POSIX 系统默认绝对目录进行保序规范化和去重。继续按原位置追加 Git 程序目录，保持 Windows 相对 PATH 与严格 init 路径检查。

## 验收条件

1. 基线先登记，独立设计审核 APPROVE 后批准并 begin，再引入 35 个文件。同步 subject 后逐项比较来源/当前 subject/attestation 的 Git mode、类型与 blob；35 项均相同。上游三个文档逐文件与 5ad71cf8 对齐，PR 不夹带旧账本或其他工作。
2. 本仓正常 approve CLI、子目录 Hook、schema 及导入/SDK 消费方的既有回归保持通过。受控 POSIX 测试涵盖系统别名、默认目录顺序、Git 目录仅追加、真实严格初始化；保留受信 PATH 环境规则及 Windows 相邻回归。在实际 POSIX Python 和 Git 上运行该候选的原生 verify，不将旧版本结果或直接运行 pytest 替代正式证据。
3. PR 路由以最新目标与实际 head 判断唯一 TASK-0162 正式候选，前置贡献检查和原生 scope 均通过；收尾、保留失败、跨版本绑定与非法条件的拒绝行为由既有集成测试覆盖。merge 之前再次核实远端目标及当前经过 required check 的精确 head。
4. 新任务按实际分类执行完整 V1，保留本地 Linux 解释器/仓库版本/工具链绑定与真实日志、完整测试、85% 核心总覆盖率、90% diff coverage、Ruff、format、mypy、whitespace 证据。独立实现审核需绑定本次 subject/evidence，通过后以原生 Gate 判断。主代理按常设授权向已核实的本仓单个 codex 分支推送、开 PR，并仅在当前 required check 与分支保护允许时以 merge commit 交付。

## 禁止动作

禁止改动 #173 三份文档、旧任务、冻结范围外的治理实现、授权政策、分支保护或质量门阈值。禁止直接推 main、强推、改写已推送历史、删除数据、部署、导出凭据、真实评分、宿主与外仓接入、付费调用。公开材料仅限本任务获准的本仓内容。

## 错误行为

范围、基线或任务身份不符时停止该候选交付并保留原因。Linux 原生验证环境需要能确认实际用户态、可用项目依赖、Git 根和精确 ref；缺失时先在工作区核实与修复环境，不伪造验证结果。新的失败、过期证据、非法 task 收尾与 required check 失败均保留可追溯事实。

## 回滚

分支独立，原分支、证据、合并历史和失败原件均可回读。如需撤回使用新的受治理提交，保留原任务和版本记录。
