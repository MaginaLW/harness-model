# 后续计划执行记录：E1 核查、E2 设计与 Linux 候选准备

日期：2026-09-13。输入提交 `ca644154dd9ab9aeb14dc7c12b5b21c674132101`。
本轮按[统一后续索引](../superpowers/plans/2026-09-12-plan-closeout-and-next-steps.md)
开始推进 I1 必要准备/I2 同仓 Linux 候选，并行完成 E1 只读证据核查与 E2 文档设计。
所有者确认私有试点有另一个任务正在处理，明确要求本轮保持只读候选准备。

## 当前结果

| 工作项 | 本轮产出与准确状态 | 后续条件 |
|---|---|---|
| I0 现状读回 | 私有目标、权限、workflow、Windows runner 与历史交付引用重新核对；16 份历史证据摘要一致。核查中目标 main 已前进到 Windows 试点版本，旧“未进入 main”描述不再是当前状态 | main 生效后的真实运行和采用状态由当前持有者核定，不用历史分支成功代替 |
| I1 必要准备/I2 Linux 候选 | 完成只读主机盘点、guest/串行窗口/依赖/恢复候选，以及树外两阶段 workflow 副本和现有 manifest 哈希更新；第二阶段因必需 root fixture 会被跳过，已明确标记契约阻断 | 尚未安装 Linux、注册服务、推送或执行 CI。先由当前持有者解决隔离执行/禁止漏验的设计，再评估完整候选与授权 |
| E1a：dotfiles | 历史 Step 3 修复提交 `9a29db6` 与收尾提交 `3cd7429` 的 CI 原始结果均成功，37/37、0 failure/timeout；可以关闭此前“最终全量结果未取回”的证据诊断项 | 原本地摘要已删除，仍保留缺失；当前 HEAD 已到 `8d22a44`，另有七个业务 dirty 文件，旧 CI 不覆盖它们。后续 Step 4–5 项目记载与当前任务单独核对 |
| E1b：私有试点 | 旧两文件未提交补记已提交；Windows 试点完整 Strict 与 17/17 fixture 成功可读回，POSIX 为零步骤、未分配 runner 的平台拒绝 | GitHub 提示付款失败或 spending limit，不能进一步区分。诊断收口为外部阻断，不是双 lane PASS；新 main 运行交给当前任务持有者 |
| E2：最小 guided 设计 | 已形成[正式设计文档](../superpowers/specs/2026-09-13-cross-agent-review-fix-loop.md)，覆盖现有能力/字段/测试、文本交接、版本/来源边界、正式 review 顺序、兼容场景与 E4 分批退出条件 | 本轮只完成文档准备；实际质量门结果以本轮独立回执为准 |
| E3：真实双产品交接 | 已完成候选可用性核查；已有“独立 review”记载，但缺少可核实双产品会话、固定受审输入和逐项修复后独立复核关联 | 保持未完成。等自然任务安全收尾时前瞻记录，不补造历史或制造试验修改 |
| E4/E5、阶段三/四 | 未开始，不由本轮设计、runner 或旧 CI 自动推进 | 继续按各自进入条件和明确实施范围处理 |

E1 这里完成的是只读证据诊断；未代替外仓持有者写回其权威状态入口，也未执行外仓测试。
dotfiles 两次远端验证分别为 [修复提交 CI](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/34684968781)
与[收尾提交 CI](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/34688993959)。
两提交间仅三个文档不同。本地原始日志的哈希不替代已删除正文，当前 dirty 不归本轮处理。

## Linux 候选的关键决定

当前 Windows 主机可见硬件虚拟化，但 Hyper-V 管理组件、WSL 和可用 guest 尚未就绪；
已有 hypervisor 不等于已能运行 Linux CI。资源余量随其他任务变化，启动前必须重新核对。
候选采用独立 Ubuntu Server 24.04 LTS amd64 guest、2 vCPU/固定 4 GiB/64 GiB 虚拟磁盘，
无个人 profile、凭据或业务目录共享。系统镜像与 runner 包的实际版本/官方摘要、guest
网络隔离和恢复仍须在执行窗口验证，不宣称已具备 OS 安全沙箱或性能验收。

