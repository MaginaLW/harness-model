# pytest 临时根选项已移除

`aiflow verify --pytest-temp-root` 及其专用目录守卫、计划字段和测试已在 TASK-0076 中移除。
当前 `verify` 使用默认临时目录行为；完整测试、验证预算、证据绑定与质量门禁仍按 active Policy 执行。
手工 coverage 重放继续将数据库和 XML 写入独立 run directory，见 [Quickstart](quickstart.md#阶段二基线重放)。

退役前的源码、测试与用法保存在 Git 提交
`d690dbf699ddfc41c7ab0cf3267dba5dd7762912` 中。若需恢复选项，以该历史版本为来源，
按当前 AI Flow 流程重新评审有界恢复变更并完成验证；不改写历史 evidence、日志或失败记录，
不清理旧运行目录。恢复前不再使用旧选项。
