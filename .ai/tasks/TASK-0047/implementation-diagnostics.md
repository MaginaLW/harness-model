# TASK-0047 实现诊断（非最终验证）

本记录保留本轮实际检查结果，不替代绑定最终 subject、规格和 Policy 的 CLI verify 证据。
完整验证、实施审核、代码批准与 Gate 均不得从以下定向结果推定通过。

## Policy 切换前

- DU-001 的 decision-unit、start 和 classify 集合：67 passed，37.47 秒。
  覆盖字段缺失/非法零写、历史同身份 no-op、pending 失效拒绝与合法清理重放。
- answer、governance paths 和 golden 的非受控路由集合：32 passed、1 failed、3 deselected。
  失败为本任务允许范围内的治理恢复测试未补新风险输入；已补真实无对应风险的两个空数组，
  该失败用例重跑 1 passed。3 个 deselected 是尚未启用受控硬规则的诊断选择，不是正式验证。
- begin/close、escalate 与 verification-evidence-flow：62 passed、3 failed，62.85 秒。
  以下三项均直接分类尚未补齐风险字段的 start 草稿，错误为
  `Classification requires explicit risk inputs (DU-001: impact_categories, controlled_actions)`：
  - `tests/integration/test_begin_close_commands.py::test_classify_records_durable_evidence_and_is_idempotent`
  - `tests/integration/test_escalate_command.py::test_block_requires_bound_resolution_evidence_before_reclassification`
  - `tests/integration/test_escalate_command.py::test_resolution_classification_recovers_from_first_transition_failure`
- 上述两个文件不在原精确 allowed_scope 内，未修改、未 skip/xfail、未改期望快照。
  它们是实际遗漏的必需配套范围，拟与计划内 Policy 恢复一次呈交新的有界规格决定。
- Ruff check、format（395 files）及 mypy（41 source files）在该检查点通过。

## 人工介入与边界

本轮只有所有者一次“批准”输入，CLI 按两个 REVIEW 单元记录两条 spec 批准。
Agent 自行完成并行实现、输入核对、定向检查、错误诊断和允许范围内修复，不逐步索取确认。
遗漏范围不伪称已获批；计划内新 Policy 绑定也不从旧批准复制。
动作测试只在隔离临时仓库中运行，本任务没有执行任何真实外部动作。

## 最终 Policy 树的全量诊断

Policy `2.3.0` SHA-256：
`d21a386779147dfad962a0fc0656bef61bc581e27f63c4789dcc06520fa10ff1`。
四份 Policy 一次启用后已立即 CLI escalate 为 ESCALATED；之后未继续实现。

- `pytest -q --cov=aiflow --cov-branch`：**1717 passed、4 failed**，614.19 秒，0 skipped。
  原三项缺风险事实失败仍在；第四项是
  `tests/integration/test_auto_preflight.py::test_auto_begin_rejects_decision_facts_changed_after_classification`：
  begin 仍 exit 1，但共用新鲜度检查更早返回 `Current classification is stale`，旧断言寻找
  `CLASSIFICATION_STALE`。没有把功能拒绝说成成功，也没有修改这三个清单外文件。
- 覆盖率：行 6556/7226，分支 1961/2444，合计 8517/9670，即 **88.08%**。
- diff-cover 对任务 base `426b80b37600d8cd9a1c129b4520bf242fead217`：
  **36 个可执行差异行全部覆盖，100%**；包括源码、staged 与 unstaged 差异。
- 最终源码/Policy 树的 Ruff check、format（396 files）、mypy（41 source files）与
  whitespace 通过；routing/verification-levels 相对旧版仅变版本，未改变任何门槛或超时。
- TASK-0046 的 validate、status 仍能读取 MERGED 历史；其 tracked 任务文件的逐文件
  SHA-256 在两项只读命令前后相同。新 Policy 下 stale 是预期，没有迁移旧记录。

