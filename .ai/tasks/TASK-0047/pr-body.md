## 变更

- 新分类要求显式风险类别与受控动作；缺项为 Agent 可修复的零写输入错误，不自动转成人审。
- 保留历史读取、受控动作与旧部署/生产删除正向风险；pending 恢复和 begin 重核分类新鲜度。
- 本地动作类别只允许 Policy 明列的 read；未知动作默认拒绝，六项高风险仍拒绝，不消费通用批准或执行外部命令。
- Policy 一次升至 2.3.0；同步精确测试、四个场景输入及操作文档，保留真实 clean-clone/install/Gate 拒绝链路。
- 附带独立提交的低干预效果观察与维护盘点，不引入新填报或后台采集。

## 验证与审核

- 本地正式 V1 10 项 required check 全通过；两轮完整测试各 1721 passed，0 failed/skip/timeout。
- 含分支总覆盖率 88.14%，36 行可执行差异覆盖率 100%；Ruff、format、mypy、whitespace、contract、scope 全通过。
- 提交态 clean-clone 4 passed；独立交叉实施审查 REV-0082 通过，所有者已批准规格与代码，本地 TASK-0047 Gate PASS。
- 旧失败 run 与诊断限制保留，未把未提交树诊断伪称安装后验证通过。
- [当前代码审核包](https://github.com/MaginaLW/harness-model/blob/fb79a39cdbd4be61a68e1f3d9ef78b462e805b3e/.ai/tasks/TASK-0047/review-package.md#当前代码审核包正式-v1-通过后追加)
- 本 PR 仍须远端 required ai-quality-gate 对精确 head 成功后才可合并；本地证据不代替远端 CI。
- 当前维护模式的 CI 执行完整质量门，不选择 TASK-0047 或运行远端 task Gate；任务绑定的 Gate 已在本地独立核对。

## 边界

不放宽维护模式、main 保护、质量阈值、ASK 义务或 spec/code/action 批准绑定。不声称已实测人工成本下降，也不声称存在可信外部执行器。
本次外部交付已有单独授权；正常推送、创建 PR 并在必需 CI 成功后正常合并，不删除分支、不部署、不绕过保护。
合并后仅以一次账本 PR 发布 CLI close 的真实合并记录，仍通过其自身 required CI；不递归创建关闭 PR，不新增实现。
