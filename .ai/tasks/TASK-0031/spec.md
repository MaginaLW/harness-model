# Task Specification

## 目标

在 `docs/operations/github-branch-protection.md` 中补充已经发生的首个 post-bootstrap
formal AI Flow pull request（PR #2）canary 记录和证据保留/验收口径；保持 workflow、
Policy、代码、历史任务和 GitHub 历史对象不变。

## 范围

1. 唯一业务文件为 `docs/operations/github-branch-protection.md`；TASK-0031 自身治理目录
   由 AI Flow 管理。
2. 记录 PR #2 的 durable platform facts：base `37dce2a61a5dc484b077ba4463cede2be04dd746`、
   final head `9b3a58d63070eb8d221c7061fd383cb2ce7bcd3d`、merge commit
   `0989da65702a756c229b0dc7a1c14d56639ad384`、required check 和成功 run
   `33450685267` / job `99679646219`。
3. 记录 formal path 的关键结果：`Resolve task`、`Verify and Gate`、
   `Upload AI Flow diagnostics` 成功，`Bootstrap quality checks` 按预期跳过。
4. 记录 diagnostics artifact `ai-flow-TASK-0030`、artifact ID `9779802345`、
   SHA-256 `9b8cfb915a79e6f3a5097739950dac42626ec50e7f6192e7b158b356dc04fe72`、
   14 天保留及 `2026-09-14T23:33:23Z` 到期事实，并明确 artifact 是临时调查证据，
   PR、merge commit 与 required check 才是 durable platform record。
5. 明确 PR #2 body 保留的是早期 subject，不能作为 final-head binding；最终 head 以
   GitHub PR/Actions event metadata 为权威。本任务不追溯编辑 PR body。
6. 保留 TASK-0029 在旧分支上的 BLOCKED 历史、两次 600 秒 coverage timeout 与
   579.8 秒隔离诊断；TASK-0030 的 Policy 2.2.0 remediation 和 PR #2 成功只解除运行时
   阻断，不改写 TASK-0029 或 TASK-0030 历史。

## 非目标

1. 不修改 `.github/workflows/**`、`.ai/policy/**`、源代码、测试、README、CHANGELOG、
   TASK-0029 或 TASK-0030 目录。
2. 不把 TASK-0031 自身 PR 表述为首个 formal canary，也不以它替代 PR #2 的历史事实。
3. 不启动阶段三、V3、模型路由、资源调度、通用命令拦截或 OS sandbox。
4. 不创建版本、tag、Release，不发布 package，不改变分支保护。

## 验收条件

1. 文档包含上述 PR、commit、run、job、步骤和 artifact 精确身份，链接指向相应 GitHub
   对象，且区分 durable 与 14-day evidence。
2. 文档明确 stale PR-body subject 的限制、权威 final-head 来源和禁止在同一受治理 PR
   中回写 run URL 造成自失效的规则。
3. 文档明确 TASK-0029 失败历史与 TASK-0030 remediation/PR #2 成功之间的时序关系，
   不把失败覆盖成成功或复用旧 evidence。
4. `python -m aiflow validate TASK-0031`、`python -m aiflow scope TASK-0031`、active
   Policy V1、read-only Gate 与 `git diff --check` 全部通过。
5. 最终业务 diff 仅包含 `docs/operations/github-branch-protection.md`；其余变化只允许
   TASK-0031 治理记录。

## 禁止动作

禁止未经单独批准的 push、merge、deploy、delete、secret export、paid external call、
package publish、tag/Release 创建、PR/Issue 评论或历史对象编辑。

## 错误行为

任何无法由当前 GitHub metadata 重放的 SHA、run、job、artifact 或 step 结论必须停止并
更正；不得猜测缺失事实、把 artifact 保留期写成 durable、把旧 PR body 当作最终绑定、
修改历史 task/evidence，或通过降低验证等级与门槛放行。

## 回滚

文档内容可由后续受治理提交反向修改；TASK-0031 的事件、分类、规格和验证记录保持追加式
审计，不删除、不重写。历史 PR、Actions run、TASK-0029 和 TASK-0030 均不受回滚影响。
