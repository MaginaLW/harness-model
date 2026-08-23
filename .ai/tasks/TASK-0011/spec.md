# Task Specification

## 目标

完成 Chapter 11.1：让 V2 的 `acceptance` 与 `integration` 从不可执行占位项变为由现有无 Shell 进程执行器编排的确定性、离线检查，并把各自的真实结果、日志、版本和失败原因写入 V2 pre evidence；`targeted_mutation` 仍明确未实现，因此真实 live V2 在 Chapters 11.2–11.5 完成前必须保持 failed，不能 finalize 或通过 Gate。

## 范围

1. 将 `.ai/policy/verification-levels.yaml` 中 V2 `acceptance` 命令固定为 `"{python}" -m pytest tests/acceptance -q`，`integration` 命令固定为 `"{python}" -m pytest tests/integration -q`；二者 `required: true`、`result_parser: pytest`，只使用本地仓库和已安装依赖，不访问网络或外部服务。
2. 在 `src/aiflow/verification.py` 对上述两个 check ID 增加精确输出语义校验：拒绝 `aiflow --help`、错误测试目录、错误 parser、额外 shell 形式或其他不能证明对应行为的命令。现有 allow-list、参数数组、单次占位符展开、cwd、超时和无 Shell 约束继续生效。
3. 在 `src/aiflow/verification_service.py` 令默认 V2 live run 按 Policy 顺序执行完整 V1 prefix 后的 `acceptance` 与 `integration`；`--check acceptance` 或 `--check integration` 只执行所选真实检查并保持 provisional 语义。`independent_verifier` 继续使用 Chapter 10 的角色事实，不能被当作外部身份认证。
4. V2 evidence 保留 schema `2.0` 和两阶段契约。`acceptance`、`integration` 的 `status`、`reason_code`、exit code、timeout、duration、stdout/stderr log ref、command summary 与 tool version 必须来自真实计划和进程结果，不得被后处理改写为 passed。
5. `targeted_mutation` 在本任务中不启动任何命令，继续写入 `unverified`、稳定 reason code `VERIFICATION_CHAPTER11_NOT_IMPLEMENTED`、`chapter-11-pending` manifest 和 `CHAPTER11-PENDING` 结果。该未验证项必须令 live V2 conclusion 为 failed；失败的 pre evidence 不能进入 implementation review finalization、code approval 或 Gate passed 路径。
6. 新增 `tests/acceptance/test_v2_acceptance.py` 作为离线 acceptance suite；更新/新增 unit 与 integration 测试，覆盖计划解析、真实调度、日志/版本、命令失败、超时或缺结果、selected-check 以及 pending mutation 边界。测试只能使用临时目录或受控 task log 目录，不能修改主工作树业务文件。
7. V0/V1 Policy check 定义、执行次序、evidence schema `1.0`、approval 与 Gate 语义保持不变；V2 的 schema、snapshot、review refs、Gate 和 approval 契约也不在本任务扩展。
8. 更新 README、Quickstart、Chapter 11 实施记录和状态投影：仅将 11.1 标为 completed，11.2–11.5 与两个 chapter exit checks 保持 pending；整体计数对齐为 11/10 chapters、65/61 tasks、348/328 steps、18/16 exits，并明确 live V2 仍失败。
9. TASK-0011 自身按 `REVIEW + V1` 建立本章增量实现基线。原因是本任务刻意不实现 V2 所必需的 targeted mutation，不能用不完整的 live V2 为自身产生 passed evidence；V1 全量验证和本任务定向测试必须证明新增编排行为。这不是 V2 passed 或验证要求降级。
10. 本任务会修改可执行 Policy。实现产生新 Policy 哈希后，必须记录 `policy_changed` 升级，重新分类、重新冻结、重新执行独立 design review，并取得绑定新 Policy 的 fresh spec approval，之后才能继续最终验证。

## 非目标

- 不实现 Chapter 11.2–11.5 的 mutant manifest、隔离 mutant runner、killed/survived 结果、预算或 replay Gate。
- 不修改 evidence/schema/template、Gate、approval、review、Verifier context 或 actor 独立性契约。
- 不把 `pytest -q`、`aiflow --help`、自然语言确认或 fixture-only passed path 当作 acceptance/integration 的独立执行证据。
- 不实现 Chapter 12 Hooks/升级观察、Chapter 13 真实 REVIEW + V2 自举、V3、模型路由或资源调度。
- 不执行 push、merge、deploy、publish、delete、凭据导出、付费调用或其他真实外部动作。

