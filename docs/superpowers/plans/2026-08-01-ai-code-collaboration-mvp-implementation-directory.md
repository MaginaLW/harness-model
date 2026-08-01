# AI 代码协同系统阶段一 MVP Execution Plan

> **For agentic workers:** REQUIRED EXECUTION FLOW: Use `subagent-driven-development` to execute this plan task-by-task when subagents are available. If no subagent capability is available, execute inline with the same task checklist and review checkpoints.

**Goal:** 在本仓库中交付一个可安装、可测试、可审计的 AI 代码协同 Python CLI，使 AUTO、ASK、REVIEW、BLOCK、V0/V1、版本绑定证据和 CI 门禁形成可复现的最小闭环。

**Approach:** 采用纵向闭环顺序，先冻结契约和黄金样例，再实现任务状态、确定性分流、治理交互、验证证据、Agent/CI 适配，最后用本仓库的真实受控任务验收。核心规则只存在于 `src/aiflow/` 与 `.ai/policy/`；Skill、Hooks 和 CI 只调用核心接口。

**Materials:** `docs/architecture/AI代码协同分流与模型路由设计_V0.1.md`；`docs/architecture/AI代码协同系统实施总体规划_V0.2.md`；`docs/superpowers/specs/2026-08-01-ai-code-collaboration-mvp-design.md`；仓库当前 Git 状态和 GitHub Actions 环境。

**Validation:** 从干净检出安装项目，依次通过 Ruff、类型检查、单元测试、集成测试、端到端场景、覆盖率门槛和 `aiflow gate`；AUTO、ASK、REVIEW 在本仓库各完成一次真实受控流程，BLOCK 完成一次拒绝与恢复验证；本地和 CI 对相同任务给出一致结论。

---

## 0. 实施目录使用规则

### 0.1 总实施顺序

| 顺序 | 章节 | 可审阅结果 | 前置章节 |
|---:|---|---|---|
| 1 | 工程基线与可执行契约 | 可安装 CLI、Schema、Policy、模板、四类黄金样例 | 无 |
| 2 | 任务记录与状态核心 | `start/begin/status/close`、原子存储、可重放状态机 | 1 |
| 3 | 分流与验证等级引擎 | `classify`、AUTO/ASK/REVIEW/BLOCK、V0/V1 | 1、2 |
| 4 | 治理交互流程 | `answer/approve/escalate`、规格冻结、批准绑定 | 1—3 |
| 5 | 验证与证据闭环 | `verify/gate`、检查执行器、证据与失效 | 1—4 |
| 6 | Agent、Hooks 与 CI 集成 | Agent 入口、`ai-flow` Skill、薄 Hook、GitHub Action | 1—5 |
| 7 | 试点验收与阶段一基线 | 四类流程、真实仓库试点、验收报告和发布基线 | 1—6 |

不得跨章提前实现后续能力。允许先创建后续文件的空目录，但不允许用空函数、始终通过的检查或未验证的占位配置满足前一章退出条件。

### 0.2 全局工程约定

- 所有命令从仓库根目录执行。
- Python 基线为 3.11，`pyproject.toml` 使用 `requires-python = ">=3.11"`。
- 运行依赖使用 `PyYAML>=6,<7` 和 `jsonschema>=4,<5`；开发依赖使用 `pytest>=8,<10`、`pytest-cov>=5,<8`、`diff-cover>=8,<10`、`ruff>=0.9,<1`、`mypy>=1.11,<2`、`types-PyYAML>=6,<7`。
- CLI 使用标准库 `argparse`，不为参数解析引入额外框架。
- YAML 只通过 `yaml.safe_load` 读取；JSON 使用 UTF-8、稳定键排序和两个空格缩进写入。
- 时间写为 UTC ISO 8601，例如 `2026-08-01T12:00:00Z`。
- 内容摘要统一使用 SHA-256；Policy 摘要基于规范化 JSON 表示计算。
- 仓库身份使用提交到 `.ai/repository-id` 的 UUID；绝对 checkout 路径只作诊断，不参与本地与 CI 身份比较。
- 子进程始终使用参数数组、显式工作目录和超时，禁止拼接 Shell 字符串。
- 任务写入使用同目录临时文件加 `os.replace`；事件日志先校验后追加。
- 阶段一只管理一个分支中的一个活动任务；CI 无法唯一解析任务时默认失败。
- 本地最终验证开始时，除当前任务 `.ai/tasks/TASK-ID/**` 治理记录外不得有未提交变化；验证绑定被审代码 `subject_commit`。后续只包含当前任务治理记录的 attestation commit 不改变被审代码版本，CI 会在 PR 最新 HEAD 重新验证并生成权威 evidence artifact。
- 本计划不授权自动执行提交、推送、合并、部署、删除或其他外部高风险动作。

### 0.3 每个任务的完成规则

每个任务按以下顺序完成：

1. 先运行任务指定的定向测试，确认基线状态；
2. 只修改任务列出的文件和必要的相邻测试；
3. 运行任务的定向验证；
4. 运行本章累计回归；
5. 检查 `git diff --check` 和 `git status --short`；
6. 在本文件中勾选已完成步骤并记录验证命令结果；
7. 先做需求符合性复核，再做代码质量复核。

除非用户在执行阶段明确要求，否则计划不包含 Git commit、push 或 PR 操作。

### 0.4 全局验证命令

工程骨架建立后，章节退出时统一运行：

```powershell
python -m pip install -e ".[dev]"
python -m ruff check .
python -m mypy src
python -m pytest
python -m pytest --cov=aiflow --cov-branch --cov-report=term-missing --cov-fail-under=85
python -m aiflow --help
git diff --check
```

确定性核心还必须满足：状态转换表、规则优先级表、批准失效表和 Gate 决策表中的每一行均至少有一个测试，不以总体覆盖率替代表驱动覆盖。

---

# 第 1 章：工程基线与可执行契约

## Task 1.1：建立 Python 工程与 CLI 骨架

