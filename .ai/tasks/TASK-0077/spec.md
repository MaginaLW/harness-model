# Task Specification

## 目标

使已有完整 AI Flow 资源的 Git 克隆可以从任意仓内子目录使用 CLI，并始终使用同一 Git 根的任务、Policy 和 Schema；保留调用目录下显式文件参数的语义及进程 cwd。

## 范围

- src/aiflow/git_context.py：抽出 resolve_repository_root(path)，复用已有只读 Git 固定 argv、超时、错误处理；校验返回根为输入目录的祖先，collect_git_context 复用它。
- src/aiflow/contracts.py：以标准库 ContextVar 和 schema_directory_context contextmanager 为一次 CLI 调用绑定 Schema 目录。显式目录优先，退出必恢复；作用域外默认行为保持。
- src/aiflow/cli.py：参数解析后，仅对业务命令定位一次根；所有服务调用使用该根，契约在对应作用域内验证。帮助、版本、无命令及 argparse 错误不需要仓库。
- 仅本任务账本。安全测试与用法文档由独立 task-free 阶段提交，不修改旧任务或历史原件。

## 非目标

不初始化仓库、复制身份或分发资源，不新增 --repo，不改变服务的显式 root API、Policy、Schema 文件、批准、Gate 或验证等级，不实现评分、Provider、可信执行器或任何真实外部动作。

## 验收条件

- tests/integration/test_cli_repository_root.py 验证多层子目录的 start/status/validate 与根目录结果一致；子目录无额外任务目录。
- tests/unit/test_repository_schema_scope.py 验证显式目录优先、嵌套/独立 context 隔离、错误与异常退出恢复；CLI main(argv) 调用前后 cwd 不变。
- --input、--options-file、--output、--evidence、--action-file、--ci-run-dir 的相对路径仍以调用目录解释；不同根的同名文件不串用。
- 嵌套 Git 无 AI Flow 配置时拒绝，不借父仓；实际返回根为祖先后，调用目录至根之前的祖先链有 .git 文件或目录时拒绝 GIT_ROOT_INVALID，防止 GIT_DIR/GIT_WORK_TREE 越过内层仓边界，保留父原件及目录不变。非 Git、bare、超时、异常或无关根返回明确错误。
- 从仓外运行 --help、--version、子命令帮助及错误参数维持 argparse 退出契约。
- 定位与后续 Git 使用同一继承环境，不增加宽泛环境拒绝或静默净化；祖先校验不接纳无关根。
- 按实际 Policy 完成原生 verify、独立实现审核、Gate、完整 pytest、85% 总覆盖率、90% diff coverage、Ruff、format、mypy、whitespace 和 required CI。

## 禁止动作

不执行部署、删除数据、凭据导出、付费调用、强推或改写已推送历史，不修改授权文件、CI 阈值、其他任务和归档标签。发布仅在常设授权覆盖与 required CI 通过后按其条件执行。

## 错误行为

找不到真实 Git 根、返回路径不属于输入目录、契约资源缺失或非法时拒绝。不得搜索父仓的 .ai 作为替代；不得自动创建身份、批准或评分；错误和异常不污染后继调用的 Schema 作用域。

## 回滚

revert 本任务实现提交可恢复原 CLI 根目录行为；保留本任务事件和审核记录。测试与用法提交使用各自明确提交回滚，不恢复已退役功能。
