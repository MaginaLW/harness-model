# 本机智能体过载防护预进入设计蓝图

> 日期：2026-08-13
> 状态：`pre-entry / not_authorized`
> 文档性质：阶段四执行计划的设计输入，不是可执行计划，不授权创建代码任务或启动 worker

## 1. 蓝图目的

本蓝图把[资源感知的多智能体调度设计](2026-08-13-resource-aware-agent-scheduling-design.md)中的单机安全控制面收敛为未来阶段四的候选交付序列。它回答“阶段四打开后应怎样编写正式执行计划”，不改变阶段一 MVP 规格和实施目录，也不提前建立阶段四代码任务。

正式实施计划必须在全部进入门满足后另建于 `docs/superpowers/plans/`，并按届时实际代码结构、Policy、CLI 和运行时 adapter 能力重新冻结文件范围、命令及测试。本文中的模块名称是职责边界，不是当前允许路径。

## 2. 不可越过的进入门

以下条件缺一时，阶段四 scope decision 必须为 `BLOCK`：

1. 阶段一十二项验收、四个真实试点和发布基线全部通过，当前 `SPEC-BLOCKER-001` 已有独立解除证据；
2. 阶段二设计/实现审核、V2、独立 Verifier、动态升级和 Hooks 的退出证据齐备；
3. 阶段三 V3、回滚演练、模型/角色注册表、资源与费用口径、真实模型路由试点全部通过；
4. AI Flow、Gate、worker envelope 和 evidence 接口已版本化，并至少经过两个兼容发布候选而没有破坏性变化；
5. 已通过至少连续 30 天或 30 个受治理任务的记录证明协调成本，且至少满足一项：
   - 两次有时间戳与资源快照的本机过载/无响应事件；
   - 至少 10% 的任务墙钟时间消耗在人工等待、串行协调或重复启动；
   - 至少 5% 的任务因资源争用被迫中止、恢复或返工；
6. 至少三个真实任务记录了暂停/恢复或集中审批需求，不能只依据架构偏好；
7. `.codex/config.toml`、获批模型路由决定和实际运行时模型目录一致，当前已知 `Sol/max` 对旧决定 `Sol/high` 的漂移已由独立 REVIEW 解决；
8. 新建 `REVIEW`、最低 `V1` 的阶段四 scope decision，绑定当时规格、Policy、允许范围、禁止动作和 `subject_commit`。

进入门中的数值是本设计的初始开启标准。若未来 Policy 要改变标准，必须以新的用户/Policy 决定替换并重新验证，不能由执行 Agent 自行降低。

## 3. 候选交付序列

正式执行计划应保持以下依赖顺序，每项都有独立退出证据后才进入下一项。

### B1：离线契约与黄金场景

交付：版本化的 ExecutionPlan、ResourceProfile、HostCapacitySnapshot、ResourceLease、SchedulerEvent、adapter capability 和调度 Policy 契约。

验证重点：环、重复节点、权限/预算放大、写冲突、三层嵌套超配额、未知画像、过期遥测、Luna 身份错误、旧 fencing、伪造 callback capability 和未观察 direct spawn。全部先由 fixture 固定语义，不连接真实模型。

### B2：资源采样、校准与压力状态

交付：跨平台采样器、机器指纹、`PROTECT/GREEN/AMBER/RED/EMERGENCY` 纯状态机、滞后与恢复节流。

验证重点：缺失值绝不当作 0；快照过期进入 PROTECT；高压停止准入；真实压力不是普通自动化测试。10 个样本只形成 `provisional/conservative` 画像；只有满足主设计的独立样本与统计门才可标记 `measured` 并提高并发。

### B3：主机级状态、队列、租约与恢复

交付：单一主机状态根、OS 独占 leader 锁、SQLite epoch/CAS、事件重放、资源租约、一次性 callback capability、冲突锁、公平队列和 orphan 恢复。

