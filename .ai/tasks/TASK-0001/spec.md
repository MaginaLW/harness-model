# Task Specification

## 目标

新增一页可验证的 evidence 失效示例，说明规格、Policy 或 subject 变化后应重新验证。

## 范围

- 仅新增 `docs/operations/evidence-expiry-example.md`。

## 非目标

- 不修改 Policy、代码、CI 或其他文档。

## 验收条件

- 页面包含 spec、Policy、subject 三类失效示例。
- V0 验证和 Gate 通过。

## 禁止动作

- 不得 push、merge、deploy、删除文件或执行外部动作。

## 错误行为

- 若分类不是 AUTO 或范围扩大，停止并重新设计试点。

## 回滚

通过一个后续本地提交删除新增页面；本试点不自动执行回滚。
