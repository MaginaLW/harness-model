# Task Specification

## 目标

在当前 `main` 上收敛仓库卫生：让根级生成物被明确忽略而任务本地审计证据不被遮蔽，让 AGENTS.md 成为唯一共享 Agent 权威、CLAUDE.md 成为受测的 Claude 适配入口，并把运行期证据的保留与有界清理边界写入文档；不改变任何运行期行为，不重写历史审计记录。

## 范围

- `.gitignore`：增加根级忽略规则，覆盖 Python 构建产物、分发目录、HTML 覆盖率输出与带后缀的 coverage 数据文件。规则必须是根级锚定的，不得以宽泛扩展名遮蔽 `.ai/tasks/**` 下的审计证据。
- `CLAUDE.md`：收敛为链接 AGENTS.md 的 Claude 平台适配入口，不再复制共享治理规则。
- `README.md`：把 Agent 规则入口指向 AGENTS.md 与 CLAUDE.md 的新分工。
- `docs/operations/recovery.md`：补充运行期证据追加式保留、有界清理与历史绝对路径例外的说明。
- `tests/integration/test_agent_entry_files.py`：覆盖入口文件契约（AGENTS.md 为共享权威、CLAUDE.md 链接到它）。
- `tests/integration/test_repository_hygiene.py`：新增，覆盖忽略规则契约的正向与负向路径。
- `CHANGELOG.md`：在 Unreleased 记录本次收敛。

## 非目标

- 不改 `src/aiflow/**` 的任何运行期行为、Policy、证据 schema、Gate 语义或 CI 配置。
- 不重写、删除或迁移任何既有任务的事件、证据、批准或日志。
- 不改动 `.gitattributes`、不处理变异证据在 Windows 检出下的换行符问题（另行立项）。
- 不引入新的忽略规则去覆盖 `.ai/tasks/*/logs/` 之外的任务目录内容。

## 验收条件

- `git check-ignore` 对代表性生成路径（构建目录、分发目录、HTML 覆盖率目录、带后缀 coverage 数据）判定为忽略。
- `.ai/tasks/` 下的 `task.yaml`、`events.jsonl`、`evidence.json`、`approvals.json` 与 review/verifier context 均不被忽略。
- `tests/integration/test_agent_entry_files.py` 与 `tests/integration/test_repository_hygiene.py` 全部通过。
- V1 完整回归、`ruff check`、`ruff format --check`、`mypy src` 通过，总覆盖率不低于 85%，diff coverage 不低于 90%。
- `aiflow scope TASK-0036` 通过，改动不超出允许范围。

## 禁止动作

push、merge、deploy、delete、secret_export、paid_external_call。本任务不执行外部动作、不访问网络、不使用凭据、不产生付费调用。

## 错误行为

- 若某条忽略规则会遮蔽 `.ai/tasks/**` 下的审计证据，测试必须失败而不是放行。
- 若 CLAUDE.md 不再链接到 AGENTS.md，或重新复制共享治理规则，入口文件测试必须失败。
- 若既有任务记录被修改，`aiflow scope` 与 `validate` 必须拒绝。

## 回滚

改动全部在版本控制内且可逆：还原 `.gitignore`、`CLAUDE.md`、`README.md`、`docs/operations/recovery.md`、两个集成测试与 `CHANGELOG.md` 即恢复原状。本任务不写入其他任务的证据，回滚不涉及既有审计账本。

## 与 TASK-0032 的关系

本任务重做 TASK-0032 的同一份内容。TASK-0032 的记录绑定 base `5f52afe`，而 `main` 已前移到 `55fd5a5`，AI Flow 没有受支持的方式移动任务的 `base_commit`，因此其证据无法在当前 main 上复用。TASK-0032 的记录作为历史保留，不被修改或删除。

原任务把四项 V2 要求全部断言为 `true`，那是阶段二「自举 REVIEW 试点」为演练 V2 所做的选择；该目的已随阶段二完成。本任务按内容实情断言为 `false`：改动限于忽略规则、Agent 入口文档与两个集成测试，不触及定向变异清单所针对的 policy、verifier、approval、gate、evidence 护栏，其自身的集成测试也已包含在 V1 完整回归中。该判断由项目所有者在本次收尾中明确确认。
