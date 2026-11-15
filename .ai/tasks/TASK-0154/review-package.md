# Review Package

## 审核目标

裁决 `TASK-0154` 对 `AGENTS.md`、`.ai/templates/{spec,ask,review-package}.md` 与 `.agents/skills/ai-flow/SKILL.md` 的阶段 2 整合实现，并针对两项阻断性程序/所有权门禁作出决定：(1) `AGENTS.md` 修改的最终 `code` 批准；(2) 本地 Windows `V1` 完整覆盖率超时（`RUNNER_TIMEOUT`）与远端 Ubuntu CI / 推送策略处理。

## 背景

根据项目所有者确认的方案 2 路线，将原独立技能 `boring-engineering`（v1.2.0）与 `approval-feedback`（不含 `%LOCALAPPDATA%` 私有台账与 `record-feedback.ps1`，保留当轮立即规则 diff 建议、权限规则归整、定时窗口四元组与收尾 `S/Q/U/H` 核验）内化至 `harness-model`。阶段 1 运维文档改动已提交于独立分支 `codex/integrate-boring-approval-docs`（`D:\Repos\harness-model-wt-stage1`，`72ebb1e7`）；本任务 `TASK-0154` 仅处理独立分支 `codex/integrate-boring-approval-governance` 上的升级清单入口、模板与技能文件。

## 代码地图

- `AGENTS.md`（仅 `## 开发与协作` L7–8 与 `## AI Flow 规则` 第 8 条 L48；`## 当前治理模式` 与 `## 常设授权` 全节保持原样未改）
- `.ai/templates/spec.md`（在 `## 范围` 与 `## 非目标` 内补充已有能力复用核查、外部边界防卫与拒绝推测性抽象）
- `.ai/templates/ask.md`（补充 `A01` 编号及可选 `0–3` 打断评分提示与 `0/1` 当轮规则 diff 处理边界；完整保留 `2—4` 与六个选项字段）
- `.ai/templates/review-package.md`（在 `## 语义变更` 与 `## 审核问题` 内嵌入 Practical DRY 三条件、边界防卫核查与交付边界五项自检 + `S/Q/U/H` 汇总说明）
- `.agents/skills/ai-flow/SKILL.md`（在 `step 2/3/4/5/6/8` 与 `## Escalation and recovery` 补充 `A01 + 0–3`、`0/1` 当轮修正与规则 diff、超过两次低分先征得同意再起草宿主削弱弹窗规则、最小权限规则归整、定时窗口四元组与无私有台账 `S/Q/U/H` 收尾；无 `#` 锚点及外部 `http(s)://` 链接）
- `.ai/tasks/TASK-0154/**`（本任务账本、规格、设计审核与证据记录）

## 语义变更

- 未修改任何 Python 运行时逻辑（`src/aiflow/**`）、Policy（`.ai/policy/*.yaml`）、Schema（`.ai/schemas/*.json`）或 CI workflow，亦未修改 `AGENTS.md` 中的 `## 常设授权` 权限边界。
- 抽象抽取明确收紧为 Practical DRY 三条件（“同业务规则、同向演进、合并不增分支标志位”）；校验、默认值与容错限定在不可信输入与外部 I/O 边界，内部调用链保持契约简洁；新增/运行测试避免镜像测试与无故扩大全量重跑。
- 提问与审批交互统一采用 `A01` 编号与可选 `0–3` 评分提示；收到明确 `0/1` 或重复打断时当轮同步给出执行修正与精确规则 diff 建议；超过两次 `0/1` 低分仅在用户明确同意后起草宿主削弱弹窗规则；相邻放行优先做最小权限规则归整；定时/窗口等待强制具备四元组（触发源、窗口周期、终止条件、连续失败上限）；收尾基于已有观察做 `S / Q / U / H` 汇总，不建外部私有台账。

## 风险

- **V1 全量门禁未通过（高风险 / 流程阻塞）**：`aiflow verify TASK-0154` 中 `unit_tests` / `regression_tests` / `coverage_xml` 执行 `pytest --cov=aiflow --cov=tools/analysis --cov-branch` 时在本机 Windows 环境跑至约 83% 即耗尽 3000s 预算（`RUNNER_TIMEOUT`），导致任务无法自动推进至 `VERIFIED` / `WAITING_FOR_FINAL_REVIEW`。
- **预存 Windows 集成测试失败**：无 `--cov-branch` 单独运行 `tests/integration` 时，`tests/integration/test_resource_bundle_distribution.py::test_incomplete_source_distribution_cannot_build_wheel` 因本机中文 Windows 默认编码读取子进程输出触发 `UnicodeDecodeError`（`0xd5`）与 `TypeError`（非本任务文件改动引起）。
- **`AGENTS.md` 治理变更风险**：虽未改动 `## 常设授权` 与 `## 当前治理模式`，但 `AGENTS.md` 属升级清单顶层入口文件，须由项目所有者亲自审核条款语义与推送/合并授权。

## 证据

### 本轮已直接观察通过的检查（覆盖最终文本改动）

- `git -C D:\Repos\harness-model-wt-stage2 diff --check`：exit 0
- `.venv\Scripts\python.exe -m ruff check .`：`All checks passed!`（exit 0）
- `.venv\Scripts\python.exe -m ruff format --check .`：`815 files already formatted`（exit 0）
- `.venv\Scripts\python.exe -m mypy src tools/analysis`：`Success: no issues found in 62 source files`（exit 0）
- `.venv\Scripts\python.exe -m pytest tests/integration/test_agent_entry_files.py tests/integration/test_ai_flow_skill.py tests/integration/test_templates_and_policy.py -v`：**24 passed in 0.79s**
- `.venv\Scripts\python.exe -m aiflow validate TASK-0154`：`TASK-0154 valid`

