# Task Specification

## 目标

消除 `aiflow` 核心状态评估与 Git 采集路径中的 `O(N_branches)` 冗余 Git 子进程调用及重复工作树扫描，并统一 `status_service` 与 `gate` 在策略路由漂移、仓库/范围就绪态及原生 V2 终态证据新鲜度上的判定逻辑。

## 范围

仅允许修改任务 `allowed_scope` 内的 4 个源码模块与 3 个测试文件（外加本任务账本目录 `.ai/tasks/TASK-0155/**`）：

1. `src/aiflow/git_context.py`
   - 在 `GitContext` 新增可选只读字段 `worktree_scope_paths: tuple[str, ...] | None = None`。
   - 保持 `_parse_status` 既有契约不变，新增 `_parse_status_with_scope_paths` 从既有的 `git status --porcelain=v2 -z --untracked-files=all` 输出一次解析工作树路径（对 `kind == "2"` 重命名/复制同时保留目标路径与规范化源路径），在 `collect_git_context` 中不改变既有的 4 条 `subprocess.run` Git 调用命令的前提下填充 `worktree_scope_paths`。
   - 重写 `task_numbers_in_refs(repository_root)`：通过 `for-each-ref --format=%(objectname) refs/heads refs/remotes` 去重提交 OID，再以 `git cat-file --batch` 批量读取 `<oid>^{tree}:.ai/tasks` 原始二进制树对象并解析树条目提取 `TASK_ID_PATTERN` 编号；无论分支/远端引用数量多少，最多发起 3 次 Git 子进程调用（常规非空分支集为 2 次），空引用集直接返回 `frozenset()`，子进程失败或输出损坏时以 `GIT_TASK_REFS_UNAVAILABLE` 失败关闭。
   - 在 `commits_are_ancestral` 中：当 `base_commit == subject_commit` 时单次调用 `_is_ancestor(repository_root, subject_commit, head_commit)`；当 `subject_commit == head_commit` 时单次调用 `_is_ancestor(repository_root, base_commit, subject_commit)`；其余情况保持两次检查。仍然校验提交 SHA 合法性与祖先关系，不跳过无效 SHA 拒绝。

2. `src/aiflow/scope.py`
   - 在 `collect_changed_paths` 与 `collect_verification_changed_paths` 新增可选参数 `worktree_paths: Sequence[str] | None = None`。
   - 当传入 `worktree_paths` 时，直接通过 `normalize_repository_path` 构建工作树路径集合，不再重复拉起 `git status --porcelain=v1 -z --untracked-files=all`；未传时保持 `_worktree_paths(repository_root)` 原行为。

3. `src/aiflow/gate.py`
   - **关键不变量（`MUT-V2-004`）**：完全不改动 `_v2_gate_facts` 函数实现与 AST 结构。
   - 提取并复用策略判定辅助函数 `classification_matches_policy(task, classification, policy) -> bool`（继续通过模块级 `route_task` 与 `verification_for_task` 调用，兼容单测 monkeypatch）以及 `policy_v2_checks(policy) -> list[Mapping[str, object]]`。
   - 在 `evaluate_gate` 中将 `getattr(context, "worktree_scope_paths", None)` 透传给 `collect_verification_changed_paths`。

4. `src/aiflow/status_service.py`
   - 在 `_current_facts` 中新增可选关键字参数 `context: GitContext | None = None` 与 `evidence: dict[str, Any] | None = None`（保持既有位置调用兼容）。
   - 在 `_current_facts` 中：
     - 复用已加载的 `bundle` 计算 `classification_policy_current`（当策略包有效加载且分类存在时调用 `classification_matches_policy`，策略包缺失或异常时沿用原有缺失容错以免破坏无策略目录的最小夹具测试）；
     - 仅在非 Node 策略（`not candidate`）且分类为 `V2` 时计算原生 V2 的 `V2_CODE_APPROVAL_FACTS`（存在 `evidence` 时在 `_current_facts` 内调用 `_v2_gate_facts` 并传入 `policy_v2_checks(bundle)`，确保 `summarize_task` 本身保持对 `pure_guard` 的无子进程纯粹性）；
     - 将 `getattr(context, "worktree_scope_paths", None)` 透传给 `collect_verification_changed_paths`；
     - 计算 `merge_scope_current`（已提交范围 `assess_scope(paths.committed, allowed_scope)` 与 `governance_only` 均为真）与 `merge_repository_current`（当 `context` 提供 `repository_id` 与 `branch` 时核对绑定且调用 `commits_are_ancestral`）。
   - 在 `summarize_task` 中：
     - 先读取 `evidence_value, evidence_invalid` 并传入 `_current_facts(..., context=context, evidence=evidence_value)`；
     - 同步处理原生 V2 与 Node V2 的 `V2_CODE_APPROVAL_FACTS` 及 `code_approved` 的 `next_events` 守卫；
     - 若 `current.get("classification_policy_current") is False`，将分类新鲜度投影为 `"stale"`；
     - 在 `_evidence_status` 中**先**判定 `schema_version in {"2.0", "3.2"}` 且 `verification_level == "V2"` 且 `phase == "pre_implementation_review"` 返回 `"awaiting_implementation_review_or_finalization"`，**再**在 `verification_level == "V2"` 且任一 `V2_CODE_APPROVAL_FACTS` 为 `False` 时返回 `"stale"`；
     - 在 `_approval_status` 中当 `evidence is not None` 时以 `_evidence_status(evidence, current) == "passed"` 作为 `approval_facts["evidence_current"]`，使原生 V2 `"2.0"` 在快照/检查/变异/评审漂移时同步使 `code` 批准失效；
     - 扩展 `_merge_readiness(..., repository_ready: bool = True, scope_ready: bool = True)` 并将 `merge_repository_current` 与 `merge_scope_current` 纳入 `gate_required` / `reverification_required` 判定。

