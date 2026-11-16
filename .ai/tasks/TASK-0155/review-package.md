# Review Package

## 审核目标

对 `TASK-0155`（分支 `codex/core-git-and-status-consolidation`，基线 `b489233a26c31e193929c5d1973eae36571ba058`，当前待审实现提交 `86f3c053afe051fae39e4372a18bf458a0236e5d`）进行 `implementation` 阶段独立审核，裁决实现是否满足 `.ai/tasks/TASK-0155/spec.md` 与 `V1` 验收条件，能否进入常设授权 `code` 批准及 `APPROVED_FOR_MERGE`。

## 背景

在项目瘦身排查中发现两个核心瓶颈与状态漂移缺口：

1. `src/aiflow/git_context.py` 的 `task_numbers_in_refs` 按每个本地/远端分支逐一执行 `git ls-tree`，呈 `O(N_branches)` 子进程增长；同时 `collect_changed_paths` / `collect_verification_changed_paths` 与 `collect_git_context` 重复扫描工作树，`commits_are_ancestral` 在相同提交之间仍执行双次祖先查询。
2. `src/aiflow/status_service.py` 与 `src/aiflow/gate.py` 在 `classification_matches_policy` 策略漂移、`merge_repository_current` / `merge_scope_current` 就绪判定以及原生 V2（`"2.0"`）`V2_CODE_APPROVAL_FACTS` / `pre_implementation_review` / `evidence_current` 新鲜度评估上存在分裂。

本任务（Slice 2）基于 Slice 1（`b489233a`）推进，严格限定在 `allowed_scope` 指定的 4 个源码模块与 3 个测试文件内完成收敛；途中通过正式 `spec_changed` 升级链路（`REV-0002` `APPROVE`）明确保持 `StatusSummary.classification` 为产物摘要指纹新鲜度、而将 `classification_policy_current` 纳入 `_merge_readiness(..., policy_ready=...)`。

## 代码地图

| 文件 | 变更内容与职责 |
| :--- | :--- |
| `src/aiflow/git_context.py` | `GitContext.worktree_scope_paths` 字段；`_run_git` 通用超时/编码处理；`_parse_status_with_scope_paths` 单次解析 porcelain-v2 脏路径（含 `kind == "2"` 重命名源/目标）；`task_numbers_in_refs` 使用 `for-each-ref` + `git cat-file --batch` 读取原始树对象并将子进程降至 `<= 3` 次；`commits_are_ancestral` 相等提交短路优化 |
| `src/aiflow/scope.py` | `collect_changed_paths` 与 `collect_verification_changed_paths` 新增可选 `worktree_paths: Sequence[str] | None = None`，复用既有扫描结果避免重复调用 `git status` |
| `src/aiflow/gate.py` | **保持 `_v2_gate_facts` 100% 原样未动（满足 `MUT-V2-004`）**；提取 `classification_matches_policy` 与 `policy_v2_checks` 共享辅助；`evaluate_gate` 透传 `worktree_scope_paths` |
| `src/aiflow/status_service.py` | `_current_facts` 接受 `context` / `evidence` 并集中计算 `classification_policy_current`、原生 V2 `V2_CODE_APPROVAL_FACTS`（保持 `summarize_task` 通过 `pure_guard`）、`merge_scope_current` 与 `merge_repository_current`；`_evidence_status` 先判 `pre_implementation_review` 再判 V2 facts 失败；`_approval_status` 对 `evidence is not None` 使用实时 `_evidence_status == "passed"`；`_merge_readiness` 纳入 `policy_ready`、`repository_ready`、`scope_ready`；保持 `StatusSummary.classification` 绑定摘要指纹新鲜度 |
| `tests/unit/test_git_context.py` | 覆盖 25+ 分支 `<= 3` 次 Git 调用（含无任务树分支、共享树对象与损坏/失败关闭）、`git mv` 源/目标工作树路径及 `commits_are_ancestral` 单次短路与非法 SHA 拒绝 |
| `tests/integration/test_status_command.py` | 覆盖策略路由漂移保持 `classification == "fresh"` 且 `merge_readiness == "reverification_required"`、工作树越界脏文件与分支偏离、Subject/Policy 错误失败关闭、原生 V2 `"2.0"` 全生命周期及变异/快照篡改检测 |
| `tests/integration/test_gate_parity.py` | 端到端校验 `(status.merge_readiness == "gate_required") == gate.passed` 在干净就绪、工作树越界、策略漂移及原生 V2 `"2.0"` 快照篡改场景的一致性 |

## 语义变更

- **`StatusSummary.classification` 与 `merge_readiness` 语义边界**：`StatusSummary.classification` 维持 `evaluate_freshness("classification", ...)` 的产物摘要指纹新鲜度契约（不破坏既有合成夹具），同时将实时 `classification_policy_current` 接入 `_merge_readiness(policy_ready=...)`，确保任何路由漂移在 `APPROVED_FOR_MERGE` 下收敛为 `merge_readiness == "reverification_required"` 与 `missing_conditions == ("reverification",)`，与 `gate.passed` 保持 100% 一致。
- **抽象抽取三条件核验**：`classification_matches_policy` 与 `policy_v2_checks` 仅抽离 `gate.py` 与 `status_service.py` 之间表达完全一致的策略路由核对与 V2 check 读取规则，同向演进且不新增任何模式标志位。
- **容错防卫边界**：仅在不可信输入与外部 I/O 边界做失败关闭（`git cat-file --batch` 对象解析、Git 超时、策略包结构校验、损坏或越界工作树状态），策略配置缺失目录仍沿用既有最小夹具容错路径，未改变公开接口枚举。

