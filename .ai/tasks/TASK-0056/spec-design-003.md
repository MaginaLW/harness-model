# TASK-0056：显式仓库外 pytest 临时目录

## 目标

为原生 verify 增加可选 --pytest-temp-root，使 pytest fixture 临时目录落在操作者指定的普通本地仓库外父目录中。默认调用、Policy 选择器、超时、环境白名单、检查集合和门禁阈值保持现值；不声称解决既有超时原因或保证性能提升。

## 范围

基线 ef92b795da729566870ff4878f100a4ffe319db5，分支 codex/e4-verification-control。
允许 src/aiflow/verification_temporary.py、verification.py、verification_service.py、process_runner.py、cli.py；tests/unit/test_verification_temporary.py、test_verification_plan.py、test_process_runner.py；tests/integration/test_verify_command.py、test_external_review_command.py、test_begin_close_commands.py；docs/operations/pytest-temporary-roots.md，以及本 task 自有治理记录。安全测试和文档单独提交，生产治理实现走完整 AI Flow。

CLI：python -m aiflow verify TASK-ID [--pytest-temp-root DIRECTORY]。父目录必须预先存在，是绝对本地普通目录；其自身和每个祖先不得为 symlink、junction 或 reparse。拒绝位于任何带 .git 文件或目录标记的仓库/工作树内，包括祖先仓库；对每个祖先用不跟随链接的元数据查询保守拒绝 HEAD 标记与 objects 或 commondir 标记共存的裸仓库结构。原有 MINENV 不包含 GIT_DIR 等仓库发现环境。Windows 在元数据访问前拒绝 UNC、设备命名空间、ADS、保留设备名、控制字符、尾随点/空格和非本地支持盘类型；不改变系统配置或环境白名单。

新增小型独立守卫模块。用已有安全 run_id 和 task_id 原子创建唯一运行容器，exist_ok=False；记录目录身份并在实际启动 pytest 前重新验证祖先、容器和命令对应关系。每个去重 execution 分配从未存在的独占叶目录，不能把父目录、日志目录、旧叶目录或源码路径作为 basetemp。pytest 自行创建叶目录，守卫不得删除已有目录。普通并发冲突或可检测身份漂移须拒绝；不宣称提供抵御同用户恶意路径替换的 OS 沙箱。

仅 unit_tests、regression_tests、coverage_xml、acceptance、integration 的原生 pytest 执行，在现有 Policy 全部语义检查之后追加一个固定 --basetemp=<owned-leaf>；最终 checks 与 executions 的 argv 必须一致，去重执行共享叶目录。不能引入任意 Policy 占位符、注入参数或改变选择器。没有 pytest 检查时验证父目录但不分配容器。不存在选项时不创建外部目录、不改 argv。--finalize 或 --abandon 不能与此运行选项混用，须在写入前拒绝。其他已有模式约束继续生效。

实际 argv、command_summary 和 reproduce_command 记录本次选择；绝对本机路径只留在被忽略的运行证据，便携治理报告采用占位符。verifier context 仍绑定原任务/规格/Policy/源码事实，不能把这个仅运行时参数加入 finalize/CI 重建的 context。CI 使用同一显式参数及原有只读账本、日志、输出约束。

实施阶段并行启用 2 个 sub-agent：一个独占守卫模块及其单元测试，一个独占已有计划/runner/CLI 集成测试。主 agent 独占生产集成及文档。准入、接口约定、统一提交、完整 V2、实现审查、批准和 Gate 串行；正式实现审查和原生独立 verifier 由未参与实现的 agent 执行。

## 非目标

不修改 Policy、Schema、workflow、阈值、预算、测试选择器、MINENV、任务状态机、mutation 行为或 E4 报告导入代码。不采用仓库内 basetemp、junction、fake home、隐式环境 hook，不停止无归属进程，不修改 Defender、ACL、系统临时目录或全局工具。不自动启动 E4.3/E4.4、provider 或后续业务阶段；TASK-0055 的依赖集成与重新准入另行显式记录。