原 POSIX job 有 sudo 安装工具步骤，不能直接搬给低权限服务。候选将固定版本工具的
安装移到 guest 管理准备，CI 保留版本和摘要检查；完整 POSIX gate、Windows job、必要
检查、阈值和超时保持。两阶段分别是仅 Linux 冒烟、随后完整双平台试点：第一阶段仅在
专用冒烟分支排除原自动 workflow，避免冒烟同时启动旧 hosted job；第二阶段恢复原触发。
临时排除是必须审查的差异，未执行原门不能算通过，冒烟分支不能用于 main 采用。

独立审查发现一项阻断：原 POSIX fixture 有四个依赖 root 的 e2e 用例；新低权限身份会
触发 SKIP 并 exit 0，旧外层仍可能汇总 PASS。当前第二阶段草案已标记
`BLOCKED_CONTRACT_GAP` 并禁止直接应用。该缺口尚未修复；后续必须设计隔离的执行边界、
补齐编译器等实际前置，并核对四例真实通过及 SKIP/缺少 sentinel 的失败处理。不能赋予
普通 runner 通用 sudo 或删除用例来绕过。现有结构/摘要检查通过不代表覆盖语义等价。

Windows/Linux 采用人工受控串行窗口候选：确认空闲后停用 Windows 接单，再启动 Linux；
Linux 完全停止并读回后才恢复 Windows。记录原启动类型、固定 VM 资源和恢复步骤。
这依赖当前持有者监督，不是已经实现的整机互斥锁、后台调度或无人值守能力。

另一个仅手动触发的 workflow 用于观察 GitHub-hosted Windows image，候选保持其诊断
用途。因此未来即使两条自动必要 lane 均本机化，也不能把所有 workflow 描述为零 hosted。

基础依据已重读 [GitHub runner 需求](https://docs.github.com/en/actions/reference/runners/self-hosted-runners)
与 [Microsoft Hyper-V 需求](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/host-hardware-requirements)。
具体安装、权限、网络和系统重启均未执行；本轮没有待用户立即批准的系统动作。

## 证据、检查与接手

公开仓库只保存本摘要、E2 设计与入口更新。私有目标身份、真实 run/job、服务配置、本机
资源和路径、逐文件摘要及 workflow 候选保留在既有受限证据根中的
`2026-09-13-linux-preparation` 独立目录。该目录含 `README.md`、`host-inventory.json`、
`e1-readonly-audit.md`、`prior-evidence-hash-check.json`、`candidate-static-receipt.json`、
`stage1-smoke/`、`stage2-pilot/` 与独立审查/静态检查结果；公开文档不复制私有内容。
候选需根据持有者最终源版本更新，不能覆盖后来提交；正式应用时还须补其运维说明并
通过目标原有 Strict、独立审查和真实 Linux CI。静态结构检查不等于这些验收完成。

本仓仍为维护模式。只修改 docs，不改治理代码、Schema、Policy、workflow、忽略规则或
账本。账本重新读取为 46 tasks：38 MERGED / 7 BLOCKED / 1 APPROVED_FOR_MERGE；
TASK-0028 仍 Missing=reverification，按已有选项 C 保留。七条历史 BLOCKED 不自动重启。
本轮三个既有未跟踪原稿原样保留，不暂存、不代为发布。

本仓交付检查沿用完整质量门：锁文件/环境、契约、全量 pytest、85% 总覆盖率、90% diff
coverage、whitespace、Ruff、format、mypy；固定候选先本地提交再验。无可执行差异按
工具实报记录，Windows skip 单列，不替代 Linux CI。检查日志、源版本、结果和候选审查
保存树外回执；本文中的验收要求不是预先声称检查已通过。

下一步由当前私有试点任务持有者接收 Linux 候选并决定实际实施窗口；本仓可在后续自然
双产品任务收尾时使用 E2 交接约定收集 E3 所缺证据。此处不新增定时器、外部回灌或
高风险执行授权，不改写旧失败、批准和历史观察。