**Artifacts / Locations:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/aiflow/__init__.py`
- Create: `src/aiflow/__main__.py`
- Create: `src/aiflow/cli.py`
- Create: `tests/conftest.py`
- Create: `tests/unit/test_cli.py`
- Review: `docs/superpowers/specs/2026-08-01-ai-code-collaboration-mvp-design.md`

- [ ] **Step 1: 建立打包配置**

在 `pyproject.toml` 中配置 setuptools 的 `src` layout、`aiflow = "aiflow.cli:main"` 控制台入口、Python 3.11 基线，以及全局约定中的运行和开发依赖。为 Ruff、mypy、pytest 和 coverage 写入统一配置；测试目录固定为 `tests`。`.gitignore` 忽略 `__pycache__/`、`.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/`、根目录 `.coverage`、根目录 `coverage.xml` 和本地虚拟环境；任务目录中被 evidence 引用的日志不由这些宽泛规则误排除。

- [ ] **Step 2: 建立最小可运行包**

在 `src/aiflow/__init__.py` 定义静态阶段一开发版本 `0.1.0.dev0`。`src/aiflow/__main__.py` 调用 `aiflow.cli.main()`。`cli.py` 实现根命令的 `--help`、`--version` 和统一退出入口；此任务不创建返回假成功的业务子命令。

- [ ] **Step 3: 建立 CLI 基线测试**

测试 `python -m aiflow --help` 返回 0、帮助文本包含产品说明，`python -m aiflow --version` 返回 `0.1.0.dev0`，未知参数返回非零且不打印 traceback。

- [ ] **Step 4: 验证工程骨架**

Run:

```powershell
python -m pip install -e ".[dev]"
python -m pytest tests/unit/test_cli.py -q
python -m ruff check pyproject.toml src tests
python -m mypy src
python -m aiflow --help
```

Expected: 所有命令成功；帮助和版本可用；没有未实现业务命令伪装成成功。

- [ ] **Step 5: 记录结果**

在本任务复核记录中保存安装命令、Python 版本和测试结果；勾选本任务步骤。

## Task 1.2：定义核心机器契约与 Schema

**Artifacts / Locations:**
- Create: `.ai/schemas/task.schema.json`
- Create: `.ai/schemas/decision-unit.schema.json`
- Create: `.ai/schemas/classification.schema.json`
- Create: `.ai/schemas/ask-options.schema.json`
- Create: `.ai/schemas/approval.schema.json`
- Create: `.ai/schemas/event.schema.json`
- Create: `.ai/schemas/evidence.schema.json`
- Create: `.ai/repository-id`
- Create: `src/aiflow/contracts.py`
- Create: `tests/unit/test_contracts.py`
- Create: `tests/fixtures/contracts/valid/`
- Create: `tests/fixtures/contracts/invalid/`

- [ ] **Step 1: 固定公共字段约定**

所有机器契约使用 `schema_version: "1.0"`。任务 ID 使用 `^TASK-[0-9]{4,}$`，决策单元 ID 使用 `^DU-[0-9]{3,}$`。状态、分流、验证等级和批准类型均使用设计说明中的封闭枚举；Schema 对机器记录设置 `additionalProperties: false`。

- [ ] **Step 2: 定义任务和决策单元 Schema**

`task.schema.json` 必填：任务 ID、目标、稳定 `repository_id`、分支、基础 commit、被审代码 `subject_commit`、工作树脏状态、允许范围、禁止动作、当前状态、创建和更新时间、决策单元列表。绝对 `repository_path_at_creation` 只允许作为诊断字段，不参与身份或版本摘要。`decision-unit.schema.json` 必填：ID、目标、输入、计划动作、影响范围、可逆性、验证方法、外部副作用和权限要求。

- [ ] **Step 3: 定义输出和审计 Schema**

`classification` 必须包含每个决策单元的 route、verification level、规则编号、解释、Policy 摘要和时间；`approval` 必须包含类型、操作者、理由、规格摘要、Policy 摘要和适用 `subject_commit`；`event` 必须包含递增序号、前后状态、事件类型、操作者、时间和负载；`evidence` 必须包含 `subject_commit`，CI evidence 还必须包含最新 `attestation_head`、检查结果、日志引用、未验证项和总体结论。

- [ ] **Step 4: 实现统一验证接口**

`contracts.py` 提供按契约名称加载 Schema、验证 Python 对象、返回按 JSON Pointer 排序的稳定错误列表，以及抛出领域校验异常的接口。错误中不得包含完整环境变量或密钥值。

- [ ] **Step 5: 建立正反例夹具**

每个 Schema 至少提供一个有效样例和三个无效样例，分别覆盖缺少必填字段、非法枚举或 ID、未知字段。增加交叉字段测试：REVIEW 批准缺少 `subject_commit`、CI 证据缺少 `attestation_head`、通过证据包含失败检查、任务当前状态与最后事件状态不一致时必须拒绝。

- [ ] **Step 6: 生成稳定仓库 ID**

使用 Python `uuid.uuid4()` 生成一次仓库 ID，以纯 UUID 文本写入 `.ai/repository-id` 并纳入版本控制。契约测试确认它可解析、内容只有一行，且复制仓库到不同绝对路径后 `repository_id` 保持不变。

- [ ] **Step 7: 验证契约**

Run:

```powershell
python -m pytest tests/unit/test_contracts.py -q
python -m ruff check src/aiflow/contracts.py tests/unit/test_contracts.py
python -m mypy src/aiflow/contracts.py
```

Expected: 所有有效样例通过；每个无效样例产生稳定、可定位的错误；仓库 ID 在不同 checkout 路径不变；交叉字段错误不会被 JSON Schema 基础校验漏掉。

## Task 1.3：建立 Policy、模板及其 Schema

**Artifacts / Locations:**
- Create: `.ai/schemas/policy.schema.json`
- Create: `.ai/policy/hard-rules.yaml`
- Create: `.ai/policy/routing.yaml`
- Create: `.ai/policy/verification-levels.yaml`
- Create: `.ai/policy/permissions.yaml`
- Create: `.ai/templates/task.yaml`
- Create: `.ai/templates/spec.md`
- Create: `.ai/templates/ask.md`
- Create: `.ai/templates/review-package.md`
- Create: `.ai/templates/evidence.json`
- Create: `tests/integration/test_templates_and_policy.py`

- [ ] **Step 1: 定义 Policy 顶层结构**

`policy.schema.json` 要求每个文件包含 `schema_version`、`policy_version` 和对应规则集合。规则 ID 在全部 Policy 文件中唯一；优先级为整数；未知谓词和未知验证检查必须拒绝。

- [ ] **Step 2: 写入阶段一硬规则**

至少定义并编号以下规则：凭据或敏感数据拟发送到外部为 BLOCK；不可逆动作且无已验证备份为 BLOCK；验证工具缺失为 BLOCK；生产数据删除、密钥、鉴权、CI/CD、部署或真实外部动作至少 REVIEW；存在多个合理业务方向为 ASK；只有范围明确、低影响、可恢复、可自动验证且无外部副作用时才允许 AUTO。未命中显式 AUTO 时默认 REVIEW。

- [ ] **Step 3: 写入 V0/V1 与权限策略**

V0 必含契约、范围、`ruff check`、`ruff format --check` 和 Smoke；V1 在 V0 基础上增加单元测试、回归测试、mypy，以及先由 pytest-cov 生成分支覆盖 XML、再由 diff-cover 检查 `base_commit..subject_commit` 变更行不低于 90%。命令参数只允许 `{python}`、`{repository_root}`、`{base_commit}`、`{subject_commit}`、`{task_id}` 和 `{run_dir}` 六种安全替换变量，替换后仍以参数数组执行；覆盖检查的环境覆盖只允许 `COVERAGE_FILE={run_dir}/.coverage`。本地 `run_dir` 位于当前任务 `logs/<run-id>/`，CI 位于 runner 临时目录。权限策略明确禁止阶段一自动 push、merge、deploy、delete、secret export 和付费外部调用。

- [ ] **Step 4: 建立人类模板**

`spec.md` 必含目标、范围、非目标、验收条件、禁止动作、错误行为和回滚；`ask.md` 必含 2—4 个选项所需字段；`review-package.md` 必含审核目标、背景、代码地图、语义变更、风险、证据、审核问题和推荐结论；模板不包含 `TBD`、`TODO` 或“稍后补充”。

- [ ] **Step 5: 建立模板与 Policy 测试**

逐个解析 YAML/JSON 模板；验证所有 Markdown 必需标题恰好存在；验证规则 ID 唯一、优先级可排序、命令为参数数组、禁止动作集合完整。额外测试未知谓词、重复规则 ID、缺少默认 REVIEW、未知命令或环境替换变量、`run_dir` 解析到允许目录外、diff-cover 阈值不是 90，以及 V1 缺少 V0 检查时失败。

- [ ] **Step 6: 验证产物**

Run:

```powershell
python -m pytest tests/integration/test_templates_and_policy.py -q
rg -n "TBD|TODO|稍后补充" .ai/templates .ai/policy
```

Expected: 测试通过；`rg` 无匹配；Policy 可以完全由程序解析且不存在静默默认放行。

## Task 1.4：建立四类黄金场景

**Artifacts / Locations:**
- Create: `examples/scenarios/README.md`
- Create: `examples/scenarios/auto-doc-edit/input.yaml`
- Create: `examples/scenarios/auto-doc-edit/expected.json`
- Create: `examples/scenarios/ask-conflict-strategy/input.yaml`
- Create: `examples/scenarios/ask-conflict-strategy/expected.json`
- Create: `examples/scenarios/review-workflow-change/input.yaml`
- Create: `examples/scenarios/review-workflow-change/expected.json`
- Create: `examples/scenarios/block-no-backup/input.yaml`
- Create: `examples/scenarios/block-no-backup/expected.json`
- Create: `tests/integration/test_golden_contracts.py`

- [ ] **Step 1: 定义 AUTO 场景**

目标为仅修改 `docs/**` 内普通说明文字；无外部副作用、可由 diff 和 Markdown 检查验证、可通过 Git 恢复。预期 route 为 AUTO、verification level 为 V0，并记录命中的显式低风险规则。

- [ ] **Step 2: 定义 ASK 场景**

目标为选择冲突报告输出 Markdown、JSON 或同时输出；三种方案均合理且有不同兼容和维护成本。预期 route 为 ASK、verification level 为 V1；预期文件包含三个完整选项和推荐项上限一项。

- [ ] **Step 3: 定义 REVIEW 场景**

目标为修改 `.github/workflows/ai-quality-gate.yml`；影响 CI/CD，代码可恢复但会影响团队质量门。预期 route 为 REVIEW、verification level 为 V1，并要求规格批准和代码批准；不自动执行真实外部动作。

- [ ] **Step 4: 定义 BLOCK 场景**

目标为覆盖一批真实文件且没有已验证备份或 dry-run。预期 route 为 BLOCK；预期原因明确指出恢复条件为提供可验证备份和缩小目标范围，而不是只写“风险高”。

- [ ] **Step 5: 固定可比较结果**

每个 `expected.json` 包含 route、verification level、规则 ID、有序理由和下一允许状态。动态时间与仓库路径不得进入黄金比较字段。

- [ ] **Step 6: 验证黄金场景契约**

Run:

```powershell
python -m pytest tests/integration/test_golden_contracts.py -q
```

Expected: 四个输入和预期文件均满足 Schema；规则 ID 都存在于 Policy；场景之间没有复用同一风险描述伪装成不同模式。

## Task 1.5：完成第一章契约回归与基线说明

**Artifacts / Locations:**
- Create: `docs/implementation/chapter-01-contract-baseline.md`
- Modify: `tests/integration/test_templates_and_policy.py`
- Modify: `tests/integration/test_golden_contracts.py`
- Review: 本章全部产物

- [ ] **Step 1: 建立一键契约测试集合**

为 pytest 增加 `contract` 标记，覆盖 Schema、模板、Policy 和黄金场景；确保测试不依赖网络、用户主目录或当前时间。

- [ ] **Step 2: 写基线说明**

记录 Schema 版本规则、Policy 修改规则、目录职责、四个场景的目的，以及哪些字段会参与 SHA-256 摘要。说明阶段一不得无迁移地修改 `schema_version: "1.0"` 的含义。

- [ ] **Step 3: 运行第一章退出检查**

Run:

```powershell
python -m pytest -m contract -q
python -m ruff check .
python -m mypy src
python -m aiflow --help
git diff --check
```

Expected: 全部通过；所有模板可解析；黄金场景预期明确；没有占位文本。

- [ ] **Step 4: 章节双重复核**

需求复核：逐项比对设计说明第 4—9 节。质量复核：确认 Schema 没有重复来源、Policy 没有代码化副本、测试错误消息可定位。两项均通过后才能开始第二章。

---

# 第 2 章：任务记录与状态核心

## Task 2.1：实现领域错误、任务 ID 与原子存储

**Artifacts / Locations:**
- Create: `src/aiflow/errors.py`
- Create: `src/aiflow/storage.py`
- Create: `tests/unit/test_storage.py`
- Review: `.ai/schemas/task.schema.json`
- Review: `.ai/schemas/event.schema.json`

- [ ] **Step 1: 定义稳定错误类型**

建立 `AiflowError`、`ContractError`、`StorageError`、`StateTransitionError`、`PolicyError`、`VerificationError` 和 `GateError`。每类错误提供稳定错误码、人类消息和机器细节；CLI 默认不输出 traceback。

- [ ] **Step 2: 实现安全路径解析**

任务根目录固定为仓库内 `.ai/tasks`。拒绝绝对任务子路径、`..`、符号链接逃逸和不符合 ID 格式的目录。读取时确认解析后的绝对路径仍位于任务根目录。

- [ ] **Step 3: 实现任务 ID 预留**

扫描合法 `TASK-*` 目录并尝试以 `mkdir(exist_ok=False)` 原子创建下一个编号；发生竞争时重新扫描重试，最多重试十次后返回明确错误。不以单独计数器文件作为唯一来源。

- [ ] **Step 4: 实现原子 YAML/JSON 写入**

写入同目录临时文件，刷新并关闭后使用 `os.replace`。临时文件名包含目标名和随机后缀；异常时清理本次临时文件，不删除既有任务文件。读取后立即执行契约校验。

- [ ] **Step 5: 测试存储边界**

覆盖首次 ID、已有多个 ID、非法目录名、并发预留模拟、写入中断、损坏 YAML/JSON、路径逃逸和未知 Schema 版本。

- [ ] **Step 6: 验证存储层**

Run:

```powershell
python -m pytest tests/unit/test_storage.py -q
python -m ruff check src/aiflow/errors.py src/aiflow/storage.py tests/unit/test_storage.py
python -m mypy src/aiflow/errors.py src/aiflow/storage.py
```

Expected: 所有失败都保留既有文件；路径逃逸被拒绝；任务 ID 不重复。

## Task 2.2：实现 Git 上下文采集

**Artifacts / Locations:**
- Create: `src/aiflow/git_context.py`
- Create: `tests/unit/test_git_context.py`
- Modify: `.ai/schemas/task.schema.json`
- Review: `.ai/repository-id`

- [ ] **Step 1: 定义 Git 命令边界**

只通过参数数组调用 `git rev-parse --show-toplevel`、`git rev-parse HEAD`、`git symbolic-ref --short -q HEAD` 和 `git status --porcelain=v1`。命令超时为十秒；stdout 按 UTF-8 解码并去除末尾换行。

- [ ] **Step 2: 采集规范化上下文**

读取并校验 `.ai/repository-id`，返回稳定仓库 ID、仅供诊断的绝对路径、分支或 `DETACHED`、HEAD、工作树是否脏以及脏文件相对路径。路径统一为 `/` 分隔符写入诊断字段；身份比较只使用仓库 ID，不读取业务文件内容。

- [ ] **Step 3: 处理失败条件**

非 Git 目录、无 commit 的空仓库、Git 命令超时和无法解析 HEAD 均返回稳定错误。Detached HEAD 允许只读记录，但 `start` 默认拒绝，除非显式传入 `--allow-detached`。

- [ ] **Step 4: 测试真实临时仓库**

测试创建临时 Git 仓库、初始 commit、脏文件、分支切换和 detached HEAD；把同一仓库复制到不同绝对路径后仓库 ID 必须相同。测试不修改当前工作区 Git 配置；提交身份通过命令级 `-c user.name=... -c user.email=...` 提供。

- [ ] **Step 5: 验证 Git 上下文**

Run:

```powershell
python -m pytest tests/unit/test_git_context.py -q
```

Expected: 清洁、脏、分支和 detached 场景结果稳定；错误不泄露环境变量。

## Task 2.3：实现 `aiflow start`

**Artifacts / Locations:**
- Modify: `src/aiflow/cli.py`
- Modify: `src/aiflow/storage.py`
- Create: `src/aiflow/task_service.py`
- Create: `tests/integration/test_start_command.py`
- Review: `.ai/templates/task.yaml`

- [ ] **Step 1: 定义命令参数**

支持 `aiflow start --objective <text> --allow <glob>`，`--allow` 可重复；支持可重复的 `--forbid-action`，缺省禁止动作从 permissions Policy 继承。目标去除首尾空白后不能为空；至少一个允许范围；禁止 `**` 单独作为无边界范围。

- [ ] **Step 2: 创建完整初始记录**

采集稳定仓库 ID 和 Git 上下文，预留任务 ID，写入 `task.yaml`、初始 `events.jsonl`、从模板生成的 `spec.md`、空但契约合法的 `approvals.json`。初始状态为 `NEW`，`base_commit` 和 `subject_commit` 均为启动时 HEAD；绝对路径只写入诊断字段。

- [ ] **Step 3: 保证操作幂等和可恢复**

命令成功后打印任务 ID 和绝对任务路径。任一必需文件写入失败时保留带 `creation_failed` 标记的预留目录，下一次运行能够明确报告并通过 `start --recover TASK-xxxx` 完成或回滚本次创建；不得静默复用半完成任务。

- [ ] **Step 4: 建立命令测试**

覆盖正常创建、空目标、无允许范围、全仓库无边界范围、非 Git 仓库、detached HEAD、脏工作树记录、重复恢复和中途写入失败。

- [ ] **Step 5: 验证 `start`**

Run:

```powershell
python -m pytest tests/integration/test_start_command.py -q
python -m aiflow start --help
```

Expected: 帮助列出全部参数；成功任务满足 Schema；失败不产生可被误认为有效的任务。

## Task 2.4：实现状态转换和可重放事件日志

**Artifacts / Locations:**
- Create: `src/aiflow/state.py`
- Create: `tests/unit/test_state.py`
- Create: `tests/fixtures/state/transitions.json`
- Modify: `src/aiflow/task_service.py`

- [ ] **Step 1: 将状态图编码为数据**

在一个不可变转换表中列出设计说明的全部允许边；为每条边指定触发事件和前置条件类别。明确包含 `VERIFYING→VERIFIED`、`VERIFIED→APPROVED_FOR_MERGE`、`VERIFIED→WAITING_FOR_FINAL_REVIEW`、`WAITING_FOR_FINAL_REVIEW→APPROVED_FOR_MERGE` 和 `APPROVED_FOR_MERGE→MERGED`，从而分别形成 AUTO/ASK 直达放行路径和 REVIEW 审批路径。另建封闭的非状态事件集合，例如 `spec_frozen`、`approval_recorded` 和 `evidence_generated`；这些事件要求 `from_state == to_state`，但不能被普通调用方伪装成状态转换。测试夹具 `transitions.json` 是期望表，不由生产代码生成。

- [ ] **Step 2: 实现转换校验**

转换接口接收当前任务、目标状态、事件类型、操作者和负载；先检查允许边或封闭非状态事件及其前置条件，再创建包含递增序号、前后状态和 UTC 时间的事件。非法跳级、倒退、未知自循环事件或缺少前置条件返回 `StateTransitionError`。

- [ ] **Step 3: 实现事件重放**

从初始事件按序号重放，检查无重复或缺失序号、每个 `from_state` 等于上个 `to_state`、事件满足 Schema。重放终态必须等于 `task.yaml` 当前状态，否则任务无效且 Gate 失败。

- [ ] **Step 4: 处理写入顺序和中断恢复**

状态变更先在内存生成新事件和新任务记录，再写新任务临时文件、追加事件、原子替换任务文件。若最后替换失败，下一次读取以合法事件重放结果修复物化状态并记录 `state_recovered` 事件；不得丢弃已成功追加的事件。

- [ ] **Step 5: 表驱动测试每条边**

对 `transitions.json` 中每条允许边至少测试一次；对每个状态至少测试一个非法目标；覆盖事件缺号、重复号、篡改前态、任务状态不一致和恢复路径。

- [ ] **Step 6: 验证状态核心**

Run:

```powershell
python -m pytest tests/unit/test_state.py -q
```

Expected: 允许边全部通过，禁止边全部拒绝，事件重放结果确定。

## Task 2.5：实现 `begin`、`close` 与重试规则

**Artifacts / Locations:**
- Modify: `src/aiflow/cli.py`
- Modify: `src/aiflow/task_service.py`
- Modify: `src/aiflow/state.py`
- Create: `tests/integration/test_begin_close_commands.py`

- [ ] **Step 1: 实现 `begin` 正常路径**

`aiflow begin TASK-ID --actor <id>` 只允许从 `READY_TO_IMPLEMENT` 进入 `IMPLEMENTING`，并确认规格已冻结、当前分类存在、所需规格批准有效、当前 Git 上下文未超出允许的基础条件。

- [ ] **Step 2: 实现失败重试**

从 `FAILED` 重试必须传入非空 `--reason`。若失败记录包含范围扩大、新依赖、新权限、无法验证或高风险副作用标记，则 `begin` 拒绝并要求先执行 `escalate`。

- [ ] **Step 3: 实现 `close`**

`aiflow close TASK-ID --result merged --merge-commit <sha> --actor <id>` 只允许从 `APPROVED_FOR_MERGE` 进入 `MERGED`。命令验证 merge commit 存在于仓库，记录外部结果但不运行 Git merge、push 或远程 API。

- [ ] **Step 4: 测试命令边界**

覆盖正常 begin、缺失规格、无效批准、普通失败重试、必须升级的失败、提前 close、未知 merge commit 和成功 close。

- [ ] **Step 5: 验证命令**

Run:

```powershell
python -m pytest tests/integration/test_begin_close_commands.py -q
python -m aiflow begin --help
python -m aiflow close --help
```

Expected: 两个命令只记录合法状态；没有任何远程或破坏性 Git 调用。

## Task 2.6：实现 `status` 和第二章退出检查

**Artifacts / Locations:**
- Modify: `src/aiflow/cli.py`
- Create: `src/aiflow/status_service.py`
- Create: `tests/integration/test_status_command.py`
- Create: `docs/implementation/chapter-02-task-state.md`

- [ ] **Step 1: 定义状态摘要模型**

摘要包含任务 ID、目标、稳定仓库 ID、当前状态、route/verification 是否已确定、允许的下一事件、缺失条件、`base_commit`、被审 `subject_commit`、当前观测 HEAD、工作树状态、批准与证据新鲜度。尚不存在的分类或证据显示为 `not_available`，不显示为通过。

- [ ] **Step 2: 实现双格式输出**

`aiflow status TASK-ID` 输出简洁文本；`--format json` 输出稳定 JSON 并满足内部摘要 Schema。只读命令不得修改时间戳或任务文件。

- [ ] **Step 3: 测试每个主状态**

为 NEW、WAITING、READY、IMPLEMENTING、FAILED、VERIFIED、APPROVED 和 MERGED 构造任务；验证下一动作与缺失条件准确。损坏事件日志或状态不一致时返回非零。

- [ ] **Step 4: 写状态章节说明**

说明任务目录、原子写入、恢复流程、状态图、`start/begin/status/close` 示例和失败排查，不重复 Policy 规则。

- [ ] **Step 5: 运行第二章退出检查**

Run:

```powershell
python -m pytest tests/unit/test_storage.py tests/unit/test_git_context.py tests/unit/test_state.py -q
python -m pytest tests/integration/test_start_command.py tests/integration/test_begin_close_commands.py tests/integration/test_status_command.py -q
python -m ruff check .
python -m mypy src
git diff --check
```

Expected: 全部通过；所有状态变化均可重放；中断或直接篡改不会被当作有效状态。

- [ ] **Step 6: 章节双重复核**

需求复核：状态、版本和恢复行为符合设计说明第 7 节。质量复核：存储无路径逃逸、状态表无重复来源、只读状态命令无副作用。通过后开始第三章。

---

# 第 3 章：分流与验证等级引擎

## Task 3.1：实现 Policy 加载、校验和稳定摘要

**Artifacts / Locations:**
- Create: `src/aiflow/policy.py`
- Create: `tests/unit/test_policy.py`
- Create: `tests/fixtures/policy/invalid/`
- Review: `.ai/policy/`
- Review: `.ai/schemas/policy.schema.json`

- [ ] **Step 1: 实现 Policy 根目录解析**

默认从仓库 `.ai/policy` 读取四个固定文件；允许测试显式传入替代目录。缺少文件、额外同名冲突文件、符号链接逃逸或读取失败均返回 `PolicyError`。

- [ ] **Step 2: 安全解析并校验**

使用 `yaml.safe_load`，先执行 Schema 校验，再执行跨文件校验：规则 ID 全局唯一、优先级唯一或有稳定次序、所有验证检查已定义、所有权限引用存在、默认 REVIEW 规则存在且位于显式安全规则之后。

- [ ] **Step 3: 计算规范化摘要**

将四个已校验对象按固定文件名和稳定键排序转成规范化 JSON，计算 SHA-256。换行或 YAML 注释变化不改变摘要；有效规则值变化必须改变摘要。

- [ ] **Step 4: 测试失败和摘要稳定性**

覆盖缺文件、未知字段、重复 ID、未知谓词、命令字符串而非数组、引用不存在、注释变化和规则值变化。

- [ ] **Step 5: 验证 Policy 层**

Run:

```powershell
python -m pytest tests/unit/test_policy.py -q
```

Expected: 有效 Policy 得到稳定摘要；任何不完整或矛盾 Policy 均不能进入分类。

## Task 3.2：实现决策单元输入与受限谓词

**Artifacts / Locations:**
- Create: `src/aiflow/decision_units.py`
- Create: `src/aiflow/predicates.py`
- Create: `tests/unit/test_decision_units.py`
- Create: `tests/unit/test_predicates.py`
- Modify: `.ai/templates/task.yaml`

- [ ] **Step 1: 实现决策单元解析**

从 `task.yaml` 的 `decision_units` 读取对象，按 ID 排序并执行 Schema 与交叉字段校验。拒绝重复 ID、空影响范围、无法识别的可逆性和未声明权限。

- [ ] **Step 2: 定义受支持谓词集合**

只支持 `equals`、`not_equals`、`in`、`contains_any`、`contains_all`、`exists`、`is_empty` 和数值 `greater_than_or_equal`。字段路径使用受限点号语法；禁止 Python 表达式、正则执行和任意函数名。

- [ ] **Step 3: 实现稳定匹配结果**

每个谓词返回布尔结果和不含敏感值的解释片段。字段缺失按规则配置的 `missing` 策略处理；硬风险字段缺失默认不匹配 AUTO，并触发保守规则。

- [ ] **Step 4: 测试解析和谓词**

覆盖所有谓词、嵌套字段、列表、缺失字段、错误类型、重复 ID、未知谓词和试图注入表达式的值。

- [ ] **Step 5: 验证决策单元层**

Run:

```powershell
python -m pytest tests/unit/test_decision_units.py tests/unit/test_predicates.py -q
```

Expected: 谓词无 `eval` 或 Shell 执行；相同输入返回相同结果和解释。

## Task 3.3：实现硬规则与 route 汇总

**Artifacts / Locations:**
- Create: `src/aiflow/routing.py`
- Create: `tests/unit/test_routing.py`
- Create: `tests/fixtures/routing/decision-table.json`
- Review: `.ai/policy/hard-rules.yaml`
- Review: `.ai/policy/routing.yaml`

- [ ] **Step 1: 实现单元级规则执行**

按 Policy 明确优先级评估所有规则，保存全部命中规则，但由 `BLOCK > REVIEW > ASK > AUTO` 决定有效 route。无显式安全规则命中时使用具名 `ROUTE-DEFAULT-REVIEW`，而不是隐式 AUTO。

- [ ] **Step 2: 实现冲突和配置失败处理**

同一优先级给出不兼容结论、BLOCK 规则引用缺失恢复条件、AUTO 规则没有完整护栏时分类失败并进入可解释 BLOCK，不得靠文件顺序偶然决定。

- [ ] **Step 3: 实现任务级安全汇总**

保留每个决策单元的原始 route。任务 `effective_route` 只汇总未完成单元中的最高等级；全部单元完成后显示 `completed`，不回写或覆盖单元 route。

- [ ] **Step 4: 固定规则决策表**

`decision-table.json` 至少包含每个硬规则一例、每对冲突 route 一例、无命中默认 REVIEW、一项任务内多单元汇总和已完成单元不参与汇总。

- [ ] **Step 5: 验证 route 引擎**

Run:

```powershell
python -m pytest tests/unit/test_routing.py -q
```

Expected: 决策表每一行通过；route 优先级无代码外副本；AUTO 只能由显式完整护栏产生。

## Task 3.4：独立实现 V0/V1 判定

**Artifacts / Locations:**
- Create: `src/aiflow/verification_level.py`
- Create: `tests/unit/test_verification_level.py`
- Create: `tests/fixtures/verification/level-table.json`
- Review: `.ai/policy/verification-levels.yaml`

- [ ] **Step 1: 定义独立输入**

验证等级只读取影响范围、行为变化、跨模块程度、可用检查、错误可检测性和 Policy，不读取 route 作为等级映射。route 仅可作为 Gate 的批准要求，不能直接决定 V0/V1。

- [ ] **Step 2: 实现 V0/V1 规则**

机械、局部、非行为性且具备完整 V0 检查的单元可为 V0；任何行为变化、代码修改、跨文件交互或回归风险为 V1。需要的验证工具缺失时产生 BLOCK 原因，不降为 V0。

- [ ] **Step 3: 实现任务级验证汇总**

任务验证等级为未完成单元的最高 V 等级。汇总结果保留每个单元的规则 ID和解释，不能只输出最终 V1。

- [ ] **Step 4: 固定独立性测试**

为 `AUTO+V1`、`ASK+V0`、`REVIEW+V1` 和工具缺失 BLOCK 建立案例，证明 route 与 verification level 没有一一映射。

- [ ] **Step 5: 验证等级引擎**

Run:

```powershell
python -m pytest tests/unit/test_verification_level.py -q
```

Expected: 所有等级表案例通过；相同验证属性在不同 route 下得到相同 V 等级。

## Task 3.5：实现 `aiflow classify`

**Artifacts / Locations:**
- Modify: `src/aiflow/cli.py`
- Create: `src/aiflow/classification_service.py`
- Modify: `src/aiflow/state.py`
- Create: `tests/integration/test_classify_command.py`

- [ ] **Step 1: 定义命令输入与前置状态**

`aiflow classify TASK-ID --actor <id>` 允许 NEW 首次分类，以及记录解除条件后的 BLOCKED/ESCALATED 重新分类。命令拒绝缺少决策单元、损坏 Policy、Git 仓库不匹配和未解释的范围扩大。

- [ ] **Step 2: 生成完整分类记录**

对每个单元保存 route、V 等级、命中规则、有序解释；保存 Policy 版本、Policy SHA-256、分类输入 SHA-256、`base_commit`、分类时 `subject_commit` 和时间。动态展示字段及绝对 checkout 路径不参与输入摘要。

- [ ] **Step 3: 推进状态**

存在 BLOCK 时进入 BLOCKED；否则存在 ASK 时进入 WAITING_FOR_ASK；否则需要实现前规格批准的 REVIEW 进入 WAITING_FOR_SPEC_REVIEW；其余进入 READY_TO_IMPLEMENT。多单元任务采用最严格未满足前置条件。

- [ ] **Step 4: 防止无授权降级**

重新分类结果低于既有 route 或 V 等级时，必须存在记录条件解除或人工授权的事件；Agent 仅提供普通 actor 时命令拒绝。升级无需人工授权，但必须记录原因。

- [ ] **Step 5: 测试命令和幂等性**

覆盖四类场景、重复分类相同输入、Policy 变化、输入变化、无授权降级、允许升级和分类记录写入失败。

- [ ] **Step 6: 验证 classify**

Run:

```powershell
python -m pytest tests/integration/test_classify_command.py -q
python -m aiflow classify --help
```

Expected: 相同输入幂等；分类文件满足 Schema；状态与最严格未满足条件一致。

## Task 3.6：运行四类黄金场景并完成第三章退出检查

**Artifacts / Locations:**
- Create: `tests/integration/test_golden_classification.py`
- Create: `docs/implementation/chapter-03-routing-verification.md`
- Review: `examples/scenarios/`

- [ ] **Step 1: 建立黄金分类参数化测试**

逐个加载场景 `input.yaml`，使用真实 Policy 和分类服务，比较 route、V 等级、规则 ID、有序理由和下一状态；禁止在测试中 mock 路由结果。

- [ ] **Step 2: 添加变形测试**

对 AUTO 场景依次增加 CI 路径、外部副作用和缺失验证工具，预期分别升级 REVIEW、升级 REVIEW 或 BLOCK、进入 BLOCK。移除这些变化后必须恢复原分类，但降级需要合法解除记录。

- [ ] **Step 3: 写分类说明**

说明决策单元、硬规则、默认 REVIEW、route 汇总、V0/V1 独立性、规则解释和 Policy 摘要；给出四类命令输出样例，不引入评分公式。

- [ ] **Step 4: 运行第三章退出检查**

Run:

```powershell
python -m pytest tests/unit/test_policy.py tests/unit/test_decision_units.py tests/unit/test_predicates.py tests/unit/test_routing.py tests/unit/test_verification_level.py -q
python -m pytest tests/integration/test_classify_command.py tests/integration/test_golden_classification.py -q
python -m ruff check .
python -m mypy src
git diff --check
```

Expected: 四类黄金结果符合预期；所有决策表行通过；每项结论含可审计规则编号。

- [ ] **Step 5: 章节双重复核**

需求复核：逐项比对原始设计的决策单元、硬规则、AUTO/ASK/REVIEW/BLOCK 和分流/验证独立原则。质量复核：无 `eval`、无隐式 AUTO、无 route 到 V 等级的硬编码映射。通过后开始第四章。

---

# 第 4 章：治理交互流程

## Task 4.1：实现统一工作流前置条件与规格冻结

**Artifacts / Locations:**
- Create: `src/aiflow/workflow.py`
- Create: `src/aiflow/specification.py`
- Modify: `src/aiflow/cli.py`
- Create: `tests/unit/test_workflow.py`
- Create: `tests/unit/test_specification.py`
- Create: `tests/integration/test_freeze_command.py`
- Review: `.ai/templates/spec.md`

- [ ] **Step 1: 建立前置条件模型**

定义结构化条件：状态允许、分类新鲜、Policy 摘要匹配、规格完整或冻结、必要批准存在、Git 上下文有效、范围未扩大和动作权限允许。每个条件返回 `pass/fail/not_applicable` 与稳定原因码。

- [ ] **Step 2: 实现规格完整性检查**

解析 `spec.md` 必需标题和内容；目标、范围、验收条件、禁止动作、错误行为和回滚均不能为空。禁止 `TBD`、`TODO`、空复选框作为唯一验收条件和“按需处理”等不可执行措辞。

- [ ] **Step 3: 实现 `aiflow freeze`**

`aiflow freeze TASK-ID --actor <id>` 在 NEW 已补充规格、CLASSIFIED、WAITING_FOR_SPEC_REVIEW 或 READY_TO_IMPLEMENT 状态校验规格，规范化换行并计算 SHA-256，将摘要和冻结时间写入任务记录与事件，但不隐式批准或改变 route。ASK 的 `answer` 命令复用同一服务，在写入决定后原子冻结更新后的规格。冻结后直接编辑导致摘要不一致，所有依赖该规格的操作失败，必须显式重新冻结并执行失效规则。

- [ ] **Step 4: 测试条件组合**

覆盖每种缺失条件、多个条件同时失败、规格完整、错误状态、freeze 不改变审批状态、规格篡改、重新冻结和 ASK answer 原子冻结。错误输出按安全优先级排序，不因字典顺序变化。

- [ ] **Step 5: 验证工作流核心**

Run:

```powershell
python -m pytest tests/unit/test_workflow.py tests/unit/test_specification.py tests/integration/test_freeze_command.py -q
python -m aiflow freeze --help
```

Expected: 所有工作流命令可复用同一条件模型；freeze 有真实 CLI 入口且不等于批准；规格变动可以确定性检测。

## Task 4.2：实现 ASK 选项校验与 `answer`

**Artifacts / Locations:**
- Modify: `src/aiflow/cli.py`
- Create: `src/aiflow/ask_service.py`
- Modify: `src/aiflow/workflow.py`
- Create: `tests/integration/test_answer_command.py`
- Review: `.ai/schemas/ask-options.schema.json`
- Review: `.ai/templates/ask.md`

- [ ] **Step 1: 定义 ASK 输入文件**

命令接收 `--options-file <json>`；文件必须有 2—4 个选项，每个包含 ID、说明、收益、代价和风险，最多一个推荐项。选项 ID 唯一；选择必须引用其中一个 ID。

- [ ] **Step 2: 实现 `answer`**

`aiflow answer TASK-ID --options-file <path> --select <id> --actor <id> --reason <text>` 只允许 WAITING_FOR_ASK。保存完整选项和选择到事件负载，生成或更新 `decisions.md` 的稳定人类摘要，并把选择写入规格的“已冻结决策”节。

- [ ] **Step 3: 冻结规格并推进状态**

回答后重新校验并冻结规格。若任务还包含需要规格审核的 REVIEW 单元，进入 WAITING_FOR_SPEC_REVIEW；否则进入 READY_TO_IMPLEMENT。ASK 回答不自动批准 REVIEW。

- [ ] **Step 4: 区分结构和语义职责**

CLI 只验证结构、数量和引用一致性；`ai-flow` Skill 后续要求 Agent 检查选项实质差异。命令输出明确说明程序未证明语义互斥，避免虚假保证。

- [ ] **Step 5: 测试 ASK 路径**

覆盖 1/2/4/5 个选项、重复 ID、两个推荐项、选择不存在、空理由、错误状态、ASK+REVIEW 混合任务、规格冻结和重复回答。

- [ ] **Step 6: 验证 answer**

Run:

```powershell
python -m pytest tests/integration/test_answer_command.py -q
python -m aiflow answer --help
```

Expected: 合法选择可重放；非法选项不修改任务；ASK 不绕过 REVIEW。

## Task 4.3：实现审核包校验与三类批准

**Artifacts / Locations:**
- Create: `src/aiflow/review.py`
- Create: `src/aiflow/approval.py`
- Modify: `src/aiflow/cli.py`
- Create: `tests/unit/test_review_package.py`
- Create: `tests/integration/test_approve_command.py`
- Review: `.ai/templates/review-package.md`
- Review: `.ai/schemas/approval.schema.json`

- [ ] **Step 1: 校验审核包**

要求八个必需节均存在且非空；“验证证据”必须区分已验证和未验证；“审核问题”至少一个；“推荐结论”只能是 APPROVE、APPROVE_WITH_CONDITIONS、REQUEST_CHANGES、REJECT 或 BLOCKED。

- [ ] **Step 2: 实现规格批准**

`aiflow approve TASK-ID --type spec --actor <id> --reason <text>` 只允许 WAITING_FOR_SPEC_REVIEW，绑定规格摘要、Policy 摘要和审核时的基础代码上下文。批准后进入 READY_TO_IMPLEMENT；规格变化使其失效。

- [ ] **Step 3: 实现代码批准**

`--type code` 只允许 WAITING_FOR_FINAL_REVIEW，要求完整审核包、通过且新鲜的 evidence，且工作树除当前任务治理记录外没有变化。批准绑定被审 `subject_commit`、规格和 Policy；任何治理目录外变化，或规格/Policy 变化，使其失效。有效批准写入后通过显式状态事件把任务转入 `APPROVED_FOR_MERGE`。批准本身写入当前任务治理记录，因此不得要求 approval 文件写入后 HEAD 仍等于 `subject_commit`。

- [ ] **Step 4: 实现动作批准**

`--type action` 还需 `--action-file <json>`，其中包含动作类型、精确目标、参数摘要、适用 commit、条件、失效时间和 `single_use: true`。阶段一只记录批准，不调用动作。目标或参数摘要变化即失效。

- [ ] **Step 5: 生成批准记录**

`approvals.json` 保存当前批准集合，事件日志保存每次批准、拒绝和失效。重新执行相同批准参数幂等；不同理由或版本生成新事件，不覆盖历史。

- [ ] **Step 6: 测试三类批准和失效**

覆盖正确状态、错误状态、缺审核包、缺 evidence、业务文件脏变化、仅当前任务治理记录变化、规格变化、Policy 变化、`subject_commit` 后出现治理目录外 commit、动作目标变化和到期批准。

- [ ] **Step 7: 验证 approve**

Run:

```powershell
python -m pytest tests/unit/test_review_package.py tests/integration/test_approve_command.py -q
python -m aiflow approve --help
```

Expected: 三类批准互不替代；过期或版本不符批准不能满足 Gate。

## Task 4.4：实现 AUTO 预检和范围护栏

**Artifacts / Locations:**
- Create: `src/aiflow/scope.py`
- Modify: `src/aiflow/workflow.py`
- Modify: `src/aiflow/task_service.py`
- Create: `tests/unit/test_scope.py`
- Create: `tests/integration/test_auto_preflight.py`

- [ ] **Step 1: 实现路径范围匹配**

将 Git 相对路径规范化为 `/`，使用明确 glob 语义匹配 allowed scope；拒绝 `..`、绝对路径和仓库外符号链接。对 `.ai/tasks/<current-task>/**` 的治理记录单独列入允许的系统写入，不把它视为业务范围扩张。

- [ ] **Step 2: 实现差异路径采集**

读取基础 commit 到当前 HEAD 的变更文件，并合并工作树已跟踪和未跟踪文件。排除明确列出的本地缓存产物；任何无法分类的路径保守判为超范围。

- [ ] **Step 3: 实现 AUTO 预检**

在 `begin` 和 `verify` 前检查所有未完成单元均为 AUTO、规格已冻结、无要求人工批准、无禁止动作、范围未扩大和验证配置完整。任一失败进入明确拒绝；发现新风险时建议 `escalate`。

- [ ] **Step 4: 测试范围边界**

覆盖允许文件、同名前缀越界、大小写差异、未跟踪文件、删除、重命名、符号链接、治理记录和多决策单元不同范围。

- [ ] **Step 5: 验证 AUTO 护栏**

Run:

```powershell
python -m pytest tests/unit/test_scope.py tests/integration/test_auto_preflight.py -q
```

Expected: AUTO 只能在完整护栏内开始；范围扩大不能被 glob 前缀误判为允许。

## Task 4.5：实现 BLOCK 条件与 `escalate`

**Artifacts / Locations:**
- Create: `src/aiflow/escalation.py`
- Modify: `src/aiflow/cli.py`
- Modify: `src/aiflow/state.py`
- Create: `tests/integration/test_escalate_command.py`

- [ ] **Step 1: 定义结构化升级原因**

支持范围扩大、连续验证失败、新依赖、新权限、网络或凭据需求、方向性发现、验证不可用、备份失效、任务描述变化，以及 Policy 或规格摘要变化。为后两类失效分别使用稳定原因码 `policy_changed` 和 `spec_changed`。所有原因都必须同时提供影响和下一步，不允许只有“有风险”。

- [ ] **Step 2: 实现 `escalate`**

`aiflow escalate TASK-ID --to ASK|REVIEW|BLOCK --reason-code <code> --impact <text> --next-step <text> --actor <id>` 校验新 route 不低于当前有效 route；保存原等级、新等级、触发信号、影响、下一步和已有成果处理方式。只有 `policy_changed`、`spec_changed` 等命名失效原因允许 `--to` 等于当前 route，用于 REVIEW→ESCALATED→重新 classify 为 REVIEW 这类同级重评；任意自定义原因的同级转换和所有降级均拒绝。BLOCK 目标进入 BLOCKED，其余目标进入 ESCALATED。

- [ ] **Step 3: 实现解除条件记录**

BLOCK 解除前必须通过事件记录每个恢复条件的证据引用。重新 classify 检查这些引用存在且与当前版本匹配。ESCALATED 重新分类保留旧分类历史。

- [ ] **Step 4: 测试升级和恢复**

覆盖所有原因码、AUTO→ASK、AUTO→REVIEW、ASK→REVIEW、REVIEW→BLOCK、REVIEW 使用 `policy_changed` 同级失效后进入 ESCALATED 并重新分类为 REVIEW、任意同级原因被拒绝、试图降级、缺影响说明、缺 `--next-step`、BLOCK 未解除和有完整证据后恢复。

- [ ] **Step 5: 验证 escalate**

Run:

```powershell
python -m pytest tests/integration/test_escalate_command.py -q
python -m aiflow escalate --help
```

Expected: Agent 可以升级但不能降级；命名失效原因能触发同级重评但不能绕过 ESCALATED；BLOCK 只有在恢复证据完整后才能重新分类。

## Task 4.6：完成治理流程端到端测试和第四章退出检查

**Artifacts / Locations:**
- Create: `tests/integration/test_governance_paths.py`
- Create: `docs/implementation/chapter-04-governance-workflows.md`
- Review: 第四章全部生产代码和事件记录

- [ ] **Step 1: 测试 AUTO 治理路径**

运行 start→classify→freeze spec→begin，确认无需人工批准但全部护栏成立；制造范围扩大后确认 begin 或 verify 拒绝并能升级。

- [ ] **Step 2: 测试 ASK 治理路径**

运行 start→classify→answer→freeze spec→begin；确认缺回答不能开始、回答写入规格、选项记录完整。

- [ ] **Step 3: 测试 REVIEW 治理路径**

运行 start→classify→spec approve→begin；构造最终审核前状态，确认 code approve 需要审核包和证据，action approve 不能替代 code approve。

- [ ] **Step 4: 测试 BLOCK 与混合单元**

确认任一未解决 BLOCK 阻止任务；解决条件后重新分类保留历史。混合 ASK+REVIEW 先回答 ASK、再做规格批准，不允许任一流程吞掉另一流程。

- [ ] **Step 5: 写治理流程说明**

给出四条时序、三类批准、规格冻结、升级和恢复的命令示例；明确阶段一不执行真实外部动作。

- [ ] **Step 6: 运行第四章退出检查**

Run:

```powershell
python -m pytest tests/unit/test_workflow.py tests/unit/test_specification.py tests/unit/test_review_package.py tests/unit/test_scope.py -q
python -m pytest tests/integration/test_answer_command.py tests/integration/test_approve_command.py tests/integration/test_auto_preflight.py tests/integration/test_escalate_command.py tests/integration/test_governance_paths.py -q
python -m ruff check .
python -m mypy src
git diff --check
```

Expected: AUTO、ASK、REVIEW、BLOCK 均可重放；三类批准互不替代；所有决定包含操作者、时间、版本和理由。

- [ ] **Step 7: 章节双重复核**

需求复核：比对原始设计中 ASK 决策压缩、审核包、设计/实现审核、代码/动作批准和 ESCALATE 原则。质量复核：CLI 与 Skill 职责边界明确，工作流条件没有散落副本。通过后开始第五章。

---

# 第 5 章：验证与证据闭环

## Task 5.1：解析 V0/V1 验证计划

**Artifacts / Locations:**
- Create: `src/aiflow/verification.py`
- Create: `tests/unit/test_verification_plan.py`
- Create: `tests/fixtures/verification/plans/`
- Review: `.ai/policy/verification-levels.yaml`
- Review: `src/aiflow/verification_level.py`

- [ ] **Step 1: 定义验证检查模型**

每项检查包含稳定 ID、适用等级、参数数组、受限环境覆盖、工作目录、超时秒数、是否必需、结果解析器和日志敏感级别。命令不得是单个 Shell 字符串；工作目录必须解析到仓库内；参数只展开 Policy 明确允许的六种变量，不执行嵌套替换或 Shell 展开。普通本地验证的 `run_dir` 必须位于当前任务日志目录；CI 与本地 CI 模拟都必须通过 `--ci-run-dir` 指向经真实路径校验的操作系统临时目录，GitHub Actions 中该目录位于 runner 临时目录。

- [ ] **Step 2: 解析 V0 计划**

按固定次序包含内置契约检查、内置范围检查、Ruff 和 Smoke。Smoke 使用 `python -m aiflow --help`；项目可以在 Policy 中替换为更强命令，但不能删除必需类别。

- [ ] **Step 3: 解析 V1 计划**

在完整 V0 后增加带 `COVERAGE_FILE={run_dir}/.coverage` 环境覆盖的 `python -m pytest --cov=aiflow --cov-branch --cov-report=xml:{run_dir}/coverage.xml`、回归测试标记集合、`python -m mypy src`，以及 `diff-cover {run_dir}/coverage.xml --compare-branch {base_commit} --fail-under=90`。diff-cover 的比较终点为当前 `subject_commit`；去重相同命令但保留所有类别映射，防止通过重复一项伪装成多种证据。

- [ ] **Step 4: 检查工具和配置可用性**

解析阶段确认 Python 模块或可执行文件可发现、超时为正数、日志路径合法、必需类别齐全。缺少必需工具返回 BLOCK 原因；可选检查缺失记录为未验证项，不得计为通过。

- [ ] **Step 5: 测试计划解析**

覆盖 V0、V1、重复命令、缺少类别、未知解析器、字符串命令、未知替换变量、`run_dir` 越界、非法环境变量、仓库外工作目录、零超时、diff-cover 缺失、覆盖 XML 缺失、变更覆盖 89% 失败和 90% 通过；运行后断言仓库根目录没有 `.coverage` 或 `coverage.xml`。

- [ ] **Step 6: 验证计划层**

Run:

```powershell
python -m pytest tests/unit/test_verification_plan.py -q
```

Expected: V1 严格包含 V0 类别；计划有稳定顺序；缺少必需能力不能降级继续。

## Task 5.2：实现受控子进程执行器与日志过滤

**Artifacts / Locations:**
- Create: `src/aiflow/process_runner.py`
- Create: `src/aiflow/redaction.py`
- Create: `tests/unit/test_process_runner.py`
- Create: `tests/unit/test_redaction.py`

- [ ] **Step 1: 实现子进程结果模型**

结果包含命令 ID、脱敏命令摘要、起止时间、耗时、退出码、timeout 标志、stdout/stderr 日志引用和解析结论。运行环境从最小允许变量集合构造，只允许 Policy 为覆盖任务设置 `COVERAGE_FILE` 到已校验 `run_dir`；不将全部父进程环境写入结果。

- [ ] **Step 2: 实现安全执行**

使用 `subprocess.run` 或等价无 Shell 接口，参数为数组，设置显式 cwd、受限环境、timeout、文本编码和捕获输出。运行前创建 `run_dir` 并验证真实路径；超时后确保子进程终止；异常统一转为失败结果而不是中断全部日志生成。

- [ ] **Step 3: 实现日志过滤**

过滤常见 `KEY=value` 密钥名、Bearer token、GitHub token 形态、用户显式配置的敏感模式和任务记录中的禁止值。过滤后保存完整日志，`evidence.json` 只保存摘要与相对日志路径。

- [ ] **Step 4: 防止命令与路径泄露**

证据中的命令摘要保留程序和非敏感参数，敏感参数替换为 `[REDACTED]`；日志路径必须位于当前任务 `logs/`，文件名由检查 ID 和序号生成。

- [ ] **Step 5: 测试成功、失败和超时**

使用本地 Python 小命令测试返回 0、返回非零、stdout/stderr、大输出截断、超时、不可执行文件、敏感字符串、仓库外 cwd、非法 `COVERAGE_FILE` 和合法任务/CI `run_dir`。

- [ ] **Step 6: 验证执行器**

Run:

```powershell
python -m pytest tests/unit/test_process_runner.py tests/unit/test_redaction.py -q
```

Expected: 任一错误形成结构化失败结果；日志不含测试密钥原文；没有 Shell 注入路径。

## Task 5.3：实现最终验证的 Git 清洁度与范围检查

**Artifacts / Locations:**
- Modify: `src/aiflow/git_context.py`
- Modify: `src/aiflow/scope.py`
- Create: `tests/integration/test_verification_git_scope.py`
- Review: `src/aiflow/workflow.py`

- [ ] **Step 1: 区分开发检查和最终证据**

`aiflow verify --provisional` 允许业务工作树脏并生成明确 `provisional` 结果，不能满足 Gate。默认本地最终 verify 开始时要求除当前任务治理记录外没有未提交变化，把此时 HEAD 记为被审 `subject_commit`，并将 `base_commit..subject_commit` 的 diff 作为范围和变更覆盖输入。验证生成的 evidence、logs 和事件属于随后允许写入的治理记录。

- [ ] **Step 2: 检查所有变更类型**

解析新增、修改、删除、重命名和子模块变化。治理记录 `.ai/tasks/<current-task>/**` 单独允许；其他任务目录变化、未知未跟踪文件和仓库外符号链接均导致范围失败。

- [ ] **Step 3: 同步被审代码 commit**

本地最终 verify 开始时只在任务仍绑定同一稳定仓库 ID、分支和基础 commit 时更新 `subject_commit` 为此时 HEAD，并追加版本同步事件。基础 commit 不得自动改写。后续提交 evidence、approval 和 event 等当前任务治理记录形成 attestation commit，不改写 `subject_commit`。

- [ ] **Step 4: 测试 Git 边界**

临时仓库覆盖干净最终验证、脏 provisional、脏最终拒绝、重命名越界、删除越界、其他任务记录变化、分支变化和基础 commit 不可达；完成 V1 后断言 coverage 数据与 XML 只在当前任务日志目录或 CI 临时目录，仓库根目录无覆盖产物。

- [ ] **Step 5: 验证 Git/范围集成**

Run:

```powershell
python -m pytest tests/integration/test_verification_git_scope.py -q
```

Expected: 只有干净且范围合法的 commit 可以生成可放行证据；provisional 永远不能变成 passed Gate。

## Task 5.4：生成 `evidence.json` 与版本摘要

**Artifacts / Locations:**
- Create: `src/aiflow/evidence.py`
- Create: `tests/unit/test_evidence.py`
- Modify: `.ai/templates/evidence.json`
- Review: `.ai/schemas/evidence.schema.json`

- [ ] **Step 1: 汇总不可省略的版本信息**

本地证据包含任务和单元 ID、稳定仓库 ID、分支、`base_commit`、`subject_commit`、规格 SHA-256、Policy SHA-256、分类输入 SHA-256、验证等级、工具版本、生成时间和统一复现命令。CI 权威证据额外包含 PR 最新 `attestation_head`，以及 `subject_commit..attestation_head` 仅含当前任务治理记录的检查结果。

- [ ] **Step 2: 汇总检查和未验证项**

每项检查保存稳定 ID、类别、状态、退出码、耗时、日志相对路径和摘要。所有可选缺失、跳过和无法覆盖场景进入 `unverified`；通过结论不得隐藏未验证项。

- [ ] **Step 3: 计算总体结论**

任一必需检查失败、超时、缺失或无法解析时结论为 failed；脏工作树验证为 provisional；全部必需检查通过且版本完整时为 passed。结论逻辑写在一个函数中并由决策表测试。

- [ ] **Step 4: 原子保存并保留历史日志**

新证据原子替换 `evidence.json`；日志目录按验证运行 ID 分组，证据引用当前运行。失败证据也必须保存，不能只在成功时留下记录。

- [ ] **Step 5: 测试证据决策表**

覆盖全通过、必需失败、可选失败、超时、缺失、provisional、空检查列表、版本字段缺失和日志路径逃逸。

- [ ] **Step 6: 验证证据层**

Run:

```powershell
python -m pytest tests/unit/test_evidence.py -q
```

Expected: 总体结论与决策表一致；失败也有完整证据；证据满足 Schema。

## Task 5.5：实现证据和批准失效服务

**Artifacts / Locations:**
- Create: `src/aiflow/freshness.py`
- Create: `tests/unit/test_freshness.py`
- Create: `tests/fixtures/freshness/decision-table.json`
- Modify: `src/aiflow/status_service.py`

- [ ] **Step 1: 固定失效矩阵**

矩阵包含：`subject_commit` 后出现当前任务治理目录外变化使 code approval 和 evidence 失效；仅 evidence/approval/event 等当前任务治理记录变化不改变 `subject_commit`，但需要 CI 在最新 `attestation_head` 重验；规格变化使 spec/code approval 与 evidence 失效；相关 Policy 变化使 classification、approval 和 evidence 失效；范围扩大要求重新分类；动作目标、参数、到期时间或已使用状态使 action approval 失效。

- [ ] **Step 2: 实现新鲜度判断**

每种产物返回 `fresh/stale/missing/not_applicable`、原因码和需要重新执行的命令。不自动删除旧文件；在状态和 Gate 中明确显示 stale。

- [ ] **Step 3: 处理规格批准的特殊绑定**

实现代码从 `base_commit` 形成 `subject_commit` 本身不使已批准且未变化的规格失效，但规格、Policy 或批准时基础上下文发生变化时失效；仅当前任务治理记录形成的 attestation commit 也不使规格失效。

- [ ] **Step 4: 测试矩阵每一行**

从 `decision-table.json` 参数化生成测试，并加入多项同时变化时的原因排序、缺文件和格式损坏。

- [ ] **Step 5: 验证新鲜度服务**

Run:

```powershell
python -m pytest tests/unit/test_freshness.py -q
```

Expected: 每个失效规则有直接测试；旧产物保留但不能满足后续条件。

## Task 5.6：实现 `aiflow verify`

**Artifacts / Locations:**
- Modify: `src/aiflow/cli.py`
- Create: `src/aiflow/verification_service.py`
- Modify: `src/aiflow/state.py`
- Create: `tests/integration/test_verify_command.py`

- [ ] **Step 1: 定义命令前置状态**

本地 verify 只允许 IMPLEMENTING、FAILED 重试后的 IMPLEMENTING 或已验证后显式重跑。开始时进入 VERIFYING；分类、规格或必要的实现前批准不新鲜时拒绝且不运行外部检查。`--ci --ci-run-dir <validated-temp-dir> --output <path-within-run-dir>` 是无状态转换的权威重验模式，允许 VERIFIED、WAITING_FOR_FINAL_REVIEW 或 APPROVED_FOR_MERGE；它要求显式 `ci-run-dir` 为操作系统或 runner 临时目录、解析后的 output 位于该目录内，并禁止修改仓库任务文件。

- [ ] **Step 2: 执行计划并保存每项结果**

按计划顺序运行；必需检查失败后继续运行不会造成副作用的剩余静态检查，以收集诊断，但总体保持失败。高成本或有副作用检查阶段一不存在。

- [ ] **Step 3: 生成证据并推进状态**

本地 passed 先进入 VERIFIED：若所有未完成单元均无需最终 REVIEW，同一命令再转入 APPROVED_FOR_MERGE；若任一单元需要最终 REVIEW，同一命令转入 WAITING_FOR_FINAL_REVIEW。failed 进入 FAILED；provisional 保持 IMPLEMENTING 并记录运行。CI 模式只写外部 evidence artifact，不改变状态。若失败暴露范围、权限或验证能力变化，输出需要 escalate 的原因码。

- [ ] **Step 4: 支持定向重跑但不伪造完整证据**

`--check <id>` 可用于诊断，生成 provisional 证据；只有不带定向过滤且执行全部必需检查的运行可以产生 passed。CI 输出记录 `subject_commit`、观测到的最新 `attestation_head` 和治理尾提交路径检查。

- [ ] **Step 5: 测试命令生命周期**

覆盖 AUTO/ASK passed 自动进入 APPROVED_FOR_MERGE、REVIEW passed 进入 WAITING_FOR_FINAL_REVIEW、代码批准后进入 APPROVED_FOR_MERGE，以及必需失败、超时、provisional、定向检查、错误状态、过期规格、过期 Policy、CI 只读输出、缺少 `--ci-run-dir`、非临时 `ci-run-dir`、output 逃逸 run dir、合法操作系统临时目录中的本地 CI 模拟、证据写入失败和重复验证。

- [ ] **Step 6: 验证 verify**

Run:

```powershell
python -m pytest tests/integration/test_verify_command.py -q
python -m aiflow verify --help
```

Expected: AUTO/ASK/REVIEW 都有可达放行路径；CI 模式不修改仓库；失败和 provisional 状态正确；定向检查不能满足 Gate。

## Task 5.7：实现 `aiflow gate`

**Artifacts / Locations:**
- Create: `src/aiflow/gate.py`
- Modify: `src/aiflow/cli.py`
- Create: `tests/unit/test_gate.py`
- Create: `tests/fixtures/gate/decision-table.json`
- Create: `tests/integration/test_gate_command.py`

- [ ] **Step 1: 定义 Gate 决策输入**

输入包括任务/事件合法性、稳定仓库 ID、当前 Git 上下文、`subject_commit`、观测 HEAD、`subject_commit..HEAD` 路径集合、分类新鲜度、有效 route、验证等级、规格冻结、批准要求、evidence 新鲜度、未解决 BLOCK/ESCALATE 和外部动作状态。

- [ ] **Step 2: 固定模式决策表**

AUTO 需要完整护栏和 passed evidence；ASK 还需要已记录回答；REVIEW 需要适用的 spec/code approval；任何 BLOCK、未解决升级、stale 产物或 provisional evidence 均失败。`subject_commit..HEAD` 只允许当前任务 `.ai/tasks/TASK-ID/**`，否则批准和证据 stale。action approval 不作为代码合并的替代条件，也不自动触发动作。

- [ ] **Step 3: 实现文本和 JSON 输出**

`aiflow gate TASK-ID` 默认读取任务内本地 evidence；CI 必须调用 `aiflow gate TASK-ID --evidence <runner-temp-evidence> --format json`。通过返回 0，门禁不通过返回专用非零码，输入损坏返回不同非零码，便于 CI 区分。

- [ ] **Step 4: 只读与确定性保证**

Gate 不修改任务、事件、批准或证据。它验证 evidence 中的稳定仓库 ID、`subject_commit` 和 CI `attestation_head` 与当前 checkout 一致；绝对路径不参与比较。相同文件和 Git HEAD 重复运行输出除运行时间外完全相同；JSON 机器输出不包含动态运行时间。

- [ ] **Step 5: 测试决策表和命令**

决策表逐行覆盖 AUTO/ASK/REVIEW/BLOCK、三类批准、证据状态、混合单元、治理-only attestation commit、治理目录外新 commit、仓库 ID 匹配、绝对路径不同和版本变化；集成测试验证退出码、输出排序和只读性。

- [ ] **Step 6: 验证 Gate**

Run:

```powershell
python -m pytest tests/unit/test_gate.py tests/integration/test_gate_command.py -q
python -m aiflow gate --help
```

Expected: 所有拒绝都有具体修复动作；重复运行不改变仓库文件。

## Task 5.8：完成第五章端到端证据回归

**Artifacts / Locations:**
- Create: `tests/integration/test_verification_evidence_flow.py`
- Create: `docs/implementation/chapter-05-verification-evidence.md`
- Review: 第五章全部生产代码和决策表

- [ ] **Step 1: 跑通通过链路**

构造已准备任务和临时 Git commit，执行全量 V0/V1 检查、生成 evidence、进入 VERIFIED 并通过 Gate；核对复现命令能再次运行。

- [ ] **Step 2: 跑通失败和恢复链路**

制造测试失败进入 FAILED，修复并通过带理由的 begin 重试，再次 verify 成功；旧失败 evidence 和日志保留，新证据指向新运行。

- [ ] **Step 3: 验证版本失效**

在通过后先创建只修改当前任务 evidence/approval/event 的 attestation commit，确认 `subject_commit` 不变且 Gate 仍可在重验后通过；再创建修改治理目录外文件的 commit，确认 evidence 和 code approval 变 stale、Gate 失败。重新 verify 和 approve 后恢复；修改规格和 Policy 分别验证对应失效矩阵。

- [ ] **Step 4: 写验证和证据说明**

记录 V0/V1、provisional/final、日志、脱敏、失效规则、Gate 退出码和故障排查。明确“测试通过”文本不能替代 `evidence.json`。

- [ ] **Step 5: 运行第五章退出检查**

Run:

```powershell
python -m pytest tests/unit/test_verification_plan.py tests/unit/test_process_runner.py tests/unit/test_redaction.py tests/unit/test_evidence.py tests/unit/test_freshness.py tests/unit/test_gate.py -q
python -m pytest tests/integration/test_verification_git_scope.py tests/integration/test_verify_command.py tests/integration/test_gate_command.py tests/integration/test_verification_evidence_flow.py -q
python -m ruff check .
python -m mypy src
python -m pytest --cov=aiflow --cov-branch --cov-report=term-missing --cov-fail-under=85
git diff --check
```

Expected: 全部通过；治理-only attestation commit 不产生自引用；覆盖产物不污染仓库根目录；旧证据不能放行任何新的非治理变更；失败、超时和缺失工具均有结构化证据。

- [ ] **Step 6: 章节双重复核**

需求复核：逐项比对原始设计的 Verification as Code、版本绑定、统一命令和 V0/V1 内容。质量复核：命令无 Shell 拼接、日志已脱敏、失效逻辑和 Gate 逻辑均为单一来源。通过后开始第六章。

---

# 第 6 章：Agent、Hooks 与 CI 集成

## Task 6.1：建立精简的 `AGENTS.md` 与 `CLAUDE.md`

**Artifacts / Locations:**
- Create: `AGENTS.md`
- Create: `CLAUDE.md`
- Create: `tests/integration/test_agent_entry_files.py`
- Review: `.ai/policy/`
- Review: `docs/superpowers/specs/2026-08-01-ai-code-collaboration-mvp-design.md`

- [ ] **Step 1: 写常驻不可绕过原则**

两个文件都声明：代码任务进入 AI Flow；不得绕过状态、范围和验证门；Agent 不得自行降级；高风险动作单独批准；批准和证据绑定当前版本；完整规则和命令位于明确路径。

- [ ] **Step 2: 保持入口文件简短**

每个文件只保留稳定原则、启动命令和文档链接，不复制硬规则表、状态转换表、V0/V1 命令清单或模型信任公式。`CLAUDE.md` 的平台说明引用同一核心流程。

- [ ] **Step 3: 增加文档一致性测试**

检查两个文件包含六项原则和有效相对链接；检查没有 YAML 规则 ID、状态转换箭头或完整验证命令表，从结构上防止规则副本。

- [ ] **Step 4: 验证入口文件**

Run:

```powershell
python -m pytest tests/integration/test_agent_entry_files.py -q
```

Expected: 两个入口覆盖相同治理原则，且不会成为第二套 Policy。

## Task 6.2：实现 `ai-flow` Skill

**Artifacts / Locations:**
- Create: `.claude/skills/ai-flow/SKILL.md`
- Create: `tests/integration/test_ai_flow_skill.py`
- Review: `AGENTS.md`
- Review: `src/aiflow/cli.py`

- [ ] **Step 1: 定义 Skill 触发范围**

说明所有代码变更、配置变更、CI 变更和会产生仓库行为的任务使用该 Skill；纯只读解释可不创建任务。Skill 不宣称具备 CLI 未实现的权限。

- [ ] **Step 2: 写标准编排流程**

按 `start→补充决策单元和规格→classify→freeze 或 answer 原子冻结→必要的 spec approve→begin→verify→必要的 code approve→gate→外部合并后 close` 编排；每一步写明允许状态、用户交互条件和失败时应调用的状态命令。

- [ ] **Step 3: 写 ASK/REVIEW 质量要求**

ASK 要求 2—4 个实质不同选项及收益、代价、风险；REVIEW 要求结构化审核包和明确问题；明确 Agent 只生成材料，程序校验和记录，人类负责方向与风险接受。

- [ ] **Step 4: 写升级与禁止行为**

遇到范围扩大、新依赖、权限、网络、凭据、验证不可用或连续失败必须 `escalate`。禁止直接改任务状态、伪造证据、跳过命令、自动降级、用 code approval 替代 action approval。

- [ ] **Step 5: 验证 Skill 与 CLI 一致**

测试从 CLI parser 枚举真实命令，确认 Skill 引用的命令均存在；检查必需段落、模板链接和禁止项；检查 Skill 中没有 Policy 判定矩阵副本。

- [ ] **Step 6: 运行 Skill 测试**

Run:

```powershell
python -m pytest tests/integration/test_ai_flow_skill.py -q
```

Expected: Skill 只编排已有命令；所有人工闸门和升级条件有明确说明。

## Task 6.3：建立统一验证包装和薄层 Hooks

**Artifacts / Locations:**
- Create: `tools/gauntlet.py`
- Create: `tools/hooks/pre_commit.py`
- Create: `tools/hooks/pre_command.py`
- Create: `tests/integration/test_tool_wrappers.py`
- Create: `docs/operations/hooks.md`

- [ ] **Step 1: 实现 `gauntlet.py` 薄包装**

只解析 `--task`、`--provisional` 和 `--format`，随后调用 `aiflow` 包内验证服务；退出码与 `aiflow verify` 一致。包装不得读取 Policy 后自行决定检查。

- [ ] **Step 2: 实现 pre-commit 薄 Hook**

从显式参数或唯一活动任务解析 ID，调用核心范围检查和 `aiflow status` 前置条件；若无法解析或超范围则拒绝。Hook 不运行 commit、不修改暂存区、不自动修复文件。

- [ ] **Step 3: 实现 pre-command 薄 Hook**

接收规范化动作类别和目标，只调用 permissions/workflow 核心判断。阶段一支持检查并拒绝 push、merge、deploy、delete、secret export 和付费调用类别；不尝试解析任意 Shell 语法。

- [ ] **Step 4: 记录平台接入方式**

`docs/operations/hooks.md` 给出 Claude Code、通用 pre-commit 和其他 Agent 如何显式调用脚本；明确未接入 Hook 的平台仍由 CLI 和 CI 最终门禁，阶段一不声称全局系统拦截。

- [ ] **Step 5: 验证薄层属性**

测试 wrapper 与核心服务对同一输入返回相同结论和退出码；用 monkeypatch 确认 wrapper 调用核心接口而非重新解析 Policy；测试缺任务、禁止动作和超范围。

- [ ] **Step 6: 运行包装测试**

Run:

```powershell
python -m pytest tests/integration/test_tool_wrappers.py -q
python tools/gauntlet.py --help
python tools/hooks/pre_commit.py --help
python tools/hooks/pre_command.py --help
```

Expected: 三个脚本均为薄包装；禁止动作被拒绝；没有外部动作被执行。

## Task 6.4：建立 GitHub Actions 质量门

**Artifacts / Locations:**
- Create: `.github/workflows/ai-quality-gate.yml`
- Create: `tests/integration/test_github_workflow.py`
- Create: `docs/operations/github-branch-protection.md`
- Review: `src/aiflow/gate.py`

- [ ] **Step 1: 定义最小权限和触发器**

工作流在 pull request 的 opened、synchronize、reopened 和 ready_for_review 触发；权限只设 `contents: read`。设置并发组按 PR 取消旧运行，设置 job 超时十五分钟，不使用仓库写权限或 secrets。

- [ ] **Step 2: 建立可复现环境**

checkout 使用 `fetch-depth: 0` 获取 base、`subject_commit` 和 PR HEAD，设置 Python 3.11，安装 `.[dev]` 并运行契约测试。读取 `.ai/repository-id` 作为稳定身份，绝对 runner checkout 路径不与本地路径比较。不得从不受信任 PR 执行具有 secrets 的 `pull_request_target`。

- [ ] **Step 3: 解析任务 ID**

先从显式工作流输入或环境变量读取；否则从 base 到 head diff 中的 `.ai/tasks/TASK-*` 目录解析，要求唯一。把结果保存为后续步骤实际使用的 `task_id` 输出；零个或多个候选均失败并打印修复方式。测试必须证明解析值被传给 verify 和 Gate，而不是只计算后丢弃。

- [ ] **Step 4: 保存诊断产物**

使用解析出的任务 ID 依次执行 `python -m aiflow verify "$task_id" --ci --ci-run-dir "$RUNNER_TEMP/aiflow" --output "$RUNNER_TEMP/aiflow/evidence.json"` 和 `python -m aiflow gate "$task_id" --evidence "$RUNNER_TEMP/aiflow/evidence.json" --format json`。无论成功失败，上传权威 CI evidence、Gate JSON 和脱敏验证日志；产物保留期设为十四天。上传步骤不包含凭据、完整环境或仓库外文件。

- [ ] **Step 5: 编写分支保护清单**

说明将 `ai-quality-gate` 设为必需检查、禁止直接和强制推送受保护分支、要求分支最新、谁可绕过以及绕过需要单独审计。注明这些设置需仓库管理员在 GitHub 外部完成。

- [ ] **Step 6: 静态测试 Workflow**

安全解析 YAML，检查权限、事件、完整 Git 历史、Python 版本、安装命令、带同一 `task_id` 的 CI verify/Gate 命令、显式 `$RUNNER_TEMP` `--ci-run-dir`、run dir 内的 evidence 路径、timeout、并发取消、禁止 `pull_request_target`、不存在 write 权限。测试任务 ID 解析脚本的零/一/多候选、不同 checkout 绝对路径但相同 repository ID，以及治理目录外 tail commit 被拒绝。

- [ ] **Step 7: 验证 GitHub Action**

Run:

```powershell
python -m pytest tests/integration/test_github_workflow.py -q
```

Expected: Workflow 结构和安全断言全部通过；解析的任务 ID 真实传入核心 verify 和 Gate；CI evidence 绑定最新 PR HEAD；绝对路径差异不导致仓库身份失败。

## Task 6.5：验证本地、包装器和 CI 决策一致性

**Artifacts / Locations:**
- Create: `tests/integration/test_gate_parity.py`
- Create: `tests/fixtures/parity/`
- Modify: `docs/implementation/chapter-06-agent-ci.md`
- Review: `tools/`
- Review: `.github/workflows/ai-quality-gate.yml`

- [ ] **Step 1: 固定一致性夹具**

准备 passed AUTO、missing ASK answer、missing REVIEW approval、stale evidence、BLOCKED、多任务歧义、治理-only attestation tail 和治理目录外 tail 八个完整任务目录快照；至少一个夹具在两个不同绝对 checkout 路径运行但共享同一 `.ai/repository-id`。

- [ ] **Step 2: 对比三条入口**

对每个夹具分别调用包内 Gate、本地 CLI JSON Gate，以及 CI 只读 verify 生成权威 evidence 后的 GitHub workflow Gate，比较结论、原因码和排序；忽略仅用于人类显示的文字差异。

- [ ] **Step 3: 验证只读性**

运行前后计算夹具目录文件摘要，确认 Gate、Hook 和 CI 包装不修改任务。验证失败场景仍输出机器 JSON。

- [ ] **Step 4: 写平台集成说明**

说明 Agent 入口、Skill、Hook、CI、分支保护各自能强制什么、不能强制什么，以及共同调用的核心接口。避免宣称提示词或 Hook 可以替代 GitHub 分支保护。

- [ ] **Step 5: 运行一致性测试**

Run:

```powershell
python -m pytest tests/integration/test_gate_parity.py -q
```

Expected: 八个夹具在三条入口的机器结论完全一致；相同 repository ID 在不同绝对路径有效；运行前后源任务文件摘要不变。

## Task 6.6：完成第六章退出检查

**Artifacts / Locations:**
- Review: `AGENTS.md`
- Review: `CLAUDE.md`
- Review: `.claude/skills/ai-flow/SKILL.md`
- Review: `tools/`
- Review: `.github/workflows/ai-quality-gate.yml`
- Review: `docs/operations/`

- [ ] **Step 1: 运行平台集成回归**

Run:

```powershell
python -m pytest tests/integration/test_agent_entry_files.py tests/integration/test_ai_flow_skill.py tests/integration/test_tool_wrappers.py tests/integration/test_github_workflow.py tests/integration/test_gate_parity.py -q
python -m ruff check .
python -m mypy src
git diff --check
```

Expected: 全部通过；所有平台入口引用真实命令；本地与 CI 结论一致。

- [ ] **Step 2: 搜索规则副本和危险配置**

Run:

```powershell
rg -n "BLOCK > REVIEW > ASK > AUTO|ROUTE-DEFAULT-REVIEW" AGENTS.md CLAUDE.md .claude tools .github
rg -n "pull_request_target|contents:\s*write|secrets:" .github/workflows/ai-quality-gate.yml
```

Expected: 第一条不在适配文件中复制规则矩阵；第二条无匹配。若测试文件需要出现这些字符串，限定搜索到生产适配文件。

- [ ] **Step 3: 章节双重复核**

需求复核：比对总体规划的 Agent 文件、Skill、Hooks、CI 与分支保护职责。质量复核：适配层薄、最小权限、无真实外部动作、诊断可读。通过后开始第七章。

---

# 第 7 章：试点验收与阶段一基线

## Task 7.1：建立端到端场景运行器

**Artifacts / Locations:**
- Create: `src/aiflow/scenarios.py`
- Create: `tests/integration/test_scenario_runner.py`
- Modify: `examples/scenarios/README.md`
- Review: `examples/scenarios/`

- [ ] **Step 1: 定义隔离运行方式**

场景运行器把输入、Policy 和模板复制到 pytest 临时 Git 仓库，创建固定初始 commit，并使用真实 CLI 服务执行；不在工作仓库的 `.ai/tasks` 中创建测试任务。

- [ ] **Step 2: 定义场景操作清单**

每个场景声明按顺序执行的命令、模拟操作者、允许的文件变化、预期状态和预期 Gate 原因码。时间和 commit 使用运行时值，但比较时通过语义字段而非硬编码 SHA。

- [ ] **Step 3: 捕获产物和重放结果**

返回任务目录快照、CLI 退出码、事件状态序列、分类摘要、批准摘要、evidence 和 Gate JSON。运行完成后从事件日志重放一次，确保终态一致。

- [ ] **Step 4: 测试隔离和确定性**

同一场景连续运行两次，除时间、临时路径和 commit 外机器结论一致；当前仓库 Git 状态和 `.ai/tasks` 摘要运行前后不变。

- [ ] **Step 5: 验证场景运行器**

Run:

```powershell
python -m pytest tests/integration/test_scenario_runner.py -q
```

Expected: 场景在隔离仓库运行，结果可重放，不污染当前工作区。

## Task 7.2：跑通四类黄金端到端场景

**Artifacts / Locations:**
- Create: `tests/e2e/test_auto_scenario.py`
- Create: `tests/e2e/test_ask_scenario.py`
- Create: `tests/e2e/test_review_scenario.py`
- Create: `tests/e2e/test_block_scenario.py`
- Modify: `examples/scenarios/*/expected.json`

- [ ] **Step 1: 完成 AUTO 场景**

执行 start、写入已定义决策单元和完整规格、classify、freeze、begin、创建允许的文档 commit、verify、gate、记录外部合并 close。断言无人工批准、V0 全部通过、范围和证据绑定正确。

- [ ] **Step 2: 完成 ASK 场景**

执行到 WAITING_FOR_ASK，确认未回答 Gate 失败；提交三个输出格式选项和选择，冻结规格，实施选择、运行 V1、通过 Gate。断言完整选项与回答进入事件和规格。

- [ ] **Step 3: 完成 REVIEW 场景**

确认修改 CI 路径触发 REVIEW+V1；缺规格批准不能 begin，缺代码批准不能 Gate。依次完成审核包、规格批准、实现、验证、代码批准和 Gate；action approval 保持不适用。

- [ ] **Step 4: 完成 BLOCK 场景**

确认无备份覆盖请求进入 BLOCK，任何 begin/verify/gate 都拒绝。增加受控备份证据并缩小操作为 dry-run，记录解除条件、重新分类并确认历史 BLOCK 事件仍存在。

- [ ] **Step 5: 运行 E2E 集合**

Run:

```powershell
python -m pytest tests/e2e -q
```

Expected: 四条路径通过；每个状态和拒绝点均有断言；测试没有网络和真实外部动作。

## Task 7.3：准备真实仓库试点与执行授权点

**Artifacts / Locations:**
- Create: `docs/pilots/README.md`
- Create: `docs/pilots/pilot-runbook.md`
- Create (external, untracked): `../harness-model-pilot-artifacts/`
- Create (Git worktree): `../harness-model-pilot-auto/`
- Create (Git worktree): `../harness-model-pilot-ask/`
- Create (Git worktree): `../harness-model-pilot-review/`
- Create (Git worktree): `../harness-model-pilot-block/`
- Review: 当前仓库 `git status --short --branch`
- Review: `docs/operations/`

- [ ] **Step 1: 固定试点前置条件**

要求章节一至六退出检查全部通过、当前实现形成一个共同 `pilot_base` commit、主工作树干净、未推送动作不在自动流程内。执行者在创建分支、worktree 或任何 commit 前向用户确认本地 Git 写入权限；未获授权时只运行黄金 E2E，不伪造真实 commit 或 CI 证据。

- [ ] **Step 2: 从同一基线创建四个隔离 worktree**

记录 `pilot_base = git rev-parse HEAD`，确认四个目标绝对路径均为主仓库的明确同级目录且当前不存在，再分别创建 `pilot/auto-doc`、`pilot/ask-report`、`pilot/review-policy`、`pilot/block-dry-run` worktree。四个 worktree 必须包含相同 `.ai/repository-id`；不得自动删除或覆盖已有同名目录。

- [ ] **Step 3: 定义四个真实任务**

AUTO 在 auto worktree 新增 `docs/operations/evidence-expiry-example.md`。ASK 在 ask worktree为 `docs/pilots/ask-pilot-summary` 选择 Markdown、JSON 或双格式并只生成用户选择。REVIEW 在 review worktree 给 `.ai/policy/permissions.yaml` 增加 `package_publish` 禁止动作和测试。BLOCK 在 block worktree请求删除 `examples/scenarios/**` 且无备份，随后安全改写为只生成 dry-run 清单；任何阶段不得实际删除文件。

- [ ] **Step 4: 定义每次试点保存内容**

每个 worktree 只在自己的 `.ai/tasks/<task-id>/` 保存治理记录，并把脱敏的 task ID、稳定仓库 ID、分支、`pilot_base`、`subject_commit`、`attestation_head`、关键命令、状态序列、分类摘要、批准类型、CI evidence、Gate JSON、人工观察和未验证项复制到外部 `../harness-model-pilot-artifacts/PILOT-*/`。外部目录不属于任一试点 Git diff。

- [ ] **Step 5: 写试点运行手册**

明确 worktree 路径验证、分支/commit 权限点、ASK 必须由真实用户选择、REVIEW 必须由实现者之外的人或独立审核者批准、BLOCK 不得绕过、每个 Gate 只在对应 worktree 的 attestation HEAD 运行、试点结束不自动 push/merge/删除 worktree。

- [ ] **Step 6: 审阅运行手册**

Check: 四个 worktree 从同一 `pilot_base` 分叉；三个真实任务分别覆盖 AUTO、ASK、REVIEW；BLOCK 有拒绝和恢复；结果在外部 artifact 目录；所有 Git 和外部状态变化都需要明确授权。

Expected: 试点任务具体、可逆、范围受控、彼此不会使对方 stale，不依赖临时发明的新产品功能。

## Task 7.4：在本仓库执行 AUTO、ASK、REVIEW 和 BLOCK 试点

**Artifacts / Locations:**
- Modify in auto worktree: `docs/operations/evidence-expiry-example.md`
- Create in ask worktree: `docs/pilots/ask-pilot-summary.md` or `docs/pilots/ask-pilot-summary.json` according to the recorded user choice
- Modify in review worktree: `.ai/policy/permissions.yaml`
- Modify in review worktree: matching permission tests under `tests/`
- Create in block worktree: a dry-run inventory under `docs/pilots/block-dry-run-inventory.md`
- Create (external, untracked): `../harness-model-pilot-artifacts/PILOT-AUTO/`
- Create (external, untracked): `../harness-model-pilot-artifacts/PILOT-ASK/`
- Create (external, untracked): `../harness-model-pilot-artifacts/PILOT-REVIEW/`
- Create (external, untracked): `../harness-model-pilot-artifacts/PILOT-BLOCK/`

- [ ] **Step 1: 执行 AUTO 真实任务**

在 auto worktree 使用工具自身创建任务并限定 `docs/operations/evidence-expiry-example.md`；形成 subject commit，完成 V0、本地 evidence 和只改当前任务治理记录的 attestation commit，再在该 worktree 运行 CI 只读 verify 与 Gate。若分类不是 AUTO，不手工降级，记录实际结果并修正场景设计后从 `pilot_base` 建立新试点分支。

- [ ] **Step 2: 执行 ASK 真实任务**

在 ask worktree 创建报告格式任务，生成三个实质不同选项，由用户真实选择；使用 `answer` 固化并原子冻结决定，生成且只生成被选择的报告格式，形成该任务自己的 subject/attestation commits，并只在 ask worktree 完成 V0/V1 和 Gate。

- [ ] **Step 3: 执行 REVIEW 真实任务**

在 review worktree 创建 Policy 修改任务并先完成初始分类、规格冻结和规格审核；实现 `package_publish` 规则和测试、形成 subject commit 后，因 Policy 摘要变化显式执行 `aiflow escalate <TASK-ID> --to REVIEW --reason-code policy_changed --impact <text> --next-step <text> --actor <id>`，确认 REVIEW→ESCALATED，再使用新 Policy 重新 classify 为 REVIEW、重新 freeze、重新完成 spec approval，之后再 begin、运行 V1、生成审核包并由独立审核者完成 code approval。批准记录形成 governance-only attestation commit 后，只在 review worktree 运行 CI 重验和 Gate。不得用执行者身份替代独立批准。

- [ ] **Step 4: 执行 BLOCK 真实验证**

在 block worktree 创建删除请求并确认 BLOCK；保存阻断原因。将目标改为只生成 `docs/pilots/block-dry-run-inventory.md`，记录用户确认和解除证据，重新分类并运行允许的流程；检查 `examples/scenarios/**` 的文件摘要前后相同。

- [ ] **Step 5: 保存和核验试点结果**

在每个 worktree 的对应 attestation HEAD 运行契约和 Gate 校验；把 task ID、CI evidence、Gate JSON 和摘要复制到对应外部 artifact 目录。逐项核对 repository ID、subject/attestation commits、规格和 Policy 摘要；确认 artifact 不包含完整敏感日志。

- [ ] **Step 6: 运行试点回归**

分别在四个 worktree 执行，不在主工作树或任一后续试点 HEAD 重新 Gate 旧任务。

Run in each matching worktree:

```powershell
python -m pytest -q
$pilotName = switch ((git branch --show-current)) {
  'pilot/auto-doc' { 'PILOT-AUTO' }
  'pilot/ask-report' { 'PILOT-ASK' }
  'pilot/review-policy' { 'PILOT-REVIEW' }
  'pilot/block-dry-run' { 'PILOT-BLOCK' }
  default { throw 'Not running in a registered pilot branch.' }
}
$pilotArtifactRoot = (Resolve-Path '..\harness-model-pilot-artifacts').Path
$pilotArtifact = Join-Path $pilotArtifactRoot $pilotName
$pilotTaskId = (Get-Content -Raw (Join-Path $pilotArtifact 'task-id.txt')).Trim()
$pilotCiRunDir = Join-Path ([System.IO.Path]::GetTempPath()) ('aiflow-' + $pilotName + '-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $pilotCiRunDir | Out-Null
$pilotEvidenceTemp = Join-Path $pilotCiRunDir 'ci-evidence.json'
$pilotGateTemp = Join-Path $pilotCiRunDir 'gate.json'
python -m aiflow verify $pilotTaskId --ci --ci-run-dir $pilotCiRunDir --output $pilotEvidenceTemp
python -m aiflow gate $pilotTaskId --evidence $pilotEvidenceTemp --format json | Tee-Object -FilePath $pilotGateTemp
Copy-Item -LiteralPath $pilotEvidenceTemp -Destination (Join-Path $pilotArtifact 'ci-evidence.json')
Copy-Item -LiteralPath $pilotGateTemp -Destination (Join-Path $pilotArtifact 'gate.json')
```

执行前先把该次实际 task ID 写入对应外部文件，并确认 `$pilotArtifact` 已按 Task 7.3 创建。权威 verify 和 Gate 首先只写新建的操作系统临时目录，通过后再把脱敏 evidence 与 Gate JSON 复制到持久 artifact 目录；不得直接把 `--ci` 输出指向 artifact 或仓库。Expected: 每个 artifact 绑定自己的分支和 attestation HEAD；AUTO、ASK、REVIEW Gate 分别通过；BLOCK 保留拒绝历史并在安全改写后达到预期状态；后续试点不改变前一试点结论；没有 push、merge、部署或删除。

## Task 7.5：建立阶段一验收矩阵

**Artifacts / Locations:**
- Create: `docs/implementation/phase-01-acceptance-matrix.md`
- Create: `docs/pilots/results/PILOT-AUTO/`
- Create: `docs/pilots/results/PILOT-ASK/`
- Create: `docs/pilots/results/PILOT-REVIEW/`
- Create: `docs/pilots/results/PILOT-BLOCK/`
- Create: `docs/pilots/results/report-task-id.txt`
- Create: `tests/integration/test_acceptance_traceability.py`
- Review: `docs/architecture/AI代码协同系统实施总体规划_V0.2.md`
- Review: `docs/superpowers/specs/2026-08-01-ai-code-collaboration-mvp-design.md`

- [ ] **Step 1: 用独立报告任务导入试点结果**

回到主工作树，在不合并四个试点分支的前提下创建一个报告任务，允许范围只含 `docs/pilots/results/**`、`docs/implementation/phase-01-acceptance-matrix.md` 和对应追踪测试。把外部 artifact 的脱敏 task ID、source branch、repository ID、pilot base、subject/attestation commits、CI evidence 摘要、Gate JSON 摘要和人工观察复制到对应结果目录；验证外部文件 SHA-256 后记录来源。报告任务形成自己的 subject/attestation commits、验证和 Gate，任务 ID写入 `report-task-id.txt`。不得在主 HEAD 重新 Gate 四个旧任务。

- [ ] **Step 2: 建立十二项追踪表**

每行包含验收 ID、原始要求、实现文件、定向测试、演示命令、证据或试点结果路径、结论和限制。覆盖设计说明第 13 节十二项，其中前十项明确映射 V0.2 原始验收标准。

- [ ] **Step 3: 验证原始十项要求**

逐项确认唯一任务记录、route/V 等级、ASK 选项、REVIEW 审核包、AUTO 护栏、无 commit 自引用的版本失效、统一验证命令、CI 在 PR 最新 HEAD 重验并拒绝、动态升级以及实际仓库 AUTO/ASK/REVIEW 流程。

- [ ] **Step 4: 验证新增两项要求**

确认本地与 CI 机器结论一致；从干净检出可以按文档安装、测试和运行示例。

- [ ] **Step 5: 自动检查追踪完整性**

测试十二个验收 ID 恰好出现一次，引用的本地文件和测试节点存在，四个试点结果包含不同 source branch 和各自 commit 绑定，外部 artifact 摘要匹配，报告任务 Gate 通过；结论只能为 passed 或 blocked。不允许 pending、TBD、在主 HEAD 重跑旧 Gate，或只写文字结论而没有证据路径。

- [ ] **Step 6: 验证验收矩阵**

Run:

```powershell
python -m pytest tests/integration/test_acceptance_traceability.py -q
```

Expected: 十二项都有存在的实现、测试和证据引用；四个试点来自各自 worktree/attestation HEAD；报告任务 Gate 通过；阶段一发布前没有 blocked 项。

## Task 7.6：验证干净检出、安装和故障恢复

**Artifacts / Locations:**
- Create: `docs/operations/quickstart.md`
- Create: `docs/operations/recovery.md`
- Create: `tests/e2e/test_clean_checkout.py`
- Review: `pyproject.toml`
- Review: `docs/implementation/phase-01-acceptance-matrix.md`

- [ ] **Step 1: 写 Quickstart**

从 `git clone` 后开始，创建虚拟环境、安装 `.[dev]`、运行测试、创建示例任务、分类、查看状态和运行 Gate。命令同时给出 PowerShell 和平台中立的 Python 入口，默认不执行 commit/push。

- [ ] **Step 2: 写恢复手册**

覆盖半创建任务、损坏 JSON/YAML、事件/物化状态不一致、FAILED 重试、BLOCK 解除、stale evidence、Policy 变化和无法唯一解析任务。每种故障给出诊断命令、可恢复操作和禁止操作。

- [ ] **Step 3: 自动运行干净检出测试**

在 pytest 临时目录使用 `git clone --local` 克隆当前仓库，创建隔离虚拟环境或使用当前解释器的 editable wheel 构建产物，按 Quickstart 的无外部动作子集运行。不得读取原工作区未跟踪文件。

- [ ] **Step 4: 验证文档命令**

测试提取 Quickstart 标记的验证命令并运行；检查所有相对路径存在；故障恢复章节覆盖指定八种情况。

- [ ] **Step 5: 运行干净检出测试**

Run:

```powershell
python -m pytest tests/e2e/test_clean_checkout.py -q
```

Expected: 干净克隆可安装、测试、查看帮助并运行无外部动作示例；不依赖用户主目录配置。

## Task 7.7：形成阶段一发布基线

**Artifacts / Locations:**
- Modify: `src/aiflow/__init__.py`
- Create: `CHANGELOG.md`
- Create: `docs/implementation/phase-01-acceptance-report.md`
- Create: `docs/implementation/phase-02-entry-inputs.md`
- Review: 本计划全部已勾选项和验收矩阵

- [ ] **Step 1: 固定版本和变更记录**

在全部验收通过后把版本从 `0.1.0.dev0` 改为 `0.1.0`。CHANGELOG 记录阶段一交付能力、明确非目标、已知限制和迁移规则；不宣称已实现 V2/V3 或真实模型路由。

- [ ] **Step 2: 写阶段一验收报告**

汇总十二项结论、四个真实试点、完整验证命令、覆盖率、CI 一致性、未验证场景和风险接受。报告引用原始证据，不复制大段日志。

- [ ] **Step 3: 提取阶段二输入**

只记录由实际测试或试点支持的缺口，按审核增强、V2、独立 Verifier、变异测试、动态升级和完整 Hooks 分类；每项包含证据来源和进入阶段二的必要性。

- [ ] **Step 4: 运行最终验证**

Run:

```powershell
python -m pip install -e ".[dev]"
python -m ruff check .
python -m mypy src
python -m pytest
python -m pytest --cov=aiflow --cov-branch --cov-report=term-missing --cov-fail-under=85
python -m pytest tests/e2e -q
python -m aiflow --version
git diff --check
```

Expected: 全部通过；版本为 0.1.0；十二项验收均 passed；四个试点结果存在且版本绑定正确。

- [ ] **Step 5: 运行占位项与范围扫描**

Run:

```powershell
rg -n "TBD|TODO|fill in later|稍后补充|待定" src .ai tests docs/implementation docs/operations docs/pilots AGENTS.md CLAUDE.md
```

Expected: 无未解释占位项。若测试夹具刻意包含这些字符串，必须限定在明确的 invalid fixture，并从发布扫描中排除该夹具目录。

- [ ] **Step 6: 章节和阶段双重复核**

需求复核：对照两份原始架构文档、获批设计说明和验收矩阵。质量复核：测试可靠、错误信息可操作、文档能从干净环境执行、非目标没有被暗中实现。两项均通过后阶段一才算完成。

---

# 阶段二至四总实施目录

本文件不把阶段二至四提前拆成代码子任务。只有满足进入条件后，才为对应阶段另建独立执行计划。

## 阶段二：审核与强化验证

**进入条件：** 阶段一十二项验收全部通过；四个真实试点完成；`phase-02-entry-inputs.md` 中每项缺口都有证据；至少有一个明确的跨模块 REVIEW 目标仓库。

**里程碑：**

1. `ai-review` 与 `ai-verify` Skill；
2. 设计审核和实现审核的结构化工作流；
3. V2、验收测试、集成测试和定向变异测试；
4. 独立 Verifier 及最小上下文包；
5. 由实际异常驱动的动态升级规则；
6. 编辑范围监控和高风险命令拦截 Hooks。

**退出条件：** 一个真实跨模块 REVIEW 任务完成设计审核、实现、独立验证、实现审核和 CI 放行；V2 证据可复现；Hooks 与核心 Policy 得到一致结论。

## 阶段三：高可靠性与模型路由

**进入条件：** 已积累足以区分任务类型和角色的内部记录；存在明确 V3 用例；费用、返工、审核缺陷和工具失败有统一采集口径。

**里程碑：**

1. V3、安全检查、故障注入、Dry-run 和回滚演练；
2. 模型能力注册表和内部表现记录；
3. 任务、角色、推理档位、工具环境和上下文相关的模型选择；
4. Claude Code、Codex 和其他模型的薄适配；
5. 独立上下文或多模型交叉验证；
6. 更严格的动作批准和分支保护。

**退出条件：** 一个真实高风险任务在沙箱中完成 V3 与回滚演练；模型选择给出可审计理由；任一高信任度都不能覆盖硬风险规则。

## 阶段四：独立编排器

**进入条件：** 多仓库、多平台或多模型任务量造成可量化的人工协调成本；阶段一至三接口稳定；暂停恢复和集中审批已成为真实需求。

**里程碑：**

1. 统一模型与平台适配器；
2. 并行执行、暂停和恢复；
3. 审批界面和预算控制；
4. 多机器状态同步；
5. 任务队列、可观测性和自动信任度更新。

**退出条件：** 编排器能从故障恢复且不跳过批准或验证；并行任务隔离有效；费用、状态、证据和批准可统一审计。

---

# 计划自查与执行交接

## 计划完成前自查

- [ ] 两份原始架构文档的阶段一要求均映射到本计划任务。
- [ ] 获批设计说明的七章、CLI、状态、Policy、验证、证据和 CI 均有实施任务。
- [ ] 所有任务给出明确文件、操作、命令和通过条件。
- [ ] 没有 `TBD`、`TODO`、“处理边界情况”或没有判据的“完善”。
- [ ] 任务顺序不存在尚未实现的隐藏依赖。
- [ ] 每章有定向测试、累计回归、需求复核和质量复核。
- [ ] 阶段一不实现真实模型 API、复杂评分、V2/V3、自动 push/merge/deploy/delete 或 Web 界面。
- [ ] 三个真实仓库试点分别覆盖 AUTO、ASK、REVIEW，BLOCK 覆盖拒绝与恢复。
- [ ] 本地和 CI 通过同一核心 Gate 得到一致结果。
- [ ] `subject_commit`、治理-only attestation commit 和 CI 最新 HEAD 重验形成无自引用的版本闭环。
- [ ] AUTO/ASK 从 VERIFIED 可达 APPROVED_FOR_MERGE，REVIEW 可达 WAITING_FOR_FINAL_REVIEW 并经 code approval 到 APPROVED_FOR_MERGE。
- [ ] Workflow 解析出的任务 ID 实际传给 verify 和 Gate，仓库身份不依赖绝对 checkout 路径。
- [ ] V1 使用 pytest-cov 分支覆盖 XML 和 diff-cover 90% 变更行门槛，包含 89% 失败与 90% 通过测试。
- [ ] `.coverage` 与 coverage XML 只写当前任务日志目录或 CI 临时目录，不形成非治理工作树变化。
- [ ] 四个真实试点从同一基线使用独立 worktree/branch 验收，旧任务不在后续试点或最终报告 HEAD 重跑 Gate。
- [ ] REVIEW Policy 试点在 Policy 变化后执行 escalate、重新 classify、重新 freeze 和重新 spec approve。
- [ ] `policy_changed` 要求 `--impact` 与 `--next-step`，允许 REVIEW→ESCALATED→REVIEW 同级重评但拒绝任意同级原因和降级。
- [ ] CI 与本地 CI 模拟都显式使用经校验的临时 `--ci-run-dir`；持久试点产物只由临时结果复制生成。
- [ ] 用户或独立审核者提出的问题已经修订并重新检查。

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-01-ai-code-collaboration-mvp-implementation-directory.md`. Recommended next step: use `subagent-driven-development` so each task gets a fresh executor plus review. If this environment has no subagent capability, execute inline using the same checklist and review checkpoints.
