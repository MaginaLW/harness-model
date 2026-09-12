# Runner Profile 与执行回执

`tools/runner/receipt.py` 提供可选的独立数据校验器。它比较冻结的 Runner Profile/执行要求与
一次 Execution Receipt，必要时只读关联现有 AI Flow evidence。它不启动 runner、不执行
输入中的命令、不读取日志正文、不联网、不改变任务/审核/批准，也不计算正式 Gate。

当前接口是 **1.0**，Schema 字典位于同一工具文件，不注册到 `.ai/schemas/`，不向旧 evidence
添加字段。原 `verify`、`review`、`status`、`gate` 继续按原方式调用。新工具的
`CONTRACT_MATCH` 只说明输入满足已冻结要求；它既不证明来源真实，也不验证产物正文，
输出固定包含 `source_authenticated=false`、`artifact_content_verified=false`、
`governance_effect=none`。哈希和 `source.kind` 字符串均不能认证实际执行。

## 可重跑示例

在可信检出的仓库根目录，用已安装项目依赖的 Python 执行：

```powershell
.\.venv\Scripts\python.exe tools/runner/receipt.py validate `
  --expected examples/self-hosted-runner/runner-profile.example.json `
  --receipt examples/self-hosted-runner/execution-receipt.example.json
```

```sh
.venv/bin/python tools/runner/receipt.py validate \
  --expected examples/self-hosted-runner/runner-profile.example.json \
  --receipt examples/self-hosted-runner/execution-receipt.example.json
```

[Profile 示例](../../examples/self-hosted-runner/runner-profile.example.json)和
[Receipt 示例](../../examples/self-hosted-runner/execution-receipt.example.json)全部是 synthetic。
虚构 ID、版本、时间和哈希只演示接口，不表示对应软件版本推荐、真实包摘要、runner 在线、
实际仓库访问权限或 CI 通过。该示例没有关联 AI Flow task。

CLI 的 `validate` 子命令要求 `--expected` 与 `--receipt`，有正式关联时另加
`--evidence <EXISTING_EVIDENCE_JSON>`。成功比较返回 0；输入或比较失败返回 2，标准输出
给出 `REJECTED` 和固定错误代码，不回显输入正文、秘密值或异常路径。未知 CLI 参数同样
非零。任何失败、缺项或未观察到的退出码都不能靠调用方最后一个成功命令掩盖。

## 冻结输入与真实证据

Profile 在 1.0 中同时承载独立冻结的执行要求。固定、可信的目标、规格、检查清单与环境
定义应来自审核过的任务基线；具体 run/job/attempt 和观察摘要、产物摘要应来自获准观察者
的独立读取。可以在执行结束后将这些观察事实附到执行前已冻结的要求，保留原版本和差异。
不要从待验 receipt 复制一份 expected 再宣称获得独立证明。

每次执行或尝试都需明确 `receipt_id`、`run_id`、`job_id`、`attempt`、
`observation_sha256` 和允许的 UTC/时区时间窗口。代码、检查规则、环境或关键依赖变化时，
重新冻结要求；旧 Profile/Receipt 保留。校验器拒绝相对于这份 expected 的旧身份/旧缓存，
但不会自行查询远端 head 或判断调用者给出的 expected 是否仍为当前权威基线。

`github_api`、`local_tool`、`agent_claim` 的语义不同。前两者也只是来源分类；调用者仍须
保留可独立核验的原始 API/本地执行资料与生成身份。`agent_claim` 不可用于成功合同匹配。
如果攻击者同时控制 expected 与 receipt，或伪造全部相互一致的来源内容，本工具不能认证
其真假。工作区隔离、权限、网络和单活动实例字段是待核验的声明，不是 OS 安全保证。

## 1.0 数据契约

所有对象拒绝附加字段、空必需集合和未知枚举；每个集合上限为 128。JSON 输入每份最多
1 MiB、最多 24 层，必须是普通文件；文件本身的符号链接/重解析点、重复键、非有限数字、
无效 UTF-8 均拒绝。CLI 不保证整个输入路径祖先目录都在某个沙箱内，应从受控证据目录读取。
直接 Python 调用使用同样的结构、深度、大小和语义检查。错误信息不包括输入值。
本工具的内存 Schema 使用 Python 正则的绝对首尾匹配；SHA、版本和所有逻辑身份后的
换行都属于非法值，不能因为 expected 与 receipt 同时带换行而接受。未向其他语言发布
这些 Python 专用正则作为可互换 Schema。

