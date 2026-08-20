# Task 5.6 执行计划

**目标：** 实现 `aiflow verify`，编排已有验证计划、受控执行器、Git 绑定与 evidence 服务，完成本地状态生命周期和只读 CI 重验。

**授权与绑定：** 用户要求按章节持续推进并逐块提交。本计划绑定基线提交 `d344b05dcee1124f2d0ac70f22ecb724b0930471`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: verify 会运行外部检查、生成 evidence 并推进任务状态，必须完整复用前序确定性服务。
- allowed scope: `src/aiflow/verification_service.py`、`src/aiflow/cli.py`、`src/aiflow/state.py`、必要的 verification/evidence/task-service 邻接兼容、`tests/integration/test_verify_command.py`、本计划和 Chapter 5/总体状态。
- forbidden actions: 不实现 Gate、不执行真实外部业务动作、不推送/合并/部署、不降低 route 或验证等级、不让 CI 修改仓库任务文件。

## 完成边界

1. 本地 verify 仅从允许状态进入 VERIFYING；过期 classification/spec/批准在运行检查前拒绝。
2. 顺序执行完整计划并保存每项结果；必需项失败仍收集其余静态检查诊断。
3. passed/failed/provisional 分别推进到目录定义状态，evidence 写失败不能留下通过状态。
4. `--check` 只能生成 provisional；完整 passed 才能满足后续 Gate。
5. CI 要求受限 temp run dir/output，写外部 evidence 且不修改任务、事件和仓库内 evidence。
6. AUTO/ASK/REVIEW、失败、超时、重跑、版本过期、CI 只读与写失败测试，以及全量回归、ruff、format、mypy、diff check 和精简复核通过后提交。