## 验收条件

1. 默认 plan 和 CLI 兼容：原检查、argv、环境、时限、去重关系、finalize/CI verifier context 不变，旧参数 Namespace 仍能分派。
2. 正常本地外部父目录：每次运行及每项原生 pytest execution 获得独占新叶，checks/executions 匹配；真正 pytest tmp_path 位于该叶下，非 Git fixture 仍检测为非仓库。
3. 初始相对/缺失/文件父目录、任意 .git 或裸库结构祖先、symlink/reparse、Windows 非法词法路径及 finalize/abandon 混用在加载任务前零写入拒绝。计划解析只验证并生成路径，不创建目录；初始已存在容器拒绝分配。执行期容器竞争、预存叶或身份漂移在日志目录创建和 pytest 启动前拒绝，保留必要的本轮任务记录并原生转入 FAILED；不得遗留 VERIFYING 或以局部结果冒充通过。原件、源树、兄弟目录和已有容器不被删除或覆盖。
4. CI 显式模式维持只读账本和现有 output/run_dir 防护；实际 argv/重现命令能说明运行位置，finalize 不发生仅因运行参数导致的 context 漂移。
5. 完整原生 V2 包含所有 Policy 必需检查、完整测试、85% 总覆盖率、90% diff coverage、whitespace、Ruff、format、mypy、acceptance、integration、targeted mutation 和独立 verifier。只有实际退出、完整证据和独立 Review 通过才完成；失败日志保留，不用局部测试替代。

## 禁止动作

本实现 task 禁止推送、合并、部署、删除、凭据导出、付费外部调用。用户已授权整体交付的推送合并，仍由后续独立发布 task 对实际候选和 CI 绑定记录。运行容器仅在显式验证操作下创建；不递归清理临时目录，不输出疑似凭据。

## 错误行为

路径不安全、所有权无法证明、身份漂移、已有叶、argv 不匹配或容器冲突时，在 pytest 启动前确定失败；执行期守卫异常记录原生 FAILED，不能回退到未经批准的另一目录或放宽守卫。原生状态/新鲜度/角色/门禁失败继续执行现有拒绝逻辑。超时仍记录真实 failed/unknown；若本改动不能解决资源阻塞，先定位新证据，不重复盲跑。

## 回滚

使用正常 Git revert 恢复本 task 生产和安全提交，保留规格、批准、事件、Review、日志和证据历史。外部临时目录不自动删除，已有源树和其他任务保持原状。不得重写旧 TASK-0055 的证据或静默更换其 base。

## 失败诊断后的测试夹具兼容修订

第二轮完整 V2 保留为 FAILED。原用例实测确认普通 Windows 物理 I/O 在 261 字符复制路径和 260 字符原子临时文件名处失败；缩短普通外部父目录没有解决所有测试文件。只在 external-review 测试夹具的复制、历史记录检查和损坏样例写入中使用兼容 Windows 的物理路径表示，逻辑 Case.root、服务参数、任务地址、真实 Git、owned temp 及全部业务断言保持原值。不得把 fixture 移出本轮独占叶或修改生产 storage 来隐式扩大本 task。

原 verify-command 模块还实测阻塞在测试 Git helper 的 Windows timeout 清理：原 10 秒期限过后 kill() 后的无期限 communicate() 等待读管道线程。该测试 helper 可在超时前保留直接进程及其后代的所有权，按平台终止该自有树并有界回收；保持原 Git argv、cwd、capture、UTF-8、check 与 10 秒命令期限，不改 production runner、MINENV、Policy 或预算。初始 Git 超时的实际原因仍 unknown；有界清理只修复已观察的测试清理阻塞，不声称提升性能。

验收增加：在原 native 最小环境和真实 TASK/run/EXEC 深度内复跑原失败用例、完整 external-review 与 verify-command 模块；Windows 超时清理须用真实自有后代复核，不伪造退出码或删掉断言。随后仍执行全部原生 V2、独立实现 Review、finalize、代码批准和 Gate。单例或模块结果不替代完整验证。
