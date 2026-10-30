# TASK-0120 路径隐私修复规格

## 目标

在不改写既有任务及其证据的前提下，使新任务和新验证证据对已知本机路径采用占位符，避免必要的治理记录在对外审查时暴露已知机器路径，同时保持真实执行和现有敏感值脱敏语义。

## 范围

自主规则 PR #134 已以 merge commit `0a9892f343ccadefa362230815878c9550681c88` 合入公开目标仓 `MaginaLW/harness-model` 的 `main`；创建本任务前已核实其为当时 main，并核实 required check `ai-quality-gate`、严格更新要求、管理员保护以及禁止强推和删除分支。将该提交普通 merge 到测试先行提交 `e0a2c385eee5f9e0816a4573b975695cb49ce33d`，产生本任务基线 `6f1aa18242e10d08e04a99861951dbda91def9fc`，分支为 `codex/privacy-test-first`；不 rebase、强推或改写已推送历史。测试先行批次只改测试及用法文档，在源码修复前不能单独发布。已核对 main 的三个目标源码 blob 与候选父版本一致；后续如有基线或源码变化，须重新检查并复核。

受治理的实现范围仅为：

- `src/aiflow/task_service.py`
- `src/aiflow/process_runner.py`
- `src/aiflow/verification_service.py`

在本任务完成独立设计审核、适用规格批准并进入实施后，重放已审候选 `2cf78ea653b75c421d2fbbde155e55d92e508e78` 相对其父提交的三个源码文件变更，生成本任务自己的提交；核对差异与上述候选等价，并验证相关最终源码 blob 与候选一致。若最新主线已经改变这些源码，使等价重放会覆盖其他变更，则停止并按实际情况重新设计、审核和分类。不能把旧任务的提交或禁令当作本任务的批准。

测试及用法说明属于独立的 task-free 测试先行批次，与本实现一起验证和交付；本任务自身的治理记录由 CLI 在其任务目录追加。本任务的初始 base 与 subject 均为 `6f1aa18242e10d08e04a99861951dbda91def9fc`；后续实现 subject、PR head 和动作目标须以执行时真实 Git 与目标仓状态重新核对。

## 启动来源与真实风险事实

使用受审候选 CLI 源码 `2cf78ea653b75c421d2fbbde155e55d92e508e78` 和 worktree 编号防冲突包装创建 `TASK-0120`。包装脚本 SHA-256 为 `51934658749b11d032a0f4c941b63d095d91e8dfdf15c90253894822b0d91c6c`；执行前核对其代码，并核对候选源码 43 个已跟踪文件与该提交一致。实际运行的 Python 为 3.11.9。以下调用中的 `<python>` 和 `<reviewed-wrapper>` 分别代表该 Python 可执行文件和上述包装脚本，不在规格中保存本机路径；其余参数按实际调用逐项列出：

```text
<python> -B <reviewed-wrapper> start --objective "Prevent known machine-path leakage in new tasks and verification evidence" --allow src/aiflow/task_service.py --allow src/aiflow/process_runner.py --allow src/aiflow/verification_service.py
```

调用成功返回 `TASK-0120`，没有传入任何 `--forbid-action`。任务记录中的 `push`、`merge`、`deploy`、`delete`、`secret_export`、`paid_external_call` 均来自当时 `.ai/policy/permissions.yaml` 的 `forbidden_automatic_actions` 默认项；这项来源判断依据实际调用、候选创建代码和当前 Policy，不推及任何旧任务，也不移除或放宽默认禁止项。

完整记录计划的公开副作用：向公开仓库 `MaginaLW/harness-model` 推送具体分支、创建 PR、满足条件后合并 PR。披露高影响、跨模块、行为变化、回归风险、条件可逆性、真实验证要求，以及 spec、code、action 批准需求；按事实运行分类，不为了规避 ASK 或降低等级虚报。已知由 Policy 注入的默认 `forbidden_automatic_actions` 保持原样；对本任务的来源只能以实际 `start` 和当时 Policy 证据证明，不能推广到旧任务。显式或来源未知的任务禁令继续有效。

