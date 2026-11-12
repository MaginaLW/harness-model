# Task Specification

## 目标

在已包含委派与阶段上下文规则的干净后继基线上，修复只读 Git 上下文可触发 optional index refresh 的缺陷，完成原政策交付的当前候选验收，不伪造 TASK-0143 成功。

## 范围

基线 6559014be43727a38cf2aaf4ce0a9efe707c217b，政策 source 82758f11b71072b666d417a212d584c73725608f，公共完整 base 39898f30b8914402d737fab9f59bebf8d8656f53。仅修改 src/aiflow/git_context.py、tests/unit/test_git_context.py 和 docs/operations/maintenance-status.md 的必要当前状态简记；治理记录只追加本任务目录。三处现有 Git subprocess（_run_git、_read_branch、_is_ancestor）通过每次调用局部 env={**os.environ, GIT_OPTIONAL_LOCKS: 0} 禁止 optional locks，保留 argv、cwd、超时、错误合同与其余继承环境。使用既有 Alpine candidate 的项目解释器和锁文件环境，不安装或更换依赖。

## 非目标

不改 AGENTS 现有政策、常设授权、Policy、CI、模型选择、权限、锁文件、fixture、业务 mutation 或其他任务历史；不新增模块、依赖、持久配置或全局环境设置。原 TASK-0143 保持 FAILED，其冻结 spec、批准及 Windows/Ubuntu/Alpine 各轮失败原件全部保留，不迁移旧批准或将新验证冒充旧轮通过。首次 index writer 仍为 unknown。

## 验收条件

1. 三处只读 Git subprocess 均显式覆盖子进程 GIT_OPTIONAL_LOCKS=0，同时保留其他继承变量、身份、argv、cwd、超时和错误合同，调用前后父进程环境不变。
2. 在真实临时 Git checkout 主动制造 tracked 文件 stat 与 index stat 不一致，调用 collect_git_context 后仍准确报告内容状态，且 index 的 inode、mtime_ns、字节内容保持完全相同；原 test_installed_mutation_transactions 的 source/actor/state 严格 no-write 断言全部保持原样并通过。
3. 最终整合树 AGENTS.md 的计划、积极委派/按需扩展、阶段上下文三条仍满足原用户结果；并发额度、主 Agent 是否计入及扩展批准继承全局，不复制数字。AGENTS 从当前治理模式标题起全文与公共 base 完全相同，既有范围控制条款保持不变；只复核当前差异，不重做未变化部署。
4. 使用真实 code_modified/behavior_changed/regression_risk 事实让现行 CLI 决定 route 和 verification level；独立 design/implementation 审核、当前候选所需批准、完整原生 verify、Gate、whitespace 与当前发布 head required CI 均须满足，不降低分类或门禁。
5. 局部回归先使用独占、精确预检的临时根；完整 pytest 先暂停，待分类与计划审阅后再启动现行 Policy 的单实例共享执行。完整单轮上限 3000 秒，参考上轮约 809 秒，另保留其他必需检查各自原预算；TEMP/TMP/TMPDIR 指向同一被测 checkout 之外的既有 guest 任务临时根，不改全局环境，保留原始日志与失败。首轮失败后先诊断，不盲重启或机械重试。

## 禁止动作

不得修改原权限守卫、snapshot fixture 白名单或 inode/mtime/content 断言来消除失败；不得改 TASK-0143 或任一冻结历史、Policy、CI、依赖、锁文件；不得真实模型调用、SDK 审核、native probe、压力测试、部署、删除数据、导出凭据或付费调用。本子代理不执行 push/merge，发布由主会话按常设授权与当前 head 必需检查统一处理。

## 错误行为

发生范围或身份漂移、未知进程归属、门禁失败、独立审核缺陷或资源异常时保留事实，只暂停受影响动作并先诊断；不得推断首次 writer 或将猜测当因果证明，不降低守卫或复用失效批准。同因失败无新证据不重试。完整验证未审阅计划前不启动。

## 回滚

源码及必要状态简记可用后续普通恢复提交撤回，不改写已发布历史；TASK-0143 与本任务追加式账本、原始失败和日志保留。
