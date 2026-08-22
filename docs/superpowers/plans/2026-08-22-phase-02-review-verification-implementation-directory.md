# 阶段二审核与强化验证实施目录

状态：proposed
设计输入：`docs/superpowers/specs/2026-08-22-phase-02-review-verification-design.md`
阶段一输入：`docs/implementation/phase-02-entry-inputs.md`

## 执行原则

1. 每个任务先进入 AI Flow，再修改允许范围内的文件。
2. 行为、Policy、schema、批准或 Gate 变化默认进入 REVIEW；按当前 Policy 分类，不手工降低 route/V。
3. 每章形成独立 commit；每个行为性任务均有冻结规格、验证证据和状态更新。
4. Phase 2 先用现有 V1 建立审核能力，再以版本化兼容方式启用 V2。
5. 不执行 push、merge、deploy、publish、删除或真实高风险命令。

## Chapter 8：结构化设计审核与实现审核

### 进入条件

- 阶段一 `0.1.0` 与 12 项验收保持完成。
- 当前仓库被明确指定为首个跨模块 REVIEW 目标。
- 阶段二设计和本实施目录已提交。
- Chapter 8 行为性任务取得绑定当前 frozen spec、Policy 和 base commit 的 spec approval。

### Task 8.1：定义审核记录与发现契约

1. 为 design/implementation review 建立版本化 JSON schema 与 dataclass/domain model。
2. 定义稳定 finding ID、severity、location、evidence、status 和 resolution。
3. 设计审核绑定 spec/Policy/base；实现审核额外绑定 subject/evidence。
4. 拒绝未知字段、错阶段字段、非法结论和未关闭高严重度发现。
5. 保留现有 8 节审核包输入兼容，并添加 schema/model 单元测试。

### Task 8.2：生成最小审核上下文包

1. 从 task/spec/classification/Git facts 生成 design review context。
2. 从实际 diff、evidence 摘要和未验证项生成 implementation review context。
3. 使用 canonical JSON 计算上下文哈希，路径与敏感值只保留必要摘要。
4. 确保审核包不依赖完整实现对话即可复核。
5. 添加确定性、缺字段、篡改和跨平台路径测试。

### Task 8.3：审核发现处置与 freshness

1. 持久化 review record 和 findings，事件只追加。
2. 允许通过显式 resolution 关闭发现，不覆盖原发现。
3. 将 spec/Policy/base/subject/evidence 变化映射到对应审核失效。
4. 未关闭高严重度发现或不可接受结论阻止 approval。
5. 保留 spec、code、action approval 的现有职责边界。

### Task 8.4：提供 `aiflow review` 命令面

1. 生成 design 或 implementation 审核包。
2. 记录审核结论与发现，支持 JSON 输出和稳定 reason codes。
3. 记录发现处置并重算可批准状态。
4. CLI 只调用共享服务，不复制 schema/freshness 逻辑。
5. 增加 CLI 集成、错误输入和只读命令测试。

### Task 8.5：Chapter 8 集成与文档

1. 覆盖 design review → spec approval → implementation review → code approval 的正向路径。
2. 覆盖错阶段、陈旧版本、未关闭发现和篡改上下文的拒绝路径。
3. 更新操作文档、实施追踪和 chapter/overall 状态。
4. 运行全量质量门并执行独立代码复核。
5. 提交 Chapter 8 完成基线。

### 验证

```powershell
python -m pytest tests/unit/test_review_package.py -q
python -m pytest tests/integration -q
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m pytest --cov=aiflow --cov-branch --cov-report=term-missing --cov-fail-under=85
python -m aiflow validate <TASK_ID>
python -m aiflow scope <TASK_ID>
git diff --check
```

### 退出条件

- design 与 implementation 审核不可互换，且均有可验证版本绑定。
- 审核者无需完整实现对话即可从最小上下文复核变更。
- 未关闭高严重度发现、陈旧审核或非法结论不能形成批准。
- 现有 V0/V1 evidence 和 Gate 行为无变化。

## Chapter 9：V2 Policy、contracts 与分类

### 进入条件

Chapter 8 完成；双阶段审核已能约束 Policy 设计变更。

### 任务

- 9.1：扩展 verification Policy 为有序 V0/V1/V2，继续拒绝 V3/未知级别。
- 9.2：定义 V2 必需检查：V1 全集、acceptance、integration、targeted mutation、independent verifier。
- 9.3：增加 V2 选择事实与分类规则，route 与 V 保持独立。
- 9.4：版本化 evidence/classification contracts，保留旧 V0/V1 fixture 回放。
- 9.5：完成 Policy/schema/parity/拒绝路径测试和章节文档。

