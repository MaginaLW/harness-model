# TASK-0049：本地实现与验证完成

2026-09-22，`begin` 的 spec approval 新鲜度一致性修复已实现并完成正式 V1。
独立实现审查 `REV-0002 r0001` 为 APPROVE、零 Findings。当前仅等待所有者代码
批准；未推送、未合并、未关闭任务。本记录更新待办清单中该缺陷的实施状态，
不将历史清单快照重写为已发布，也不启动其中的条件性扩展。

## 固定版本与语义

- 原 base：`10b13d17001b3decce17080bc3773fcfe8f5a8fc`。
- 独立 task-free 测试提交：`25f48e4eb1c7126eae13eff6a1abf55dfe527d0b`。
- 实现及正式验证 subject：`d05beb274290c90aad67f986efdaac49a4e0967b`。
- 当前规格摘要：`61c5d9d70e995c9cdd9dafca7687b9d0524104d60a9aeeaee18b83e792b8d489`。
- 实现审查 context：`316b2fd0461d2aa4689c5a53cb551e5c5c5e331c4e85148d6de2b1a66bfc3f3f`。

唯一生产修改为 `task_service._require_ready_artifacts`，复用既有 freshness evaluator。
spec 按 base/policy/spec 判断，subject-only 变化不再误拒；缺失或错误 base 不再误放行。
分类检查、每个 REVIEW 单元覆盖、错误码、AUTO 路径及 code/action 绑定均保留。

## 验证事实

| 检查 | 本次结果 |
| --- | --- |
| 新回归对旧源码 | 30 passed、3 failed，准确复现 subject-only、base stale、base missing |
| 修复后定向回归 | 33 passed |
| 正式 V1 单元 | 1320 passed |
| 正式 V1 全量回归 | 1958 passed，526.96 秒 |
| 正式 V1 覆盖率轮 | 1958 passed，632.53 秒 |
| 总覆盖率 | 88.12%；显式 `coverage report --fail-under=85` 退出 0 |
| diff coverage | 100%，1 个可执行差异行；90% 门槛保留 |
| 契约、scope、Ruff、format、mypy、smoke | 均通过；mypy 检查 41 个源码文件 |
| whitespace | 原 task base 及已核对 main 到固定 subject 均通过 |

正式 V1 十项 required checks 均 exit 0、无超时。总覆盖率的独立复算为
`(6557 + 1963) / (7225 + 2444) = 88.1167%`，包括分支，不将行覆盖率冒充总覆盖率。
本次没有运行远端 CI，不复用 PR #39 的通过结果覆盖本候选。

## 证据保管与复核

原始 evidence SHA256：`2e44856dac3270f5fe2c1de56f774336b2570e7e5a56b0f941b5d8c1feb5ca7f`。
完整原件、日志、coverage XML/数据库、工具环境及移交清单位于专用本地材料目录
`<ARTIFACT_ROOT>/TASK-0049/`；实际路径由交付消息提供。原始 evidence 含本机命令路径，
因此只在本地任务目录保存，通过本地 Git exclude 排除；日志沿用仓库既有 ignore。
Git 提交仅含不含本机路径的账本、审核材料与本摘要，不修改原始 evidence 字节。
移交归档对每份原件记录字节摘要并读回校验；Git LF 文本不能替代 CRLF 原件。

正式验证使用同分支、同 repository identity 的干净本地检出，并固定到实际提交。
隔离 Python 环境导入路径及两个业务文件的规范化字节已核对；没有移动三个用户原稿。
重新执行可用该环境的 `python -m aiflow status TASK-0049` / `gate TASK-0049 --format json`
核对当前状态；本次并无重跑已通过测试的必要。

## 批准与发布边界

当前 `status`：WAITING_FOR_FINAL_REVIEW、Missing: code_approval、evidence passed。
Gate 拒绝为 `GATE_STATE_INVALID` 与 `GATE_CODE_APPROVAL_STALE`，对应尚未批准代码的
等待状态，不是完整验证失败，也不要求重新获得有效的 spec 批准。

当前远端 main 只读核对仍为 `7dad5c0be700c0ba72ed4f33f8856148e3265825` 且受保护。
后续发布候选包含原 `7eec053` / `10b13d1` 的七文件收尾增量，以及本次准备、独立
测试、修复和治理收尾；以最终 head 对该 base 的累计 diff 为准。须先获 code 批准，
再取得具体 push/merge 授权、通过新候选 required CI，并记录真实合并后才 close。
TASK-0048 不重复关闭，TASK-0028 选项 C、七项历史 BLOCKED、E3 自然双产品案例及
条件性 E4/I1–I5/后续阶段保持原边界。本次不宣称这些条件性条目全部完成。
