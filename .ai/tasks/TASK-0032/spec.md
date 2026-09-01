# Task Specification

## 目标

在不改写历史审计证据、不改变 AI Flow 运行时语义的前提下，防止常见
Python 生成物误入库，收敛 Agent 入口规则的权威源，并明确本地验证日志、
审计证据和机器绝对路径的保留与清理边界。

## 范围

1. 在 `.gitignore` 中增加仅限仓库根的 `/build/`、`/dist/`、`/htmlcov/`
   和 `/.coverage.*`；保留现有 task-local logs 和其他 Python 忽略规则。
2. 保留 `AGENTS.md` 为共享 Agent 规则的唯一权威；将 `CLAUDE.md` 缩减为
   Claude Code 平台入口，明确要求先读取并遵循 `AGENTS.md`。
3. 同步 `README.md` 中的 Agent/Claude 入口说明，避免暗示存在两份并列权威。
4. 在 `docs/operations/recovery.md` 增加运行时证据保留与清理边界：
   任务账本和哈希绑定证据不改写；活动 task 的本地 logs 保留；被忽略的
   logs 不作跨 clone 持久性承诺；只允许精确清理已确认无诊断或审计用途的
   OS 临时运行目录。
5. 在同一恢复说明中区分人工编写文档与历史运行时记录：新的文档/
   示例使用 `${REPO_ROOT}`、`${TEMP_ROOT}` 等占位符；现有 task、evidence、
   action 和 snapshot 中的绝对路径作为不可变历史保留。
6. 更新 `tests/integration/test_agent_entry_files.py`，并新增
   `tests/integration/test_repository_hygiene.py` 锁定上述规则。
7. `TASK-0032` 自身治理目录由 AI Flow 管理，不计入业务文件数。

## 非目标

1. 不删除、取消跟踪、压缩、迁移或改写任何 `.ai/tasks/**` 历史记录、
   logs、evidence、action、review 或 snapshot。
2. 不修改 AI Flow 的路径生成、脱敏、schema、Policy、验证或 Gate 逻辑；
   运行时路径规范化属于后续独立行为变更。
3. 不修改 `.gitattributes`，不对全仓库执行行尾重写或 renormalize。
4. 不忽略全局 `*.log`、`*.xml` 或任意 `coverage/` 目录，不隐藏治理证据。
5. 不删除空日志目录，不执行 Git GC，不调整历史分支或 worktree。

## 验收条件

1. `git check-ignore -v build/output.whl dist/package.tar.gz htmlcov/index.html .coverage.worker`
   全部命中新增的根目录规则；子目录中的同名普通路径不被过宽规则隐藏。
2. `CLAUDE.md` 不再复制 `AGENTS.md` 的六条稳定原则，但包含有效的
   `AGENTS.md` 相对链接、平台说明和启动顺序。
3. 恢复文档明确区分 tracked ledger/evidence、ignored local logs、OS-temp run
   及历史绝对路径，并要求迁移或删除经独立受治理任务和操作批准。
4. `python -m pytest tests/integration/test_agent_entry_files.py
   tests/integration/test_repository_hygiene.py -q`、`git diff --check`、
   `python -m aiflow validate TASK-0032`、最终 scope、active Policy 验证与 Gate 全部通过。
5. 业务 diff 仅限于范围中的五个现有文件和一个新测试文件；不出现新的
   机器用户名或本机绝对路径。

## 禁止动作

未经独立批准，禁止 push、merge、deploy、delete、secret export、paid external
call、package publish、Git GC、历史改写、分支/worktree 删除与任何外部写入。

## 错误行为

若忽略规则会覆盖 task-local 证据、入口缩减后无法确定权威规则、文档建议
改写历史审计记录，或实现需扩展到源码、schema、Policy、`.gitattributes`、
历史 logs 或范围外文件，必须停止实现并扩大范围后重新分类；不得通过
手工改状态、降低验证等级或删除证据绕过门禁。

## 回滚

通过后续受治理提交恢复上述业务文件即可回滚忽略规则、入口文案、恢复指南和
测试；`TASK-0032` 的事件、分类、规格和验证记录保持追加式审计，不删除、
不改写。本任务不会修改历史证据，因此无需对历史哈希做反向迁移。
