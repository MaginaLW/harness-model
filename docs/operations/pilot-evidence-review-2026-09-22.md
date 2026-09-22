# 登记试点证据复核：2026-09-22

## 2026-09-22 后续修订已应用

所有者明确要求继续修正，并确认 dotfiles 没有其他写入任务后，已在该项目按其规则完成
两份文档的最小修订：`docs/CI_FAILURE_RULES.md` 更正归因及拆分对应索引，
`status/active/live-safety-hardening.md` 尾部追加事实更正，原历史正文保留。
目标基线为 `8f84eececf71f111a28c953f07ac2b1d490ac3fe`，实际本地修复提交为
`51044a55fc0dd8991e2ac25dad36fb1369a9027b`。本轮未推送、未触发外仓 CI。

本次直接读取保留的 run/job JSON 及 job `103999311576` 的原始日志，确认 run
`34851206631` 为 39 套件、36 passed、1 failed、2 timed-out：task-skills 22/0，
automation-safety 通过，hard-kill 加载摘要不匹配，另外两项为 300/180 秒超时。
原日志 SHA256 为 `4acee9b4179291c5f83943f214ad39a2cb8d92489fab23dfb3d7be2da026fe0c`。
Git 字节核对同时纠正了旧更正记录的一处细节：`45e9a50` 继承父提交 `8e27e4a`
的脚本和旧 pin，本身未修改该脚本；`b86b8b1` 更新 pin，`06d1902` 的本地 318/0
记录仍不等于原 CI 重跑成功。三个历史原件摘要未变。

目标文档检查通过：secret scan 零阻断、PowerShell syntax 179 文件、whitespace 和
新增链接/锚点检查；独立 sub-agent 按原始证据及 Git blob 复核通过。没有为纯文档修订
重跑完整回归，也不据此宣称 CI 或生产验收通过。历史原件保留在目标仓未跟踪的 `tmp/`；
本轮选材副本及运行回执保存在树外，均未纳入 tracked 交付。
两名同产品 sub-agent 分别核对原始证据与验收边界；随后通过所有者提供的 ZCode Web
Remote Control 在目标项目新建独立会话，对固定修复提交的 F1（套件失败归因）和
F2（历史提交归因）逐项复核。实际界面已读回两项“验证成立”和“已完成审查，未发现问题”，
并显示读取原始 run/job/log、历史 Git 对象及三项 002 检查回执的工具记录。
复核后目标 HEAD 未变、工作树干净，两份文档与受检输入和提交 blob 原始字节一致。

本次“Codex 发现与修复 → ZCode 独立复核”的文档维护案例满足 E3 最小 guided
双产品交接验收。树外证据集 `DOTFILES-CI-ATTRIBUTION-20260922` 保存可回查的独立
会话引用、界面观察及选定报告正文；报告 `zcode-review-result-001.md` 的 SHA256 为
`80e9ebd7de1891a214075741a88abd134518195ceee6edcfd927855ac6e77ecd`。
报告是从界面复制后转录的技术正文，非完整会话导出；实际运行模型与费用均为 `unknown`，
不以界面模型切换提示、当前选择器或报告自述认证模型。访问链接鉴权参数未保存。
本仓收尾提交不属于 ZCode 对目标修复的技术复核范围。

该结论仅覆盖本案例，不代表全部 E1、历史 CI 重跑、AI Flow Gate、生产验收或自动化能力。
尚未观察到足以选定 E4 内核桥接范围的具体缺口；r3s 的并行工作与 I1 其他生命周期未接管。

下文保留首次只读诊断窗口；“尚未修改”“未完成回灌”和错误提交归因均按本节更新，
不将已应用修订再次列为待办，也不把本次新读回倒记为首次诊断已有的原始证据。

## 首次只读诊断窗口

本次响应所有者持续处理待办的请求，按[按需反馈约定](feedback-loop.md)只读复核两个
已登记试点，接续[2026-09-20 固定窗口复盘](zcode-retrospective-2026-09-20.md)。
结论是：部分旧状态已更新，一项已知规则正文冲突仍在；当前已读材料不足以核定 E3。
这是供目标原任务接手者采用的诊断，未修改、测试或发布外仓，未完成回灌。

## 固定对象和证据边界

| 目标 | 本次本地 HEAD | 工作区边界 |
| --- | --- | --- |
| `ai-agent-dotfiles` | `8f84eececf71f111a28c953f07ac2b1d490ac3fe` | 工作树干净；本地 main 相对缓存的 origin/main 领先 5 |
| `r3s-VPS` | `29f3a0684b94396e5b453f352213a276cdee1c99` | `docs/PROJECT_STATUS.md`、`tools/artifacts.manifest.json` 有既有未提交改动；本地 main 相对缓存的 origin/main 领先 1、落后 1 |

HEAD、工作区状态和以下文件文字已直接读取；远端跟踪引用不是实时 GitHub 核验。
本文件以本地固定材料为诊断依据，不把缓存引用或目标记载算作实时远端 CI 验收。
本轮未读取生产状态、调用 provider、重跑外仓检查或接管写入权。
目标记载的运行结果均标为“仅目标项目记载”，不等于本轮独立验证原始日志。
下文路径采用“逻辑仓库 + 相对路径 + 行号”；r3s 的未提交文字单独标明，不能归入其 HEAD。

