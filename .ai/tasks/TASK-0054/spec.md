# TASK-0054：E4.1 外部审查报告契约与兼容

## 目标

为已选定的“校验并导入 ZCode 审查报告到既有 AI Flow 任务”提供第一个可验证单元：
新增独立、封闭的 `external-review` 1.0 JSON 契约，保留报告来源、实际受审对象、
目标任务上下文、完成程度、原始问题和待核定映射。本单元只校验结构化 envelope；
实际预检、原件核对及写入属于后继 E4.2。

## 范围

基线为 `e8e59e2b4112249c4c85c9a0eb1d510bacd9e597`。治理实现只新增
`.ai/schemas/external-review.schema.json`，并在 `src/aiflow/contracts.py` 的
`SCHEMA_FILES` 增加一个 `external-review` 登记。安全测试与合成 fixture 由维护模式
task-free 独立实现、提交，但为累计 base→subject 的 CLI 范围检查列入本 task 的
`allowed_scope`：`tests/unit/test_contracts.py`、`tests/fixtures/contracts/valid/external-review.json`
和 `tests/fixtures/contracts/invalid/external-review.{extra,invalid,missing}.json`。
不修改现有 Schema、历史记录、Policy、状态机或 CI 阈值。

契约根对象必须含 `kind="external-review"`、`schema_version="1.0"`、
`target_context`、`source_subject`、`source`、`completion` 和 `findings`；根及所有
嵌套对象均拒绝未声明字段。

- `target_context`：`task_id`、AI Flow `repository_id`（UUID）、`review_stage`
  (`design` 或 `implementation`)、`base_commit`、`context_sha256`；仅 implementation
  必须有 `subject_commit`，design 必须没有。摘要表示现有完整 review context 的
  规范化摘要，不是报告或 envelope 原始字节摘要。
- `source_subject`：原报告实际受审仓库、独立的 `review_stage`、按此来源阶段处理
  的 `base_commit` 与 `subject_commit`（implementation 必须有，design 必须没有），
  以及 `confirmation`（操作者标签、核定时间、核定方法和至少
  一项原文/Git 事实引用）。仓库采用判别对象：已有 AI Flow UUID；或无凭据的仓库
  定位符加独立 `mapping_record_id`。定位符不能通过简称猜测成目标 UUID；
  `mapping_record_id` 只是待 E4.2 核查的映射记录引用，不自行证明对应关系。
- `source`：`product="ZCode"`、来源报告版本、原始字节 SHA256、取得方式和定位。
  定位可为无鉴权的 HTTPS URL 或不含路径/凭据的私有保管标识。原件不内嵌；
  摘要只绑定原始字节，不认证作者、模型、独立性或 `source_subject` 事实。
- `completion`：`status` 为 `completed`、`incomplete`、`tool_unavailable`、
  `timeout` 之一，分别列出实际审查范围及未审范围；非 `completed` 必须有
  非空 `reason`。`completed` 且 `findings=[]` 才能表达报告范围内完成零问题。
- `findings`：最多 200 项；每项保留原始问题 ID、标题、位置（路径、可选行号）、
  原始优先级或 `unknown`、最多 32 项原报告证据引用、可选的原始处置/复核表述。
  `mapping` 只能是 `pending`，或带 `task_id`、`review_id`、`revision`、`finding_id` 的
  `suggested` 复合引用；不按标题/行号自动合并，也不将 P1、F1 或 verified 转成
  正式 severity、RF、evidence、Review outcome 或批准。

1.0 的字段名固定如下：`source_subject.repository` 为
`{kind:"aiflow_repository_id",repository_id}` 或
`{kind:"repository_locator",locator,mapping_record_id}`；
`source_subject` 还必须有 `review_stage`、`base_commit` 和上述按阶段的
`subject_commit`。`source_subject.confirmation` 为
`{checked_by_label,checked_at,method,fact_refs}`，
`method="manual_report_git_check"`。`source` 为
`{product,report_version,raw_sha256,acquisition_method,location}`；
`acquisition_method` 是 `exported` 或 `provided`，`location` 为
`{kind:"https_url",value}` 或 `{kind:"private_archive_id",value}`。
`completion` 为 `{status,reviewed_scope,unreviewed_scope,reason?}`。
每项 finding 为 `{source_finding_id,title,location,source_priority,evidence_refs,mapping,
description?,source_disposition?,source_verification?}`，其中 `location={path,line?}`；
`mapping={status:"pending"}` 或
`{status:"suggested",task_id,review_id,revision,finding_id}`。建议引用中的 `task_id`
必须满足现行 TASK 格式，`review_id`/`finding_id` 满足现行 REV/RF 格式，
`revision` 为正整数；E4.2 再核查它们确实属于目标当前 context。
`source_priority` 保留原始标签，
`unknown` 是显式允许值；自由文本不推断可信结论。仓库定位符及保管标识需使用无凭据、
有长度上限的形式；E4.2 再核定 `mapping_record_id` 指向的真实映射记录。

