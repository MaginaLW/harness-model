# Task Specification

## 目标

让 `tools/hooks/pre_command.py` 在 task 持有**与本次动作匹配且新鲜**的 action 批准时放行
`push` / `merge`，使 Policy 中「push、merge 必须单独获批」的要求从**不可执行的流程约定**
变为**可执行的拦截**。

## 依据（全部为实测，附代码位置）

1. **当前 wrapper 从不查询批准。** `tools/hooks/pre_command.py:78` 传入
   `action_allowed=permission.allowed_automatically` —— 一个 Policy 常量。实测：

   | 动作 | `allowed_automatically` | precondition | 退出码 |
   |---|---|---|---|
   | `read` | True | True | 0 |
   | `push` / `merge` / `delete` / `deploy` | False | False | **2** |

   与该 task 是否持有有效 action 批准**完全无关**。

2. **因此 Policy 的要求当前不可执行。** `gate.py:531` 与 `status_service.py:211` 在计算批准
   新鲜度前显式跳过 `approval_type == "action"`；账本佐证：AUTO 任务 TASK-0037（PR #8）与
   TASK-0039（PR #12）的 `approvals.json` 均为 `[]`，全程 0 次 action 批准即完成 push 与 merge。

3. **所需的查询函数已存在，无需新建。** `src/aiflow/approval.py:295` 的
   `matching_approval(approvals, approval_type=..., context=...)` 返回第一个新鲜的指定类型
   批准；`approval_is_current`（第 260 行）与 `canonical_action_sha256`（第 180 行）亦已实现。

4. **本改动同时接通一条死分支。** `src/aiflow/freshness.py` 的 `action_approval` 分支当前
   无任何生产调用方（`status_service.py:132` 把 `used_action_sha256s` 硬编码为 `()`）。

5. **`.git/hooks/` 当前未安装任何 hook。** 本任务不改变这一点（见非目标 4）。

## 主动修改的架构原则（项目所有者已明确决定）

`docs/operations/hooks.md` 现载：

> All wrappers fail closed. They do not install themselves, consume an approval, execute a
> command, or **turn a diagnostic result into permission**.

**项目所有者已明确决定修改最后一项**：wrapper 在持有有效批准时**可以**放行。其余三项
（不自行安装、不消费批准、不执行命令）**保持不变**，并须在文档中显式重申。

这是本任务与既有设计原则的**唯一**冲突点，故在此单列而非藏入实现细节。

## 范围

- `tools/hooks/pre_command.py`：`check_pre_command` 的 `action_allowed` 判定。
- `docs/operations/hooks.md`：原则修改与边界重申。
- `tests/integration/test_tool_wrappers.py`、`tests/integration/test_observation_parity.py`。
- 执行目录：记录 B3 的落地结论。

## 非目标

1. **不修改 `src/aiflow/**`。** 所需函数均已存在并已导出；若实现过程中发现必须修改核心，
   须停止并重新分类（该路径在 `AGENTS.md` 升级清单内）。
2. **不改变 `permissions.yaml` 的 `forbidden_automatic_actions` 六项。** 本任务改变的是
   「批准存在时是否放行」，不是「是否需要批准」。
3. **wrapper 仍不消费批准。** 放行不得写入 `used_action_sha256s`、不得产生消费副作用；
   一次性语义的消费点仍只在 `src/aiflow/mutation_evidence.py`（`targeted_mutation_v2`）。
4. **wrapper 仍不自行安装、不执行任何命令。** 本任务不向 `.git/hooks/` 写入任何内容。
5. 不改动 CI 质量门禁的检查项与阈值，不改 `main` 分支保护。

## 验收条件

| 检查 | 预期 |
|---|---|
| `python -m pytest tests/integration/test_tool_wrappers.py -q` | 通过 |
| `python -m pytest tests/integration/test_observation_parity.py -q` | 通过 |
| `python -m pytest -q` / `python -m mypy src` | 通过 |
| 无批准 | `push`、`merge` 仍退出 2 |
| 批准存在但 `action_sha256` 不匹配本次动作 | 退出 2 |
| 批准已过期（`expires_at` 已过） | 退出 2 |
| 批准已被消费（在 `used_action_sha256s` 中） | 退出 2 |
| 批准新鲜且 `action_sha256` 匹配 | **退出 0** |
| 六个禁止动作在无有效批准时 | 逐一验证仍全部退出 2 |
| 放行后 | `used_action_sha256s` 未被写入，无消费副作用 |
| `.git/hooks/` | 任务前后均无新增文件 |

## 禁止动作

push、merge、deploy、delete、secret_export、paid_external_call，以及任何外部系统调用。
本任务只修改本地文件并运行验证。

## 错误行为

- 批准记录不合契约、`action_sha256` 缺失或格式非法时 **fail closed**（退出 2），不得放行。
- task 无法唯一解析时仍按现有语义失败，不得回落为放行。
- observation 记录失败时不得放行 —— 审计失败即拒绝。
- 任何异常路径的默认结果都必须是拒绝。

## 回滚

改动仅限受版本控制的文本文件。回滚 = 还原 `pre_command.py`、`hooks.md` 与测试。
本任务不写入 `.git/hooks/`，不产生仓库外副作用，回滚后行为与改动前逐字节一致。
