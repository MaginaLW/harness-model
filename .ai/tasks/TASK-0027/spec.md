# TASK-0027 Specification

## 目标

删除仓库内已跟踪的 `.reasonix` 运行时元数据目录，并在根 `.gitignore` 中忽略
`/.reasonix/`，使后续桌面运行时生成的同类文件不再污染 Git 工作树。

## 范围

1. 业务范围严格限定为 `.reasonix/**` 与根 `.gitignore`。
2. 删除当前 Git 跟踪的 10 个 `.reasonix` 文件以及删除后为空的目录。
3. `.gitignore` 只新增根目录规则 `/.reasonix/`，不改变其他 ignore 语义。
4. 删除动作只适用于仓库内解析后的 `.reasonix` 目录，并绑定当前任务的单次 action approval。

## 非目标

1. 不修改 `.ai/`、源码、测试、Policy、依赖、锁文件或项目状态投影。
2. 不删除 `.reasonix` 以外的文件，不清理用户目录、其他仓库或任何外部系统数据。
3. 不执行 push、merge、deploy、发布、凭据导出、外部模型或付费调用。

## 验收条件

1. 删除前的精确清单只包含当前 10 个 Git 跟踪文件，且没有未知未跟踪内容。
2. 实施后 `Test-Path -LiteralPath .reasonix` 为 false，`git ls-files .reasonix` 无输出。
3. `git check-ignore -v .reasonix/probe.json` 显示由根 `.gitignore` 的 `/.reasonix/` 规则命中。
4. base..subject 的唯一业务变化为 10 个 `.reasonix` 文件删除和 `.gitignore` 一行新增。
5. AI Flow validate、scope、Policy 选定验证、`git diff --check` 与完整回归通过。

## 禁止动作

禁止 push、merge、deploy、package publish、secret export、paid external call、external model
call；禁止删除 `.reasonix` 之外的任何路径。若 action approval 缺失、过期、绑定变化或清单出现
未知内容，不得执行删除。

## 错误行为

若解析后的目标不是仓库根下精确的 `.reasonix`、目录清单相对冻结规格发生变化、发现未知未跟踪
文件、Git 恢复基线不可用，或实现需要修改允许范围外文件，必须停止并重新治理；不得扩大删除范围、
使用递归通配符指向上级目录或把删除伪装成未受控清理。

## 回滚

通过后续受治理提交从本任务父提交恢复 10 个已跟踪文件，并移除根 `.gitignore` 中新增的
`/.reasonix/` 规则；TASK-0027 的规格、批准、receipt、事件与 evidence 保持追加式，不删除或重写。
