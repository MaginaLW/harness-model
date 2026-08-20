# Task 5.5 执行计划

**目标：** 用单一失效矩阵判断 classification、evidence 与三类 approval 的 fresh/stale/missing/not_applicable，并给出稳定原因和恢复命令。

**授权与绑定：** 用户要求按章节持续推进并逐章完成。本计划绑定基线提交 `f3f310bcfd052f80fe08a665a1589159219134bb`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: 状态、批准和 Gate 必须共享同一版本失效语义，不能各自以布尔快捷判断放过旧产物。
- allowed scope: `src/aiflow/freshness.py`、`src/aiflow/status_service.py`、必要的 approval/status 邻接兼容、`tests/unit/test_freshness.py`、`tests/fixtures/freshness/decision-table.json`、本计划和 Chapter 5/总体状态。
- forbidden actions: 不删除旧产物、不重新分类或验证、不改写批准、不推进状态、不实现 verify/gate CLI、不推送/合并。

## 完成边界

1. 固定 subject 后非当前任务治理变化、spec/Policy/classification input、范围和 action 目标/参数/期限/使用状态的失效矩阵。
2. 每类产物返回 fresh/stale/missing/not_applicable、稳定有序原因码与最小重新执行 argv，不泄露文件内容。
3. spec approval 不因正常实现形成新 subject 或纯当前任务 attestation 失效，但其规格、Policy 或批准基础上下文变化会失效。
4. evidence/code approval 严格绑定 current subject；CI attestation 额外绑定最新 head 且 governance-only。
5. status 只消费统一 freshness 结果，损坏文件稳定显示 stale/invalid，旧文件保留。
6. 决策表、组合排序、缺失/损坏、定向/全量回归、ruff、format、mypy、diff check 与精简双重复核通过后本地提交。
