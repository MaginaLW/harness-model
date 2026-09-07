# 精确范围与当前事实的最终补记

在 scope-resolution.md 之后进一步核实 shared fixture 的实际消费者，移除无需修改的
contract、Gate/status、begin、AUTO preflight、verify 测试路径；它们仍随完整 V1 运行。
只增加未知动作与既有审计/Hook/CLI/CI 语义相关的两份 observation 回归文件。
旧 contracts valid/invalid fixtures 不修改，继续作为历史格式兼容证据。

四个 examples/scenarios 输入会被真实 golden classification 调用，因此明确列出各自
input.yaml，而不通过测试 helper 静默补默认值。没有新增目录 glob。

另发现当前 hooks.md 的“All wrappers fail closed”与未知动作默认允许的源码冲突。
该当前事实说明按维护模式独立修正文档并验证，不实现 TASK-0047 的默认拒绝行为；文档
明确把待批方案与当前代码分开，不借本任务未来 Gate 证明当前实现。其文件处于已声明
范围，CLI 可以正常同步实际提交后的 subject，无须手工改绑定或添加虚构业务改动。

初稿治理提交导致 HEAD 已超过旧 subject，而 classify 要求二者精确相同；sync 在仅有
本 task 账本提交时不会推进 subject。该拒绝是机械恢复问题，已保留失败事实；不得把它
交给用户重复批准、删历史提交或手改 subject。本次在上述真实文档工作提交后按 CLI
同步，再追加当前 subject 对应的 resolution 并重分类。

本补记不更改前一份已引用证据；所有者对精确配套范围的例外仍未批准，不开始实现。
