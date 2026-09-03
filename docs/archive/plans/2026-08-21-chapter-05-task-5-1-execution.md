# Task 5.1 执行计划

**目标：** 将 Policy 中 V0/V1 检查解析为稳定、无 Shell、路径受限且可在执行前判定能力完整性的验证计划。

**授权与绑定：** 用户要求按章节持续推进并逐章完成。本计划绑定基线提交 `6b0601b216d033d714cfa229a65c0d19d1ec8787`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: 验证计划会决定后续受控执行的命令、目录、超时与证据类别，必须拒绝 Shell 字符串、越界路径、未知替换和缺失必需能力，并保持 V0/V1 包含关系可审计。
- allowed scope: `src/aiflow/verification.py`、必要的 `verification_level.py`/Policy schema 邻接修正、`tests/unit/test_verification_plan.py`、`tests/fixtures/verification/plans/**`、本计划和 Chapter 5/总体状态。
- forbidden actions: 不执行计划中的测试/覆盖命令，不联网、不安装工具、不推送/合并；不得因工具缺失将必需检查计为通过或降低等级。

## 完成边界

1. 检查模型含稳定 ID、等级、argv、受限环境、cwd、timeout、required、parser、日志敏感级别和类别映射；命令永远是参数数组。
2. 仅对 Policy 允许的六个变量做一次性替换，拒绝嵌套、Shell 展开、未知变量与仓库外 cwd/run_dir。
3. 本地 run_dir 位于当前任务日志目录；CI/本地 CI 模拟必须显式传入经真实路径校验的 OS 临时目录。
4. V0 必需类别完整且顺序稳定；V1 严格包含 V0，再增加覆盖、回归、Mypy 与 diff-cover，重复命令不重复执行但保留全部类别。
5. 解析阶段检查工具、正超时、环境、parser 和输出配置；必需能力缺失产生 BLOCK，optional 缺失保留未验证。
6. 实施目录列出的路径、变量、类别、工具、coverage/diff-cover 89/90 边界测试与定向回归全部通过后本地提交。
