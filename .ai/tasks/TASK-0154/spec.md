# Task Specification

## 目标

将 `boring-engineering` 工程克制约束与 `approval-feedback` 低打断交互协议（含 `A01` + 可选 `0–3` 打分、当轮 `0/1` 规则 diff 建议、权限规则归整、定时窗口四元组与交付边界五项自检）整合进 `AGENTS.md`、`.ai/templates/` 模板及 `.agents/skills/ai-flow/SKILL.md`，在保持既有治理与契约测试完全兼容的前提下减少人工打断并规范求助格式。

## 范围

仅允许修改以下工作区文件及 `TASK-0154` 自身账本记录：

- `AGENTS.md`（仅 `## 开发与协作` 与 `## AI Flow 规则` 协作条款；不修改 `## 常设授权` 节授权范围与条目）
- `.ai/templates/spec.md`（在现有 `## 范围` 与 `## 非目标` 段落内补充能力复用与拒绝推测性抽象提示，保持现有七个 `##` 标题集合与顺序完全不变）
- `.ai/templates/ask.md`（在现有段落内补充 `A01` 编号及可选 `0–3` 打分提示说明，完整保留 `2—4` 与全部六个字段说明）
- `.ai/templates/review-package.md`（在现有 `## 语义变更` 与 `## 审核问题` 段落内嵌入交付边界五项自检要点，保持现有八个 `##` 标题集合与顺序完全不变）
- `.agents/skills/ai-flow/SKILL.md`（在人工提问、设计审核与实现审核/外部动作步骤补充 `A01` + 可选 `0–3` 与定时窗口四元组提醒；所有相对链接不带 `#` 锚点，仅引用既有 `aiflow` 子命令）
- `.ai/tasks/TASK-0154/**`（本任务自身账本、规格、审核输入与验证证据）

实施前已核对仓内现有文档与模板契约：`docs/operations/low-intervention.md`、`docs/operations/effect-observations.md` 与 `examples/adoption/project-rules.md` 属运维指南与采用示例，已归入阶段 1 文档改动并明确排除在本任务外。

## 非目标

- 不修改 `AGENTS.md` 中的 `## 常设授权`、`## 当前治理模式`、`.ai/policy/*.yaml`、`.ai/schemas/*.json` 或 `src/aiflow/**`。
- 不修改任何现有 Markdown 模板的 `##` 顶级/二级标题列表，不引入任何未完成占位符或空勾选框。
- 不在本仓或本机 `%LOCALAPPDATA%` 写入私有积分台账或移植 `record-feedback.ps1`。
- 不在本任务中执行 `docs/operations/**`、目标外仓（`agent-bridge` / `ai-agent-dotfiles`）改造、`git push` 或 PR 合并。

## 验收条件

1. `tests/integration/test_agent_entry_files.py`、`tests/integration/test_ai_flow_skill.py` 与 `tests/integration/test_templates_and_policy.py` 全部通过（无新增 `##` 标题、无断链、`.agents/skills/ai-flow/SKILL.md` 无 `#fragment`、无空占位符）。
2. `ruff check .`、`ruff format --check .`、`mypy` 与 `git diff --check` 全部退出码为 0。
3. `aiflow validate TASK-0154`、`aiflow scope TASK-0154` 与 `aiflow verify TASK-0154 --actor codex` 通过。
4. 独立子代理审核结论为明确裁决，且 `AGENTS.md` 修改交由项目所有者亲自确认 `code` 批准与后续推送合并，不在未获所有者审阅前以 `project-owner` 自签最终 `code` 批准或推送/合并。

## 禁止动作

- 禁止修改 `## 常设授权` 或扩大任何自动授权/外部动作权限。
- 禁止跳过独立设计/实现审核、绕过 `aiflow` 状态机或伪造验证/审核结论。
- 禁止执行 `deploy`、`delete`、`secret_export`、`paid_external_call`、`git push`、`git merge` 或改动主工作区 `D:\Repos\harness-model`。

## 错误行为

- 若契约测试（如模板标题集合、`SKILL.md` 相对链接格式或策略占位符检查）失败，必须先修正模板/文档或中止并上报，禁止修改测试断言放宽标准。
- 若范围漂移或出现需要新增 `impact_scope` 的文件，立即通过 `aiflow escalate` 或暂停等待决定，不得越权编辑范围外文件。
- 若 CLI 校验、新鲜度或验证工具失败，按 CLI 指引诊断修复或保留失败证据上报，禁止直接编辑 `.ai/tasks/TASK-0154/` 状态字段绕过门禁。

## 回滚

本任务仅涉及独立工作树 `D:\Repos\harness-model-wt-stage2` 上的文档、模板与任务记录修改；若需回滚，可在该工作树内使用 `git restore` 或删除对应提交/分支与工作树，对 `origin/main` 与主工作区零影响。