## 验收条件

1. V2 plan 精确包含 V1 prefix、acceptance、integration、targeted_mutation、independent_verifier；acceptance/integration 分别解析为上述固定 pytest argv，错误目录、parser 或 `aiflow --help` 占位均以稳定契约错误拒绝且不启动进程。
2. 默认 live V2 真实执行 acceptance 与 integration，各自生成独立的 task-local stdout/stderr log ref 和 pytest tool version；两个命令返回 0 时对应 evidence checks 为 passed。
3. 任一 acceptance/integration 命令非零、超时、无结果或工具不可用时，对应 check 为 failed/unverified 并保留稳定 reason；不得被 V2 evidence 升级逻辑覆盖为 passed。
4. `--check acceptance` 与 `--check integration` 的定向运行只启动所选检查，结果为 provisional；未运行的必需检查保持未验证，不得形成 final/Gate eligible evidence。
5. 无论 acceptance/integration 是否通过，targeted_mutation 都保持 `unverified`、`VERIFICATION_CHAPTER11_NOT_IMPLEMENTED` 和 pending manifest/result，live V2 conclusion 为 failed，`--finalize` 不能成功。
6. V0/V1 计划、执行、evidence、approval、Gate 和既有 fixtures 回放不变；现有 V2 两阶段 snapshot、review 与 Gate 定向测试继续通过。
7. `tests/acceptance` 与 `tests/integration` 均可离线、确定性执行；测试验证 runner 不使用 Shell、不访问网络且不在主工作树业务路径落盘。
8. `uv run aiflow validate TASK-0011`、`uv run aiflow scope TASK-0011`、Ruff、format、mypy、全量 pytest、branch coverage、Python diff coverage 不低于 90% 及 `git diff --check` 全部通过，并完成独立 implementation review。
9. README、Quickstart、Chapter 11 实施记录和 chapter/overall 状态准确显示 11.1 完成、11.2–11.5 pending、整体累计计数及 live V2 pending-mutation 失败边界。
10. 初始规格批准绑定旧 Policy；Policy 文件变化后旧分类、设计审核和批准按 freshness 规则失效，只有完成 `policy_changed` 升级、重新分类/冻结/设计审核和 fresh spec approval 后才允许最终验证。

## 禁止动作

- 禁止 push、merge、deploy、publish、delete、凭据导出和付费外部调用。
- 禁止降低 route、verification level、review、approval、freshness 或 Gate 要求。
- 禁止把 acceptance/integration 与 V1 regression 通过混为同一 evidence check，或伪造日志、tool version、exit code、review ref 与 mutation 结果。
- 禁止让 acceptance/integration 命令访问网络、依赖非固定外部状态、修改主工作树业务文件或使用 shell 字符串执行。
- 禁止在未重新绑定新 Policy 的 fresh spec approval 前执行最终验证。

## 错误行为

- acceptance/integration Policy 命令仍为 `aiflow --help`、不是精确 pytest 目标、parser 不匹配、含未知占位符或 shell-like 内容时，计划解析必须在进程启动前拒绝。
- runner 非零、超时、日志写入失败、缺少结果或工具不可用时，evidence 必须如实失败或未验证，不能由后处理改写。
- targeted_mutation missing/unverified 时，V2 必须失败；不得因为 acceptance/integration 通过而 finalize、批准代码或通过 Gate。
- 修改 `.ai/policy/verification-levels.yaml` 后若 classification、design review 或 spec approval 仍绑定旧 Policy，任务必须升级/拒绝，不得继续验证。
- 实际需要修改 schema、Gate、approval、mutation runner、扩大允许路径或改变 V0/V1 语义时，必须显式升级、重新分类、重新冻结并重新批准。

## 回滚

所有变更均为本地版本化 Policy、Python、测试和文档，可通过后续反向提交回滚。回滚必须同时恢复 acceptance/integration Policy 命令、计划语义、V2 执行选择和状态文档，不能只恢复其中一层而留下伪可执行能力；既有 V0/V1 artifacts 不迁移或重写。任何 push、merge、deploy 或 task close 均不在本任务授权内。
