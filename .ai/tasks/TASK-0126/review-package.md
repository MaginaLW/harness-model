# TASK-0126 审核包

## 审核目标

交付普通 wheel 与 sdist 中的版本化资源，不覆盖目标资源，不将种子视为目标授权。

## 背景

前序失败及已消费动作保留在原分支；本任务从真实实施前基线重新审核，独立测试修复先行。

## 代码地图

`setup.py` 和 `MANIFEST.in` 控制分发；`resource_bundle.py` 校验固定清单、类型、版本与摘要；`pyproject.toml` 和锁文件提供明确构建依赖。

## 语义变更

普通 wheel 分发 15 份 Schema、四份待目标审核的 Policy 种子及规格模板；可编辑安装不提供内置资源。运行时仍读取目标自身资源。

## 风险

摘要不认证发行者；资源读取与构建守卫不构成任意并发文件系统修改的沙箱。初始化、目标 Node 验证、外仓 V2 和 CI 尚属后续范围。

## 证据

已验证：权威记录为 `reviews/REV-0001-r0001.json`、`reviews/REV-0002-r0001.json` 与已完成 finalization 的 `evidence.json`。4220 项测试、14 项 required checks 和五项当前 native 合同变异通过；core 90%、analysis 98%、本次资源 diff coverage 96.7%。含本机路径的原始日志留在忽略目录。

未验证：本次远端 required CI、实际推送与合并尚待执行；本任务不证明初始化或真实目标已接入。

## 审核问题

资源完整性、非覆盖边界、当前版本绑定和现有质量门是否完整保留，且未把资源交付称作完整 agent-bridge 接入？

## 推荐结论

依据当前独立实现审核 APPROVE 和原生 V2 通过，记录 code 批准并运行 Gate；远端 required check 通过后才按常设授权合并。
