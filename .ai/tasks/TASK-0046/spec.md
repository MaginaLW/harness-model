# Task Specification

## 目标

同一决策单元同时命中 ASK 与 REVIEW 规则时，仍须先取得方向选择，再进入原有 REVIEW
审核流程；不能因最终 route 为 REVIEW 而遗漏 ASK，也不能用 ASK 回答代替 spec/code 批准。

## 范围

- `src/aiflow/routing.py`：共享判定从已通过 classification 契约校验的条目中读取 ASK
  义务；`route == ASK` 仍表示需要回答，REVIEW 条目则保留 matched_rules 中的 ASK 命中。
- `src/aiflow/classification_service.py`：分类目标状态与同档/更低档重分类的 ASK 义务丢失检查。
- `src/aiflow/ask_service.py`：需要回答的单元选择及回答后的状态。
- `src/aiflow/gate.py`：按同一 ASK 义务识别未答复的单元。
- 与本行为修复不可分的回归验证：`tests/unit/test_routing.py`、
  `tests/integration/test_classify_command.py`、`test_answer_command.py`、`test_gate_command.py`。
- `docs/operations/low-intervention.md`：同步本修复的使用边界；当前任务的追加式规格、审核和证据。

独立的效果基线与维护快照文档已先按 task-free 方式提交为 `47b7de4`，不混入本任务的
治理决定。四组回归测试专门验证这一个治理行为，不纳入无关的安全测试优化。

这是对当前已确定目标的最小修复，复用既有必填 matched_rules，不另建 Policy、Schema
字段或替代路由方案。旧候选只作为代码参考，旧分支的 TASK-0042、批准和失败证据不迁入。

## 非目标

- 不改变 ROUTE_ORDER、effective_route、任何 HARD-* 或权限规则、批准类型与版本绑定。
- 不支持多个需要 ASK 的决策单元；现有 ASK_DECISION_UNIT_COUNT_UNSUPPORTED 保持。
- 不修改现有分类契约，不迁移或补写历史 matched_rules，不把非法结构当作合法旧格式。
- 不将本修复扩成风险字段必填、动作枚举、未知动作默认策略或可信执行授权方案。
- 不启动阶段三、自动观测或原始会话采集；不关闭 TASK-0028 或重开其他已否决任务。

## 验收条件

1. direction count 至少为 2、impact_categories 包含 ci 的同一单元：最终 route 保持
   REVIEW，HARD-REVIEW-CI-CD 仍命中，但任务先进入 WAITING_FOR_ASK。
2. 实际 CLI 回答后进入 WAITING_FOR_SPEC_REVIEW；未经 spec 批准不得 begin，回答本身
   不能代替 code 批准；在完整当前证据和真实所需批准齐备后 Gate 才通过。
3. 缺少该单元的 ask_answered 时，Gate 返回 GATE_ASK_UNANSWERED；其他单元的回答不能
   代替它。仅有一个 REVIEW+ASK 单元并另有纯 REVIEW 单元时仍按单元识别义务。
4. BLOCK 优先于 ASK；纯 REVIEW、纯 ASK 的已有流程保持。多个需要 ASK 的单元继续
   按既有明确错误拒绝，不静默挑选一个。
5. REVIEW+ASK 重分类为同档或更低档且不再命中 ASK 时，判为降级并服从既有拒绝门；
   升到更高 route（包括 BLOCK）仍按原有升级处理，不新增“永远携带旧 ASK”的规则。
6. malformed/missing matched_rules 的持久分类文件由既有契约校验拒绝，关键失败路径
   不写任务；共享判定不宣传对未校验输入的兼容回退等同 fail-closed。
7. 完整现行 V1 检查、全量测试、总覆盖率至少 85%、diff coverage 至少 90%、Ruff、
   format、mypy、whitespace 和最终 Gate 全部通过；另进行独立技术审查。

V1 已运行整套 pytest（含现有 CLI 集成测试）；本次不声明新的 V2 专属验收、定向变异或
独立 Verifier 协议需求，不因测试文件位于 integration 目录便另外制造一次 V2 流程。
风险为中等：分类、答复与 Gate 跨模块交互，可能产生多余阻断或遗漏必要方向选择。
由 CLI 根据上述事实确定 route/V；若实施中发现额外风险或验证不足，应按原规则升级。

## 禁止动作

push、merge、deploy、delete、secret_export、paid_external_call。此前 PR #31/#32 的外部
交付授权已经完成，不视为对本次新实现的推送/合并授权。不得降低 CI 或审核门槛。

## 错误行为

分类文件不满足现行契约时拒绝；没有 ASK 义务时 answer 继续拒绝；状态、选项、单元或
版本绑定错误时沿用现有拒绝。保留 BLOCK 优先级及重分类降级门，不手改状态来消除失败。

## 回滚

以新的 Git 回退提交撤销本任务源码、必要回归测试及使用说明；保留任务记录、批准、
事件、审核和证据。回滚不删除历史记录；如涉及外部提交发布，另行取得该动作授权。
