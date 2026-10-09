# Task Specification

## 目标

在不改变任何 CLI、Policy、契约、证据或 Gate 行为的前提下，删除 `src/aiflow` 中无需求的复杂度：把 YAML 解码缓存的派发守卫换成标准库最小实现，把仅测试使用的场景运行器移出产品包，删除生产代码中写死历史任务 ID 的选择器和无调用方的死代码，并让 V0 检查清单只保留一份定义。

## 范围

- `src/aiflow/document_parsing.py`：保留 `load_yaml_text(text)` 接口与“调用方拿到独立对象”的语义；删除 `_DispatchGuard`、字节码/派发识别和图遍历，改为标准库最小实现：按文本内容键的有界缓存（最多 64 条，超过 16384 字符的文本绕过缓存），每次调用（含首次）返回 `deepcopy`，解析异常原样抛出且不缓存，线程安全；运行时修改 PyYAML 后缓存可能返回旧结果，这一限制写入 docstring（无生产或测试代码这样做）。
- `src/aiflow/scenarios.py`：移到 `tests/` 下的测试支持模块，更新 `tests/e2e/scenario_support.py` 与 `tests/integration/test_scenario_runner.py` 的导入。
- `src/aiflow/mutation_evidence.py`：删除只被测试调用、按历史 TASK-0014 选择生产模式的 `_task0014_production_subject`；相关测试只保留合成（mock）路径。
- `src/aiflow/errors.py`（`VerificationError`、`GateError`）、`src/aiflow/scope.py`（`_nul_paths`）、`src/aiflow/workflow.py`（`check_preconditions`）：删除无调用方的定义。
- `src/aiflow/verification_level.py`：V0 必需检查改为引用 `aiflow.verification.V0_CHECK_IDS`，不再重复定义。
- `tests/**`：删除只测试被删实现细节的用例（如派发守卫与解析器变更绕过、TASK-0014 生产模式选择），保留独立结果、别名、集合、日期、环、不缓存错误、大小/LRU 上限与并发调用等语义测试；场景运行器移至 `tests/e2e/scenario_runner.py`。
- `.ai/tasks/<本任务>/**`。

## 非目标

- 不修改 CLI 子命令（保留 `sync`：Policy 变化后的恢复流程需要它）、Policy、schemas、mutation manifest 及其目标符号（`policy._validate_cross_file`、`verifier_service.validate_verifier_actor`、`approval._v2_evidence_current`、`gate._v2_gate_facts`、`evidence.validate_v2_snapshot`）。
- 不合并 observation/verification 等模块，不统一各模块的 git、进程树或时间戳工具函数（跨模块改动多、与在途分支冲突成本高，收益有限）。
- 不改写历史任务记录与证据；不执行 push、merge、deploy、delete 或任何外部动作。

## 验收条件

- `python -m aiflow --help` 输出的子命令集合不变；`git grep -n "aiflow.scenarios\|_task0014_production_subject\|_DispatchGuard" -- src tests tools` 无结果。
- `src/aiflow` 总行数减少至少 900 行。
- 改前改后各计时一次 `python -m pytest tests/unit/test_policy.py tests/integration/test_classify_command.py -q`（重度读取 YAML 的用例），改后不超过改前 +10%；AI Flow verify 的完整 pytest 执行仍在 1200 秒预算内并记录耗时。场景运行器移出后不再计入覆盖率源，总覆盖率仍需 ≥85%。
- 完整质量检查通过：全量 pytest 带 `--cov-fail-under=85`、diff coverage ≥90%、ruff check/format、mypy、`git diff --check`；AI Flow `verify` 与 `gate` 按 CLI 结论通过。

## 禁止动作

push、merge、deploy、delete、secret_export、paid_external_call；不修改其他任务目录。

## 错误行为

- YAML 解析错误必须原样抛出（不缓存失败），调用方修改返回值不得影响后续读取结果。
- 若发现被删函数在生产路径存在调用方，停止并升级，而不是保留兼容分支。

## 回滚

`git revert` 本任务实现提交即可恢复；历史证据不受影响。
