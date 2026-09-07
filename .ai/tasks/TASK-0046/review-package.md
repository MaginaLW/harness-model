# TASK-0046 实现审核包

## 审核目标

接受 subject `41332307250675d6e5802d4a3cf2b8e086613184` 的 ASK 义务修复。
本次请求是代码接受，不重复请求已有效的规格批准，也不包含 push、merge 或其他外部动作。

## 背景

同一决策单元共同命中 ASK 与 REVIEW 时，原实现只消费最终 REVIEW route，遗漏了必要的
方向选择。项目所有者已批准最小修复规格；设计技术审查为 REV-0076，CLI 已正常批准并
begin。原有维护模式、路由优先级、权限规则、批准类型和质量门保持不变。

## 代码地图

- `src/aiflow/routing.py`：entry_requires_ask 从已校验分类读取 ASK 义务。
- `src/aiflow/classification_service.py`：分类目标状态与 ASK 丢失的降级判断。
- `src/aiflow/ask_service.py`：定位待回答单元，回答后保留规格审核。
- `src/aiflow/gate.py`：按真正需要 ASK 的单元检查新鲜回答。
- `tests/unit/test_routing.py` 与三个 classify/answer/gate 集成测试文件：相应回归。
- `docs/operations/low-intervention.md`：说明必要方向决定与日常机械步骤的边界。

## 语义变更

REVIEW+ASK 仍为 REVIEW，但先进入 WAITING_FOR_ASK，回答后进入 WAITING_FOR_SPEC_REVIEW；
回答不能代替 spec/code 批准。Gate 不接受其他单元的回答来覆盖该单元的 ASK 义务。
同级或更低路由重分类丢失 ASK 按既有降级门处理，更高路由（包括 BLOCK）保持原升级规则。
BLOCK 仍优先；纯 ASK/REVIEW 行为不变。未增加 Policy、Schema 字段或多 ASK 单元支持。

## 风险

修复会恢复此前被静默遗漏的必要方向选择，不能将它宣传为减少所有人工决定。
多余阻断由真实 CLI 升级/解决/重分类回归覆盖；遗漏审核由完整回答、规格批准、实现、
验证、代码批准和 Gate 生命周期覆盖。非法持久分类仍由现有契约拒绝且关键路径零写，
helper 不是未验证输入的 fail-closed 校验器。回滚应使用新提交，保留历史账本与证据。

## 证据

已验证：现行 V1 的 10 项必需检查全部通过；证据见 `evidence.json`，运行标识
`run-20260907T141446453478Z`，绑定上述 subject 及已冻结规格。

- 1,092 项单元测试通过；全量 1,657 项通过，覆盖率轮次同为 1,657 项通过。
- 分支覆盖口径的总覆盖率 87.98%，独立执行 85% 最低门槛检查退出码为 0。
- 相对 base `47b7de4e7a7d94d85ed93f24e0774c8ef3474ba2` 的 19 行可执行改动
  全部覆盖，diff coverage 100%，超过原有 90% 门槛。
- Ruff、format、mypy（41 个源码文件）、contract、scope、smoke、whitespace 均通过。
- 88 项定向测试通过；相对实现前全量基线新增 23 项回归。
- 两位独立 Agent 交叉审查源码/文档与对方测试，已发现的测试夹具缺口和残留参数均修正，
  修正后的整体测试与完整 V1 通过。结构化实现审查已记录为
  `reviews/REV-0077-r0001.json`，技术推荐 APPROVE，findings 为空。

复算命令（在仓库开发环境中，日志路径相对当前任务目录）：

```sh
python -m aiflow verify TASK-0046 --actor codex
python -m coverage report --data-file=.ai/tasks/TASK-0046/logs/run-20260907T141446453478Z/.coverage --fail-under=85 --precision=2 --format=total
diff-cover .ai/tasks/TASK-0046/logs/run-20260907T141446453478Z/coverage.xml --compare-branch 47b7de4e7a7d94d85ed93f24e0774c8ef3474ba2 --fail-under=90
git diff --check 47b7de4e7a7d94d85ed93f24e0774c8ef3474ba2..41332307250675d6e5802d4a3cf2b8e086613184
```

未验证：本次尚未推送或运行远端 CI，未合并/部署，也没有真实人工耗时或缺陷逃逸数据。
测试夹具中的 Gate PASS 证明批准边界，不表示本任务已获人类代码批准；本任务应在实际
代码批准后再执行 Gate。多 ASK 单元仍显式不支持，其他已列非目标不在本次交付内。

## 审核问题

- 是否接受这份已经验证的实现：恢复必要 ASK 选择，同时保留 REVIEW、BLOCK、权限和质量门？
- 是否确认本次代码接受不替代任何外部动作授权？

技术核查已由独立 Agent 完成；上述问题中的代码/风险接受仍由项目所有者决定。

## 推荐结论

APPROVE。实现符合已批准规格，完整本地验证通过，无未解决的阻断性技术发现。
这只是提交给项目所有者的代码接受建议，不自动记录人类批准或授权外部动作。