诊断产物留在本任务忽略目录 `logs/policy23-diagnostic/`：`pytest.xml`、`coverage.xml`、
`diff-coverage.json`。它们不是 `evidence.json`，不替代最终 CLI verify，也不是 Gate PASS。
诊断原始文件 SHA-256：

- coverage.xml：`3d58275904f43aa91e02b2355d87ce5196c811b3ede6a1bac1246261562dd300`
- diff-coverage.json：`a8f6b61242c2f812b009cfaa82cafd063c20fc44ec8c6b89f5dc1668b3b7c437`
- pytest.xml：`36965bbae3a8b80e5cde04a57cb77396cf21827ed056b94da9d145f3317efb3c`

新增拟议范围现精确为三份测试文件，规格修订保留了逐项原因与修改边界。
尚待：本修订规格及三文件同任务例外的真实批准、修复这四项、正式完整验证、实施审核、
代码批准和 Gate；远端发布动作仍未授权。

## 已提交实现的首次正式 V1：失败证据

前述三文件规格修订现已真实获批，四项失败均已修复；定向 56 passed（28.37 秒），
本地提交 `1c286be3951b9083742a33fc2d111ae986d38407`。CLI sync 绑定该 subject 后，
于 `2026-09-07T16:23:21Z` 开始正式完整 V1，`16:41:53Z` 结束为 **FAILED**。

- contract、scope、Ruff check/format、smoke、mypy 均通过；unit tests 1115 passed。
- 普通全量：1720 passed、1 failed，491.48 秒；覆盖率全量：1720 passed、1 failed，
  592.76 秒。两轮均无 skipped；唯一失败是
  `tests/e2e/test_clean_checkout.py::test_clean_clone_installs_and_runs_documented_safe_subset`。
- 安装后真实 classify 返回 `Classification requires explicit risk inputs
  (DU-001: controlled_actions)`。该样例已有 documentation 事实但漏写受控动作事实。
- XML：行 6558/7226、分支 1963/2444，合计 8521/9670，即 **88.12%**。
  diff coverage 为 36/36，即 **100%**。覆盖率数值达标不抵消测试退出失败，正式
  coverage_xml check 仍为 failed；没有最终实施审核、代码批准或 Gate PASS。

漏检原因属于 Agent 的配套盘点不足：前轮全量诊断运行于未提交实现树，clean-clone
测试却安装当时已提交的旧 HEAD，所以该项通过不能证明新实现的安装行为。原诊断记录
及其 hash 不改写；本节补充其有效性限制。正式提交态两轮测试已暴露相同真实失败。

交叉只读审计确认：新增必要路径仅上述 e2e 与 `docs/operations/quickstart.md`；后者
可复制 YAML 同样漏字段，且“缺事实均为 BLOCK”与当前 Policy 版本说明需要同步。
其余 e2e 新分类来源复用四个已补齐的场景输入。未改动这两份未批准文件，未修改源码
默认值、共享 helper、期望路由、安装机制、检查阈值或 skip/xfail。

原始产物在 `logs/run-20260907T162321824527Z/`；正式 `evidence.json` 与 run 内副本
一致。以下 SHA-256 保留本次失败绑定；后续新验证不得改写该 run 的原始证据：

- evidence.json：`cf78889a20b8d06f681db38f0909f0f7b37df504b6c46ddf1c43a475b49162b9`
- coverage.xml：`060b4af044fa78b28dc82832eb17bac859c26007a85528290e94ff3d1161a3b1`
- regression_tests-007.stdout.log：`b553c32b1b08e72410189a9963bdbc902a728d57c425cbbfaf328f0143b973d7`
- coverage_xml-009.stdout.log：`46024c23d8db2b3be6f0debc29c4ad7e4fcc44870bb04df358e3f9eb7a668e75`

失败后 CLI 按真实 `spec_changed` 进入 ESCALATED，准备仅两文件的范围修订。
既有批准和失败记录保留；规格修订获批前不继续实施，不能把它伪称独立 task-free 修复。
