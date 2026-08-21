# Task Specification

## 目标

将 `package_publish` 加入自动禁止动作，并用契约测试锁定该 Policy 行为。

## 范围

- `.ai/schemas/policy.schema.json`
- `.ai/policy/permissions.yaml`
- `tests/unit/test_permissions_policy.py`
- `tests/integration/test_templates_and_policy.py`
- `tests/integration/test_start_command.py`

## 非目标

- 不实现包发布、不修改发布凭据、不改变其他 Policy 规则。

## 验收条件

- Policy schema 有效且 `package_publish` 位于 `forbidden_automatic_actions`。
- V1、独立代码审核和 Gate 通过。

## 禁止动作

- 不得发布包、push、merge、deploy 或访问凭据。

## 错误行为

- 缺 spec/code approval 或 Policy 变化后未重新分类时必须拒绝。

## 回滚

通过后续本地提交移除新增规则和对应测试；不自动执行回滚。