## 非目标

- 不重写、删除、脱敏覆盖或公开未经授权的 TASK-0116 或其他旧 task、恢复标记、审批、review、evidence、日志和证据绑定；旧任务的禁令不解除、不转移，也不复用其绑定到旧版本的批准和验证结果。
- 不宣称所有未知路径、原始日志、覆盖率产物或外部材料已被匿名化；不传输未经授权的私有材料。
- 不改 Policy、Schema、Hook 程序、CI、质量门槛或分支保护；不忽略、禁用或绕过实际集成 Hook 或服务端的拒绝。
- 不把调用例外、actor 标签、本地 Gate、测试通过或用户的目标授权伪装成机器验证的身份认证、单次消费或对任意外部动作的授权。

## 验收条件

- 新建 task 与新建失败恢复标记不包含创建机器绝对路径；旧任务与旧恢复标记仍能读取，并保持原有恢复语义。
- 新本地证据命令摘要仅对已知解释器、仓库根和运行目录使用明确占位符；新 CI 复现命令对已知运行目录和证据输出路径使用占位符。真实执行 argv、环境、超时、输出位置、结果解析与原有 secret 脱敏保持不变；未知路径和日志不作通用脱敏承诺。
- 以本任务的冻结规格、真实 facts 和 subject 完成独立设计审核、适用 spec 批准、实施、sync、完整适用的原生 V1 或 CLI 按事实要求的更高等级验证、独立实现审核、code 批准和 Gate；不得借用 TASK-0116 的旧版本绑定结果。完整测试、85% 总覆盖率、90% diff coverage、whitespace、Ruff、format、mypy 与目标仓 required checks 保持不变；记录实际结果和跳过项。
- 先行测试批次中的任务创建与恢复、真实 argv/环境、secret、路径前缀和 Windows/POSIX 边界及 CI 复现占位等覆盖与本任务候选一起运行。该批次中任何红灯不得单独对外发布。
- 公布前对拟提交的全部新 task 记录、证据、文档和源码做已知本机路径、用户名及机器名检查；忽略的原始日志保留在本地，不因其未入库而声称日志已脱敏。既有历史文件不得重写以通过检查。
- 外部交付前分别核对并记录具体 push、开 PR 和 merge 的授权与适用动作记录，包括目标仓、分支/ref、当前 subject、实际 PR head、条件、有效期及单次使用状态；所有者已给的授权如覆盖该动作，不重复请求。仅在适用任务、Policy、Hook、目标仓规则和当前版本绑定均满足时执行；required CI 成功且仍绑定当前 PR head 后以 merge commit 合并。对于所有者明确授权的具体 push/merge，可按已生效的 Hook 文档例外不主动调用该必拒 wrapper；任何真实的已安装 Hook 或服务器拒绝仍须遵守。

## 禁止动作

禁止未经授权的外部副作用，以及部署、删除数据、凭据导出、付费调用、强推或改写已推送历史；不得删除或重写任何旧任务记录。显式或来源未知的任务禁令不得由 action 记录消除。

## 错误行为

授权、真实风险事实、来源、基线、scope、版本绑定、审核、验证、隐私检查或目标仓权限有缺失、失效、冲突时，停止相关动作，保留记录并修复后重新核对；不伪造通过，不降低门槛。可继续已授权的不依赖该阻塞的工作。

## 风险

路径替换范围限于已知值；第三方输出、旧证据和原始日志仍可能包含路径，公开前须按实际内容检查。CLI action actor 与单次使用目前依赖过程核对，不能证明调用人的真实身份或提供原子消费。公开推送或 PR 可能已被外部读取，无法保证撤回。

## 回滚

若需要撤销已合入的源码，按仓库规则审阅并以 Git revert 恢复；测试及文档的先行提交按实际依赖关系单独处理。所有既有及新产生的任务、审核、证据和日志保持原始历史与适用留存方式，不通过改写历史回滚。
