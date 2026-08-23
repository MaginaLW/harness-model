# Task Specification

## 目标

完成 Chapter 11.2：建立一个受版本控制、可严格校验且只覆盖阶段二五项关键保障的 mutant manifest，为后续隔离 runner 提供确定性输入；本任务不执行 mutant、不生成 killed/survived evidence，也不改变 `targeted_mutation` 未验证和真实 live V2 失败的现状。

## 范围

1. 新增 `.ai/mutations/phase-02-critical-manifest.json` 作为跨任务、仓库级权威清单。顶层字段固定为 `schema_version`、`manifest_id`、`scope` 和 `mutations`；分别使用 `1.0`、`phase-02-critical`、`phase-02-critical-safeguards` 和非空数组，不允许额外字段。
2. 每个 mutation 仅包含 `mutation_id`、`safeguard_id`、`target`、`target_symbol`、`operator`、`expected_detector`、`expected_outcome`；不允许命令、参数、脚本、结果、日志、时间戳、commit 或动态环境字段。`target` 只能是仓库相对 `.py` 路径且不含 symbol，`target_symbol` 只能是该模块的顶层函数名，二者不得用 `::` 拼成一个字段；唯一性按每个字段分别检查。`expected_outcome` 固定为 `killed`。
3. 清单精确包含以下五项，顺序稳定，不能静默增删：
   - `MUT-V2-001` / `V2_REQUIRED_CHECK_SET`：`target` 为 `src/aiflow/policy.py`，`target_symbol` 为 `_validate_cross_file`，operator 为 `drop_targeted_mutation_required_check`，detector 为 `tests/unit/test_policy.py::test_v2_policy_requires_ordered_semantic_prefix_and_fixed_required_extras`。
   - `MUT-V2-002` / `V2_VERIFIER_INDEPENDENCE`：`target` 为 `src/aiflow/verifier_service.py`，`target_symbol` 为 `validate_verifier_actor`，operator 为 `allow_same_verifier_actor`，detector 为 `tests/integration/test_verify_command.py::test_v2_actor_rejections_happen_before_plan_or_runner`。
   - `MUT-V2-003` / `V2_CODE_APPROVAL_REQUIRES_PASSING_EVIDENCE`：`target` 为 `src/aiflow/approval.py`，`target_symbol` 为 `_v2_evidence_current`，operator 为 `allow_nonpassing_required_check`，detector 为 `tests/integration/test_mutation_manifest_contract.py::test_v2_code_approval_rejects_nonpassing_required_check`。
   - `MUT-V2-004` / `V2_GATE_REQUIRES_KILLED_MUTATIONS`：`target` 为 `src/aiflow/gate.py`，`target_symbol` 为 `_v2_gate_facts`，operator 为 `accept_non_killed_mutation`，detector 为 `tests/integration/test_mutation_manifest_contract.py::test_v2_gate_rejects_non_killed_mutation`。
   - `MUT-V2-005` / `V2_SNAPSHOT_BINDS_VERIFICATION_FACTS`：`target` 为 `src/aiflow/evidence.py`，`target_symbol` 为 `validate_v2_snapshot`，operator 为 `ignore_snapshot_mismatch`，detector 为 `tests/unit/test_evidence.py::test_v2_snapshot_rejects_mutation_of_bound_verification_facts`。