## 旧复盘中已经更新的事实

- **dotfiles 发布状态入口已纠正。** `STATUS.md:11–37`、`AGENTS.md:101–102` 和
  `docs/ZCODE.md:32–35` 已明确 checked-in policy 为 released，但不表示 lab 验收或
  live 部署获准；`STATUS.md:13–16` 仍记载 Task 8 Steps 2–5 未完成。旧复盘中“首页仍称
  interlocked”的说法不能再作为当前入口结论。`STATUS.md:50–53` 明示后续正文是历史日志。
- **dotfiles 推送关系及 CI 记录已补充。**
  `status/active/live-safety-hardening.md:3459–3472` 追加所有者推送决定，说明原
  local-only 文字先于该推送，并记载 #128 成功、#129–#131 分片作业失败、#132 部分成功。
  `STATUS.md:27–32` 与 `status/archived/2026-09-21-ci-released-pin-repair.md:13–17,92–101`
  记载随后本地修复及局部验证，最终修复仍待首次 CI。这些是目标记载，本轮没有重新确认
  远端最新 run，不以旧 `tmp/ci-128.json` 缓存判断现在的 CI。
- **r3s 第 35 轮结果已有待提交登记。** 工作树 `docs/PROJECT_STATUS.md:220–226`
  记载 run `35480113163` 的 Windows 7 steps 成功、POSIX 零 step 被拒，以及 c29
  Strict 17/17 合并覆盖两批。它们更新了旧复盘“只登记触发”的观察，仍只是未提交的
  项目记载；本轮未回读树外原件，也不能将这些结果归给当前 HEAD 或算作独立的两次验证。
- **r3s 指定范围的旧终审缺项没有在已读入口中补齐。** HEAD 版本
  `docs/PROJECT_STATUS.md:592`（当前工作树第 607 行）仍记载三次独立终审未取得。
  其他批次或其他范围的成功不能替代该次终审；这不证明其他位置不存在后续材料。

## dotfiles 尚存的具体正文冲突

同一固定 HEAD 中，`docs/CI_FAILURE_RULES.md:317–319` 仍将 run `34851206631` 的
`Task skill dry-run failed` 外层提示列为未定位失败，并称另有 automation-safety 超时；
第 339 行索引仍称该 run 有 task-skills 激活失败。

但 `status/active/live-safety-hardening.md:3218–3227` 已明确更正：该 run 的唯一失败套件是
`canonical-hard-kill`，在加载时因 `canonical-transaction-common.ps1` 的 reviewed-load
hash 不匹配失败；`45e9a50` 修改被钉文件，`b86b8b1` 重新封存，`06d1902` 记载修复后
318/0。task-skills 的提示来自预期负例，该套件为 22/0；实际超时是 harness-authority
300 秒和 harness-env 180 秒，automation-safety 在该 run 通过。

本次确认的是两个执行入口的文字矛盾；上述细节仍来自目标更正记录，未在本轮重放原始 run。
这与旧复盘的已知问题相同，不另造一次新业务缺陷或宣称已修复。

供下一次有明确写入权的目标任务采用的最小修订：

1. 核对目标当时 HEAD、原始 run 记录及上述更正段，将 `CI_FAILURE_RULES.md:317–319`
   改为“已更正归因”，写明负例提示与套件结论的区别，并链接该更正记录；删除其针对
   该 run 的错误 automation-safety 超时归因，不重新推断其他 run。
2. 第 339 行将 `34851206631` 单独列出或加明确限定，指向 hard-kill load-hash 更正及
   实际修复提交；同一行其他 run 保留原有证据边界，不借此一并标为已解决。
3. 按目标当前文档检查要求复核改动和链接，保留原始日志及历史更正。仅在实际修改、
   验证并形成目标提交后记录“已应用”；本诊断及建议本身不是回灌、终审或 CI 通过。

## E3 仍需的材料

[既定 E2 交接设计](../superpowers/specs/2026-09-13-cross-agent-review-fix-loop.md)要求
两种实际产品及可核实会话来源。dotfiles `docs/ZCODE.md:500–508` 记载 Grok worker
独立审查，新修复档记载版本和验证；这些不能仅凭模型名或 worktree 数量证明双产品。
r3s 的历史终审记录也没有提供所缺的独立验证。

在下一项自然发生的案例中，继续使用原任务材料，关联以下已有要求即可：

- 两种实际产品、独立 Reviewer/Fixer/复核会话的可核实来源；模型身份不明仍为 unknown。
- 固定受审输入及具体 Finding，修复前后提交，以及逐项问题处置。
- 与修复版本匹配的验证原件和独立复核结论，保留失败、未执行及未解决项。

本轮不制造案例、调用第二产品或用同产品 sub-agent 补足条件；证据不足不是案例失败。
E4 仍应等自然 E3 证明真实接口缺口后再决定，不因本诊断新增审批、统计或定时任务。