### 其余已执行测试记录（670eb2c8 基线上的分层诊断，仅修改后做了上述 24 项直接关联契约测试、ruff、mypy 与 validate 复测）

- `pytest tests/acceptance tests/e2e -q`：**41 passed in 51.86s**（`670eb2c8` 上实跑）
- `pytest tests/unit/test_review_detection_sources.py -q`：**130 passed in 46.82s**（`670eb2c8` 上实跑）
- `pytest` 剩余 19 个单元测试文件（`test_review_feedback*.py` 至 `test_workflow.py`）：**993 passed in 50.64s**（`670eb2c8` 上实跑）
- `pytest tests/integration -q`：**1192 passed, 6 skipped, 1 failed in 1597.99s**（唯一失败为 `test_incomplete_source_distribution_cannot_build_wheel` GBK 解码异常；`670eb2c8` 上实跑）
- `aiflow verify TASK-0154 --actor codex`（`logs/run-20261115T023202579536Z/`）：`contract`、`scope`、`ruff_check`、`ruff_format_check`、`smoke`、`mypy` 均 `passed`；`unit_tests`、`regression_tests`、`coverage_xml` 因 `RUNNER_TIMEOUT`（3000094 ms，停在约 83%）失败，`diff_coverage` 因缺少 `coverage.xml` 返回 exit 1。

### 独立审核与决策机会收尾汇总

- 设计审核：独立子代理 `8e09590a` 结论 `APPROVE`（已记录 `REV-0001`，3 条低级别实现护栏均已在实现与复修中落实）。
- 实现审核：独立子代理 `a6a71a65` 对 `670eb2c8` 结论 `APPROVE_WITH_CONDITIONS`（已采纳并修复 2 条 `[low]` 措辞/图例问题；明确保留 1 条 `[high]` 流程条件：V1 `RUNNER_TIMEOUT` 未通过前不得推进 `code` 批准/合并）。
- **`S / Q / U / H` 决策机会收尾汇总**：`S = 1`（本次收尾集中上呈的阶段 2 审核/V1 超时与推送合并裁决）；`Q = 1`（预存 `test_incomplete_source_distribution_cannot_build_wheel` Windows GBK 解码失败记为非本任务既有风险）；`U = 0`（阶段 1/2 推进过程未发生多余阻塞确认；阶段 1/2 无 `0/1` 低分评价）；`H = 1`（按 `AGENTS.md` 与 `spec.md` 主动拦截并保留 `AGENTS.md` `code` 批准及 `V1` 未过状态，未擅自绕过门禁或推送）。人类工时与交付后缺陷保持 `unknown`。

## 审核问题

1. 是否认可本任务对 `AGENTS.md`（仅 `## 开发与协作` 与 `## AI Flow 规则` 第 8 条）、`.ai/templates/{spec,ask,review-package}.md` 及 `.agents/skills/ai-flow/SKILL.md` 的文案与边界整合，并对 `AGENTS.md` 给予项目所有者 `code` 批准？
2. 针对本机 Windows 运行完整 `V1`（`pytest --cov-branch`）超过 3000s 触发 `RUNNER_TIMEOUT` 且未通过 `aiflow verify` 的情况：是否授权先将阶段 1 与阶段 2 分支推送至 `origin/codex/*` 开 PR 由 Ubuntu GitHub Actions required CI 执行全量 `V1` 与覆盖率检查（并在 CI 通过后按 `--ci` 或 `aiflow close` 归档），还是先行排查 Windows 测试性能/修复 `test_incomplete_source_distribution_cannot_build_wheel`？

交付边界五项自检结论：

1. 目标与关键假设清楚：是，阶段 2 严格对应方案 2 与已保留的 `S/Q/U/H` / 当轮规则 diff 设计，未擅自扩展至外仓。
2. 已有复用机会已核实：是，复用既有 `low-intervention.md`、`effect-observations.md`（阶段 1）及现有模板字段/CLI 命令，无自造冗余机制。
3. 修改模块无更简单直接写法：是，仅以紧致条目与内联提示补齐语义，未重排现有章节或引入复杂脚手架。
4. 新增条款与提示均有当前依据：是，全部对应 `boring-engineering`、`approval-feedback` 保留范围与独立设计/实现审核发现。
5. 未波及任务范围边界外文件：是，仅修改 5 个白名单文件及 `.ai/tasks/TASK-0154/**`；原主工作区 `D:\Repos\harness-model` 与 `## 常设授权` 保持原样。

## 推荐结论

**`APPROVE_WITH_CONDITIONS`（代码/文案整合可接受，但流程门禁处于 `ESCALATED / verification_unavailable`，需所有者裁决）**：文件内容已通过全部直接关联契约测试、静态检查（`ruff`、`mypy`、`git diff --check`）及独立审核员复核；因本机 Windows `V1` `pytest --cov-branch` 耗尽 3000s 预算并受 `test_incomplete_source_distribution_cannot_build_wheel` 预存编码异常影响，建议由项目所有者审阅 `AGENTS.md` 变更并批准推送开 PR，借助远端 Ubuntu required CI 完成全量 `V1` 与覆盖率验证后再决定合并与进入阶段 3（`agent-bridge`）。
