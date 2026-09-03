# Review Package

## 审核目标

裁决 subject `f6c8cb4dfd98dd1d9101f1002e3995ec9407b548` 是否可以获得 code approval：按项目所有者的明确决定重建 bootstrap 标记，使仓库进入维护模式。

## 背景

AGENTS.md 此前写明「未经项目所有者新的明确决定，不得重建标记或恢复 task-free 自举例外」。项目所有者在本次会话中作出了该明确决定，因此本任务是执行所有者决定，而非 Agent 自行放松治理。

CI 在 **base SHA** 上读取标记，而 `main` 此刻尚无标记，因此本 PR 自身仍走正式路径，并需要恰好一个可解析的任务目录——这也是本轮最后一个必须走完整 AI Flow 的变更。

## 代码地图

- `.ai/bootstrap-mode.yaml`（新增）—— 两行裸值 `mode: bootstrap_auto` 与 `status: active`。CI 用 `grep -qx` 整行精确匹配，带引号或多字段一律 fail-closed 为非 active。
- `AGENTS.md` —— 治理模式声明改写，并明确列出维护模式**不**放松的四类边界。
- `README.md` —— 「当前治理模式」段落与「开始参与」步骤同步。
- `.claude/skills/ai-flow/SKILL.md` —— `Governance activation` 小节改写。
- `tests/integration/test_agent_entry_files.py` —— 入口文件契约断言改为维护模式事实，并新增一条断言「不放松什么」。
- `CHANGELOG.md` —— Unreleased 记录模式切换。

未触及 `.github/workflows/ai-quality-gate.yml`：bootstrap 分支及其质量检查早已存在于 workflow 中，本任务只是让 base 上的标记激活它。

## 语义变更

代码、配置、CI 或行为变更不再强制创建 AI Flow task。CI 由此跳过五个正式路径步骤：PR head 分支绑定、`.ai/repository-id` 校验、`Resolve task`、`Verify and Gate`（`aiflow verify --ci` + `aiflow gate`）、以及 `ai-flow-<TASK-ID>` 诊断产物上传。

不变部分：bootstrap 路径仍执行完整 pytest（含分支覆盖率）、`--cov-fail-under=85`、`diff-cover --fail-under=90`、`git diff --check`、`ruff check`、`ruff format --check`、`mypy`；`main` 分支保护与 required check 不变；高风险动作仍须单独获批；既有任务记录与证据仍是追加式的。`src/aiflow/**` 不含任何 bootstrap 感知，CLI 保持完全可用。

## 风险

- **无法区分变更风险等级**（主要残余风险）：标记是二值的，一行文档改动与 CI 任务解析改动同样跳过账本。按历史 marker 语义，本轮四个任务全部会跳过账本，其中 TASK-0035 正是 `HARD-REVIEW-CI-CD` 要拦的类别，TASK-0036 的实现审核则抓到了全部测试都放过的忽略规则漏洞。项目所有者已知悉并选择在本变更合并后、于新模式下补写升级清单。
- **退出不对称**：CI 从 base SHA 读标记，因此将来移除标记的 PR 自身在较弱的 bootstrap 路径下被评判。该 PR 应保持简单。
- **标记格式错误导致静默失效**：判定 fail-closed，格式不符即视为非 active；既有参数化测试锁定该行为，本任务未放宽。
- **文档互相矛盾**：三处陈述由入口文件契约测试强制一致。

## 证据

已验证：

- V1 完整验证在 subject `f6c8cb4` 通过，十项必需检查全部 `passed`。
- `tests/integration/test_agent_entry_files.py` 与 `test_github_workflow.py` 共 30 项通过；bootstrap 判定契约的既有断言未改动。
- `aiflow scope TASK-0038` 通过，改动限于允许范围的六个文件。
- AGENTS.md 25 行，处于其契约测试的上限内；`CORE_PRINCIPLES` 随第 1 条改写同步更新而非删除。
- 独立测量（37 份 evidence 记录，合计 7.45 小时检查时间）：治理 CLI 调用占 0.14%，测试执行占 99.73%。本变更买到的是撰写时间与 CI 第二遍验证，而非检查本身的机器时间。
- 已核实正式路径的 `coverage_xml` 无 `--cov-fail-under`，其 parser 仅在退出码非零或 XML 缺失时判失败，`pyproject.toml` 亦无 `fail_under`；bootstrap 路径显式带 `--cov-fail-under=85` 与 `git diff --check`。故在这两项上维护模式更严。

复现命令：`python -m aiflow verify TASK-0038 --actor <ACTOR>`。

仍未验证：bootstrap 路径在本 PR 合并后的首次真实运行；本 PR 自身仍在正式路径上被评判。

## 审核问题

1. 标记是否为 CI 判定所要求的精确形式？——是，两行裸值，既有 fail-closed 测试锁定。
2. 是否降低了任何质量门槛？——否；在总覆盖率与 whitespace 两项上反而更严。
3. 三处治理陈述是否一致且无残留旧表述？——是，由测试强制。
4. 是否触及 workflow、Policy、Gate 语义或既有任务记录？——否。
5. 主要残余风险是否被明确记录？——是，且所有者已选择随后补写升级清单。

## 推荐结论

APPROVE。变更执行的是项目所有者的明确决定，范围受控且可逆（删除一个文件即回滚），V1 十项检查全部通过，边界由测试而非仅由文字强制。主要残余风险已如实记录并有后续处置计划。