验证重点：两个仓库和两个会话连接同一状态根；只有持有 OS 锁且 epoch 当前的 leader 可在一个事务中创建 reservation、冲突锁、lease 和 admission 事件；数据库/锁不可用进入 PROTECT，不退化成每任务独立数据库。

### B4：Mock supervisor 与受控本地进程

交付：统一 dispatcher、能力协商、mock worker 和仅能启动固定无副作用 fixture 的本地进程 adapter。

验证重点：无租约、错误身份、旧 token、错误 callback capability、任意可执行路径和未过滤环境全部拒绝；测试结束无 orphan fixture 进程。此阶段仍不接 Codex 或外部模型 worker。

### B5：Evidence、Gate 与操作恢复

交付：调度证据摘要、`scheduler_required` Gate 条件、只读验证/模拟/状态/重放接口、脱敏报告和操作手册。

验证重点：需要受控 worker 的任务必须证明所有已观察 start 都有有效租约，adapter capability 未过期且没有未关闭 orphan。无法观察 direct spawn 的 adapter 标记 `advisory_unenforceable`，不能凭“没有观察到违规”通过全树强制力验收。

### B6：离线负载、故障矩阵和受控试点

交付：固定 seed 的大队列仿真、崩溃点矩阵、split-brain/旧 worker 副作用测试、性能记录，以及经单独动作批准的无副作用单机试点。

验证重点：逐步验证单 worker、两个可容纳只读 fixture、AMBER/RED/PROTECT、恢复节流和 leader 重启。任何 UI 无响应、EMERGENCY、未知进程或审计持久化失败立即停止。试点不含模型付费调用、凭据、push、merge、deploy 或 delete。

## 4. 正式执行计划必须冻结的内容

达到进入门后，新的执行计划至少明确：

- 当时实际目录结构中的逐文件允许范围，不能沿用本蓝图猜测路径；
- `aiflow start --objective ...`、每个重复 `--allow` 和 `--forbid-action` 参数；
- 依赖新增及 lockfile 更新的独立批准；
- 主机状态根、ACL、host identity、迁移、备份和卸载规则；
- 每个 Schema、错误码、状态迁移和 Policy 默认值；
- fake clock、fake sampler、mock supervisor、两仓库/两会话和崩溃点测试；
- V1 或更高 verify/Gate 的确切 task ID 和仓库外 run directory；
- 内容提交、独立需求/安全/质量复核和治理-only attestation 的绑定顺序；
- 真实压力、外部 worker、付费调用和任何高风险动作的单独批准点。

## 5. 候选退出标准

正式计划只有同时证明以下结果，才可把单机控制面标记为可用：

1. 同一主机的受控会话和仓库共享一个强制状态根，active leases 从不超过最小有效容量；
2. RED、EMERGENCY、PROTECT 下没有新 start；恢复按 Policy 逐个放行；
3. 无租约、旧 fencing、伪造 callback、过期 capability 和错误身份都不能改变状态；
4. 旧 worker 未确认退出前，其 reservation 和冲突锁不释放，同范围新 attempt 不启动；
5. 写节点在隔离 worktree/运行目录执行；不能隔离或副作用不明的 orphan 进入 REVIEW_REQUIRED；
6. leader 崩溃、暂停恢复和并发接管不能产生两个有效 admission；
7. 相同 Policy、DAG、快照、队列和假时钟输入产生字节稳定决定；
8. Gate 能区分 `enforced` 与 `advisory_unenforceable`，不夸大全局强制力；
9. 自动化测试不靠压满用户电脑；真实试点有动作批准、人工监看和明确停止条件；
10. 阶段一至三的治理、身份和外部 worker 不变量没有被放宽。

## 6. 当前禁止动作

本文当前不授权：创建上述模块、修改 `.codex/config.toml`、初始化主机状态根、启动 worker、运行压力试验、调用模型/API、读取凭据、修改阶段一状态、推送、合并、部署或删除。任何执行者看到本蓝图时都必须先检查第 2 节进入门并创建新的正式执行计划。