4. 新增 `.ai/schemas/mutation-manifest.schema.json`，采用 JSON Schema Draft 2020-12、`additionalProperties: false`、封闭的 operator enum、ID/path/nodeid 格式约束及上述必需字段。将 `mutation-manifest` 注册到 `src/aiflow/contracts.py` 的已知 contract 映射，不接受调用方提供任意 schema 路径。
5. 新增 `src/aiflow/mutation_manifest.py` 的只读加载与语义校验：仅从调用方给定的仓库根读取 manifest；拒绝绝对路径、反斜杠、空段、`.`、`..`、仓库逃逸、symlink 逃逸、非 `src/aiflow/*.py` 目标、`.ai/tasks/**`、`.ai/policy/**`、`tests/**` 目标、重复 mutation/safeguard/target/operator/detector，以及不存在的目标、Python symbol、pytest 文件或 test function。`src/aiflow/policy.py` 是允许的 Python 实现目标，不能与受控配置目录 `.ai/policy/**` 混淆。loader 不得根据 manifest 自动执行 detector 或修改文件。
6. 错误优先级与 reason code 固定为：文件/JSON 无法读取为 `MUTATION_MANIFEST_READ_FAILED`；JSON Schema 失败沿用 `CONTRACT_VALIDATION_FAILED`；字段重复为 `MUTATION_MANIFEST_DUPLICATE`；词法路径非法为 `MUTATION_MANIFEST_PATH_INVALID`；解析后越出仓库（包括 symlink）为 `MUTATION_MANIFEST_PATH_ESCAPE`；目标文件不存在为 `MUTATION_MANIFEST_TARGET_MISSING`；顶层 symbol 不存在为 `MUTATION_MANIFEST_SYMBOL_MISSING`；detector 文件或 test function 不存在为 `MUTATION_MANIFEST_DETECTOR_MISSING`。按此顺序只报告最先命中的语义类别，contract 自身仍可返回排序后的全部 JSON Pointer 错误。
7. 新增 `tests/unit/test_mutation_manifest.py`，覆盖 schema 正例、缺字段、额外字段、空清单、非法 operator/ID/path/nodeid、各类重复项、仓库逃逸、symlink 逃逸和不存在的目标/symbol/detector；全部使用临时目录或只读仓库输入。symlink 逃逸在 Windows 无创建权限时必须通过可注入或 monkeypatch 的路径解析边界确定性验证，不得跳过该断言。
8. 新增 `tests/integration/test_mutation_manifest_contract.py`，验证权威 manifest 恰好包含上述五项，顺序与内容稳定，所有 target/symbol/detector 均存在，且读取/校验不改变主工作树；同时增加两项直接触达 `_v2_evidence_current` 与 `_v2_gate_facts` 的正常保障测试，证明 non-passing required check 不能支持 V2 code approval、非 killed mutation 不能满足 V2 Gate。manifest loader 不调度这些 detector，测试也不应用任何 mutant。
9. 更新 `docs/implementation/chapter-11-acceptance-integration-mutation.md`、`docs/superpowers/state/chapters/chapter-11.yaml` 和 `docs/superpowers/state/overall.yaml`：仅将 11.2 标为 completed，指针移至 11.3；累计计数变为 65/62 tasks、348/333 steps、18/16 exits。11.3–11.5、两个 Chapter 11 exit checks 和 live mutation evidence 继续 pending。
10. TASK-0012 按 `REVIEW + V1` 自举验证。`verification_requirements` 四项保持 false，因为本任务只建立 manifest，尚无 11.3 runner 与 11.4/11.5 evidence/Gate 闭环；这不是验证降级，也不构成 V2 passed。

## 非目标

- 不实现 Chapter 11.3 的 subprocess、fixture/worktree 隔离、源码变异或由 manifest runner 调度 detector；普通 pytest 回归仍会执行这些测试函数。
- 不实现 Chapter 11.4 的 killed/survived/unverified 结果、日志、预算、运行时间或 evidence 写入。
- 不实现 Chapter 11.5 的 survived/missing 失败接线、finalize、approval 或 Gate 重放变化。
- 不修改 `.ai/schemas/evidence.schema.json`、active Policy、`verification_service.py` 的 `chapter-11-pending` 占位、现有 V2 conclusion、approval、Gate、Verifier 或 V0/V1 语义。
- 不建立通用 mutation-testing 框架，不接受自由文本 transform、shell 命令、插件、网络服务或任意仓库文件作为 mutation target。
- 不实现 Chapter 12 Hooks、Chapter 13 自举、V3、模型路由或资源调度。

## 验收条件

