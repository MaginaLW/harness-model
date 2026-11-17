# E4 启动前修复与准备收尾：2026-09-23

## 固定修复候选

本轮按所有者授权，在 `ai-agent-dotfiles` 的隔离分支
`codex/ci-regressions-e4-preflight` 完成并推送三个递进修补。最终源码为
`3b835f143616c91fff3249ba7881996ea4876cf7`，共同基线为
`627ef3f623dff4ba3005eb92ad7427d08da61cd4`。推送是普通快进；没有合并 main。
该分支只修改三份测试及四份指导/状态文档，不修改生产脚本、Schema、工具锁或 CI 配置。

固定 [CI run 35873759132](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/35873759132)
为 push 触发、attempt 1，于 2026-09-23T15:40:44Z 完成最后一个 job。
repository gates 及三个分片全部 success；套件总计 **42 / 42 / 0 / 0**，
三个分片分别为 7/7、8/8、27/27。最终回执核对了同一 head、run/attempt、四个
job/check、GitHub Actions app 及原始日志摘要。该结果不覆盖原仓其他分支的并行生产修补。

## 修复及其验证含义

- sync：released public DryRun 在身份前提完整时应正常产生计划、返回 0。
  复制夹具只适配身份和默认路径定位；检查计划字段/摘要及无越界写入，保留缺失前提
  和 interlocked 策略的拒绝断言。旧的无条件非零断言已用真实 RED/GREEN 复现并纠正。
- root-claims：让计划、锁持有者及 public recovery 子进程使用同一隔离身份；
  工具缓存留在 sealed private root 之外，仍走原有锁、租约和校验。
  复制 toolchain 补齐冻结摘要实际读取的 `.gitleaks.toml` 和 `bootstrap.ps1`，
  并在构造 canonical setup 计划前实际计算 policy hash。
- released 完整 Apply：将该单个调用的测试期限从 15 秒改为 60 秒；默认 helper、
  DryRun、busy、interlocked 的 15 秒期限及套件/CI 预算保留。该调用先前继承的是
  快速拒绝用例期限，完整恢复还包含多次真实 Schema 校验和外部进程启动。
  成功日志现在记录 elapsed；超时仍保留进程回收及捕获到的两流诊断。

当前固定 CI 的 root-claims 完整套件已通过，released Apply 返回 0、写入完成的
abandon 结果；记录 **15,912 ms**。该字段从 Process.Start 前计时到 stdout/stderr
回收之后，证明本轮完整 helper 的成功耗时，不单独证明 WaitForExit 超过 15 秒，
也不定位旧 CI 的内部慢点。sync 完整套件及仓库门禁亦已通过。

离线 Windows Sandbox 使用禁网、一次性身份和复制输入，完整运行提取出的九项
恢复断言。旧源码两次在原期限下完成，新源码也通过；这些是定向夹具结果。
对应 head 的完整自然 CI 现已通过。沙盒已停止，宿主权限未修改。
两名 sub-agent 分别审查源码/契约边界和固定运行证据；这不替代真实 ZCode 会话或正式 Review。

## 失败历史和证据保管

按 `discovered / passed / failed / timed_out` 分别计数；失败运行均自然结束，未取消或重跑。

| 固定源码 | CI run | 已完成结果 |
| --- | --- | --- |
| `51044a55` | [35733693990](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/35733693990) | 42 / 40 / 2 / 0；原 root-claims 内部期限及 sync 断言失败 |
| `e4e1dac7` | [35856160012](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/35856160012) | 42 / 40 / 1 / 1；复制 toolchain 缺文件，另有 harness-env 套件超时 |
| `a326ddac` | [35863733603](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/35863733603) | 42 / 41 / 1 / 0；补齐文件后 released Apply 达到 15 秒期限 |
| `3b835f14` | [35873759132](https://github.com/MaginaLW/ai-agent-dotfiles/actions/runs/35873759132) | 42 / 42 / 0 / 0；完整检查通过 |

`harness-env` 的 600 秒超时仍没有确定根因；相同相关源码在前后其他运行通过。
本轮未修改该套件、runner 或预算，也不将当前通过称为修复了该历史超时。
旧 runner 在超时异常时未返回内部阶段两流，诊断缺口保留，不能补造慢点归因。

私有证据集合 `E4-CI-REPAIR-20260923` 的 README 维护导航，`ci-audit-001` 至
`ci-audit-003` 保留逐次 run/job/check 快照、原始作业日志及 SHA256。
失败子进程两流只按 helper 实际捕获的文本记录；没有另存原件时不声称存在独立两流文件。
`recovery-deadline-receipt-001.json` 汇总时限来源、精确源码、离线复现及独立审查。
最终 `ci-audit-003/final-receipt-001.json` 的 SHA256 为
`c5d967bbe2f8987d6d89245e0ae5ddfdb512483e60f4480a2224c855883eff63`。
运行材料在仓库外保管；原始失败、旧批准、任务账本及三个用户草稿保留。

## E4 启动点

所有者已选定“将 ZCode 审查报告校验并导入既有 AI Flow 任务”。
[启动前规格](../superpowers/specs/2026-09-23-zcode-report-import-preflight.md)
已给出最小范围、字段语义、正负验收和任务拆分：E4.1 先做独立契约及兼容检查，
E4.2 才做预检和不可变附属记录导入；旧 Review、approval、evidence 和 Gate 语义保留。

开始 E4.1 时仍需串行执行：固定当时基线，创建独立治理 task，运行 CLI 分类和
规格冻结，完成设计审查，再按真实 `status` 的 Missing 项及准入结果推进 begin。
这属于下一阶段执行，本轮没有创建 E4 task、begin 或修改内核/Schema/Policy。
实现获准后，主 agent 负责治理两文件，计划一名 sub-agent 独占安全测试五文件，
最后串行集成、完整验证和审查；完整必需检查与覆盖率阈值不变。

匹配目标任务的真实 ZCode 报告是后继 E4.2 的接受材料，**不是 E4.1 启动的缺项**。
已有 dotfiles/51044a55 原报告可作为错目标负例，不能改写成 harness 任务的真实正例。
原仓独立生产修补或历史 lab 接受问题不作为导入契约的依赖，也不由本次 CI 改判。
主仓这些准备与关闭文档仅本地提交；dotfiles 修复分支保持对应已推送源码。
