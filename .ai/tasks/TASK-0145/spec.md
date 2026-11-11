# Task Specification

## 目标

补齐只读 scope Git 采集入口的 optional index refresh 缺陷，使包含委派/阶段上下文规则及 Git context 修复的最终整合候选满足既有交付与验证要求。

## 范围

基线 12f15a3b7feaf365cf60d019a1b0417ce27407cf 已保留 TASK-0144 真实失败及 26c8adc319b7aeba3ed8a68a601168e9db532e36 的 Git context 修复；政策 source 为 82758f11b71072b666d417a212d584c73725608f，公共完整 base 为 39898f30b8914402d737fab9f59bebf8d8656f53。仅修改 src/aiflow/scope.py、tests/unit/test_scope.py 和 docs/operations/maintenance-status.md 必要当前状态简记；治理记录只追加本任务目录。复用 scope._run_git 的现有单一入口，以瞬时子进程 env 覆盖 GIT_OPTIONAL_LOCKS=0，保留其他继承变量、argv、cwd、超时、返回值与错误合同。不安装或更换环境、版本、依赖。

## 非目标

不改 AGENTS 的现有政策、常设授权、Policy、CI、锁文件、fixture、业务 mutation 或任何历史任务。不新增模块、依赖、持久配置或全局环境设置。TASK-0143 与 TASK-0144 保持 FAILED，冻结 spec、批准、原始 evidence 和各轮日志完整保留；不重用旧批准、不将新结果冒充旧轮通过，也不推断首次 index writer。TASK-0144 的 source 场景 index 字节也发生变化，不能统一描述为仅 inode/mtime 改变。

## 验收条件

1. scope 只读 Git 入口禁止 optional locks，继承其他父环境且不修改父环境；原 argv、超时、cwd、错误优先级与路径报告语义不变。最终整合树保留 Git context 三入口的既有修复与真实回归 PASS。
2. 在真实隔离 Git checkout 主动制造 tracked 文件 stat 失配，父/测试环境显式允许 optional locks；同一实际 scope 采集用例在旧 scope 实现下 RED，在修复后 GREEN，路径结果准确，index inode、mtime_ns 和全部字节严格不变。不得以父进程 GIT_OPTIONAL_LOCKS=0 或测试专用旁路消除副作用。
3. TASK-0144 的四个失败用例保持原 strict 断言与 fixture 全部不变；scope 测试、git_context 测试及原失败四路径的局部回归通过。由独立实例只读审计四条失败路径的完整 Git 调用图，核对所有实际可达入口，无同类遗漏；发现超出本范围的真实缺口则暂停受影响修改，按实际范围重新规划，不机械逐模块 full。
4. 最终 AGENTS 仍只包含政策目标对应的计划、积极委派/按需扩展、阶段上下文三条差异；全树额度、主 Agent 计数与扩展批准继承全局，不复制数字。从当前治理模式标题起全文与公共 base 相同，既有范围控制条款不变。
5. 用真实 code_modified、behavior_changed、regression_risk 事实由正规 CLI 决定 route/level；独立 design/implementation 审核、当前版本所需批准、完整原生 verify、Gate、diff 检查和发布 head required CI 均须满足，不降低门槛。完整验证先 HOLD，只有四失败路径 Git 审计无剩余缺口且有意义 RED/GREEN 与原 strict 局部验证完成后才按主会话计划启动单实例正式完整验证；每次完整共享 pytest 上限保持 3000 秒，预计约 14–16 分钟，其余检查沿原预算，失败先诊断不盲重试。
6. 子进程 TEMP/TMP/TMPDIR 统一精确预检的本任务 guest 临时根，位于被测 checkout 之外；局部 RED/GREEN 日志分别保留在 ignored build/task145，原 full 失败原件不覆盖。

## 禁止动作

不得放宽权限守卫、snapshot 白名单、inode/mtime/content 断言或原失败四case；不得改 TASK-0143/0144 冻结历史、Policy、CI、安装环境或锁文件。不得真实模型/SDK审核/native probe/压力测试/部署/删除数据/导出凭据/付费调用。本子代理不执行 push/merge，发布由主会话按既有授权与当前候选必需门禁统一处理。

## 错误行为

完整性审计发现额外入口、范围漂移、未知进程、身份变化或门禁失败时保留原件，只暂停受影响操作并先诊断；不将 wrapper exit0 或局部 PASS 当完整通过，不降低分类或原守卫，不用无来源的全局环境设置掩盖缺陷。重复同因失败无新证据不重试。

## 回滚

可通过后续普通恢复提交撤回本任务源码与必要状态简记，不改写已发布历史；旧任务与当前任务追加式账本、失败和原始日志保留。