1. `mutation-manifest` contract 对权威清单通过；缺失/额外字段、未知 operator、无效格式或空 mutations 以稳定、JSON Pointer 定位的 contract 错误拒绝。
2. loader 返回不可变、规范化且顺序稳定的五项声明；`target` 与 `target_symbol` 分离，重复 mutation ID、safeguard ID、target、operator 或 detector 以 `MUTATION_MANIFEST_DUPLICATE` 拒绝。
3. 任一 target 为绝对路径、包含反斜杠/`.`/`..`/空段、逃逸仓库、经 symlink 逃逸、位于 `tests/**`、`.ai/policy/**` 或 `.ai/tasks/**`，或不是 `src/aiflow/*.py` 时，在任何执行或写入前按冻结 reason code 拒绝；`src/aiflow/policy.py` 必须作为合法实现目标通过。
4. 五个 target 文件、target symbol、detector 文件和 detector test function 在当前 subject 上都存在；不存在或格式不符时明确失败，不做模糊匹配或自动修复。
5. loader 与 contract 集成不根据 manifest 调度 detector，不运行 mutant、不启动 shell、不访问网络、不修改主工作树业务文件，也不产出 mutation 结果或日志；普通 pytest 可以直接执行冻结的 detector 测试以证明未变异保障成立。
6. 当前 `tests/integration/test_verify_command.py` 的 live V2 pending-mutation 场景继续证明 `targeted_mutation` 为 `unverified`、reason 为 `VERIFICATION_CHAPTER11_NOT_IMPLEMENTED`、manifest ref 为 `chapter-11-pending` 且 conclusion 为 failed。
7. V0/V1、V2 Policy/evidence/review/approval/Gate 既有回归保持不变；active Policy 继续为 `2.1.0`，本任务不产生 Policy change。
8. `uv run aiflow validate TASK-0012`、`uv run aiflow scope TASK-0012`、定向测试、Ruff、format、mypy、全量 pytest、branch coverage、Python diff coverage不低于 90% 和 `git diff --check` 全部通过，并完成独立 implementation review。
9. Chapter 11 与 overall 状态只记录 11.2 完成及 TASK-0012 的可重放 V1 evidence；不得将 manifest 存在写成 mutation executed、killed 或 live V2 passed。

## 禁止动作

- 禁止 push、merge、deploy、delete、凭据导出和付费外部调用。
- 禁止由 manifest loader/runner 执行任何 mutant、调度 detector 或接受自由形式命令，禁止修改主工作树中的 mutation target；普通 V1 pytest 回归执行冻结 detector 测试不属于该禁止项。
- 禁止伪造 killed/survived evidence、日志、V2 passed、finalize、code approval 或 Gate passed。
- 禁止扩大五项 safeguard 集合、allowed scope、route 或验证语义而不重新分类、冻结、设计审核和批准。
- 禁止降低 review、approval、freshness、scope 或验证门。

## 错误行为

- schema、语义唯一性、安全路径、文件/symbol/detector 存在性任一不满足时，manifest 加载必须失败并返回稳定 reason code，不得返回部分清单。
- 清单含结果、日志、命令、时间戳、commit、动态环境或未知字段时必须拒绝。
- 权威清单不是精确五项、顺序或字段漂移、target/detector 不再存在时，集成测试必须失败，不得将缺失项视为跳过或 passed。
- 若实现需要运行 subprocess、写临时变异文件、修改 `verification_service.py`/evidence/approval/Gate/Policy，必须停止并把工作升级到对应 11.3–11.5 的新任务；不得在 TASK-0012 内隐式扩展。
- spec、Policy、subject 或 review 绑定陈旧时，后续 begin/verify/approval 必须按 AI Flow 拒绝。

## 回滚

所有变更均为本地版本化 JSON、schema、Python、测试、文档和状态投影，可通过后续反向提交整体回滚。回滚必须同时移除 manifest contract/loader、权威清单及其测试，并把 Chapter 11/overall 恢复到 11.2 pending、61/65 tasks、328/348 steps；不得只删除清单而留下“11.2 已完成”的状态。任何 push、merge、deploy 或 task close 均不在本任务授权内。
