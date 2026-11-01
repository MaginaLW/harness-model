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

已完成的新原件：ordinary wheel两条实际V0/V1链通过，独立接受SHA201576c12a3bd03207bf1a311e906844edfaf7fd1505c90ad6f25f5b9c8d7547；当前API4d5886794158908f17e595b9a1b5774c7d7a3c47b9767750980f3811c6499c41保留V0末尾负例和V1 current/pass/GatePASS。新sdist/LF-CRLF direct/rebuilt及四隔离资源API通过，独立增量SHAae355322841e152ebb1975566632807ecdad201ebb6385f1203c073c7ee7ef8d，所有四包76项ZIP内容等于本轮Node验收包。

完整Native实际失败：原件logs/run-20261101T043903736967Z/evidence.json与根evidence字节一致，SHA433bde0d4fcea8ea0a856d9985da783361dda2b73a3f5d818494912472af60f3。5674项完整跑完，6 failed、5663 passed、5个原有skip，1227.86秒；没有3000秒超时，coverage数据库/XML生成且两域85总/90diff检查通过。14项为9pass/5fail，五项逻辑检查共用实际pytest失败；五实际变异killed。seq20真实消费84c，seq21记录FAILED，动作已耗尽。六个失败均为test_node_v0_contract.py:1762直接调用旧fixture签名，缺node_policy_seed_bytes；测试性能优化的跨模块消费者遗漏，尚未执行六case后续断言。失败与旧草案004high/005medium整改原件均保留，不能采信为完整通过。

未验证：精确夹具调用修复、当前subject后续完整Native、正式implementation review、同verifier finalize、code批准/Gate及exact-head required CI尚未完成。

## 审核问题

是否所有Node实现及预算均在真实base..subject与85/90分母？新Policy SHA是否在分类/设计/批准/材料/证据绑定中一致？所有本轮结果是否由真实新原件支持？

## 推荐结论

BLOCKED。完整Native已跑完但存在六个测试调用失败；保留真实失败、修复受影响消费者并重新完成当前全部门禁，不以预算改变或覆盖率通过代替整轮通过。
