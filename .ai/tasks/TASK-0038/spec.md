# Task Specification

## 目标

按项目所有者的明确决定重建 bootstrap 标记，使仓库进入维护模式：后续代码、配置、CI 或行为变更不再强制创建 AI Flow task，而 CI 的质量门禁保持原有强度不变。

## 范围

- `.ai/bootstrap-mode.yaml`：新建，内容为 CI 判定所要求的规范两行——`mode` 为 `bootstrap_auto`，`status` 为 `active`。必须是无引号的裸值，因为 CI 用 `grep -qx` 做整行精确匹配。
- `AGENTS.md`：更新治理模式声明，记录本次所有者决定、维护模式的适用范围，以及仍然不被放松的边界。
- `README.md`：更新「当前治理模式」段落，与 AGENTS.md 保持一致。
- `.claude/skills/ai-flow/SKILL.md`：更新 `Governance activation` 小节，使其描述维护模式下 Skill 的实际适用条件。
- `tests/integration/test_agent_entry_files.py`：更新入口文件契约断言，使其断言维护模式下的事实而非正式模式下的事实。
- `CHANGELOG.md`：在 Unreleased 记录治理模式切换。

## 非目标

- 不修改 `.github/workflows/ai-quality-gate.yml`。bootstrap 分支及其质量检查早已存在于 workflow 中，本任务只是让 base 分支上的标记把它激活。
- 不修改 `src/aiflow/**` 的任何行为。CLI 不含任何 bootstrap 感知，维护模式是纯 CI 层旁路，AI Flow 仍可随时按需使用。
- 不降低任何质量门槛：完整 pytest、85% 总覆盖率、90% diff coverage、whitespace、`ruff check`、`ruff format --check`、`mypy` 在 bootstrap 路径下全部照常执行。
- 不修改 Policy、证据 schema、Gate 语义或任何既有任务记录。
- 不删除既有任务目录或历史证据。

## 验收条件

- `.ai/bootstrap-mode.yaml` 存在，且恰好包含 `mode: bootstrap_auto` 与 `status: active` 两行裸值；`test_bootstrap_detection_is_canonical_and_fail_closed` 所验证的判定规则对该文件返回 active。
- `tests/integration/test_github_workflow.py` 全部通过，workflow 的 bootstrap 判定契约未被改动。
- `tests/integration/test_agent_entry_files.py` 全部通过，且其断言反映维护模式下的事实。
- AGENTS.md、README.md 与 ai-flow Skill 三处治理模式陈述彼此一致，无残留的「正式自用治理已启用」表述。
- V1 完整回归、`ruff check`、`ruff format --check`、`mypy src` 通过，总覆盖率不低于 85%，diff coverage 不低于 90%。
- `aiflow scope TASK-0038` 通过。

## 禁止动作

push、merge、deploy、delete、secret_export、paid_external_call。本任务不执行外部动作、不访问网络、不使用凭据、不产生付费调用。

## 错误行为

- 标记文件若带引号、缺行或含额外字段，CI 判定必须 fail-closed 为非 active；该规则由既有测试锁定，本任务不得放宽。
- 若三处治理陈述互相矛盾，入口文件契约测试必须失败。
- 若改动触及允许范围之外的文件，`aiflow scope` 必须拒绝。

## 回滚

删除 `.ai/bootstrap-mode.yaml` 并还原其余五个文件即恢复正式自用治理。由于 CI 在 base SHA 上读取标记，回滚 PR 会在 bootstrap 路径下运行，而合并后的下一个 PR 恢复正式路径——与本次进入的对称。既有任务记录与证据不受影响。

## 本次决定的边界

维护模式解除的是**任务账本的强制性**：分类、规格冻结、审批、结构化审核、证据绑定与 Gate 不再是每次变更的前置条件。它**不**解除：

- CI 质量门禁的任何一项检查或阈值。
- 高风险动作仍需单独批准——push、merge、deploy、删除、凭据导出、付费调用不因维护模式而获得授权。
- `main` 的分支保护与 required check。
- 仓库卫生与证据保留约定：既有任务记录、证据与日志仍是追加式的，不得重写或删除。

AI Flow CLI 保持完全可用。对风险较高、需要留痕或需要人类决策的变更，仍应主动创建 task；维护模式只是不再把它作为每一次变更的强制前置。恢复正式模式只需删除标记文件。

## 与本轮收尾的关系

本任务是本轮最后一个必须走完整 AI Flow 的变更：CI 在 base SHA 上读取标记，而 `main` 此刻尚无标记，因此本 PR 自身仍走正式路径并需要恰好一个可解析的任务目录。合并后，后续 PR 才在 bootstrap 路径下运行。

本轮同时留下三个未处理的治理缺口（任务 `base_commit` 无法重新绑定、变异证据在 Windows 检出下无法校验、分支保护与 attestation 约束互斥）。维护模式不修复它们，但会显著降低前两个缺口的日常代价——因为大多数变更不再产生需要绑定 base 与 subject 的任务记录。
