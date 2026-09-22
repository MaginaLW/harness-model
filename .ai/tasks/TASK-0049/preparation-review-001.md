# TASK-0049 规格准备与独立核查

日期：2026-09-22。实施前基线：`10b13d17001b3decce17080bc3773fcfe8f5a8fc`。

## 核查结果

独立 sub-agent 只读核查确认：`_require_ready_artifacts` 手工比较 subject 而遗漏
base，与共享 `spec_approval` 规则不一致。最小修复复用既有 freshness evaluator，
保留分类门、批准类型、决策单元覆盖和错误行为。规格技术核查通过，不代表人类批准。

冻结规格摘要：`cf316b043a1dcc104eb4f8de97816f486982b2c148c20b4b37b448740dca41e4`。
CLI classify 为 REVIEW/V1；freeze 成功；validate 为 valid；status 为
WAITING_FOR_SPEC_REVIEW、Missing: spec_approval。第一次 freeze 因标题未匹配
必需章节被拒绝，补齐章节后成功，未跨越实现门。

现有基线检查：`python -m pytest tests/integration/test_begin_close_commands.py -q`
得到 20 passed（15.77 秒）。这是既有测试基线，不能证明缺陷已修复。
实施时须给 make_ready 的有效批准 fixture 补 base，并验证 subject-only、陈旧或
缺失绑定、历史批准混合、错误类型及单元；无效 Schema 可提前拒绝，仍须无状态推进。
完整质量门在实现后执行；当前没有修改受控源码，也没有新增实现批准。

## 发布范围核查

另一独立 sub-agent 通过只读 Git/GitHub 核对：main 为
`7dad5c0be700c0ba72ed4f33f8856148e3265825`、受保护，PR #39 已合并。
核查时本地待发布为 `7eec053` 与 `10b13d1`，相对该 main 共 7 文件、224 增行、
2 删行。包括 TASK-0048 四个真实关闭文件及三个后续文档；不重复 close TASK-0048。
本任务准备提交将增加候选范围，旧候选 `2dffdf0` 的授权与 CI 不覆盖新 head。
最终发布需重新冻结累计范围、完成质量检查并获得具体 push/merge 授权。

## 保留事项

三个既有未跟踪计划原稿保持原样。TASK-0028 选项 C、七个历史 BLOCKED 及依赖真实
案例、目标或阶段准入的 E/I 条目不自动重启。当前可推进的源码修复在规格批准处等待；
后续安全回归测试与文档独立提交，源码按本任务串行 begin、实现、验证和审核。
