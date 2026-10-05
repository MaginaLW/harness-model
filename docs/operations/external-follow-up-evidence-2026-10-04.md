# 外仓后继证据与剩余依赖：2026-10-04

## 2026-10-05 取消只影响原自然 CI 路径

六个固定源码/报告的独立薄核已封存；本核没有新增 GET、业务或 VM 调用。
`i1-cancelled-natural-job-scope-001/ASSESSMENT.md` SHA256
`9b616b3a98d2f4c89997c5a63a0ea5e7833aa4d52488ae6c5b8f605c71cd91e0`。
TASK-0066 已批准 spec 将一次 cold BOOT 与 POSIX CI/服务交接明确区分；009
没有 queued/API 状态门，并声明 tree_or_ci_acceptance=false。原 cancelled
attempt 不可自然接取验收，但不会自动撤销同范围 BOOT spec，也不会成为 009
新增的拒绝条件。BOOT 当前仍缺真实 admission、资格和准确单次 action；启用
runner、服务交接或 CI 重跑须另外确定范围和动作。下列 14:18 实际窗口仍有效，
取消原因保持未知。详见[完整边界](backlog-execution-2026-10-04.md#2026-10-05-诊断-006-与取消范围核定)。

## 2026-10-05 晚间只读刷新：原 POSIX job 已取消

UTC `2026-10-05T14:18:11.645950Z–14:18:14.846072Z` 的八个固定官方 gh GET 均
HTTP 200 / exit 0，各 raw stdout/stderr、HTTP、exit、时间与 SHA 保留于
`${RUNTIME_ROOT}/harness-model-backlog-20261004-001/external-current-read-004`。
报告 SHA256 `448ae9971ce118bb8b98064bf7a6b49c3e2b05bddccc1f3fc1d1ef76d8375088`；
manifest SHA256 `a921898db67e09a98183bd65e3856553dd75b5cb2dbe55111d6e0eaa43dc5197`。
root 工具 `09dbec` 独立读取实际 HTTP body，核实两 SHA、全部 jobs/steps 与取消终态。

- r3s main 保持 `9e1b538c6acdcb8fde410172ebf1dff4485e6ffb`；
  [run 37177002687](https://github.com/MaginaLW/r3s-VPS/actions/runs/37177002687)
  attempt 1 已为 completed/cancelled，API updated_at 为 `2026-10-05T04:26:34Z`。
  POSIX `111361608389` 同为 completed/cancelled、runner 0、0 steps；Windows
  `111361608550` 保持 success，七 steps 全 success。取消原因及主体未查询，保持未知。
- r3s runner 21 online、22 offline，均 busy=false。既有停用约定未改变；恢复 runner
  不能让已终态的原 job 重新排队，后继验收须重新冻结合法的 job/action 路径。
- 精确 dotfiles 仓库为 `MaginaLW/ai-agent-dotfiles`，main 保持
  `ac8e4854b50592a1216acce7f0d08b718478e25a`；
  [run 37109686458](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/37109686458)
  attempt 1 保持 success，四 jobs、29 steps 全 success。自托管 runners GET 返回空；
  这不否定历史 jobs 中的 GitHub 托管 runner，也不证明实际 Apply。

八查询非原子；本窗口没有最新 run 发现、check-runs 或保护规则刷新，不构成 I1
两次 300 秒 host gates、双通道验收或新权限。没有 CI 取消、重跑、新 push、服务、
VM、SSH 或部署。原排队窗口、原件及既有规格批准仍保留；冷启动后继须按新实际
终态评估，不把原批准推导为新 CI 触发。下列旧窗口保持其当时事实。

## 2026-10-05 本地晨间只读刷新

新查询窗口为 UTC `2026-10-04T23:02:08.0985444Z–23:06:09.9473006Z`，18 个 GET，
各原始 body/stdout/stderr、exit、HTTP error 与哈希保留。查询非原子快照；本节不替代
I1 冷启动前两次 fresh host gate。树外 leaf 为
`${RUNTIME_ROOT}/harness-model-backlog-20261004-001/external-current-read-002`。
`current-summary.json` SHA256
`978c5d5bb77b5a3ca4ec7ad03d15ab761b8982ab45447971492aeac179b0e4ca`，
`manifest.json` SHA256
`9517d2f23bd670af665d5ef9219ce872fe46a69835609cce44c81dbfd7d246f0`；89 个原件摘要匹配。

- r3s 两端 main 仍为 `9e1b538c6acdcb8fde410172ebf1dff4485e6ffb`，本地现场 clean；
  自然 push run `37177002687` attempt1 未变。Windows job/check `111361608550`
  completed/success、七 steps success；POSIX `111361608389` queued/null、runner0、
  steps 空。其 API started_at 不是实际执行证据。22 offline/idle，21 online/idle。
- dotfiles 两端 main 仍为 `ac8e4854b50592a1216acce7f0d08b718478e25a`，本地现场 clean；
  run `37109686458` attempt1 的四 jobs/checks、29 steps 全 completed/success。完整 CI
  不证明实际 Apply、接管或部署；本窗口未执行这些动作。
- r3s protection/rulesets 仍各 403，配置未知；dotfiles protection 404 明示未保护，
  rulesets 为空。三条失败原始响应均保留，未当作成功或空配置。
- 宿主 QEMU 名称查询空，Worker 名称查询空。精确 Windows21 服务 Running/Auto、
  service PID2152，可见 Listener PID5604/parent2152；两进程 executable path 均 null，
  token/SID 未核。按可见路径过滤的 matching_listener_count0 不代表 Listener 不存在。
  guest BOOT、guest 服务、transport、WHPX、image chain/check 和 cold-copy 仍未执行。

未产生新 CI run 或 VM/SSH/服务动作。I1 草案的独立边界预审为 NO_GO_FOR_EXECUTION：
须补 native Task/单次 action、可执行消费 wrapper、opened final path/volume/file identity、
receipt 祖先、copy→image→launch 守卫和绝对绑定 SSH。原草案及 review 原件保留，后继
准备写入新独占 runtime 目录；实际批准和执行均未发生。

本记录刷新[待办第 4、5 项](follow-up-backlog-2026-09-22.md)的事实窗口，沿用
[下阶段启动条件](next-stage-start-conditions-2026-10-02.md)。它是只读核查结果，不是
runner 恢复、CI 重跑、Apply、部署或扩仓执行单；原历史失败、取消与准入边界保留。

## 来源与观察窗口

- 核查前确认 GitHub 当前活跃账号与两个目标仓库的 origin 所属账号一致；仅使用 Git 与
  GitHub CLI 的只读查询，没有输出凭据正文，没有执行 workflow、主机或外仓写入。
- 首轮本地 Git、远端 main、workflow、run/jobs/check-runs 与入口文档核查的包络时间为
  `2026-10-04T04:36:52.6333759Z` 至 `2026-10-04T04:39:10.4700720Z`。
  这不是每条 API 的单独计时；首轮没有采集每条查询的 UTC 起止。
- r3s 当前 jobs 的末次计时查询窗口为
  `2026-10-04T04:39:51.7612453Z` 至 `2026-10-04T04:39:52.9906864Z`；
  runners 为 `2026-10-04T04:39:51.7525165Z` 至 `2026-10-04T04:39:53.1184530Z`。
  两次 API 实际 exit 0。上一 run 的 jobs 在同批只读补读，未采集其独立 UTC 起止。
- 本页仅记录上述窗口，没有为文档再次查询、轮询或重跑。API 原始输出在核查会话中，
  本页是便携摘要，没有另建原始证据文件或哈希封存证明。

## 准确候选与完整检查

| 目标 | 本地及远端 main | 本窗口检查结果 |
| --- | --- | --- |
| ai-agent-dotfiles | `ac8e4854b50592a1216acce7f0d08b718478e25a` | 本地 main 干净；[Validate run 37109686458](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/37109686458) 为 push、attempt 1、completed/success，创建 `2026-10-03T08:26:07Z`，更新 `2026-10-03T09:56:28Z` |
| r3s-VPS | `9e1b538c6acdcb8fde410172ebf1dff4485e6ffb` | 本地 main 干净；[offline-verify run 37177002687](https://github.com/MaginaLW/r3s-VPS/actions/runs/37177002687) 为 push、attempt 1，创建 `2026-10-04T04:26:32Z`；run-level 为 queued/conclusion null，实际 Windows job 已在执行、POSIX 尚未执行 |

dotfiles 的 [workflow](https://github.com/MaginaLW/ai-agent-dotfiles/blob/ac8e4854b50592a1216acce7f0d08b718478e25a/.github/workflows/validate.yml)
定义 repository gates 与三个测试 shard。jobs 与准确 SHA 的 check-runs 共四项，集合和
head_sha 一致，均 completed/success，所有实际 steps 均 success：

| job / check-run | ID | 开始 UTC | 完成 UTC |
| --- | --- | --- | --- |
| Validate repository gates | `111165020618` | `2026-10-03T08:26:09Z` | `2026-10-03T08:29:05Z` |
| Validate test shard 1 of 3 | `111165020681` | `2026-10-03T08:26:09Z` | `2026-10-03T09:39:19Z` |
| Validate test shard 2 of 3 | `111165020543` | `2026-10-03T08:26:10Z` | `2026-10-03T09:37:32Z` |
| Validate test shard 3 of 3 | `111165020633` | `2026-10-03T08:26:09Z` | `2026-10-03T09:56:27Z` |

r3s 的 [workflow](https://github.com/MaginaLW/r3s-VPS/blob/9e1b538c6acdcb8fde410172ebf1dff4485e6ffb/.github/workflows/offline-verify.yml)
定义 `windows-strict` 与 `posix-shells` 两个独立通道；当前准确 SHA 的 jobs/check-runs
集合一致，但未完整通过：

| job / check-run | ID | 末次观察状态 | 实际执行 |
| --- | --- | --- | --- |
| windows-strict | `111361608550` | in_progress、conclusion null；runner 21 | `2026-10-04T04:26:38Z` 开始；steps 1–4 success，step 5 `Run the single offline acceptance gate` in_progress，post-checkout pending；完成时点 UNKNOWN |
| posix-shells | `111361608389` | queued、conclusion null；runner_id 0 | API started_at 为 `2026-10-04T04:26:33Z`，实际 steps 为空；该字段不能解释为门禁已执行 |

因此，dotfiles 当前准确候选的完整 CI 缺项已关闭；r3s 当前候选连 Windows 最终结果也仍未取得。
不能以先前 Windows 成功或本地 Strict 代替当前双通道。

## 上轮终态与 runner 状态

上一 [r3s run 37089685709](https://github.com/MaginaLW/r3s-VPS/actions/runs/37089685709)
绑定 `4159becf9427532c2f3ea0d86d8d2a7431e2d80c`、attempt 1，当前已是
completed/cancelled，updated_at 为 `2026-10-04T02:24:14Z`。
其中 Windows job `111107160099` 于 `2026-10-03T02:24:17Z` 至
`2026-10-03T03:09:43Z` 执行，7 个 steps 全 success；POSIX job `111107159855`
为 runner_id 0、零 steps、cancelled，completed_at `2026-10-04T02:24:14Z`。
目标文档先前的排队/预计终态说法仅属于其历史窗口；本轮核到真实终态，不推断取消机制。

末次 runners GET 核到：

| 已登记实例 | 状态 | busy | 标签 |
| --- | --- | --- | --- |
| Linux runner 22 | offline | false | self-hosted / X64 / Linux / trusted-linux |
| Windows runner 21 | online | true | self-hosted / Windows / X64 / trusted-win |

dotfiles runners GET 为 total_count 0；其本次四个 job 使用 GitHub 托管 runner。
Linux offline 的根因、guest 当前电源与服务状态、连接与注册完整性仍 UNKNOWN，未访问主机。

## GitHub 分支保护核验限制

工作流定义的必需执行检查与 GitHub 对 main 的保护配置分开报告：

- dotfiles `branches/main/protection` GET 实际返回 404、`Branch not protected`；
  repository rulesets GET 为 `[]`。不能将四项 CI success 写成已具备 protected-main
  required-check 配置。
- r3s `branches/main/protection` 与 repository rulesets GET 均实际返回 403，响应要求
  升级 GitHub Pro 或公开仓库后启用该功能。本轮没有变更订阅、仓库可见性或规则，
  无法证明其 GitHub protected-main required-check 配置已启用。
- 上述是本窗口实际 API 响应，不涉及本仓 main 保护要求，也不授权降低任一检查。

## 第 4 项：可选择的实际恢复与 Apply 范围

### r3s 已登记 Linux runner 22

offline 加当前 POSIX 零执行构成真实恢复需求。可以为既有实例准备独立执行单，冻结目标
仓库、准确候选 SHA、现有 runner ID/标签、guest 与服务身份、工具和网络边界；不能把恢复
现有实例解释为自动接入新仓库或平台。

恢复前先取得目标项目准入及具体主机操作授权，再只读诊断 guest/服务/连接/注册的实际原因。
具体方案应复用[自托管 runner 运维入口](self-hosted-runners.md)，满足以下验证与回退条件：

1. 绑定现有注册和低权限身份；启动、服务恢复或配置恢复只作用于批准的实例，不重复注册，
   不覆盖凭据，不扩大 ACL，不让管理员身份接 job。未知或冲突状态保持拒绝。
2. 记录恢复前实例/配置/身份与服务状态，明确本次改动的恢复前像、停止方法和可执行回退。
   回退仅撤销本次恢复变更，保留既有注册和证据；若回退不能完整执行，应在动作前说明缺项。
3. 以真实 runner online、预期身份/工具和当前准确 SHA 的实际 POSIX job/steps 为证据；
   取得同一冻结 SHA 的 Windows Strict 与 POSIX 全部必需检查成功，再独立核 job/step 原件。
   单纯 online、本地 Strict、旧 SHA 双绿或 run-level 排队/取消均不满足。
4. 当前自然 push run 尚在进行，能否由获批恢复承接应按其届时真实状态决定；不得默认取消、
   rerun 或制造新 push。需要任何新执行时，以准确候选和动作范围重新办理。

本轮没有执行上述诊断、恢复、回退演练或新 CI。

### dotfiles setup 与实际部署

[当前入口](https://github.com/MaginaLW/ai-agent-dotfiles/blob/ac8e4854b50592a1216acce7f0d08b718478e25a/STATUS.md#L159-L184)
与[具体活动记录](https://github.com/MaginaLW/ai-agent-dotfiles/blob/ac8e4854b50592a1216acce7f0d08b718478e25a/status/active/live-safety-hardening.md#L6302-L6308)
记录 2026-10-03 真机 setup DryRun PASS、`canonical-plan-created`，PlanHash
`2a2ad62e362195e7a7236950f8c701b54fa3c3990a45cc311b351550a76a01d6`；计划为
15388 字节，SHA256 `0b7b2c234985779e5089b751e36bf678bf4ff7680d28f01e194346a87a0b3a16`。
这些是本轮读取的 tracked 引用；私有计划原件及其当前字节未读取、未重新核定。

当前记录明确没有 Apply、adopt、activate、部署或 runner approval。真实 setup Apply
仍缺计划原件审查、当前 host/identity/source/live 根与受保护目录及 secret-scan 条件核定，
以及具体逐项授权；其后以独立进程消费同一已审计划。adopt 的环境 `<name>` 仍待所有者
选择，不能默认 `work` 或 `full`。记录中的历史发布路径授权不替代这些绑定条件。

两仓 GitHub deployments GET 均为 `[]`，仅说明未登记 GitHub deployment，不能据此
证明所有外部部署都未发生。r3s 当前目标入口有 2026-09-21 网络维护/定期 IPv6 许可任务的
历史执行记录；它不等于当前 package Deploy 获准。其
[机器状态登记](https://github.com/MaginaLW/r3s-VPS/blob/9e1b538c6acdcb8fde410172ebf1dff4485e6ffb/docs/current-state.json)
仍为 recorded-read-only-baseline / recorded-not-live、readiness blocked/provenance-stale；
生产动作须按目标执行单取得新鲜门禁和对应授权。

## 第 5 项：I1 / I2 准入结论

- I1：恢复现有 Linux runner 22 是本轮已发现的具体生命周期需求，可按上述范围准备。
  尚未选定其他安装、更新或恢复范围，不另造 harness-env 工作。
- I2：本轮没有选定新的可信仓库或平台；dotfiles 当前侧未发现新 I2 缺项，既有方法回灌
  no-op 保持。恢复既有 runner、补 r3s 当前双通道属于试点收尾，不构成新增扩仓完成。
- [TASK-0048 历史验收](../superpowers/plans/2026-09-13-runner-infrastructure-execution.md)
  的注册、同仓双通道、采用与恢复成果不重开；历史在线/成功也不证明当前实例或候选状态。
- 真正剩余的是 r3s 恢复执行单与准确 SHA 双通道完整结果、dotfiles 计划审查及具体 Apply/
  环境选择，以及若要扩仓时由所有者指定的真实目标和独立准入。上述项目仍未完成。

## 2026-10-04 13:29–13:36 UTC：I1 受控恢复接单调查

本节为新的只读窗口，保留上方 04:36–04:39 UTC 快照。仅刷新自然 push run、检查原
文档/树外工具与历史授权，并读取已明确绑定的本机进程/服务元数据；没有执行 SSH、
guest 工具、冷启动、服务启停、磁盘内容读取、CI 重跑/取消或任何凭据导出。

### 当前准确候选与自然 CI

| 只读查询 | 实际 UTC 起止 | 结果 |
| --- | --- | --- |
| remote main GET | `13:29:56.6303765Z–13:29:58.0238367Z` | 仍为 `9e1b538c6acdcb8fde410172ebf1dff4485e6ffb` |
| main 自然 runs GET | `13:29:56.8012800Z–13:29:58.2340436Z` | [run 37177002687](https://github.com/MaginaLW/r3s-VPS/actions/runs/37177002687) 仍是 push、attempt 1、run-level queued/conclusion null，没有创建新 run |
| runners GET | `13:29:57.0023355Z–13:29:58.3205058Z` | 22 offline/busy=false；21 online/busy=false |
| run 全 jobs GET | `13:30:31.0910433Z–13:30:32.4113332Z` | Windows 已成功；POSIX 仍 queued、runner_id 0、零 steps |
| accurate SHA 全 check-runs GET | `13:30:31.2763865Z–13:30:32.5756502Z` | 两个 check 与 jobs 集合、head_sha、状态/结论一致 |

表内时间均为 `2026-10-04`，五次 API 实际 exit 0。Windows job/check
[`111361608550`](https://github.com/MaginaLW/r3s-VPS/actions/runs/37177002687/job/111361608550)
从 `04:26:38Z` 至 `05:26:34Z`，completed/success、7 个实际 steps 全 success；
POSIX job/check
[`111361608389`](https://github.com/MaginaLW/r3s-VPS/actions/runs/37177002687/job/111361608389)
仍 queued/conclusion null，steps 为空。run-level queued 不抹去 Windows 成功，也不证明
POSIX 执行。准确 SHA 完整双通道仍缺。

### 找到的原资产与历史默认状态

本轮定位到树外原资产根 basename `task02-linux`。下列相对引用都以该受限私有根为基准；
本页不提交该根的实际位置、服务名、账号、SSH 参数或凭据。仅检查静态文件和元数据，
没有运行这些入口。

| 原资产相对引用 | 本轮实际重算 | 用途与范围 |
| --- | --- | --- |
| `tools/stage60-linux-service-actions/request_template.py` | 8790 bytes；SHA256 `5e61454be0cb7e1c3ee3a1f6e6cc2a50fc60740e8c068348723f400fee6ac863` | 固定 Linux install/start/stop；同目录 README 是绑定/拒绝合同 |
| `tools/stage60-windows-handoff/handoff-diagnostic-002.ps1` | 6420 bytes；SHA256 `844e1d30f7144ca38b1349b42687aba7acedadf4dfb8d4c49e89abe7a2b5f5a2` | Windows 21 的精确 Stop/Restore，核服务身份、无 Worker 与远端串行状态 |
| `tools/stage60-postboot-lifecycle-dispatch/dispatch.py` | 8081 bytes；SHA256 `9cdd2a857c101c333ccc10be60f56fcdf886c4f7d28ab3ff7e500807b136feb3` | 原 action/request/window、QEMU 进程出生身份与 strict transport 绑定；历史 dispatcher |
| `tools/stage60-reboot-prep/final-stop-readback.py` | 13123 bytes；SHA256 `6d3eeaa1e1a8993a860b646d017bac4bc843b588c09cf9c1f9ba998461395c0d` | 精确 Linux 停用后独立只读核验；容器/pod/用户 manager 与服务分别核对 |
| `tools/stage60-reboot-prep/service-recovery-review-001.json` | 2921 bytes；SHA256 `3e1d8a0be99a182697219260274bce63938e5e83a77058a7e2a9b57acc551c53` | 原 stop/start + 新业务 job 审查，绑定 `949fc6036a95e5c1ed55c4d5d5f96793ba42670f`、run `35547201811` attempt 2/job `106358427430`，不是当前候选或 reboot 证明 |
| `evidence/stage60-final-stop-independent-001/review-receipt.json` | 1776 bytes；SHA256 `17d3d77af45b6d88af90241b89f9f204b7b171d08e2d01ab80b178d8a1fdd001` | 旧最终停用回执；与主仓历史引用一致，不证明当前 guest 状态 |
| `evidence/stage60-reboot-relaunch-001/launch.json` | 1813 bytes；SHA256 `698abba5e23ac70df96b804d417b046643abbf95355f22f69e6fd60eec86ff2a` | 旧 QEMU launch/出生身份；同目录保留当次冷态工具、输入、copy/image/check 原件 |

[任务 02 最终运行约定](../implementation/task02-runtime-integration.md#本轮试验复盘与最终运行约定)
明确最终默认 Windows 接单，Linux 注册及 guest 保留、runner 服务 disabled/offline；再次
切换必须重核 busy/Worker 与两端状态。[最终串行交接](../implementation/task02-runtime-integration.md#重启后真实业务验收与最终串行交接)
记录当时 Linux inactive/dead/disabled、MainPID/ControlPID 0、无 Runner/容器/pod 残留，
随后恢复 Windows。故上文将 offline 称为故障需求的表述在本节收窄：**本轮可确认的是
既有实例受控恢复接单需求；当前 offline 不能单独证明新故障，旧主动停用约定与当前
guest 不在线的原因需要分别核定。**

`tools/stage60-authorization/` 中原 Linux start、final-stop 和 Windows restore 都为
single_use，分别到期于 `2026-09-21T13:49:08.165896+00:00`、
`2026-09-21T14:25:16.347408+00:00`、`2026-09-21T14:52:23.2535044+00:00`。
它们绑定原 source/window/request，不可作为本轮有效动作或通过改到期、BOOT、request
hash 复用。首次只读投影曾因 PowerShell 自动日期反序列化导致 Parse 异常，未产生授权
判定；随后仅用 `ConvertFrom-Json -DateKind String` 修正数据读取，核到原 ISO 日期均过期，
没有改原文件。

dotfiles 的 `scripts/runner-policy.psd1`、`scripts/approved-runner-common.ps1` 描述
Git-private preview/event runner 与逐机批准，不是 r3s 的 GitHub runner 22 服务合同，
不能将 dotfiles runner approval 或 setup Apply 批准移交为该实例恢复权限。

### 本窗口实际宿主观察与尚缺事实

- `2026-10-04T13:34:53.0417357Z`：仅按旧 launch 绑定的 PID `32316` 查询，进程不存在，
  因而旧 dispatcher 的进程出生/handle 绑定当前不可成立；不存在旧 PID 不证明退出原因。
- `2026-10-04T13:35:41.4851799Z`：限定 `qemu-system-x86_64.exe` 的本机进程查询为 0。
  这不是冷启动合同要求的全部 `qemu%`/image helper、端口、内存、磁盘空间与两次 absence
  preflight，也不是 guest 内部证明；本轮未调用该 preflight。
- `2026-10-04T13:34:53.7321664Z`：原精确 Windows 21 服务存在，Running/Auto、PID `2152`，
  已配置账号与二进制位置匹配原绑定。未采集其 actual token/SID、完整 Listener/Worker、
  delayed-auto 或故障恢复配置；远端 idle 不能补这些本机事实。
- 当前 guest BOOT、磁盘/镜像元数据与恢复目标完整性、注册包/unit/helper 的实际 guest
  字节、用户 manager/挂载/隔离配置、旧 Listener/Worker 与 delegated containers/pods
  均未现场采集。未读 guest 磁盘内容、seed 内容、credential 文件或 raw runner diagnostics。
- 当前 workflow 要求 root-owned 固定 POSIX contract/adapter/binding、UID/GID 1001、
  原软件包版本/工具摘要及当前准确 checkout。原安装对当前 `9e1b538c…` 的相容性和
  source/contract 绑定未现场核定；不能先上线让 queued job 执行，再补做准入检查。

### 可审查的下一动作清单

材料已足够确定下面的顺序、对象和验收边界；**尚不足以生成可直接执行的新 service
request**。旧 launch 绑定失效，需先准备新的精确 guest 启动及 transport/BOOT 证据，
再生成新的串行服务动作；没有现成有效的本轮授权文件或 observation binding。

| 顺序 | 准备/动作对象 | 必须在动作前核到的事实与动作后验证 | 失败、停止或回退 |
| --- | --- | --- | --- |
| 1. 冻结受控窗口 | 原 guest + runner 22 + Windows 21；当前候选 `9e1b538c…` 和自然 run `37177002687` | 新的动作范围与到期/window；重新核 private/repository ID、owner-only/fork/PR 和两端实时 busy/Worker；选择允许暂时暂停 Windows 接单的窗口 | 有业务/Worker、身份未知或其他写者时不启停；不重注册、不改路由/ACL/网络/包/凭据 |
| 2. 新 guest 身份建立 | 原 task-owned guest 与原 immutable inputs；原 cold preservation 工具仅作审查起点 | 补当前完整 host absence、端口/资源/路径身份/输入摘要；若批准冷启动，则独占冷态保全、原 backing-chain 与只读 image check、一次隐藏启动；新 PID/creation/executable/端口 owner、严格既有 host-key transport 和新 BOOT | 不读运行磁盘，不 repair/rebase/convert，不自动 launch/retry/rollback。退出/启动/SSH/BOOT 分别留证；任何未知保留并停在下一动作前 |
| 3. 注册和 CI preflight | 原 registration 22、固定 unit/helper/runner package、root-owned POSIX contract/adapter | 只读核同实例与包字节、无 sudo/额外组、所需挂载/user manager、rootless 隔离、当前 SHA contract/源码与全部工具；只 stat credential 元数据并读取许可的 `.runner` 字段 | 自动更新或 source/contract 漂移不得靠重装/改批准字节消除；另行确定最小修复范围。此步期间 Linux 保持不接单 |
| 4. Windows 定向交接 | 原精确 Windows 21 服务；独立新 Stop action | 空闲且无本机 Worker，原服务/账号/SID/二进制/父子/启动与故障恢复配置匹配；定向 disable/stop 后核 stopped/disabled、无 Service/Listener/Worker、remote offline | 仅作用原实例；保留前像与回执。状态或 native 返回未知先 reconcile，不开始 Linux，不重试，Restore 是独立动作 |
| 5. Linux 定向启动 | 原固定 Linux unit；新的 `task_owned_linux_runner_service` start | fresh Windows stopped/disabled/offline + BOOT/observed_at/expires_at≤300秒；新 request/action hash；原 helper/unit 摘要、同 package/registration、无 Worker/quiet window、同 user manager。原语义先 enable 再 `systemctl --job-mode=fail start <PINNED_UNIT>`；核 MainPID/唯一 Listener UID/cgroup 与远端 ID22 online | 本地 LOCAL_ACTION_VERIFIED 不等于业务验收。queued job 可能立即生成 Worker，须精确核其身份/cgroup；不因此停止 active job。SSH/transport 超时为 UNKNOWN，保留后核，不自动重试 |
| 6. 自然 job 完整验收 | 同 SHA/run/attempt 的 POSIX job `111361608389` | 若原排队仍有效且接取，核真实 runner 22、checkout、全部原 steps/markers/native 退出、完整原件及 root fixture 回收；与现有该 SHA Windows success 成对核定 | 不预授权 rerun/cancel/new push；自然 job 已终态或出现新 scope 时先冻结新具体动作。缺行/SKIP/timeout/清理未知均非成功 |
| 7. 恢复原默认运行方式 | 独立新 Linux stop/disable，再独立新 Windows Restore | Linux remote idle且无 Worker；原 stop native≤315秒、外层≤420秒，核 inactive/disabled、MainPID/ControlPID/Job 0、cgroup 空、无 Listener/Worker；另核 containers/pods/manager。确认22 offline后恢复21，核原 delayed-auto/恢复配置与实际身份/online | 先完成精确 Linux 回收再恢复 Windows接单；不将 cgroup空代替 delegated容器证明。残留/UNKNOWN 时保留证据和窗口，禁止两端同时接单；不注销或删除资产 |

原服务合同的 stop/start 是分别绑定的动作，不提供通用 restart；业务 rerun、guest reboot、
包更新、workflow/source 适配及注销都是单独范围。原 Linux start 的 enable 行为也须在新
提案中明确披露，并由最后的 disable/stop 恢复原默认策略，不能隐含永久改变开机接单。

本节使后续 I1 决定具体到**原 guest 身份建立 → 串行恢复接单 → 准确自然 job → 原默认
策略恢复**；旧禁用状态不抹去，失败原因仍 UNKNOWN，I1 及双通道收尾仍未完成。
本节没有新增 I2 仓库/平台、V3 故障注入或生产/付费执行范围。

## 追加窗口：I1 原 guest 隔离冷启动请求准备

本节保留前两窗口及全部原资产，只追加 `2026-10-04T13:46:23.8688501Z`
创建独占准备 leaf 后的事实。产出位于受限 runtime 的
`<RUNTIME>/i1-cold-start-preparation-001/`，不入库；真实位置、账号、服务名、
VM 名称、key 路径和完整 native argv 仅在该私有包中。已按 scope 检查现有
AGENTS；该原资产及新 runtime 的相关祖先未找到额外 AGENTS，遵循主仓规则。

**具体下一动作草案已形成，但未授权、未执行：对原 VM 做独占冷态保全，执行
一次隐藏且阻断出网的冷启动，核新 PID/出生身份和回环端口 owner，再以一次严格
只读 SSH 探测记录 BOOT。** runner 21/22 服务配置不动，Linux 保持不接取新任务。
这不是原出网 launch 的直接重用，也不是 service 恢复、自然 POSIX job 或 I1 完成。

### 本轮唯一实际 native 检查

只运行已审查为纯读的原
`tools/stage57-cold-start/host_preflight.ps1`，其实际 SHA256 为
`a59ea58a67518c3b18192b04dd3d2bc3ea4f4b2b0a684f431254e5eb88bf7854`。
native 窗口 `13:50:43.4411423Z–13:50:45.0286618Z`、exit 0，观察时刻
`13:50:44.9337324Z`；stdout 374 bytes、SHA256
`17f48209795e68d2348918e8a74dd5ccab453aeae53ff9fbb7e84c1c210d3670`，
stderr 0 bytes。该源只用 CIM/端口/资源/文件元数据查询，不复制或打开 VM 字节、
不启动 QEMU/SSH/guest 工具、不改服务。

| 完整 host 条件 | 本次纯读观察 | 原合同要求与限度 |
| --- | --- | --- |
| 全部 `qemu%` 进程（包含 image helper） | 空集合 | 本窗口 absent；不能替代动作前的两次 fresh absence |
| TCP 监听端口 `22240` | 空集合 | 查询全部 Listen 后筛端口；不是 guest 或 SSH 证明 |
| 空闲物理内存 | `12924228 KiB` | 严格大于 `5242880 KiB`，本窗口通过；当前 WHPX 尚未核定 |
| 可用磁盘 | `1077298880512 bytes` | 至少当前源盘 `5338103808 + 536870912 = 5874974720 bytes`，本窗口通过 |
| 原可变 VM 文件元数据 | `5338103808 bytes`；最后写入 `2026-09-23T12:57:31.828042Z` | 未读 VM 字节；该时间晚于旧最终 disabled 回执，不能推定当前持久 service 状态 |

`13:50:43.4411423Z–13:50:46.5032616Z` 重算六项 immutable 输入摘要，与原绑定
一致；hash 前后的元数据快照稳定，并在 hash 前核祖先无 reparse。这仍不是
exclusive handle、持久文件身份或启动间隙原子转移的证明。

| 输入角色 | 实际 bytes | SHA256 |
| --- | --- | --- |
| 固定 QEMU executable | `25457048` | `47d57a6072e0bb3bd98f87926eb129eb1736dfe818c67b3b81ef7ce4edd0b3cd` |
| kernel | `15059336` | `0066409132868538bc0c9076f60131025775d5bbd8617df074d059f91b584918` |
| initrd | `30694978` | `e7732308dee547d2455f6203b664d4ff47da050227fd6f2ad6a331dbff4ec0d2` |
| 只读 seed | `67584` | `f7e55cd38957125c061bad875aafba22128002a5a4d4bb433c76d915fc4410e4` |
| 固定 qemu-img executable | `1934744` | `9d930582d0d574bb106d89982c547688e10b8f356192d302cc3d0ae4e8674534` |
| 原 immutable backing image | `625256960` | `612b2c0cc1bc413a6cb8c38fd611794caf0f2b436c50013d8b3794db12ad7354` |

原 immutable 绑定引用 `evidence/stage48-next-guest-entry-001/input-bindings.json`
3487 bytes、SHA256
`799085abb93d7ee75978a7de16b54ac37219e04e3cc525021481a25f6c146908`。
所有引用以受限原资产根为基准，未改原件、原 seed、key、VM 或旧 backup。

### 原出网参数与本轮隔离提案

原最新 `evidence/stage60-reboot-relaunch-001/launch-request.json` 的 SHA256 为
`6731b2cadac8a15f635f3c4a32319a8948fa4a9e5bd38213b7e8009c308b3e5b`。
其中 `-netdev user,id=net0,hostfwd=tcp:127.0.0.1:22240-:22` 允许出网，且原
recovery scope 明确 enabled runner 可能自动重连。当前 guest 持久 service 状态
未知，不能直接启动原 argv 后再证明 Linux 未接单。

私有新草案将唯一网络参数改为
`user,id=net0,restrict=on,hostfwd=tcp:127.0.0.1:22240-:22`。
固定 QEMU 随附官方手册 `tools/qemu-11.1.0/share/doc/system/invocation.html`
第 2308–2311 行说明 `restrict=on` 阻断 guest 向宿主及外部的 IP 路由，保留显式
forward；本轮手册 actual SHA256
`ae36275c0ba301d6beed39f64c72bb8ad86c44a46ea185b0905bad90c19b2d29`。
没有新增 guestfwd、共享目录、额外 NIC/端口或 host 网络变更。
**这是未执行的新参数提案，不是现场隔离验证或当前 guest 事实。**
不得换回原 unrestricted 参数作为 fallback。

其余原 launch 参数保留：2 vCPU、4096 MiB、WHPX/host CPU、q35、无 display/monitor、
原 kernel/initrd、同 VM qcow2、readonly seed 和同一个回环 SSH forward；最新原
relaunch 未含 `-no-reboot`，本草案不隐含补入。只有 serial/pidfile/log 目的地另指向
本 leaf 的新独占 `execution-001`。BOOT 与 guest service/Worker/contract 核验尚缺，
隔离启动不释放 Linux 接单资格。

### 私有可审查产物与具体动作边界

`14:02:28.0173471Z` 生成请求包，准备 builder 没有启动任何 native 命令。状态固定为
`PREPARED_NOT_AUTHORIZED_NOT_EXECUTED`，批准、action ID 和绝对窗口开始/到期字段
均为 null；旧 action 原件及 expired 事实全部保留。

| 私有 leaf 内产物 | 本次 SHA256 | 内容与执行状态 |
| --- | --- | --- |
| `cold-start-request.draft.json` | `c11f53331f91af342b14e5cbae2a0e748b36c7e205dface8dcce57d663da9e3d` | 原目标/输入、完整 future native argv、closed environment、资源、fresh gates 与停止条件；不是有效 action |
| `cold-copy.proposed.ps1` | `b3a2eb782ee23e4dc590fd113ada95cb3de9c5a50dbfd875ef3a3a6d64c56896` | 未执行候选；只改原 copy 源的 destination/receipt 两条赋值并加准备说明 |
| `guest-boot-readonly.proposed.py` | `843250089b4daef628fc8d9493b4415664a88ca7ee77a000c4d8fa4595a062d9` | 未执行且 nonce/hash 绑定的 stdin，只读 `/proc` BOOT 并输出 UTC/UID/kernel；无 service 动作/文件写入/凭据读取 |
| `REQUEST.md`、`request-preparation-receipt.json`、`packet-manifest.json` | 摘要和全文件摘要保留在私有 manifest | 便于审批核对；不提供批准或执行证明 |

未来写入仅限本 leaf 下当前尚不存在的 `recovery-001` 与 `execution-001`；本轮没有
创建它们。冷备源为原 VM，只读独占 `FileAccess.Read / FileShare.None`；目标
`CreateNew / ReadWrite / None`，完整 source handle 身份/单 link/FILETIME、stream
hash、Flush 和 target 全量 readback、base 独占 hash、逐对象 disposal 与 secondary
失败均保留。原 copy 源 SHA256
`ca8d8ab2e873f50a48164acfdbb1e49c578d74239ef4b987c0fe15658f923ca1`
未改、未运行。部分 copy/失败也须保留，不自动删除、restore、repair、rebase、convert
或 retry；冷备是恢复资产，不是恢复批准。

提议新 single-use 窗口最多 1800 秒，绝对起止由新决定绑定；执行层的有效 action
检查尚未创建，不能运行旧 `cold_start`/`wait_and_relaunch` 或将草案当授权。
复制前和 launch 前分别要求不超过 300 秒的完整 host 条件、输入 hashes、路径/祖先
身份、无其他 writer；冷拷贝最多 600 秒，native `qemu-img info --backing-chain
--output=json` 最多 60 秒、`check --output=json` 最多 180 秒，不带 repair。
必须原两个 qcow2、原 backing 路径、VM/backing 虚拟尺寸
`68719476736 / 3758096384 bytes`、native exit 0 且 check-errors/corruptions/leaks
全零，源 metadata 不变。本轮未执行任何 copy/image check，也未证明当前 WHPX。

一次 launch 使用 `CREATE_NO_WINDOW`、原 closed environment、DEVNULL/close_fds 和
独占 stdout/stderr；必须保存新原始 process handle 的 PID、creation FILETIME、
executable/hash/argv/environment、launch UTC，并在 3 秒后核同 handle 身份及仍存活。
pidfile 只作旁证。严格核 `127.0.0.1:22240` listener owner 是该出生身份 PID，无
wildcard/额外转发；随后只允许一次原 strict SSH（固定 known_hosts、BatchMode、
IdentitiesOnly、StrictHostKeyChecking=yes、不用全局 trust），90 秒 outer budget，
以 hash 绑定 stdin 的 nonce、canonical BOOT UUID、launch 后 UTC 和 native exit 0
绑定新 PID/端口/transport。当前 BOOT/transport 仍 UNKNOWN，不换 key/账号或重试。
未来 native SSH 仅消费既有私钥，不导出正文；本轮未读取 key 正文或运行 SSH。

资源影响为至少 4 GiB guest、2 vCPU、未知 host overhead；冷备初始 5338103808 bytes，
guest 启动会写原 qcow2，虚拟上限 64 GiB，日志增长没有静态上限。成功或后续验证
UNKNOWN 时 VM 可能继续占用资源并保留隔离；窗口到期不授权自动 poweroff/terminate
或 restore，停止 VM 是后续独立精确动作。禁止 service start/enable/stop/disable、
Windows 21 handoff/restore、Linux 接单、CI rerun/cancel/push/merge、部署或付费调用。

host/输入漂移、copy/image/secondary 失败、窗口过期、隔离 argv 未核、出生/port owner
或 strict BOOT 未知均在下一动作前停止并保留回执；若 runner 22 异常上线或出现实际
接单，也停止推进、不自动改服务补救。guest 的持久服务、Worker、注册包/helper、
合同、挂载、user manager 与 delegated containers/pods 仍需后续现场只读准入；
不能用本包或历史 disabled 记录替代。**当前交付是一个具体隔离 cold-start 请求草案，
不是 guest 已恢复、service 已恢复或准确 SHA 双通道已完成。**

`14:06:21.9077612Z` 静态核对通过：私有包摘要、cold-copy 仅目标赋值改写、
PowerShell 源 parse、单次/无批准/隔离 argv、未来 recovery/execution 目的地仍不存在、
tracked 文档私有路径/账号检查，以及 `git diff --check` 与未跟踪文件的 no-index
whitespace 检查（exit 1 仅代表文件差异，diagnostics 空）。首次隐私正则将 HTTPS
尾部误识别为盘符；加前缀字母边界后核对通过，未发现真实路径/账号泄漏，
未因此执行任何 cold/guest 操作。私有 `verification-receipt.json` 和最终准备 manifest
保留这次检查及全部准备文件摘要，主 agent 统一复核和提交，本 agent 未 commit。
