# Review Package

## 审核目标

审核 TASK-0130 当前完整 Node V0/V1 与所有者批准的3000秒完整pytest预算；true base保持无Node的a050377，当前subject0ff2b79，不隐藏Node覆盖率分母。

## 背景

旧TASK-0128/0129及所有失败、已消费动作和旧批准保留，不提供本任务启动授权或当前通过。此次只完成Node V0/V1与预算变更并收尾。

## 代码地图

Node执行/材料/Job/输出/coverage与共同evidence/review/approval/Gate消费者；contracts/state/policy和Git固定查询的既有精确批次；预算位于verification.py及verification-levels.yaml。完整Scope以task.yaml为准。

## 语义变更

普通wheel提供封闭Node3.1/@1本地V0/V1。完整Native共享pytest预算从1200改为3000秒，其他timeout、85总/90diff、完整case、14checks和五项真实变异保持。Policy label2.6.0保持但canonical SHA改变；同版本不同SHA不等价，新引擎拒绝旧1200配置，升级不自动修改目标。

## 风险

可信宿主与受审引擎边界保持，不提供恶意同用户沙箱。旧PR142的89.3059percent diff coverage失败保留；新候选须取得实际平台通过。Node installedV2/CI/真实采用、真实模型和私有材料传输未交付且不属本次执行。

## 证据

已验证：当前Policy重新分类及独立design REV0002 APPROVE；预算定向103passed，Ruff/format与whitespace检查通过。完整Node净重放相对旧cfbf仅verification预算常量变化，所有原Node正反例保留。

未验证：当前source/engine的ordinary wheel两条完整生命周期、完整Native3000、正式implementation review、同verifier finalize、code批准/Gate及exact-head required CI正在等待。旧普通wheel/Native通过不能移用于当前预算实现。

## 审核问题

是否所有Node实现及预算均在真实base..subject与85/90分母？新Policy SHA是否在分类/设计/批准/材料/证据绑定中一致？所有本轮结果是否由真实新原件支持？

## 推荐结论

BLOCKED。当前完整验收尚未完成，不以旧结果或预算变更本身报告通过。
