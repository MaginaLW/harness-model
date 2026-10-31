# Review Package

## 审核目标

裁定当前完整 Node 3.1 本地 V0/V1 候选及限定性能修复是否满足冻结规格。正式裁定记录为 `reviews/REV-0002-r0001.json`，本文件提供 CLI 要求的交接概要，不替代该记录。

## 背景

任务从不含 Node 实现的 main 基线创建，全部 Node 生产差异保留在 base..subject 与覆盖率分母。旧 TASK-0128 的 BLOCK 和本任务先前失败的 e9 执行保留，不提供当前授权。

## 代码地图

- `src/aiflow/node_execution.py`、`node_verification.py`、`process_runner.py`：封闭材料、执行、输出、覆盖率与只读重核。
- `src/aiflow/policy.py`、`initialization.py`、`verification.py`、`verification_level.py`：显式版本、非覆盖初始化与固定计划。
- evidence、verification_service、review_service、approval、gate、status_service、task_service、freshness：共同消费者与既有 Native 语义。
- `contracts.py`、`state.py`、`git_context.py`：只读批次的新鲜性、逐事件语义与固定 Git 查询。
- Node companions、Git 回归及 SDK 合成前缀测试提供正反例。

## 语义变更

普通 wheel 新增 Windows x64、CPython 3.11、本地 NTFS 上的 Node Policy 3.1.0/profile @1/evidence 3.1 本地 V0/V1；固定工具、材料、Job/EOF/清理、TS line 85/90 和实际原件共同约束成功。Node V2/CI 在副作用前拒绝。

事件与 Policy 批次只复用当次 Schema 构建并在返回前复核全部资源内容，单值接口保持新鲜；Git 正常路径由四次缩为三次查询，保留合法 fullref、POSIX 路径、Windows ADS 拒绝及原错误优先级；SDK 各例使用独立合成副本并真实重核。

## 风险

该合同依赖受审源码与可信宿主，不提供恶意同用户代码沙箱或全部 OS/DLL 认证。完整材料、原件、漂移及未知清理均 fail closed。原 16 条 high 与新增 5 条 medium 在正式记录中保留严重度、证据与 resolved 理由，未忽略或降低门禁。

## 证据

已验证：当前 ordinary-wheel 两条真实生命周期、18 个检查进程、正向 Gate 后 6/2 种实际篡改拒绝；76 输入及 49 源码与 ZIP/安装字节一致。独立 verifier 接受全部 14 项 Native 检查，完整 5663 项中 5658 通过、5 条明确的平台或依赖 skip，1067.07 秒，原 1200 秒预算保持；两个 opt-in 场景已在 wheel 验收实跑。原工具的两域 branch-enabled combined 总覆盖率 85 与 diff 90 门通过，五项实际固定变异全部 killed。

已验证：正式实现审核 APPROVE、无未关闭发现，同一独立 verifier 已 finalize；当前 `evidence.json` 为 final/passed，稳定 snapshot 与正式 context 均保持。

未验证：当前 PR head 的 Ubuntu required check 尚未运行；Node installed V2、Node CI 和真实目标采用尚未交付。本轮未调用真实模型、微信或生产，也未上传私有目标材料。

## 审核问题

- 完整 Node 实现及限定性能修改是否符合当前冻结规格与原门禁？
- 普通 wheel、真实进程、材料和消费者的成功及失败事实是否得到当前原件支持？
- 历史失败、21 条发现、尚未交付能力及可信宿主边界是否如实保留？

## 推荐结论

APPROVE。当前正式记录与独立验证支持代码批准；合并仍要求当前 Gate 和 exact-head required CI 通过。
