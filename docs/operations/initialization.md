# AI Flow 非覆盖初始化

[PR #140](https://github.com/MaginaLW/harness-model/pull/140) 引入 Python 非覆盖初始化；[PR #143](https://github.com/MaginaLW/harness-model/pull/143) 增加 Node profile 和本地 V0/V1。

普通 wheel 提供 `init preview`、`apply`、`inspect`、`migration-plan` 与 `render-python-policy`，支持 `native-python-v1`、`agent-bridge-node@1` 与 `agent-bridge-node@2`。目标均须是已有提交的普通 Git 工作树，首次预览尚无 `.ai`。Python profile 要求 Python 源码及 `[project].name`，根目录不能有 `package.json`；Node profile 要求根 `package.json` 的非空 name 和 check/build/test 脚本，以及显式输入的四份完整 `3.1.0`（`@1`）或 `3.2.0`（`@2`，本地 Node V2）Policy。写入支持 Windows x64（CPython 3.11、本地 NTFS）及 POSIX / Linux（CPython >= 3.11）；[Node 本地 V0/V1](node-verification.md)与[普通安装的本地 Node V2](node-verification.md#revision-2-local-v2)已提供，真实 agent-bridge 采用另行交付。

先按[资源包说明](resource-bundle.md)构建并安装普通 wheel。可编辑安装没有内置资源，不会隐式读取源码仓 `.ai`。运行材料中的绝对路径只保存在本地，预览和审核文件放在目标仓之外。

## 预览与审核

```text
python -m aiflow init preview --target <TARGET> --profile native-python-v1
```

Node profile 必须显式使用候选 Policy：

```text
python -m aiflow init preview --target <TARGET> --profile agent-bridge-node@1 --policy-candidate-root <POLICY_DIR>
```

Node 候选目录只能包含完整同版本的 `hard-rules.yaml`、`routing.yaml`、`verification-levels.yaml`、`permissions.yaml`，只有 verification Policy 声明 Node profile。Node 不使用默认 Python 种子；apply 同时传入同一 `--policy-candidate-root <POLICY_DIR>`，migration-plan 同时传入 Node profile 和该目录。

预览输出单个 JSON 对象，本身不写文件。调用者将原始 JSON 以 UTF-8、无 BOM 保存到 `<PREVIEW_JSON>`，核对目标 Git 根、HEAD、清单、拟建 UUID、资源和四份 Policy 的哈希。Windows PowerShell 的默认重定向可能使用其他编码，保存时须明确编码。若需采用候选 Policy，四份文件必须同目录、完整且相互兼容，给 preview/apply 同时传入 `--policy-candidate-root <POLICY_DIR>`；默认种子仅供审阅，不是目标授权。

取得目标规则要求的内容审核后，创建审核 JSON。字段必须精确对应原预览：

```python
decision = {
    "schema_version": "1.0",
    "kind": "aiflow-policy-review",
    "preview_sha256": preview["preview_sha256"],
    "repository_id": preview["repository_id"],
    "profile": preview["profile"],
    "policy_version": preview["policy"]["policy_version"],
    "policies": [
        {"path": item["path"], "sha256": item["sha256"]} for item in preview["policy"]["files"]
    ],
    "reviewer": "<REVIEWER_LABEL>",
    "outcome": "APPROVE",
}
```

将结果以 UTF-8、无 BOM 保存为目标仓外的 `<REVIEW_JSON>`。摘要和 reviewer 标签只绑定输入，不认证审核人或产生执行权限；不得凭生成此 JSON 代替实际批准。

## 应用、恢复和检查

```text
python -m aiflow init apply --target <TARGET> --preview <PREVIEW_JSON> --policy-review <REVIEW_JSON>
python -m aiflow init inspect --target <TARGET>
python -m aiflow init migration-plan --target <TARGET> --profile native-python-v1
```

apply 重核原预览和材料，只创建固定清单内的新对象，以最后无覆盖发布 `repository-id` 标识完成。`.ai` 内未知文件、无法对应同一预览的安装、链接、资源或 Git 基线变化会拒绝；不会覆盖或清理现场。安装不复制源仓身份、历史、维护模式或授权。

中断后保留原预览、审核和全部现场，再执行相同 apply；只有精确可验证的 partial 才会补建缺项并保留同一 UUID。完成重放不写字节或时间戳。不要删除 pending/state 来制造全新安装，不要对有历史的仓重复应用旧预览。普通治理命令会拒绝未完成或资源已改变的新式安装；完整安装允许创建和读取目标自己的 task 历史，但产生历史后旧预览的 apply 会拒绝。legacy 无安装标记仓保持原行为。

inspect 和 migration-plan 只报告状态、文件差异与历史存在性，不自动恢复、迁移或删除。升级 Python 包不会暗改目标 Policy 或 Schema。未知或修改后的对象需要目标负责人按当前规则处理。

Windows 句柄在创建和身份发布期间保持对象保护；祖先目录仅需 TRAVERSE/READ_ATTRIBUTES，不要求系统 Temp 的 LIST_DIRECTORY。实际目标根和安装目录保留目录访问与共享约束。

POSIX / Linux 使用持有目录文件描述符（`dir_fd`）及 `O_NOFOLLOW | O_CLOEXEC`（目录附加 `O_DIRECTORY`，新建文件附加 `O_CREAT | O_EXCL`）拒绝符号链接和既有对象覆盖，并通过同目录 `link`、`unlink` 与 `fsync` 原子无覆盖发布 `.ai/repository-id` 后复核对象标识（`st_dev`、`st_ino` 与 `st_nlink == 1`）。POSIX 不提供 Windows 风格打开句柄共享排他锁，不防备同用户并发写入。

初始化只校验固定验证合同的结构，不准备工具或依赖、不探测 Node/npm、不运行 suite，也不证明目标验证已可执行。Node 本地 V0/V1 须显式准备绑定材料并完成任务验证、审核批准及 Gate，见[Node 验证](node-verification.md)。普通安装的本地 Node V2（`agent-bridge-node@2`）已在 `main` 交付（见[Revision 2 local V2](node-verification.md#revision-2-local-v2)）；目标 Node CI、combined Gate、真实 `agent-bridge` 接入以及 installed 外仓 Python V2 当前仍未验收／不受支持。

这些边界不提供整棵 Git 工作树的原子锁、恶意同用户代码沙箱或断电事务保证。完整跨仓步骤见[接入方案](sdk-and-engine-plan.md#完整引擎跨仓初始化)。

## 外部 Python 仓库便携验证

默认内置的 `native-python-v1` 种子 Policy（`2.6.0`）面向本仓 `src/aiflow` 与 `tools/ci/check_coverage.py`。外部 Python 仓库通过 `TASK-0192` 交付的便携 Python 验证接入时，可使用非覆盖渲染命令从内置或指定资源包直接生成四份同版本候选 Policy，再在 `init preview`、`init apply` 与 `init migration-plan` 中传入 `--policy-candidate-root <POLICY_DIR>`（按上文保存目标仓外的 `<PREVIEW_JSON>` 与 `<REVIEW_JSON>`）：

```text
python -m aiflow init render-python-policy --output-dir <POLICY_DIR> --cov-target <COV_TARGET> --source <SOURCE_DIR>
```

- `--output-dir` 必须指向尚不存在的新目录（不可含 `..` 遍历，且父目录须为真实普通目录，拒绝符号链接、重解析点或既有目标）。
- `--cov-target` 须满足覆盖率目标白名单（如 `sample_pkg` 或 `src/sample_pkg`）；`--source` 至少传一次且可重复指定多个仓库内相对源码目录（如 `--source src/pkg_a --source src/pkg_b`），按首次出现顺序去重。
- 可选 `--bundle-root <BUNDLE_DIR>` 用于可编辑安装或离线指定已校验资源包目录。
- 渲染仅改写 `verification-levels.yaml` 中测试命令的 `--cov=aiflow` 为 `--cov=<COV_TARGET>`，并将 `diff_coverage` 改写为 `["{python}", "-m", "aiflow.coverage_check", "--run-dir", "{run_dir}", "--base", "{base_commit}", "--source", ...]`；其余三份策略（`hard-rules.yaml`、`routing.yaml`、`permissions.yaml`）、允许命令/环境变量及 `85%` / `90%` 覆盖率门槛均保持原字节不变。
- 命令先在临时目录以资源包 Schema 完成四份策略与 `V0` / `V1` / `V2` 验证计划的完整解析校验，再原子创建 `<POLICY_DIR>` 并以非覆盖模式写入规范化 UTF-8/LF 文件，最后输出确定性 JSON 摘要（`schema_version`、`kind`、`policy_version`、`semantic_sha256`、`cov_target`、`sources`、`files`）。
- 目标 CI 可参考[外仓 Python CI 参考工作流](../../examples/adoption/external-python-ci.yml)接入 `aiflow validate`、`aiflow verify --ci` 与 `aiflow gate`，并在合入后的 `MERGED` 收尾 PR 中直接通过已安装包的 `python -m aiflow.closeout_check` 校验账本收尾（按 `aiflow status <TASK-ID> --format json` 的只读 `current_state` 分流）；不得复制本仓 `tools/ci/resolve_task.py` 或 `.ai/bootstrap-mode.yaml`。
