# AI Flow 非覆盖初始化

[PR #140](https://github.com/MaginaLW/harness-model/pull/140)已合并并交付本页命令。

普通 wheel 提供 `init preview`、`apply`、`inspect` 和 `migration-plan`。当前仅支持 `native-python-v1`：目标须是已有提交、包含 Python 源码及 `[project].name` 的普通 Git 工作树，首次预览时尚无 `.ai`，根目录不能有 `package.json`。写入限 Windows x64、CPython 3.11、本地 NTFS；Node 验证与 agent-bridge 的实际采用另行交付。

先按[资源包说明](resource-bundle.md)构建并安装普通 wheel。可编辑安装没有内置资源，不会隐式读取源码仓 `.ai`。运行材料中的绝对路径只保存在本地，预览和审核文件放在目标仓之外。

## 预览与审核

```text
python -m aiflow init preview --target <TARGET> --profile native-python-v1
```

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

初始化只校验固定验证合同的结构，不准备工具、依赖或外仓 V2 材料，不证明目标 V0/V1/V2 已可执行。

这些边界不提供整棵 Git 工作树的原子锁、恶意同用户代码沙箱或断电事务保证。完整跨仓步骤见[接入方案](sdk-and-engine-plan.md#完整引擎跨仓初始化)。