## 风险

| 风险 | 影响 | 缓解措施 |
| :--- | :--- | :--- |
| 原生 git tree 二进制格式解析边界（跨平台换行、超长文件名、损坏条目） | 树条目误解析或异常未包装 | 严格按 `<mode> <name>\0<20-byte-oid>` 解析并验证边界，任何越界/损坏统一抛出 `GIT_TASK_REFS_UNAVAILABLE` |
| `MUT-V2-004` AST 绑定敏感性 | `gate._v2_gate_facts` 改动会触发变异契约失败 | 完全保留 `_v2_gate_facts` 实现与签名前后一致，且已由全量 pytest 中 `test_mutation_manifest_contract.py` 验证通过 |
| 策略包与 `status_service` 新增就绪条件对既有夹具的回归影响 | 既有集成夹具报错 | 保留策略包缺失容错，并保持 `classification` 绑定摘要指纹，全量 `6,527` 测试全部通过 |

## 证据

在实现提交 `86f3c053afe051fae39e4372a18bf458a0236e5d` 之后完成一次完整 `V1` 验证：

- 复现命令：`python -m aiflow verify TASK-0155 --actor verifier`（日志目录 `.ai/tasks/TASK-0155/logs/run-20261115T173014088759Z`）
- 已验证结果：`conclusion: passed`（退出码 `0`，耗时 `2,115.58s`），任务迁移至 `WAITING_FOR_FINAL_REVIEW`
- 10 项全量门禁结果：
  - `contract`、`scope`、`ruff_check`、`ruff_format_check`、`smoke`、`mypy`：全部 `passed`（`0` 警告/`0` 错误）
  - `unit_tests` / `regression_tests` / `coverage_xml`：`6527 passed, 9 skipped in 2109.85s`（9 项 skip 为固定外部 Node 夹具与 POSIX 专属路径测试）
  - `diff_coverage`（vs `b489233a`）：`core` 域 diff 覆盖率 `94%`（`163` 行未覆盖 `9` 行 >= `90%` 门禁：`gate.py` `90.9%`、`git_context.py` `95.1%`、`scope.py` `100%`、`status_service.py` `94.6%`）；总覆盖率 `core` `90% >= 85%`、`analysis` `98% >= 85%`
- 未验证场景：未执行远端 `git push` 或 CI 云端运行（按授权边界保留在本地审核通过后请求项目所有者许可）。

## 审核问题

1. **Git 批处理实现正确性**：`task_numbers_in_refs` 使用 `for-each-ref` + `cat-file --batch` 是否在空引用集、共享树对象去重、无 `.ai/tasks` 分支及损坏树对象时均行为正确且子进程数严格收敛在 `<= 3`？
2. **契约与不变量守卫**：`gate._v2_gate_facts` 是否确保持 `MUT-V2-004` 无任何改动，`summarize_task` 是否保持 `pure_guard` 纯粹性，且 `StatusSummary.classification` 与 `merge_readiness` 是否与 `evaluate_gate` 完全对齐？
3. **交付边界五项自检结论**：
   - （1）**目标与关键假设**：目标清晰，所有假设（Porcelain-v2 格式、Git tree 二进制格式、V2 终态证据模型、`classification` 摘要新鲜度语义）均已获代码核对与全量测试验证。
   - （2）**标准库与既有复用**：直接复用已有 `route_task`、`verification_for_task`、`evaluate_freshness`、`assess_scope`、`commits_are_ancestral`、`_v2_gate_facts` 与 Python 标准库（`hashlib`/`subprocess`），无重复造轮子。
   - （3）**更简直接实现**：各模块改动均在既有职责边界内最小实现，无过渡期兼容层或冗余重构；此前 `spec_changed` 已及时将过度复杂的全局投影调整为 `_merge_readiness(policy_ready=...)`。
   - （4）**新增抽象依据**：`classification_matches_policy` 与 `policy_v2_checks`、`policy_ready` 参数均源于消除 `status_service` / `gate` 语义分裂的当前需求，无推测性扩展。
   - （5）**任务范围与打断汇总**：严格只改动 `allowed_scope` 7 个文件与 `.ai/tasks/TASK-0155/**`；`S=0`、`Q=3`（公开仓 `git push`/PR、`tools/analysis/*` 去向、过期工作树/分支清理将在最终交付汇总表集中一次确认）、`U=0`、`H=2`（守住 `MUT-V2-004` 与不越权推送）。

## 推荐结论

推荐结论：**APPROVE**——所有实现严格贴合 `spec.md` 与 `allowed_scope`，无阻塞缺陷，`V1` 完整验证 `6,527 passed`、diff 覆盖率 `94%`、静态检查全绿，满足常设授权 `code` 批准及进入 `APPROVED_FOR_MERGE` 的条件。
