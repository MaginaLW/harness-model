# 有界复制实施草稿的线程启动边界审查

本记录是独立静态预审的追加式摘要，不是原生 ImplementationReview、
implementation result、pytest、完整 V2 或 Gate 通过。task 仍处于
IMPLEMENTING；未推送或合并，也未选择新的单次 action。

冻结规格为 992b927ce833a8fa9876c7e278d024eca7903763621ea84391c2ad4c09f6916c，
准入前 source 为 f7d598fca29b5fae710e9b8b641ed044f4923107。
尚未提交的两文件草稿实际 SHA256：

- repository_fixture.py：e88573352e0d87869ff00a5b087b8ced6dcd3d14eb320aed59b206683a1ff2cd。
- test_repository_fixture.py：965c83fe286aee6108bb2054fad3af96586207816f9eaf8a0fcccd783d65c14e。

作者实际静态记录证明 Ruff、format、compile、旧函数与完整旧测试前缀 AST、
whitespace 和 src mypy 检查通过。单独检查 fixture 的旧 object-index 错误在
原版与草稿都存在，均实际 exit1；不得将该项称为通过。新增15测试函数，
静态预计25参数用例，实际 collection 与 runtime 均未执行。

独立预审 PC-STATIC-001 阻断该草稿：真实标准 executor 先入队，再调用
Thread.start，随后才登记 pool._threads。若实际线程已启动后发生 BaseException，
该线程可能未登记，submit 也未返回 Future；仅 standard shutdown 的 join 不能
证明它已结束。现启动故障用例在真正启动前抛错，不能证明这个启动后边界。

实际 CPython3.11.9 threading.py 还显示：中断的 _wait_for_tstate_lock 可 release
并 _stop；重复 join/is_alive 单独不足以证明实际 worker 结束。这是静态证明
限制，未运行反例，也不是历史 integration 超时归因。3.13的 _handle.join
路径不同，不能仅核对3.13就宣称 CI3.11 的终态契约得到验证。

修复须在 start 前独立保留每个本次 worker 的归属，处理实际启动及未知启动
状态，排空所有实际写入并保持原异常身份与 partial。局部 owned executor 与
必要私有辅助函数属于当前规格的实现范围；私有协议未知或绑定改变必须在
目标复制前保留 serial 回退。不得改全局 Thread/Executor、用全局枚举代替
归属、假定 cancellation 停止 running copy，或新增线程期限、降低终态保证。
原4workers/256累计提交、当前输入守卫、DirEntry/copy2、DFS/postorder、
错误形状/逻辑优先级、原600与全部14检查/5mutation/覆盖阈值均保持。

private 报告位于 ${RUNTIME_ROOT}/parallel-copy-final-admission-preparation-001/
final-source-pre-review-001.json，实际 SHA256
8af446992315d1063092292352a97dd9c7be656a1f2a1495f256270c056f1ba1。
原两文件完整字节保存在 ${RUNTIME_ROOT}/parallel-copy-implementation-001/
rejected-by-independent-review-001/，各 SHA 与上述一致；作者与审查者的实际角色
分别为安全实现者、未写源码的独立静态审查者，不表示真实外部 ZCode 报告。

两套完整 warm 草稿与前置检查脚本仍未绑定、未执行。修复短案先独立审查，
再实施、统一提交与固定候选。完整 warm、fixture、原 external-review 与原
integration600 实际通过后，才可进入新的默认完整 V2；当前无此通过结论。