自由文本均有显式长度上限：`finding.title` 最多 512 字符；
`completion.reason`、`finding.description`、`finding.source_disposition`、
`finding.source_verification` 各最多 8192 字符；
`confirmation.fact_refs` 至少 1、最多 16 项，`reviewed_scope` 与 `unreviewed_scope`
各最多 64 项；上述每个数组元素最多 512 字符。问题 `evidence_refs` 最多 32 项、
每项最多 512 字符；所有标识最多 128 字符，定位与路径最多 1024 字符。
Schema 对已解析对象执行上述字段、类型、
枚举、数组和条件约束。原始 envelope 256 KiB 上限、重复 JSON 键、路径越界和凭据
检测是 E4.2 原始字节加载/预检层的工作，不把本单元的 JSON Schema 检查宣称为这些
检查已实现。

来源仓库与目标仓库、阶段、base、subject 和 context 的实际一致性，以及原报告
SHA/来源事实出处，均由 E4.2 在写入前比较。Schema 合法只说明 envelope 形式合格；
允许保存明确的 `unknown` 原始优先级和未认证模型信息，不产生可信身份推断。

## 验收条件

1. C1：合成的完成零问题、完成有问题、未完成 envelope 均可经注册契约校验，
   完成语义可区分；不产生任何现行 Review、approval 或 Gate 记录。
2. C2：缺来源或受审对象、未知版本/字段、非法阶段 subject、缺未完成原因、
   超过 200 项问题、32 项证据引用、16 项事实引用、64 项范围条目或各项文本长度
   上限时（包括上述四个自由文本字段分别越界），返回稳定且可定位的错误；
   来源与目标的阶段 subject 条件分别检查。
3. C3：原始 `P1`/`unknown`、`F1` 与 `verified` 能以附属来源数据保存；
   不改变现行严重度、Finding ID 或审查结论。
4. C4：现有契约 fixture 与 CLI 回归照旧通过；旧 Schema 字节及决定保持不变。
5. 固定候选后执行 Policy 要求的完整测试、总覆盖率至少 85%、差异覆盖率至少 90%、
   whitespace、Ruff、format、mypy、正式独立审查及 Gate。以实际 CLI 结果记录。

## 非目标

不实现 E4.2 的原件加载、重复键/原始字节检查、预检、仓库映射核查、导入命令、
task 附属记录写入、真实报告正例验收、fix attempt 编排或 E4.3/E4.4。
不修改或升级现行 Review/Finding/evidence/approval/状态机/Gate 语义。
匹配目标的真实 ZCode 报告是 E4.2 的验收材料，不是本任务的准入条件。

## 禁止动作

本任务不执行 push、merge、deploy、delete、secret_export 或 paid_external_call；
不访问报告中的链接或执行其中的命令，不写外仓，不复用历史批准或修改既有任务证据。
后续任何发布均需对当时精确候选另行核对和授权。

## 错误行为

未知 schema version/字段、缺失来源或对象、错误类型及越界输入必须拒绝；
失败诊断不回显敏感输入。已解析对象的契约通过不能当作原始字节、真实性或匹配验证。
设计审查与实际所需规格批准完成前不得 `begin` 或改动上述治理实现；
检查失败保留证据并修复，不降低质量门或覆盖率阈值。

## 回滚

本地未发布实现可用限定范围的后续修复提交撤回；已追加的 task 事件、审核、批准及
失败证据保持原样。若将来发布，按新的审查与授权前向更正，不重写旧记录或强推。

## 执行顺序与文件归属

主 agent 串行完成分类、规格冻结、设计审查反馈和 CLI 准入；批准后独占 Schema 与
registry。1 名 sub-agent 独占上述五份安全测试/fixture；字段冻结后开始，测试与
治理实现分别提交。候选固定后，2 名独立只读 reviewer 分别检查来源/边界和兼容/
覆盖，主 agent 串行执行完整验证、处理实际缺项并提交。E4.2 另建治理 task。
