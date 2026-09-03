# Task 3.1 执行计划

**目标：** 实现四份固定 Policy 的安全加载、Schema/跨文件校验和规范化 SHA-256 摘要。

**授权与绑定：** 用户要求继续下一章并按大块提交。本计划绑定基线提交 `05da404dbfd2e97dd4718f59bb002528b4af3e4b`、实施目录摘要 `e531d7b9be3c64d1a8d261a146d76ef2ba96a5f22c3206ebed4ded1ffd39ef7a` 与 MVP 设计摘要 `62db47d72b347c52f5b5ffdbb75e67053e1ea66e9df79510c152a907fae792fc`。

## AI Flow 决定

- route: `REVIEW`
- verification: `V1`
- rationale: Policy 将驱动后续确定性分类，必须拒绝不完整或矛盾集合；使用定向失败测试和全量回归，不增加额外审计层。
- allowed scope: `src/aiflow/policy.py`、`tests/unit/test_policy.py`、`tests/fixtures/policy/invalid/`、本计划及 Chapter 3/总体状态。

## 完成边界

1. 只加载四个固定文件，拒绝缺失、冲突扩展名、symlink 逃逸和读取失败。
2. safe_load 后执行 Policy Schema，再检查全局规则 ID/优先级、V0/V1 检查、权限动作和默认 REVIEW 顺序。
3. 以固定文件名和 sort_keys 规范 JSON 计算摘要；注释/换行不影响，语义值变化必影响。
4. 覆盖实施目录列出的全部成功与失败场景，通过后提交并推进 Task 3.2。
