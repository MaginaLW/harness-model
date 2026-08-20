# ASK Decision

## 决策问题

清楚描述需要用户选择的单一问题，并说明选择会改变什么。

## 选项格式

提供 2—4 个实质不同的选项；每项都使用以下字段：

- `option_id`：稳定选项 ID。
- `description`：方案说明。
- `benefit`：主要收益。
- `cost`：主要代价。
- `risk`：主要风险。
- `recommended`：布尔值，最多一个选项为 true。

## 选择记录

保存选中的 `option_id`、操作者、UTC 时间和理由，并将结果冻结到规格。
