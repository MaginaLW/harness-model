# Task 5.4 执行计划

**目标：** 把版本绑定、每项验证结果、未验证场景和总体结论汇总为契约合法且可原子替换的 `evidence.json`。

**授权与绑定：** 用户要求按章节持续推进并逐章完成。本计划绑定基线提交 `9c31952238c32afa011617bab935cc340cbecc08`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: evidence 是后续失效、批准和 Gate 的机器输入，必须完整绑定版本、保留失败/未验证事实并由唯一决策函数计算结论。
- allowed scope: `src/aiflow/evidence.py`、`.ai/templates/evidence.json`、必要的 evidence schema/contracts fixture 邻接修正、`tests/unit/test_evidence.py`、本计划和 Chapter 5/总体状态。
- forbidden actions: 不执行验证命令、不推进任务状态、不生成批准、不实现 verify/gate CLI、不删除或覆盖历史日志、不推送/合并。

## 完成边界

1. local/CI 证据完整绑定 task/DU、repo/branch/base/subject、spec/Policy/classification input、等级、工具版本、时间和复现 argv。
2. 每项检查含稳定类别、结果、退出/超时、耗时、脱敏摘要与相对日志引用；optional 缺失或无法覆盖显式进入 unverified。
3. 唯一决策函数：必需失败/超时/缺失/不可解析→failed；provisional 永不可 Gate；全部必需通过且版本完整→passed。
4. 证据先完整契约校验再原子替换；失败证据同样保存，日志引用仅指向当前 run 且不逃逸。
5. CI 额外绑定 attestation_head 和 governance-only 检查；本地不得伪装 CI 权威证据。
6. 决策表、契约、定向/全量回归、ruff、format、mypy、diff check 与精简双重复核通过后本地提交。
