# 低干预接入准备的独立交付

## 维护范围与授权

所有者要求完成可安全推进的后续工作，并确认首选候选工具为智谱 ZCode、以后逐步推广。
本次选择轻量规则试点，不为清空历史记录启动完整引擎产品化、TASK-0028 重验或阶段三/四。
八份实现与文档文件是维护模式下的 task-free 工作，提交为
`5a9681ef1ce48f92d1b96abbf377cd79a7f183dc`，基于 main `765cfcb7d801519a2d87398ec7287eedbb8ac316`。

所有者随后明确回复“授权本轮推送、PR 和通过检查后的合并”。本次只发布
`codex/adoption-readiness` 到 main 的一个 PR，不删除分支、不部署、不改变 ZCode 或其他
项目配置。push 与 merge 各自使用新的单次 action；不复用之前任何已执行动作的授权。

按既有维护交付方式，TASK-0047 仅承载本次交付动作的追加审计，其原冻结 subject 仍为
`c0b4cb62eb8754d9364433df6ba9948ffcf43fc2`，动作正文另明确绑定本次实现提交和允许的
发布元数据。该 task 仍是 MERGED，Missing 为 none；不改冻结输入或实现证据，不重开，
不重复 close，不把终态历史 approvals/evidence 的 stale 提示解释为新的代码审核请求。
本地 action 只是流程审计，不是可信身份或通用动作执行消费者。

## 已验证事实

- 独立文档与工具审查均通过。工具只读盘点固定入口；禁用 fsmonitor、lazy fetch 和传输
  协议，隔离继承 Git 环境；配置含 clean/process filter 时报告 unknown 而不执行 status。
  local/include/worktree 配置和链接/父路径边界均有回归，不将存在性说成准入或授权。
- 新工具 19 项定向测试通过；单独 branch coverage 91.79%，151 个可执行差异行覆盖
  141 行，diff coverage 93.4%。它不在原 `--cov=aiflow` 范围内，因此另做覆盖率检查，
  没有修改既有 CI 或阈值。
- 本仓根目录与子目录盘点结果一致，运行前后 Git index 哈希不变。
- 首次预提交全量运行在 clean-clone 用例失败：暂存区新增文件尚未进入 HEAD，克隆清单
  与 source index 不一致。单独重放确认该失败后停止原运行；没有修改旧测试或把失败改写
  为成功。提交上述实现后，干净克隆安装与工具组合测试 20 passed。
- 在该已提交实现上重新运行完整回归：1,740 passed，580.42 秒，Windows 核心总覆盖率
  88.12%。Ruff、format、mypy、补充工具 strict mypy 与 whitespace 均通过。
- 入口/Skill/仓库卫生测试 19 passed，契约/模板/Policy 测试 105 passed；本次交付审计
  的契约仍须再次检查，最终精确 PR head 还须通过远端完整 required CI，才能正常合并。

追加发布审计后，CLI `validate TASK-0047` 通过，契约/模板/Policy/action 回归
114 passed（12.13 秒），独立交付审查通过。原核心 coverage XML 的 diff 无新增
可执行源码行；新工具另由上述独立 93.4% diff coverage 验证，不混淆两个覆盖范围。

## 非目标与实际交付

没有安装外部引擎、接入真实 ZCode 任务、调用付费模型或收集原始会话；真实效率与缺陷
改善尚无可比证据。完整引擎跨仓库初始化、定位、事实录入和目标 CI 适配仍是条件性产品化
工作，不是轻量试点前置。说明与试点入口见[接入指南](../../../docs/operations/adoption.md)。

本次发布不降低 main 保护、完整质量检查或 85% / 90% 阈值。实际 PR、精确 CI head、
CI 结果与 merge commit 由平台事实及交付回复确认，不在发生前预写成功，不生成虚假的
action 消费 receipt，也不为发布结果再创建一轮关闭记录 PR。
