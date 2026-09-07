# TASK-0047 两文件配套范围补充

## 审核目标

请求批准当前修订规格，仅将干净克隆测试和快速入门文档补入同任务必要配套例外。
这不是重复批准此前三份测试，不包含代码批准或任何外部动作。

## 背景

此前批准已经记录并执行：三份测试的四项失败修复，定向 56 passed，提交 `1c286be`。
正式提交态 V1 又发现独立 clean-clone 样例漏字段。前次未提交诊断克隆旧 HEAD，未验证
新实现的安装后行为；这是 Agent 的配套盘点遗漏，原失败与诊断限制均已记录。

## 代码地图

- `tests/e2e/test_clean_checkout.py`：仅为现有样例补 `controlled_actions: []`。
- `docs/operations/quickstart.md`：同一 YAML 补字段、纠正缺字段与 BLOCK 的区别，
  将当前 Policy 版本同步为 2.3.0。
- 具体边界见 [规格](spec.md) 的“提交态验证后的两文件配套修订”；两文件仍未修改。

## 语义变更

不再改变源码或 Policy；只使既有测试和文档提供新分类所需的显式事实。空数组依据该
本地文档样例不执行部署或生产数据删除，不将未知风险默认视为无风险。克隆已提交
HEAD、隔离安装、AUTO 与未实施 Gate 拒绝断言全部保留。

## 风险

当前正式验证失败，不能进入实施审核、代码批准或 Gate。不能借维护模式在当前治理
任务中绕过精确范围，也不能降低阈值、跳过测试或复制旧批准。两文件获批后仍需先提交
修复再完成正式验证；技术审查不保证尚未执行的验证通过。外部交付仍未授权。

## 证据

- [正式失败记录](implementation-diagnostics.md)：两轮均 1720 passed、1 failed，
  唯一失败为 clean-clone 样例缺 `controlled_actions`。总覆盖率 88.12%，diff 100%；
  contract、scope、Ruff、format、smoke、mypy、1115 项 unit 检查通过。失败证据原样保留。
- 全部 clone/安装包入口、e2e 新分类和活跃可执行示例已交叉核查，未发现第三个同类遗漏。
- CLI 已完成 spec_changed、resolve、classify、freeze。当前 REVIEW / V1，
  WAITING_FOR_SPEC_REVIEW，Missing 为 spec_approval；不新增人的机械操作步骤。
- Spec：`d49fde7d808e11406328e7864992bd5351dc75011656fc2b7a983d821b10006a`。
- Policy：`d21a386779147dfad962a0fc0656bef61bc581e27f63c4789dcc06520fa10ff1`，未再次变更。
- Design context：`2dbe29d0461b0382cf23687eafc10e625312a0287329600cc93d191e1dc599e0`，
  见 [当前上下文](design-review-context-clean-clone.json)。
- 独立设计审查 [REV-0081](reviews/REV-0081-r0001.json) 已绑定当前上下文并记录
  APPROVE，无阻断发现；不是人类规格批准或实施审查。

## 审核问题

是否批准当前修订规格，仅增加上述两文件的必要配套例外，由 Agent 连续完成修复、
提交态 clean-clone 检查、完整 V1 和实施审核？不含代码批准、推送、合并或部署。

## 推荐结论

建议 APPROVE 这一有界配套方案；独立技术设计记录为 REV-0081 APPROVE。
所有者尚未批准本次两文件范围，既有批准不被转录为本次决定。
