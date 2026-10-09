# Review Package

## 审核目标

裁决 TASK-0073 实现提交 `26e745177a26c200d427cd1d8d506a8b777dac74` 是否满足冻结规格 `662f8e515d3da1a34f29f427b415fb9fd05287908787a87947749c49f997225d`：在不改变 CLI、Policy、契约、证据或 Gate 行为的前提下删除 `src/aiflow` 中无需求的复杂度。

## 背景

架构审计发现 `document_parsing.py` 有约 460 行只为保护 64 条 YAML 缓存的派发守卫，`scenarios.py` 是只被测试使用、还反向导入 `aiflow.cli` 的产品模块，`mutation_evidence` 保留只对已合并的历史 TASK-0014 生效的生产选择器，另有若干无调用方的定义与重复的 V0 清单。设计审核 REV-0001（APPROVE_WITH_CONDITIONS，要求保留有界 deepcopy 缓存）→ 规格修订 → REV-0002（APPROVE）。

## 代码地图

- `src/aiflow/document_parsing.py`：646 行 → 41 行；`load_yaml_text` 使用按文本键的有界缓存（64 条，超过 16384 字符绕过），每次返回 `deepcopy`，异常不缓存，加锁。调用方 `policy.py`、`storage.py` 不变。
- `src/aiflow/scenarios.py` → `tests/e2e/scenario_runner.py`（内容不变）；`tests/e2e/scenario_support.py`、`tests/integration/test_scenario_runner.py` 改为从新位置导入。
- `src/aiflow/mutation_evidence.py`：删除 `_task0014_production_subject`；`tests/integration/test_mutation_runner_contract.py` 只保留合成路径，删除 4 个仅测试选择器的单元测试。
- `src/aiflow/errors.py`、`scope.py`、`workflow.py`：删除无调用方的 `VerificationError`、`GateError`、`_nul_paths`、`check_preconditions`。
- `src/aiflow/verification_level.py`：改用 `verification.V0_CHECK_IDS`（`required.issuperset(...)`）。
- `tests/unit/test_document_parsing.py`：删除派发守卫与解析器变更绕过测试，保留并补充独立结果、首次结果独立、别名、标量与集合、日期、环、深/宽图、错误不缓存、大小与 LRU、命中不重解析、并发等语义测试。

## 语义变更

- 生产行为不变：CLI 子命令集合、Policy、schemas、mutation manifest 及其目标符号均未改动。
- YAML 缓存不再检测运行时对 PyYAML 的修改；缓存命中后若有人在运行时改了 loader 配置，可能返回旧结果（docstring 已说明，生产与测试代码都不这样做）。环形或深层文档现在也会被缓存，返回值仍通过 `deepcopy` 保持独立与拓扑。
- 场景运行器不再随包发布，也不再计入覆盖率源。

## 风险

- 运行时修改 PyYAML 的旧结果风险：低，无调用路径。
- 与在途分支的合并冲突：在途分支若修改 `document_parsing.py` 或依赖 `aiflow.scenarios`，需在合并时适配。
- 覆盖率源变小：总覆盖率仍为 89%。

## 证据

- 已验证：AI Flow V1 evidence `.ai/tasks/TASK-0073/evidence.json`，subject `26e745177a26c200d427cd1d8d506a8b777dac74`，run `run-20261009T155400929841Z`，全部检查 passed；pytest 共用一次执行：`2770 passed, 1 skipped in 603.76s`（1200 秒预算内），verify 总耗时 607 秒。
- 已验证：总覆盖率 `COVERAGE_FILE=<run>/.coverage python -m coverage report --fail-under=85` → TOTAL 89%；diff coverage 100%。
- 已验证：`git diff --shortstat 61eeff3 -- src/aiflow` → 7 files changed, 16 insertions, 1052 deletions；`python -m aiflow --help` 子命令集合不变；`git grep` 已无 `aiflow.scenarios`、`_task0014_production_subject`、`_DispatchGuard`。
- 已验证：YAML 密集测试 `tests/unit/test_policy.py tests/integration/test_classify_command.py` 改前 22.9～25.4 秒，改后 21.7～23.6 秒。
- 已验证：mypy、ruff check/format、`git diff --check` 通过；`tests/unit` 与受影响集成测试 1987 passed。
- 未验证：Linux CI 上的运行；在途分支合并后的兼容性。

## 审核问题

1. 新的 `load_yaml_text` 是否在所有调用路径上保持独立返回值与原始错误语义？
2. 被删除的定义是否确实没有生产调用方，删除的测试是否只覆盖了被删实现细节？
3. 场景运行器移入测试后，e2e 与集成测试的导入方式是否稳定？
4. 是否存在规格范围外的必要改动被遗漏？

## 推荐结论

APPROVE：实现与冻结规格一致，生产行为与 CLI 不变，完整验证一次通过且耗时下降，`src/aiflow` 减少约 1040 行。