### 退出条件

- V2 只增不减且可确定解析；V3/未知值被拒绝。
- 旧 V0/V1 记录保持原语义，无静默重分类。
- Policy/spec 变化触发重新分类、冻结和批准。

## Chapter 10：独立 Verifier 与 V2 evidence/Gate

### 进入条件

Chapter 9 完成；V2 contracts 已稳定。

### 任务

- 10.1：在任务记录中定义 Implementer、Verifier、Reviewer 角色标识与职责。
- 10.2：生成 Verifier 最小上下文并计算 canonical hash。
- 10.3：`verify --actor` 在 V2 拒绝与 Implementer 相同的 actor。
- 10.4：V2 evidence 记录 actor、上下文、命令、subject 和审核引用。
- 10.5：Gate 校验独立性、freshness、双审核和同一 attestation HEAD。
- 10.6：完成成功、相同 actor、上下文篡改、陈旧 evidence 的集成/E2E 测试。

### 退出条件

- V2 可执行验证必须使用不同任务 actor，并明确“非外部身份认证”的限制。
- code approval 与本地 evidence、CI Gate 与外部 evidence 的边界未被混淆。
- V1 不被倒灌独立 Verifier 要求。

## Chapter 11：验收、集成与定向变异

### 进入条件

Chapter 10 完成；V2 evidence 能记录新增检查。

### 任务

- 11.1：增加确定性、离线 acceptance 与 integration 检查编排。
- 11.2：建立只覆盖阶段二关键保障的 mutant manifest。
- 11.3：在隔离 fixture/subprocess 中运行 mutant，不修改主工作树。
- 11.4：记录 killed/survived、目标规则、日志和未覆盖项。
- 11.5：任一 survived/missing mutant 令 V2 失败，并覆盖重放测试。

### 退出条件

- 关键保障被破坏时测试会失败的结论可重放。
- V1 不要求 mutation；未覆盖项不被“通过”文字掩盖。

## Chapter 12：运行期升级观测与完整 Hooks

### 进入条件

Chapter 11 完成；V2 失败原因和 evidence 结构可供 Hook 复用。

### 任务

- 12.1：定义范围越界、Policy/受控文件变化、高风险命令和 evidence 缺失观察事件。
- 12.2：共享核心将事件映射为 escalation/refusal，禁止自动降级。
- 12.3：实现编辑后范围检查 Hook，只提交观察事实。
- 12.4：实现明确命令形式的 pre-command 拒绝与审计记录。
- 12.5：证明 Hook、CLI、CI parity，并记录 shell/平台覆盖限制。
- 12.6：更新恢复与操作文档。

### 退出条件

- 支持范围内的越界/高风险请求在执行前被一致升级或拒绝。
- Hook 不含独立 Policy 决策表，不宣称通用安全沙箱。

## Chapter 13：自举 REVIEW 试点与阶段二基线

### 进入条件

Chapters 8–12 完成；V2、独立验证、mutation 和 Hooks 均有通过证据。

### 任务

- 13.1：冻结当前仓库跨模块 REVIEW 自举规格和允许范围。
- 13.2：在隔离本地 worktree 执行设计审核、实现和独立 V2 验证。
- 13.3：执行实现审核、code approval、CI 模拟和 Gate。
- 13.4：覆盖相同 actor、survived mutant、越界升级和陈旧审核 E2E。
- 13.5：建立阶段二验收矩阵与可重放证据索引。
- 13.6：更新状态、CHANGELOG、操作文档和阶段三输入，提交阶段二基线。

### 退出条件

- 一个真实跨模块 `REVIEW + V2` 任务完成双审核、独立验证和 CI/Gate。
- V2 evidence 在 attestation HEAD 可重放，包含验收、集成、定向变异与独立性证据。
- Hook、CLI 和 CI 对支持范围内的相同事实给出一致结论。
- 未实现 V3、模型路由、资源调度或任何未经授权的外部动作。

## 阶段二总验收

1. 六类阶段二输入均映射到实现、测试和 evidence。
2. 阶段一 V0/V1 与既有试点证据仍可验证。
3. 所有章节状态、任务 evidence、规格和 Policy 哈希一致。
4. 全量 pytest、Ruff、格式、mypy、覆盖率和 Gate 通过。
5. 失败与限制保留在 evidence 中，不以人工描述替代。
