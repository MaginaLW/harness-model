# Task Specification

## 目标

在保留初始 BLOCK 历史的同时，只生成场景文件 dry-run 清单且不删除任何文件。

## 范围

- 仅新增 `docs/pilots/block-dry-run-inventory.md`。
- `examples/scenarios/**` 只读并核对摘要。

## 非目标

- 不执行删除，不修改任何 golden scenario。

## 验收条件

- 初始分类为 BLOCK，begin/verify/Gate 的拒绝历史必须保留。
- 恢复前后 `examples/scenarios/**` 摘要完全一致。

## 禁止动作

- 不得删除、push、merge、deploy 或执行真实外部动作。

## 错误行为

- 任何删除、范围扩张或摘要变化必须拒绝。

## 回滚

通过后续本地提交删除 inventory；场景文件始终不变。
