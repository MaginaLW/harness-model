# 提交态样例遗漏的规格恢复事实

本文件仅支撑 `spec_changed` 后的重新分类，不是人类批准或测试通过声明。

- 当前 subject 为 `1c286be3951b9083742a33fc2d111ae986d38407`，此前批准的三份测试
  修复已经提交；Policy 仍为 2.3.0，SHA-256 为
  `d21a386779147dfad962a0fc0656bef61bc581e27f63c4789dcc06520fa10ff1`。
- 正式完整 V1 两轮均为 1720 passed、1 failed，唯一失败是 clean-clone 样例缺少
  `controlled_actions`；失败 evidence 与原始日志已保留，见 implementation-diagnostics.md。
- 新规格只请求增加 `tests/e2e/test_clean_checkout.py` 与
  `docs/operations/quickstart.md` 两条精确配套路径。facts 中列入路径仅用于审核准备；
  两文件尚未修改，新规格获批后才实施。不修改源码、Policy、路由、验证级别或阈值。
- 两个 DU 的业务风险事实不变，仍为 REVIEW / V1 的治理工作；不借配套文件建立安全
  DU 或降级，不改旧批准 hash。此前三文件批准继续作为历史真实决定，而非本次批准。
- 提交态 clone/安装测试和活跃文档已交叉检查，未发现其他同类遗漏。下一步只重分类、
  冻结并取得当前独立设计审查，再请所有者决定这两文件的有界同任务例外。

外部动作、代码批准、最终验证与 Gate 仍未获放行；不自行 begin 或实施拟议范围。