5. 测试扩展边界
   - `tests/unit/test_git_context.py`：25+ 分支 `task_numbers_in_refs`（`<= 3` 次 Git 调用、含无 `.ai/tasks` 分支、共享树与失败关闭）、`worktree_scope_paths`（含 `git mv` 源与目标）、`commits_are_ancestral`（1 次短路与无效 SHA 拒绝）。
   - `tests/integration/test_status_command.py`：原生 V2 `"2.0"` `pre_implementation_review` 与篡改/失败/未杀灭场景、策略漂移使 `classification == "stale"`、工作树越界脏文件使 `APPROVED_FOR_MERGE` 的 `merge_readiness == "reverification_required"`。
   - `tests/integration/test_gate_parity.py`：端到端核对 `(status.merge_readiness == "gate_required") == gate.passed` 在干净就绪、工作树越界、策略漂移与原生 V2 `"2.0"` 篡改下的一致性。

## 非目标

- 不修改 `gate.py::_v2_gate_facts` 的实现或格式。
- 不修改 `StatusSummary` 字段名或 `merge_readiness` 枚举集合（保持 `not_applicable`、`not_ready`、`gate_required`、`reverification_required`）。
- 不修改 `agents`、`workflows`、`.ai/policy/**`、`.ai/schemas/**`、`tools/analysis/**`、历史 `.ai/tasks/**`（`TASK-0155` 除外）或任意文档。
- 不引入缓存后台进程、长驻 Git daemon 或额外第三方依赖。

## 验收条件

1. 定向测试全部通过：
   `pytest tests/unit/test_git_context.py tests/unit/test_scope.py tests/unit/test_gate.py tests/unit/test_node_v2_evidence.py tests/integration/test_status_command.py tests/integration/test_gate_parity.py tests/integration/test_mutation_manifest_contract.py -q`
2. 静态质量检查全部通过：`ruff check .`、`ruff format --check .`、`mypy src tools/analysis`、`git diff --check`。
3. 在实现提交之后执行一次完整原生 V1 验证 `aiflow verify TASK-0155 --actor verifier`，所有 V1 检查项通过且总覆盖率 `>= 85%`、diff 覆盖率 `>= 90%`。
4. 独立实现评审为 `APPROVE`，经由常设授权记录 `code` 批准并提交治理记录后，`aiflow status TASK-0155 --format json` 返回 `merge_readiness == "gate_required"` 且 `aiflow gate TASK-0155 --format json` 返回 `passed == true`（退出码 `0`）。

## 禁止动作

- 禁止执行 `deploy`、`delete`、`secret_export`、`paid_external_call`。
- 禁止修改 `allowed_scope` 之外文件或触碰根工作区/其他历史工作树。
- 禁止未经项目所有者明确许可执行 `git push` 或开启远端 PR。
- 禁止在 tracked 文件或提交信息中写入本机用户名或本机绝对路径。

## 错误行为

- `task_numbers_in_refs` 遇到 `for-each-ref` 或 `cat-file --batch` 非零退出、超时、无效对象头或损坏树对象时，必须以 `AiflowError(..., code="GIT_TASK_REFS_UNAVAILABLE")` 失败关闭，不得吞错返回空集或部分集合。
- `_parse_status_with_scope_paths` 对非法 porcelain-v2 路径、头部或重命名源路径必须继续抛出 `GIT_STATUS_INVALID` / `GIT_HEAD_UNAVAILABLE` 等契约错误。
- `classification_matches_policy` 对缺失/非法的 `classifications` 列表必须抛出 `ContractError(..., code="GATE_INPUT_INVALID")`，且 `status_service` 对任意损坏/越界/漂移条件均只向降级状态收敛（`stale` / `reverification_required`），不得自动重写账本或放行合并。

## 回滚

- 本任务位于独立分支 `codex/core-git-and-status-consolidation`（基于 Slice 1 提交 `b489233a`），未改动 `main` 或其他分支；如需回滚可直接在任务分支使用 `git revert` 还原代码或放弃未推送的工作树分支。