| Profile 部分 | 必需事实 |
|---|---|
| 身份 | `schema_version=1.0`、`kind=runner_profile`；`repository.github_id` 是正整数，`owner_name` 是快照名称，`visibility=private`、`trust=trusted`。当前版本只支持单仓 repository-level 可信私有接入；组织共享需后续独立设计。 |
| Runner | 正整数 runner ID、稳定 `profile_id`、scope、Windows/Linux/macOS 与 X64/ARM64、版本、低权限声明、独立工作区声明、单活动实例声明、逻辑网络引用、环境摘要。labels 不能代替这些访问控制与观察事实。 |
| 代码 | base、subject、实际 checkout 的完整 40 位 SHA，实际被测树摘要；`dirty=false`。PR head 与 merge checkout 可以不同，但必须在冻结要求中分别写明。dirty 开发日志可另外保留，本接口拒绝将其冒充提交验证。 |
| 执行定义 | portable workflow 相对引用、workflow/check-set/依赖锁 SHA-256；必要检查来自独立冻结清单，不能由待审分支减少。 |
| 运维声明 | work/cache/temp/retention 的逻辑引用，凭据机制引用；不含真实路径、token、密码或 Agent 登录态。`observation` 保存 profile 观察 ID 和时间，不是认证签名。 |
| 运行期待 | 唯一 receipt、run、job、attempt、来源类别、观察文档摘要与起止窗口；只接收 github_api/local_tool。 |
| 检查/产物 | `required_checks` 是唯一 ID + 受控 `command_ref`；`required_artifacts` 是唯一相对路径 + 独立观察摘要。每项都必需，1.0 不混入未定义的可选检查。 |
| 关联 | 无完整引擎则 `association=null`；有引擎则采用下文独立关联，不改变其原 evidence。 |

Receipt 有独立 `kind=execution_receipt`，原样绑定 repository、runner、code、definition、
association；source 记录来源/run/job/attempt/观察摘要和观察时间。started/finished/observed
时间必须顺序正确且位于冻结窗口内。只有 `result=succeeded` 且所有必要检查 `passed`、
真实观察的整数退出码为 0 才能匹配；failed/skipped/cancelled/unknown、缺项、重复项、
额外检查、命令引用变化和结论伪装均拒绝。布尔值不能冒充退出码或 repository/runner ID。

Artifact 引用只能是 portable 相对路径，拒绝绝对路径、盘符、反斜线、`..`、空段、通配符、
URL、Windows 设备名等；校验器不解析或打开这些引用。产物 SHA-256 必须与独立观察清单
匹配，但正文是否仍可读、hash 是否真正来自正文，需要观察者另外核验。日志正文不得塞入
receipt。凭据字段、控制命令字段、`gate_pass` 或 merge/approval 字段因附加字段规则拒绝；
常见 token/私钥格式也拒绝。这些检查不是任意秘密字符串的完整识别器，公开交付仍须脱敏。

## 与现有 AI Flow 的薄关联

`association` 包含 `repository_uuid`、`task_id`、`evidence_canonical_sha256`、
`spec_sha256`、`policy_sha256`、`classification_input_sha256`。GitHub 的数字仓库 ID 与
AI Flow 的 UUID 分开保存；它们不是可互换标识，二者的真实映射来自任务的可信接入记录。

有 association 时必须给出既有 evidence 文件。工具调用现有 `validate_contract("evidence", ...)`
作只读检查，核对 UUID、task、base/subject、CI attestation 对实际 checkout、规格/Policy/分类摘要、required check ID 集合、
检查结果和证据生成窗口；本地/GitHub来源分别关联 local/ci evidence。缺失 evidence、旧SHA、
旧规则、旧窗口、遗漏必要检查、失败/未验证或摘要变化均拒绝。
本地 evidence 的 subject 必须就是实际 checkout；旧本地 evidence 没有能证明另一个
checkout 的独立字段。若 checkout 与 subject 不同，保留原运行材料并通过能够绑定实际
checkout 的适用验证路径重新验证，不能用匹配的 subject 或摘要声称另一提交已测试。

`evidence_canonical_sha256` 使用 `canonical_sha256()`：对整个解析后对象按键排序、
`ensure_ascii=True`、紧凑分隔符、禁止 NaN 编码，再计算 SHA-256。它明确是规范化文档摘要，
不冒充现有 V2 `verification_snapshot_sha256`，也不代替原始文件字节摘要。消费者不改写
传入 evidence，示例的 hash 不能用于真实 evidence。

V2 的本地 final 与外部 CI pre-review evidence 保留原语义。工具不把关联结果提升为 final，
也不要求所有 CI evidence 先变 final；是否满足正式 Gate 的角色、review、approval、当前
新鲜度和完整 CI 组合仍由原引擎判定。关联函数没有任务写入或 finding resolve 路径。

## 关闭与恢复

未使用本工具时原流程完全不受影响。集成方可显式调用：

```sh
python tools/runner/receipt.py validate --disabled
```

返回 `ADAPTER_DISABLED`、`contract_matched=false`、`governance_effect=none`，不读取输入文件。
退出 0 只表示该可选适配已关闭，不能作为 CI/验证通过。调用者继续执行原有 verifier/Gate，
不能把“已关闭”当作缺失必需验证的替代。原 evidence、Schema、Policy、CI 与历史记录都不
需要迁移、删除或重写。

本接口不声明 PREPARED→ONLINE→SMOKE_PASS→PILOT_PASS→ADOPTED 自动晋级。真实运行、
正确 runner、必要平台检查、服务恢复及 main 生效需要各自证据。没有远端/现场验证时保持
未验证；任务 02 的整体完成不能由示例匹配或合成测试推断。
