# 本机 self-hosted runner 迁移盘点实录

核查日期：2026-09-12。当前仓库状态为 **NOT_APPLICABLE**；目标选择前的迁移状态为
**BLOCKED（尚未选择可信私有目标）**。本记录是已执行检查的交付，不是部署方案或
迁移成功证明。未达到 PREPARED、RUNNER_ONLINE、SMOKE_PASS 或 PILOT_PASS。

盘点后，用户已在会话中明确选择一个私有目标并授权继续本地候选准备；后续在该目标
单独执行和记录，本报告保留 harness-model 的阶段事实，不公开私有目标详情。

本轮执行依据为用户提供的 `01_self_hosted_runner_codex_prompt_2026-09-12.md`。
其第一、二节限定一个可信私有仓库，并明确不授权改变公开 harness-model 的 runner；
当前仓库公开时，只读列出私有候选，等待目标决定，不自动进入另一仓库修改。
`02_harness_model_self_hosted_runner_plan_2026-09-12.md` 的扩展工作未实施。

## 实际基线

| 检查 | 实测结果 |
|---|---|
| 工作目录 | `${REPO_ROOT}`，origin 指向 `https://github.com/MaginaLW/harness-model.git` |
| 起始分支 / HEAD | `codex/zcode-document-pilot` / `ed4fac33c135d8e864c8e41e664f0a3755a373fa` |
| 工作区 | tracked 文件无修改；3 个既有未跟踪计划文件保留，未暂存或改写 |
| 其他 worktree | 2 个既有 worktree，均未操作 |
| 默认分支 | 远端 `main@f633c036cc2a0394f7b1efb20efe4d91ba944255`；起始 HEAD 比它前进 14 个提交、落后 0 个 |
| 起始分支的远端 ref | 精确 ref API 返回 HTTP 404；没有将本地分支视为已推送 |
| GitHub 身份与权限 | `gh auth status` 登录有效，账号 `MaginaLW`；OAuth scopes 为 `gist, read:org, repo`；仓库权限 ADMIN |
| 仓库 | ID `1319293089`；**public**；非 fork，未 archived/disabled |
| 仓库 runner | runner API 成功，`total_count=0` |
| Windows | Windows 11 Pro，版本 `10.0.26200`；OS 与运行时架构 X64，CPU Architecture=9 |
| 基础工具 | Git `2.55.0.windows.3`；GitHub CLI `2.98.0`；PowerShell `7.6.6` |
| 执行身份 | 当前终端未提权，但账号属于 Administrators；没有已验证的独立低权限 runner 身份 |
| 本机 runner | 未发现 `actions.runner.*` / GitHub Actions Runner 服务或 Runner.Listener / Runner.Worker 进程 |
| 安装位置探测 | 四个常见系统盘/数据盘 runner 目录均不存在；未全盘搜索，不排除别处存在未启动安装 |
| 仓库治理 | `.ai/bootstrap-mode.yaml` 仍 active；维护模式保持 |
| 保护规则 | main protected；required check `ai-quality-gate`，strict=true，enforce_admins=true；未修改 |

没有读取或导出 token/密码，没有读取个人私钥、浏览器或 Agent 登录文件。专用身份的
目录 ACL、工具 PATH 和凭据不可读性尚未验证；当前交互终端的工具可用性不是服务身份验收。
未选择真实 job，因此未安装 Python、Node、uv 或 runner 包。

## Workflow 与兼容性

本地 YAML 经解析，且其 Git blob 与远端 main 一致：
`f79c2b5eb4d0e39382e1210206379c9c21351ccf`。Actions API 也只列出一个 active workflow。

| Workflow / job | 平台与触发 | 技术兼容判断 | 本轮决定 |
|---|---|---|---|
| `.github/workflows/ai-quality-gate.yml` / `ai-quality-gate` | `ubuntu-latest`；PR opened/synchronize/reopened/ready_for_review；checkout 精确 PR head | Python 工具链可能跨平台，但 Bash 与权限行为需适配和实测，不能直接替换 runs-on | 保留原平台；公开 PR 代码不接入本机 |

不存在矩阵、reusable workflow、本地 composite action、container/services、Docker action、
macOS/GPU、签名或发布步骤。引用的本地 CI 脚本为 `tools/ci/resolve_task.py`，正式路径再调用
`python -m aiflow verify/gate`。脚本与治理 Policy 的平台假设不能仅从 YAML 判断为已验证。

