# Review Package

## 审核目标

确认项目协作三条规则覆盖积极委派、按需扩展、全局额度继承和分阶段最小上下文，且不改变权限与宿主限制。

## 背景

新任务使用完整 main base 39898f30b8914402d737fab9f59bebf8d8656f53 的 app 隔离工作树和锁文件环境。原 TASK-0142 的不完整 base 失败与日志在原隔离分支保留；本任务不复用其批准。当前真实行为改变与非机械事实由 Policy2.6.0 分类 REVIEW/V1，独立设计 REV-0001 APPROVE，spec 批准依常设授权。

## 代码地图

AGENTS.md「开发与协作」三条为规范入口，docs/operations/maintenance-status.md 当前状态简记链接入口；本任务目录追加既有 CLI 账本、证据与独立审核。

## 语义变更

必要摸底后积极委派独立研究、实现、验证或审核，按收益、独立工作量与资源调整扩展。全局工作约定决定共享并发额度、主 Agent 计数及扩展审批，整棵委派树共享且遵守当前会话和宿主限制。上下文按阶段最小读取，并在阶段切换、新证据或冲突时更新假设、限制与待办。

## 风险

不在项目复制全局数字以免漂移，不宣称文档扩大实际并发能力。main 既有范围控制条款、当前治理模式以后全文保持相等；不改常设授权、Policy、CI、源码、依赖或模型边界。

## 证据

全新独立设计 APPROVE、候选独立预审无发现、git diff --check 与 main 后段/范围条款一致性检查通过。Windows V1 run-20261111T132104658352Z 共享完整 pytest 收集 6511 项，在日志进度 77% 时达到 3000 秒上限，duration_ms=3000141、RUNNER_TIMEOUT；contract、scope、Ruff、format、smoke、mypy 六项 passed，三项 pytest 投影 timeout，diff coverage 因 coverage database missing 失败。Windows 慢因仍 UNKNOWN，原始日志与失败提交保留。

用户授权准备受支持 Linux 环境后，当前同 source、Policy、锁与规格的 Ubuntu ext4 V1 run-20261111T152719013634Z 完整执行 809128ms，未超时，结果为 93 failed、6321 passed、77 skipped、20 errors。contract、scope、Ruff、format、smoke、mypy、diff coverage 七项 passed；三项 pytest 投影失败。首批共同根为原 runner 默认 PATH 先选中经 merged-usr 别名的 Git，严格无链接祖先守卫拒绝该路径；已有原始 trace 与同一真实 Git 二进制的只读路径选择复现，不将各失败数解释为独立缺陷。没有改变源码、守卫、Policy、默认路径或超时，没有把另一诊断 PATH 的成功当作正式验证。

当前正式 implementation 通过结论、code approval 与 Gate 均未获得；两轮失败 evidence、事件与各自 ignored 原始日志保留。后续只在受支持的真实标准环境满足相同守卫后正规恢复，不机械重跑。原 root staged WIP 保持。未运行真实模型、SDK 审核、native probe、压力测试或外部发布。

## 审核问题

全局共享树额度、主计数与审批是否完整继承？实际限制是否保留且不重复数字？三条规则是否覆盖按需扩展和阶段上下文更新？范围与授权后段是否不变？当前证据与 subject 是否一致？

## 推荐结论

设计已独立 APPROVE；正式实施结论由独立审核者在当前 verify 后记录，实现者不代判。
