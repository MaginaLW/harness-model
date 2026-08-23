# Review Package

## 审核目标

确认 TASK-0012 在 subject `e2b6522efa2a900110b449c25f7c386f98027e12` 上完成的 Chapter 11.2 变更准确满足冻结规格：仓库拥有精确五项阶段二关键保障的版本化 mutant manifest、封闭 schema、只读且安全的 loader，以及可实际触达相应保障的 detector 绑定；本任务没有执行 mutant、生成 killed/survived evidence 或改变真实 live V2/Gate 结论。

## 背景

Chapter 11.1 已让 V2 acceptance/integration 真实、离线执行，但 `targeted_mutation` 仍以 `VERIFICATION_CHAPTER11_NOT_IMPLEMENTED` 明确未验证。Chapter 11.2 只建立后续隔离 runner 的权威声明输入，不实现 11.3–11.5。任务按 `REVIEW + V1` 自举，Policy 保持 `2.1.0`，这不是 V2 passed 或验证降级。

首次设计审查 `REV-0001` 发现 target/symbol 表达冲突、Policy 路径边界歧义，以及两个 detector 不触达目标。三项 finding 均通过 revisions 2–4 关闭；重新冻结后 `REV-0002` 在当前规格 context 上 `APPROVE` 且无 findings。

首次实现审查 `REV-0003` 发现精确五项未在 loader 强制、schema 路径可经 symlink 逃逸、公共 contract API 被扩大为任意 schema 目录，以及 JSON 重复键语义不唯一。四项 finding 均在 revisions 2–5 关闭：schema 固定五项基数、loader 锁定完整有序声明、schema 目录和文件均做 containment、公共 API 恢复固定签名，duplicate key 在 JSON 读取阶段稳定拒绝。修复已形成新 subject 并完整重跑 V1。

修复后的安全复审 `REV-0004` 进一步发现仓库内 mutation schema 损坏或不可解析时会泄出底层 JSON/schema-resolution 异常。该 finding 已在 revision 2 关闭：loader 保留正常 `ContractValidationError`，并把 schema I/O、解码、结构、规范判定和引用解析失败稳定归一为 `MUTATION_MANIFEST_READ_FAILED`；损坏 JSON 与不可解析 `$ref` 均有回归覆盖并经独立复验通过。

## 代码地图

- `.ai/mutations/phase-02-critical-manifest.json`：精确、有序的五项 mutation 声明，分别绑定 V2 必需检查、Verifier 独立性、code approval evidence、Gate killed mutation 与 snapshot 完整性。
- `.ai/schemas/mutation-manifest.schema.json`：Draft 2020-12 封闭 contract，固定五项基数、manifest 身份、字段、operator、ID、target、pytest nodeid 和 `killed` 预期。
- `src/aiflow/contracts.py`：注册 `mutation-manifest`；现有公共 validation API 继续只读固定本地 schema，repository-bound loader 仅在 containment 后使用私有 schema-directory helper。
- `src/aiflow/mutation_manifest.py`：固定 canonical path 的只读 loader；返回 frozen dataclass/tuple，拒绝 duplicate JSON key，校验重复声明、完整有序五项、词法路径、manifest/schema/target/detector 的 repository/symlink 逃逸、目标文件、顶层 AST symbol 与 detector test function。
- `tests/unit/test_mutation_manifest.py`：覆盖 contract、错误优先级、重复、非法路径、escape、缺文件/symbol/detector、不可变性与只读行为；Windows symlink 权限不足时使用解析边界 monkeypatch，不跳过该新增保障。
- `tests/integration/test_mutation_manifest_contract.py`：锁定权威五项及其顺序，验证 canonical 引用，并直接证明 `_v2_evidence_current` 拒绝 non-passing required check、`_v2_gate_facts` 拒绝非 killed mutation。
- Chapter 11 实施记录与 chapter/overall 状态：仅将 11.2 标为 completed，把指针移到 11.3，并保持 11.3–11.5、两个退出检查和 live mutation evidence pending。

## 语义变更

