# Task Specification

## 目标

完成 Chapter 11.3：从 11.2 的仓库级固定 manifest 读取精确五项声明，在逐项隔离、可清理的 detached 临时 Git worktree 中应用对应的封闭 AST mutation operator，并以固定、shell-free subprocess 只运行该项唯一 detector；返回不可变的内存执行事实并证明主工作树没有变化。本任务不持久化 killed/survived evidence，不接入 live V2，也不改变 approval 或 Gate 结论。

## 范围

1. 本规格只能在 TASK-0012 已有 `merge_recorded`、状态为 `MERGED` 后冻结。该事件记录的 external merge commit 固定为 `e5b00f4502354ef9d18ad7d1f9f1c52e27aac604`；task-local `dependency-resolution.md` 保留 TASK-0012 状态、external merge commit、最初 TASK-0013 base 与当时 HEAD 一致的不可变证据，以及用户对绑定旧 classification input `962b313a40736ef20ab9da93a530975b2e946280ea7e99e551cd4e9ec5d62569` 和 Policy `f4854d7fa05e5bddc21303350476bf47568bfe50f64c9d1f9199c0d744321bbf` 的 `BLOCK -> REVIEW` 明确人工降级授权。为持久化 TASK-0012 close receipt，随后创建的本地治理提交 `dc49293936ae8f705b7a474dc5c7b0ac0c981865` 必须以该 external merge commit 为唯一父提交且只修改 `.ai/tasks/TASK-0012/events.jsonl` 与 `.ai/tasks/TASK-0012/task.yaml`；TASK-0013 的执行 `base_commit`/初始 `subject_commit` 固定改绑该干净治理提交，并在 `baseline-transition.md` 记录两种 commit 语义与精确路径。该改绑必须通过 `spec_changed` 同路由升级、证据化 resolution、重新 classify、重新 freeze 和新的 design review 使所有版本绑定重新一致；旧 classification/freeze/review 只保留为被取代的审计历史，不能充当当前批准。仅有 Chapter 状态投影中的“11.2 completed”不能替代这些证据。
2. 唯一执行输入是 `load_mutation_manifest(repository_root)` 返回的固定 `phase-02-critical`、精确有序五项声明。runner 不接受调用方提供 manifest 路径、operator、detector、argv、环境、transform、worktree 路径或 timeout。
3. 新增 `src/aiflow/mutation_runner.py`，提供两个冻结 dataclass。`MutationProbe` 字段精确为 `mutation_id: str`、`baseline_exit_code: int | None`、`mutant_exit_code: int | None`、`timed_out: bool`、`duration_ms: int`、`reason_code: str | None`；`MutationRun` 字段精确为 `manifest_id: str`、40 位 `subject_commit: str`、manifest 顺序的 `probes: tuple[MutationProbe, ...]`、`main_tree_unchanged: bool`、run-level `reason_code: str | None`。preflight 失败抛出稳定 `ContractError` 且不返回部分 run；首项 worktree 创建尝试后始终返回五项有序 probe，安全失败后尚未执行的项使用 `MUTATION_NOT_EXECUTED`，run-level reason 覆盖单项正常退出事实。公开结果不得包含 `killed`、`survived`、evidence/log ref、时间戳、绝对 scratch 路径或动态环境字段。
4. runner API 仅接受 `repository_root` 与完整 `subject_commit`。subject 必须存在且可解析为 commit。临时根固定由 `tempfile.mkdtemp(prefix="aiflow-mutation-", dir=tempfile.gettempdir())` 创建并立即 resolve，且必须是规范化系统临时根的受控直接子目录；每项 worktree 只能位于该根下的规范化 mutation ID 子目录。所有 Git 调用固定为 `git -c core.hooksPath=<已验证的空临时 hooks 目录> ...`、`shell=False`；不得建立或移动 branch/tag/ref，不 checkout 到主工作树。
5. preflight 必须证明 `git rev-parse HEAD == subject_commit`，并以固定 pathspec 验证 manifest、schema、五个 target 与去重 detector 文件相对 subject 没有 staged/unstaged 漂移；无关的预存 dirty 状态允许保留并纳入前后快照。还必须逐个对这些受控路径运行 `git check-attr filter -- <path>`，仅接受 `unspecified` 或 `unset`，拒绝任一 checkout filter。每个 worktree 建立后重新加载固定 manifest，并与 subject/preflight 的 manifest 身份、顺序和完整字段逐字一致；任一漂移在 mutation 或 detector 启动前失败。
6. 五个 operator 与路径/symbol 必须一一硬编码，不允许通用文本替换：
   - `drop_targeted_mutation_required_check`：只在 `src/aiflow/policy.py::_validate_cross_file` 的 V2 fixed extras tuple 中删除唯一 `targeted_mutation` 项。
   - `allow_same_verifier_actor`：只使 `src/aiflow/verifier_service.py::validate_verifier_actor` 中唯一的 same-actor 拒绝 guard 不再触发。
   - `allow_nonpassing_required_check`：只使 `src/aiflow/approval.py::_v2_evidence_current` 中唯一的 required-check non-passing guard 不再返回 false。
   - `accept_non_killed_mutation`：只使 `src/aiflow/gate.py::_v2_gate_facts` 中唯一的 mutation outcome predicate 接受 non-killed 项。
   - `ignore_snapshot_mismatch`：只使 `src/aiflow/evidence.py::validate_v2_snapshot` 中唯一的 snapshot mismatch 拒绝 guard 不再触发。
