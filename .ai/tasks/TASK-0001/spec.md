# Task Specification

## 目标

由用户选择试点摘要格式，并且只生成所选格式的文件。

## 范围

- `docs/pilots/ask-pilot-summary.md`
- `docs/pilots/ask-pilot-summary.json`

## 非目标

- 不同时生成未被选择的格式。

## 验收条件

- ASK 事件保存三个完整选项和用户选择。
- 只存在所选输出，V1 与 Gate 通过。

## 禁止动作

- 不得自行替用户选择；不得 push、merge、deploy 或执行外部动作。

## 错误行为

- 未回答 ASK 时 begin 和 Gate 必须拒绝。

## 回滚

通过后续本地提交删除所选摘要；不触及其他试点。

## 已冻结决策

### DU-001

- 已选择：`OPT-01`
- 操作者：user
- 回答时间：2026-08-20T23:51:24Z
- 理由：User selected Markdown only