仓库现在可以从传入 repository root 下的固定 `.ai/mutations/phase-02-critical-manifest.json` 读取一份严格、不可变的声明对象。loader 不接受任意 manifest/schema 路径，不 import target，不执行 pytest、subprocess 或 shell，也不写业务文件或 evidence。合法 JSON 但非对象走 contract failure；duplicate JSON key 以及损坏或不可解析的 repository-owned schema 走 read failure；四项/六项、重排或字段漂移、自由字段、未知 operator、非法 ID/nodeid、重复声明、绝对/反斜杠/dot-segment target、repository 或 symlink 逃逸，以及缺失 target/symbol/detector 均按冻结优先级拒绝。

现有 Policy、V2 evidence schema、verification service、approval 和 Gate 实现没有被修改。manifest 的 detector 作为普通 V1 pytest 回归可执行，但 manifest loader 不会调度它们。`targeted_mutation` 仍为 `unverified`，manifest ref 仍为 `chapter-11-pending`，因此真实 live V2 继续 failed。

## 风险

- 路径或 symlink 逃逸可能把 schema 或后续 runner 指向仓库外；loader 对 canonical manifest、schema 目录/文件、target 和 detector 做 resolved containment 校验，且有无需 Windows symlink 权限的确定性负向测试。
- 仅存在的 nodeid 可能并不检测声明的保障；两项原先不触达 enforcement point 的 detector 已换成直接 helper 测试，其他三项绑定现有精确保障测试。
- 自由 transform 或命令字段可能把 manifest 变成执行入口；schema `additionalProperties: false` 且 operator 为五项封闭 enum，manifest 不含 argv、script、结果或日志。
- schema 从进程 cwd 读取会破坏多 checkout 确定性；loader 显式绑定调用方 repository root 下的固定 schema 目录。
- manifest 存在可能被误写为 mutation 已通过；文档、状态和测试明确 11.3–11.5 pending，live V2 继续失败。

## 证据

- subject：`e2b6522efa2a900110b449c25f7c386f98027e12`；base：`9d8a7d1dad7d256bbefaafad9ce5d4270238b4fe`。
- 冻结规格：`8b2244cc388b78eaab141a9257bc6ee1bf759f025ab97df234ddff333fd9ea36`；Policy `2.1.0`：`f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf`。
- 当前 V1 evidence SHA-256：`7c298a41637dfcac9ea0d54a26fdafa2e330f816e1e31c417447024869c7c1c5`；10 个 required checks 全部 passed。
- focused mutation-manifest suite：`43 passed`；unit：`445 passed, 2 skipped`；全量回归与 branch coverage：`736 passed, 3 skipped`。
- Python diff coverage：`96%`（130 行、4 missing），高于冻结规格的 90% 门槛；`contracts.py` 为 100%，`mutation_manifest.py` 为 96.7%。
- contract、scope、Ruff、format、smoke、mypy、coverage XML、diff coverage 与 `git diff --check` 均通过。
- 三个既有 skip 均是环境缺少真实 symlink 创建权限；TASK-0012 自身的 symlink escape 新增测试通过 monkeypatch 路径解析边界确定性执行，没有 skip。
- 未验证且未执行：任何 mutant、manifest 驱动 detector 调度、隔离 subprocess/worktree、killed/survived 日志与 evidence、survived/missing V2 replay、Chapter 11 两个退出检查，以及 push、merge、deploy、delete、凭据导出、付费调用和 task close。

## 审核问题

- manifest 是否精确限制为冻结的五项阶段二关键保障，且没有自由命令或动态执行字段？
- loader 是否只读、repository-root-bound，并在读取/执行任何目标前可靠拒绝 lexical、repository 与 symlink 逃逸？
- target 顶层 symbol 与 pytest detector 是否通过 AST 验证，两个新增 detector 是否真实触达 approval/Gate enforcement point？
- 错误码与优先级、不可变返回、schema 闭合和现有 contract API 兼容性是否满足规格？
- Chapter 11/overall 是否只宣称 11.2 完成，并继续保留 11.3–11.5、exit checks 和 live V2 失败边界？
- 是否存在任何未关闭的 high 或 critical finding，或需要扩大到 11.3–11.5 的实现？

## 推荐结论

当前 subject 的完整 V1 evidence 已通过，设计、首次实现审查及安全复审 findings 已关闭，范围和状态投影与冻结规格一致。schema 异常归一修复形成新 subject 后须重新运行完整 V1，并由新的独立实现 reviewer 对新 context 给出最终结论；该建议不授权 code approval、push、merge、deploy、close，也不代表 targeted mutation 或真实 live V2 passed。