7. AST 变换必须先确认目标顶层函数恰好一个、预期结构锚点恰好命中一次，并在写入隔离 target 前 `fix_missing_locations`、`compile` 验证。零次、多次、错误 target/symbol/operator 组合或编译失败均 fail closed；不得自动猜测、模糊匹配或回退到字符串替换。
8. baseline 与 mutant detector 的 argv 均精确固定为 `(sys.executable, "-m", "pytest", "-q", <manifest 已校验 nodeid>)`。每次 subprocess 固定 `shell=False`、cwd 为隔离 worktree、timeout 为 60 秒、进程组隔离，并在 timeout 时终止完整子进程树；不得使用 `-c` bootstrap 或拼接命令字符串。
9. detector 使用最小环境：仅受控 `PATH`、Windows 必需的 `SystemRoot`、指向该项隔离临时目录的 `TMP`/`TEMP`、固定 `PYTHONPATH=<worktree>/src`、`PYTHONDONTWRITEBYTECODE=1`、`PYTHONNOUSERSITE=1` 和 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`；不继承 token、代理、凭据、用户路径、coverage 或自由环境变量。runner 本身不创建网络 client、不传代理/网络配置，五个冻结 detector 必须保持离线；本任务不宣称提供 OS 网络沙箱。baseline `0` 与 mutant `1` 的成对执行必须证明隔离源码生效，而非导入主工作树/editable-install 路径。
10. 每个隔离 worktree 先在未变异状态运行同一 detector 并要求 exit `0`，再应用唯一 mutation 并运行同一 detector。baseline exit `1` 使用 `MUTATION_BASELINE_FAILED` 且不启动该项 mutation；mutant 的 pytest 正常退出码 `0`/`1` 只作为原始执行事实返回，11.3 不持久化或命名为 survived/killed。任一阶段 exit `2`–`5`、launch 失败、timeout、operator/worktree/cleanup 失败均带稳定 reason code；发生安全或基础设施失败后停止创建后续 worktree，并以 `MUTATION_NOT_EXECUTED` 补齐剩余有序 probe。stdout/stderr 固定写入 `DEVNULL`，不落盘、不进入公共 dataclass，也不在内存无界累积。
11. 每项始终从干净独立 worktree 开始并在 `finally` 中清理。`delete` 继续属于禁止自动执行动作，decision unit 固定声明标准 `action_approval` permission requirement；批准单位是一个精确、一次性的外层命令事务，不是单个内部 runner 调用。该批准是实施者执行真实 worktree 测试/V1 的 AI Flow 前置，不进入 runner API，也不由 runner 读取。允许的事务只有两类：

    - `focused_integration`：pytest argv 精确为 `(sys.executable, "-m", "pytest", "-q", "tests/integration/test_mutation_runner_contract.py")`，内部 `run_targeted_mutations` 调用预算为最多一次，即最多创建一个 `aiflow-mutation-*` root 和五个逐项 worktree。
    - `v1_verify`：精确的单次 local 或 CI `aiflow verify TASK-0013` 完整 V1 命令，不得带 `--check` 或 `--finalize`，并绑定当前 V1 Policy plan；当前 `regression_tests` 与 `coverage_xml` 各收集一次真实 integration test，所以内部 runner 调用预算固定为最多两次，即最多两个 root、每个最多五个逐项 worktree。通过事务应观察到两次；提前失败可以少于两次，但剩余额度不得用于另一命令。任一 check 选择、测试收集、spec、Policy、classification 或 subject 变化均使批准失效。

    每个事务前，实施者必须在上述绑定均未变时生成 task-local action file，经用户明确同意后用 `aiflow approve --type action --action-file ...` 记录；文件固定 `action_type=delete`、当前 `subject_commit`、`single_use=true`、未过期时间、事务类型、完整外层 argv 和对应的 1/2 次 runner invocation budget。批准 target 必须在生成 action file 时解析为 `<resolved-system-temp>/aiflow-mutation-*` 受限模式；conditions 必须要求每次内部 runner 仅以固定 `mkdtemp` 创建一个匹配模式的 direct-child root，所有 worktree/hooks/temp 文件均为该 root 后代，只删本事务创建对象，任何 containment 或预算不满足即拒绝，且不触及仓库根/用户目录/workspace。focused integration、local V1、CI V1 或任何重跑都是不同事务，不能共用 action approval；不得在 `v1_verify` 外直接运行会收集真实 integration test 的全量 pytest/coverage，除非先重新冻结新增的精确事务类型和预算。

    当前 AI Flow 尚无 action-consume 命令或 action-use schema，因此按仓库约定采用明确的人工审计 fallback，不宣称由 CLI/runner 强制 single-use：实施者在启动外层命令前核对 action file SHA 与 approval record、expiry、spec/Policy/base/subject/current classification，并确认不存在同 SHA 的 use record；随后先以 `apply_patch` 创建 task-local `action-use-<action_sha256>.md`，精确记录 task/DU/action SHA、上述绑定哈希、事务 ID/类型、完整 argv、runner budget、`started_at` 与 `status: started`，从外层命令启动起即保守视为已使用。命令结束或异常后再以 `apply_patch` 补记实际 runner 调用数、verification run/evidence ID（若有）、结果、cleanup 状态与 `completed_at`；即使进程崩溃、少用预算或结果未知，该 approval 也不得重用。每次 remove 前重新做 containment；Windows 锁文件清理允许最多三次、总计不超过一秒的有界重试。未获当前批准时只能运行 mocked/seam 单元测试，不得创建真实 worktree；cleanup 失败不得返回成功。
12. runner 在最外层 `finally` 后比较主工作树 `git status --porcelain=v1 --untracked-files=all` 原始 bytes、权威 manifest/schema、五个 target、去重 detector 文件的 SHA-256，以及 `git worktree list --porcelain` 原始 bytes。若主树发生变化，run-level `MUTATION_MAIN_TREE_CHANGED` 优先于任何正常/cleanup 结果；否则 cleanup/registry 恢复失败为 `MUTATION_WORKTREE_CLEANUP_FAILED`。不得自动恢复、stash、reset、checkout 或删除用户变化。
13. 新增 `tests/unit/test_mutation_runner.py`，覆盖五个精确 AST 变换、零/多锚点、错误 operator-target 组合、无效 subject、worktree/路径逃逸、create/write/compile/launch/timeout/pytest infra/cleanup 失败、最小环境、进程树终止、顺序与不可变返回。Windows 无 symlink 权限时必须通过解析/执行 seam 确定性覆盖，不得跳过新增安全断言。
14. 新增 `tests/integration/test_mutation_runner_contract.py`，在当前受控 subject 上真实建立五个逐项隔离 worktree，证明每个固定 detector baseline exit `0`、mutant exit `1`，隔离源码生效、五次执行互不污染，且主工作树文件、状态和 worktree 注册表前后完全一致。exit `1` 只称为 raw probe fact；11.4 才命名并持久化 killed。测试不写 task evidence 或永久日志。
15. 更新 Chapter 11 实施文档、chapter state 和 overall state：仅把 11.3 标为 completed、指针移到 11.4，累计计数变为 63/65 tasks、338/348 steps、16/18 exits；11.4、11.5、两个 Chapter 11 exit checks、持久 mutation evidence 与 live V2 仍 pending。
16. TASK-0013 按 `REVIEW + V1` 自举验证；四项 `verification_requirements` 保持 false，因为 V2 的 mutation evidence/replay 尚未由 11.4/11.5 接线。这不是验证降级，也不得把五个隔离 detector 的退出码扩写为 live V2 passed。

允许修改范围固定为：

- `src/aiflow/mutation_runner.py`
- `tests/unit/test_mutation_runner.py`
- `tests/integration/test_mutation_runner_contract.py`
- `docs/implementation/chapter-11-acceptance-integration-mutation.md`
- `docs/superpowers/state/chapters/chapter-11.yaml`
- `docs/superpowers/state/overall.yaml`

## 非目标

- 不修改 11.2 manifest/schema/loader、现有通用 `process_runner.py` 或其 API。
- 不修改 active Policy、classification/evidence schema、`verification_service.py`、CLI、approval、Gate、Verifier、Hooks 或 V0/V1 行为。
- 不把 mutation runner 接入 live V2，不替换 `VERIFICATION_CHAPTER11_NOT_IMPLEMENTED`/`chapter-11-pending`，不 finalize V2 evidence。
- 不持久化 stdout/stderr、killed/survived/unverified、result/log ref、预算、运行时间或 mutation evidence；这些属于 11.4。
- 不实现 missing/survived replay、approval/Gate 拒绝接线或 Chapter 11 exit checks；这些属于 11.5。
- 不建立通用 mutation framework，不接受自由 AST/text transform、shell、插件、网络服务、任意 pytest nodeid 或任意仓库 target。
- 不支持并行 mutation；11.3 固定按 manifest 顺序串行运行，避免共享 Git/worktree 状态竞争。
- 不新增 action-consume CLI/schema，也不让 runner 读取 task approval；single-use 在该能力上线前按 task-local 人工审计 fallback 保守执行。

## 验收条件

1. TASK-0012 `MERGED` 前，TASK-0013 不得冻结；依赖满足、旧输入绑定的 `BLOCK -> REVIEW` 人工降级已记录、TASK-0012 close receipt 已作为 `e5b00f4` 的单一治理后继提交持久化，并完成 TASK-0013 `base_commit`/初始 `subject_commit` 改绑的 `spec_changed` resolution、重新分类、冻结、新设计审核和当前 spec approval 后才可 begin 或实现。
2. 权威 manifest loader 在主工作树与每个隔离 worktree 都返回相同精确五项，runner 不存在任意 manifest/operator/detector/argv/env/scratch/timeout 输入面。
3. 五个 AST operator 各自只修改声明的顶层函数和唯一保障 guard；0/多锚点、结构漂移或交叉配对以稳定错误拒绝，隔离文件保持可编译。
4. 每项 detector 在其独立 mutant worktree 中真实退出 `1`；未变异同一 detector 在干净隔离 worktree 中退出 `0`，证明失败来自对应 mutant 而非 fixture/import 污染。
5. detector 进程实际从隔离 `src/aiflow` 导入；固定 argv、`shell=False`、最小环境、cwd containment、60 秒 timeout 与完整进程树终止均由可执行测试证明。
6. baseline 必须 exit `0`；mutant exit `0`/`1` 保留为原始事实。exit `2`–`5`、launch/timeout/operator/worktree/cleanup 异常稳定失败，不被写成 killed、passed 或 Gate-eligible。
7. 成功、mutant exit `0` raw fact、timeout、operator 失败、pytest infra failure 和 cleanup failure 后，主工作树的预存 dirty 状态、manifest/target/detector bytes 与 Git worktree 注册表均保持原样。
8. runner 不写 `.ai/tasks/**/evidence.json`、mutation log/result 或主工作树业务文件；返回对象不可变、有序且不包含绝对 scratch path、动态环境或永久 log ref。
9. live V2 pending-mutation 回归继续证明 `targeted_mutation=unverified`、reason `VERIFICATION_CHAPTER11_NOT_IMPLEMENTED`、manifest ref `chapter-11-pending`、conclusion failed。
10. V0/V1、Policy、manifest、review/evidence/approval/Gate 既有回归全部保持通过。
11. focused tests、`uv run aiflow validate/scope TASK-0013`、Ruff、format、mypy、全量 pytest、branch coverage、Python diff coverage不低于 90% 和 `git diff --check` 全部通过，并完成独立 implementation review。
12. Chapter/overall 只记录 11.3 隔离执行能力，不能写成 mutation evidence 已持久化、11.4/11.5/exit checks 完成或 live V2 passed。
13. 每个真实 `focused_integration` 或 `v1_verify` 外层命令事务前都存在 spec/Policy/base/subject/current classification、精确 argv 与 1/2 次 runner budget 绑定且未过期、未使用的 single-use `delete` action approval，并在启动前先建立该 SHA 的 `status: started` 人工 use record；执行后补记实际调用数与结果。通过的 V1 事务必须恰好观察到 `regression_tests`/`coverage_xml` 各一次 runner 调用；提前失败可少用预算但不得复用剩余额度。验收证明该 fallback 记录完整、重复 SHA/超预算/跨事务复用被人工流程拒绝，但不宣称当前 CLI/runner 已提供 action-consume 强制；未获批准时没有真实 worktree create/remove。

## 禁止动作

- 禁止 push、merge、deploy、package publish、凭据导出、付费外部调用，以及未经单独授权的 task close。
- 禁止修改、stash、reset、checkout、clean、删除或自动恢复主工作树文件；禁止在主工作树应用任何 mutant。
- 禁止 `shell=True`、自由 argv/env/transform/path、runner 网络 client 或代理/网络配置、用户 hooks、branch/tag/ref 创建或移动；冻结 detector 必须离线，但本任务不宣称提供 OS 网络沙箱。
- 禁止把 pytest infrastructure failure、timeout、missing detector、cleanup failure 或未执行项表述为 detector failure、killed、passed 或已验证。
- 禁止扩大 allowed scope、改变 Policy/验证等级或跨入 11.4/11.5 而不重新分类、冻结、设计审核和批准。
- 临时 worktree 删除只能发生在当前、未过期、未使用的 single-use action approval 所批准的一个精确外层命令事务及其 1/2 次 runner budget 和规范化系统临时专属根模式内，并必须先验证精确 resolved path；不得跨事务复用、超预算，或递归删除仓库根、用户目录、workspace root、未验证路径。

## 错误行为

错误优先级固定为：

1. 11.2 manifest loader 的 `MUTATION_MANIFEST_*` / `CONTRACT_VALIDATION_FAILED` 原样优先透传。
2. subject 非完整 commit 或 Git 查询失败：`MUTATION_SUBJECT_INVALID`。
3. 临时根/worktree 路径无效或逃逸：`MUTATION_WORKSPACE_INVALID` / `MUTATION_WORKTREE_PATH_ESCAPE`。
4. worktree 创建、隔离 manifest 漂移：`MUTATION_WORKTREE_CREATE_FAILED` / `MUTATION_SUBJECT_DRIFT`。
5. operator 不支持、target/operator 不匹配、AST 锚点/编译前置不满足或写入失败：`MUTATION_OPERATOR_UNSUPPORTED` / `MUTATION_OPERATOR_PRECONDITION_FAILED` / `MUTATION_PATCH_WRITE_FAILED`。
6. baseline exit `1`：`MUTATION_BASELINE_FAILED`；detector launch、timeout 或 pytest exit 2–5：`MUTATION_DETECTOR_EXECUTION_FAILED` / `MUTATION_DETECTOR_TIMEOUT` / `MUTATION_DETECTOR_INFRA_FAILURE`。
7. 最外层 `finally` 发现主工作树事实变化：`MUTATION_MAIN_TREE_CHANGED`；该 run-level 错误覆盖任何正常 probe 或 cleanup 结果，但不得自动改回用户文件。
8. 主工作树未变但 worktree 清理或注册表恢复失败：`MUTATION_WORKTREE_CLEANUP_FAILED`。
9. 安全或基础设施失败后未启动的后续项：probe-level `MUTATION_NOT_EXECUTED`；它不能覆盖触发停止的首个 run-level 错误。

任一项失败不得返回部分清单为 passed；首项 worktree 创建尝试后返回的五项原始 probe facts 顺序必须与 manifest 完全相同，所有未正常执行项必须显式带 reason code。

## 回滚

所有持久变更仅为新 runner、测试和 Chapter 11 文档/状态投影。回滚通过后续反向提交删除 `mutation_runner.py` 与两份测试，并把 11.3 恢复 pending、指针移回 11.3、累计计数恢复 62/65 tasks 与 333/348 steps。运行期临时 worktree 必须已清理且主工作树 bytes/status 不变；若 cleanup 失败，只报告精确临时路径标识和稳定错误，不得通过广泛删除或 Git reset 伪造回滚完成。push、merge、deploy、task close 与 11.4/11.5 evidence 变更均不在本任务回滚授权内。
