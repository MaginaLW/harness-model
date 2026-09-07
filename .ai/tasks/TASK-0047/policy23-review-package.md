# TASK-0047 当前 Policy 2.3.0 规格决定包

## 审核目标

请项目所有者批准当前冻结的修订规格，并将原先的同任务必要配套例外仅补入三份漏列测试。
这是计划内 Policy 变更后的真实新绑定与有限范围修订，不重复请求已记录的初始批准；
不包含代码批准或任何外部动作授权。

## 背景

初始“批准”已由 CLI 记录并 begin。Agent 已完成原范围内实现、独立技术复核、全量诊断和
本地检查点 `91af61c967d5001fec2c3550bb7dddd16b1c5b58`；没有推送、合并或部署。
最终 Policy 一次性从 2.2.0 升为 2.3.0 后，已完成 escalate、sync、resolve、classify、freeze。
当前为 REVIEW / V1、WAITING_FOR_SPEC_REVIEW，Missing 仅为 spec_approval。

## 代码地图

- 分类：decision-unit schema、classification_service、task template 与 hard-rules。
- 动作拒绝：permissions/schema、policy evaluator 与 pre_command；没有新增执行器。
- 启动保护：task_service 在共用前置检查校验当前分类，不改变批准绑定。
- 拟补配套：test_begin_close_commands.py、test_escalate_command.py、test_auto_preflight.py，
  均在 tests/integration 下且在本次决定前未修改。逐项边界见 [修订规格](spec.md)。

## 语义变更

新分类缺风险事实时零写拒绝，由 Agent 补齐，不新建人审；历史读取保留。
受控风险与旧正向 token 同时保留，不能靠空数组消去已知风险。
未知动作默认拒绝，read 只有 Policy 明列才允许；六项高风险仍观察后拒绝，不消费通用批准。
所有路线启动前核对当前分类，旧风险事实或 Policy 不能借旧分类继续。

本次新请求仅修复被上述已实现语义影响的三个测试文件：局部补事实、保留 BLOCK/恢复路径、
同步更早的 stale 拒绝断言；不改变共享 start/make_ready 为默认无风险，也不降低检查。

## 风险

仍有四项测试失败，不能视为最终完成。完整验证、实施审查、代码批准及 Gate 仍未完成。
覆盖率达标不抵消测试失败；不以 skip/xfail、删除测试或重写旧证据放行。
本地检查不能证明真实 shell 语义，亦不能拦截所有 GUI/客户端。服务端身份与可信外部执行器
仍未实现且不在范围；此轮无外部授权。维护模式、main 保护与所有 CI 门槛保持不变。

## 证据

- [实现诊断](implementation-diagnostics.md)：全量 1721 项中 1717 passed、4 failed，
  614.19 秒、0 skipped；四失败均落在三份拟补文件，无未知失败。
- 总覆盖率 8517/9670，即 88.08%；36 个可执行差异行全覆盖，diff coverage 100%。
- Ruff check、format、mypy、whitespace 通过。历史 TASK-0046 可读且 tracked 文件字节未变。
- 最终四 Policy 的独立复核确认：routing/verification-levels 仅改版本，所有检查、阈值和
  超时不变；风险规则和六项动作拒绝完整。当前独立设计审查
  [REV-0080](reviews/REV-0080-r0001.json) 为 APPROVE，不代替人类决定或实施审核。

当前绑定（旧 final/r2 上下文仅保留历史，不能替代）：

- Spec：`a7957fd15d0ac357cca521d2134a8649bcfa3fededfc45b4e98d1a0664fa4205`
- Policy：`d21a386779147dfad962a0fc0656bef61bc581e27f63c4789dcc06520fa10ff1`
- Design context：`ae766152f541a97e551e7cadc4520c8f1489e5a149dce68f8193474c0b7abe4d`
- 当前上下文文件：[design-review-context-policy23.json](design-review-context-policy23.json)。

这些是诊断和设计材料，不是正式 evidence.json，不存在最终 Gate PASS 或远端 CI 成功声明。

## 审核问题

是否批准上述当前冻结规格及 Policy 2.3.0 绑定，并同意仅将这三份必要测试补入本任务例外？
获批后 Agent 将修复四项测试，完成正式完整验证和实施审核；代码接受与外部交付仍按各自
真实缺项请求，不将本次规格决定扩成未来代码、推送、合并或部署授权。

## 推荐结论

技术设计建议 APPROVE。人的当前修订规格决定尚未收到，不将初始批准或技术建议转录为批准。
原配套的例外继续只适用于本任务；本修订不创设未来任务的通用豁免。
