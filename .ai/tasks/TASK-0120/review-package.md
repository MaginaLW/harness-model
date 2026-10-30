# TASK-0120 审核包

## 审核目标

确认新任务及证据的已知路径有限脱敏，同时保留执行语义、既有敏感值处理和历史记录。

## 背景

所有者已授权解决公开交付的路径隐私阻碍；旧任务的禁令、记录和日志保持原状。

## 代码地图

当前 subject 修改 `src/aiflow/task_service.py`、`src/aiflow/process_runner.py` 和 `src/aiflow/verification_service.py`；测试先行和用法说明位于独立基线提交。

## 语义变更

新任务不再写入可选创建机器路径；新证据对已知解释器、仓库根、运行目录和 CI 复现路径使用占位符。实际执行参数、环境、超时及原有敏感值脱敏保持不变。

## 风险

替换仅覆盖已知路径，不承诺匿名化未知路径或原始日志。旧账本和日志可能含本机路径；外部动作仍须满足任务禁令、Policy、Hook、精确授权和目标仓规则。

## 证据

已验证：`reviews/REV-0001-r0001.json` 是独立设计审核，`reviews/REV-0002-r0001.json` 是当前 subject 的独立实现审核。`evidence.json` 记录 V1 十项必需检查通过；同一次 pytest 为 4029 passed、146 项因基线未实现 resource bundle 而 skipped。核心及分析域总覆盖率分别为 89% 和 98%；核心 diff coverage 为 90%，分析域变更无可计覆盖行。

V1 使用目标 checkout 自身的 CLI、隔离 guest 和本地镜像；独立校验的 setuptools 84.2.1 不属于 uv.lock。guest 可写的镜像日志不是隔离的独立证明。

未验证：目标仓 required CI 与具体外部动作结果。原始运行日志未承诺匿名化，不作为公开材料。

## 审核问题

- 新证据是否仅替换展示路径，并保留真实执行和旧记录语义？
- 验证是否绑定当前 subject，且没有冒充目标仓 CI 或通用匿名化？

## 推荐结论

APPROVE：当前独立实现审核通过；批准和 Gate 按 CLI 执行，外部动作条件另行核验。