具体适配点包括未声明 shell 的 `COVERAGE_FILE=...`、反斜杠续行、`$VAR`、`test`、
`sha256sum`、`mkdir -p`，以及显式 Bash 步骤依赖的 grep 等工具。Windows 默认 shell 下
这些命令不能直接照搬。符号链接相关测试存在权限不足时 skip 的分支，低权限身份跑测试
即使退出 0，也必须核对 skip 是否改变了实际覆盖范围。当前未做 Windows 等价测试。

完整质量门保持原样：完整 pytest、85% 总 branch coverage、90% diff coverage、whitespace、
Ruff、format、mypy；正式 AI Flow 路径和 90 分钟 job timeout 均未改。
仅 push 一个尚无 PR 的新分支不会触发现有 PR-only workflow；创建 PR 或向已有 PR 分支
push 会触发质量门。本轮均未执行。

## 真实运行证据与计费边界

按 UTC `created >= 2026-09-01` 查询，返回 44/44 个历史 run：38 success、5 failure、
1 cancelled；时间范围为 09-01 10:01:12 至 09-08 11:28:51。此为本月观察窗口，实际账单
周期和消耗来源未核实，运行数量或时长不等于计费分钟。

最新历史样本（只读回读，**不是本轮触发或迁移验收**）：

| 证据 | 值 |
|---|---|
| Run | [34220910193](https://github.com/MaginaLW/harness-model/actions/runs/34220910193)，success |
| Job | [102043541088](https://github.com/MaginaLW/harness-model/actions/runs/34220910193/job/102043541088)，`ai-quality-gate`，success |
| 提交 | `bbec6e05428173e03a94a602672193509ba177f1` |
| Runner | ID `1000000304`，name `GitHub Actions 1000000304`，group `GitHub Actions`，labels `[ubuntu-latest]` |
| 步骤 | Validate contracts 与 Bootstrap quality checks success；formal task / Verify and Gate / diagnostics 路径 skipped |

回读了 run/job 和步骤元数据，未下载历史完整日志；历史样本不证明当前本地 HEAD 通过 CI，
其 skipped 步骤也不记为成功。本轮新增 run/job/PR/远端提交均为无。

公开仓库使用标准 GitHub-hosted runner 的计算分钟免费，不能把 2,000 分钟提示归因于
本仓库；存储和其他服务费用须另行核对。参见实际打开核对的
[GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)。
本机安全边界参见
[Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)；
容器平台要求参见
[Self-hosted runners reference](https://docs.github.com/en/actions/reference/runners/self-hosted-runners)。

## 已完成范围与未完成项

- 已完成当前仓库、权限、可见性、runner、Windows 和 workflow 的只读核查；账号可见的
  私有候选另在会话中只读列出，名称和私有 CI 内容不写入公开仓库。
- 本地交付只新增本报告，使用 `codex/self-hosted-runner-inventory` 分支；属于维护模式
  下 task-free 文档变更，不修改 AI Flow 账本或升级清单文件。
- 验证限于事实回读、workflow 解析、文档 diff/whitespace 与泄露检查；未因新增报告
  宣称全量测试或远端 CI 通过。具体本地提交由最终交付列明。
- 未注册 runner、创建账号、修改 ACL、安装服务、push、创建 PR 或触发远端任务。
  未修改 Billing、保护规则、质量门或全局配置，未 merge。
- 没有已选定目标可编写实际安装配置、健康检查脚本或冒烟 workflow；不添加脱离目标的
  演示脚本，也不提前迁移真实 job。目标和安全身份明确后仍须先在线、冒烟，再迁移一个 job。

## 回退与阶段决定

本轮没有运行中的 runner 或远端配置需要回退，无须停服务或注销。保留本报告作为盘点证据。
工作区干净且需要返回原上下文时，可以 `git switch codex/zcode-document-pilot`；本次报告
保留在盘点分支。不要删除三个既有未跟踪计划文件，不执行 reset、clean 或自动 stash。
若未来报告进入其他分支，只有本次文档提交需要按实际提交号定向 revert；此操作未执行。

**盘点时的必要决定是选择一个可信私有仓库，现已由用户在会话中作出。** 目标选择要求
来自执行文件的明确范围。后续先完成目标的本地候选和身份检查，再将确实缺少的注册、
账号/ACL、服务、push/PR/触发授权按具体账号、目录、分支、测试及回退步骤集中说明。
仓库 ADMIN 权限不能代替这些动作授权；历史 AI Flow 批准也未复用。
