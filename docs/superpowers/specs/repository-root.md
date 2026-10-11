# CLI 仓库根定位与 Schema 作用域

状态：可审阅规格准备。本文提出最小兼容方案；源码实施仍须当前 AI Flow 准入、独立审核、规格批准及正式验证，本设计不提供执行许可。

## 1. 问题与范围

[CLI](../../../src/aiflow/cli.py)目前将 `Path.cwd()` 传给业务服务；[contracts](../../../src/aiflow/contracts.py)默认从相对 `.ai/schemas` 加载资源。因此完整克隆内的子目录调用可能读错任务或找不到 Schema。[接入指南](../../operations/adoption.md#完整引擎的跨仓库边界)已经列出这项产品化缺口。

本次让 CLI 从工作树根或任意内部目录运行同一业务命令时，使用同一仓库资源。仅修改 `src/aiflow/cli.py`、`src/aiflow/contracts.py`、`src/aiflow/git_context.py`；测试与长期用法文档独立准备，不混入治理源码 task。

不增加初始化、资源分发、外仓 CI 适配或 `--repo`，不修改 Policy、Schema 内容、身份、授权、质量阈值、评分或 provider。缺少 `.ai` 资源的仓库仍不能仅凭安装 wheel 运行完整引擎。

## 2. 定位规则

在 [git_context](../../../src/aiflow/git_context.py)提取 `resolve_repository_root(path: Path) -> Path`，复用 `_run_git` 的错误和10秒超时处理。`collect_git_context` 复用该定位函数，继续负责 repository-id、HEAD、branch 与 dirty 状态，不建立第二套 Git 执行或身份校验。

1. 对传入调用目录执行 `Path.resolve()`，运行 `git rev-parse --show-toplevel`。
2. 输出须非空、绝对路径且有效 UTF-8；将根解析为真实绝对路径。
3. 根须为调用目录本身或其祖先，用路径关系判断，不能用字符串前缀接受相邻目录。
4. 根关系成立后，检查调用目录及其逐级父目录，直到返回根之前（不含返回根）；任一目录存在 `.git` 文件或目录，说明定位跨越嵌套仓库边界，以 `GIT_ROOT_INVALID` 拒绝。只检查 `.git` 标记，不搜索 `.ai`，不回退或初始化。
5. bare、非仓库、失败和超时按现有稳定错误报告；空根、相对根或无祖先关系拒绝。不得在失败后向上搜索 `.ai` 或借用其他仓库资源。

Git 环境与现有业务 Git 调用一致，继承当前环境；不只在定位时净化 `GIT_DIR`、`GIT_WORK_TREE` 等变量，也不因这些变量存在而一律拒绝。相对值按既有定位和业务 Git 校验判断。根无祖先关系或跨越上述 `.git` 边界时拒绝；这不是新沙箱、全面 Git 身份认证或跨仓访问授权。

无环境覆盖时由 Git 决定工作树根；额外标记检查只拒绝被越过的嵌套边界。最近嵌套根缺少 `.ai` 时由原有资源校验拒绝，不能退回父仓。普通 linked worktree 使用自己的根，根自身的 `.git` 文件不被上述检查拒绝。

## 3. CLI 调用与相对路径兼容

先完成 `argparse`。仓外 `--help`、子命令 help、`--version`、无命令及 `argparse` 错误保持现有行为，不定位 Git、不加载仓库资源。只有成功解析并需要分派的业务命令才定位一次。

CLI 保存调用目录，定位根后在一个 Schema 作用域中分派命令，将根传给原来接收 `Path.cwd()` 的所有业务服务。每次 CLI 分派只做一次入口定位；业务服务原有的 Git 身份与验证读取仍按需要执行，不缓存或跳过这些检查。不得 `chdir`，也不得暂时改全局工作目录或模块常量。

| 路径类别 | 解析基准与兼容要求 |
|---|---|
| 内部 task、Policy、模板及 Schema | 业务服务使用定位根；默认 Schema 使用该根的 `.ai/schemas`。 |
| `--input`、`--options-file`、`--output` | 保持用户调用目录的相对文件语义；绝对路径仍按原输入处理。 |
| `--evidence`、`--action-file`、`--ci-run-dir` | 同样保持调用目录；不得将用户显式文件参数重新拼到仓库根。 |
| 允许范围、任务内引用和其他非文件字符串 | 保持各自现有业务定义，不因根定位重新解释或增加路径参数。 |

## 4. Schema 作用域

contracts 使用标准库 `ContextVar` 与 context manager 管理本次 CLI 的 Schema 目录，候选入口为 `schema_directory_context(directory: Path)`。CLI 绑定根下 `.ai/schemas` 后调用业务服务；退出时在 `finally` 中恢复 token，成功、异常和嵌套调用均恢复先前作用域。

目录优先级为：显式 `schema_directory` 参数 → 当前作用域目录 → 现有相对 `.ai/schemas` 默认值。显式相对目录仍相对调用目录，不被作用域重定位；未从 CLI 调用的既有库用法保持默认行为，不隐式引入 Git 查找。

`load_schema`、Schema registry、默认 validation 及 require 路径必须使用同一个有效目录；不能主 Schema 来自根而 `$ref` registry 仍来自调用目录。现有带显式目录的内部入口保留；避免将默认参数预绑定到常量，或在一个上下文中缓存另一上下文的资源。

ContextVar 仅提供调用作用域隔离，不证明跨线程自动传播或建立并发调度器。本次没有新后台线程或执行器；测试覆盖嵌套与独立上下文之间不串资源。

## 5. 验收矩阵

| 检查 | 必须证明的行为 |
|---|---|
| 根与子目录 CLI | 真实隔离 Git fixture 中 root/深层目录的只读命令结果一致；写命令各在等价新 fixture 中只写正确根下任务，不在子目录生成 `.ai`。 |
| 默认和显式 Schema | 子目录默认使用根资源；显式目录优先。使用两个可区分 Schema 的根证明没有串用，registry 引用与主 Schema 一致。 |
| 作用域与 cwd | 成功、业务异常及嵌套上下文后，cwd 与先前 Schema 上下文恢复；连续不同仓库 CLI 调用不泄漏状态。 |
| 六类文件参数 | 在子目录提供与根同名、内容不同的文件，证明读取/写入和 `ci-run-dir` 均保持调用目录语义。 |
| 错误边界 | bare、非仓库、Git超时、空/相对/无关根输出被拒绝；真实nested fixture缺少`.ai`且绝对`GIT_DIR`/`GIT_WORK_TREE`指向父仓时，以`GIT_ROOT_INVALID`拒绝并证明父原件不变。普通最近根和linked worktree仍可用；相对Git环境保留定位与业务校验。 |
| 无仓库入口 | help/version/无命令/argparse错误不调用Git或业务服务，保留现有退出与输出合同。 |
| 正式质量 | 固定候选通过完整测试、85%总覆盖率、90%diff coverage、whitespace、Ruff、format、mypy及required CI；原生verify/Gate分别保留对应版本结果。 |

新增测试以真实 CLI 分派、资源绑定和错误边界为中心，不只复述辅助函数。mock仅用于难以稳定制造的Git超时/非法输出；根、子目录、嵌套仓库及文件参数场景采用真实隔离fixture。

## 6. 并行与准入顺序

计划3名sub-agent并行：Git定位与`collect_git_context`复用；contracts作用域；独立测试与文档准备。分别独占文件，主Agent负责CLI接线、统一接口和整合。安全测试/文档按维护模式task-free独立提交；治理源码作为单独AI Flow task，先核原生status/classify、Design Review与所需spec批准，不因安全材料完成跨过实现门。

整合后计划2名非作者并行审：路径/环境/调用兼容；Schema作用域/资源引用及错误边界。作者定点修复，主Agent串行固定候选、正式验证、账本、暂存与提交；实现审核、原生verify及Gate成立后按现行常设授权推进。无新实质问题不扩大重复审核，独审结论不替代测试或授权。

本项退出只证明完整克隆内的统一仓库定位与相对参数兼容。初始化、资源分发、CI适配及其他外仓产品化能力继续按真实需求分别建设。
