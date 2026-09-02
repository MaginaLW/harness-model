# Review Package

## 审核目标

裁决 subject `4d2f548b12421b5ac430fcd4d40a63273ad0ce98` 是否可以获得 code approval：在当前 `main` 上重做仓库卫生收敛。

## 背景

TASK-0032 完成过同一份内容，但其记录绑定 base `5f52afe`，而 `main` 已前移到 `55fd5a5`。AI Flow 没有受支持的方式移动任务的 `base_commit`（`start --recover` 只补完中断的创建），因此其证据无法在当前 main 上复用。项目所有者选择在当前 main 上重做，TASK-0032 的记录作为历史保留、不被修改。

原任务把四项 V2 要求全部断言为 `true`，那是阶段二「自举 REVIEW 试点」为演练 V2 所做的选择，该目的已随阶段二完成。本任务按内容实情断言为 `false`，等级 V1；该差异由项目所有者在本次收尾中明确确认，属于记录在案的所有者决定，而非 Agent 自行降级。

## 代码地图

- `.gitignore` — 新增四条根级锚定规则：`/.coverage.*`、`/build/`、`/dist/`、`/htmlcov/`。既有 `/.ai/tasks/*/logs/` 保持为唯一的 task-local 忽略规则。
- `CLAUDE.md` — 收敛为链接 AGENTS.md 的 Claude 适配入口，不再复制共享治理规则。
- `README.md` — 文档地图更新为 AGENTS.md 与 CLAUDE.md 的新分工。
- `docs/operations/recovery.md` — 新增「运行时证据、精确清理与路径边界」小节；TASK-0034 的 REC-11 与既有 REC-09/REC-10 均保持不变。
- `tests/integration/test_agent_entry_files.py` — 扩展入口文件契约覆盖。
- `tests/integration/test_repository_hygiene.py` — 新增，覆盖忽略规则契约。
- `CHANGELOG.md` — Unreleased 记录本次收敛。

## 语义变更

生成物在仓库根被明确忽略，而嵌套同名路径不受影响；`.ai/tasks/**` 下的审计账本在任何情况下都必须保持对 git 可见。Agent 规则的唯一权威从「AGENTS.md 与 CLAUDE.md 各自表述」收敛为「AGENTS.md 唯一权威 + CLAUDE.md 受测适配入口」。运行期证据的保留、有界清理与历史绝对路径例外从口头约定变为文档约定。

不变部分：`src/aiflow/**` 的任何运行期行为、Policy、证据 schema、Gate 语义、CI 配置、`.gitattributes`，以及所有既有任务的记录。

## 风险

- **忽略规则遮蔽审计证据**（本次审核的主要发现）：宽扩展名规则或窄路径规则都可能隐藏账本。已由两条互补守卫覆盖，并在临时仓库中验证守卫确实会失败。
- **入口文件规则丢失**：CLAUDE.md 收敛可能丢掉原有治理条款。已对照 `git show 668c8a0:CLAUDE.md`、新 CLAUDE.md 与 AGENTS.md 三方核对，无条款丢失，链接由测试强制。
- **与已合入内容冲突**：recovery.md 同时被 TASK-0034 改过。合并后 REC-09/REC-10/REC-11 与 `## REC-NN ` 标题集合断言均保持成立。
- **重做导致范围漂移**：`aiflow scope` 通过，改动严格限于 allowed_scope 的七个文件。

## 证据

已验证：

- V1 完整验证在 subject `4d2f548b` 通过，十项必需检查全部 `passed`（回归 354.9s、coverage 418.8s），含 85% 总覆盖率与 90% diff coverage。
- 四视角独立审核 + 对抗性证伪：11 条 finding，10 条被证伪，1 条高严重度成立并已在本 subject 修复。
- 守卫有效性在临时 git 仓库中直接验证：当前规则下账本路径可见；加入 `/.ai/tasks/*/evidence.json` 后 `evidence.json` 变为 IGNORED，新断言随即失败。
- `git check-ignore -v --no-index` 确认 `build/`、`dist/`、`htmlcov/`、`.coverage.*` 被忽略，而 `task.yaml`、`events.jsonl`、`spec.md`、`evidence.json`、`approvals.json`、`reviews/*.json`、`review-contexts/*.json` 均未被忽略。
- `aiflow scope TASK-0036` 与 `aiflow validate TASK-0036` 通过。

复现命令：`python -m aiflow verify TASK-0036 --actor <ACTOR>`。

仍未验证：忽略规则在非 Windows 检出下的行为未单独重放（CI 的 Linux 运行将覆盖）；本任务不涉及、也未验证 `.gitattributes` 对变异证据换行符的影响，该缺陷另行立项。

## 审核问题

1. 忽略规则是否可能遮蔽审计证据？——当前不会，且已加回归守卫；守卫的有效性经实证。
2. CLAUDE.md 收敛是否丢失治理条款？——否，三方核对无丢失，链接由测试强制。
3. 是否触及运行期行为、Policy、Gate、CI 或既有任务记录？——否。
4. V1 而非 V2 的等级判断是否恰当？——内容不触及定向变异清单所针对的护栏，其集成测试已含在 V1 完整回归中；该判断由项目所有者明确确认。

## 推荐结论

APPROVE。内容与冻结规格一致，范围受控且可逆，V1 十项检查全部通过；审核中发现的唯一实质缺陷已在本 subject 修复并经实证验证守卫有效。
