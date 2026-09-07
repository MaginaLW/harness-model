# Policy 2.3.0 当前事实恢复

本文件用于解除 policy_changed 后的重新分类阻塞，不是人类批准、最终验证或交付就绪证明。

- 初始规格批准已经真实记录；已授权实现以本地检查点
  `91af61c967d5001fec2c3550bb7dddd16b1c5b58` 保存，CLI sync 已绑定该 subject。
- 四份最终 Policy 一次性升级到 `2.3.0`，共同 SHA-256 为
  `d21a386779147dfad962a0fc0656bef61bc581e27f63c4789dcc06520fa10ff1`。
  routing、verification-levels 仅改版本，所有验证检查、阈值及超时未变。
- 两个 DU 已按冻结规格的自用恢复方案补 `controlled_actions: []`：本次修改本地代码、
  规则与测试，不执行部署或生产数据删除；DU-002 的 authentication 风险事实保留。
- 原有允许范围内的风险输入、默认拒绝和共用 begin 新鲜度保护已实现。独立技术复核
  未发现阻断；这不是 implementation review 或人类代码批准。
- 诊断共 1721 项，1717 passed、4 failed；所有失败精确落在修订规格列出的三份漏列测试。
  它们未修改，原证据及全量结果保留在 implementation-diagnostics.md 和忽略日志目录。
  88.08% 总覆盖率、100% diff coverage 不使失败的测试变为通过。
- 修订规格只请求三份必要测试的同任务例外；任务 facts 中逐条列出拟议路径是审核准备，
  未获本修订批准前不实施这些修改。没有新增外部权限、降低 route/V 或授权 downgrade。
- 现在可按实际 Policy、输入、base 和 subject 重新分类并冻结当前规格。所有旧批准、
  审查和证据继续保留；当前设计审查与所有者规格决定必须重新绑定，不能复制旧 hash。

重新分类之后只完成审核准备并报告真实缺项；本修订获批后才能修复剩余四项和执行正式
完整 verify、实施审核、代码批准及 Gate。推送、合并与其他外部动作仍需单独授权。
